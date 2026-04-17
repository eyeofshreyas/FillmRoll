/* ── ai-chat.js ── AI chat panel + search toast ── */
import { $ } from './utils.js';

// ── Module state ──────────────────────────────────────────────
export const aiState = {
    aiOnline: false,
    aiPanelOpen: false,
    isStreaming: false,
    pendingSearchQuery: '',
};

let chatHistory = [];        // { role, content }[]
let currentContext = {};     // { selected, recommendations }

// ── Status check ─────────────────────────────────────────────

export async function checkOllamaStatus() {
    try {
        const res = await fetch('/api/ai-status');
        const data = await res.json();
        aiState.aiOnline = data.available;
    } catch {
        aiState.aiOnline = false;
    }

    const dot   = $('ai-dot');
    const txt   = $('ai-status-text');
    const badge = $('fab-badge');

    if (aiState.aiOnline) {
        dot.className   = 'dot on';
        txt.textContent = 'Online';
        badge.className = 'fab-badge online';
    } else {
        dot.className   = 'dot off';
        txt.textContent = 'Offline';
        badge.className = 'fab-badge offline';
    }
}

// ── Panel toggle ──────────────────────────────────────────────

export function toggleAiPanel() {
    aiState.aiPanelOpen = !aiState.aiPanelOpen;
    $('ai-panel').classList.toggle('open', aiState.aiPanelOpen);
    if (aiState.aiPanelOpen) {
        setTimeout(() => $('ai-input').focus(), 200);
    }
}

// ── Context update (called after recommendations render) ──────

export function updateAiContext(sel, results) {
    currentContext = { selected: sel, recommendations: results };
}

// ── Message helpers ───────────────────────────────────────────

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

// ── Send message ──────────────────────────────────────────────

export function sendAiMessage() {
    const input = $('ai-input');
    const text  = input.value.trim();
    if (!text || aiState.isStreaming) return;
    input.value = '';
    sendAiPrompt(text);
}

export async function sendAiPrompt(text) {
    if (!aiState.aiOnline) {
        appendAiMsg('system-msg', '⚠ AI service unavailable. Check that HF_TOKEN is set.');
        return;
    }
    if (aiState.isStreaming) return;

    // Hide quick-suggestions after first user message
    $('ai-suggestions').style.display = 'none';

    appendAiMsg('user', text);
    chatHistory.push({ role: 'user', content: text });

    // Typing indicator
    const typingEl = appendAiMsg('assistant', '<div class="ai-typing"><span></span><span></span><span></span></div>');
    typingEl.dataset.typing = 'true';
    scrollAiChat();

    aiState.isStreaming = true;
    $('ai-send').disabled = true;

    try {
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: text,
                context: currentContext,
                history: chatHistory.slice(0, -1), // exclude the just-pushed message
            }),
        });

        typingEl.innerHTML = '';
        typingEl.dataset.typing = 'false';
        let fullResponse = '';

        const reader  = res.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value, { stream: true });
            for (const line of chunk.split('\n')) {
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

    } catch (_) {
        typingEl.innerHTML = '';
        typingEl.textContent = 'Sorry, something went wrong. Please try again.';
    }

    aiState.isStreaming = false;
    $('ai-send').disabled = false;
}

// ── Search fallback toast ─────────────────────────────────────

export function showAiToast(query) {
    $('toast-text').innerHTML = `<strong>"${query}"</strong> not found. <strong>Ask AI to find it?</strong>`;
    $('ai-search-toast').classList.add('show');
    $('ai-search-spinner').classList.remove('active');
    $('btn-ai-search').style.display = '';
}

export function hideAiToast() {
    $('ai-search-toast').classList.remove('show');
}

/**
 * Ask the AI to resolve a vague/misspelled query, then trigger a real search.
 * @param {function} fetchRecsFn - the bound fetchRecs callback
 */
export async function doAiSearch(fetchRecsFn) {
    if (!aiState.pendingSearchQuery) return;
    $('btn-ai-search').style.display = 'none';
    $('ai-search-spinner').classList.add('active');
    $('toast-text').innerHTML = 'AI is searching\u2026';

    try {
        const res = await fetch('/api/ai-search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: aiState.pendingSearchQuery }),
        });
        const data = await res.json();
        hideAiToast();

        if (data.found && data.title) {
            $('movie-input').value = data.title;
            $('hero-input').value  = data.title;
            fetchRecsFn();
        } else {
            alert(`AI couldn't find a matching movie. Try describing it differently.`);
        }
    } catch {
        hideAiToast();
        alert('AI search failed. Make sure Ollama is running.');
    }
}
