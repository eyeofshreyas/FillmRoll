import os
from flask import Flask
from dotenv import load_dotenv

load_dotenv()

# We need to initialize the app first
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET') or os.environ.get('SECRET_KEY', 'development_key_only')

# Initialize extensions (OAuth)
from extensions import init_oauth
init_oauth(app)

# Initialize Firebase
from db import init_firebase
init_firebase()

# Initialize ML models
from services.ml import init_app as init_ml_service
init_ml_service()

# Register Blueprints
from blueprints.auth import auth_bp
from blueprints.core import core_bp
from blueprints.ai import ai_bp
from blueprints.user import user_bp
from blueprints.reviews import reviews_bp

app.register_blueprint(auth_bp)
app.register_blueprint(core_bp)
app.register_blueprint(ai_bp)
app.register_blueprint(user_bp)
app.register_blueprint(reviews_bp)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    # Use 'stat' reloader to avoid watchdog scanning site-packages on every request
    app.run(host='0.0.0.0', port=port, debug=True, reloader_type='stat')
