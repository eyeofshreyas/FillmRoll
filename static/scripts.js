
/* ── user menu ── */
function toggleUserMenu() {
    const dd = document.getElementById('user-dropdown');
    if (dd) dd.classList.toggle('open');
}
document.addEventListener('click', e => {
    const menu = document.getElementById('user-menu');
    if (menu && !menu.contains(e.target)) {
        const dd = document.getElementById('user-dropdown');
        if (dd) dd.classList.remove('open');
    }
});

const $ = id => document.getElementById(id);
const on = (el, ev, fn) => el.addEventListener(ev, fn);

on($('movie-input'), 'keydown', e => { if (e.key === 'Enter') fetchRecs(); });
on($('hero-input'), 'keydown', e => { if (e.key === 'Enter') heroSearch(); });

function focusSearch() {
    showHomeSections();
    window.scrollTo({ top: 0, behavior: 'smooth' });
    setTimeout(() => $('hero-input').focus(), 400);
}

function searchByGenre(seedTitle) {
    $('movie-input').value = seedTitle;
    $('hero-input').value = seedTitle;
    fetchRecs();
}

function heroSearch() {
    const val = $('hero-input').value.trim();
    if (!val) return;
    $('movie-input').value = val;
    fetchRecs();
}

/* ── trending carousel ── */
(async function loadTrending() {
    try {
        const res = await fetch('/trending');
        const list = await res.json();
        const row = $('trending-row');
        if (!list.length) return;
        row.innerHTML = '';
        list.forEach(m => {
            const card = document.createElement('div');
            card.className = 't-card';
            card.innerHTML = `
          <div class="t-poster"><img src="${m.poster}" alt="${m.title}" loading="lazy"
            onerror="this.src='https://via.placeholder.com/300x450/1c1916/2e2a22?text=No+Poster'"/></div>
          <div class="t-title">${m.title}</div>
          <div class="t-meta"><span class="t-star">&#9733; ${m.rating}</span> &middot; ${m.year}</div>`;
            card.addEventListener('click', () => {
                $('movie-input').value = m.title;
                $('hero-input').value = m.title;
                fetchRecs();
            });
            row.appendChild(card);
        });
    } catch (_) { }
})();

/* ── fade-in observer ── */
const fadeObs = new IntersectionObserver((entries) => {
    entries.forEach(e => {
        if (e.isIntersecting) { e.target.classList.add('visible'); fadeObs.unobserve(e.target); }
    });
}, { threshold: 0.12 });
document.querySelectorAll('.fade-up').forEach(el => fadeObs.observe(el));

/* ── modal ── */
function handleBackdropClick(e) {
    if (e.target === $('modal-backdrop')) closeModal();
}
function closeModal() {
    $('modal-backdrop').classList.remove('open');
    const fr = $('modal-trailer').querySelector('iframe');
    if (fr) fr.src = '';
}
on(document, 'keydown', e => { if (e.key === 'Escape') closeModal(); });

async function openModal(data) {
    $('modal-title').textContent = data.title;
    $('modal-tagline').textContent = '';
    $('modal-overview').textContent = data.overview || '';
    $('modal-chips').innerHTML = data.rating
        ? `<span class="chip a">&#9733; ${data.rating} / 10</span>` : '';

    const img = $('modal-img');
    img.src = data.poster || '';
    img.onerror = () => { img.src = 'https://via.placeholder.com/300x450/1c1916/2e2a22?text=No+Image'; };

    $('modal-trailer').innerHTML =
        `<div class="modal-loading">
         <div class="dots" style="margin:0"><span></span><span></span><span></span></div>
         Loading trailer
       </div>`;
    $('modal-cast').style.display = 'none';
    $('cast-row').innerHTML = '';

    $('modal-backdrop').classList.add('open');
    $('modal-backdrop').scrollTop = 0;

    try {
        const res = await fetch('/details', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ movie_id: data.movie_id, title: data.title, media_type: data.media_type }),
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
            <img src="${c.photo || 'https://via.placeholder.com/56x56/242019/2e2a22?text=?'}"
                 alt="${c.name}"
                 onerror="this.src='https://via.placeholder.com/56x56/242019/2e2a22?text=?'"/>
            <div class="p-name">${c.name}</div>
            <div class="p-role">${c.character || ''}</div>`;
                row.appendChild(el);
            });
            $('modal-cast').style.display = 'block';
        }
    } catch (_) {
        $('modal-trailer').innerHTML = `<div class="no-trailer">Could not load details</div>`;
    }
}

/* ── recommendations ── */
async function fetchRecs() {
    const title = $('movie-input').value.trim();
    const n = parseInt($('num-recs').value);
    if (!title) return;

    $('hero-section').style.display = 'none';
    $('trending-section').style.display = 'none';
    $('genre-section').style.display = 'none';
    document.querySelectorAll('.home-spacer').forEach(s => s.style.display = 'none');

    setActiveNav('');   /* clear nav highlight on results page */
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
            alert(`"${title}" wasn't found. Try a different spelling.`);
            return;
        }

        renderFeatured(data.selected, data.results);
        renderGrid(data.results);
    } catch (_) {
        $('spinner').classList.remove('active');
        alert('Server error — make sure Flask is running.');
    }
}

function fetchRecommendations() { fetchRecs(); }

/* ── nav helpers ── */
function setActiveNav(id) {
    ['nav-home', 'nav-trending', 'nav-browse'].forEach(n => {
        $(n).classList.toggle('active', n === id);
    });
}

function showHomeSections() {
    $('results-page').style.display = 'none';
    $('hero-section').style.display = '';
    $('trending-section').style.display = '';
    $('genre-section').style.display = '';
    document.querySelectorAll('.home-spacer').forEach(s => s.style.display = '');
}

function navHome() {
    setActiveNav('nav-home');
    showHomeSections();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function navTrending() {
    setActiveNav('nav-trending');
    showHomeSections();
    setTimeout(() => {
        $('trending-section').scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 60);
}

function navBrowse() {
    setActiveNav('nav-browse');
    showHomeSections();
    setTimeout(() => {
        $('genre-section').scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 60);
}

function renderFeatured(sel, results) {
    const title = sel ? sel.title : $('movie-input').value.trim();
    $('sel-title').textContent = title;
    $('sel-overview').textContent =
        sel && sel.overview
            ? sel.overview
            : `Showing ${results.length} titles similar to "${title}".`;

    const img = $('sel-poster');
    img.src = sel && sel.poster ? sel.poster : '';
    img.onerror = () => { img.src = 'https://via.placeholder.com/300x450/1c1916/2e2a22?text=No+Image'; };

    const rat = $('sel-rating');
    rat.innerHTML = sel && sel.rating
        ? `<svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg> ${sel.rating}` : '';

    const feat = document.querySelector('.featured');
    feat.onclick = () => sel && openModal(sel);
    feat.style.animation = 'none';
    feat.offsetHeight;
    feat.style.animation = null;

    $('selected-section').style.display = 'block';
}

function renderGrid(results) {
    const grid = $('rec-grid');
    grid.innerHTML = '';

    results.forEach((r, i) => {
        const card = document.createElement('div');
        card.className = 'card';
        const pct = (r.score * 100).toFixed(0);

        card.innerHTML = `
        <div class="poster-wrap">
          <img src="${r.poster}" alt="${r.title}" loading="lazy"
               onerror="this.src='https://via.placeholder.com/300x450/1c1916/2e2a22?text=No+Poster'"/>
          <div class="card-overlay">
            <h4>${r.title}</h4>
            <div class="meta-row">
              <span class="c-star">&#9733; ${r.rating}</span>
              <span class="c-pct">${pct}%</span>
            </div>
          </div>
          <div class="card-hover-overlay">
            <p>${r.overview || 'No overview available.'}</p>
            <div class="hover-cta">Watch trailer &rarr;</div>
          </div>
        </div>`;

        card.addEventListener('click', () => openModal(r));
        grid.appendChild(card);
        setTimeout(() => card.classList.add('show'), i * 55);
    });

    $('rec-count').textContent = `${results.length} titles`;
    $('rec-section').style.display = 'block';
}

/* ══════════════════════════════════════════
   AI CHAT PANEL — JavaScript
══════════════════════════════════════════ */
let aiOnline = false;
let aiPanelOpen = false;
let chatHistory = [];        // {role, content}
let currentContext = {};     // selected movie + recs
let isStreaming = false;
let pendingSearchQuery = '';

// ── Check Ollama status on load ──
async function checkOllamaStatus() {
    try {
        const res = await fetch('/api/ollama-status');
        const data = await res.json();
        aiOnline = data.available;
    } catch { aiOnline = false; }

    const dot = $('ai-dot');
    const txt = $('ai-status-text');
    const badge = $('fab-badge');

    if (aiOnline) {
        dot.className = 'dot on';
        txt.textContent = 'Online';
        badge.className = 'fab-badge online';
    } else {
        dot.className = 'dot off';
        txt.textContent = 'Offline';
        badge.className = 'fab-badge offline';
    }
}
checkOllamaStatus();
setInterval(checkOllamaStatus, 30000);  // recheck every 30s

// ── Toggle panel ──
function toggleAiPanel() {
    aiPanelOpen = !aiPanelOpen;
    $('ai-panel').classList.toggle('open', aiPanelOpen);
    if (aiPanelOpen) {
        setTimeout(() => $('ai-input').focus(), 200);
    }
}

// ── Send message from input ──
function sendAiMessage() {
    const input = $('ai-input');
    const text = input.value.trim();
    if (!text || isStreaming) return;
    input.value = '';
    sendAiPrompt(text);
}

// ── Send prompt ──
async function sendAiPrompt(text) {
    if (!aiOnline) {
        appendAiMsg('system-msg', '⚠ Ollama is offline. Start it with: ollama serve');
        return;
    }
    if (isStreaming) return;

    // Hide suggestions after first message
    $('ai-suggestions').style.display = 'none';

    appendAiMsg('user', text);
    chatHistory.push({ role: 'user', content: text });

    // Show typing indicator
    const typingEl = appendAiMsg('assistant', '<div class="ai-typing"><span></span><span></span><span></span></div>');
    typingEl.dataset.typing = 'true';
    scrollAiChat();

    isStreaming = true;
    $('ai-send').disabled = true;

    try {
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: text,
                context: currentContext,
                history: chatHistory.slice(0, -1),  // don't double-send current msg
            }),
        });

        // Replace typing indicator with actual content
        typingEl.innerHTML = '';
        typingEl.dataset.typing = 'false';
        let fullResponse = '';

        const reader = res.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                try {
                    const payload = JSON.parse(line.slice(6));
                    if (payload.content) {
                        fullResponse += payload.content;
                        typingEl.textContent = fullResponse;
                        scrollAiChat();
                    }
                } catch { }
            }
        }

        chatHistory.push({ role: 'assistant', content: fullResponse });

    } catch (err) {
        typingEl.innerHTML = '';
        typingEl.textContent = 'Sorry, something went wrong. Please try again.';
    }

    isStreaming = false;
    $('ai-send').disabled = false;
}

function appendAiMsg(role, html) {
    const div = document.createElement('div');
    div.className = `ai-msg ${role}`;
    div.innerHTML = html;
    $('ai-messages').appendChild(div);
    scrollAiChat();
    return div;
}

function scrollAiChat() {
    const c = $('ai-messages');
    c.scrollTop = c.scrollHeight;
}

// Enter to send
$('ai-input').addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendAiMessage();
    }
});

// ── Update context when recommendations load ──
const _origRenderFeatured = renderFeatured;
renderFeatured = function (sel, results) {
    _origRenderFeatured(sel, results);
    currentContext = {
        selected: sel,
        recommendations: results,
    };
};

// ── AI Search Fallback ──
const _origFetchRecs = fetchRecs;
fetchRecs = async function () {
    const title = $('movie-input').value.trim();
    const n = parseInt($('num-recs').value);
    if (!title) return;

    $('hero-section').style.display = 'none';
    $('trending-section').style.display = 'none';
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
            // Instead of just alerting, offer AI search
            if (aiOnline) {
                pendingSearchQuery = title;
                showAiToast(title);
                // Restore home view
                showHomeSections();
                setActiveNav('nav-home');
                $('results-page').style.display = 'none';
            } else {
                alert(`"${title}" wasn't found. Try a different spelling.`);
            }
            return;
        }

        renderFeatured(data.selected, data.results);
        renderGrid(data.results);
    } catch (_) {
        $('spinner').classList.remove('active');
        alert('Server error — make sure Flask is running.');
    }
};

function showAiToast(query) {
    $('toast-text').innerHTML = `<strong>"${query}"</strong> not found. <strong>Ask AI to find it?</strong>`;
    $('ai-search-toast').classList.add('show');
    $('ai-search-spinner').classList.remove('active');
    $('btn-ai-search').style.display = '';
}

function hideAiToast() {
    $('ai-search-toast').classList.remove('show');
}

async function doAiSearch() {
    if (!pendingSearchQuery) return;
    $('btn-ai-search').style.display = 'none';
    $('ai-search-spinner').classList.add('active');
    $('toast-text').innerHTML = 'AI is searching…';

    try {
        const res = await fetch('/api/ai-search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: pendingSearchQuery }),
        });
        const data = await res.json();
        hideAiToast();

        if (data.found && data.title) {
            $('movie-input').value = data.title;
            $('hero-input').value = data.title;
            fetchRecs();
        } else {
            alert(`AI couldn't find a matching movie. Try describing it differently.`);
        }
    } catch {
        hideAiToast();
        alert('AI search failed. Make sure Ollama is running.');
    }
}
