"""Tests for mettle.digest — built up incrementally across Tasks 2-4."""

from mettle.digest import _diff_dependencies

# ---------- _diff_dependencies (5 tests) ----------


def test_diff_dependencies_added_only():
    diff = _diff_dependencies(
        [],
        [{"name": "click", "version": "8.1.0", "manager": "pypi"}],
    )
    assert diff == {
        "added": [{"name": "click", "manager": "pypi"}],
        "removed": [],
        "bumped": [],
    }


def test_diff_dependencies_removed_only():
    diff = _diff_dependencies(
        [{"name": "click", "version": "8.1.0", "manager": "pypi"}],
        [],
    )
    assert diff == {
        "added": [],
        "removed": [{"name": "click", "manager": "pypi"}],
        "bumped": [],
    }


def test_diff_dependencies_bumped_only():
    diff = _diff_dependencies(
        [{"name": "click", "version": "8.1.0", "manager": "pypi"}],
        [{"name": "click", "version": "8.2.0", "manager": "pypi"}],
    )
    assert diff == {
        "added": [],
        "removed": [],
        "bumped": [{"name": "click", "manager": "pypi", "from": "8.1.0", "to": "8.2.0"}],
    }


def test_diff_dependencies_mixed():
    diff = _diff_dependencies(
        [
            {"name": "click", "version": "8.1.0", "manager": "pypi"},
            {"name": "vuex", "version": "4.0.0", "manager": "npm"},
        ],
        [
            {"name": "click", "version": "8.2.0", "manager": "pypi"},
            {"name": "zod", "version": "3.22.0", "manager": "npm"},
        ],
    )
    # added: zod; removed: vuex; bumped: click
    assert {"name": "zod", "manager": "npm"} in diff["added"]
    assert {"name": "vuex", "manager": "npm"} in diff["removed"]
    assert len(diff["bumped"]) == 1 and diff["bumped"][0]["name"] == "click"


def test_diff_dependencies_manager_disambiguates():
    """Same name under different manager is a different dep — both add+remove fire."""
    diff = _diff_dependencies(
        [{"name": "click", "version": "8.1.0", "manager": "pypi"}],
        [{"name": "click", "version": "1.0.0", "manager": "npm"}],
    )
    assert {"name": "click", "manager": "pypi"} in diff["removed"]
    assert {"name": "click", "manager": "npm"} in diff["added"]
    assert diff["bumped"] == []
