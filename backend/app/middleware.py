import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class QueryCacheMiddleware(BaseHTTPMiddleware):
    """
    Middleware to cache API GET responses in memory to increase DB fetch speed.
    Automatically invalidates cache when POST, PUT, or DELETE requests are made.
    """

    def __init__(self, app):
        super().__init__(app)
        self.cache = {}

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Only cache /api/ requests
        if not path.startswith("/api/"):
            return await call_next(request)

        method = request.method

        # If it's a mutation, clear the cache for that resource group
        if method in ["POST", "PUT", "DELETE", "PATCH"]:
            # Simple invalidation: clear everything to ensure data consistency
            # since a sale affects inventory, reports, etc.
            self.cache.clear()
            return await call_next(request)

        # Only cache GET requests
        if method != "GET":
            return await call_next(request)

        # Do not cache sensitive or dynamic routes
        if "auth" in path or "health" in path:
            return await call_next(request)

        # Construct cache key from URL and query params
        query_string = request.url.query
        cache_key = f"{path}?{query_string}" if query_string else path

        # Check cache (15 second TTL for fast realtime feeling, but prevents DB overload)
        if cache_key in self.cache:
            data, expiry, headers, status_code = self.cache[cache_key]
            if time.time() < expiry:
                return Response(content=data, status_code=status_code, headers=headers)
            else:
                del self.cache[cache_key]

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

            # Store in cache with 15-second TTL
            self.cache[cache_key] = (body, time.time() + 15, headers, response.status_code)

            return Response(content=body, status_code=response.status_code, headers=headers)

        return response
