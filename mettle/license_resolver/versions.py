"""Helpers for turning version strings stored in dependency manifests into
something a registry URL will accept.

`detect_dependencies` records whatever the manifest declared, which is almost
always a *constraint* (`>=0.115`, `^18.2.0`, `~2.1`, `*`, `1.0.*`) rather
than a concrete release version. Pasting those straight into a registry URL
gives 404s, so we sanitise here: emit a concrete-looking version when we can
recognise one, else return None so the caller falls back to the registry's
"latest" endpoint.

Licenses very rarely change between minor versions of the same package, so
"latest" is a pragmatic fallback — strictly speaking it can be wrong, but
the false-positive rate is negligible compared to the false-negative rate
of refusing to resolve anything with a `>=` in it.
"""

from __future__ import annotations

import re

# A "concrete" version string starts with an optional `v` / `V`, then a digit,
# and contains only digit / dot / dash / plus / underscore / alphanumerics
# after that (semver pre-release + build metadata, PEP 440 post / dev / local).
_CONCRETE_VERSION_RE = re.compile(r"^[vV]?\d[\w.\-+]*$")


def concrete_version(version: str | None) -> str | None:
    """Return ``version`` when it looks like a specific release version a
    registry will accept (e.g. ``"1.2.3"``, ``"v0.4"``, ``"18.2.0-rc.1"``,
    ``"1.0.0+build.42"``). Returns ``None`` for constraints (``">=1"``,
    ``"^18"``, ``"~2.0"``, ``"*"``, etc.) so the caller can fall back to
    the registry's latest endpoint."""
    if not version:
        return None
    v = version.strip()
    if not v:
        return None
    # Reject anything that looks like a constraint expression.
    if any(op in v for op in (">", "<", "=", "!", "*", " ", ",", "|", "@")):
        return None
    if v[0] in "^~":
        return None
    if _CONCRETE_VERSION_RE.match(v):
        return v
    return None
