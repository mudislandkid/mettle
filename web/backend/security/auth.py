"""Bearer-token auth for HTTP routes and WebSocket handshakes.

HTTP: TokenAuthMiddleware (Starlette BaseHTTPMiddleware) rejects requests
missing/wrong-token with 401. The /ws/* upgrade path is exempt — WS auth
is handled by the route dependency `authorize_websocket()` below
(added in Task 5).
"""

import hmac
import logging

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

log = logging.getLogger("mettle.security")


class TokenAuthMiddleware(BaseHTTPMiddleware):
    """Bearer-token authentication for HTTP routes. No-op when token is None.

    The /ws/* upgrade path is exempt — WS auth is handled at the route layer
    because it needs to speak the Sec-WebSocket-Protocol handshake.
    """

    def __init__(self, app, token: str | None):
        super().__init__(app)
        self._token = token

    async def dispatch(self, request: Request, call_next):
        if self._token is None:
            return await call_next(request)
        if request.url.path.startswith("/ws/"):
            return await call_next(request)

        header = request.headers.get("authorization", "")
        scheme, _, presented = header.partition(" ")
        if scheme.lower() != "bearer" or not hmac.compare_digest(presented, self._token):
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing bearer token."},
                headers={"WWW-Authenticate": 'Bearer realm="mettle"'},
            )
        return await call_next(request)
