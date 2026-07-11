---
title: TripWeaver
emoji: ✈️
colorFrom: purple
colorTo: orange
sdk: gradio
app_file: app.py
pinned: false
---

# TripWeaver frontend

Gradio chat UI for TripWeaver. Talks only to the TripWeaver FastAPI backend
over `BACKEND_URL` - never calls OpenAI or Amadeus directly, and never
holds their credentials.

## Local dev

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in BACKEND_URL / BACKEND_API_KEY
python app.py
```

Open http://localhost:7860

## Deploying to Hugging Face Spaces

1. Create a new Space -> SDK: Gradio -> hardware: CPU basic is enough.
2. Push this `frontend/` folder's contents to the Space's git repo root
   (Spaces expects `app.py` and `requirements.txt` at the root of the repo).
3. In the Space's **Settings -> Variables and secrets**, add:
   - `BACKEND_URL` - your deployed Railway backend URL
   - `BACKEND_API_KEY` - one of the keys you set in the backend's
     `TRIPWEAVER_API_KEYS`
4. The Space rebuilds automatically. See the root `README.md` for the full
   deployment order (MCP servers -> backend -> frontend).
