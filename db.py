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
