/* ── reviews.js ── community reviews & comments ── */
import { $ } from './utils.js';
import { timeAgo } from './utils.js';

/** Wire up the character-count listener for the review textarea. */
export function initReviewCharCount() {
    const ta = $('review-text');
    if (ta) {
        ta.addEventListener('input', e => {
            $('review-char-count').textContent = `${e.target.value.length}/500`;
        });
    }
}

/**
 * Submit a new review for the currently open modal movie.
 * @param {object|null} currentModalMovie
 * @param {object}      userRatings
 * @param {function}    loadReviewsFn - callback to reload the review list
 */
export async function submitReview(currentModalMovie, userRatings, loadReviewsFn) {
    if (!currentModalMovie) return;
    const comment = $('review-text').value.trim();
    if (!comment) return;

    const rating = userRatings[currentModalMovie.title] || 0;
    if (rating === 0) {
        alert('Please select a star rating first.');
        return;
    }

    const btn = document.querySelector('.review-submit-btn');
    if (btn) btn.disabled = true;

    try {
        const res = await fetch('/api/reviews', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                movie_title: currentModalMovie.title,
                movie_id:    currentModalMovie.movie_id,
                rating,
                comment,
            }),
        });

        if (res.ok) {
            $('review-text').value = '';
            $('review-char-count').textContent = '0/500';
            const revSec = $('review-input-section');
            if (revSec) revSec.style.maxHeight = '0px';
            loadReviewsFn(currentModalMovie.title);
        } else {
            alert('Failed to post review. Please try again.');
        }
    } catch (_) {
        alert('Network error. Check your connection.');
    } finally {
        if (btn) btn.disabled = false;
    }
}

/**
 * Fetch and render reviews for a movie.
 * @param {string} title - movie title
 */
export async function loadMovieReviews(title) {
    const list = $('reviews-list');
    const sec  = $('community-reviews');
    if (!list || !sec) return;

    sec.style.display = 'block';
    list.innerHTML = '<div style="opacity:0.5; font-size:14px;">Loading reviews...</div>';

    try {
        const res     = await fetch('/api/reviews/' + encodeURIComponent(title));
        const reviews = await res.json();
        renderReviewCards(reviews);
    } catch (_) {
        list.innerHTML = '<div style="color:red; font-size:14px;">Failed to load reviews.</div>';
    }
}

/**
 * Delete a review by ID, then reload the list.
 * @param {string} id    - review ID
 * @param {string} title - movie title (to reload reviews)
 */
export async function deleteMyReview(id, title) {
    if (!confirm('Are you sure you want to delete your review?')) return;
    try {
        const res = await fetch('/api/reviews/' + encodeURIComponent(id), { method: 'DELETE' });
        if (res.ok) {
            loadMovieReviews(title);
        } else {
            alert('Could not delete review.');
        }
    } catch (_) {
        alert('Could not delete review.');
    }
}

/**
 * Render a list of review objects into the reviews-list element.
 * @param {object[]} reviews
 */
function renderReviewCards(reviews) {
    const list = $('reviews-list');
    $('reviews-count').textContent = reviews.length;

    if (!reviews || reviews.length === 0) {
        list.innerHTML = '<div class="review-empty-state">No reviews yet. Be the first!</div>';
        return;
    }

    list.innerHTML = '';
    const userEmailRaw = document.getElementById('user-dropdown')
        ?.querySelector('.user-email')?.textContent || '';

    reviews.forEach(r => {
        const card = document.createElement('div');
        card.className = 'review-card';

        let starsHtml = '';
        for (let i = 1; i <= 5; i++) {
            starsHtml += `<span style="color: ${i <= r.rating ? '#eebb4d' : '#444'}">★</span>`;
        }

        const isMine    = userEmailRaw === r.user_email;
        const deleteBtn = isMine
            ? `<button class="review-delete-btn" onclick="window._deleteReview('${r.id}', '${r.movie_title}')">&times;</button>`
            : '';

        card.innerHTML = `
            <div class="review-header">
                <img class="review-avatar"
                     src="${r.user_picture || `https://placehold.co/32x32/333/fff?text=${r.user_name?.[0] || '?'}`}"
                     onerror="this.src='https://placehold.co/32x32/333/fff?text=?'"/>
                <div style="flex:1">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-weight:600; color:#fff; font-size:14px;">${r.user_name}</span>
                        <div style="display:flex; align-items:center;">
                            <span style="margin-right:8px; font-size:13px; letter-spacing:1px;">${starsHtml}</span>
                            <span style="font-size:12px; opacity:0.5;">${timeAgo(r.created_at)}</span>
                            ${deleteBtn}
                        </div>
                    </div>
                </div>
            </div>
            <div class="review-body">${r.comment.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</div>
        `;
        list.appendChild(card);
    });
}
