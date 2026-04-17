import os
import sys
import json
import base64
import threading
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from dotenv import load_dotenv

load_dotenv()

_firebase_init_lock = threading.Lock()

def init_firebase():
    """Initialize Firebase App and return Firestore client."""
    # Fast check path
    if firebase_admin._apps:
        return firestore.client()

    with _firebase_init_lock:
        # Check again under lock to avoid race conditions
        if firebase_admin._apps:
            return firestore.client()

        # Try base64 encoded credentials (good for Heroku standard ENV vars)
        b64_creds = os.environ.get('FIREBASE_CREDENTIALS_BASE64')
        if b64_creds:
            try:
                # ''.join(...split()) removes ALL embedded whitespace (\n, \r, \t, spaces)
                # that appear when copy-pasting base64 into Heroku config vars.
                # Plain .strip() only handles leading/trailing whitespace.
                b64_creds = ''.join(b64_creds.split())
                b64_creds = b64_creds.strip('"\'')
                dict_creds = json.loads(base64.b64decode(b64_creds).decode('utf-8'))
                
                # FIX: Heroku/env var JSON often double-escapes newlines in the private key,
                # OR users accidentally strip the newlines completely when creating the Base64 string.
                if 'private_key' in dict_creds:
                    key = dict_creds['private_key']
                    if '-----BEGIN PRIVATE KEY-----' in key:
                        middle = key.replace('-----BEGIN PRIVATE KEY-----', '').replace('-----END PRIVATE KEY-----', '')
                        middle = middle.replace('\\n', '').replace('\n', '')
                        middle = ''.join(middle.split()) # Strip all whitespace/newlines from the actual payload
                        # Chunk into 64 character lines to strictly comply with PEM standards
                        chunks = [middle[i:i+64] for i in range(0, len(middle), 64)]
                        formatted_middle = '\n'.join(chunks)
                        # Reconstruct a perfectly compliant PEM format
                        dict_creds['private_key'] = f"-----BEGIN PRIVATE KEY-----\n{formatted_middle}\n-----END PRIVATE KEY-----\n"
                        
                
                cred = credentials.Certificate(dict_creds)
                if not firebase_admin._apps:
                    firebase_admin.initialize_app(cred)
                return firestore.client()
            except Exception as e:
                print(
                    f"[Firebase] WARNING: Base64 credentials failed ({type(e).__name__}: {e}). "
                    f"Falling back to local file.",
                    file=sys.stderr
                )
                # Fall through to local file fallback below

        # Fallback to local file
        cred_path = os.environ.get('FIREBASE_CREDENTIALS', 'firebase-credentials.json')
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            if not firebase_admin._apps:
                firebase_admin.initialize_app(cred)
            return firestore.client()
        else:
            if os.environ.get('FIREBASE_CREDENTIALS_BASE64'):
                # Had base64 creds but they failed AND no local file — fatal in production
                raise RuntimeError(
                    "FATAL FIREBASE ERROR: Base64 credentials are invalid and no local "
                    "firebase-credentials.json found. Check FIREBASE_CREDENTIALS_BASE64."
                )
            print("[Firebase] WARNING: No credentials found. Set FIREBASE_CREDENTIALS_BASE64 env var.", file=sys.stderr)
            return None

def get_user_ratings(email):
    """Retrieve all ratings for a given user email."""
    db = init_firebase()
    if not db or not email:
        return {}
    try:
        doc = db.collection('users').document(email).get()
        if doc.exists:
            return doc.to_dict().get('ratings', {})
    except Exception as e:
        print(f"Firebase read error: {e}")
    return {}

def save_user_rating(email, title, rating):
    """Save or update a specific rating for a user."""
    db = init_firebase()
    if not db or not email:
        return False
    try:
        db.collection('users').document(email).set({
            'ratings': {title: rating}
        }, merge=True)
        return True
    except Exception as e:
        print(f"Firebase write error: {e}")
        return False

def save_last_mood(email, mood):
    """Save the user's last requested mood."""
    db = init_firebase()
    if not db or not email:
        return False
    try:
        db.collection('users').document(email).set({
            'last_mood': mood
        }, merge=True)
        return True
    except Exception as e:
        print(f"Firebase write error: {e}")
        return False

def get_watchlist(email):
    """Return watchlist as a list of item dicts, sorted newest-first."""
    db = init_firebase()
    if not db or not email:
        return []
    try:
        doc = db.collection('users').document(email).get()
        if doc.exists:
            wl = doc.to_dict().get('watchlist', {})
            items = list(wl.values())
            items.sort(key=lambda x: x.get('added_at', ''), reverse=True)
            return items
    except Exception as e:
        print(f"Firebase watchlist read error: {e}")
    return []


def add_to_watchlist(email, item):
    """Add a movie to the watchlist map, keyed by str(movie_id)."""
    db = init_firebase()
    if not db or not email:
        return False
    try:
        key = str(item['movie_id'])
        db.collection('users').document(email).set(
            {'watchlist': {key: item}}, merge=True
        )
        return True
    except Exception as e:
        print(f"Firebase watchlist add error: {e}")
        return False


def remove_from_watchlist(email, movie_id):
    """Remove a movie from the watchlist map by movie_id."""
    db = init_firebase()
    if not db or not email:
        return False
    try:
        key = f'watchlist.{movie_id}'
        db.collection('users').document(email).update(
            {key: firestore.DELETE_FIELD}
        )
        return True
    except Exception as e:
        print(f"Firebase watchlist remove error: {e}")
        return False

def save_review(email, name, picture, movie_title, movie_id, rating, comment):
    """Save a review document to the reviews collection and upsert the rating."""
    db = init_firebase()
    if not db or not email:
        return False
    try:
        save_user_rating(email, movie_title, rating)
        
        from datetime import datetime, timezone
        review_data = {
            'user_email': email,
            'user_name': name,
            'user_picture': picture,
            'movie_title': movie_title,
            'movie_id': movie_id,
            'rating': rating,
            'comment': comment,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'likes': 0
        }
        db.collection('reviews').add(review_data)
        return True
    except Exception as e:
        print(f"Firebase review save error: {e}")
        return False

def get_movie_reviews(movie_title, limit=20):
    """Fetch all reviews for a specific movie, newest first."""
    db = init_firebase()
    if not db:
        return []
    try:
        docs = db.collection('reviews') \
                 .where(filter=FieldFilter('movie_title', '==', movie_title)) \
                 .limit(limit) \
                 .stream()
        reviews = [{'id': doc.id, **doc.to_dict()} for doc in docs]
        # Sort in Python to avoid needing a Firestore composite index
        reviews.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return reviews
    except Exception as e:
        print(f"Firebase reviews get error: {e}")
        return []

def delete_review(review_id, email):
    """Let a user delete their own review."""
    db = init_firebase()
    if not db:
        return False
    try:
        doc_ref = db.collection('reviews').document(review_id)
        doc = doc_ref.get()
        if doc.exists and doc.to_dict().get('user_email') == email:
            doc_ref.delete()
            return True
    except Exception as e:
        print(f"Firebase review delete error: {e}")
    return False
