import os
import requests

API_KEY   = os.environ.get('TMDB_API_KEY', '')
IMG_BASE  = 'https://image.tmdb.org/t/p/w342'
LOGO_BASE = 'https://image.tmdb.org/t/p/w92'
TMDB_BASE = 'https://api.themoviedb.org/3'
SEARCH_MULTI_URL = f'{TMDB_BASE}/search/multi'

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
    return 'https://placehold.co/500x750/ede9e0/7a7060?text=No+Poster'

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

def weighted_score(item):
    """Credibility-weighted score: vote_average × (vote_count / (vote_count + 5000))."""
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
