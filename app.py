import pickle
import json
import pandas as pd
import requests
from flask import Flask, render_template, request, jsonify, Response, stream_with_context

app = Flask(__name__)

API_KEY  = 'ebef1aa0b639138c3040e6929ea9f1eb'
IMG_BASE = 'https://image.tmdb.org/t/p/w500'
TMDB_BASE = 'https://api.themoviedb.org/3'
SEARCH_URL = f'{TMDB_BASE}/search/movie'

OLLAMA_BASE = 'http://localhost:11434'
LLAMA_MODEL = 'llama3.2'

# Load model once at startup
movies_dict = pickle.load(open('movies_dict.pkl', 'rb'))
similarity  = pickle.load(open('similarity.pkl',  'rb'))
movies      = pd.DataFrame(movies_dict)


def is_valid_path(val):
    if val is None:
        return False
    try:
        s = str(val).strip()
        return s != '' and s != 'nan' and s != 'None'
    except Exception:
        return False


def tmdb_get(path, extra_params=None):
    params = {'api_key': API_KEY, 'language': 'en-US'}
    if extra_params:
        params.update(extra_params)
    try:
        r = requests.get(f'{TMDB_BASE}{path}', params=params, timeout=6)
        return r.json()
    except Exception:
        return {}


def fetch_poster_from_tmdb(title):
    data = tmdb_get('/search/movie', {'query': title})
    results = data.get('results', [])
    if results and results[0].get('poster_path'):
        return IMG_BASE + results[0]['poster_path']
    return None


def get_poster(poster_path, title=None):
    if is_valid_path(poster_path):
        return IMG_BASE + str(poster_path).strip()
    if title:
        live = fetch_poster_from_tmdb(title)
        if live:
            return live
    return 'https://via.placeholder.com/500x750/ede9e0/7a7060?text=No+Poster'


def get_movie_id_from_row(row):
    """Safely extract movie_id from a DataFrame row."""
    val = row.get('movie_id')
    if val is None:
        return None
    try:
        s = str(val).strip()
        if s in ('', 'nan', 'None'):
            return None
        return int(float(s))
    except Exception:
        return None


def build_movie_dict(row, score=None):
    d = {
        'movie_id': get_movie_id_from_row(row),
        'title':    row['title'],
        'poster':   get_poster(row.get('poster_path'), row['title']),
        'rating':   round(float(row.get('vote_average', 0)), 1),
        'overview': row.get('overview', ''),
    }
    if score is not None:
        d['score'] = round(float(score), 3)
    return d


def recommend(movie_title, n=8):
    match = movies[movies['title'].str.lower() == movie_title.lower()]
    if match.empty:
        return []

    idx       = match.index[0]
    distances = similarity[idx]
    top_n     = sorted(enumerate(distances), key=lambda x: x[1], reverse=True)[1:n + 1]

    return [build_movie_dict(movies.iloc[i], score) for i, score in top_n]


# ── Ollama / Llama helpers ──────────────────────────────────────

def ollama_available():
    """Check if Ollama server is reachable."""
    try:
        r = requests.get(f'{OLLAMA_BASE}/api/tags', timeout=3)
        if r.status_code == 200:
            models = [m['name'] for m in r.json().get('models', [])]
            # Match model name with or without tag suffix
            return any(m.startswith(LLAMA_MODEL) for m in models)
        return False
    except Exception:
        return False


def build_system_prompt(context=None):
    """Build a movie-expert system prompt for Llama."""
    base = (
        "You are FilmRoll AI, a passionate and knowledgeable movie expert assistant. "
        "You help users discover and discuss movies. Keep responses concise (2-4 sentences usually), "
        "enthusiastic, and conversational. Use movie terminology naturally. "
        "When recommending movies, briefly explain WHY you think the user would enjoy them. "
        "If you don't know about a specific movie, say so honestly."
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
                f"\n\nThe system recommended these similar films: {', '.join(rec_titles)}. "
                "You can reference these when the user asks about the recommendations."
            )

    return base


def stream_ollama_chat(messages):
    """Stream chat completion from Ollama, yielding SSE events."""
    try:
        r = requests.post(
            f'{OLLAMA_BASE}/api/chat',
            json={
                'model': LLAMA_MODEL,
                'messages': messages,
                'stream': True,
            },
            stream=True,
            timeout=120,
        )

        for line in r.iter_lines():
            if line:
                data = json.loads(line)
                content = data.get('message', {}).get('content', '')
                done = data.get('done', False)
                if content:
                    yield f"data: {json.dumps({'content': content, 'done': False})}\n\n"
                if done:
                    yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
                    break

    except Exception as e:
        yield f"data: {json.dumps({'content': f'Error: {str(e)}', 'done': True})}\n\n"


# ── Routes ────────────────────────────────────────────────────

@app.route('/')
def index():
    movie_list = sorted(movies['title'].dropna().tolist())
    return render_template('index.html', movies=movie_list)


@app.route('/trending')
def trending():
    """Fetch trending movies from TMDB for the homepage carousel."""
    try:
        data = tmdb_get('/trending/movie/week')
        results = data.get('results', [])[:12]
        out = []
        for m in results:
            poster = IMG_BASE + m['poster_path'] if m.get('poster_path') else None
            out.append({
                'title':   m.get('title', ''),
                'poster':  poster,
                'rating':  round(float(m.get('vote_average', 0)), 1),
                'year':    (m.get('release_date') or '')[:4],
            })
        return jsonify(out)
    except Exception:
        return jsonify([])


@app.route('/recommend', methods=['POST'])
def get_recommendations():
    data  = request.get_json()
    title = data.get('title', '')
    n     = int(data.get('n', 8))
    recs  = recommend(title, n)

    selected = None
    match = movies[movies['title'].str.lower() == title.lower()]
    if not match.empty:
        selected = build_movie_dict(movies.iloc[match.index[0]])

    return jsonify({'results': recs, 'selected': selected})


@app.route('/movie-details', methods=['POST'])
def movie_details():
    data     = request.get_json()
    movie_id = data.get('movie_id')
    title    = data.get('title', '')

    # If no stored id, search TMDB to get it
    if not movie_id:
        search = tmdb_get('/search/movie', {'query': title})
        results = search.get('results', [])
        if results:
            movie_id = results[0]['id']

    if not movie_id:
        return jsonify({'error': 'Not found'}), 404

    # ── Trailer ──────────────────────────────────────────────
    trailer_key = None
    videos = tmdb_get(f'/movie/{movie_id}/videos').get('results', [])
    # prefer official trailer
    for v in videos:
        if v.get('site') == 'YouTube' and v.get('type') == 'Trailer' and v.get('official'):
            trailer_key = v['key']
            break
    if not trailer_key:
        for v in videos:
            if v.get('site') == 'YouTube' and v.get('type') == 'Trailer':
                trailer_key = v['key']
                break
    if not trailer_key:
        for v in videos:
            if v.get('site') == 'YouTube':
                trailer_key = v['key']
                break

    # ── Cast ─────────────────────────────────────────────────
    cast = []
    credits = tmdb_get(f'/movie/{movie_id}/credits')
    for c in credits.get('cast', [])[:8]:
        cast.append({
            'name':      c.get('name', ''),
            'character': c.get('character', ''),
            'photo':     IMG_BASE + c['profile_path'] if c.get('profile_path') else None,
        })

    # ── Extra details ─────────────────────────────────────────
    detail = tmdb_get(f'/movie/{movie_id}')
    genres = [g['name'] for g in detail.get('genres', [])]
    runtime = detail.get('runtime')
    tagline = detail.get('tagline', '')

    return jsonify({
        'trailer_key': trailer_key,
        'cast':        cast,
        'genres':      genres,
        'runtime':     runtime,
        'tagline':     tagline,
    })


# ── Ollama / AI Endpoints ────────────────────────────────────

@app.route('/api/ollama-status')
def ollama_status():
    """Check whether Ollama + the model are available."""
    available = ollama_available()
    return jsonify({'available': available, 'model': LLAMA_MODEL})


@app.route('/api/chat', methods=['POST'])
def ai_chat():
    """Stream a chat response from Llama 3.2 via SSE."""
    if not ollama_available():
        return jsonify({'error': 'Ollama is not running or model not found'}), 503

    data = request.get_json()
    user_message = data.get('message', '').strip()
    context = data.get('context', {})
    history = data.get('history', [])

    if not user_message:
        return jsonify({'error': 'Empty message'}), 400

    # Build messages array for Ollama
    messages = [{'role': 'system', 'content': build_system_prompt(context)}]

    # Add conversation history (keep last 10 exchanges)
    for msg in history[-20:]:
        messages.append({
            'role': msg.get('role', 'user'),
            'content': msg.get('content', ''),
        })

    # Add current user message
    messages.append({'role': 'user', 'content': user_message})

    return Response(
        stream_with_context(stream_ollama_chat(messages)),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        },
    )


@app.route('/api/ai-search', methods=['POST'])
def ai_search():
    """Use Llama to interpret a free-text query and find the best matching movie title."""
    if not ollama_available():
        return jsonify({'error': 'Ollama is not running'}), 503

    data = request.get_json()
    query = data.get('query', '').strip()
    if not query:
        return jsonify({'error': 'Empty query'}), 400

    # Get a sample of movie titles for Llama to pick from
    all_titles = movies['title'].dropna().tolist()

    prompt = (
        f"The user is searching for a movie with this description: \"{query}\"\n\n"
        f"Here is a list of available movies in the database:\n"
        f"{json.dumps(all_titles[:500])}\n\n"
        "Based on the user's description, which ONE movie title from the list above "
        "is the best match? Reply with ONLY the exact movie title, nothing else. "
        "If no movie matches well, reply with 'NO_MATCH'."
    )

    try:
        r = requests.post(
            f'{OLLAMA_BASE}/api/chat',
            json={
                'model': LLAMA_MODEL,
                'messages': [
                    {'role': 'system', 'content': 'You are a movie matching assistant. Reply with only the movie title.'},
                    {'role': 'user', 'content': prompt},
                ],
                'stream': False,
            },
            timeout=60,
        )
        result = r.json()
        matched_title = result.get('message', {}).get('content', '').strip().strip('"\'')

        if matched_title and matched_title != 'NO_MATCH':
            # Verify it's actually in our dataset
            check = movies[movies['title'].str.lower() == matched_title.lower()]
            if not check.empty:
                return jsonify({'title': check.iloc[0]['title'], 'found': True})

        return jsonify({'title': None, 'found': False})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
