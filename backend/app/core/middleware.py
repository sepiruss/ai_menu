import uuid
import time
import structlog
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from app.core.config import get_settings

logger = structlog.get_logger()


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        
        start_time = time.time()
        response: Response = await call_next(request)
        process_time = time.time() - start_time
        
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        
        logger.info(
            "request_completed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(process_time * 1000, 2),
        )
        return response


class TenantContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        restaurant_id = request.headers.get("X-Restaurant-ID")
        if restaurant_id:
            try:
                request.state.restaurant_id = int(restaurant_id)
            except ValueError:
                pass
        return await call_next(request)


class InMemoryRateLimiter:
    def __init__(self):
        self.requests: dict[str, list[float]] = defaultdict(list)
    
    def is_allowed(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        now = time.time()
        window_start = now - window
        
        # Clean old requests
        self.requests[key] = [ts for ts in self.requests[key] if ts > window_start]
        
        if len(self.requests[key]) >= limit:
            return False, len(self.requests[key])
        
        self.requests[key].append(now)
        return True, len(self.requests[key])


_rate_limiter = InMemoryRateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, exempt_paths: list[str] | None = None):
        super().__init__(app)
        self.exempt_paths = exempt_paths or ["/docs", "/redoc", "/openapi.json", "/health"]
        self.settings = get_settings()
    
    def _get_client_key(self, request: Request) -> str:
        # Use X-Forwarded-For if behind proxy, otherwise client host
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        return f"ratelimit:{client_ip}:{request.url.path}"
    
    def _is_exempt(self, path: str) -> bool:
        for exempt in self.exempt_paths:
            if path.startswith(exempt):
                return True
        return False
    
    async def dispatch(self, request: Request, call_next):
        if self._is_exempt(request.url.path):
            return await call_next(request)
        
        settings = get_settings()
        key = self._get_client_key(request)
        allowed, current = _rate_limiter.is_allowed(
            key, 
            settings.RATE_LIMIT_PER_MINUTE, 
            60  # 1 minute window
        )
        
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please try again later."},
                headers={
                    "X-RateLimit-Limit": str(settings.RATE_LIMIT_PER_MINUTE),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + 60),
                }
            )
        
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(settings.RATE_LIMIT_PER_MINUTE)
        response.headers["X-RateLimit-Remaining"] = str(settings.RATE_LIMIT_PER_MINUTE - current)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)
        return response