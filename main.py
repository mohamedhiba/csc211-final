import os
import asyncio
from typing import List, Optional
from urllib.parse import quote

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# trying to load .env file if it exists (doesn't matter if it fails)
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

# environment variables stuff
# if you want to run this locally, you need to set the environment variables in the .env file, I have mine in the .env (didn't submit it in the final version)
EMPL_ID = os.getenv("EMPL_ID", "00000000")
LAST_NAME = os.getenv("LAST_NAME", "LastName")

SPOONACULAR_API_KEY = os.getenv("SPOONACULAR_API_KEY", "")
GOOGLE_AI_STUDIO_API_KEY = os.getenv("GOOGLE_AI_STUDIO_API_KEY", "")

# pollinations api for generating images, no key needed
# https://image.pollinations.ai/prompt/<url-encoded-prompt>
POLLINATIONS_BASE = "https://image.pollinations.ai/prompt/"


# fastapi app setup
app = FastAPI(title="CSC 221 Final Challenge - Recipe Suggester (APIs + Async + Gemini)")

# adding cors middleware so frontend can call this from anywhere
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def home():
    return FileResponse("static/index.html")


@app.get("/id")
async def get_id():
    """endpoint #1 - just returns my empl_id and last name"""
    return {"EMPL_ID": EMPL_ID, "LAST_NAME": LAST_NAME}


class RecipeRequest(BaseModel):
    description: str = Field(..., min_length=1, max_length=120)
    max_time: int = Field(60, ge=5, le=240)


class Ingredient(BaseModel):
    name: str
    amount: str


class RecipeResponse(BaseModel):
    title: str
    image_url: str
    total_time_minutes: int
    source_url: Optional[str] = None
    ingredients: List[Ingredient]
    instructions: List[str]
    ai_blurb: str
    api_used: str


async def spoonacular_search(query: str, max_time: int, client: httpx.AsyncClient) -> int:
    """searches spoonacular api for a recipe and returns the recipe id"""
    url = "https://api.spoonacular.com/recipes/complexSearch"
    params = {
        "query": query,
        "maxReadyTime": max_time,
        "number": 1,
        "apiKey": SPOONACULAR_API_KEY,
    }
    r = await client.get(url, params=params, timeout=20)
    if r.status_code == 401:
        raise HTTPException(status_code=500, detail="Invalid SPOONACULAR_API_KEY (401).")
    r.raise_for_status()
    data = r.json()
    results = data.get("results", [])
    if not results:
        raise HTTPException(status_code=404, detail="No recipes found for that query/time.")
    return int(results[0]["id"])


async def spoonacular_info(recipe_id: int, client: httpx.AsyncClient) -> dict:
    """gets all the recipe details from spoonacular using the recipe id"""
    url = f"https://api.spoonacular.com/recipes/{recipe_id}/information"
    params = {"apiKey": SPOONACULAR_API_KEY, "includeNutrition": "false"}
    r = await client.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def pollinations_image_url(title: str) -> str:
    """generates an image url using pollinations api based on the recipe title"""
    prompt = f"high quality food photography of {title}, plated, natural lighting"
    return POLLINATIONS_BASE + quote(prompt)


def extract_instructions(info: dict) -> List[str]:
    analyzed = info.get("analyzedInstructions") or []
    steps: List[str] = []
    if analyzed and analyzed[0].get("steps"):
        for s in analyzed[0]["steps"]:
            step_text = (s.get("step") or "").strip()
            if step_text:
                steps.append(step_text)
    else:
        raw = (info.get("instructions") or "").strip()
        if raw:
            steps = [x.strip() for x in raw.split(".") if x.strip()]

    if not steps:
        steps = ["No step-by-step instructions were returned by the API for this recipe."]
    return steps


def extract_ingredients(info: dict) -> List[Ingredient]:
    out: List[Ingredient] = []
    for item in info.get("extendedIngredients", []) or []:
        name = item.get("name", "ingredient")
        amt = (item.get("original") or "").strip()
        out.append(Ingredient(name=name, amount=amt if amt else name))
    if not out:
        out = [Ingredient(name="N/A", amount="No ingredients returned by the API.")]
    return out


def gemini_blurb_sync(title: str) -> str:
    """calls gemini api to generate a blurb about the recipe, runs in thread so it doesn't block"""
    if not GOOGLE_AI_STUDIO_API_KEY:
        return "AI Studio key not set. (Set GOOGLE_AI_STUDIO_API_KEY to enable Gemini blurb.)"

    try:
        import google.generativeai as genai  # type: ignore
        genai.configure(api_key=GOOGLE_AI_STUDIO_API_KEY)

        model = genai.GenerativeModel("gemini-flash-latest")
        prompt = (
            f"Write a short, friendly 2-line description for the recipe '{title}'. "
            f"Keep it simple and student-like, no fancy tone."
        )
        resp = model.generate_content(prompt)
        text = (getattr(resp, "text", "") or "").strip()
        return text if text else "Gemini returned an empty response."
    except Exception as e:
        return f"Gemini error: {e}"


@app.post("/recipe", response_model=RecipeResponse)
async def recipe(req: RecipeRequest):
    """
    endpoint #2 - main recipe endpoint
    uses spoonacular for recipes, pollinations for images, and gemini for the blurb
    """
    if not SPOONACULAR_API_KEY:
        raise HTTPException(status_code=500, detail="Server missing SPOONACULAR_API_KEY.")

    query = req.description.strip()
    max_time = req.max_time

    async with httpx.AsyncClient() as client:
        # first find the recipe id
        recipe_id = await spoonacular_search(query, max_time, client)

        # now get recipe info and generate image in parallel
        # running image generation in thread to show async usage
        info_task = spoonacular_info(recipe_id, client)
        img_task = asyncio.to_thread(pollinations_image_url, query)
        # using query for now, will regenerate with title later once we have it
        info, image_url = await asyncio.gather(info_task, img_task)

    title = (info.get("title") or query.title()).strip()
    total_time = int(info.get("readyInMinutes") or max_time)

    ingredients = extract_ingredients(info)
    instructions = extract_instructions(info)

    # call gemini to get the blurb, running in thread
    ai_blurb = await asyncio.to_thread(gemini_blurb_sync, title)

    # regenerate image url with the actual recipe title instead of the query
    image_url = pollinations_image_url(title)

    return RecipeResponse(
        title=title,
        image_url=image_url,
        total_time_minutes=total_time,
        source_url=info.get("sourceUrl"),
        ingredients=ingredients,
        instructions=instructions,
        ai_blurb=ai_blurb,
        api_used="Spoonacular (recipes) + Pollinations (image) + Google AI Studio Gemini (blurb)"
    )
