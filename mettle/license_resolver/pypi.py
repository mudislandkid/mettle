"""PyPI resolver. Queries `https://pypi.org/pypi/<name>/<version>/json`.

License precedence:
    1. `info.license_expression` (PEP 639 — current best practice).
    2. `info.classifiers` — the `License :: OSI Approved :: <X>` family.
    3. `info.license` — a free-form string. Last resort because authors
       often put "MIT" or a 600-character paragraph here.
"""

from __future__ import annotations

from .http import RegistryClient
from .spdx import normalize
from .versions import concrete_version

_REGISTRY = "https://pypi.org/pypi"

# Map common PyPI classifiers onto SPDX ids. PyPI's classifier vocabulary is
# stable; this table only needs additions when a new classifier is rolled out.
_CLASSIFIER_TO_SPDX = {
    "License :: OSI Approved :: MIT License": "MIT",
    "License :: OSI Approved :: Apache Software License": "Apache-2.0",
    "License :: OSI Approved :: BSD License": "BSD-3-Clause",
    "License :: OSI Approved :: ISC License (ISCL)": "ISC",
    "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)": "MPL-2.0",
    "License :: OSI Approved :: GNU General Public License v2 (GPLv2)": "GPL-2.0-only",
    "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)": "GPL-2.0-or-later",
    "License :: OSI Approved :: GNU General Public License v3 (GPLv3)": "GPL-3.0-only",
    "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)": "GPL-3.0-or-later",
    "License :: OSI Approved :: GNU Lesser General Public License v2 (LGPLv2)": "LGPL-2.0-only",
    "License :: OSI Approved :: GNU Lesser General Public License v2 or later (LGPLv2+)": "LGPL-2.0-or-later",
    "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)": "LGPL-3.0-only",
    "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)": "LGPL-3.0-or-later",
    "License :: OSI Approved :: GNU Affero General Public License v3": "AGPL-3.0-only",
    "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)": "AGPL-3.0-or-later",
    "License :: OSI Approved :: Python Software Foundation License": "PSF-2.0",
    "License :: OSI Approved :: zlib/libpng License": "Zlib",
    "License :: Public Domain": "CC0-1.0",
    "License :: CC0 1.0 Universal (CC0 1.0) Public Domain Dedication": "CC0-1.0",
}


class PyPiResolver:
    def __init__(self, client: RegistryClient):
        self.client = client

    def resolve(self, name: str, version: str | None) -> tuple[str | None, str]:
        # Manifest version is typically a PEP 508 constraint (`>=0.115`,
        # `~=2.1`). Only pass it through when it looks like a specific
        # release; otherwise hit the registry's catch-all (latest) endpoint.
        concrete = concrete_version(version)
        url = f"{_REGISTRY}/{name}/{concrete}/json" if concrete else f"{_REGISTRY}/{name}/json"
        payload = self.client.get_json(url)
        return self._parse(payload), "pypi"

    @staticmethod
    def _parse(payload: dict | None) -> str | None:
        if not isinstance(payload, dict):
            return None
        info = payload.get("info") or {}
        if not isinstance(info, dict):
            return None

        # 1. PEP 639 license_expression
        expr = info.get("license_expression")
        if isinstance(expr, str):
            normalized = normalize(expr)
            if normalized:
                return normalized

        # 2. Classifiers
        classifiers = info.get("classifiers") or []
        if isinstance(classifiers, list):
            for c in classifiers:
                if isinstance(c, str) and c in _CLASSIFIER_TO_SPDX:
                    return _CLASSIFIER_TO_SPDX[c]

        # 3. Free-form info.license
        lic = info.get("license")
        if isinstance(lic, str):
            # Sometimes the field holds the entire license body — don't try
            # to normalise that. Cap at 200 chars before passing to normaliser.
            if len(lic) < 200:
                normalized = normalize(lic)
                if normalized:
                    return normalized
        return None
