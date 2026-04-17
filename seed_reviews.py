import os
import random
from datetime import datetime, timezone, timedelta
from db import init_firebase
from dotenv import load_dotenv

load_dotenv()

db = init_firebase()

movies = [
    {"title": "Interstellar", "id": 157336},
    {"title": "The Dark Knight", "id": 155},
    {"title": "Inception", "id": 27205},
    {"title": "Parasite", "id": 496243}
]

users = [
    {"name": "Alex R.", "pic": "https://api.dicebear.com/7.x/initials/svg?seed=Alex"},
    {"name": "Priya K.", "pic": "https://api.dicebear.com/7.x/initials/svg?seed=Priya"},
    {"name": "Jordan M.", "pic": "https://api.dicebear.com/7.x/initials/svg?seed=Jordan"},
    {"name": "Sam T.", "pic": "https://api.dicebear.com/7.x/initials/svg?seed=Sam"}
]

reviews = [
    "Absolutely blew my mind. The cinematography is out of this world.",
    "A solid 4 stars. Great pacing and engaging from start to finish.",
    "One of Nolan's best works. I still get chills thinking about the ending.",
    "A true cinematic masterpiece. The score alone is worth 5 stars.",
    "Good, but felt a bit slow in the second act. Still worth watching.",
    "Unbelievable visuals and deep storytelling. Love it."
]

def seed():
    if not db:
        print("Firebase not initialized.")
        return
        
    print("Seeding reviews...")
    count = 0
    for movie in movies:
        # Give each movie 2-4 reviews
        num_reviews = random.randint(2, 4)
        selected_users = random.sample(users, num_reviews)
        
        for u in selected_users:
            days_ago = random.randint(1, 30)
            created_at = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
            
            review_data = {
                'user_email': f"{u['name'].replace('.', '').replace(' ', '.').lower()}@example.com",
                'user_name': u['name'],
                'user_picture': u['pic'],
                'movie_title': movie['title'],
                'movie_id': movie['id'],
                'rating': random.choice([4, 5, 5, 4, 3, 5]),
                'comment': random.choice(reviews),
                'created_at': created_at,
                'likes': 0
            }
            db.collection('reviews').add(review_data)
            count += 1
            
    print(f"Successfully seeded {count} reviews.")

if __name__ == '__main__':
    seed()
