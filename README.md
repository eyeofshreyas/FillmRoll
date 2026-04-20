<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white" alt="Python 3.12" />
  <img src="https://img.shields.io/badge/Flask-Web_App-black?logo=flask" alt="Flask" />
  <img src="https://img.shields.io/badge/Qdrant-Vectors-DC244C?logo=qdrant&logoColor=white" alt="Qdrant" />
  <img src="https://img.shields.io/badge/Firebase-Firestore-FFCA28?logo=firebase&logoColor=black" alt="Firebase" />
  <img src="https://img.shields.io/badge/TMDB-API-01d277?logo=themoviedatabase&logoColor=white" alt="TMDB" />
  <img src="https://img.shields.io/badge/Hugging_Face-AI_Chat-FFD21E?logo=huggingface&logoColor=black" alt="Hugging Face" />
  <img src="https://img.shields.io/badge/Google-OAuth2-4285F4?logo=google&logoColor=white" alt="Google OAuth" />
</p>

<h1 align="center">FilmRoll — Movie discovery & recommendations</h1>

<p align="center">
  Flask web app for browsing TMDB content, content-based recommendations via Qdrant vector search, optional collaborative-style blending from your ratings, Google sign-in, Firestore-backed watchlists and reviews, and an AI assistant powered by Llama&nbsp;3.1 on Hugging Face.
</p>

---

## What it does

- **Similar-title recommendations** — Each title in your catalog has a dense embedding. Qdrant returns nearest neighbors (cosine similarity) for “more like this.”
- **“For you” blends** — Star ratings in Firestore are combined with those vectors (weighted positives and light negative weight for low scores) to suggest titles aligned with your taste.
- **Home & browse** — Cached trending and new releases, mood presets, and genre discovery, all driven by TMDB.
- **Detail drawer** — Trailers, cast, genres, runtime, tagline, and **where to watch** (stream / rent / buy) for a chosen region.
- **Watchlist** — Add/remove items; stored per user in Firestore.
- **Reviews** — Short reviews with star ratings; listed per title; users can delete their own.
- **AI assistant** — Streaming chat and natural-language catalog search via **Hugging Face Inference** (`meta-llama/Llama-3.1-8B-Instruct`), plus extras like a “movie night matchmaker” and “why you might like this” blurbs when `HF_TOKEN` is set.
- **Auth** — Google OAuth (Authlib); main routes require a signed-in session.

---

## Architecture (how the repo is laid out)

| Area | Role |
|------|------|
| `app.py` | Creates the Flask app, loads env, initializes OAuth, Firebase, and the ML service, registers blueprints, optionally warms TMDB caches in a background thread. |
| `extensions.py` | Shared Authlib `OAuth` instance and `init_oauth(app)`. |
| `db.py` | Firebase Admin bootstrap (base64 or local JSON credentials), Firestore helpers for ratings, watchlist, and reviews. |
| `blueprints/auth.py` | Login, Google OAuth callback, logout, `login_required` decorator. |
| `blueprints/core.py` | Home page, `/recommend`, `/home-data`, `/trending`, `/new-releases`, `/genre`, `/mood`, `/details`. |
| `blueprints/user.py` | `/rate`, `/my-ratings`, `/cf-recommend`, watchlist CRUD. |
| `blueprints/ai.py` | `/api/ai-status`, `/api/chat` (SSE), `/api/ai-search`, `/api/matchmaker`, `/api/why-you-like`. |
| `blueprints/reviews.py` | `/api/reviews` POST/GET/DELETE. |
| `services/ml.py` | Loads `movies_dict.pkl`, talks to Qdrant collection `filmroll_movies` for recommendations and CF-style queries. |
| `services/tmdb.py` | TMDB HTTP helper; posters, discover, etc. Uses `TMDB_API_KEY`. |
| `services/ai.py` | Hugging Face chat completions (streaming + sync). |
| `services/cache.py` | Small in-process TTL cache for TMDB-heavy endpoints. |
| `static/` | Modular CSS under `css/`, ES modules under `js/` (`main.js` entry). |
| `templates/` | `index.html`, `login.html`. |
| `scripts/upload_to_qdrant.py` | One-off uploader: `movies_dict.pkl` + `vectors.pkl` → Qdrant. |

---

## Data & Qdrant setup

1. **Build artifacts** — Run `movie-recommender-system.ipynb` to produce **`movies_dict.pkl`** and **`vectors.pkl`** (tag vectors + metadata; the notebook no longer relies on a huge `similarity.pkl` matrix for serving).
2. **Vector index** — Create/populate the Qdrant collection:

   ```bash
   set QDRANT_URL=https://your-cluster.example.cloud.qdrant.io:6333
   set QDRANT_API_KEY=your_key
   python scripts/upload_to_qdrant.py
   ```

   Collection name: **`filmroll_movies`**, cosine distance, point IDs aligned with dataframe row indices (see script).

3. **Runtime** — The app needs **`movies_dict.pkl`** at the project root and valid **`QDRANT_URL`** (and API key if your cluster requires it).

---

## Environment variables

| Variable | Purpose |
|----------|---------|
| `TMDB_API_KEY` | [TMDB](https://www.themoviedb.org/settings/api) key for all movie/TV requests. |
| `FLASK_SECRET` or `SECRET_KEY` | Flask session signing. |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google OAuth Web client. |
| `FIREBASE_CREDENTIALS_BASE64` | Base64-encoded Firebase service-account JSON (good for PaaS). |
| `FIREBASE_CREDENTIALS` | Optional path to JSON file; defaults to `firebase-credentials.json` if present. |
| `QDRANT_URL` | Qdrant server URL (required for recommendations). |
| `QDRANT_API_KEY` | Qdrant API key (empty for local/no auth). |
| `HF_TOKEN` | [Hugging Face](https://huggingface.co/settings/tokens) token; enables AI chat and related routes. |
| `PORT` | Optional; dev server defaults to 5000. |

Behind a reverse proxy that terminates TLS, set Flask/Werkzeug’s **`ProxyFix`** (or equivalent) so OAuth redirect URLs use `https://` — not wired in `app.py` by default.

---

## Local run

```powershell
cd "path\to\MOVIE REOCOMDATION SYSTEM"
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
# If training the notebook:
# pip install scikit-learn nltk

# Place movies_dict.pkl (and ensure Qdrant is populated). Create a .env with
# the variables from the table below, then:
python app.py
```

Open `http://localhost:5000` (or the port in `PORT`). Sign in with Google; the UI talks to the blueprint JSON routes under the same origin.

**Production-style:**

```bash
gunicorn app:app
```

---

## Project structure (concise)

```text
├── app.py
├── extensions.py
├── db.py
├── blueprints/
│   ├── auth.py
│   ├── core.py
│   ├── user.py
│   ├── ai.py
│   └── reviews.py
├── services/
│   ├── ml.py
│   ├── tmdb.py
│   ├── ai.py
│   └── cache.py
├── scripts/
│   └── upload_to_qdrant.py
├── static/
│   ├── css/
│   └── js/
├── templates/
├── movie-recommender-system.ipynb
├── movies_dict.pkl          # required at runtime (from notebook)
├── vectors.pkl              # used by upload script, not loaded by Flask
└── requirements.txt
```

---

## License

This project is licensed under the [MIT License](LICENSE).

<p align="center">Flask · Qdrant · Firebase · TMDB · Hugging Face</p>
