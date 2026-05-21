"""License resolution for declared dependencies.

Turns a list of `{name, version, manager}` dicts (the output of
`mettle.analyzers.dependency_detection.detect_dependencies`) into resolved
SPDX licenses by querying public package-registry metadata. Cached in SQLite
so re-runs are free.

Public surface:
    - `ResolvedLicense` dataclass
    - `resolve_all(deps, *, cache=None, on_progress=None) -> list[ResolvedLicense]`

Per-manager support lives in sibling modules (npm, pypi, crates). Adding a
new ecosystem is one module + one entry in `_RESOLVERS`.
"""

from __future__ import annotations

from dataclasses import dataclass

from .cache import LicenseCache
from .crates import CratesResolver
from .http import RegistryClient
from .npm import NpmResolver
from .pypi import PyPiResolver


@dataclass
class ResolvedLicense:
    name: str
    version: str | None
    manager: str
    spdx: str | None  # canonical SPDX id, or None if unresolvable
    source: str  # "npm" / "pypi" / "crates" / "cache" / "unsupported"


# Maps dependency_detection.py's `manager` strings to a resolver class.
_RESOLVERS = {
    "npm": NpmResolver,
    "pypi": PyPiResolver,
    "cargo": CratesResolver,
}


def resolve_all(
    deps: list[dict],
    *,
    cache: LicenseCache | None = None,
    client: RegistryClient | None = None,
    on_progress=None,
) -> list[ResolvedLicense]:
    """Resolve every (manager, name, version) tuple to an SPDX id.

    Cache hits are returned immediately. Cache misses fan out across a small
    thread pool — registries tolerate sequential polite traffic better than
    bursts, so concurrency is intentionally capped low.

    `on_progress(i, total)` is called after each entry (cache hit or miss) so
    callers can render a progress bar.
    """
    import threading
    from concurrent.futures import ThreadPoolExecutor

    cache = cache or LicenseCache()
    client = client or RegistryClient()
    resolved: list[ResolvedLicense] = []
    lock = threading.Lock()

    # Dedupe by (manager, name, version) — many projects pull "react@18.2.0",
    # one resolution serves them all.
    seen: dict[tuple[str, str, str | None], ResolvedLicense] = {}
    order: list[tuple[str, str, str | None]] = []
    for dep in deps:
        key = (dep["manager"], dep["name"], dep.get("version"))
        if key not in seen:
            order.append(key)
            seen[key] = ResolvedLicense(
                name=dep["name"],
                version=dep.get("version"),
                manager=dep["manager"],
                spdx=None,
                source="unsupported",
            )

    total = len(order)
    completed = 0

    def _bump():
        nonlocal completed
        with lock:
            completed += 1
            if on_progress:
                on_progress(completed, total)

    def _resolve_one(key):
        manager, name, version = key
        cached = cache.get(manager, name, version)
        if cached is not None:
            spdx, source = cached
            seen[key] = ResolvedLicense(
                name=name, version=version, manager=manager, spdx=spdx, source=source
            )
            _bump()
            return

        resolver_cls = _RESOLVERS.get(manager)
        if resolver_cls is None:
            # No resolver for this ecosystem — leave unresolved, don't cache
            # negative result (we might add the ecosystem later).
            seen[key] = ResolvedLicense(
                name=name, version=version, manager=manager, spdx=None, source="unsupported"
            )
            _bump()
            return

        resolver = resolver_cls(client)
        try:
            spdx, source = resolver.resolve(name, version)
        except Exception:
            # Registry call failed entirely (network, parse error). Treat as
            # unresolved but cache it so we don't retry on every run — the
            # cache TTL story can come in v2 if it matters.
            spdx, source = None, manager

        cache.put(manager, name, version, spdx, source)
        seen[key] = ResolvedLicense(
            name=name, version=version, manager=manager, spdx=spdx, source=source
        )
        _bump()

    if total > 0:
        with ThreadPoolExecutor(max_workers=6) as pool:
            list(pool.map(_resolve_one, order))

    # Re-emit in *original dependency-list order*, with duplicates expanded
    # so the caller's per-project SBOM has one row per dep (not deduped).
    for dep in deps:
        key = (dep["manager"], dep["name"], dep.get("version"))
        entry = seen[key]
        resolved.append(
            ResolvedLicense(
                name=entry.name,
                version=entry.version,
                manager=entry.manager,
                spdx=entry.spdx,
                source=entry.source,
            )
        )
    return resolved


__all__ = ["LicenseCache", "RegistryClient", "ResolvedLicense", "resolve_all"]
