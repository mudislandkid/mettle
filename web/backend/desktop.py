"""Sidecar entry point for the Tauri desktop build.

PyInstaller freezes this module into a single-file binary that Tauri spawns
on app launch. The binary:

  1. Picks a random free localhost port (or honours METTLE_PORT)
  2. Generates a per-launch auth token (or honours METTLE_TOKEN)
  3. Resolves the user data dir (METTLE_DATA_DIR, defaults to platform default)
  4. Boots uvicorn against ``web.backend.main:app`` bound to 127.0.0.1
  5. Emits a single ``MettleReady port=<n> token=<hex>`` line on stdout once
     uvicorn is accepting connections — Tauri parses this to wire the WebView.

The handshake line is the contract between the Rust host and the Python
sidecar; keep its format stable.
"""

from __future__ import annotations

import os
import secrets
import socket
import sys
import threading
import time
from pathlib import Path


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _default_data_dir() -> Path:
    """Platform-appropriate per-user data directory for the desktop build."""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Mettle"
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / "Mettle"
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "mettle"


def _wait_for_port(port: int, timeout: float = 30.0) -> bool:
    """Poll the port until something is listening, or timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.25)
            try:
                s.connect(("127.0.0.1", port))
                return True
            except OSError:
                time.sleep(0.05)
    return False


def main() -> int:
    # ------------------------------------------------------------------
    # Resolve environment before importing the app — config.py reads env
    # at import time.
    # ------------------------------------------------------------------
    if not os.environ.get("METTLE_DATA_DIR"):
        os.environ["METTLE_DATA_DIR"] = str(_default_data_dir())

    port = int(os.environ.get("METTLE_PORT") or _pick_free_port())
    os.environ["METTLE_PORT"] = str(port)

    if not os.environ.get("METTLE_TOKEN"):
        os.environ["METTLE_TOKEN"] = secrets.token_hex(24)
    token = os.environ["METTLE_TOKEN"]

    # CORS for the Tauri WebView origin (tauri://localhost on macOS/Linux,
    # https://tauri.localhost on Windows) plus standard dev origins.
    if not os.environ.get("METTLE_CORS_ORIGINS"):
        os.environ["METTLE_CORS_ORIGINS"] = ",".join(
            (
                "tauri://localhost",
                "https://tauri.localhost",
                "http://localhost:5173",
                "http://127.0.0.1:5173",
            )
        )

    # ------------------------------------------------------------------
    # Boot uvicorn. Import here so env is in place before the app reads it.
    # ------------------------------------------------------------------
    import uvicorn  # noqa: E402

    from web.backend.main import app  # noqa: E402

    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        access_log=False,
        loop="asyncio",
    )
    server = uvicorn.Server(config)

    # Watch for the port to open in a thread so we can emit the handshake
    # line on stdout the moment Tauri can connect.
    def _announce() -> None:
        if _wait_for_port(port):
            sys.stdout.write(f"MettleReady port={port} token={token}\n")
            sys.stdout.flush()
        else:
            sys.stderr.write("MettleSidecarError port-never-opened\n")
            sys.stderr.flush()

    threading.Thread(target=_announce, daemon=True).start()

    try:
        server.run()
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
