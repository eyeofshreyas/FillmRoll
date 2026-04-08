# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run locally (dev)
python app.py

# Run with gunicorn (prod-like)
gunicorn app:app

# Install dependencies
pip install -r requirements.txt
```

## Architecture

**FilmRoll** is a Flask-based movie recommendation web app deployed on Heroku.

### Core files
- [app.py](app.py) — Flask app, all routes and business logic
- [db.py](db.py) — Firebase/Firestore client (init + read/write helpers)
- [templates/index.html](templates/index.html) — main SPA-style page
- [templates/login.html](templates/login.html) — Google OAuth login page
- [static/scripts.js](static/scripts.js) — all frontend JS
- [static/styles.css](static/styles.css) — all CSS

### Data files (not in git)
- `movies_dict.pkl` — pandas DataFrame of movies (title, poster_path, movie_id, media_type, vote_average, overview)
- `similarity.pkl` — cosine similarity matrix (NxN); downloaded from Hugging Face at startup if missing (`HF_TOKEN` env var needed for private repo)

### Recommendation approaches
1. **Content-based** (`/recommend`): cosine similarity via `similarity.pkl`
2. **Collaborative filtering** (`/cf-recommend`): weighted sum of similarity vectors for rated movies
3. **Mood-based** (`/mood`): TMDB Discover API filtered by genre IDs mapped from mood name
4. **Genre-based** (`/genre`): TMDB Discover API by genre slug
5. **Trending** (`/trending`): TMDB trending movies + TV, week window

### External services
- **TMDB API** — poster images, trailers, cast, details, discover, trending. Key hardcoded as `API_KEY` in app.py
- **Hugging Face Inference API** — Llama 3.1 chat (`/api/chat`) and AI-powered search (`/api/search`); requires `HF_TOKEN` env var
- **Google OAuth** — auth via Authlib; requires `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` env vars
- **Firebase Firestore** — persists user ratings and last mood; initialized from `FIREBASE_CREDENTIALS_BASE64` (base64 JSON) or local `firebase-credentials.json`

### Environment variables
| Variable | Purpose |
|---|---|
| `FLASK_SECRET` | Flask session secret |
| `HF_TOKEN` | Hugging Face API token (chat + similarity download) |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `FIREBASE_CREDENTIALS_BASE64` | Base64-encoded Firebase service account JSON |

### Auth flow
All routes except `/login`, `/auth/google`, `/auth/callback` require `@login_required` (checks `session['user']`). Google OAuth redirects to `/auth/callback` which sets `session['user']`.

### Rating persistence
Ratings stored in both Flask session and Firebase. On first `/my-ratings` or `/cf-recommend` call, session is synced from Firebase and `session['db_synced']` flag is set to avoid redundant reads.

### Deployment
Deployed on Heroku. `Procfile` runs `gunicorn app:app`. `ProxyFix` middleware is applied so OAuth redirects use `https://`.
