import time


class RedisLikeCache:
    """
    A simple, fast in-memory cache that behaves like Redis (key-value store with TTL).
    Perfect for speeding up database queries without needing an external Redis server.
    """

    def __init__(self):
        self.store = {}

    def get(self, key: str):
        if key in self.store:
            val, expiry = self.store[key]
            if time.time() < expiry:
                return val
            else:
                del self.store[key]
        return None

    def set(self, key: str, value, ttl: int = 300):
        """Set a value with a Time-To-Live in seconds (default 5 minutes)"""
        self.store[key] = (value, time.time() + ttl)

    def delete(self, key: str):
        if key in self.store:
            del self.store[key]

    def clear(self):
        """Clear all cached data (useful for invalidation on writes)"""
        self.store = {}


# Global cache instance
cache = RedisLikeCache()
