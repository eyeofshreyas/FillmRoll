/* ── nav.js ── navigation & page visibility ── */
import { $ } from './utils.js';

const NAV_MAP = {
    'nav-home':          'mob-home',
    'nav-trending':      'mob-trending',
    'nav-new-releases':  'mob-new-releases',
    'nav-browse':        'mob-browse',
    'nav-foryou':        'mob-foryou',
};

export function setActiveNav(id) {
    ['nav-home', 'nav-trending', 'nav-new-releases', 'nav-browse', 'nav-foryou'].forEach(n => {
        const el = $(n);
        if (el) el.classList.toggle('active', n === id);
    });
    ['mob-home', 'mob-trending', 'mob-new-releases', 'mob-browse', 'mob-foryou'].forEach(n => {
        const el = $(n);
        if (el) el.classList.toggle('active', n === NAV_MAP[id]);
    });
}

export function showHomeSections() {
    $('results-page').style.display = 'none';
    const wlPage = $('watchlist-page');
    if (wlPage) wlPage.style.display = 'none';
    const mmPage = $('matchmaker-page');
    if (mmPage) mmPage.style.display = 'none';
    $('hero-section').style.display = '';
    $('trending-section').style.display = '';
    const nrSection = $('new-releases-section');
    if (nrSection) nrSection.style.display = '';
    $('mood-section').style.display = '';
    $('genre-section').style.display = '';
    document.querySelectorAll('.home-spacer').forEach(s => s.style.display = '');
}

export function showResultsPage() {
    $('hero-section').style.display = 'none';
    $('trending-section').style.display = 'none';
    const nrSection = $('new-releases-section');
    if (nrSection) nrSection.style.display = 'none';
    $('mood-section').style.display = 'none';
    $('genre-section').style.display = 'none';
    document.querySelectorAll('.home-spacer').forEach(s => s.style.display = 'none');
    const wlPage = $('watchlist-page');
    if (wlPage) wlPage.style.display = 'none';
    const mmPage = $('matchmaker-page');
    if (mmPage) mmPage.style.display = 'none';
    setActiveNav('');
    $('results-page').style.display = 'block';
    $('spinner').classList.add('active');
    $('selected-section').style.display = 'none';
    $('rec-section').style.display = 'none';
}

export function navHome() {
    setActiveNav('nav-home');
    showHomeSections();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

export function navTrending() {
    setActiveNav('nav-trending');
    showHomeSections();
    setTimeout(() => {
        $('trending-section').scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 60);
}

export function navNewReleases() {
    setActiveNav('nav-new-releases');
    showHomeSections();
    setTimeout(() => {
        $('new-releases-section').scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 60);
}

export function navBrowse() {
    setActiveNav('nav-browse');
    showHomeSections();
    setTimeout(() => {
        $('genre-section').scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 60);
}

export function focusSearch() {
    showHomeSections();
    window.scrollTo({ top: 0, behavior: 'smooth' });
    setTimeout(() => $('hero-input').focus(), 400);
}

/** Toggle the user dropdown menu. */
export function toggleUserMenu() {
    const dd = $('user-dropdown');
    if (dd) dd.classList.toggle('open');
}
