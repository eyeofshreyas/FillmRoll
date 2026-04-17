import os
import pickle
import pandas as pd
import numpy as np
import requests

movies = None
similarity = None

def init_ml():
    global movies, similarity
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
        
    movies_dict = pickle.load(open('movies_dict.pkl', 'rb'))
    similarity  = pickle.load(open('similarity.pkl',  'rb'))
    movies      = pd.DataFrame(movies_dict)

def build_item_dict(row, score=None):
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

def get_movie_exact(title):
    if movies is None: init_ml()
    match = movies[movies['title'].str.lower() == title.lower()]
    if not match.empty:
        return build_item_dict(movies.iloc[match.index[0]])
    return None

def recommend(movie_title, n=8):
    if movies is None: init_ml()
    match = movies[movies['title'].str.lower() == movie_title.lower()]
    if match.empty:
        return []

    idx       = match.index[0]
    distances = similarity[idx]
    top_n     = sorted(enumerate(distances), key=lambda x: x[1], reverse=True)[1:n + 1]

    return [build_item_dict(movies.iloc[i], score) for i, score in top_n if i < len(movies)]

def cf_recommend(ratings_dict, n=8):
    if movies is None: init_ml()
    if not ratings_dict: return []
    
    combined = np.zeros(len(movies))

    for title, user_rating in ratings_dict.items():
        match = movies[movies['title'].str.lower() == title.lower()]
        if match.empty:
            continue
        idx = match.index[0]
        combined += similarity[idx] * (user_rating / 5.0)

    # Zero out already-rated movies
    for title in ratings_dict:
        match = movies[movies['title'].str.lower() == title.lower()]
        if not match.empty:
            combined[match.index[0]] = 0.0

    top_indices = np.argsort(combined)[::-1][:n]
    results = [
        build_item_dict(movies.iloc[int(i)], float(combined[i]))
        for i in top_indices if combined[i] > 0
    ]
    return results

def get_movie_by_exact_match(matched_title):
    if movies is None: init_ml()
    check = movies[movies['title'].str.lower() == matched_title.lower()]
    if not check.empty:
        return check.iloc[0]['title']
    return None

def get_movie_by_fuzzy_match(suggested_title):
    if movies is None: init_ml()
    match = movies[movies['title'].str.lower() == suggested_title.lower()]
    if match.empty:
        match = movies[
            movies['title'].str.lower().str.contains(
                suggested_title.lower(), na=False, regex=False
            )
        ]
    if not match.empty:
        return build_item_dict(movies.iloc[match.index[0]])
    return None

def get_all_titles():
    if movies is None: init_ml()
    return sorted(movies['title'].dropna().tolist())

# Initialization hook called by app.py
def init_app():
    init_ml()
