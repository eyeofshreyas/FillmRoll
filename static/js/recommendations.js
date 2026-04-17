/* ── recommendations.js ── search, render featured & grid ── */
import { $ } from './utils.js';
import { setActiveNav, showHomeSections } from './nav.js';

/**
 * Render the "Based on" featured panel.
 * @param {object|null} sel     - selected movie object (may be null)
 * @param {object[]}    results - recommendation array
 * @param {function}    openModalFn - callback to open the modal
 */
export function renderFeatured(sel, results, openModalFn) {
    const title = sel ? sel.title : $('movie-input').value.trim();
    $('sel-title').textContent = title;
    $('sel-overview').textContent =
        sel && sel.overview
            ? sel.overview
            : `Showing ${results.length} titles similar to "${title}".`;

    const img = $('sel-poster');
    const posterCol = $('feat-poster-col');
    if (sel && sel.poster) {
        img.src = sel.poster;
        img.onerror = () => { img.src = 'https://placehold.co/300x450/1c1916/2e2a22?text=No+Image'; };
        posterCol.style.display = '';
    } else {
        img.src = '';
        posterCol.style.display = 'none';
    }

    const rat = $('sel-rating');
    rat.innerHTML = sel && sel.rating
        ? `<svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg> ${sel.rating}` : '';

    const feat = document.querySelector('.featured');
    feat.onclick = () => sel && openModalFn(sel);
    feat.style.animation = 'none';
    feat.offsetHeight; // force reflow
    feat.style.animation = null;

    $('selected-section').style.display = 'block';
}

/**
 * Render the recommendation card grid.
 * @param {object[]} results    - recommendation array
 * @param {function} openModalFn - callback to open the modal
 */
export function renderGrid(results, openModalFn) {
    const grid = $('rec-grid');
    grid.innerHTML = '';

    results.forEach((r, i) => {
        const card = document.createElement('div');
        card.className = 'card';
        const pct  = (r.score * 100).toFixed(0);
        const year = r.release_date ? r.release_date.slice(0, 4) : '';

        card.innerHTML = `
        <div class="poster-wrap">
          <img src="${r.poster}" alt="${r.title}" loading="lazy"
               onerror="this.src='https://placehold.co/300x450/1c1916/2e2a22?text=No+Poster'"/>
          <div class="card-overlay">
            <h4>${r.title}</h4>
            <div class="meta-row">
              <span class="c-star">&#9733; ${r.rating}</span>
              ${year ? `<span class="c-year">${year}</span>` : ''}
              <span class="c-pct">${pct}%</span>
            </div>
          </div>
          <div class="card-hover-overlay">
            <p>${r.overview || 'No overview available.'}</p>
            <div class="hover-cta">Watch trailer &rarr;</div>
          </div>
        </div>`;

        card.addEventListener('click', () => openModalFn(r));
        grid.appendChild(card);
        setTimeout(() => card.classList.add('show'), i * 55);
    });

    $('rec-count').textContent = `${results.length} titles`;
    $('rec-section').style.display = 'block';
}

/**
 * Fetch recommendations for the current search input value.
 * @param {object}   aiState     - { aiOnline, pendingSearchQuery }
 * @param {function} showAiToast - callback(query)
 * @param {function} openModalFn - callback for card clicks
 * @param {function} onResults   - callback(sel, results) after successful fetch
 */
export async function fetchRecs(aiState, showAiToast, openModalFn, onResults) {
    const title = $('movie-input').value.trim();
    const n = parseInt($('num-recs').value);
    if (!title) return;

    $('hero-section').style.display = 'none';
    $('trending-section').style.display = 'none';
    const nrSec = $('new-releases-section');
    if (nrSec) nrSec.style.display = 'none';
    $('mood-section').style.display = 'none';
    $('genre-section').style.display = 'none';
    document.querySelectorAll('.home-spacer').forEach(s => s.style.display = 'none');

    setActiveNav('');
    $('results-page').style.display = 'block';
    $('spinner').classList.add('active');
    $('selected-section').style.display = 'none';
    $('rec-section').style.display = 'none';

    try {
        const res = await fetch('/recommend', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, n }),
        });
        const data = await res.json();
        $('spinner').classList.remove('active');

        if (!data.results || !data.results.length) {
            if (aiState.aiOnline) {
                aiState.pendingSearchQuery = title;
                showAiToast(title);
                showHomeSections();
                setActiveNav('nav-home');
                $('results-page').style.display = 'none';
            } else {
                alert(`"${title}" wasn't found. Try a different spelling.`);
            }
            return;
        }

        renderFeatured(data.selected, data.results, openModalFn);
        renderGrid(data.results, openModalFn);
        if (onResults) onResults(data.selected, data.results);
    } catch (_) {
        $('spinner').classList.remove('active');
        alert('Server error — make sure Flask is running.');
    }
}

/** Trigger fetchRecs from the hero search bar. */
export function heroSearch(fetchRecsFn) {
    const val = $('hero-input').value.trim();
    if (!val) return;
    $('movie-input').value = val;
    fetchRecsFn();
}

/** Set both inputs to seedTitle and trigger search (used from genre cards). */
export function searchByGenre(seedTitle, fetchRecsFn) {
    $('movie-input').value = seedTitle;
    $('hero-input').value = seedTitle;
    fetchRecsFn();
}
