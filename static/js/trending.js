/* ── trending.js ── trending carousel loader ── */
import { $ } from './utils.js';

/**
 * Fetch trending movies from the server and render the carousel.
 * @param {function} onCardClick - callback(movie) when a card is clicked
 */
export async function loadTrending(onCardClick) {
    try {
        const res = await fetch('/trending');
        const list = await res.json();
        const row = $('trending-row');
        if (!list.length) return;
        row.innerHTML = '';
        list.forEach(m => {
            const year = m.release_date ? m.release_date.slice(0, 4) : '';
            const card = document.createElement('div');
            card.className = 't-card';
            card.innerHTML = `
          <div class="t-poster"><img src="${m.poster}" alt="${m.title}" loading="lazy"
            onerror="this.src='https://placehold.co/300x450/1c1916/2e2a22?text=No+Poster'"/></div>
          <div class="t-title">${m.title}</div>
          <div class="t-meta"><span class="t-star">&#9733; ${m.rating}</span>${year ? ' &middot; ' + year : ''}</div>`;
            card.addEventListener('click', () => onCardClick(m));
            row.appendChild(card);
        });
    } catch (_) { }
}
