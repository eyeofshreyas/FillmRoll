import re

# Collect all blueprint routes
routes = {}
for fn in ['blueprints/auth.py','blueprints/core.py','blueprints/user.py','blueprints/ai.py','blueprints/reviews.py']:
    text = open(fn, encoding='utf-8').read()
    for m in re.finditer(r"@\w+_bp\.route\('([^']+)'[^)]*methods=\[([^\]]+)\]", text, re.DOTALL):
        route, methods_raw = m.group(1), m.group(2)
        methods = [x.strip().strip("'\"") for x in methods_raw.split(',')]
        routes[route] = methods
    for m in re.finditer(r"@\w+_bp\.route\('([^']+)'\)\s*\n", text):
        if m.group(1) not in routes:
            routes[m.group(1)] = ['GET']

print('=== REGISTERED ROUTES ===')
for r, ms in sorted(routes.items()):
    print(f'  {ms} {r}')

# Collect all JS fetch calls
js = open('static/scripts.js', encoding='utf-8').read()

print()
print('=== JS FETCH CALLS ===')
mismatches = []
for m in re.finditer(r"fetch\('(/[^'?]+)", js):
    url = m.group(1)
    ctx = js[m.start():m.start()+300]
    meth_m = re.search(r"method:\s*'([^']+)'", ctx)
    meth = meth_m.group(1) if meth_m else 'GET'
    
    # Normalize dynamic URLs like /api/reviews/XXX
    url_norm = re.sub(r'/[0-9a-f-]{8,}$', '/<id>', url)
    url_norm = re.sub(r'/[A-Z][^/]+$', '/<title>', url_norm) if url_norm not in routes else url_norm
    
    matched = url in routes or url_norm in routes
    status = 'OK' if matched else 'MISSING'
    if not matched:
        mismatches.append((meth, url))
    print(f'  [{meth}] {url}  =>  {status}')

if mismatches:
    print()
    print('=== MISSING/BROKEN ROUTES ===')
    for meth, url in mismatches:
        print(f'  [{meth}] {url}')
else:
    print()
    print('All JS fetch URLs have matching blueprint routes!')
