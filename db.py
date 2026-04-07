import os
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
                dict_creds = json.loads(base64.b64decode(b64_creds).decode('utf-8'))
                cred = credentials.Certificate(dict_creds)
                firebase_admin.initialize_app(cred)
                return firestore.client()
            except Exception as e:
                print(f"Error loading base64 Firebase creds: {e}")

        # Fallback to local file
        cred_path = os.environ.get('FIREBASE_CREDENTIALS', 'firebase-credentials.json')
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            return firestore.client()
        else:
            print("WARNING: Firebase credentials not found. DB calls will be skipped. Ensure you set FIREBASE_CREDENTIALS_BASE64 env var or provide firebase-credentials.json.")
            return None
    
    return firestore.client()

def get_user_ratings(email):
    """Retrieve all ratings for a given user email."""
    db = init_firebase()
    if not db or not email:
        return {}
    try:
        doc = db.collection('users').document(email).get(timeout=3.0)
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
        }, merge=True, timeout=3.0)
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
        }, merge=True, timeout=3.0)
        return True
    except Exception as e:
        print(f"Firebase write error: {e}")
        return False
