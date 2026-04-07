import time
import os
try:
    from db import init_firebase, get_user_ratings
    print("Testing Firebase connection...")
    
    t0 = time.time()
    db = init_firebase()
    t1 = time.time()
    print(f"init_firebase() took {t1-t0:.2f}s")
    
    t0 = time.time()
    # Replace email with a test email or random string
    res = get_user_ratings("test@example.com")
    t1 = time.time()
    print(f"get_user_ratings() took {t1-t0:.2f}s, result: {res}")
    
except Exception as e:
    print(f"Error: {e}")
