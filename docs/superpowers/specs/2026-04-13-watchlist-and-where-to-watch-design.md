# Design Spec: Watchlist & "Where to Watch"

**Date:** 2026-04-13  
**Status:** Approved  

---

## Overview

Two high-priority features to increase user engagement:

1. **"Where to Watch"** — Show streaming providers (Netflix, Prime, etc.) inside the movie details modal, auto-detected by the user's browser locale.
2. **Personal Watchlist** — Bookmark movies to a persistent watchlist, accessible via the user dropdown menu and shown as a full-page view.

---

## Feature 1: Where to Watch

### Backend (`app.py`)

The existing `/details` POST endpoint gains one additional TMDB call:

```python
tmdb_get(f'/{media_type}/{item_id}/watch/providers')
```

- The frontend sends a `country` field in the POST body (e.g. `"IN"`, `"US"`).
- Backend picks `results.get(country, results.get('US', {}))` as fallback.
- Extracts `flatrate`, `rent`, and `buy` arrays. Each item has `provider_name` and `logo_path`.
- These are included in the existing `/details` JSON response under a `watch_providers` key:
  ```json
  {
    "watch_providers": {
      "flatrate": [{"provider_name": "Netflix", "logo_path": "/path.png"}],
      "rent": [...],
      "buy": [...]
    }
  }
  ```

### Frontend (`scripts.js` + `index.html`)

- When opening the details modal, include `country: navigator.language.split('-')[1] || 'US'` in the fetch body.
- Modal HTML gains a "Where to Watch" section below the cast row.
- Providers shown as 32px logo images with `title` tooltip for the name.
- Grouped under "Stream", "Rent", "Buy" labels.
- If no providers found: show "Not available for streaming in your region."

---

## Feature 2: Personal Watchlist

### Database (`db.py`)

Three new functions, following the exact pattern of the existing ratings functions:

| Function | Description |
|---|---|
| `get_watchlist(email)` | Reads `watchlist` array from `users/{email}` Firestore doc |
| `add_to_watchlist(email, item)` | Appends item using `firestore.ArrayUnion` |
| `remove_from_watchlist(email, movie_id)` | Removes matching item using `firestore.ArrayRemove` |

Each watchlist item stored as:
```json
{
  "movie_id": 123,
  "title": "Inception",
  "poster": "https://...",
  "media_type": "movie",
  "rating": 8.4,
  "added_at": "2026-04-13T00:00:00Z"
}
```

### Backend (`app.py`)

Three new `@login_required` routes:

| Route | Method | Description |
|---|---|---|
| `/watchlist` | GET | Returns user's watchlist array (session-cached like `/my-ratings`) |
| `/watchlist/add` | POST | Validates payload, calls `add_to_watchlist`, updates session cache |
| `/watchlist/remove` | POST | Calls `remove_from_watchlist` by `movie_id`, updates session cache |

Session key: `watchlist` — list of watchlist items, populated on first `/watchlist` GET.

### Frontend (`scripts.js` + `index.html`)

**Bookmark button:**
- Appears on every movie card and inside the details modal.
- SVG bookmark icon — outline when not in watchlist, filled when bookmarked.
- Clicking toggles via `/watchlist/add` or `/watchlist/remove`.
- JS maintains a `watchlistIds` Set (populated on app load) for instant toggle state without extra network calls.

**Watchlist page:**
- `showWatchlist()` function follows exact pattern of `navForYou()` / `navBrowse()` — hides hero and other sections, shows dedicated watchlist grid.
- Uses existing card HTML structure for consistency.
- Empty state: "Your watchlist is empty. Bookmark movies to save them here."

**User dropdown:**
- "My Watchlist" item added above "Sign out" in the dropdown menu.
- Same style/structure as the existing "Sign out" link.
- Calls `showWatchlist()` and closes the dropdown.

---

## Error Handling

- TMDB watch providers call failure: silently returns `watch_providers: {}` — frontend shows "Not available" message.
- Firestore watchlist errors: log to stderr, return `[]` gracefully (same pattern as ratings).
- Add/remove while unauthenticated: `@login_required` redirects to login.

---

## What is NOT in scope

- Sharing watchlists publicly
- Watchlist ordering/sorting
- Watchlist count badge on the avatar
- Country picker setting
