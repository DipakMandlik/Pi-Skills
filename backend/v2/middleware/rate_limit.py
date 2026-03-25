from __future__ import annotations

import time
from collections import defaultdict
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from backend.v2.shared.response import error_response

_rate_limits: dict[str, list[float]] = defaultdict(list)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 60, auth_requests_per_15min: int = 5):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.auth_requests_per_15min = auth_requests_per_15min

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path

        if path.startswith("/auth/login") or path.startswith("/auth/forgot") or path.startswith("/auth/reset"):
            key = f"auth:{client_ip}"
            window = 900
            max_requests = self.auth_requests_per_15min
        else:
            key = f"general:{client_ip}"
            window = 60
            max_requests = self.requests_per_minute

        now = time.time()
        _rate_limits[key] = [t for t in _rate_limits[key] if now - t < window]

        if len(_rate_limits[key]) >= max_requests:
            return error_response(429, "RATE_LIMIT_EXCEEDED", "Too many requests. Please try again later.")

        _rate_limits[key].append(now)
        return await call_next(request)
