/* ── modal.js ── movie detail modal ── */
import { $ } from './utils.js';

/**
 * Fetch and show the "Why you'll like this" AI blurb.
 * @param {object} movie
 * @param {object} userRatings  - reference to the live ratings map
 * @param {object} modalState   - { currentMovie } reference so we can guard stale responses
 */
export async function fetchWhyBlurb(movie, userRatings, modalState) {
    const blurbEl = $('modal-why-blurb');
    const textEl  = $('why-blurb-text');
    if (!blurbEl || !textEl) return;

    const expectedTitle = movie.title;

    if (Object.keys(userRatings).length < 2) {
        blurbEl.classList.add('hidden');
        return;
    }

    blurbEl.classList.remove('hidden');
    blurbEl.classList.add('loading');
    textEl.textContent = 'Personalizing\u2026';

    try {
        const res = await fetch('/api/why-you-like', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: movie.title, overview: movie.overview || '', userRatings }),
        });
        if (modalState.currentModalMovie?.title !== expectedTitle) return;
        if (!res.ok) throw new Error(res.status);
        const data = await res.json();
        if (data.blurb) {
            textEl.textContent = data.blurb;
            blurbEl.classList.remove('loading');
        } else {
            blurbEl.classList.remove('loading');
            blurbEl.classList.add('hidden');
        }
    } catch (_) {
        if (modalState.currentModalMovie?.title === expectedTitle) {
            blurbEl.classList.remove('loading');
            blurbEl.classList.add('hidden');
        }
    }
}

/** Close the modal and stop any playing trailer. */
export function closeModal() {
    $('modal-backdrop').classList.remove('open');
    const fr = $('modal-trailer').querySelector('iframe');
    if (fr) fr.src = '';
    const watchBtn = $('modal-watch-btn');
    if (watchBtn) {
        watchBtn.textContent = '\u25BA Watch Now';
        watchBtn.onclick = () => watchNow();
    }
}

const SOURCES = [
    { label: 'Source 1', url: (type, id) => `https://vidsrc.mov/embed/${type}/${id}` },
    { label: 'Source 2', url: (type, id) => `https://player.autoembed.cc/embed/${type}/${id}` },
];

function buildPlayer(type, movieId, activeIdx) {
    const src = SOURCES[activeIdx].url(type, movieId);
    const tabs = SOURCES.map((s, i) =>
        `<button class="src-tab${i === activeIdx ? ' active' : ''}"
                 onclick="switchSource(${i})">${s.label}</button>`
    ).join('');
    $('modal-trailer').innerHTML =
        `<div class="src-tabs" data-type="${type}" data-id="${movieId}">${tabs}</div>
         <iframe src="${src}" allowfullscreen allow="fullscreen; autoplay"></iframe>`;
}

export function switchSource(idx) {
    const tabs = $('modal-trailer').querySelector('.src-tabs');
    if (!tabs) return;
    buildPlayer(tabs.dataset.type, tabs.dataset.id, idx);
}

/** Replace the trailer with an embedded player with source fallback. */
export function watchNow() {
    const btn       = $('modal-watch-btn');
    const movieId   = btn.dataset.movieId;
    const mediaType = btn.dataset.mediaType || 'movie';
    if (!movieId) return;

    buildPlayer(mediaType === 'tv' ? 'tv' : 'movie', movieId, 0);
    btn.textContent = '\u2715 Close Player';
    btn.onclick = () => closePlayer();
}

function closePlayer() {
    const btn = $('modal-watch-btn');
    $('modal-trailer').innerHTML =
        `<div class="modal-loading">
           <div class="dots" style="margin:0"><span></span><span></span><span></span></div>
           Reload trailer
         </div>`;
    btn.textContent = '\u25BA Watch Now';
    btn.onclick = () => watchNow();
}

/** Handle a click on the backdrop (close if clicked outside the modal box). */
export function handleBackdropClick(e) {
    if (e.target === $('modal-backdrop')) closeModal();
}

/**
 * Open the movie detail modal.
 * @param {object} data  - movie object { title, overview, poster, rating, movie_id, media_type }
 */
export async function openModal(data) {
    $('modal-title').textContent = data.title;
    $('modal-tagline').textContent = '';
    $('modal-overview').textContent = data.overview || '';
    $('modal-chips').innerHTML = data.rating
        ? `<span class="chip a">&#9733; ${data.rating} / 10</span>` : '';

    const img = $('modal-img');
    img.src = data.poster || '';
    img.onerror = () => { img.src = 'https://placehold.co/300x450/1c1916/2e2a22?text=No+Image'; };

    $('modal-trailer').innerHTML =
        `<div class="modal-loading">
         <div class="dots" style="margin:0"><span></span><span></span><span></span></div>
         Loading trailer
       </div>`;
    $('modal-cast').style.display = 'none';
    $('cast-row').innerHTML = '';
    $('modal-providers').style.display = 'none';
    $('providers-groups').innerHTML = '';

    const watchBtn = $('modal-watch-btn');
    if (watchBtn) {
        if (data.movie_id) {
            watchBtn.dataset.movieId   = data.movie_id;
            watchBtn.dataset.mediaType = data.media_type || 'movie';
            watchBtn.style.display     = '';
            watchBtn.textContent       = '\u25BA Watch Now';
            watchBtn.onclick           = () => watchNow();
        } else {
            watchBtn.style.display = 'none';
        }
    }

    $('modal-backdrop').classList.add('open');
    $('modal-backdrop').scrollTop = 0;

    try {
        const res = await fetch('/details', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                movie_id:   data.movie_id,
                title:      data.title,
                media_type: data.media_type,
                country:    (() => {
                    try { return new Intl.Locale(navigator.language).region || 'US'; }
                    catch (_) { return (navigator.language.split('-')[1] || 'US').toUpperCase(); }
                })(),
            }),
        });
        const det = await res.json();

        // trailer
        const tw = $('modal-trailer');
        if (det.trailer_key) {
            tw.innerHTML = `
                <iframe src="https://www.youtube.com/embed/${det.trailer_key}?autoplay=1&rel=0"
                        allow="autoplay; encrypted-media" allowfullscreen></iframe>
                <a class="yt-fallback" href="https://www.youtube.com/watch?v=${det.trailer_key}"
                   target="_blank" rel="noopener">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M19.615 3.184c-3.604-.246-11.631-.245-15.23 0-3.897.266-4.356 2.62-4.385 8.816.029 6.185.484 8.549 4.385 8.816 3.6.245 11.626.246 15.23 0 3.897-.266 4.356-2.62 4.385-8.816-.029-6.185-.484-8.549-4.385-8.816zm-10.615 12.816v-8l8 3.993-8 4.007z"/></svg>
                    Watch on YouTube
                </a>`;
        } else {
            tw.innerHTML = `<div class="no-trailer">
          <svg width="44" height="44" fill="none" stroke="currentColor" stroke-width="1" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="10"/>
            <polygon points="10 8 16 12 10 16 10 8" fill="currentColor" stroke="none"/>
          </svg>
          No trailer available
        </div>`;
        }

        // chips
        const chips = $('modal-chips');
        (det.genres || []).slice(0, 4).forEach(g => {
            const s = document.createElement('span');
            s.className = 'chip'; s.textContent = g;
            chips.appendChild(s);
        });
        if (det.runtime) {
            const s = document.createElement('span');
            s.className = 'chip'; s.textContent = `${det.runtime} min`;
            chips.appendChild(s);
        }

        if (det.tagline) $('modal-tagline').textContent = `"${det.tagline}"`;

        // cast
        if (det.cast && det.cast.length) {
            const row = $('cast-row');
            det.cast.forEach((c, i) => {
                const el = document.createElement('div');
                el.className = 'cast-person';
                el.style.animationDelay = `${i * 50}ms`;
                el.innerHTML = `
            <img src="${c.photo || 'https://placehold.co/56x56/242019/2e2a22?text=?'}"
                 alt="${c.name}"
                 onerror="this.src='https://placehold.co/56x56/242019/2e2a22?text=?'"/>
            <div class="p-name">${c.name}</div>
            <div class="p-role">${c.character || ''}</div>`;
                row.appendChild(el);
            });
            $('modal-cast').style.display = 'block';
        }

        // providers
        if (det.watch_providers) {
            const groups = $('providers-groups');
            const jwLink = det.watch_providers.link || '';
            const labels = { flatrate: 'Stream', rent: 'Rent', buy: 'Buy' };
            let hasAny = false;
            ['flatrate', 'rent', 'buy'].forEach(type => {
                const list = det.watch_providers[type] || [];
                if (!list.length) return;
                hasAny = true;
                const group = document.createElement('div');
                group.className = 'provider-group';
                const typeLabel = document.createElement('span');
                typeLabel.className = 'provider-type-label';
                typeLabel.textContent = labels[type];
                group.appendChild(typeLabel);
                list.forEach(p => {
                    const img = document.createElement('img');
                    img.src = p.logo_path || '';
                    img.alt = p.provider_name;
                    img.title = p.provider_name;
                    img.className = 'provider-logo';
                    img.onerror = () => img.style.display = 'none';
                    if (jwLink) {
                        const a = document.createElement('a');
                        a.href = jwLink;
                        a.target = '_blank';
                        a.rel = 'noopener noreferrer';
                        a.appendChild(img);
                        group.appendChild(a);
                    } else {
                        group.appendChild(img);
                    }
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
    } catch (_) {
        $('modal-trailer').innerHTML = `<div class="no-trailer">Could not load details</div>`;
    }
}
