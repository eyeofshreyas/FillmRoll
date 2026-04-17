/* ── watchlist.js ── watchlist CRUD & page ── */
import { $ } from './utils.js';
import { setActiveNav } from './nav.js';

// ── Module state ──────────────────────────────────────────────
export const watchlistState = {
    watchlistIds: new Set(), // Set<movie_id> for O(1) lookup
};

let _animTimers = []; // stagger animation timers

// ── Load watchlist IDs ────────────────────────────────────────

export async function loadWatchlist() {
    try {
        const res   = await fetch('/watchlist');
        const items = await res.json();
        watchlistState.watchlistIds = new Set(items.map(m => m.movie_id));
    } catch (_) { }
}

// ── Bookmark icon ─────────────────────────────────────────────

/**
 * Sync the bookmark icon state with the watchlist.
 * @param {object|null} currentModalMovie
 */
export function updateBookmarkIcon(currentModalMovie) {
    const icon = $('bookmark-icon');
    const btn  = $('modal-bookmark');
    if (!icon || !btn || !currentModalMovie) return;
    const filled = watchlistState.watchlistIds.has(currentModalMovie.movie_id);
    icon.setAttribute('fill', filled ? 'currentColor' : 'none');
    btn.setAttribute('aria-pressed', String(filled));
    btn.setAttribute('aria-label', filled ? 'Remove from watchlist' : 'Add to watchlist');
}

// ── Toggle ────────────────────────────────────────────────────

/**
 * Add or remove the current modal movie from the watchlist.
 * @param {object|null} currentModalMovie
 */
export async function toggleWatchlist(currentModalMovie) {
    if (!currentModalMovie) return;
    const id = currentModalMovie.movie_id;
    if (!id) return;

    const inList = watchlistState.watchlistIds.has(id);
    const url    = inList ? '/watchlist/remove' : '/watchlist/add';
    const body   = inList
        ? { movie_id: id }
        : {
            movie_id:   id,
            title:      currentModalMovie.title,
            poster:     currentModalMovie.poster,
            media_type: currentModalMovie.media_type || 'movie',
            rating:     currentModalMovie.rating || 0,
          };

    try {
        const resp = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (!resp.ok) return;
        if (inList) {
            watchlistState.watchlistIds.delete(id);
        } else {
            watchlistState.watchlistIds.add(id);
        }
        updateBookmarkIcon(currentModalMovie);
    } catch (_) { }
}

// ── Watchlist page ────────────────────────────────────────────

/**
 * Show the watchlist page and populate it with the user's saved movies.
 * @param {function} openModalFn - callback to open the detail modal
 */
export async function showWatchlist(openModalFn) {
    // Hide all other sections
    $('hero-section').style.display = 'none';
    $('trending-section').style.display = 'none';
    $('mood-section').style.display = 'none';
    $('genre-section').style.display = 'none';
    $('results-page').style.display = 'none';
    document.querySelectorAll('.home-spacer').forEach(s => s.style.display = 'none');
    const mmPage = $('matchmaker-page');
    if (mmPage) mmPage.style.display = 'none';
    setActiveNav('');

    const page = $('watchlist-page');
    page.style.display = 'block';
    $('watchlist-grid').innerHTML = '';
    $('watchlist-empty').style.display = 'none';
    $('watchlist-spinner').style.display = 'block';

    try {
        const res   = await fetch('/watchlist');
        const items = await res.json();
        $('watchlist-spinner').style.display = 'none';

        watchlistState.watchlistIds = new Set(items.map(m => m.movie_id));

        if (!items.length) {
            $('watchlist-empty').style.display = 'block';
            $('watchlist-count').textContent = '';
            return;
        }

        $('watchlist-count').textContent = `${items.length} title${items.length !== 1 ? 's' : ''}`;
        const grid = $('watchlist-grid');

        _animTimers.forEach(clearTimeout);
        _animTimers = [];

        items.forEach((r, i) => {
            const card = document.createElement('div');
            card.className = 'card';

            const wrap = document.createElement('div');
            wrap.className = 'poster-wrap';

            const img = document.createElement('img');
            img.loading = 'lazy';
            img.src     = r.poster || '';
            img.alt     = r.title  || '';
            img.onerror = () => { img.src = 'https://placehold.co/300x450/1c1916/2e2a22?text=No+Poster'; };

            const overlay = document.createElement('div');
            overlay.className = 'card-overlay';
            const h4 = document.createElement('h4');
            h4.textContent = r.title || '';
            const metaRow = document.createElement('div');
            metaRow.className = 'meta-row';
            const star = document.createElement('span');
            star.className   = 'c-star';
            star.textContent = `★ ${r.rating}`;
            metaRow.appendChild(star);
            overlay.appendChild(h4);
            overlay.appendChild(metaRow);

            const hoverOverlay = document.createElement('div');
            hoverOverlay.className = 'card-hover-overlay';
            const cta = document.createElement('div');
            cta.className   = 'hover-cta';
            cta.textContent = 'View details →';
            hoverOverlay.appendChild(cta);

            wrap.appendChild(img);
            wrap.appendChild(overlay);
            wrap.appendChild(hoverOverlay);
            card.appendChild(wrap);

            card.addEventListener('click', () => openModalFn(r));
            grid.appendChild(card);
            _animTimers.push(setTimeout(() => card.classList.add('show'), i * 55));
        });
    } catch (_) {
        $('watchlist-spinner').style.display = 'none';
        $('watchlist-empty').style.display = 'block';
    }
}
