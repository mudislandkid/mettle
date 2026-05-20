"""Tests for mettle.license_detection — SPDX matching via top-level LICENSE
files and pyproject/package.json metadata fallback."""

import pytest

from mettle.license_corpus import SPDX_CORPUS
from mettle.license_detection import detect_license

# ---------------- canonical text matches (parametrized) ----------------


@pytest.mark.parametrize("spdx_id", ["MIT", "Apache-2.0", "BSD-3-Clause", "GPL-3.0-only", "ISC"])
def test_detects_canonical_license_file(spdx_id, tmp_path):
    (tmp_path / "LICENSE").write_text(SPDX_CORPUS[spdx_id])
    assert detect_license(tmp_path) == spdx_id


# ---------------- filename variations (parametrized) ----------------


@pytest.mark.parametrize("filename", ["LICENSE", "LICENCE", "COPYING", "LICENSE.md", "LICENSE.txt"])
def test_detects_alternate_filenames(filename, tmp_path):
    (tmp_path / filename).write_text(SPDX_CORPUS["MIT"])
    assert detect_license(tmp_path) == "MIT"


# ---------------- cosmetic tolerance ----------------


def test_detects_license_with_custom_copyright_line(tmp_path):
    text = "Copyright (c) 2026 Some Project Name\n\n" + SPDX_CORPUS["MIT"]
    (tmp_path / "LICENSE").write_text(text)
    assert detect_license(tmp_path) == "MIT"


# ---------------- negatives ----------------


def test_returns_none_when_no_license_file(tmp_path):
    assert detect_license(tmp_path) is None


def test_returns_none_for_unknown_license(tmp_path):
    (tmp_path / "LICENSE").write_text("All your code are belong to us.")
    assert detect_license(tmp_path) is None


def test_handles_unreadable_license_file(tmp_path):
    bad = tmp_path / "LICENSE"
    bad.write_bytes(b"\xff\xfe\xfd not a real license")
    # Should not crash; lossy decode produces non-matching content
    assert detect_license(tmp_path) is None


# ---------------- metadata fallback ----------------


def test_falls_back_to_pyproject_license_string(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nlicense = "MIT"\n')
    assert detect_license(tmp_path) == "MIT"


def test_falls_back_to_pyproject_license_dict_text(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nlicense = { text = "Apache-2.0" }\n')
    assert detect_license(tmp_path) == "Apache-2.0"


def test_falls_back_to_package_json_license(tmp_path):
    (tmp_path / "package.json").write_text('{"license": "ISC"}')
    assert detect_license(tmp_path) == "ISC"


def test_rejects_unrecognised_metadata_value(tmp_path):
    """'MIT License' is not a canonical SPDX id — return None, don't echo."""
    (tmp_path / "pyproject.toml").write_text('[project]\nlicense = "MIT License"\n')
    assert detect_license(tmp_path) is None


def test_malformed_pyproject_is_graceful(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project\n  license = 'oops")
    assert detect_license(tmp_path) is None


def test_license_file_wins_over_metadata(tmp_path):
    """If both LICENSE file and pyproject metadata exist, the file wins."""
    (tmp_path / "LICENSE").write_text(SPDX_CORPUS["MIT"])
    (tmp_path / "pyproject.toml").write_text('[project]\nlicense = "Apache-2.0"\n')
    assert detect_license(tmp_path) == "MIT"
