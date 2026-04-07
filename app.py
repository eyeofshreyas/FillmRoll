import os
import pickle
import json
import numpy as np
import pandas as pd
import requests
from flask import (Flask, render_template, request, jsonify,
                   Response, stream_with_context,
                   session, redirect, url_for, flash)
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
load_dotenv()

from db import get_user_ratings, save_user_rating, save_last_mood

# ── Download similarity matrix from Hugging Face if not present ──
def download_similarity():
    similarity_path = 'similarity.pkl'
    if not os.path.exists(similarity_path):
        print("Downloading similarity.pkl from Hugging Face...")
        hf_token = os.environ.get('HF_TOKEN', '')
        url = 'https://huggingface.co/Shreyansh00700/FilmRoll/resolve/main/similarity.pkl'
        headers = {'Authorization': f'Bearer {hf_token}'} if hf_token else {}
        with requests.get(url, headers=headers, stream=True) as r:
            r.raise_for_status()
            with open(similarity_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print("Download complete.")

download_similarity()

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET', 'filmroll-dev-secret-change-in-prod')

# Trust Heroku's reverse proxy so OAuth re direct uses https://
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# ── Google OAuth config ──────────────────────────────────────
GOOGLE_CLIENT_ID     = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')

oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)

API_KEY  = 'ebef1aa0b639138c3040e6929ea9f1eb'
IMG_BASE = 'https://image.tmdb.org/t/p/w500'
TMDB_BASE = 'https://api.themoviedb.org/3'
SEARCH_MULTI_URL = f'{TMDB_BASE}/search/multi'

HF_TOKEN   = os.environ.get('HF_TOKEN', '')
HF_MODEL   = 'meta-llama/Meta-Llama-3.1-8B-Instruct'
HF_CHAT_URL = f'https://api-inference.huggingface.co/models/{HF_MODEL}/v1/chat/completions'

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
    data = tmdb_get('/search/multi', {'query': title})
    results = data.get('results', [])
    for result in results:
        if result.get('poster_path'):
            return IMG_BASE + result['poster_path']
    return None


def get_poster(poster_path, title=None):
    if is_valid_path(poster_path):
        return IMG_BASE + str(poster_path).strip()
    if title:
        live = fetch_poster_from_tmdb(title)
        if live:
            return live
    return 'https://via.placeholder.com/500x750/ede9e0/7a7060?text=No+Poster'


def get_item_id_from_row(row):
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


def build_item_dict(row, score=None):
    d = {
        'movie_id':   get_item_id_from_row(row),
        'media_type': row.get('media_type', 'movie'),
        'title':      row['title'],
        'poster':     get_poster(row.get('poster_path'), row['title']),
        'rating':     round(float(row.get('vote_average', 0)), 1),
        'overview':   row.get('overview', ''),
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

    return [build_item_dict(movies.iloc[i], score) for i, score in top_n if i < len(movies)]


# ── Ollama / Llama helpers ──────────────────────────────────────

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


# ── Auth helpers ──────────────────────────────────────────────

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user'):
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated


# ── Auth Routes ───────────────────────────────────────────────

@app.route('/login')
def login_page():
    if session.get('user'):
        return redirect(url_for('index'))
    return render_template('login.html')


@app.route('/auth/google')
def google_login():
    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)


@app.route('/auth/callback')
def google_callback():
    try:
        token = google.authorize_access_token()
        user_info = token.get('userinfo')
        if not user_info:
            user_info = google.userinfo()
        session['user'] = {
            'name':    user_info.get('name', ''),
            'email':   user_info.get('email', ''),
            'picture': user_info.get('picture', ''),
        }
        return redirect(url_for('index'))
    except Exception as e:
        flash('Sign-in failed. Please try again.')
        return redirect(url_for('login_page'))


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login_page'))




# ── Routes ────────────────────────────────────────────────────

@app.route('/')
@login_required
def index():
    movie_list = sorted(movies['title'].dropna().tolist())
    user = session.get('user', {})
    return render_template('index.html', movies=movie_list, user=user)


@app.route('/trending')
def trending():
    """Fetch trending movies and TV shows from TMDB for the homepage carousel."""
    try:
        data_movie = tmdb_get('/trending/movie/week')
        data_tv    = tmdb_get('/trending/tv/week')
        
        results_movie = data_movie.get('results', [])[:6]
        results_tv    = data_tv.get('results', [])[:6]
        
        results = results_movie + results_tv
        # pseudo-random mix
        results.sort(key=lambda x: x.get('popularity', 0), reverse=True)
        
        out = []
        for m in results:
            poster = IMG_BASE + m['poster_path'] if m.get('poster_path') else None
            title = m.get('title') or m.get('name', '')
            release_date = m.get('release_date') or m.get('first_air_date', '')
            out.append({
                'title':   title,
                'poster':  poster,
                'rating':  round(float(m.get('vote_average', 0)), 1),
                'year':    release_date[:4],
                'media_type': m.get('media_type', 'movie')
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
        selected = build_item_dict(movies.iloc[match.index[0]])

    return jsonify({'results': recs, 'selected': selected})


@app.route('/details', methods=['POST'])
def item_details():
    data       = request.get_json()
    item_id    = data.get('movie_id')  # legacy payload key from UI
    title      = data.get('title', '')
    media_type = data.get('media_type', 'movie')

    # If no stored id, search TMDB to get it
    if not item_id:
        search = tmdb_get('/search/multi', {'query': title})
        results = search.get('results', [])
        for r in results:
            if r.get('media_type') in ('movie', 'tv'):
                item_id = r['id']
                media_type = r['media_type']
                break

    if not item_id:
        return jsonify({'error': 'Not found'}), 404

    # ── Trailer ──────────────────────────────────────────────
    trailer_key = None
    videos = tmdb_get(f'/{media_type}/{item_id}/videos').get('results', [])

    # ── Cast ─────────────────────────────────────────────────
    credits = tmdb_get(f'/{media_type}/{item_id}/credits')

    # If both came back empty, the media_type may be wrong — try the other one
    if not videos and not credits.get('cast'):
        alt_type = 'tv' if media_type == 'movie' else 'movie'
        alt_videos  = tmdb_get(f'/{alt_type}/{item_id}/videos').get('results', [])
        alt_credits = tmdb_get(f'/{alt_type}/{item_id}/credits')
        if alt_videos or alt_credits.get('cast'):
            media_type = alt_type
            videos     = alt_videos
            credits    = alt_credits

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

    cast = []
    for c in credits.get('cast', [])[:8]:
        cast.append({
            'name':      c.get('name', ''),
            'character': c.get('character', ''),
            'photo':     IMG_BASE + c['profile_path'] if c.get('profile_path') else None,
        })

    # ── Extra details ─────────────────────────────────────────
    detail = tmdb_get(f'/{media_type}/{item_id}')
    genres = [g['name'] for g in detail.get('genres', [])]
    if media_type == 'movie':
        runtime = detail.get('runtime')
    else:
        run_times = detail.get('episode_run_time', [])
        runtime = run_times[0] if run_times else None
    tagline = detail.get('tagline', '')

    return jsonify({
        'trailer_key': trailer_key,
        'cast':        cast,
        'genres':      genres,
        'runtime':     runtime,
        'tagline':     tagline,
    })


# ── Ollama / AI Endpoints ────────────────────────────────────

@app.route('/api/ai-status')
def ai_status():
    """Check whether the HF AI service is configured."""
    return jsonify({'available': hf_available(), 'model': HF_MODEL})


@app.route('/api/chat', methods=['POST'])
def ai_chat():
    """Stream a chat response from Llama 3.1 via HF Inference API SSE."""
    if not hf_available():
        return jsonify({'error': 'HF_TOKEN is not configured'}), 503

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
        stream_with_context(stream_hf_chat(messages)),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        },
    )


@app.route('/api/ai-search', methods=['POST'])
def ai_search():
    """Use Llama via HF to interpret a free-text query and find the best matching movie title."""
    if not hf_available():
        return jsonify({'error': 'HF_TOKEN is not configured'}), 503

    data = request.get_json()
    query = data.get('query', '').strip()
    if not query:
        return jsonify({'error': 'Empty query'}), 400

    all_titles = movies['title'].dropna().tolist()

    prompt = (
        f"The user is searching for a movie or TV show with this description: \"{query}\"\n\n"
        f"Here is a list of available titles in the database:\n"
        f"{json.dumps(all_titles[:500])}\n\n"
        "Based on the user's description, which ONE title from the list above "
        "is the best match? Reply with ONLY the exact title, nothing else. "
        "If no title matches well, reply with 'NO_MATCH'."
    )

    try:
        r = requests.post(
            HF_CHAT_URL,
            headers={'Authorization': f'Bearer {HF_TOKEN}'},
            json={
                'model': HF_MODEL,
                'messages': [
                    {'role': 'system', 'content': 'You are a database matching assistant. Reply with only the movie or TV show title.'},
                    {'role': 'user', 'content': prompt},
                ],
                'stream': False,
                'max_tokens': 64,
            },
            timeout=30,
        )
        matched_title = r.json()['choices'][0]['message']['content'].strip().strip('"\'')

        if matched_title and matched_title != 'NO_MATCH':
            check = movies[movies['title'].str.lower() == matched_title.lower()]
            if not check.empty:
                return jsonify({'title': check.iloc[0]['title'], 'found': True})

        return jsonify({'title': None, 'found': False})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Mood → TMDB genre mapping ────────────────────────────────
MOOD_GENRES = {
    'happy':       [35, 10751, 16],   # Comedy, Family, Animation
    'excited':     [28, 12, 878],     # Action, Adventure, Sci-Fi
    'romantic':    [10749, 18],       # Romance, Drama
    'sad':         [18, 10749],       # Drama, Romance
    'scared':      [27, 53],          # Horror, Thriller
    'adventurous': [12, 14, 878],     # Adventure, Fantasy, Sci-Fi
    'curious':     [99, 36, 9648],    # Documentary, History, Mystery
    'chill':       [35, 16, 10402],   # Comedy, Animation, Music
}

# ── Genre slug → TMDB genre ID ───────────────────────────────
GENRE_IDS = {
    'action':      28,
    'animation':   16,
    'comedy':      35,
    'crime':       80,
    'documentary': 99,
    'drama':       18,
    'fantasy':     14,
    'horror':      27,
    'mystery':     9648,
    'romance':     10749,
    'scifi':       878,
    'thriller':    53,
}


def weighted_score(item):
    """Credibility-weighted score: vote_average × (vote_count / (vote_count + 5000)).
    Rewards films that are both well-rated AND have enough votes to be trustworthy.
    Films with few votes get pulled toward zero; films with 5k+ votes get their full rating.
    """
    avg = float(item.get('vote_average', 0))
    cnt = float(item.get('vote_count', 0))
    return avg * (cnt / (cnt + 5000))


def fetch_tmdb_discover(genre_ids, pages=3, min_votes=200):
    """Fetch movies from TMDB discover across multiple pages, deduped by id."""
    seen = set()
    items = []
    for page in range(1, pages + 1):
        result = tmdb_get('/discover/movie', {
            'with_genres': ','.join(map(str, genre_ids)),
            'sort_by': 'popularity.desc',
            'vote_count.gte': min_votes,
            'page': page,
        })
        for m in result.get('results', []):
            if m['id'] not in seen:
                seen.add(m['id'])
                items.append(m)
    return items


@app.route('/mood', methods=['POST'])
def mood_recommend():
    data = request.get_json()
    mood = data.get('mood', '').lower()
    n = int(data.get('n', 60))

    user_email = session.get('user', {}).get('email')
    if user_email and mood:
        save_last_mood(user_email, mood)

    genre_ids = MOOD_GENRES.get(mood)
    if not genre_ids:
        return jsonify({'error': 'Unknown mood'}), 400

    raw = fetch_tmdb_discover(genre_ids, pages=3, min_votes=300)
    raw.sort(key=weighted_score, reverse=True)

    items = []
    for m in raw[:n]:
        poster = IMG_BASE + m['poster_path'] if m.get('poster_path') else None
        items.append({
            'title':      m.get('title', ''),
            'poster':     poster,
            'rating':     round(float(m.get('vote_average', 0)), 1),
            'overview':   m.get('overview', ''),
            'movie_id':   m.get('id'),
            'media_type': 'movie',
            'score':      round(weighted_score(m) / 10, 3),
        })
    return jsonify({'results': items, 'mood': mood})


@app.route('/genre', methods=['POST'])
def genre_recommend():
    data = request.get_json()
    genre = data.get('genre', '').lower()
    n = int(data.get('n', 60))

    genre_id = GENRE_IDS.get(genre)
    if not genre_id:
        return jsonify({'error': 'Unknown genre'}), 400

    raw = fetch_tmdb_discover([genre_id], pages=3, min_votes=200)
    raw.sort(key=weighted_score, reverse=True)

    items = []
    for m in raw[:n]:
        poster = IMG_BASE + m['poster_path'] if m.get('poster_path') else None
        items.append({
            'title':      m.get('title', ''),
            'poster':     poster,
            'rating':     round(float(m.get('vote_average', 0)), 1),
            'overview':   m.get('overview', ''),
            'movie_id':   m.get('id'),
            'media_type': 'movie',
            'score':      round(weighted_score(m) / 10, 3),
        })
    return jsonify({'results': items, 'genre': genre})


@app.route('/rate', methods=['POST'])
def rate_movie():
    data = request.get_json()
    title = data.get('title', '')
    rating = int(data.get('rating', 0))
    if not title or not (1 <= rating <= 5):
        return jsonify({'error': 'Invalid rating'}), 400
        
    user_email = session.get('user', {}).get('email')
    if user_email:
        save_user_rating(user_email, title, rating)
        
    if 'ratings' not in session:
        session['ratings'] = {}
    session['ratings'][title] = rating
    session.modified = True
    
    return jsonify({'ok': True, 'total': len(session['ratings'])})

@app.route('/my-ratings')
def my_ratings():
    user_email = session.get('user', {}).get('email')
    if user_email and 'db_synced' not in session:
        session['ratings'] = get_user_ratings(user_email)
        session['db_synced'] = True
        session.modified = True
    return jsonify(session.get('ratings', {}))


@app.route('/cf-recommend', methods=['POST'])
def cf_recommend():
    """Weighted content-based collaborative filtering using session/DB ratings."""
    data = request.get_json()
    n = int(data.get('n', 8))

    user_email = session.get('user', {}).get('email')
    if user_email and 'db_synced' not in session:
        session['ratings'] = get_user_ratings(user_email)
        session['db_synced'] = True
        session.modified = True
        
    ratings = session.get('ratings', {})

    if not ratings:
        return jsonify({'results': [], 'message': 'Rate some movies first'})

    rated_lower = {t.lower() for t in ratings}
    combined = np.zeros(len(movies))

    for title, user_rating in ratings.items():
        match = movies[movies['title'].str.lower() == title.lower()]
        if match.empty:
            continue
        idx = match.index[0]
        combined += similarity[idx] * (user_rating / 5.0)

    # Zero out already-rated movies
    for title in ratings:
        match = movies[movies['title'].str.lower() == title.lower()]
        if not match.empty:
            combined[match.index[0]] = 0.0

    top_indices = np.argsort(combined)[::-1][:n]
    results = [
        build_item_dict(movies.iloc[int(i)], float(combined[i]))
        for i in top_indices if combined[i] > 0
    ]
    return jsonify({'results': results, 'rated_count': len(ratings)})


if __name__ == '__main__':
    app.run(debug=True)
