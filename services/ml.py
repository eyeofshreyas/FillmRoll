import os
import pickle
import numpy as np
import pandas as pd
from qdrant_client import QdrantClient

COLLECTION = 'filmroll_movies'

movies: pd.DataFrame | None = None
_qdrant: QdrantClient | None = None
_title_to_id: dict[str, int] = {}


def _client() -> QdrantClient:
    global _qdrant
    if _qdrant is None:
        _qdrant = QdrantClient(
            url=os.environ['QDRANT_URL'],
            api_key=os.environ.get('QDRANT_API_KEY', ''),
        )
    return _qdrant


def init_ml():
    global movies, _title_to_id
    movies_dict = pickle.load(open('movies_dict.pkl', 'rb'))
    movies = pd.DataFrame(movies_dict)
    _title_to_id = {str(t).lower(): i for i, t in enumerate(movies['title'])}
    _client()


def _lookup_id(title: str) -> int | None:
    return _title_to_id.get(title.lower())


def _row_to_dict(row, score=None):
    from services.tmdb import get_poster, get_item_id_from_row
    d = {
        'movie_id':     get_item_id_from_row(row),
        'media_type':   row.get('media_type', 'movie'),
        'title':        row['title'],
        'poster':       get_poster(row.get('poster_path'), row['title']),
        'rating':       round(float(row.get('vote_average', 0)), 1),
        'overview':     row.get('overview', ''),
        'release_date': row.get('release_date', '') or '',
    }
    if score is not None:
        d['score'] = round(float(score), 3)
    return d


def _payload_to_dict(payload: dict, score=None):
    from services.tmdb import get_poster
    d = {
        'movie_id':     payload.get('movie_id'),
        'media_type':   payload.get('media_type', 'movie'),
        'title':        payload.get('title', ''),
        'poster':       get_poster(payload.get('poster_path'), payload.get('title', '')),
        'rating':       round(float(payload.get('vote_average', 0)), 1),
        'overview':     payload.get('overview', ''),
        'release_date': payload.get('release_date', '') or '',
    }
    if score is not None:
        d['score'] = round(float(score), 3)
    return d


def get_movie_exact(title):
    if movies is None:
        init_ml()
    match = movies[movies['title'].str.lower() == title.lower()]
    if not match.empty:
        return _row_to_dict(movies.iloc[match.index[0]])
    return None


def recommend(movie_title, n=8):
    if movies is None:
        init_ml()
    point_id = _lookup_id(movie_title)
    if point_id is None:
        return []
    # Passing an int as query = "more like this" in the new query_points API
    results = _client().query_points(
        collection_name=COLLECTION,
        query=point_id,
        limit=n + 1,
        with_payload=True,
    ).points
    return [_payload_to_dict(r.payload, r.score) for r in results if r.id != point_id][:n]


def cf_recommend(ratings_dict, n=8):
    if movies is None:
        init_ml()
    if not ratings_dict:
        return []

    entries = [(title, _lookup_id(title), rating) for title, rating in ratings_dict.items()]
    entries = [(t, pid, r) for t, pid, r in entries if pid is not None]
    if not entries:
        return []

    # Batch-fetch all vectors in one round-trip
    all_ids = [pid for _, pid, _ in entries]
    pts = _client().retrieve(COLLECTION, ids=all_ids, with_vectors=True)
    id_to_vec = {p.id: p.vector for p in pts}

    query = np.zeros(5000, dtype=np.float32)
    for _, pid, rating in entries:
        vec = id_to_vec.get(pid)
        if vec is None:
            continue
        weight = rating / 5.0 if rating >= 3 else -0.3
        query += np.array(vec, dtype=np.float32) * weight

    norm = np.linalg.norm(query)
    if norm == 0:
        return []
    query /= norm

    exclude = {pid for _, pid, _ in entries}
    results = _client().query_points(
        collection_name=COLLECTION,
        query=query.tolist(),
        limit=n + len(exclude),
        with_payload=True,
    ).points
    filtered = [r for r in results if r.id not in exclude]
    return [_payload_to_dict(r.payload, r.score) for r in filtered[:n]]


def get_movie_by_exact_match(matched_title):
    if movies is None:
        init_ml()
    check = movies[movies['title'].str.lower() == matched_title.lower()]
    if not check.empty:
        return check.iloc[0]['title']
    return None


def get_movie_by_fuzzy_match(suggested_title):
    if movies is None:
        init_ml()
    match = movies[movies['title'].str.lower() == suggested_title.lower()]
    if match.empty:
        match = movies[
            movies['title'].str.lower().str.contains(
                suggested_title.lower(), na=False, regex=False
            )
        ]
    if not match.empty:
        return _row_to_dict(movies.iloc[match.index[0]])
    return None


def get_all_titles():
    if movies is None:
        init_ml()
    return sorted(movies['title'].dropna().tolist())


def init_app():
    init_ml()
