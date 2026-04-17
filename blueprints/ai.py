from flask import Blueprint, request, jsonify, Response
from services.ai import stream_hf_chat, call_hf_chat_sync, build_system_prompt, hf_available
from services.ml import get_movie_by_exact_match, get_movie_by_fuzzy_match, get_all_titles
from blueprints.auth import login_required
import json
import re

ai_bp = Blueprint('ai', __name__)

@ai_bp.route('/api/ai-status', methods=['GET'])
def ai_status():
    return jsonify({'available': hf_available()})

@ai_bp.route('/api/chat', methods=['POST'])
@login_required
def chat():
    data = request.get_json()
    user_msg = data.get('message', '').strip()
    history  = data.get('history', [])
    context  = data.get('context', {})

    if not user_msg:
        return jsonify({'error': 'Empty message'}), 400
    if not hf_available():
        return jsonify({'error': 'HF token not configured. AI features disabled.'}), 503

    messages = [{"role": "system", "content": build_system_prompt(context)}]
    for msg in history[-6:]:
        role = 'assistant' if msg.get('isBot') else 'user'
        if msg.get('text'):
            messages.append({"role": role, "content": msg['text']})
    messages.append({"role": "user", "content": user_msg})

    return Response(stream_hf_chat(messages), mimetype='text/event-stream')

@ai_bp.route('/api/ai-search', methods=['POST'])
@login_required
def ai_search():
    data = request.get_json()
    query = data.get('query', '').strip()
    if not query:
        return jsonify({'error': 'Empty query'}), 400

    titles = get_all_titles()
    system_msg = (
        "You are an AI that maps natural language queries to EXACT movie titles. "
        "Return ONLY a JSON list of up to 5 exact matching titles from the catalog. "
        "Do NOT output markdown formatting like ```json. ONLY the raw list."
    )
    prompt = (
        f"Query: \"{query}\"\n\n"
        f"Catalog contains {len(titles)} titles. E.g. {titles[:10]}\n\n"
        "Return exactly a JSON list of strings (e.g. [\"Inception\", \"Interstellar\"]) representing the best matches."
    )

    resp = call_hf_chat_sync([
        {"role": "system", "content": system_msg},
        {"role": "user", "content": prompt}
    ], max_tokens=150)

    if not resp:
        return jsonify({'error': 'AI failed to respond or not configured'}), 503

    try:
        clean_text = resp.strip()
        if clean_text.startswith('```json'):
            clean_text = clean_text[7:-3].strip()
        elif clean_text.startswith('```'):
            clean_text = clean_text[3:-3].strip()

        suggested_titles = json.loads(clean_text)
        if not isinstance(suggested_titles, list):
            suggested_titles = []
    except json.JSONDecodeError:
        matches = re.findall(r'"([^"]+)"', resp)
        suggested_titles = matches if matches else []

    found = []
    for st in suggested_titles:
        m = get_movie_by_fuzzy_match(st)
        if m:
            found.append(m)

    if not found:
        return jsonify({'error': 'No matching movies found in catalog for your prompt.', 'raw': str(resp)})

    return jsonify(found)

@ai_bp.route('/api/matchmaker', methods=['POST'])
@login_required
def matchmaker():
    data = request.get_json()
    partner_desc = data.get('partner_desc', '').strip()
    if not partner_desc:
        return jsonify({'error': 'No description provided'}), 400

    titles = get_all_titles()
    system_msg = (
        "You are an AI movie matchmaker. Given a description of a partner's taste and potentially the user's taste, "
        "recommend exactly ONE movie. Return ONLY valid JSON with two keys: 'title' (string) and 'reason' (string). "
        "Do not wrap in markdown."
    )
    prompt = (
        f"Partner description: \"{partner_desc}\"\n"
        "Recommend the single best movie for a date night. "
        "Ensure the output is strictly ```json{\"title\":\"...\",\"reason\":\"...\"}```"
    )

    resp = call_hf_chat_sync([
        {"role": "system", "content": system_msg},
        {"role": "user", "content": prompt}
    ], max_tokens=200)

    if not resp:
        return jsonify({'error': 'AI failed to respond'}), 503

    try:
        clean = resp.strip()
        if clean.startswith('```json'): clean = clean[7:-3].strip()
        elif clean.startswith('```'): clean = clean[3:-3].strip()
        parsed = json.loads(clean)
        title = parsed.get('title', '')
        reason = parsed.get('reason', '')
    except Exception:
        match = re.search(r'"title"\s*:\s*"([^"]+)"', resp, re.IGNORECASE)
        t_match = match.group(1) if match else "Unknown"
        rmatch = re.search(r'"reason"\s*:\s*"([^"]+)"', resp, re.IGNORECASE)
        r_match = rmatch.group(1) if rmatch else "We think you'll like this."
        title = t_match
        reason = r_match

    exact = get_movie_by_exact_match(title)
    if exact:
        return jsonify({'in_catalog': True, 'title': exact, 'movie': get_movie_by_fuzzy_match(exact), 'reason': reason})
    return jsonify({'in_catalog': False, 'title': title, 'reason': reason})

@ai_bp.route('/api/why-you-like', methods=['POST'])
@login_required
def why_you_like():
    data = request.get_json()
    movie_title = data.get('title')
    user_ratings = data.get('userRatings', {})

    if not movie_title:
        return jsonify({'error': 'Missing title'}), 400

    # If no ratings yet, skip silently
    if not user_ratings:
        return jsonify({'blurb': None})

    highly_rated = [t for t, r in user_ratings.items() if r >= 4 and t.lower() != movie_title.lower()]
    context_str = ", ".join(highly_rated[:5]) if highly_rated else "various movies"

    system_msg = (
        "You analyze why a user might enjoy a specific movie based on their previously highly rated movies. "
        "Keep it to exactly one short, punchy sentence. Example: 'Because you loved the fast-paced action in X, you will enjoy Y.'"
    )
    prompt = f"Target movie: '{movie_title}'. User highly rated: {context_str}. Why will they like the target movie? One sentence."

    ans = call_hf_chat_sync([
        {"role": "system", "content": system_msg},
        {"role": "user", "content": prompt}
    ], max_tokens=60)

    if ans:
        return jsonify({'blurb': ans})
    return jsonify({'error': 'AI timeout'}), 503
