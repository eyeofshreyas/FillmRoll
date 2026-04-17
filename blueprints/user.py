from flask import Blueprint, request, jsonify, session
from services.ml import cf_recommend
from db import save_user_rating, get_user_ratings, add_to_watchlist, remove_from_watchlist, get_watchlist
from blueprints.auth import login_required
import datetime

user_bp = Blueprint('user', __name__)

@user_bp.route('/rate', methods=['POST'])
@login_required
def rate_movie():
    data = request.get_json()
    title = data.get('title')
    rating = data.get('rating')
    email = session['user']['email']

    if title and rating:
        save_user_rating(email, title, rating)
        return jsonify({'status': 'success'})
    return jsonify({'error': 'Invalid data'}), 400

@user_bp.route('/my-ratings', methods=['GET'])
@login_required
def my_ratings():
    email = session['user']['email']
    ratings = get_user_ratings(email)
    return jsonify(ratings)

@user_bp.route('/cf-recommend', methods=['POST'])
@login_required
def do_cf_recommend():
    data = request.get_json()
    n = int(data.get('n', 8) if data else 8)
    email = session['user']['email']
    ratings = get_user_ratings(email)
    
    if not ratings:
        return jsonify({'results': [], 'message': 'Rate some movies first'})
        
    res = cf_recommend(ratings, n=n)
    return jsonify({'results': res})

@user_bp.route('/watchlist', methods=['GET'])
@login_required
def get_user_watchlist():
    email = session['user']['email']
    items = get_watchlist(email)
    return jsonify(items)

@user_bp.route('/watchlist/add', methods=['POST'])
@login_required
def add_watchlist_item():
    email = session['user']['email']
    data = request.get_json()
    if not data or not data.get('movie_id'):
        return jsonify({'error': 'Invalid data'}), 400
    
    item = {
        'movie_id':   data['movie_id'],
        'title':      data.get('title', 'Unknown'),
        'poster':     data.get('poster', ''),
        'media_type': data.get('media_type', 'movie'),
        'rating':     data.get('rating', 0),
        'added_at':   datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    
    add_to_watchlist(email, item)
    return jsonify({'status': 'success'})

@user_bp.route('/watchlist/remove', methods=['POST'])
@login_required
def remove_watchlist_item():
    email = session['user']['email']
    data = request.get_json()
    if not data or not data.get('movie_id'):
        return jsonify({'error': 'Invalid data'}), 400
    
    remove_from_watchlist(email, data['movie_id'])
    return jsonify({'status': 'success'})
