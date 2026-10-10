import json
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import redis.asyncio as redis
import asyncio
from app.config import settings

class QueryCacheMiddleware(BaseHTTPMiddleware):
    """
    Middleware to cache API GET responses in Redis to increase DB fetch speed.
    Automatically invalidates cache when POST, PUT, or DELETE requests are made.
    """

    def __init__(self, app):
        super().__init__(app)
        self.redis = redis.from_url(settings.REDIS_URL, decode_responses=False)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Only cache /api/ requests
        if not path.startswith("/api/"):
            return await call_next(request)

        method = request.method

        # If it's a mutation, clear the cache for that resource group
        if method in ["POST", "PUT", "DELETE", "PATCH"]:
            try:
                await asyncio.wait_for(self.redis.flushdb(), timeout=2.0)
            except Exception as e:
                # Fallback if Redis is down, we just proceed
                print(f"Redis cache clear error: {e}")
            return await call_next(request)

        # Only cache GET requests
        if method != "GET":
            return await call_next(request)

        # Do not cache sensitive or dynamic routes
        if "auth" in path or "health" in path:
            return await call_next(request)

        # Construct cache key from URL and query params
        query_string = request.url.query
        cache_key = f"cache:{path}?{query_string}" if query_string else f"cache:{path}"

        try:
            # Check Redis cache
            cached_data = await self.redis.get(cache_key)
            if cached_data:
                cached_headers_json = await self.redis.get(f"{cache_key}:headers")
                headers = json.loads(cached_headers_json) if cached_headers_json else {}
                return Response(content=cached_data, status_code=200, headers=headers)
        except Exception as e:
            print(f"Redis read error: {e}")
            # If Redis is down, continue without cache

        # Process the request
        response = await call_next(request)

        # Only cache successful JSON responses
        if response.status_code == 200 and response.headers.get("content-type") == "application/json":
            # We must consume the body to cache it
            body = b""
            async for chunk in response.body_iterator:
                body += chunk

            # Reconstruct the response body since we consumed it
            headers = dict(response.headers)
            # Remove content-length as it might change or cause issues if compressed
            headers.pop("content-length", None)

            try:
                # Store in Redis with 15-second TTL
                await self.redis.setex(cache_key, 15, body)
                await self.redis.setex(f"{cache_key}:headers", 15, json.dumps(headers).encode('utf-8'))
            except Exception as e:
                print(f"Redis write error: {e}")

            return Response(content=body, status_code=response.status_code, headers=headers)

        return response
