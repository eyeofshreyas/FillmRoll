"""Simple in-memory TTL cache — no dependencies required."""
import time

_store: dict = {}

def get(key):
    entry = _store.get(key)
    if entry and time.time() < entry['exp']:
        return entry['val']
    _store.pop(key, None)
    return None

def set(key, val, ttl=1800):
    """Cache *val* under *key* for *ttl* seconds (default 30 min)."""
    _store[key] = {'val': val, 'exp': time.time() + ttl}
