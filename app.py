import pickle
import pandas as pd
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

API_KEY  = 'ebef1aa0b639138c3040e6929ea9f1eb'
IMG_BASE = 'https://image.tmdb.org/t/p/w500'
TMDB_BASE = 'https://api.themoviedb.org/3'
SEARCH_URL = f'{TMDB_BASE}/search/movie'

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


if __name__ == '__main__':
    app.run(debug=True)
