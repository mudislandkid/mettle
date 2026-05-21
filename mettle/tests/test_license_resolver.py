"""Tests for the license_resolver package (ENHANCEMENTS #24).

Covers pure logic (SPDX normalisation, copyleft sets, per-registry parsers)
and the orchestrator with a fake registry client so no network is hit.
"""

from __future__ import annotations

import threading
import urllib.error

import pytest

from mettle.license_resolver import resolve_all
from mettle.license_resolver.cache import LicenseCache
from mettle.license_resolver.crates import CratesResolver
from mettle.license_resolver.http import RegistryClient, RegistryError
from mettle.license_resolver.npm import NpmResolver
from mettle.license_resolver.pypi import PyPiResolver
from mettle.license_resolver.runner import resolve_project
from mettle.license_resolver.spdx import (
    COPYLEFT_STRONG,
    COPYLEFT_WEAK,
    is_copyleft,
    normalize,
)

# ─── SPDX normaliser ───────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("MIT", "MIT"),
        ("MIT License", "MIT"),
        ("mit", "MIT"),
        ("(MIT)", "MIT"),
        ("Apache 2.0", "Apache-2.0"),
        ("apache-2.0", "Apache-2.0"),
        ("Apache Software License", "Apache-2.0"),
        ("BSD-3-Clause", "BSD-3-Clause"),
        ("BSD", "BSD-3-Clause"),
        ("GPL-3.0-or-later", "GPL-3.0-or-later"),
        ("AGPL-3.0+", "AGPL-3.0-or-later"),
        ("MIT OR Apache-2.0", "MIT"),
        ("Apache-2.0 AND MIT", "Apache-2.0"),
        ("Zlib", "Zlib"),  # falls through canonical-shape detection
        ("0BSD", "0BSD"),
        ("", None),
        (None, None),
        ("SEE LICENSE IN FILE", None),
        ("Other/Proprietary License", None),
        ("NOASSERTION", None),
    ],
)
def test_normalize(raw, expected):
    assert normalize(raw) == expected


def test_copyleft_sets_are_disjoint():
    """Strong and weak copyleft sets must not overlap — a license is one or
    the other, never both."""
    assert COPYLEFT_STRONG.isdisjoint(COPYLEFT_WEAK)


@pytest.mark.parametrize(
    "spdx,expected",
    [
        ("GPL-3.0-only", "strong"),
        ("AGPL-3.0-or-later", "strong"),
        ("LGPL-2.1-or-later", "weak"),
        ("MPL-2.0", "weak"),
        ("MIT", None),
        ("Apache-2.0", None),
        (None, None),
        ("", None),
    ],
)
def test_is_copyleft(spdx, expected):
    assert is_copyleft(spdx) == expected


# ─── Per-registry parsers ──────────────────────────────────────────────────


def test_npm_parse_handles_all_three_legacy_shapes():
    assert NpmResolver._parse({"license": "MIT"}) == "MIT"
    assert NpmResolver._parse({"license": {"type": "Apache-2.0"}}) == "Apache-2.0"
    assert NpmResolver._parse({"license": ["BSD-3-Clause", "ISC"]}) == "BSD-3-Clause"
    assert NpmResolver._parse({"licenses": [{"type": "ISC"}]}) == "ISC"  # plural legacy form
    assert NpmResolver._parse({}) is None
    assert NpmResolver._parse(None) is None


def test_pypi_parse_prefers_license_expression_then_classifiers_then_freeform():
    assert PyPiResolver._parse({"info": {"license_expression": "Apache-2.0"}}) == "Apache-2.0"
    assert (
        PyPiResolver._parse({"info": {"classifiers": ["License :: OSI Approved :: MIT License"]}})
        == "MIT"
    )
    assert PyPiResolver._parse({"info": {"license": "BSD-3-Clause"}}) == "BSD-3-Clause"
    # 500-char paragraph in info.license must not be treated as the license id
    big = "x" * 600
    assert PyPiResolver._parse({"info": {"license": big}}) is None


def test_crates_parse_versioned_and_unversioned():
    assert CratesResolver._parse({"version": {"license": "MIT"}}, has_version=True) == "MIT"
    payload = {"versions": [{"license": "Apache-2.0", "yanked": False}]}
    assert CratesResolver._parse(payload) == "Apache-2.0"
    # Skips yanked versions
    payload = {
        "versions": [
            {"license": "MIT", "yanked": True},
            {"license": "Apache-2.0", "yanked": False},
        ]
    }
    assert CratesResolver._parse(payload) == "Apache-2.0"


# ─── Cache ─────────────────────────────────────────────────────────────────


def test_cache_round_trip(tmp_path):
    cache = LicenseCache(path=tmp_path / "lic.sqlite3")
    assert cache.get("npm", "react", "18.2.0") is None
    cache.put("npm", "react", "18.2.0", "MIT", "npm")
    assert cache.get("npm", "react", "18.2.0") == ("MIT", "npm")


def test_cache_negative_hit_is_distinct_from_miss(tmp_path):
    """A stored None spdx must read back as (None, source) so we don't refetch."""
    cache = LicenseCache(path=tmp_path / "lic.sqlite3")
    cache.put("pypi", "some-pkg", "1.0", None, "pypi")
    assert cache.get("pypi", "some-pkg", "1.0") == (None, "pypi")


def test_cache_versionless_keys_work(tmp_path):
    cache = LicenseCache(path=tmp_path / "lic.sqlite3")
    cache.put("npm", "left-pad", None, "WTFPL", "npm")
    assert cache.get("npm", "left-pad", None) == ("WTFPL", "npm")
    # Different version must miss
    assert cache.get("npm", "left-pad", "1.0.0") is None


# ─── Orchestrator with fake client ─────────────────────────────────────────


class _FakeClient:
    """RegistryClient stand-in. Returns canned JSON payloads keyed by URL."""

    def __init__(self, payloads: dict[str, dict | None]):
        self.payloads = payloads
        self.calls: list[str] = []
        self._lock = threading.Lock()

    def get_json(self, url: str):
        with self._lock:
            self.calls.append(url)
        if url not in self.payloads:
            return None
        return self.payloads[url]


def test_resolve_all_uses_cache_for_repeats(tmp_path):
    cache = LicenseCache(path=tmp_path / "lic.sqlite3")
    client = _FakeClient(
        {
            "https://registry.npmjs.org/react/18.2.0": {"license": "MIT"},
            "https://pypi.org/pypi/flask/3.0.0/json": {
                "info": {"license_expression": "BSD-3-Clause"}
            },
        }
    )
    deps = [
        {"name": "react", "version": "18.2.0", "manager": "npm"},
        {"name": "react", "version": "18.2.0", "manager": "npm"},  # duplicate
        {"name": "flask", "version": "3.0.0", "manager": "pypi"},
    ]
    out = resolve_all(deps, cache=cache, client=client)
    assert [(r.name, r.spdx) for r in out] == [
        ("react", "MIT"),
        ("react", "MIT"),
        ("flask", "BSD-3-Clause"),
    ]
    # Duplicate didn't trigger a second network call.
    assert client.calls.count("https://registry.npmjs.org/react/18.2.0") == 1

    # Second resolve hits the cache for everything.
    client2 = _FakeClient({})  # no payloads — must serve from cache
    out2 = resolve_all(deps, cache=cache, client=client2)
    assert [(r.name, r.spdx) for r in out2] == [
        ("react", "MIT"),
        ("react", "MIT"),
        ("flask", "BSD-3-Clause"),
    ]
    assert client2.calls == []


def test_resolve_all_unsupported_manager_stays_unresolved(tmp_path):
    cache = LicenseCache(path=tmp_path / "lic.sqlite3")
    client = _FakeClient({})
    out = resolve_all(
        [{"name": "anything", "version": "1.0", "manager": "go"}],
        cache=cache,
        client=client,
    )
    assert out[0].spdx is None
    assert out[0].source == "unsupported"
    # Unsupported ecosystem must NOT be cached — that way if we add a Go
    # resolver later, the next run picks up the resolution.
    assert cache.get("go", "anything", "1.0") is None


# ─── Per-project runner ────────────────────────────────────────────────────


def test_runner_flags_strong_copyleft_in_proprietary_project(tmp_path):
    cache = LicenseCache(path=tmp_path / "lic.sqlite3")
    client = _FakeClient(
        {
            "https://registry.npmjs.org/gpl-thing/1.0": {"license": "GPL-3.0-only"},
            "https://registry.npmjs.org/mit-thing/2.0": {"license": "MIT"},
        }
    )
    deps = [
        {"name": "gpl-thing", "version": "1.0", "manager": "npm"},
        {"name": "mit-thing", "version": "2.0", "manager": "npm"},
    ]
    licenses, summary, has_risk = resolve_project(
        deps,
        project_license_spdx=None,
        project_flags=["proprietary"],
        cache=cache,
        client=client,
    )
    assert summary["resolved"] == 2
    assert summary["copyleft_strong"] == 1
    assert summary["by_spdx"]["GPL-3.0-only"] == 1
    assert has_risk is True

    # Same deps on an MIT-licensed project must NOT trip the risk flag.
    _, _, mit_risk = resolve_project(
        deps,
        project_license_spdx="MIT",
        project_flags=[],
        cache=cache,
        client=client,
    )
    assert mit_risk is False


# ─── HTTP wrapper smoke test ───────────────────────────────────────────────


def test_http_404_returns_none(monkeypatch):
    """A 404 from the registry means "no such package" — not an error."""

    def fake_urlopen(req, timeout):
        raise urllib.error.HTTPError(
            url=req.full_url, code=404, msg="not found", hdrs=None, fp=None
        )

    monkeypatch.setattr("mettle.license_resolver.http.urllib.request.urlopen", fake_urlopen)
    client = RegistryClient(retries=0)
    assert client.get_json("https://example.invalid/whatever") is None


def test_http_500_after_retries_raises(monkeypatch):
    calls = {"n": 0}

    def fake_urlopen(req, timeout):
        calls["n"] += 1
        raise urllib.error.HTTPError(url=req.full_url, code=503, msg="busy", hdrs=None, fp=None)

    monkeypatch.setattr("mettle.license_resolver.http.urllib.request.urlopen", fake_urlopen)
    # No real sleeping in tests — patch out backoff.
    monkeypatch.setattr("mettle.license_resolver.http.time.sleep", lambda *_: None)
    client = RegistryClient(retries=2)
    with pytest.raises(RegistryError):
        client.get_json("https://example.invalid/whatever")
    assert calls["n"] == 3  # initial + 2 retries
