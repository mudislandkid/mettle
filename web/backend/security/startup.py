"""One-shot startup gates.

All process-aborting checks live here so they're easy to audit. Call
`assert_bind_is_safe` from the launcher (web/run.py, mettle/cli.py) before
booting uvicorn. Call `validate_or_die` from web/backend/main.py once the
app is being constructed.
"""

import logging
import sys

from . import settings

log = logging.getLogger("mettle.security")


def assert_bind_is_safe(host: str, allow_public: bool) -> None:
    """Refuse to start if the bind is risky and not explicitly opted into.

    - Loopback (127.0.0.1, localhost, ::1) is always safe.
    - Non-loopback requires --allow-public-bind AND METTLE_TOKEN.

    Raises SystemExit with a clear message on refusal — never returns in an unsafe state.
    """
    if host in ("127.0.0.1", "localhost", "::1"):
        return

    if not allow_public:
        sys.exit(
            f"Refusing to bind to {host!r} without --allow-public-bind.\n"
            "  Loopback (127.0.0.1) is the default. To expose Mettle on this network,\n"
            "  re-run with --allow-public-bind AND set METTLE_TOKEN."
        )

    if settings.token() is None:
        sys.exit(
            "--allow-public-bind requires METTLE_TOKEN to be set.\n"
            "  Mettle will not expose unauthenticated endpoints on a non-loopback bind."
        )


def validate_cors(origins: list[str]) -> None:
    """Reject CORS configurations that would silently break the security model.

    Raises SystemExit on wildcards, missing schemes, or empty-with-token.
    """
    for origin in origins:
        if "*" in origin:
            sys.exit(
                f"CORS wildcard origin ({origin!r}) is not allowed.\n"
                "  Set METTLE_CORS_ORIGINS to a comma-separated list of exact origins."
            )
        if not (origin.startswith("http://") or origin.startswith("https://")):
            sys.exit(
                f"CORS origin must include scheme: got {origin!r}.\n"
                "  Use e.g. 'https://mettle.example.com', not 'mettle.example.com'."
            )
    if settings.token() is not None and not origins:
        sys.exit(
            "METTLE_TOKEN is set but METTLE_CORS_ORIGINS resolved to an empty list.\n"
            "  A token-protected backend with no allowed origins cannot be reached from any browser."
        )


def warn_if_jail_disabled() -> None:
    """Log a startup warning when METTLE_SCAN_ROOTS is unset."""
    roots = settings.scan_roots()
    if roots is None:
        log.warning(
            "METTLE_SCAN_ROOTS unset — path-jail disabled. Any user with API access "
            "can scan any path the backend process can read."
        )
    else:
        log.info("Path-jail active: %d allowed roots loaded", len(roots))
        log.debug("Allowed roots: %s", roots)


def validate_or_die() -> None:
    """Run the in-process startup checks. Called from web/backend/main.py."""
    validate_cors(settings.cors_origins())
    warn_if_jail_disabled()
