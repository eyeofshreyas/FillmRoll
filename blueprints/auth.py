import logging
from flask import Blueprint, redirect, url_for, session, render_template, flash
from extensions import oauth

log = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user'):
            return redirect(url_for('auth.login_page'))
        return f(*args, **kwargs)
    return decorated

@auth_bp.route('/login')
def login_page():
    if session.get('user'):
        return redirect(url_for('core.index'))
    return render_template('login.html')

@auth_bp.route('/auth/google')
def google_login():
    redirect_uri = url_for('auth.google_callback', _external=True)
    print(f'[OAuth] redirect_uri = {redirect_uri}', flush=True)
    return oauth.google.authorize_redirect(redirect_uri)

@auth_bp.route('/auth/callback')
def google_callback():
    try:
        token = oauth.google.authorize_access_token()
        user_info = token.get('userinfo')
        if not user_info:
            user_info = oauth.google.userinfo()
        session['user'] = {
            'name':    user_info.get('name', ''),
            'email':   user_info.get('email', ''),
            'picture': user_info.get('picture', ''),
        }
        return redirect(url_for('core.index'))
    except Exception as e:
        log.error('OAuth callback failed: %s', e, exc_info=True)
        flash(f'Sign-in failed: {e}')
        return redirect(url_for('auth.login_page'))

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login_page'))
