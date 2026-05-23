"""Tests for TokenAuthMiddleware — HTTP bearer authentication."""

from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient

from web.backend.security.auth import TokenAuthMiddleware


def _app_with_middleware(token: str | None) -> FastAPI:
    app = FastAPI()
    app.add_middleware(TokenAuthMiddleware, token=token)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    @app.websocket("/ws/echo")
    async def ws_echo(ws: WebSocket):
        await ws.accept()
        await ws.send_text("hi")
        await ws.close()

    return app


def test_no_token_set_passes_through(security_env):
    security_env()
    client = TestClient(_app_with_middleware(None))
    r = client.get("/ping")
    assert r.status_code == 200


def test_missing_header_returns_401(security_env):
    security_env(TOKEN="abc")
    client = TestClient(_app_with_middleware("abc"))
    r = client.get("/ping")
    assert r.status_code == 401
    assert "bearer" in r.headers.get("www-authenticate", "").lower()


def test_wrong_scheme_returns_401(security_env):
    security_env(TOKEN="abc")
    client = TestClient(_app_with_middleware("abc"))
    r = client.get("/ping", headers={"Authorization": "Basic abc"})
    assert r.status_code == 401


def test_wrong_token_returns_401(security_env):
    security_env(TOKEN="abc")
    client = TestClient(_app_with_middleware("abc"))
    r = client.get("/ping", headers={"Authorization": "Bearer wrong"})
    assert r.status_code == 401


def test_correct_token_returns_200(security_env):
    security_env(TOKEN="abc")
    client = TestClient(_app_with_middleware("abc"))
    r = client.get("/ping", headers={"Authorization": "Bearer abc"})
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_options_preflight_is_exempt(security_env):
    """CORS preflight (OPTIONS) must pass through so CORSMiddleware can answer.

    Without this, cross-origin POSTs from the Tauri WebView get 401'd at the
    preflight stage — the browser never sends the real request.
    """
    security_env(TOKEN="abc")
    client = TestClient(_app_with_middleware("abc"))
    r = client.options(
        "/ping",
        headers={
            "Origin": "tauri://localhost",
            "Access-Control-Request-Method": "POST",
        },
    )
    # FastAPI without CORSMiddleware returns 405 for OPTIONS on a GET route,
    # but the key behaviour is that we did NOT 401 — so anything other than
    # 401 means the auth layer let it through.
    assert r.status_code != 401


def test_ws_path_is_exempt_from_http_middleware(security_env):
    """The /ws/* upgrade path is handled by the route dependency, not the HTTP middleware.

    Without this exemption the HTTP middleware would 401 the upgrade before the WS
    handshake had a chance to inspect Sec-WebSocket-Protocol.
    """
    security_env(TOKEN="abc")
    client = TestClient(_app_with_middleware("abc"))
    # If middleware reached /ws/echo this would be a 401. Instead it passes through.
    with client.websocket_connect("/ws/echo") as ws:
        assert ws.receive_text() == "hi"
