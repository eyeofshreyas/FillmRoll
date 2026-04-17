/* ── matchmaker.js ── Movie Night Matchmaker page ── */
import { $ } from './utils.js';
import { setActiveNav } from './nav.js';

/**
 * Show the matchmaker page, populate the "Your Taste" chips,
 * and reset all form / result / error state.
 * @param {object} userRatings - the live ratings map from ratingState
 */
export function showMatchmaker(userRatings) {
    // Hide all other sections
    $('hero-section').style.display = 'none';
    $('trending-section').style.display = 'none';
    $('mood-section').style.display = 'none';
    $('genre-section').style.display = 'none';
    document.querySelectorAll('.home-spacer').forEach(s => s.style.display = 'none');

    ['results-page', 'watchlist-page'].forEach(id => {
        const el = $(id);
        if (el) el.style.display = 'none';
    });

    const page = $('matchmaker-page');
    if (!page) return;
    page.style.display = '';

    setActiveNav('');

    // Populate "Your Taste" chips from the top 6 rated movies
    const chipsEl = $('my-taste-chips');
    const emptyEl = $('my-taste-empty');
    if (chipsEl) {
        chipsEl.innerHTML = '';
        const sorted = Object.entries(userRatings).sort((a, b) => b[1] - a[1]).slice(0, 6);
        if (sorted.length === 0) {
            if (emptyEl) emptyEl.classList.remove('hidden');
        } else {
            if (emptyEl) emptyEl.classList.add('hidden');
            sorted.forEach(([title, rating]) => {
                const chip = document.createElement('span');
                chip.className   = 'taste-chip';
                chip.textContent = title;
                const star = document.createElement('span');
                star.className   = 'chip-star';
                star.textContent = '\u2605'.repeat(rating);
                chip.appendChild(star);
                chipsEl.appendChild(chip);
            });
        }
    }

    // Reset UI state
    const result  = $('matchmaker-result');
    const errEl   = $('matchmaker-error');
    const spinner = $('matchmaker-spinner');
    const input   = $('partner-input');
    if (result)  result.classList.add('hidden');
    if (errEl)   errEl.classList.add('hidden');
    if (spinner) spinner.classList.add('hidden');
    if (input)   input.value = '';
}

/**
 * Call the matchmaker API and display the result.
 * @param {function} openModalFn - callback to open the detail modal
 */
export async function fetchMatch(openModalFn) {
    const input      = $('partner-input');
    const partnerDesc = (input ? input.value : '').trim();
    const errEl      = $('matchmaker-error');
    const btn        = $('matchmaker-btn');
    const spinner    = $('matchmaker-spinner');
    const result     = $('matchmaker-result');

    if (!partnerDesc) {
        if (errEl) {
            errEl.textContent = 'Please describe your partner\u2019s taste first.';
            errEl.classList.remove('hidden');
        }
        return;
    }

    if (btn)     btn.disabled = true;
    if (spinner) spinner.classList.remove('hidden');
    if (result)  result.classList.add('hidden');
    if (errEl)   errEl.classList.add('hidden');

    try {
        const res  = await fetch('/api/matchmaker', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ partner_desc: partnerDesc }),
        });
        const data = await res.json();

        if (!res.ok) {
            if (errEl) {
                errEl.textContent = data.error || 'Something went wrong. Try again.';
                errEl.classList.remove('hidden');
            }
            return;
        }

        const cardEl   = $('matchmaker-card');
        const reasonEl = $('matchmaker-reason');

        if (cardEl) {
            if (data.in_catalog && data.movie) {
                const m   = data.movie;
                const img = document.createElement('img');
                img.src     = m.poster || '';
                img.alt     = m.title;
                img.loading = 'lazy';
                img.onerror = () => { img.src = 'https://placehold.co/300x450/1c1916/2e2a22?text=No+Poster'; };

                const info  = document.createElement('div');
                info.className = 'matchmaker-card-info';
                const h3in = document.createElement('h3');
                h3in.textContent = m.title;
                const pin  = document.createElement('p');
                pin.textContent = '\u2B50 ' + (m.rating ? m.rating.toFixed(1) : 'N/A');
                info.appendChild(h3in);
                info.appendChild(pin);

                cardEl.innerHTML = '';
                cardEl.appendChild(img);
                cardEl.appendChild(info);
                cardEl.onclick = () => openModalFn(m);
            } else {
                const wrapper = document.createElement('div');
                wrapper.className = 'matchmaker-card-info';
                const h3out = document.createElement('h3');
                h3out.textContent = data.title || 'Unknown';
                const pout  = document.createElement('p');
                pout.style.color   = '#e06c75';
                pout.textContent   = 'Not in our catalog \u2014 try searching online';
                wrapper.appendChild(h3out);
                wrapper.appendChild(pout);
                cardEl.innerHTML = '';
                cardEl.appendChild(wrapper);
                cardEl.onclick = null;
            }
        }

        if (reasonEl) {
            reasonEl.textContent = data.reason ? `\u201C${data.reason}\u201D` : '';
        }
        if (result) result.classList.remove('hidden');

    } catch (_) {
        if (errEl) {
            errEl.textContent = 'Network error. Check your connection.';
            errEl.classList.remove('hidden');
        }
    } finally {
        if (btn)     btn.disabled = false;
        if (spinner) spinner.classList.add('hidden');
    }
}
