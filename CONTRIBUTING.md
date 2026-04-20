# Contributing to FilmRoll

Thanks for your interest in improving FilmRoll.

## Development Setup

1. Fork the repository and clone your fork.
2. Create and activate a virtual environment.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

Optional notebook/training dependencies:

```bash
pip install scikit-learn nltk
```

4. Create a `.env` file with required environment variables listed in `README.md`.
5. Run locally:

```bash
python app.py
```

## Branching and Pull Requests

- Create a feature branch from `main`:
  - `feat/<short-description>` for features
  - `fix/<short-description>` for bug fixes
- Keep pull requests focused and small.
- Write clear PR descriptions: what changed, why, and how to test.

## Code Style

- Follow existing project structure (`blueprints/`, `services/`, `db.py`, `static/`).
- Keep functions small and focused.
- Prefer explicit error handling for external API/database calls.
- Do not commit secrets (tokens, credentials, `.env`, service-account JSON).

## Testing and Verification

Before opening a PR:

- Ensure the app starts without errors.
- Validate core flows:
  - Google login
  - recommendations
  - details modal
  - watchlist and ratings
  - AI endpoints (if `HF_TOKEN` is configured)
- If adding endpoints, verify response shape is consistent with frontend usage.

## Commit Guidelines

- Use descriptive commit messages in imperative mood:
  - `fix watchlist remove response handling`
  - `add fallback when TMDB details request fails`

## Reporting Bugs

Please open an issue and include:

- What happened
- Expected behavior
- Steps to reproduce
- Logs or screenshots if available
- Environment details (OS, Python version, browser)

## Questions

If you're unsure about an approach, open a discussion or draft PR early.
