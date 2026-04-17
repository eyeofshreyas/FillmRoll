import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

core = open('blueprints/core.py', encoding='utf-8').read()
user = open('blueprints/user.py', encoding='utf-8').read()
ai   = open('blueprints/ai.py', encoding='utf-8').read()
rev  = open('blueprints/reviews.py', encoding='utf-8').read()

print("=== /trending return type ===")
i = core.index('def get_trending')
print(core[i:i+400][-150:])

print("\n=== /watchlist return type ===")
i = user.index('def get_user_watchlist')
print(user[i:i+200])

print("\n=== /my-ratings return type ===")
i = user.index('def my_ratings')
print(user[i:i+200])

print("\n=== cast 'photo' key in details ===")
print("'photo' in core.py:", "'photo'" in core)

print("\n=== reviews routes ===")
for line in rev.splitlines():
    if 'route' in line or 'def ' in line:
        print(line)

print("\n=== ai-search returns array? ===")
i = ai.index('def ai_search')
print(ai[i:i+400][-200:])
