import threading
import time
from typing import Any

class TTLCache:
    """
    MF-7: Simple thread-safe TTL Cache to avoid external dependencies.
    """
    def __init__(self, maxsize: int = 128, ttl: int = 300):
        self.maxsize = maxsize
        self.ttl = ttl
        self._cache: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            if key not in self._cache:
                return None
            timestamp, value = self._cache[key]
            if time.time() - timestamp > self.ttl:
                del self._cache[key]
                return None
            return value

    def set(self, key: str, value: Any):
        with self._lock:
            # Simple eviction if maxsize is reached
            if len(self._cache) >= self.maxsize:
                # Evict oldest
                oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][0])
                del self._cache[oldest_key]
            self._cache[key] = (time.time(), value)

    def clear(self):
        with self._lock:
            self._cache.clear()

def ttl_cache(ttl: int = 300, maxsize: int = 128):
    """
    Decorator for caching function results with a TTL.
    """
    cache = TTLCache(maxsize=maxsize, ttl=ttl)
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Create a cache key from args and kwargs
            key = str(args) + str(frozenset(kwargs.items()))
            cached = cache.get(key)
            if cached is not None:
                return cached
            
            result = func(*args, **kwargs)
            cache.set(key, result)
            return result
        
        # Attach the cache instance to the wrapper for manual invalidation/inspection
        wrapper.cache = cache
        return wrapper
    return decorator
