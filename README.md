# CSC 221 Final Challenge — Recipe Suggester (APIs + Async + Gemini)

This project satisfies:
- A deployed web service URL
- Two endpoints (REST):
  - GET /id
  - POST /recipe
- Front-end shows EMPL_ID and calls the /recipe endpoint after clicking 'Suggest'
- Uses **real APIs**:
  - Spoonacular (recipe correctness)
  - Pollinations (photo generation via prompt -> image URL)
  - Google AI Studio Gemini (AI blurb text)
- Uses FastAPI + async/await + coroutines (async HTTP calls + asyncio.gather + asyncio.to_thread)

## 1) Run locally

### Install
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Set env vars
Option A: create a `.env` file using `.env.example`

Option B (macOS/Linux):
```bash
export EMPL_ID="12345678"
export LAST_NAME="Hiba"
export SPOONACULAR_API_KEY="YOUR_KEY"
export GOOGLE_AI_STUDIO_API_KEY="YOUR_KEY"
```

### Start server
```bash
uvicorn main:app --reload --port 8080
```

Open:
- http://localhost:8080  (front-end)
- http://localhost:8080/id  (endpoint #1)
- http://localhost:8080/docs (Swagger)

## 2) Deploy to Google App Engine
1) Edit `app.yaml` and set:
   - EMPL_ID
   - SPOONACULAR_API_KEY
   - GOOGLE_AI_STUDIO_API_KEY

2) Deploy:
```bash
gcloud app deploy
```

3) Open the app:
```bash
gcloud app browse
```

## 3) Screenshot requirement
Open the site, enter a recipe, click **Suggest**, wait for results + image, then take a screenshot.

## Notes
- If Google AI Studio key is missing, the app still works, but the AI blurb will say the key isn't set.
- If Spoonacular key is missing, /recipe will return an error (recipes must be correct using the API).
