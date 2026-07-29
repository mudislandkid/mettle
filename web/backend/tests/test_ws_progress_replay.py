"""Progress snapshot replay for late-connecting WebSocket clients.

`POST /api/analysis/start` hands the work to FastAPI BackgroundTasks, which
Starlette runs the moment the HTTP response is flushed. The frontend only
opens the progress WebSocket *after* that POST resolves, so the analysis is
frequently already running — often already finished — by the time the socket
registers itself in `active_connections`.

Because `broadcast_progress` is fire-and-forget, every frame emitted before
the socket connects used to be dropped with no way to catch up, so the UI
either jumped straight to "done" with no progress or hung on the running
state forever.

These tests pin the fix: the server keeps the latest progress payload per
analysis and replays a snapshot to each client the instant it connects,
falling back to the persisted DB status when no in-memory payload exists.
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from web.backend.api import routes_analysis
from web.backend.database.connection import engine, run_migrations
from web.backend.database.models import Analysis
from web.backend.main import app


@pytest.fixture(autouse=True)
def _clear_progress_state():
    """Create the schema (tests share a tmp DB) and keep caches from leaking."""
    run_migrations()
    routes_analysis.last_progress.clear()
    routes_analysis.active_connections.clear()
    yield
    routes_analysis.last_progress.clear()
    routes_analysis.active_connections.clear()


def _make_analysis(status: str, **kw) -> int:
    with Session(engine) as session:
        analysis = Analysis(directory_path="/tmp/whatever", status=status, **kw)
        session.add(analysis)
        session.commit()
        session.refresh(analysis)
        return analysis.id


def test_late_client_gets_completed_snapshot_from_db(security_env):
    """The exact desktop symptom: analysis finished before the socket opened.

    With no in-memory payload to replay, the snapshot must be reconstructed
    from the persisted analysis row so the UI can leave the running state.
    """
    security_env()
    analysis_id = _make_analysis("completed", total_projects=3)

    client = TestClient(app)
    with client.websocket_connect(f"/api/analysis/ws/{analysis_id}") as ws:
        frame = ws.receive_json()

    assert frame["status"] == "completed"
    assert frame["total"] == 3


def test_late_client_gets_failed_snapshot_from_db(security_env):
    """A failed run must also reach a late client, with its error surfaced."""
    security_env()
    analysis_id = _make_analysis("failed", error_message="PermissionError")

    client = TestClient(app)
    with client.websocket_connect(f"/api/analysis/ws/{analysis_id}") as ws:
        frame = ws.receive_json()

    assert frame["status"] == "failed"
    assert frame["error"] == "PermissionError"


def test_late_client_gets_last_in_flight_progress(security_env):
    """Mid-run connect replays the most recent progress frame, not silence."""
    security_env()
    analysis_id = _make_analysis("running")

    routes_analysis.record_progress(
        analysis_id,
        {
            "status": "running",
            "current": 4,
            "total": 10,
            "project_name": "acme",
            "message": "Analyzing project 4/10: acme",
            "logs": ["[4/10] Analyzing: acme"],
        },
    )

    client = TestClient(app)
    with client.websocket_connect(f"/api/analysis/ws/{analysis_id}") as ws:
        frame = ws.receive_json()

    assert frame["status"] == "running"
    assert frame["current"] == 4
    assert frame["total"] == 10


def test_pending_analysis_replays_pending_snapshot(security_env):
    """A queued-but-not-started run should not be reported as finished."""
    security_env()
    analysis_id = _make_analysis("pending")

    client = TestClient(app)
    with client.websocket_connect(f"/api/analysis/ws/{analysis_id}") as ws:
        frame = ws.receive_json()

    assert frame["status"] == "pending"


def test_snapshot_does_not_break_ping_pong(security_env):
    """The replayed frame must not consume the keepalive exchange."""
    security_env()
    analysis_id = _make_analysis("running")

    client = TestClient(app)
    with client.websocket_connect(f"/api/analysis/ws/{analysis_id}") as ws:
        ws.receive_json()  # snapshot
        ws.send_text("ping")
        assert ws.receive_text() == "pong"


def test_record_progress_evicts_oldest_entries():
    """The replay cache is bounded so long-lived desktop sessions don't leak."""
    for i in range(routes_analysis.MAX_TRACKED_ANALYSES + 25):
        routes_analysis.record_progress(i, {"status": "running", "current": i})

    assert len(routes_analysis.last_progress) <= routes_analysis.MAX_TRACKED_ANALYSES
    # Newest retained, oldest evicted.
    assert routes_analysis.MAX_TRACKED_ANALYSES + 24 in routes_analysis.last_progress
    assert 0 not in routes_analysis.last_progress
