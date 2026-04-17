"""
Comprehensive static code audit: cross-references every JS fetch call
with backend blueprints, checks response shapes, and flags mismatches.
"""
import re, ast, os

ROOT = r"d:\TE BOOKS\Praticals\DSBDA\MOVIE REOCOMDATION SYSTEM"
JS   = os.path.join(ROOT, "static", "scripts.js")
BP   = os.path.join(ROOT, "blueprints")

js_text = open(JS, encoding="utf-8").read()
js_lines = js_text.splitlines()

# ── 1. All JS fetch() calls with method + URL ───────────────────────────────
print("=" * 60)
print("JS FETCH CALLS vs BACKEND ROUTES")
print("=" * 60)

bp_routes = {}
for fn in sorted(os.listdir(BP)):
    if not fn.endswith(".py"): continue
    txt = open(os.path.join(BP, fn), encoding="utf-8").read()
    for m in re.finditer(r"@\w+_bp\.route\('([^']+)'[^)]*(?:methods=\[([^\]]+)\])?", txt):
        route = m.group(1)
        methods_raw = m.group(2) or "'GET'"
        methods = [x.strip().strip("'\"") for x in methods_raw.split(",")]
        bp_routes[route] = (fn, methods)

all_ok = True
for m in re.finditer(r"fetch\('(/[^'?]+)", js_text):
    url = m.group(1)
    ctx = js_text[m.start():m.start()+250]
    meth_m = re.search(r"method:\s*'([^']+)'", ctx)
    meth = meth_m.group(1) if meth_m else "GET"

    # Dynamic URLs e.g. /api/reviews/TITLE  →  /api/reviews/<movie_title>
    normalized = re.sub(r"/[^/]+$", "/<x>", url)
    found = url in bp_routes or any(
        re.sub(r"<[^>]+>", "<x>", r) == normalized or r == url
        for r in bp_routes
    )
    status = "✅" if found else "❌ MISSING"
    if not found:
        all_ok = False
    print(f"  [{meth:6}] {url:35} {status}")

# ── 2. Check response shape for key endpoints ────────────────────────────────
print()
print("=" * 60)
print("RESPONSE SHAPE CHECKS")
print("=" * 60)

checks = [
    # (endpoint, JS reads key, blueprint file, python returns key)
    ("/recommend",      "data.results",           "core.py",    "results"),
    ("/recommend",      "data.selected",          "core.py",    "selected"),
    ("/trending",       "list (array)",            "core.py",    "array direct"),
    ("/genre",          "data.results",           "core.py",    "results"),
    ("/mood",           "data.results",           "core.py",    "results"),
    ("/cf-recommend",   "data.results",           "user.py",    "results"),
    ("/watchlist",      "array",                  "user.py",    "array direct"),
    ("/my-ratings",     "dict",                   "user.py",    "dict direct"),
    ("/details",        "det.watch_providers",    "core.py",    "watch_providers"),
    ("/details",        "det.cast[].photo",       "core.py",    "cast[].photo"),
    ("/details",        "det.genres",             "core.py",    "genres"),
    ("/details",        "det.runtime",            "core.py",    "runtime"),
    ("/details",        "det.tagline",            "core.py",    "tagline"),
    ("/details",        "det.trailer_key",        "core.py",    "trailer_key"),
    ("/api/reviews/X",  "array of {id,...}",      "reviews.py", "array"),
    ("/api/ai-status",  "res.available",          "ai.py",      "available"),
    ("/api/chat",       "SSE stream",             "ai.py",      "stream"),
    ("/api/why-you-like","data.blurb",            "ai.py",      "blurb"),
    ("/api/matchmaker", "res.reason/title",       "ai.py",      "in_catalog/title/reason"),
    ("/api/ai-search",  "array of movie dicts",   "ai.py",      "array"),
]

# Verify key fields in JS match backend code
for endpoint, js_key, bp_file, py_key in checks:
    bp_path = os.path.join(BP, bp_file)
    bp_txt  = open(bp_path, encoding="utf-8").read()
    # Check python returns the expected key
    found_in_bp = py_key.replace("[]", "").replace(".", "").split("/")[0] in bp_txt
    print(f"  {endpoint:20} JS reads [{js_key:30}]  →  {'✅' if found_in_bp else '❌ CHECK BACKEND'}")

# ── 3. Check openModal resets ────────────────────────────────────────────────
print()
print("=" * 60)
print("MODAL STATE RESET CHECKS")
print("=" * 60)

resets = [
    ("cast-row",        "cast-row.innerHTML = ''"),
    ("providers-groups","providers-groups.innerHTML = ''"),
    ("modal-providers", "modal-providers style display = none"),
    ("modal-chips",     "modal-chips.innerHTML"),
    ("modal-trailer",   "modal-trailer.innerHTML"),
    ("modal-tagline",   "modal-tagline.textContent"),
]

for elem, desc in resets:
    found = elem in js_text and (
        f"$('{elem}').innerHTML = ''" in js_text or
        f"$('{elem}').style.display = 'none'" in js_text or
        f"$('{elem}').textContent = ''" in js_text or
        f"$('{elem}').innerHTML =" in js_text
    )
    print(f"  Reset #{elem:25}  {'✅' if found else '❌ NOT RESET'}")

print()
if all_ok:
    print("All JS fetch URLs have matching routes ✅")
else:
    print("Some routes MISSING ❌ — see above")
