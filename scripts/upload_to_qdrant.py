"""
One-time script: upload movie vectors to Qdrant Cloud.

Run from the project root after re-running the notebook:
    python scripts/upload_to_qdrant.py

Required env vars:
    QDRANT_URL      — e.g. https://xyz.us-east-1-0.aws.cloud.qdrant.io:6333
    QDRANT_API_KEY  — Qdrant Cloud API key
"""
import os
import pickle
import sys
import numpy as np
import pandas as pd
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

COLLECTION = 'filmroll_movies'
BATCH_SIZE = 50


def main():
    qdrant_url = os.environ.get('QDRANT_URL')
    qdrant_key = os.environ.get('QDRANT_API_KEY', '')
    if not qdrant_url:
        sys.exit('Set QDRANT_URL before running this script.')

    print('Loading movies_dict.pkl ...')
    movies = pd.DataFrame(pickle.load(open('movies_dict.pkl', 'rb')))

    print('Loading vectors.pkl ...')
    vectors: np.ndarray = pickle.load(open('vectors.pkl', 'rb'))

    if len(movies) != len(vectors):
        sys.exit(f'Row count mismatch: {len(movies)} movies vs {len(vectors)} vectors')

    vector_size = vectors.shape[1]
    print(f'{len(movies)} movies | vector dim {vector_size}')

    client = QdrantClient(url=qdrant_url, api_key=qdrant_key, timeout=120)

    print(f'Recreating collection "{COLLECTION}" ...')
    client.recreate_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
    )

    total = len(movies)
    for start in range(0, total, BATCH_SIZE):
        end = min(start + BATCH_SIZE, total)
        batch = movies.iloc[start:end]

        points = []
        for idx, row in batch.iterrows():
            mid = row.get('movie_id')
            try:
                mid = int(float(str(mid))) if str(mid) not in ('', 'nan', 'None') else None
            except (ValueError, TypeError):
                mid = None

            payload = {
                'title':        str(row.get('title', '')),
                'movie_id':     mid,
                'media_type':   str(row.get('media_type', 'movie')),
                'overview':     str(row.get('overview', '')),
                'poster_path':  str(row.get('poster_path', '')),
                'vote_average': float(row.get('vote_average', 0)),
            }
            points.append(PointStruct(
                id=int(idx),
                vector=vectors[idx].tolist(),
                payload=payload,
            ))

        client.upsert(collection_name=COLLECTION, points=points)
        print(f'  uploaded {end}/{total}', end='\r')

    print(f'\nDone — {total} points in "{COLLECTION}".')


if __name__ == '__main__':
    main()
