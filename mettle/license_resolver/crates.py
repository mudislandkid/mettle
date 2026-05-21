"""crates.io resolver. Queries `https://crates.io/api/v1/crates/<name>/<version>`.

Cargo enforces SPDX-style license expressions in `Cargo.toml`, so the value
the registry returns is already pretty close to canonical. We still run it
through `normalize()` to pick the first operand of expressions like
"MIT OR Apache-2.0".
"""

from __future__ import annotations

from .http import RegistryClient
from .spdx import normalize

_REGISTRY = "https://crates.io/api/v1/crates"


class CratesResolver:
    def __init__(self, client: RegistryClient):
        self.client = client

    def resolve(self, name: str, version: str | None) -> tuple[str | None, str]:
        if version:
            url = f"{_REGISTRY}/{name}/{version}"
        else:
            url = f"{_REGISTRY}/{name}"
        payload = self.client.get_json(url)
        return self._parse(payload, has_version=bool(version)), "crates"

    @staticmethod
    def _parse(payload: dict | None, has_version: bool = False) -> str | None:
        if not isinstance(payload, dict):
            return None
        # `/crates/{name}/{version}` returns {"version": {... "license": ...}}.
        # `/crates/{name}` returns {"crate": {...}, "versions": [...]}; pick
        # the newest non-yanked entry.
        if has_version:
            v = payload.get("version") or {}
            if isinstance(v, dict):
                lic = v.get("license")
                if isinstance(lic, str):
                    return normalize(lic)
            return None
        versions = payload.get("versions") or []
        if isinstance(versions, list):
            for v in versions:
                if not isinstance(v, dict):
                    continue
                if v.get("yanked"):
                    continue
                lic = v.get("license")
                if isinstance(lic, str):
                    return normalize(lic)
        return None
