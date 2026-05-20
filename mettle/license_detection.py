"""SPDX license detector. Top-level LICENSE-named file matched against the
~230KB corpus in mettle.license_corpus; falls back to pyproject.toml or
package.json metadata fields when the file path comes up empty."""

from __future__ import annotations

import json
import re
from pathlib import Path

try:
    import tomllib  # py311+
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore

from .license_corpus import SPDX_CORPUS

LICENSE_FILENAMES = (
    "LICENSE",
    "LICENCE",
    "COPYING",
    "UNLICENSE",
    "LICENSE.md",
    "LICENCE.md",
    "COPYING.md",
    "LICENSE.txt",
    "LICENCE.txt",
    "COPYING.txt",
    "LICENSE.rst",
    "LICENCE.rst",
)

MAX_LICENSE_BYTES = 65_536  # read up to 64KB; GPL-3.0-only is ~34KB

_WHITESPACE = re.compile(r"\s+")
_PUNCT_AND_COPYRIGHT = re.compile(
    r"(?:copyright\s+\(c\)\s*\d{4}(?:\s*[-,]\s*\d{4})?\s*[^\n]*\n?"
    r"|[(){}\[\]<>.,;:'\"!?*\-_/\\])",
    re.IGNORECASE,
)


def _normalize(text: str) -> str:
    """Lowercase, strip copyright lines + punctuation, collapse whitespace."""
    text = _PUNCT_AND_COPYRIGHT.sub(" ", text)
    return _WHITESPACE.sub(" ", text.lower()).strip()


def _find_license_file(project_path: Path) -> Path | None:
    for name in LICENSE_FILENAMES:
        candidate = project_path / name
        if candidate.is_file():
            return candidate
    return None


def _match_corpus(normalised_content: str) -> str | None:
    for spdx_id, canonical in SPDX_CORPUS.items():
        if _normalize(canonical) in normalised_content:
            return spdx_id
    return None


def _coerce_to_spdx_id(raw: str) -> str | None:
    """Strict case-insensitive lookup against the corpus keys. 'MIT License'
    → None. 'mit' → 'MIT'. 'Apache 2.0' → None (canonical id is 'Apache-2.0';
    we don't fuzz word boundaries)."""
    lookup = {sid.lower(): sid for sid in SPDX_CORPUS}
    return lookup.get(raw.lower())


def _read_metadata_license(project_path: Path) -> str | None:
    pyproject = project_path / "pyproject.toml"
    if pyproject.is_file():
        try:
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            data = {}
        license_field = data.get("project", {}).get("license")
        if isinstance(license_field, dict):
            text = license_field.get("text")
            if isinstance(text, str) and text.strip():
                return _coerce_to_spdx_id(text.strip())
        elif isinstance(license_field, str) and license_field.strip():
            return _coerce_to_spdx_id(license_field.strip())

    package_json = project_path / "package.json"
    if package_json.is_file():
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        license_field = data.get("license")
        if isinstance(license_field, str) and license_field.strip():
            return _coerce_to_spdx_id(license_field.strip())

    return None


def detect_license(project_path: Path) -> str | None:
    """Return the SPDX id of this project's license, or None.

    Tries the top-level LICENSE-named file (matched against the 20-license
    SPDX corpus) first, then the `license` field in pyproject.toml or
    package.json.
    """
    license_file = _find_license_file(project_path)
    if license_file is not None:
        try:
            content = license_file.read_text(encoding="utf-8", errors="replace")[:MAX_LICENSE_BYTES]
        except OSError:
            content = ""
        if content:
            spdx_id = _match_corpus(_normalize(content))
            if spdx_id is not None:
                return spdx_id

    return _read_metadata_license(project_path)
