from flask import Blueprint, session, jsonify, request, render_template
import random
import html as _html
from concurrent.futures import ThreadPoolExecutor, as_completed
from services.tmdb import tmdb_get, fetch_tmdb_discover
from services.ml import recommend, get_movie_exact, get_all_titles
from services import cache
from blueprints.auth import login_required

core_bp = Blueprint('core', __name__)

# Built once at first request, reused for the dyno's lifetime
_movie_options_cache: str | None = None

@core_bp.route('/')
@login_required
def index():
    global _movie_options_cache
    if _movie_options_cache is None:
        movie_list = get_all_titles()
        _movie_options_cache = ''.join(f'<option value="{_html.escape(m)}">' for m in movie_list)
    return render_template('index.html', movie_options=_movie_options_cache, user=session.get('user'))

@core_bp.route('/recommend', methods=['POST'])
@login_required
def do_recommend():
    data = request.get_json()
    movie = data.get('title', '').strip()
    if not movie:
        return jsonify({'error': 'No title provided'}), 400
    
    from services.ml import get_movie_by_fuzzy_match
    selected = get_movie_by_fuzzy_match(movie)
    if not selected:
        return jsonify({'selected': None, 'results': []})
        
    res = recommend(selected['title'], n=12)
    return jsonify({
        'selected': selected,
        'results': res
    })

@core_bp.route('/new-releases', methods=['GET'])
@login_required
def get_new_releases():
    cached = cache.get('new-releases')
    if cached is not None:
        return jsonify(cached)
    results = _build_new_releases()
    cache.set('new-releases', results, ttl=1800)
    return jsonify(results)

@core_bp.route('/home-data', methods=['GET'])
@login_required
def home_data():
    """Return trending + new-releases in one round-trip, fetching in parallel if uncached."""
    trending_cached    = cache.get('trending')
    new_releases_cached = cache.get('new-releases')

    if trending_cached is not None and new_releases_cached is not None:
        return jsonify({'trending': trending_cached, 'new_releases': new_releases_cached})

    with ThreadPoolExecutor(max_workers=2) as ex:
        fut_t  = ex.submit(_build_trending)     if trending_cached    is None else None
        fut_nr = ex.submit(_build_new_releases) if new_releases_cached is None else None
        trending    = fut_t.result()  if fut_t  else trending_cached
        new_releases = fut_nr.result() if fut_nr else new_releases_cached

    cache.set('trending',     trending,     ttl=1800)
    cache.set('new-releases', new_releases, ttl=1800)
    return jsonify({'trending': trending, 'new_releases': new_releases})

def _build_trending():
    from services.tmdb import get_poster, get_item_id_from_row
    data = tmdb_get('/trending/movie/week')
    filtered = []
    for r in data.get('results', []):
        filtered.append({
            'movie_id':     get_item_id_from_row(r),
            'title':        r.get('title') or r.get('name', 'Unknown'),
            'poster':       get_poster(r.get('poster_path')),
            'rating':       round(float(r.get('vote_average', 0)), 1),
            'overview':     r.get('overview', ''),
            'release_date': r.get('release_date', '') or r.get('first_air_date', ''),
        })
        if len(filtered) == 12:
            break
    return filtered

def _build_new_releases():
    from datetime import date, timedelta
    from services.tmdb import get_poster, get_item_id_from_row
    today = date.today()
    thirty_days_ago = today - timedelta(days=30)
    data = tmdb_get('/discover/movie', {
        'primary_release_date.gte': thirty_days_ago.isoformat(),
        'primary_release_date.lte': today.isoformat(),
        'sort_by': 'popularity.desc',
        'vote_count.gte': 10,
    })
    results = []
    for r in data.get('results', []):
        results.append({
            'movie_id':     get_item_id_from_row(r),
            'title':        r.get('title') or r.get('name', 'Unknown'),
            'poster':       get_poster(r.get('poster_path')),
            'rating':       round(float(r.get('vote_average', 0)), 1),
            'overview':     r.get('overview', ''),
            'release_date': r.get('release_date', ''),
        })
        if len(results) == 12:
            break
    return results

@core_bp.route('/trending', methods=['GET'])
@login_required
def get_trending():
    cached = cache.get('trending')
    if cached is not None:
        return jsonify(cached)
    filtered = _build_trending()
    cache.set('trending', filtered, ttl=1800)
    return jsonify(filtered)

GENRE_IDS = {
    'action':      28,
    'animation':   16,
    'comedy':      35,
    'crime':       80,
    'documentary': 99,
    'drama':       18,
    'fantasy':     14,
    'horror':      27,
    'mystery':     9648,
    'romance':     10749,
    'scifi':       878,
    'thriller':    53,
}

@core_bp.route('/genre', methods=['POST'])
@login_required
def get_by_genre():
    data = request.get_json()
    genre_key = str(data.get('genre', '')).lower().strip()
    if not genre_key:
        return jsonify({'results': []})

    # Accept either a genre name string OR a numeric TMDB id
    if genre_key.isdigit():
        gid = int(genre_key)
    else:
        gid = GENRE_IDS.get(genre_key)
        if not gid:
            return jsonify({'results': []})

    try:
        results = fetch_tmdb_discover([gid], pages=2, min_votes=300)
        from services.tmdb import weighted_score, get_poster, get_item_id_from_row
        results = sorted(results, key=lambda x: weighted_score(x), reverse=True)[:18]
        filtered = [{
            'movie_id':     get_item_id_from_row(r),
            'title':        r.get('title') or r.get('name', 'Unknown'),
            'poster':       get_poster(r.get('poster_path')),
            'rating':       round(float(r.get('vote_average', 0)), 1),
            'overview':     r.get('overview', ''),
            'score':        round(weighted_score(r), 3),
            'release_date': r.get('release_date', '') or r.get('first_air_date', ''),
        } for r in results]
        return jsonify({'results': filtered})
    except Exception as e:
        return jsonify({'results': [], 'error': str(e)})

# Mood → TMDB genre IDs  (keys match what the HTML onclick sends)
MOOD_GENRES = {
    'happy':       [35, 10751],          # Comedy, Family
    'excited':     [28, 12, 53],         # Action, Adventure, Thriller
    'romantic':    [10749, 35],          # Romance, Comedy
    'sad':         [18, 10749],          # Drama, Romance
    'scared':      [27, 53],             # Horror, Thriller
    'adventurous': [12, 28, 14],         # Adventure, Action, Fantasy
    'curious':     [9648, 99, 878],      # Mystery, Documentary, Sci-Fi
    'chill':       [35, 16, 10751],      # Comedy, Animation, Family
}

@core_bp.route('/mood', methods=['POST'])
@login_required
def get_by_mood():
    data = request.get_json()
    mood = str(data.get('mood', '')).lower().strip()
    gids = MOOD_GENRES.get(mood, [35])   # default: Comedy
    try:
        results = fetch_tmdb_discover(gids, pages=2, min_votes=300)
        from services.tmdb import weighted_score, get_poster, get_item_id_from_row
        results = sorted(results, key=lambda x: weighted_score(x), reverse=True)[:18]
        random.shuffle(results)
        filtered = [{
            'movie_id':     get_item_id_from_row(r),
            'title':        r.get('title') or r.get('name', 'Unknown'),
            'poster':       get_poster(r.get('poster_path')),
            'rating':       round(float(r.get('vote_average', 0)), 1),
            'overview':     r.get('overview', ''),
            'score':        round(weighted_score(r), 3),
            'release_date': r.get('release_date', '') or r.get('first_air_date', ''),
        } for r in results]
        return jsonify({'results': filtered})
    except Exception as e:
        return jsonify({'results': [], 'error': str(e)})


@core_bp.route('/details', methods=['POST'])
@login_required
def movie_details():
    try:
        data       = request.get_json()
        item_id    = data.get('movie_id')
        title      = data.get('title', '')
        media_type = data.get('media_type', 'movie')

        # If no stored id, search TMDB to get it
        if not item_id:
            search = tmdb_get('/search/multi', {'query': title})
            for r in search.get('results', []):
                if r.get('media_type') in ('movie', 'tv'):
                    item_id    = r['id']
                    media_type = r['media_type']
                    break

        if not item_id:
            return jsonify({'error': 'Not found'}), 404

        # ── Parallel TMDB fetch (videos, credits, details, providers) ──
        from services.tmdb import IMG_BASE, LOGO_BASE
        country = data.get('country', 'US').upper()

        def _fetch_videos():   return tmdb_get(f'/{media_type}/{item_id}/videos').get('results', [])
        def _fetch_credits():  return tmdb_get(f'/{media_type}/{item_id}/credits')
        def _fetch_detail():   return tmdb_get(f'/{media_type}/{item_id}')
        def _fetch_providers():return tmdb_get(f'/{media_type}/{item_id}/watch/providers')

        with ThreadPoolExecutor(max_workers=4) as ex:
            fv = ex.submit(_fetch_videos)
            fc = ex.submit(_fetch_credits)
            fd = ex.submit(_fetch_detail)
            fp = ex.submit(_fetch_providers)
            videos  = fv.result()
            credits = fc.result()
            detail  = fd.result()
            providers_data = fp.result()

        # If both empty, the media_type may be wrong — try the other
        if not videos and not credits.get('cast'):
            alt = 'tv' if media_type == 'movie' else 'movie'
            def _alt_videos():  return tmdb_get(f'/{alt}/{item_id}/videos').get('results', [])
            def _alt_credits(): return tmdb_get(f'/{alt}/{item_id}/credits')
            with ThreadPoolExecutor(max_workers=2) as ex:
                av = ex.submit(_alt_videos)
                ac = ex.submit(_alt_credits)
                alt_v = av.result()
                alt_c = ac.result()
            if alt_v or alt_c.get('cast'):
                media_type = alt
                videos     = alt_v
                credits    = alt_c

        trailer_key = None
        for v in videos:
            if v.get('site') == 'YouTube' and v.get('type') == 'Trailer' and v.get('official'):
                trailer_key = v['key']; break
        if not trailer_key:
            for v in videos:
                if v.get('site') == 'YouTube' and v.get('type') == 'Trailer':
                    trailer_key = v['key']; break
        if not trailer_key:
            for v in videos:
                if v.get('site') == 'YouTube':
                    trailer_key = v['key']; break

        # ── Cast ─────────────────────────────────────────────────
        cast = []
        for c in credits.get('cast', [])[:8]:
            cast.append({
                'name':      c.get('name', ''),
                'character': c.get('character', ''),
                'photo':     IMG_BASE + c['profile_path'] if c.get('profile_path') else None,
            })

        # ── Extra details ─────────────────────────────────────────
        genres  = [g['name'] for g in detail.get('genres', [])]
        runtime = detail.get('runtime') if media_type == 'movie' else (detail.get('episode_run_time') or [None])[0]
        tagline = detail.get('tagline', '')

        # ── Watch Providers ───────────────────────────────────────
        all_regions    = providers_data.get('results', {})
        region         = all_regions.get(country) or all_regions.get('US') or {}

        def fmt_providers(lst):
            return [
                {'provider_name': p['provider_name'],
                 'logo_path': LOGO_BASE + p['logo_path'] if p.get('logo_path') else None}
                for p in lst
            ]

        watch_providers = {
            'link':     region.get('link', ''),
            'flatrate': fmt_providers(region.get('flatrate', [])),
            'rent':     fmt_providers(region.get('rent', [])),
            'buy':      fmt_providers(region.get('buy', [])),
        }

        return jsonify({
            'trailer_key':     trailer_key,
            'cast':            cast,
            'genres':          genres,
            'runtime':         runtime,
            'tagline':         tagline,
            'watch_providers': watch_providers,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

