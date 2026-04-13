import os
import sys
import json
import base64
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()

def init_firebase():
    """Initialize Firebase App and return Firestore client."""
    if not firebase_admin._apps:
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
                firebase_admin.initialize_app(cred)
                return firestore.client()
            except Exception as e:
                raise RuntimeError(
                    f"FATAL FIREBASE ERROR: {type(e).__name__}: {e} | "
                    f"Prefix: {repr(os.environ.get('FIREBASE_CREDENTIALS_BASE64', '')[:50])}"
                )

        # Fallback to local file
        cred_path = os.environ.get('FIREBASE_CREDENTIALS', 'firebase-credentials.json')
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            return firestore.client()
        else:
            print("[Firebase] WARNING: No credentials found. Set FIREBASE_CREDENTIALS_BASE64 env var.", file=sys.stderr)
            return None
    
    return firestore.client()

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
