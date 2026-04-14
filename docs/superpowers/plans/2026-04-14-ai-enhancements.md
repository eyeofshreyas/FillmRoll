# AI Enhancements (Priority 3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement two AI-powered features: (1) a personalized "Why You'll Love This" blurb in the movie modal driven by the user's rating history, and (2) a "Movie Night Matchmaker" page where the user describes their partner's taste and the AI picks a movie both will enjoy.

**Architecture:** Both features call a new `call_hf_chat_sync()` helper that reuses the existing HF Inference API setup (`HF_CHAT_URL`, `HF_MODEL`, `HF_TOKEN`) but fires a non-streaming POST and returns the raw text. Two new Flask routes (`/api/why-you-like` and `/api/matchmaker`) build prompts from `session['ratings']`, call the helper, and return JSON. The frontend wires up the blurb into the existing modal DOM and adds a new Matchmaker page reachable from the user dropdown.

**Tech Stack:** Python/Flask (app.py), Jinja2 (index.html), vanilla JS (scripts.js), CSS custom properties (styles.css), HF Inference API (meta-llama/Llama-3.1-8B-Instruct)

---

## File Map

| File | What changes |
|---|---|
| `app.py` | Add `call_hf_chat_sync()` (after line 227), `/api/why-you-like` route, `/api/matchmaker` route |
| `templates/index.html` | Add `#modal-why-blurb` div inside modal (after line 312); add `#matchmaker-page` section (after line 288); add dropdown nav item (after line 69) |
| `static/scripts.js` | Add `fetchWhyBlurb()` called from `openModal()`; add `showMatchmaker()` + `fetchMatch()` functions |
| `static/styles.css` | Add `.why-blurb` styles; add `.matchmaker-*` styles |

---

## Task 1: Add `call_hf_chat_sync()` helper to app.py

**Files:**
- Modify: `app.py` — add after `stream_hf_chat()` which ends around line 227

- [ ] **Step 1: Open app.py and find the end of `stream_hf_chat()`**

  Search for the line `except Exception as e:` inside `stream_hf_chat` (around line 225). Insert the new function immediately after the closing of `stream_hf_chat`.

- [ ] **Step 2: Insert `call_hf_chat_sync()` after `stream_hf_chat()`**

  Add this function at approximately line 228 (right after `stream_hf_chat` ends):

  ```python
  def call_hf_chat_sync(messages, max_tokens=150):
      """Non-streaming HF chat completion. Returns content string or None on error."""
      if not hf_available():
          return None
      try:
          r = requests.post(
              HF_CHAT_URL,
              headers={'Authorization': f'Bearer {HF_TOKEN}'},
              json={'model': HF_MODEL, 'messages': messages, 'stream': False, 'max_tokens': max_tokens},
              timeout=30,
          )
          if r.status_code == 200:
              return r.json()['choices'][0]['message']['content'].strip()
      except Exception:
          pass
      return None
  ```

- [ ] **Step 3: Verify the app still starts**

  Run: `.venv\Scripts\activate && python app.py`

  Expected: Flask dev server starts on port 5000 with no import errors. Kill with Ctrl+C.

- [ ] **Step 4: Commit**

  ```bash
  git add app.py
  git commit -m "feat: add call_hf_chat_sync helper for non-streaming HF completions"
  ```

---

## Task 2: Add `/api/why-you-like` route to app.py

**Files:**
- Modify: `app.py` — add after the `/api/ai-search` route (around line 538)

- [ ] **Step 1: Find the insertion point**

  Search for `@app.route('/api/ai-search'` in app.py. The route ends a few lines after. Insert the new route after the closing of that function.

- [ ] **Step 2: Add the route**

  ```python
  @app.route('/api/why-you-like', methods=['POST'])
  def why_you_like():
      """Return a 2-sentence AI blurb explaining why the user will love a movie."""
      data = request.get_json()
      title = (data.get('title') or '').strip()
      overview = (data.get('overview') or '')[:200]

      ratings = session.get('ratings', {})
      if not ratings or not title:
          return jsonify({'blurb': None})

      top_rated = sorted(ratings.items(), key=lambda x: x[1], reverse=True)[:5]
      history_str = ', '.join(f"{t} ({r}\u2605)" for t, r in top_rated)

      messages = [
          {
              'role': 'system',
              'content': (
                  "You are FilmRoll AI. Given a user's favorite movies and a new movie, "
                  "write exactly 2 sentences explaining why they will love it. "
                  "Be specific about shared themes, tone, or style. "
                  "Start the response with \"Since you loved\""
              ),
          },
          {
              'role': 'user',
              'content': (
                  f"User's favorites: {history_str}\n"
                  f"New movie: {title}\n"
                  f"Overview: {overview}\n"
                  "Explain in 2 sentences why they'll love it."
              ),
          },
      ]

      blurb = call_hf_chat_sync(messages, max_tokens=120)
      return jsonify({'blurb': blurb})
  ```

- [ ] **Step 3: Smoke-test the route manually**

  Start the server, log in, rate at least 2 movies, then run in a terminal:

  ```bash
  curl -s -X POST http://127.0.0.1:5000/api/why-you-like \
    -H "Content-Type: application/json" \
    -H "Cookie: <paste session cookie from browser dev tools>" \
    -d '{"title":"Inception","overview":"A thief who steals corporate secrets through dreams."}'
  ```

  Expected: `{"blurb": "Since you loved ..."}` (a 2-sentence string). If AI offline: `{"blurb": null}`.

- [ ] **Step 4: Commit**

  ```bash
  git add app.py
  git commit -m "feat: add /api/why-you-like route for personalized movie blurbs"
  ```

---

## Task 3: Add `/api/matchmaker` route to app.py

**Files:**
- Modify: `app.py` — add after `/api/why-you-like` route

- [ ] **Step 1: Add the route immediately after `why_you_like()`**

  ```python
  @app.route('/api/matchmaker', methods=['POST'])
  def matchmaker():
      """Given partner taste description, return a movie both users will enjoy."""
      data = request.get_json()
      partner_desc = (data.get('partner_desc') or '').strip()
      if not partner_desc:
          return jsonify({'error': 'partner_desc is required'}), 400

      ratings = session.get('ratings', {})
      top_rated = sorted(ratings.items(), key=lambda x: x[1], reverse=True)[:5]
      user_str = (
          ', '.join(f"{t} ({r}\u2605)" for t, r in top_rated)
          if top_rated else 'No rated movies yet'
      )

      messages = [
          {
              'role': 'system',
              'content': (
                  "You are a movie matchmaker. Given taste profiles for two people, "
                  "suggest ONE movie both would enjoy. "
                  'Respond ONLY with valid JSON, no markdown: '
                  '{"title": "exact movie title", "reason": "one sentence why both will enjoy it"}'
              ),
          },
          {
              'role': 'user',
              'content': (
                  f"Person 1 favorites: {user_str}\n"
                  f"Person 2 likes: {partner_desc}\n"
                  "Suggest ONE movie both will enjoy."
              ),
          },
      ]

      raw = call_hf_chat_sync(messages, max_tokens=120)
      if not raw:
          return jsonify({'error': 'AI unavailable'}), 503

      # Extract JSON from model response (may be wrapped in extra text)
      import re as _re
      m = _re.search(r'\{[^{}]+\}', raw, _re.DOTALL)
      try:
          result = json.loads(m.group() if m else raw)
          suggested_title = result.get('title', '').strip()
          reason = result.get('reason', '').strip()
      except Exception:
          return jsonify({'error': 'Could not parse AI response', 'raw': raw}), 500

      if not suggested_title:
          return jsonify({'error': 'AI returned empty title', 'raw': raw}), 500

      # Look up movie in catalog (exact then partial)
      match = movies[movies['title'].str.lower() == suggested_title.lower()]
      if match.empty:
          match = movies[
              movies['title'].str.lower().str.contains(
                  suggested_title.lower()[:20], na=False, regex=False
              )
          ]

      if match.empty:
          return jsonify({'title': suggested_title, 'reason': reason, 'in_catalog': False})

      movie = build_item_dict(movies.iloc[match.index[0]])
      return jsonify({'movie': movie, 'reason': reason, 'in_catalog': True})
  ```

- [ ] **Step 2: Smoke-test the route**

  Start the server, log in, rate some movies. Run:

  ```bash
  curl -s -X POST http://127.0.0.1:5000/api/matchmaker \
    -H "Content-Type: application/json" \
    -H "Cookie: <session cookie>" \
    -d '{"partner_desc":"loves romantic comedies and feel-good films"}'
  ```

  Expected: `{"movie": {...}, "reason": "...", "in_catalog": true}` or `{"title":"...", "reason":"...", "in_catalog": false}`.

- [ ] **Step 3: Commit**

  ```bash
  git add app.py
  git commit -m "feat: add /api/matchmaker route for Movie Night Matchmaker"
  ```

---

## Task 4: Add "Why You'll Love This" modal blurb (HTML + CSS)

**Files:**
- Modify: `templates/index.html` — insert after `#modal-overview` (line 312)
- Modify: `static/styles.css` — add `.why-blurb` styles

- [ ] **Step 1: Open index.html and find `#modal-overview`**

  Search for `id="modal-overview"`. It is at approximately line 312. Insert the blurb div on the next line.

- [ ] **Step 2: Add the blurb HTML after `#modal-overview`**

  Find this line in index.html (around line 312):
  ```html
        <p id="modal-overview" class="modal-overview"></p>
  ```

  Insert immediately after it:
  ```html
        <div id="modal-why-blurb" class="why-blurb hidden" aria-live="polite">
          <span class="why-icon" aria-hidden="true">✦</span>
          <p id="why-blurb-text"></p>
        </div>
  ```

- [ ] **Step 3: Add CSS for `.why-blurb` in styles.css**

  Append at the end of `static/styles.css`:

  ```css
  /* ── Why You'll Love This blurb ── */
  .why-blurb {
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
    background: rgba(var(--accent-rgb, 255, 180, 0), 0.08);
    border-left: 3px solid var(--accent, #ffb400);
    border-radius: 0 8px 8px 0;
    padding: 0.65rem 0.9rem;
    margin: 0.75rem 0 0.25rem;
    font-size: 0.88rem;
    line-height: 1.55;
    color: var(--text-secondary, #ccc);
    transition: opacity 0.3s;
  }
  .why-blurb.hidden { display: none; }
  .why-blurb .why-icon {
    color: var(--accent, #ffb400);
    font-size: 0.75rem;
    flex-shrink: 0;
    margin-top: 0.2rem;
  }
  .why-blurb p { margin: 0; }
  .why-blurb.loading p { opacity: 0.5; font-style: italic; }
  ```

- [ ] **Step 4: Verify modal renders**

  Open the app in a browser, search for a movie, open the modal. The blurb area is invisible (hidden class). No visual regressions.

- [ ] **Step 5: Commit**

  ```bash
  git add templates/index.html static/styles.css
  git commit -m "feat: add why-you-like blurb section to movie modal"
  ```

---

## Task 5: Add Matchmaker page (HTML + CSS + nav entry)

**Files:**
- Modify: `templates/index.html` — add `#matchmaker-page` after `#watchlist-page`; add dropdown nav item
- Modify: `static/styles.css` — add `.matchmaker-*` styles

- [ ] **Step 1: Add Matchmaker dropdown item in the user dropdown**

  Find this block in index.html (around line 68–72):
  ```html
          <button class="dropdown-item" onclick="showWatchlist(); toggleUserMenu()">
  ```

  Insert a new button immediately **after** the watchlist button closing tag (after line 70 approximately):
  ```html
          <button class="dropdown-item" onclick="showMatchmaker(); toggleUserMenu()">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
            </svg>
            Movie Night Matchmaker
          </button>
  ```

- [ ] **Step 2: Add `#matchmaker-page` section after `#watchlist-page`**

  Find the closing `</main>` of `#watchlist-page` (around line 289 — the line after `<div class="grid" id="watchlist-grid">`). Insert after it:

  ```html
  <main class="page" id="matchmaker-page" style="display:none" aria-label="Movie Night Matchmaker">
    <div class="matchmaker-container">
      <h2 class="matchmaker-title">Movie Night Matchmaker</h2>
      <p class="matchmaker-subtitle">Describe what your partner enjoys and we'll find a movie you'll both love.</p>

      <div class="matchmaker-grid">
        <div class="taste-card">
          <h3 class="taste-label">Your Taste</h3>
          <div id="my-taste-chips" class="taste-chips"></div>
          <p id="my-taste-empty" class="taste-empty hidden">Rate some movies to set your taste profile.</p>
        </div>
        <div class="taste-plus" aria-hidden="true">+</div>
        <div class="taste-card">
          <h3 class="taste-label">Partner's Taste</h3>
          <textarea
            id="partner-input"
            class="partner-textarea"
            rows="4"
            maxlength="300"
            placeholder="e.g. loves action thrillers, Christopher Nolan films, and anything with a twist ending…"
          ></textarea>
        </div>
      </div>

      <button id="matchmaker-btn" class="matchmaker-btn" onclick="fetchMatch()">Find Our Movie</button>

      <div id="matchmaker-spinner" class="matchmaker-spinner hidden">
        <div class="spin"></div>
        <p>Asking the AI matchmaker…</p>
      </div>

      <div id="matchmaker-result" class="matchmaker-result hidden">
        <div id="matchmaker-card" class="matchmaker-card"></div>
        <p id="matchmaker-reason" class="matchmaker-reason"></p>
      </div>

      <p id="matchmaker-error" class="matchmaker-error hidden"></p>
    </div>
  </main>
  ```

- [ ] **Step 3: Add Matchmaker CSS to styles.css**

  Append at the end of `static/styles.css`:

  ```css
  /* ── Movie Night Matchmaker ── */
  .matchmaker-container {
    max-width: 760px;
    margin: 2rem auto;
    padding: 0 1rem;
    text-align: center;
  }
  .matchmaker-title {
    font-size: 1.6rem;
    font-weight: 700;
    margin-bottom: 0.4rem;
  }
  .matchmaker-subtitle {
    color: var(--text-secondary, #aaa);
    margin-bottom: 2rem;
    font-size: 0.95rem;
  }
  .matchmaker-grid {
    display: flex;
    align-items: flex-start;
    gap: 1rem;
    margin-bottom: 1.5rem;
  }
  .taste-card {
    flex: 1;
    background: var(--card-bg, #1e1e1e);
    border-radius: 12px;
    padding: 1.25rem;
    text-align: left;
  }
  .taste-label {
    font-size: 0.85rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--accent, #ffb400);
    margin-bottom: 0.75rem;
  }
  .taste-chips { display: flex; flex-wrap: wrap; gap: 0.4rem; }
  .taste-chip {
    background: rgba(255,255,255,0.08);
    border-radius: 20px;
    padding: 0.25rem 0.7rem;
    font-size: 0.8rem;
    white-space: nowrap;
  }
  .taste-chip .chip-star { color: var(--accent, #ffb400); margin-left: 0.2rem; }
  .taste-empty { font-size: 0.85rem; color: var(--text-secondary, #888); }
  .taste-plus {
    font-size: 2rem;
    color: var(--text-secondary, #555);
    padding-top: 2.5rem;
    flex-shrink: 0;
  }
  .partner-textarea {
    width: 100%;
    background: transparent;
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 8px;
    color: inherit;
    font: inherit;
    font-size: 0.9rem;
    padding: 0.65rem 0.75rem;
    resize: vertical;
    transition: border-color 0.2s;
    box-sizing: border-box;
  }
  .partner-textarea:focus {
    outline: none;
    border-color: var(--accent, #ffb400);
  }
  .matchmaker-btn {
    background: var(--accent, #ffb400);
    color: #000;
    border: none;
    border-radius: 8px;
    padding: 0.7rem 2rem;
    font-size: 0.95rem;
    font-weight: 700;
    cursor: pointer;
    transition: opacity 0.2s;
  }
  .matchmaker-btn:disabled { opacity: 0.5; cursor: not-allowed; }
  .matchmaker-spinner {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.75rem;
    margin: 1.5rem 0;
    color: var(--text-secondary, #aaa);
    font-size: 0.9rem;
  }
  .matchmaker-spinner.hidden { display: none; }
  .matchmaker-result { margin-top: 2rem; }
  .matchmaker-result.hidden { display: none; }
  .matchmaker-card {
    display: flex;
    align-items: center;
    gap: 1.25rem;
    background: var(--card-bg, #1e1e1e);
    border-radius: 12px;
    padding: 1rem;
    text-align: left;
    margin-bottom: 1rem;
    cursor: pointer;
    transition: transform 0.2s;
  }
  .matchmaker-card:hover { transform: translateY(-2px); }
  .matchmaker-card img {
    width: 70px;
    border-radius: 6px;
    flex-shrink: 0;
    object-fit: cover;
  }
  .matchmaker-card-info h3 { margin: 0 0 0.3rem; font-size: 1.1rem; }
  .matchmaker-card-info p { margin: 0; font-size: 0.85rem; color: var(--text-secondary, #aaa); }
  .matchmaker-reason {
    font-size: 0.9rem;
    color: var(--text-secondary, #bbb);
    font-style: italic;
    text-align: center;
  }
  .matchmaker-error {
    color: #e06c75;
    font-size: 0.9rem;
    margin-top: 1rem;
  }
  .matchmaker-error.hidden { display: none; }
  @media (max-width: 600px) {
    .matchmaker-grid { flex-direction: column; }
    .taste-plus { padding-top: 0; align-self: center; }
  }
  ```

- [ ] **Step 4: Visual check**

  Open app, click user avatar → dropdown should now show "Movie Night Matchmaker" item. Clicking it should navigate to the matchmaker page (which is empty for now — JS comes next).

- [ ] **Step 5: Commit**

  ```bash
  git add templates/index.html static/styles.css
  git commit -m "feat: add Movie Night Matchmaker page layout and styles"
  ```

---

## Task 6: Wire up "Why You'll Love This" blurb in scripts.js

**Files:**
- Modify: `static/scripts.js` — add `fetchWhyBlurb()` function; call it from `openModal()`

- [ ] **Step 1: Add `fetchWhyBlurb()` function**

  Find the section in scripts.js where `openModal` is defined (around line 85). Add this new standalone function **before** `openModal`:

  ```javascript
  async function fetchWhyBlurb(movie) {
    const blurbEl = document.getElementById('modal-why-blurb');
    const textEl  = document.getElementById('why-blurb-text');
    if (!blurbEl || !textEl) return;

    // Need at least 2 ratings and AI must be online
    if (Object.keys(userRatings).length < 2) {
      blurbEl.classList.add('hidden');
      return;
    }

    // Show loading state
    blurbEl.classList.remove('hidden');
    blurbEl.classList.add('loading');
    textEl.textContent = 'Personalizing…';

    try {
      const res = await fetch('/api/why-you-like', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: movie.title, overview: movie.overview || '' }),
      });
      const data = await res.json();
      if (data.blurb) {
        textEl.textContent = data.blurb;
        blurbEl.classList.remove('loading');
      } else {
        blurbEl.classList.add('hidden');
      }
    } catch (_) {
      blurbEl.classList.add('hidden');
    }
  }
  ```

- [ ] **Step 2: Call `fetchWhyBlurb()` inside `openModal()`**

  Inside the `openModal(data)` function body, find the line where `currentModalMovie` is assigned (around line 759 — search for `currentModalMovie =`). Add the call immediately after it:

  ```javascript
  // existing line (already there):
  currentModalMovie = data;
  // add this line right after:
  fetchWhyBlurb(data);
  ```

  Also add a reset at the top of `openModal()`, right after `const blurbEl = ...` or wherever you reset other modal fields. Search for the block that clears modal content (where `modal-title`, `modal-overview` etc. are reset). Add:

  ```javascript
  document.getElementById('modal-why-blurb').classList.add('hidden');
  ```

- [ ] **Step 3: Verify in browser**

  1. Start the server, log in, rate at least 2 movies (use the star UI in any modal).
  2. Open a different movie's modal.
  3. Wait ~3 seconds — a blurb should appear below the overview with a gold left border and a "✦" icon.
  4. For a user with 0 ratings: no blurb visible.
  5. For AI offline (no `HF_TOKEN`): no blurb visible.

- [ ] **Step 4: Commit**

  ```bash
  git add static/scripts.js
  git commit -m "feat: show personalized why-you-like blurb in movie modal"
  ```

---

## Task 7: Add Matchmaker JS logic to scripts.js

**Files:**
- Modify: `static/scripts.js` — add `showMatchmaker()` and `fetchMatch()` functions

- [ ] **Step 1: Add `showMatchmaker()` function**

  Append the following to the end of `static/scripts.js` (before the closing IIFE `})()`  if the file uses one, otherwise at the bottom):

  ```javascript
  // ── Movie Night Matchmaker ────────────────────────────────────────────────
  function showMatchmaker() {
    // Hide all other pages
    ['#results-page', '#watchlist-page', '#browse-page', '#trending-page'].forEach(sel => {
      const el = document.querySelector(sel);
      if (el) el.style.display = 'none';
    });
    document.getElementById('home-content') && (document.getElementById('home-content').style.display = 'none');

    const page = document.getElementById('matchmaker-page');
    if (!page) return;
    page.style.display = '';

    // Deactivate nav links
    document.querySelectorAll('.nav-link').forEach(b => b.classList.remove('active'));

    // Populate "Your Taste" chips from userRatings
    const chipsEl = document.getElementById('my-taste-chips');
    const emptyEl = document.getElementById('my-taste-empty');
    chipsEl.innerHTML = '';
    const sorted = Object.entries(userRatings).sort((a, b) => b[1] - a[1]).slice(0, 6);
    if (sorted.length === 0) {
      emptyEl && emptyEl.classList.remove('hidden');
    } else {
      emptyEl && emptyEl.classList.add('hidden');
      sorted.forEach(([title, rating]) => {
        const chip = document.createElement('span');
        chip.className = 'taste-chip';
        chip.innerHTML = `${title}<span class="chip-star">${'★'.repeat(rating)}</span>`;
        chipsEl.appendChild(chip);
      });
    }

    // Reset result/error state
    document.getElementById('matchmaker-result').classList.add('hidden');
    document.getElementById('matchmaker-error').classList.add('hidden');
    document.getElementById('matchmaker-spinner').classList.add('hidden');
    document.getElementById('partner-input').value = '';
  }

  async function fetchMatch() {
    const partnerDesc = (document.getElementById('partner-input').value || '').trim();
    if (!partnerDesc) {
      const errEl = document.getElementById('matchmaker-error');
      errEl.textContent = 'Please describe your partner\'s taste first.';
      errEl.classList.remove('hidden');
      return;
    }

    const btn     = document.getElementById('matchmaker-btn');
    const spinner = document.getElementById('matchmaker-spinner');
    const result  = document.getElementById('matchmaker-result');
    const errEl   = document.getElementById('matchmaker-error');

    btn.disabled = true;
    spinner.classList.remove('hidden');
    result.classList.add('hidden');
    errEl.classList.add('hidden');

    try {
      const res  = await fetch('/api/matchmaker', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ partner_desc: partnerDesc }),
      });
      const data = await res.json();

      if (!res.ok) {
        errEl.textContent = data.error || 'Something went wrong. Try again.';
        errEl.classList.remove('hidden');
        return;
      }

      const cardEl   = document.getElementById('matchmaker-card');
      const reasonEl = document.getElementById('matchmaker-reason');

      if (data.in_catalog && data.movie) {
        const m = data.movie;
        cardEl.innerHTML = `
          <img src="${m.poster || '/static/placeholder.png'}" alt="${m.title}" loading="lazy">
          <div class="matchmaker-card-info">
            <h3>${m.title}</h3>
            <p>⭐ ${m.rating ? m.rating.toFixed(1) : 'N/A'}</p>
          </div>`;
        cardEl.onclick = () => openModal(m);
      } else {
        // Not in catalog — show title only
        cardEl.innerHTML = `
          <div class="matchmaker-card-info">
            <h3>${data.title}</h3>
            <p style="color:#e06c75">Not in our catalog — search it online</p>
          </div>`;
        cardEl.onclick = null;
      }

      reasonEl.textContent = data.reason ? `"${data.reason}"` : '';
      result.classList.remove('hidden');
    } catch (_) {
      errEl.textContent = 'Network error. Check your connection.';
      errEl.classList.remove('hidden');
    } finally {
      btn.disabled = false;
      spinner.classList.add('hidden');
    }
  }
  ```

- [ ] **Step 2: Verify matchmaker end-to-end in browser**

  1. Start the app, log in, rate at least 2 movies.
  2. Click user avatar → "Movie Night Matchmaker".
  3. Matchmaker page appears, your top-rated movies show as gold chips.
  4. Type in partner textarea: `"loves romantic comedies and feel-good films"`.
  5. Click "Find Our Movie".
  6. Spinner appears, then a movie card with poster and reason text appears.
  7. Clicking the card opens the movie modal.
  8. Test with an empty textarea — should show inline error message.

- [ ] **Step 3: Commit**

  ```bash
  git add static/scripts.js
  git commit -m "feat: add Movie Night Matchmaker UI logic"
  ```

---

## Verification Checklist

Run through these before marking the feature complete:

- [ ] User with **0 ratings** → modal opens, no blurb visible
- [ ] User with **2+ ratings** → modal opens, blurb appears within 3-4s with "Since you loved…"
- [ ] `HF_TOKEN` not set → `/api/why-you-like` returns `{blurb: null}`, blurb hidden
- [ ] Matchmaker page → your chips populate from `userRatings`
- [ ] Matchmaker → empty textarea submit → inline error shown, no API call
- [ ] Matchmaker → valid input → spinner, then result card with poster and reason
- [ ] Matchmaker result card → click → opens movie modal
- [ ] Movie not in catalog → shows title + "Not in our catalog" message
- [ ] Mobile layout → matchmaker grid stacks vertically (test at 375px width)
- [ ] No regressions on existing features: search, For You, watchlist, AI chat

---

## Execution Options

**Plan saved to** `docs/superpowers/plans/2026-04-14-ai-enhancements.md`

**1. Subagent-Driven (recommended)** — fresh subagent per task, review between tasks

**2. Inline Execution** — execute tasks in this session using executing-plans skill
