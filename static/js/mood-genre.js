/* ── mood-genre.js ── mood & genre recommendation pages ── */
import { $ } from './utils.js';
import { showResultsPage, showHomeSections } from './nav.js';

const MOOD_LABELS = {
    happy: 'Happy', excited: 'Excited', romantic: 'Romantic',
    sad: 'Emotional', scared: 'Scary', adventurous: 'Adventurous',
    curious: 'Curious', chill: 'Chill',
};

/**
 * Fetch mood-based recommendations from the server.
 * @param {string}   mood        - mood key string
 * @param {function} renderFn    - renderFeatured(sel, results, openModalFn)
 * @param {function} renderGridFn - renderGrid(results, openModalFn)
 * @param {function} openModalFn - modal opener
 */
export async function fetchMoodRecs(mood, renderFn, renderGridFn, openModalFn) {
    showResultsPage();

    try {
        const res  = await fetch('/mood', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mood, n: 60 }),
        });
        const data = await res.json();
        $('spinner').classList.remove('active');

        if (!data.results || !data.results.length) {
            showHomeSections();
            return;
        }

        const label  = MOOD_LABELS[mood] || mood;
        const pseudo = {
            title:    `Mood: ${label}`,
            poster:   null,
            overview: `${data.results.length} top-rated picks ranked by quality & vote credibility — for when you're feeling ${label.toLowerCase()}.`,
            rating:   null,
        };
        renderFn(pseudo, data.results, openModalFn);
        renderGridFn(data.results, openModalFn);
    } catch (_) {
        $('spinner').classList.remove('active');
        showHomeSections();
    }
}

/**
 * Fetch genre-based recommendations from the server.
 * @param {string}   genre       - genre key string
 * @param {string}   label       - display label
 * @param {function} renderFn    - renderFeatured
 * @param {function} renderGridFn - renderGrid
 * @param {function} openModalFn - modal opener
 */
export async function fetchGenreRecs(genre, label, renderFn, renderGridFn, openModalFn) {
    showResultsPage();

    try {
        const res  = await fetch('/genre', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ genre, n: 60 }),
        });
        const data = await res.json();
        $('spinner').classList.remove('active');

        if (!data.results || !data.results.length) {
            showHomeSections();
            return;
        }

        const pseudo = {
            title:    label,
            poster:   null,
            overview: `${data.results.length} top ${label} films — ranked by rating credibility (vote average × vote confidence).`,
            rating:   null,
        };
        renderFn(pseudo, data.results, openModalFn);
        renderGridFn(data.results, openModalFn);
    } catch (_) {
        $('spinner').classList.remove('active');
        showHomeSections();
    }
}
