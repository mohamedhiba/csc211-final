import os
import asyncio
import json
from typing import List, Optional, Dict
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


def gemini_generate_recipe_sync(description: str, max_time: int) -> Dict:
    """generates a recipe using gemini api based on description and max time"""
    if not GOOGLE_AI_STUDIO_API_KEY:
        raise HTTPException(status_code=500, detail="Server missing GOOGLE_AI_STUDIO_API_KEY.")
    
    try:
        import google.generativeai as genai  # type: ignore
        genai.configure(api_key=GOOGLE_AI_STUDIO_API_KEY)
        
        model = genai.GenerativeModel("gemini-flash-latest")
        prompt = f"""Generate a recipe based on this description: "{description}"
The recipe should take no more than {max_time} minutes to prepare and cook.

Return the response as valid JSON with this exact structure:
{{
    "title": "Recipe Title",
    "total_time_minutes": {max_time},
    "ingredients": [
        {{"name": "ingredient name", "amount": "amount with units"}},
        {{"name": "ingredient name", "amount": "amount with units"}}
    ],
    "instructions": [
        "Step 1 instruction",
        "Step 2 instruction",
        "Step 3 instruction"
    ],
    "blurb": "A short 2-line friendly description of this recipe, keep it simple and student-like"
}}

Make sure the JSON is valid and the recipe is creative and matches the description. Include at least 3 ingredients and at least 3 steps."""
        
        resp = model.generate_content(prompt)
        text = (getattr(resp, "text", "") or "").strip()
        
        # try to extract json from the response (gemini might wrap it in markdown)
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        
        recipe_data = json.loads(text)
        return recipe_data
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Gemini returned invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini error: {str(e)}")


def pollinations_image_url(title: str) -> str:
    """generates an image url using pollinations api based on the recipe title"""
    prompt = f"high quality food photography of {title}, plated, natural lighting"
    return POLLINATIONS_BASE + quote(prompt)


@app.post("/recipe", response_model=RecipeResponse)
async def recipe(req: RecipeRequest):
    """
    endpoint #2 - main recipe endpoint
    uses gemini to generate original recipes, pollinations for images
    """
    if not GOOGLE_AI_STUDIO_API_KEY:
        raise HTTPException(status_code=500, detail="Server missing GOOGLE_AI_STUDIO_API_KEY.")

    query = req.description.strip()
    max_time = req.max_time

    # generate recipe using gemini (running in thread since it's sync)
    recipe_data = await asyncio.to_thread(gemini_generate_recipe_sync, query, max_time)
    title = recipe_data.get("title", query.title()).strip()
    
    # generate image with the recipe title
    image_url = await asyncio.to_thread(pollinations_image_url, title)

    # extract ingredients and instructions from gemini response
    ingredients_list = recipe_data.get("ingredients", [])
    ingredients = [Ingredient(name=ing.get("name", ""), amount=ing.get("amount", "")) 
                   for ing in ingredients_list]
    
    instructions = recipe_data.get("instructions", [])
    if not instructions:
        instructions = ["No instructions provided."]
    
    total_time = int(recipe_data.get("total_time_minutes", max_time))
    ai_blurb = recipe_data.get("blurb", "A tasty recipe generated just for you!")

    return RecipeResponse(
        title=title,
        image_url=image_url,
        total_time_minutes=total_time,
        source_url=None,  # no source url since it's generated
        ingredients=ingredients,
        instructions=instructions,
        ai_blurb=ai_blurb,
        api_used="Google AI Studio Gemini (recipe generation) + Pollinations (image generation)"
    )
