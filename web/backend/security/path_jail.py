"""METTLE_SCAN_ROOTS path-jail enforcement.

`resolve_and_check(path)` resolves a user-supplied path and verifies it
falls inside the configured allow-list. When the allow-list is unset, the
function is a no-op pass-through.

`jailed_path` is a FastAPI dependency for routes that take a path in the
request body. For routes that look up paths from the DB, the handler should
call `resolve_and_check` directly (and convert PathJailError to HTTPException).

`filter_jailed` is for DB-sourced lists like /api/recent-paths — silently
drops violators instead of raising, since the DB may hold entries from a
previous configuration.
"""

from pathlib import Path

from fastapi import Body, HTTPException

from . import settings


class PathJailError(Exception):
    """Raised when a request path violates the jail. Maps to HTTP 403."""


def resolve_and_check(raw_path: str) -> Path:
    """Resolve a user-supplied path; raise PathJailError if outside METTLE_SCAN_ROOTS.

    - Expands ~, follows symlinks, resolves .. (via Path.resolve(strict=False)).
    - When METTLE_SCAN_ROOTS is unset, returns the resolved path with no check.
    """
    resolved = Path(raw_path).expanduser().resolve(strict=False)
    roots = settings.scan_roots()
    if roots is None:
        return resolved
    for root in roots:
        try:
            resolved.relative_to(root)
            return resolved
        except ValueError:
            continue
    raise PathJailError(f"Path {resolved} is outside the configured METTLE_SCAN_ROOTS.")


def jailed_path(path: str = Body(..., embed=True)) -> Path:
    """FastAPI dependency. Resolves + jails a `path` field in the request body.

    Usage:
        @router.post("/foo")
        def foo(path: Path = Depends(jailed_path)):
            ...
    """
    try:
        return resolve_and_check(path)
    except PathJailError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


def filter_jailed(paths: list[str]) -> list[Path]:
    """Filter a path list to only those passing the jail. Silently drops violators."""
    out: list[Path] = []
    for p in paths:
        try:
            out.append(resolve_and_check(p))
        except PathJailError:
            continue
    return out
