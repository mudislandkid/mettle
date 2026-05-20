"""Tests for authorize_websocket — Sec-WebSocket-Protocol subprotocol handshake."""

import pytest
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from web.backend.security.auth import authorize_websocket


def _app_with_ws_auth() -> FastAPI:
    """Build an app whose /ws/echo route uses authorize_websocket()."""
    app = FastAPI()

    @app.websocket("/ws/echo")
    async def ws_echo(ws: WebSocket):
        subprotocol = await authorize_websocket(ws)
        # If token was set but authorize closed, we just return.
        from web.backend.security import settings

        if settings.token() is not None and subprotocol is None:
            return
        await ws.accept(subprotocol=subprotocol)
        await ws.send_text("hi")
        await ws.close()

    return app


def test_no_token_set_accepts_without_subprotocol(security_env):
    security_env()
    client = TestClient(_app_with_ws_auth())
    with client.websocket_connect("/ws/echo") as ws:
        assert ws.receive_text() == "hi"


def test_missing_subprotocol_rejected(security_env):
    security_env(TOKEN="abc", CORS_ORIGINS="http://testserver")
    client = TestClient(_app_with_ws_auth())
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/ws/echo") as ws:
            ws.receive_text()
    assert exc.value.code == 1008


def test_wrong_protocol_name_rejected(security_env):
    security_env(TOKEN="abc", CORS_ORIGINS="http://testserver")
    client = TestClient(_app_with_ws_auth())
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/ws/echo", subprotocols=["wrong.bearer", "abc"]):
            pass
    assert exc.value.code == 1008


def test_wrong_token_rejected(security_env):
    security_env(TOKEN="abc", CORS_ORIGINS="http://testserver")
    client = TestClient(_app_with_ws_auth())
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/ws/echo", subprotocols=["mettle.bearer", "wrong"]):
            pass
    assert exc.value.code == 1008


def test_correct_token_accepted_echoes_subprotocol(security_env):
    security_env(TOKEN="abc", CORS_ORIGINS="http://testserver")
    client = TestClient(_app_with_ws_auth())
    with client.websocket_connect("/ws/echo", subprotocols=["mettle.bearer", "abc"]) as ws:
        assert ws.receive_text() == "hi"
