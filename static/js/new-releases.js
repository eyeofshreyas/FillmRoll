/* ── new-releases.js ── movies released in the past 30 days ── */
import { $ } from './utils.js';

export async function loadNewReleases(onCardClick, prefetchedList) {
    try {
        const list = prefetchedList ?? await fetch('/new-releases').then(r => r.json());
        const row  = $('new-releases-row');
        if (!list.length) {
            document.getElementById('new-releases-section').style.display = 'none';
            return;
        }
        row.innerHTML = '';
        list.forEach(m => {
            const label = m.release_date
                ? new Date(m.release_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
                : '';
            const card = document.createElement('div');
            card.className = 't-card';
            card.innerHTML = `
              <div class="t-poster" style="position:relative">
                <img src="${m.poster}" alt="${m.title}" loading="lazy"
                  onerror="this.src='https://placehold.co/300x450/1c1916/2e2a22?text=No+Poster'"/>
                <span class="nr-badge">NEW</span>
              </div>
              <div class="t-title">${m.title}</div>
              <div class="t-meta"><span class="t-star">&#9733; ${m.rating || '—'}</span>${label ? ' &middot; ' + label : ''}</div>`;
            card.addEventListener('click', () => onCardClick(m));
            row.appendChild(card);
        });
    } catch (_) { }
}
