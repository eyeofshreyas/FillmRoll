from flask import Blueprint, request, jsonify, session
from db import save_review, get_movie_reviews, delete_review
from blueprints.auth import login_required

reviews_bp = Blueprint('reviews', __name__)

@reviews_bp.route('/api/reviews', methods=['POST'])
@login_required
def submit_review():
    data = request.get_json()
    user = session['user']
    movie_title = data.get('movie_title')
    movie_id = data.get('movie_id')
    rating = data.get('rating')
    comment = data.get('comment')
    
    if not all([movie_title, movie_id, rating, comment]):
        return jsonify({'error': 'Missing required fields'}), 400
        
    save_review(user['email'], user['name'], user['picture'], movie_title, movie_id, rating, comment)
    return jsonify({'status': 'success'})

@reviews_bp.route('/api/reviews/<movie_title>', methods=['GET'])
@login_required
def fetch_movie_reviews(movie_title):
    reviews = get_movie_reviews(movie_title)
    return jsonify(reviews)

@reviews_bp.route('/api/reviews/<review_id>', methods=['DELETE'])
@login_required
def delete_user_review(review_id):
    user = session['user']
    if delete_review(review_id, user['email']):
        return jsonify({'status': 'success'})
    return jsonify({'error': 'Not authorized or not found'}), 403
