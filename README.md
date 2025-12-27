# CSC 221 Final Challenge — Recipe Suggester (APIs + Async + Gemini)

This project satisfies:
- A deployed web service URL
- Two endpoints (REST):
  - GET /id
  - POST /recipe
- Front-end shows EMPL_ID and calls the /recipe endpoint after clicking 'Suggest'
- Uses **real APIs**:
  - Google AI Studio Gemini (generates original recipes - ingredients, instructions, and blurb)
  - Pollinations (photo generation via prompt -> image URL)
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

2) Set the Google AI Studio API key as an environment variable (do NOT commit this to git):
```bash
export GOOGLE_AI_STUDIO_API_KEY="your_key_here"
```

3) Deploy (the environment variable will be available during deployment):
```bash
gcloud app deploy
```

Alternatively, you can set it directly during deployment:
```bash
gcloud app deploy --set-env-vars GOOGLE_AI_STUDIO_API_KEY=your_key_here
```

4) Open the app:
```bash
gcloud app browse
```

## 3) Screenshot requirement
Open the site, enter a recipe, click **Suggest**, wait for results + image, then take a screenshot.

## Notes
- Google AI Studio key is required for the app to work (used to generate recipes).
- Recipes are AI-generated based on your description and time constraints, not looked up from a database.
