import os
import json
import requests

HF_TOKEN    = os.environ.get('HF_TOKEN', '')
HF_MODEL    = 'meta-llama/Llama-3.1-8B-Instruct'
HF_CHAT_URL = 'https://router.huggingface.co/v1/chat/completions'

def hf_available():
    """Check if HF token is configured."""
    return bool(HF_TOKEN)

def build_system_prompt(context=None):
    """Build a movie-expert system prompt for Llama."""
    base = (
        "You are FilmRoll AI, a passionate and knowledgeable entertainment expert assistant. "
        "You help users discover and discuss movies and TV shows. Keep responses concise (2-4 sentences usually), "
        "enthusiastic, and conversational. Use terminology naturally. "
        "When recommending titles, briefly explain WHY you think the user would enjoy them. "
        "If you don't know about a specific title, say so honestly."
    )

    if context:
        selected = context.get('selected')
        recs = context.get('recommendations', [])

        if selected:
            base += f"\n\nThe user is currently looking at: \"{selected['title']}\" "
            if selected.get('rating'):
                base += f"(rated {selected['rating']}/10). "
            if selected.get('overview'):
                base += f"Overview: {selected['overview'][:200]}. "

        if recs:
            rec_titles = [r['title'] for r in recs[:8]]
            base += (
                f"\n\nThe system recommended these similar titles: {', '.join(rec_titles)}. "
                "You can reference these when the user asks about the recommendations."
            )

    return base

def stream_hf_chat(messages):
    """Stream chat completion from HF Inference API, yielding SSE events."""
    try:
        r = requests.post(
            HF_CHAT_URL,
            headers={'Authorization': f'Bearer {HF_TOKEN}'},
            json={'model': HF_MODEL, 'messages': messages, 'stream': True, 'max_tokens': 512},
            stream=True,
            timeout=60,
        )

        if r.status_code != 200:
            try:
                err_msg = r.json().get('error', r.text)
            except Exception:
                err_msg = r.text
            yield f"data: {json.dumps({'content': f'HF API Error ({r.status_code}): {err_msg}', 'done': True})}\n\n"
            return

        for line in r.iter_lines():
            if not line:
                continue
            line = line.decode('utf-8') if isinstance(line, bytes) else line
            if not line.startswith('data: '):
                continue
            chunk = line[6:]
            if chunk == '[DONE]':
                yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
                break
            try:
                data = json.loads(chunk)
                content = data['choices'][0]['delta'].get('content', '')
                if content:
                    yield f"data: {json.dumps({'content': content, 'done': False})}\n\n"
            except Exception:
                pass

    except Exception as e:
        yield f"data: {json.dumps({'content': f'Error: {str(e)}', 'done': True})}\n\n"

def call_hf_chat_sync(messages, max_tokens=150):
    """Non-streaming HF chat completion. Returns content string or None on error."""
    if not hf_available():
        return None
    try:
        r = requests.post(
            HF_CHAT_URL,
            headers={'Authorization': f'Bearer {HF_TOKEN}'},
            json={'model': HF_MODEL, 'messages': messages, 'stream': False, 'max_tokens': max_tokens},
            timeout=30,
        )
        if r.status_code == 200:
            return r.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        pass
    return None
