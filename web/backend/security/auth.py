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

from . import settings

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
        # CORS preflight is safe by design (no body, no side-effects) and the
        # browser never attaches Authorization headers to it. Let it through so
        # CORSMiddleware can answer with the right Access-Control-Allow-*
        # headers — otherwise cross-origin POSTs from the Tauri WebView
        # (tauri://localhost → http://127.0.0.1:<port>) get a 401 here before
        # the real request is even attempted.
        if request.method == "OPTIONS":
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


async def authorize_websocket(websocket) -> str | None:
    """Validate a WebSocket handshake. Returns the subprotocol to echo on accept(),
    or None when the token is unset (no auth required) or after the handshake
    has been rejected (close() already called inside).

    Callers must check the return BEFORE calling websocket.accept(). When auth
    is required and the handshake fails, this function closes the socket with
    code 1008 and the caller should simply return.
    """
    # Origin check applies in both auth modes — defense in depth against
    # browser-originated requests from disallowed pages even in the no-token
    # local-only mode. A browser-loaded file:// page or a malicious page on
    # another origin should not be able to subscribe to analysis events on
    # 127.0.0.1, regardless of whether a token is configured.
    origin = websocket.headers.get("origin", "")
    if origin and origin not in settings.cors_origins():
        log.warning("WS rejected: origin %r not in METTLE_CORS_ORIGINS", origin)
        await websocket.close(code=1008, reason="origin not allowed")
        return None

    expected = settings.token()
    if expected is None:
        return None  # no auth — caller should accept() with no subprotocol

    protocols = websocket.headers.get("sec-websocket-protocol", "")
    parts = [p.strip() for p in protocols.split(",") if p.strip()]
    if len(parts) != 2 or parts[0] != "mettle.bearer":
        await websocket.close(code=1008, reason="missing or malformed bearer subprotocol")
        return None
    if not hmac.compare_digest(parts[1], expected):
        await websocket.close(code=1008, reason="invalid bearer")
        return None
    return "mettle.bearer"
