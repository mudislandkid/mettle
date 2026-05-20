#!/usr/bin/env python3
"""Unified startup script for Mettle web application."""

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

WEB_DIR = Path(__file__).parent.resolve()
BACKEND_DIR = WEB_DIR / "backend"
FRONTEND_DIR = WEB_DIR / "frontend"


class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def log(message: str, color: str = Colors.RESET) -> None:
    print(f"{color}{message}{Colors.RESET}")


def check_python_deps() -> bool:
    try:
        import fastapi  # noqa: F401
        import sqlmodel  # noqa: F401
        import uvicorn  # noqa: F401

        return True
    except ImportError:
        return False


def install_python_deps() -> None:
    log("Installing Python dependencies (CLI + [web] extra)...", Colors.YELLOW)
    project_root = WEB_DIR.parent
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", f"{project_root}[web]"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        log(f"Failed to install Python dependencies:\n{result.stderr}", Colors.RED)
        sys.exit(1)
    log("Python dependencies installed successfully.", Colors.GREEN)


def check_node_modules() -> bool:
    return (FRONTEND_DIR / "node_modules").exists()


def install_npm_deps() -> None:
    log("Installing frontend dependencies...", Colors.YELLOW)
    result = subprocess.run(
        ["npm", "install"],
        cwd=FRONTEND_DIR,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        log(f"Failed to install npm dependencies:\n{result.stderr}", Colors.RED)
        sys.exit(1)
    log("Frontend dependencies installed successfully.", Colors.GREEN)


def start_backend(host: str, port: int, reload: bool) -> subprocess.Popen:
    label = "with --reload" if reload else "single-process"
    log(f"Starting backend server on http://{host}:{port} ({label})", Colors.BLUE)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(WEB_DIR.parent)

    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.main:app",
        "--host",
        host,
        "--port",
        str(port),
    ]
    if reload:
        cmd.append("--reload")
    else:
        # Stay in a single worker so an in-memory websocket map stays consistent.
        cmd.extend(["--workers", "1"])

    return subprocess.Popen(cmd, cwd=WEB_DIR, env=env)


def start_frontend(port: int) -> subprocess.Popen:
    log(f"Starting frontend dev server on http://localhost:{port}", Colors.BLUE)
    return subprocess.Popen(
        ["npm", "run", "dev", "--", "--port", str(port)],
        cwd=FRONTEND_DIR,
    )


def build_frontend() -> None:
    log("Building frontend for production...", Colors.YELLOW)
    result = subprocess.run(["npm", "run", "build"], cwd=FRONTEND_DIR)
    if result.returncode != 0:
        log("Frontend build failed.", Colors.RED)
        sys.exit(1)
    log("Frontend built successfully.", Colors.GREEN)


def main(args: argparse.Namespace | None = None) -> int:
    if args is None:
        parser = argparse.ArgumentParser(description="Run Mettle web application")
        parser.add_argument(
            "--mode",
            choices=["dev", "prod", "backend-only"],
            default="dev",
            help="Run mode: dev (both servers, with reload), prod (build frontend + serve via backend), backend-only",
        )
        parser.add_argument(
            "--backend-host", default="127.0.0.1", help="Backend host (default: 127.0.0.1)"
        )
        parser.add_argument(
            "--backend-port", type=int, default=8000, help="Backend port (default: 8000)"
        )
        parser.add_argument(
            "--frontend-port", type=int, default=5173, help="Frontend dev port (default: 5173)"
        )
        parser.add_argument(
            "--skip-install",
            action="store_true",
            help="Skip dependency installation checks (recommended for production).",
        )
        parser.add_argument(
            "--auto-install",
            action="store_true",
            help="Run pip/npm install automatically if deps are missing. Off by default to avoid supply-chain surprises.",
        )
        parser.add_argument(
            "--allow-public-bind",
            action="store_true",
            help="Required to bind --backend-host to a non-loopback address.",
        )
        args = parser.parse_args()

    # Security gate: refuse non-loopback bind without --allow-public-bind AND METTLE_TOKEN.
    # Imported lazily so test fixtures importing web.run don't trigger the env-var read.
    from web.backend.security.startup import assert_bind_is_safe

    assert_bind_is_safe(args.backend_host, args.allow_public_bind)

    log(f"\n{Colors.BOLD}Mettle Web Application{Colors.RESET}\n", Colors.GREEN)

    # Verify deps; install only when explicitly opted in. The old behavior was
    # to silently `pip install` on every launch which is a supply-chain
    # footgun and slow.
    if not args.skip_install:
        if not check_python_deps():
            if args.auto_install:
                install_python_deps()
            else:
                log(
                    "Python deps missing. From the repo root run:\n"
                    '    pip install -e ".[web]"\n'
                    "or re-run this script with --auto-install.",
                    Colors.RED,
                )
                sys.exit(1)

        if args.mode in ("dev", "prod") and not check_node_modules():
            if args.auto_install:
                install_npm_deps()
            else:
                log(
                    "Frontend deps missing. Run `npm install` inside web/frontend/,\n"
                    "or re-run with --auto-install.",
                    Colors.RED,
                )
                sys.exit(1)

    processes: list[subprocess.Popen] = []
    shutting_down = False

    def cleanup(signum=None, frame=None) -> None:
        nonlocal shutting_down
        if shutting_down:
            return
        shutting_down = True
        log("\nShutting down...", Colors.YELLOW)
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
        for proc in processes:
            if proc.poll() is None:
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    try:
        if args.mode == "prod":
            build_frontend()
            log("\nRunning in production mode.", Colors.GREEN)
            log(f"Access at: http://{args.backend_host}:{args.backend_port}", Colors.GREEN)
            backend = start_backend(args.backend_host, args.backend_port, reload=False)
            processes.append(backend)
            backend.wait()

        elif args.mode == "backend-only":
            log("\nRunning backend only.", Colors.YELLOW)
            log(f"API at: http://{args.backend_host}:{args.backend_port}", Colors.GREEN)
            backend = start_backend(args.backend_host, args.backend_port, reload=False)
            processes.append(backend)
            backend.wait()

        else:  # dev mode
            log("\nRunning in development mode.", Colors.GREEN)
            backend = start_backend(args.backend_host, args.backend_port, reload=True)
            processes.append(backend)
            time.sleep(2)

            frontend = start_frontend(args.frontend_port)
            processes.append(frontend)

            log(f"\n{Colors.BOLD}Application URLs:{Colors.RESET}", Colors.GREEN)
            log(f"  Frontend: http://localhost:{args.frontend_port}", Colors.GREEN)
            log(f"  Backend API: http://{args.backend_host}:{args.backend_port}/docs", Colors.GREEN)
            log("\nPress Ctrl+C to stop all servers.\n", Colors.YELLOW)

            try:
                while True:
                    exited = next((p for p in processes if p.poll() is not None), None)
                    if exited is not None:
                        log(
                            f"Process exited (rc={exited.returncode}); shutting down peers.",
                            Colors.YELLOW,
                        )
                        break
                    time.sleep(1)
            finally:
                cleanup()

    except Exception as e:
        log(f"Error: {e}", Colors.RED)
        cleanup()
        sys.exit(1)

    return 0


if __name__ == "__main__":
    main()
