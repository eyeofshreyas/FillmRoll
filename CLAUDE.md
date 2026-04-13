# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Activate virtual environment (Windows)
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run development server
python app.py

# Run production server (same as Heroku)
gunicorn app:app
```

## Architecture

**FilmRoll** is a Flask web app for content-based movie recommendations.

### Data Layer
- `movies_dict.pkl` — serialized DataFrame with movie metadata (title, overview, poster_path, vote_average, movie_id, media_type)
- `similarity.pkl` — pre-computed cosine similarity matrix (rows/cols indexed the same as `movies` DataFrame); too large for git, downloaded from Hugging Face at startup if missing
- `movie-recommender-system.ipynb` — the notebook that builds both pkl files from TMDB data using CountVectorizer + weighted tags + Porter stemming

### Backend (`app.py`)
- Loads both pkl files into globals `movies` (DataFrame) and `similarity` (matrix) at import time
- `recommend(title, n)` — looks up row index, sorts similarity scores, returns top-N as dicts
- `cf_recommend` route — weighted collaborative filtering: blends similarity rows proportional to user's 1–5 star ratings
- TMDB API key is hardcoded (`API_KEY`); all TMDB calls go through `tmdb_get(path, extra_params)`
- AI chat streams from HF Inference API (`meta-llama/Llama-3.1-8B-Instruct`) via SSE; requires `HF_TOKEN` env var
- Google OAuth via Authlib; uses `ProxyFix` for Heroku's HTTPS proxy

### Database (`db.py`)
- Firebase Firestore for persistent user ratings and last mood
- Credentials loaded from `FIREBASE_CREDENTIALS_BASE64` env var (base64-encoded JSON) or local `firebase-credentials.json`
- The `init_firebase()` function reconstructs a valid PEM private key from the env var (Heroku strips newlines)
- Falls back gracefully when Firebase is unavailable (ratings stored in Flask session only)

### Frontend
- `templates/index.html` + `templates/login.html` — Jinja2 templates
- `static/scripts.js` — all client-side JS (fetch calls to backend routes, SSE chat, modal logic)
- `static/styles.css` — dark cinematic theme

### Auth flow
- `/login` → `/auth/google` → `/auth/callback` (stores user info in Flask session)
- `@login_required` decorator guards the main index route
- User email from session is used as Firestore document key

## Environment Variables

| Variable | Purpose |
|---|---|
| `TMDB_API_KEY` | TMDB API key for posters, trailers, cast, trending |
| `FLASK_SECRET` | Flask session secret key |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `HF_TOKEN` | Hugging Face token for AI chat and similarity.pkl download |
| `FIREBASE_CREDENTIALS_BASE64` | Base64-encoded Firebase service account JSON |

## Deployment

Heroku via `Procfile` (`gunicorn app:app`), Python 3.12.9 (`runtime.txt`). The `similarity.pkl` file (~500 MB) is excluded from git and downloaded from `https://huggingface.co/Shreyansh00700/FilmRoll/resolve/main/similarity.pkl` on first startup.
