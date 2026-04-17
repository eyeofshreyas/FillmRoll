/* ── utils.js ── shared helpers ── */

/** Shorthand for document.getElementById */
export const $ = id => document.getElementById(id);

/** Shorthand for addEventListener */
export const on = (el, ev, fn) => el.addEventListener(ev, fn);

/**
 * Convert an ISO date string to a human-readable "time ago" string.
 * @param {string} isoDate
 * @returns {string}
 */
export function timeAgo(isoDate) {
    if (!isoDate) return '';
    const seconds = Math.floor((new Date() - new Date(isoDate)) / 1000);
    let interval = seconds / 31536000;
    if (interval > 1) return Math.floor(interval) + 'y ago';
    interval = seconds / 2592000;
    if (interval > 1) return Math.floor(interval) + 'mo ago';
    interval = seconds / 86400;
    if (interval > 1) return Math.floor(interval) + 'd ago';
    interval = seconds / 3600;
    if (interval > 1) return Math.floor(interval) + 'h ago';
    interval = seconds / 60;
    if (interval > 1) return Math.floor(interval) + 'm ago';
    return 'Just now';
}
