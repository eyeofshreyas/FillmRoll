/**
 * main.js — orchestrates all modules.
 *
 * Import order matters: utils → nav → modal → recommendations →
 * ai-chat → mood-genre → ratings → watchlist → matchmaker → reviews
 *
 * Nothing here is global by accident. Functions that must be reachable
 * from HTML onclick="" attributes are deliberately attached to window.
 */

import { $, on } from './utils.js';
import {
    setActiveNav, showHomeSections, showResultsPage,
    navHome, navTrending, navNewReleases, navBrowse, focusSearch, toggleUserMenu,
} from './nav.js';
import { loadTrending }      from './trending.js';
import { loadNewReleases }   from './new-releases.js';
import { closeModal, handleBackdropClick, openModal, fetchWhyBlurb, watchNow, switchSource } from './modal.js';
import { renderFeatured, renderGrid, fetchRecs, heroSearch } from './recommendations.js';
import {
    aiState, checkOllamaStatus, toggleAiPanel,
    sendAiMessage, sendAiPrompt, updateAiContext,
    showAiToast, hideAiToast, doAiSearch,
} from './ai-chat.js';
import { fetchMoodRecs, fetchGenreRecs } from './mood-genre.js';
import {
    ratingState, highlightStars, updateForYouBadge,
    loadUserRatings, initStarRating, fetchCFRecs,
} from './ratings.js';
import {
    watchlistState, loadWatchlist, updateBookmarkIcon,
    toggleWatchlist, showWatchlist,
} from './watchlist.js';
import { showMatchmaker, fetchMatch } from './matchmaker.js';
import {
    initReviewCharCount, submitReview,
    loadMovieReviews, deleteMyReview,
} from './reviews.js';

// ── Intersection observer (fade-in) ──────────────────────────
const fadeObs = new IntersectionObserver(entries => {
    entries.forEach(e => {
        if (e.isIntersecting) {
            e.target.classList.add('visible');
            fadeObs.unobserve(e.target);
        }
    });
}, { threshold: 0.12 });
document.querySelectorAll('.fade-up').forEach(el => fadeObs.observe(el));

// ── Bound openModal (adds rating / review hooks before delegating) ─
async function handleOpenModal(data) {
    ratingState.currentModalMovie = data;
    $('modal-why-blurb').classList.add('hidden');
    fetchWhyBlurb(data, ratingState.userRatings, ratingState).catch(err =>
        console.warn('[why-blurb]', err)
    );
    highlightStars(ratingState.userRatings[data.title] || 0);
    $('rate-msg').textContent = '';

    // Reset providers
    $('modal-providers').style.display = 'none';
    $('providers-groups').innerHTML = '';

    updateBookmarkIcon(data);

    // Reset review input section
    const revSec  = $('review-input-section');
    if (revSec)   revSec.style.maxHeight = '0px';
    const revText = $('review-text');
    if (revText)  revText.value = '';
    const revChar = $('review-char-count');
    if (revChar)  revChar.textContent = '0/500';

    loadMovieReviews(data.title);

    await openModal(data);
}

// ── Bound fetchRecs ──────────────────────────────────────────
async function handleFetchRecs() {
    await fetchRecs(
        aiState,
        showAiToast,
        handleOpenModal,
        (sel, results) => updateAiContext(sel, results)   // update AI context on success
    );
}

// ── Bound renderFeatured / renderGrid ────────────────────────
function handleRenderFeatured(sel, results) {
    renderFeatured(sel, results, handleOpenModal);
}
function handleRenderGrid(results) {
    renderGrid(results, handleOpenModal);
}

// ── Bound navForYou ──────────────────────────────────────────
function navForYou() {
    setActiveNav('nav-foryou');
    fetchCFRecs(handleRenderFeatured, handleRenderGrid, handleOpenModal);
}

// ── Star rating: show review input after rating ──────────────
initStarRating(v => {
    const revSec = $('review-input-section');
    if (revSec && revSec.style.maxHeight === '0px') {
        revSec.style.maxHeight = '200px';
    }
});

// ── Initialise modules ───────────────────────────────────────
// Single request for both trending + new-releases; parallel with other init calls
fetch('/home-data')
    .then(r => r.json())
    .then(({ trending, new_releases }) => {
        loadTrending(m => {
            $('movie-input').value = m.title;
            $('hero-input').value  = m.title;
            handleFetchRecs();
        }, trending);
        loadNewReleases(handleOpenModal, new_releases);
    })
    .catch(() => {
        loadTrending(m => {
            $('movie-input').value = m.title;
            $('hero-input').value  = m.title;
            handleFetchRecs();
        });
        loadNewReleases(handleOpenModal);
    });

checkOllamaStatus();
setInterval(checkOllamaStatus, 30000);

loadUserRatings();
loadWatchlist();
initReviewCharCount();

// ── Event listeners ──────────────────────────────────────────
on($('movie-input'), 'keydown', e => { if (e.key === 'Enter') handleFetchRecs(); });
on($('hero-input'),  'keydown', e => { if (e.key === 'Enter') heroSearch(handleFetchRecs); });
on($('ai-input'),    'keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendAiMessage(); }
});
on(document, 'keydown', e => { if (e.key === 'Escape') closeModal(); });

// Close user dropdown when clicking outside
document.addEventListener('click', e => {
    const menu = $('user-menu');
    if (menu && !menu.contains(e.target)) {
        const dd = $('user-dropdown');
        if (dd) dd.classList.remove('open');
    }
});

// ── Expose to HTML onclick="" attributes ─────────────────────
// Navigation
window.navHome        = navHome;
window.navTrending    = navTrending;
window.navNewReleases = navNewReleases;
window.navBrowse      = navBrowse;
window.navForYou     = navForYou;
window.focusSearch   = focusSearch;
window.toggleUserMenu = toggleUserMenu;

// Search
window.fetchRecommendations = handleFetchRecs;
window.fetchRecs            = handleFetchRecs;   // back-compat alias
window.heroSearch           = () => heroSearch(handleFetchRecs);
window.searchByGenre        = (seed) => {
    $('movie-input').value = seed;
    $('hero-input').value  = seed;
    handleFetchRecs();
};

// Modal
window.closeModal          = closeModal;
window.handleBackdropClick = handleBackdropClick;
window.watchNow            = watchNow;
window.switchSource        = switchSource;

// Mood / Genre
window.fetchMoodRecs  = (mood)          => fetchMoodRecs(mood, handleRenderFeatured, handleRenderGrid, handleOpenModal);
window.fetchGenreRecs = (genre, label)  => fetchGenreRecs(genre, label, handleRenderFeatured, handleRenderGrid, handleOpenModal);

// AI
window.toggleAiPanel  = toggleAiPanel;
window.sendAiMessage  = sendAiMessage;
window.sendAiPrompt   = sendAiPrompt;
window.doAiSearch     = () => doAiSearch(handleFetchRecs);
window.hideAiToast    = hideAiToast;

// Watchlist
window.toggleWatchlist = () => toggleWatchlist(ratingState.currentModalMovie);
window.showWatchlist   = () => showWatchlist(handleOpenModal);

// Matchmaker
window.showMatchmaker = () => showMatchmaker(ratingState.userRatings);
window.fetchMatch     = () => fetchMatch(handleOpenModal);

// Reviews
window.submitReview  = () => submitReview(ratingState.currentModalMovie, ratingState.userRatings, loadMovieReviews);
window._deleteReview = (id, title) => deleteMyReview(id, title);
