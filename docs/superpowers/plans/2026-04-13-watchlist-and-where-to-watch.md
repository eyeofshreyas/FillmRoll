# Watchlist & Where to Watch — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add persistent personal watchlists and streaming provider info to FilmRoll.

**Architecture:** Watchlist stored as a Firestore map `users/{email}.watchlist.{movie_id}` (keyed by string movie_id for safe add/remove). Watch providers fetched from TMDB `/watch/providers` inside the existing `/details` route, country auto-detected from browser locale. Frontend follows all existing patterns (`openModal` intercept, `$()` helper, section show/hide model).

**Tech Stack:** Flask, Firebase Firestore, TMDB API, vanilla JS, CSS custom properties.

---

## File Map

| File | Change |
|---|---|
| `db.py` | Add `get_watchlist`, `add_to_watchlist`, `remove_from_watchlist` |
| `app.py` | Add `/watchlist` GET, `/watchlist/add` POST, `/watchlist/remove` POST; add providers call to `/details` |
| `templates/index.html` | Add watchlist page section, watchlist dropdown item, bookmark button in modal, providers section in modal |
| `static/scripts.js` | Add `watchlistIds` Set, `toggleWatchlist`, `showWatchlist`, `loadWatchlist`; send `country` in `/details` fetch; render providers |
| `static/styles.css` | Add styles for providers section, bookmark button, watchlist page |

---

## Task 1: Watchlist DB functions (`db.py`)

**Files:**
- Modify: `db.py`

- [ ] **Step 1: Add the three functions** at the bottom of `db.py` (after `save_last_mood`):

```python
def get_watchlist(email):
    """Return watchlist as a list of item dicts, sorted newest-first."""
    db = init_firebase()
    if not db or not email:
        return []
    try:
        doc = db.collection('users').document(email).get()
        if doc.exists:
            wl = doc.to_dict().get('watchlist', {})
            items = list(wl.values())
            items.sort(key=lambda x: x.get('added_at', ''), reverse=True)
            return items
    except Exception as e:
        print(f"Firebase watchlist read error: {e}")
    return []


def add_to_watchlist(email, item):
    """Add a movie to the watchlist map, keyed by str(movie_id)."""
    db = init_firebase()
    if not db or not email:
        return False
    try:
        key = str(item['movie_id'])
        db.collection('users').document(email).set(
            {'watchlist': {key: item}}, merge=True
        )
        return True
    except Exception as e:
        print(f"Firebase watchlist add error: {e}")
        return False


def remove_from_watchlist(email, movie_id):
    """Remove a movie from the watchlist map by movie_id."""
    db = init_firebase()
    if not db or not email:
        return False
    try:
        from google.cloud import firestore as _fs
        key = f'watchlist.{movie_id}'
        db.collection('users').document(email).update(
            {key: _fs.DELETE_FIELD}
        )
        return True
    except Exception as e:
        print(f"Firebase watchlist remove error: {e}")
        return False
```

- [ ] **Step 2: Update the import at the top of `app.py`** to include the new functions:

In `app.py` line 14, change:
```python
from db import get_user_ratings, save_user_rating, save_last_mood
```
to:
```python
from db import (get_user_ratings, save_user_rating, save_last_mood,
                get_watchlist, add_to_watchlist, remove_from_watchlist)
```

- [ ] **Step 3: Verify manually** — start the Flask dev server and check no import errors:

```bash
python app.py
```
Expected: server starts without `ImportError`.

- [ ] **Step 4: Commit**

```bash
git add db.py app.py
git commit -m "feat: add watchlist DB functions (get/add/remove)"
```

---

## Task 2: Watchlist backend routes (`app.py`)

**Files:**
- Modify: `app.py` (add three routes after the `/cf-recommend` route)

- [ ] **Step 1: Add the three routes** before `if __name__ == '__main__':` in `app.py`:

```python
@app.route('/watchlist')
@login_required
def get_watchlist_route():
    """Return the current user's watchlist, with session cache."""
    user_email = session.get('user', {}).get('email')
    if user_email and 'watchlist_synced' not in session:
        session['watchlist'] = get_watchlist(user_email)
        session['watchlist_synced'] = True
        session.modified = True
    return jsonify(session.get('watchlist', []))


@app.route('/watchlist/add', methods=['POST'])
@login_required
def watchlist_add():
    data = request.get_json()
    movie_id = data.get('movie_id')
    title = data.get('title', '')
    if not movie_id or not title:
        return jsonify({'error': 'movie_id and title are required'}), 400

    item = {
        'movie_id':   int(movie_id),
        'title':      title,
        'poster':     data.get('poster', ''),
        'media_type': data.get('media_type', 'movie'),
        'rating':     data.get('rating', 0),
        'added_at':   __import__('datetime').datetime.utcnow().isoformat(),
    }

    user_email = session.get('user', {}).get('email')
    if user_email:
        add_to_watchlist(user_email, item)

    wl = session.get('watchlist', [])
    wl = [m for m in wl if m.get('movie_id') != int(movie_id)]
    wl.insert(0, item)
    session['watchlist'] = wl
    session.modified = True

    return jsonify({'ok': True, 'count': len(wl)})


@app.route('/watchlist/remove', methods=['POST'])
@login_required
def watchlist_remove():
    data = request.get_json()
    movie_id = data.get('movie_id')
    if not movie_id:
        return jsonify({'error': 'movie_id is required'}), 400

    user_email = session.get('user', {}).get('email')
    if user_email:
        remove_from_watchlist(user_email, str(movie_id))

    wl = session.get('watchlist', [])
    wl = [m for m in wl if m.get('movie_id') != int(movie_id)]
    session['watchlist'] = wl
    session.modified = True

    return jsonify({'ok': True, 'count': len(wl)})
```

- [ ] **Step 2: Verify manually** — restart Flask, then in a browser open DevTools console and run:

```js
fetch('/watchlist').then(r => r.json()).then(console.log)
```
Expected: `[]` (empty array, no error).

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: add watchlist API routes (get/add/remove)"
```

---

## Task 3: Add watch providers to `/details` route (`app.py`)

**Files:**
- Modify: `app.py` — the `item_details()` function

- [ ] **Step 1: Add providers fetch** inside `item_details()`. Find the block that ends with `return jsonify({...})` (around line 407) and replace it:

```python
    # ── Watch Providers ───────────────────────────────────────
    country = data.get('country', 'US').upper()
    providers_data = tmdb_get(f'/{media_type}/{item_id}/watch/providers')
    all_regions = providers_data.get('results', {})
    region = all_regions.get(country) or all_regions.get('US') or {}
    watch_providers = {
        'flatrate': [
            {'provider_name': p['provider_name'],
             'logo_path': IMG_BASE + p['logo_path'] if p.get('logo_path') else None}
            for p in region.get('flatrate', [])
        ],
        'rent': [
            {'provider_name': p['provider_name'],
             'logo_path': IMG_BASE + p['logo_path'] if p.get('logo_path') else None}
            for p in region.get('rent', [])
        ],
        'buy': [
            {'provider_name': p['provider_name'],
             'logo_path': IMG_BASE + p['logo_path'] if p.get('logo_path') else None}
            for p in region.get('buy', [])
        ],
    }

    return jsonify({
        'trailer_key':    trailer_key,
        'cast':           cast,
        'genres':         genres,
        'runtime':        runtime,
        'tagline':        tagline,
        'watch_providers': watch_providers,
    })
```

The new `watch_providers` field is added at the end of the existing `return jsonify({...})`. Remove the old `return jsonify({...})` block and replace with the above.

- [ ] **Step 2: Verify manually** — restart Flask, open DevTools console and run:

```js
fetch('/details', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({movie_id: 550, title: 'Fight Club', media_type: 'movie', country: 'IN'})
}).then(r => r.json()).then(d => console.log(d.watch_providers))
```
Expected: object with `flatrate`, `rent`, `buy` arrays (may be empty depending on TMDB data).

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: add watch providers to /details endpoint"
```

---

## Task 4: Watchlist page + dropdown link in HTML (`index.html`)

**Files:**
- Modify: `templates/index.html`

- [ ] **Step 1: Add "My Watchlist" to the user dropdown** — find the dropdown block (around line 62–73). Add before the `<div class="dropdown-divider">`:

```html
          <a href="#" class="dropdown-item" onclick="showWatchlist(); toggleUserMenu(); return false;">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>
            My Watchlist
          </a>
          <div class="dropdown-divider"></div>
```

So the full dropdown now reads:

```html
        <div class="user-dropdown" id="user-dropdown">
          <div class="user-info">
            <div class="user-name">{{ user.name }}</div>
            <div class="user-email">{{ user.email }}</div>
          </div>
          <div class="dropdown-divider"></div>
          <a href="#" class="dropdown-item" onclick="showWatchlist(); toggleUserMenu(); return false;">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>
            My Watchlist
          </a>
          <div class="dropdown-divider"></div>
          <a href="/logout" class="dropdown-item">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
            Sign out
          </a>
        </div>
```

- [ ] **Step 2: Add the watchlist page section** — add this block right before `<!-- ── MODAL ── -->` (around line 271):

```html
  <!-- ── WATCHLIST PAGE ── -->
  <main class="page" id="watchlist-page" style="display:none">
    <div id="watchlist-spinner" style="display:none">
      <div class="dots"><span></span><span></span><span></span></div>
      <div class="spin-msg">Loading your watchlist</div>
    </div>
    <div id="watchlist-header" class="section-row" style="margin-bottom:24px">
      <h3>My Watchlist</h3>
      <span class="count-pill" id="watchlist-count"></span>
    </div>
    <div id="watchlist-empty" style="display:none;text-align:center;padding:80px 0;color:var(--text3);font-size:0.95rem">
      Your watchlist is empty.<br>Bookmark movies to save them here.
    </div>
    <div class="grid" id="watchlist-grid"></div>
  </main>
```

- [ ] **Step 3: Add bookmark button to the modal** — inside `<div class="modal-rate-row">` (around line 300), add a bookmark button as the last child:

```html
      <div class="modal-rate-row">
        <span class="rate-label">Your rating</span>
        <div class="star-rating" id="modal-stars">
          <span class="star" data-v="1">★</span>
          <span class="star" data-v="2">★</span>
          <span class="star" data-v="3">★</span>
          <span class="star" data-v="4">★</span>
          <span class="star" data-v="5">★</span>
        </div>
        <span class="rate-msg" id="rate-msg"></span>
        <button class="btn-bookmark" id="modal-bookmark" onclick="toggleWatchlist()" title="Add to watchlist">
          <svg id="bookmark-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>
        </button>
      </div>
```

- [ ] **Step 4: Add providers section to the modal** — add this block right after `</div>` closing `modal-cast-row` (around line 297) and before `modal-rate-row`:

```html
      <div class="modal-providers-row" id="modal-providers" style="display:none">
        <div class="providers-label">Where to Watch</div>
        <div class="providers-groups" id="providers-groups"></div>
      </div>
```

- [ ] **Step 5: Verify HTML renders** — open the app in the browser. Confirm:
  - User dropdown shows "My Watchlist" above "Sign out"
  - No JS console errors on page load

- [ ] **Step 6: Commit**

```bash
git add templates/index.html
git commit -m "feat: add watchlist page, bookmark button, providers section to HTML"
```

---

## Task 5: Watchlist & providers JavaScript (`scripts.js`)

**Files:**
- Modify: `static/scripts.js`

- [ ] **Step 1: Add watchlist state + load function** — add at the top of `scripts.js` (after the `userRatings = {}` declaration, around line 705):

```js
/* ══════════════════════════════════════════
   WATCHLIST
══════════════════════════════════════════ */
let watchlistIds = new Set();  // Set of movie_id numbers for O(1) lookup

async function loadWatchlist() {
    try {
        const res = await fetch('/watchlist');
        const items = await res.json();
        watchlistIds = new Set(items.map(m => m.movie_id));
    } catch (_) { }
}
loadWatchlist();

async function toggleWatchlist() {
    if (!currentModalMovie) return;
    const id = currentModalMovie.movie_id;
    if (!id) return;

    const inList = watchlistIds.has(id);
    const url = inList ? '/watchlist/remove' : '/watchlist/add';
    const body = inList
        ? { movie_id: id }
        : {
            movie_id:   id,
            title:      currentModalMovie.title,
            poster:     currentModalMovie.poster,
            media_type: currentModalMovie.media_type || 'movie',
            rating:     currentModalMovie.rating || 0,
          };

    try {
        await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (inList) {
            watchlistIds.delete(id);
        } else {
            watchlistIds.add(id);
        }
        updateBookmarkIcon();
    } catch (_) { }
}

function updateBookmarkIcon() {
    const icon = $('bookmark-icon');
    if (!icon || !currentModalMovie) return;
    const filled = watchlistIds.has(currentModalMovie.movie_id);
    icon.setAttribute('fill', filled ? 'currentColor' : 'none');
}

async function showWatchlist() {
    // Hide all home sections and results page
    $('hero-section').style.display = 'none';
    $('trending-section').style.display = 'none';
    $('mood-section').style.display = 'none';
    $('genre-section').style.display = 'none';
    $('results-page').style.display = 'none';
    document.querySelectorAll('.home-spacer').forEach(s => s.style.display = 'none');
    setActiveNav('');

    const page = $('watchlist-page');
    page.style.display = 'block';
    $('watchlist-grid').innerHTML = '';
    $('watchlist-empty').style.display = 'none';
    $('watchlist-spinner').style.display = 'block';

    try {
        const res = await fetch('/watchlist');
        const items = await res.json();
        $('watchlist-spinner').style.display = 'none';

        watchlistIds = new Set(items.map(m => m.movie_id));

        if (!items.length) {
            $('watchlist-empty').style.display = 'block';
            $('watchlist-count').textContent = '';
            return;
        }

        $('watchlist-count').textContent = `${items.length} title${items.length !== 1 ? 's' : ''}`;
        const grid = $('watchlist-grid');
        items.forEach((r, i) => {
            const card = document.createElement('div');
            card.className = 'card';
            card.innerHTML = `
            <div class="poster-wrap">
              <img src="${r.poster}" alt="${r.title}" loading="lazy"
                   onerror="this.src='https://via.placeholder.com/300x450/1c1916/2e2a22?text=No+Poster'"/>
              <div class="card-overlay">
                <h4>${r.title}</h4>
                <div class="meta-row">
                  <span class="c-star">&#9733; ${r.rating}</span>
                </div>
              </div>
              <div class="card-hover-overlay">
                <div class="hover-cta">View details &rarr;</div>
              </div>
            </div>`;
            card.addEventListener('click', () => openModal(r));
            grid.appendChild(card);
            setTimeout(() => card.classList.add('show'), i * 55);
        });
    } catch (_) {
        $('watchlist-spinner').style.display = 'none';
        $('watchlist-empty').style.display = 'block';
    }
}
```

- [ ] **Step 2: Update the `openModal` intercept** — find this block (around line 710):

```js
const _origOpenModal = openModal;
openModal = async function (data) {
    currentModalMovie = data;
    highlightStars(userRatings[data.title] || 0);
    $('rate-msg').textContent = '';
    await _origOpenModal(data);
};
```

Replace with:

```js
const _origOpenModal = openModal;
openModal = async function (data) {
    currentModalMovie = data;
    highlightStars(userRatings[data.title] || 0);
    $('rate-msg').textContent = '';
    // Reset providers section
    $('modal-providers').style.display = 'none';
    $('providers-groups').innerHTML = '';
    updateBookmarkIcon();
    await _origOpenModal(data);
};
```

- [ ] **Step 3: Update the `/details` fetch in `openModal`** — inside the original `openModal` function (around line 108), change the fetch call to send the country:

```js
        const res = await fetch('/details', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                movie_id:   data.movie_id,
                title:      data.title,
                media_type: data.media_type,
                country:    (navigator.language.split('-')[1] || 'US').toUpperCase(),
            }),
        });
```

- [ ] **Step 4: Render providers after cast** — still inside `openModal`, after the cast rendering block (after the `$('modal-cast').style.display = 'block';` line), add:

```js
        // providers
        if (det.watch_providers) {
            const groups = $('providers-groups');
            const labels = { flatrate: 'Stream', rent: 'Rent', buy: 'Buy' };
            let hasAny = false;
            ['flatrate', 'rent', 'buy'].forEach(type => {
                const list = det.watch_providers[type] || [];
                if (!list.length) return;
                hasAny = true;
                const group = document.createElement('div');
                group.className = 'provider-group';
                group.innerHTML = `<span class="provider-type-label">${labels[type]}</span>`;
                list.forEach(p => {
                    const img = document.createElement('img');
                    img.src = p.logo_path || '';
                    img.alt = p.provider_name;
                    img.title = p.provider_name;
                    img.className = 'provider-logo';
                    img.onerror = () => img.style.display = 'none';
                    group.appendChild(img);
                });
                groups.appendChild(group);
            });
            if (hasAny) {
                $('modal-providers').style.display = 'block';
            } else {
                groups.innerHTML = '<span class="provider-unavailable">Not available for streaming in your region.</span>';
                $('modal-providers').style.display = 'block';
            }
        }
```

- [ ] **Step 5: Verify in browser** — open any movie modal. Check:
  - "Where to Watch" section appears with provider logos (or "Not available" message)
  - Bookmark icon appears in rating row
  - Clicking bookmark icon fills/unfills it
  - DevTools Network shows `country` in the `/details` POST body

- [ ] **Step 6: Commit**

```bash
git add static/scripts.js
git commit -m "feat: add watchlist JS and where-to-watch rendering"
```

---

## Task 6: CSS for new elements (`styles.css`)

**Files:**
- Modify: `static/styles.css`

- [ ] **Step 1: Add all new styles** at the bottom of `styles.css`:

```css
/* ── Where to Watch ── */
.modal-providers-row {
    padding: 14px 24px;
    border-top: 1px solid var(--rule);
}

.providers-label {
    font-size: 0.72rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--text3);
    margin-bottom: 10px;
}

.providers-groups {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    align-items: center;
}

.provider-group {
    display: flex;
    align-items: center;
    gap: 8px;
}

.provider-type-label {
    font-size: 0.65rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text3);
    flex-shrink: 0;
}

.provider-logo {
    width: 32px;
    height: 32px;
    border-radius: 6px;
    object-fit: cover;
}

.provider-unavailable {
    font-size: 0.82rem;
    color: var(--text3);
}

/* ── Bookmark button ── */
.btn-bookmark {
    margin-left: auto;
    background: none;
    border: 1px solid var(--rule);
    border-radius: 6px;
    padding: 6px 8px;
    cursor: pointer;
    color: var(--text2);
    display: flex;
    align-items: center;
    transition: border-color 0.15s, color 0.15s;
}

.btn-bookmark:hover {
    border-color: var(--text2);
    color: var(--text1);
}

/* ── Watchlist page ── */
#watchlist-page {
    padding-top: 32px;
}

#watchlist-header {
    padding: 0 0 8px 0;
}

#watchlist-spinner {
    text-align: center;
    padding: 60px 0;
    color: var(--text3);
}
```

- [ ] **Step 2: Verify styling** — open a movie modal and confirm:
  - "Where to Watch" section looks consistent with the "Cast" section above it
  - Bookmark button sits at the right edge of the rating row
  - Watchlist page (via dropdown) shows the grid with correct spacing

- [ ] **Step 3: Commit**

```bash
git add static/styles.css
git commit -m "feat: add CSS for providers, bookmark button, and watchlist page"
```

---

## Task 7: Smoke test end-to-end

- [ ] **Step 1: Start the server**

```bash
python app.py
```

- [ ] **Step 2: Test Where to Watch**
  1. Open any movie → click a result card → modal opens
  2. "Where to Watch" section appears with provider logos (or "Not available" message)
  3. Open DevTools → Network → find the `/details` POST → confirm `country` field matches your locale (e.g. `"IN"`)

- [ ] **Step 3: Test Watchlist add**
  1. In modal, click the bookmark button → icon fills solid
  2. Close modal, click user avatar → "My Watchlist" is in the dropdown
  3. Click "My Watchlist" → watchlist page shows the bookmarked movie

- [ ] **Step 4: Test Watchlist remove**
  1. Click the bookmarked movie card → modal opens → bookmark icon is filled
  2. Click bookmark button → icon becomes outline
  3. Go back to Watchlist page → movie is gone (or "empty" message appears)

- [ ] **Step 5: Test persistence**
  1. Refresh the page
  2. Open "My Watchlist" → previously bookmarked movie is still there (loaded from Firestore)

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "feat: watchlist and where-to-watch — complete implementation"
```
