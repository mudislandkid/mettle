"""npm registry resolver. Queries `https://registry.npmjs.org/<name>/<version>`.

The `license` field has three historical shapes:
    - "MIT"                              (current, since npm 3+)
    - {"type": "MIT", "url": "..."}      (old, still in many published packages)
    - ["MIT", "BSD-3-Clause"]            (old "multiple licenses" form)

Anything we can't parse maps to None — the caller decides what to do with that.
"""

from __future__ import annotations

from .http import RegistryClient
from .spdx import normalize

_REGISTRY = "https://registry.npmjs.org"


class NpmResolver:
    def __init__(self, client: RegistryClient):
        self.client = client

    def resolve(self, name: str, version: str | None) -> tuple[str | None, str]:
        # Versionless: ask the registry for "latest". Better than guessing.
        url = f"{_REGISTRY}/{name}/{version}" if version else f"{_REGISTRY}/{name}/latest"
        payload = self.client.get_json(url)
        return self._parse(payload), "npm"

    @staticmethod
    def _parse(payload: dict | None) -> str | None:
        if not isinstance(payload, dict):
            return None
        lic = payload.get("license")
        # The {type, url} form
        if isinstance(lic, dict):
            lic = lic.get("type")
        # The ["MIT", "BSD-3-Clause"] form
        if isinstance(lic, list) and lic:
            first = lic[0]
            if isinstance(first, dict):
                first = first.get("type")
            lic = first
        if isinstance(lic, str):
            return normalize(lic)
        # `licenses` (plural) is the very old shape — same dict/list rules.
        legacy = payload.get("licenses")
        if isinstance(legacy, list) and legacy:
            first = legacy[0]
            if isinstance(first, dict):
                first = first.get("type")
            if isinstance(first, str):
                return normalize(first)
        return None
