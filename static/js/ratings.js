/* ── ratings.js ── star ratings & "For You" badge ── */
import { $ } from './utils.js';
import { showResultsPage, showHomeSections, setActiveNav } from './nav.js';

// ── Shared mutable state (exported so other modules can read) ─
export const ratingState = {
    userRatings:      {},     // { [movieTitle]: starValue }
    currentModalMovie: null,  // the movie currently open in the modal
};

// ── Star UI ───────────────────────────────────────────────────

export function highlightStars(n) {
    document.querySelectorAll('#modal-stars .star').forEach(s => {
        s.classList.toggle('active', parseInt(s.dataset.v) <= n);
    });
}

// ── For-You badge ─────────────────────────────────────────────

export function updateForYouBadge() {
    const count = Object.keys(ratingState.userRatings).length;
    const val   = count > 0 ? count : '';
    [$('foryou-badge'), $('mob-foryou-badge')].forEach(b => { if (b) b.textContent = val; });
}

// ── Load ratings from server ──────────────────────────────────

export async function loadUserRatings() {
    try {
        const res = await fetch('/my-ratings');
        ratingState.userRatings = await res.json();
        updateForYouBadge();
    } catch (_) { }
}

// ── Wire up star interaction ──────────────────────────────────

/**
 * Attach hover/click handlers to the modal star elements.
 * @param {function} onRated - callback() after a rating is saved (e.g. show review input)
 */
export function initStarRating(onRated) {
    document.querySelectorAll('#modal-stars .star').forEach(star => {
        star.addEventListener('mouseenter', () => highlightStars(parseInt(star.dataset.v)));
        star.addEventListener('mouseleave', () => {
            const current = ratingState.currentModalMovie
                ? (ratingState.userRatings[ratingState.currentModalMovie.title] || 0)
                : 0;
            highlightStars(current);
        });
        star.addEventListener('click', async () => {
            if (!ratingState.currentModalMovie) return;
            const v = parseInt(star.dataset.v);
            ratingState.userRatings[ratingState.currentModalMovie.title] = v;
            highlightStars(v);

            if (onRated) onRated(v);

            try {
                await fetch('/rate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title: ratingState.currentModalMovie.title, rating: v }),
                });
                $('rate-msg').textContent = 'Saved!';
                setTimeout(() => { if ($('rate-msg')) $('rate-msg').textContent = ''; }, 2000);
                updateForYouBadge();
            } catch (_) { }
        });
    });
}

// ── Collaborative filtering ("For You") ──────────────────────

/**
 * Fetch CF recommendations and render them.
 * @param {function} renderFn     - renderFeatured(sel, results, openModalFn)
 * @param {function} renderGridFn - renderGrid(results, openModalFn)
 * @param {function} openModalFn  - modal opener
 */
export async function fetchCFRecs(renderFn, renderGridFn, openModalFn) {
    showResultsPage();
    const n = parseInt($('num-recs').value);

    try {
        const res  = await fetch('/cf-recommend', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ n }),
        });
        const data = await res.json();
        $('spinner').classList.remove('active');

        if (!data.results || !data.results.length) {
            showHomeSections();
            setActiveNav('nav-home');
            alert(data.message || 'Rate some movies in the modal to get personalised picks.');
            return;
        }

        const pseudo = {
            title:    'For You',
            poster:   null,
            overview: `Based on ${data.rated_count} film${data.rated_count !== 1 ? 's' : ''} you rated — titles we think you'll love.`,
            rating:   null,
        };
        renderFn(pseudo, data.results, openModalFn);
        renderGridFn(data.results, openModalFn);
    } catch (_) {
        $('spinner').classList.remove('active');
        showHomeSections();
    }
}
