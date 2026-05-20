"""Tests for mettle.digest — built up incrementally across Tasks 2-4."""

from datetime import datetime, timedelta, timezone

from sqlmodel import Session, SQLModel, create_engine

from mettle.digest import (
    SECTION_ORDER,
    _classify_project,
    _diff_dependencies,
    _section_biggest_swing,
    _section_dependency_drift,
    _section_grown_most,
    _section_new_since,
    _section_newly_stale,
    _section_stalled_with_todos,
    compute_digest,
    render_json,
    render_markdown,
)
from web.backend.database.models import Analysis, Project

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


# ---------- _classify_project (4 tests) ----------


def _make_engine():
    e = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(e)
    return e


def _seed(
    session,
    path,
    analyzed_at,
    *,
    code_lines=100,
    todos=0,
    last_commit_at=None,
    dependencies=None,
):
    """Insert one Analysis + one Project. Returns the Project."""
    a = Analysis(directory_path=path, analyzed_at=analyzed_at, status="completed")
    session.add(a)
    session.flush()
    p = Project(
        analysis_id=a.id,
        name=path.split("/")[-1],
        path=path,
        code_lines=code_lines,
        total_lines=code_lines,
        todos=todos,
        last_commit_at=last_commit_at,
        dependencies=dependencies or [],
    )
    session.add(p)
    session.flush()
    return p


def test_classify_with_baseline():
    now = datetime(2026, 5, 20, tzinfo=timezone.utc)
    window_start = now - timedelta(days=7)
    engine = _make_engine()
    with Session(engine) as s:
        old = _seed(s, "/p", now - timedelta(days=14))
        new = _seed(s, "/p", now - timedelta(days=1))
        history = [new, old]  # DESC by analyzed_at
        analyzed_at_by_id = {
            old.analysis_id: now - timedelta(days=14),
            new.analysis_id: now - timedelta(days=1),
        }
        bucket, current, baseline = _classify_project(history, analyzed_at_by_id, window_start)
        assert bucket == "with_baseline"
        assert current.analysis_id == new.analysis_id
        assert baseline.analysis_id == old.analysis_id


def test_classify_new_only():
    now = datetime(2026, 5, 20, tzinfo=timezone.utc)
    window_start = now - timedelta(days=7)
    engine = _make_engine()
    with Session(engine) as s:
        only = _seed(s, "/p", now - timedelta(days=2))
        history = [only]
        analyzed_at_by_id = {only.analysis_id: now - timedelta(days=2)}
        bucket, current, baseline = _classify_project(history, analyzed_at_by_id, window_start)
        assert bucket == "new"
        assert baseline is None


def test_classify_no_recent():
    now = datetime(2026, 5, 20, tzinfo=timezone.utc)
    window_start = now - timedelta(days=7)
    engine = _make_engine()
    with Session(engine) as s:
        old = _seed(s, "/p", now - timedelta(days=30))
        history = [old]
        analyzed_at_by_id = {old.analysis_id: now - timedelta(days=30)}
        bucket, current, baseline = _classify_project(history, analyzed_at_by_id, window_start)
        assert bucket == "no_recent"


def test_classify_picks_newest_baseline():
    """Baseline = newest analysis < window_start (DESC iteration finds it first)."""
    now = datetime(2026, 5, 20, tzinfo=timezone.utc)
    window_start = now - timedelta(days=7)
    engine = _make_engine()
    with Session(engine) as s:
        oldest = _seed(s, "/p", now - timedelta(days=60))
        middle = _seed(s, "/p", now - timedelta(days=20))
        newest = _seed(s, "/p", now - timedelta(days=1))
        history = [newest, middle, oldest]
        analyzed_at_by_id = {
            oldest.analysis_id: now - timedelta(days=60),
            middle.analysis_id: now - timedelta(days=20),
            newest.analysis_id: now - timedelta(days=1),
        }
        bucket, current, baseline = _classify_project(history, analyzed_at_by_id, window_start)
        assert baseline.analysis_id == middle.analysis_id  # newest qualifying baseline


# ---------- _section_* (8 tests) ----------


def _make_pair(
    path,
    *,
    baseline_lines,
    current_lines,
    todos=0,
    last_commit_at=None,
    baseline_deps=None,
    current_deps=None,
):
    """Build a (current, baseline) Project pair for section tests."""
    engine = _make_engine()
    with Session(engine) as s:
        baseline = _seed(
            s,
            path,
            datetime(2026, 5, 13, tzinfo=timezone.utc),
            code_lines=baseline_lines,
            dependencies=baseline_deps or [],
        )
        current = _seed(
            s,
            path,
            datetime(2026, 5, 20, tzinfo=timezone.utc),
            code_lines=current_lines,
            todos=todos,
            last_commit_at=last_commit_at,
            dependencies=current_deps or [],
        )
        return current, baseline


def test_grown_most_excludes_zero_and_negative():
    pairs = [
        _make_pair("/a", baseline_lines=100, current_lines=200),  # +100
        _make_pair("/b", baseline_lines=100, current_lines=100),  # 0  excluded
        _make_pair("/c", baseline_lines=200, current_lines=100),  # -100 excluded
    ]
    entries = _section_grown_most(pairs, top_n=10)
    assert len(entries) == 1
    assert entries[0].project_path == "/a"
    assert entries[0].headline_value == 100


def test_grown_most_ordering_and_top_n():
    pairs = [
        _make_pair("/a", baseline_lines=100, current_lines=200),  # +100
        _make_pair("/b", baseline_lines=100, current_lines=400),  # +300
        _make_pair("/c", baseline_lines=100, current_lines=150),  # +50
    ]
    entries = _section_grown_most(pairs, top_n=2)
    assert [e.project_path for e in entries] == ["/b", "/a"]


def test_biggest_swing_includes_negative_abs_sort():
    pairs = [
        _make_pair("/a", baseline_lines=1000, current_lines=500),  # -500
        _make_pair("/b", baseline_lines=100, current_lines=300),  # +200
        _make_pair("/c", baseline_lines=100, current_lines=100),  # 0  excluded
    ]
    entries = _section_biggest_swing(pairs, top_n=10)
    assert [e.project_path for e in entries] == ["/a", "/b"]
    assert entries[0].headline_label.startswith("-")


def test_dependency_drift_total_is_sum():
    deps_old = [{"name": "vue", "version": "3.4.0", "manager": "npm"}]
    deps_new = [
        {"name": "vue", "version": "3.5.0", "manager": "npm"},  # bumped
        {"name": "zod", "version": "3.22.0", "manager": "npm"},  # added
    ]
    pairs = [
        _make_pair(
            "/a",
            baseline_lines=100,
            current_lines=100,
            baseline_deps=deps_old,
            current_deps=deps_new,
        )
    ]
    entries = _section_dependency_drift(pairs, top_n=10)
    assert len(entries) == 1
    assert entries[0].headline_value == 2  # 1 added + 1 bumped


def test_dependency_drift_excludes_zero_change():
    pairs = [
        _make_pair(
            "/a",
            baseline_lines=100,
            current_lines=100,
            baseline_deps=[{"name": "vue", "version": "3.4.0", "manager": "npm"}],
            current_deps=[{"name": "vue", "version": "3.4.0", "manager": "npm"}],
        )
    ]
    entries = _section_dependency_drift(pairs, top_n=10)
    assert entries == []


def test_stalled_with_todos_requires_both_conditions():
    now = datetime(2026, 5, 20, tzinfo=timezone.utc)
    stale_threshold = now - timedelta(days=30)
    # stale + todos
    pairs1 = [
        _make_pair(
            "/a",
            baseline_lines=100,
            current_lines=100,
            todos=5,
            last_commit_at=stale_threshold - timedelta(days=10),
        )
    ]
    assert len(_section_stalled_with_todos(pairs1, 10, now, 30)) == 1
    # stale but no todos
    pairs2 = [
        _make_pair(
            "/b",
            baseline_lines=100,
            current_lines=100,
            todos=0,
            last_commit_at=stale_threshold - timedelta(days=10),
        )
    ]
    assert _section_stalled_with_todos(pairs2, 10, now, 30) == []
    # active but has todos
    pairs3 = [
        _make_pair(
            "/c",
            baseline_lines=100,
            current_lines=100,
            todos=5,
            last_commit_at=now - timedelta(days=1),
        )
    ]
    assert _section_stalled_with_todos(pairs3, 10, now, 30) == []


def test_newly_stale_crossed_during_window():
    now = datetime(2026, 5, 20, tzinfo=timezone.utc)
    window_start = now - timedelta(days=7)
    stale_days = 30
    # Crossed during window: last_commit was 25d ago at start of window, now 32d ago
    pairs1 = [
        _make_pair(
            "/a", baseline_lines=100, current_lines=100, last_commit_at=now - timedelta(days=32)
        )
    ]
    assert len(_section_newly_stale(pairs1, 10, now, window_start, stale_days)) == 1
    # Already stale before window
    pairs2 = [
        _make_pair(
            "/b", baseline_lines=100, current_lines=100, last_commit_at=now - timedelta(days=60)
        )
    ]
    assert _section_newly_stale(pairs2, 10, now, window_start, stale_days) == []
    # Still active
    pairs3 = [
        _make_pair(
            "/c", baseline_lines=100, current_lines=100, last_commit_at=now - timedelta(days=10)
        )
    ]
    assert _section_newly_stale(pairs3, 10, now, window_start, stale_days) == []


def test_new_since_full_list_no_top_n():
    """new_since/no_recent_activity are coverage sections — not capped."""
    # Build 7 'new' projects
    engine = _make_engine()
    with Session(engine) as s:
        news = [
            _seed(s, f"/p{i}", datetime(2026, 5, 19, tzinfo=timezone.utc), code_lines=100 * (i + 1))
            for i in range(7)
        ]
        analyzed_at_by_id = {
            p.analysis_id: datetime(2026, 5, 19, tzinfo=timezone.utc) for p in news
        }
        entries = _section_new_since(news, analyzed_at_by_id)
        # All 7, no cap
        assert len(entries) == 7


# ---------- compute_digest end-to-end (4 tests) ----------


def test_compute_digest_seven_sections_in_fixed_order():
    """Even an empty DB produces all 7 sections in stable order."""
    engine = _make_engine()
    with Session(engine) as s:
        report = compute_digest(s)
    assert len(report.sections) == 7
    kinds = [sec.kind for sec in report.sections]
    assert kinds == [k for (k, _t, _d) in SECTION_ORDER]
    assert report.total_projects == 0


def test_compute_digest_coverage_counts():
    """Three projects across three buckets — coverage counts correct."""
    now = datetime(2026, 5, 20, tzinfo=timezone.utc)
    engine = _make_engine()
    with Session(engine) as s:
        # with_baseline
        _seed(s, "/a", now - timedelta(days=14), code_lines=100)
        _seed(s, "/a", now - timedelta(days=1), code_lines=200)
        # new
        _seed(s, "/b", now - timedelta(days=2), code_lines=50)
        # no_recent
        _seed(s, "/c", now - timedelta(days=30), code_lines=300)
        report = compute_digest(s, window_days=7, now=now)
    assert report.total_projects == 3
    assert report.projects_with_baseline == 1
    assert report.projects_new == 1
    assert report.projects_no_recent == 1


def test_compute_digest_planted_growth_appears_in_grown_most():
    now = datetime(2026, 5, 20, tzinfo=timezone.utc)
    engine = _make_engine()
    with Session(engine) as s:
        _seed(s, "/a", now - timedelta(days=10), code_lines=100)
        _seed(s, "/a", now - timedelta(days=1), code_lines=350)
        report = compute_digest(s, window_days=7, now=now)
    grown = next(sec for sec in report.sections if sec.kind == "grown_most")
    assert len(grown.entries) == 1
    assert grown.entries[0].headline_value == 250


def test_compute_digest_empty_db():
    engine = _make_engine()
    with Session(engine) as s:
        report = compute_digest(s)
    assert report.total_projects == 0
    for sec in report.sections:
        assert sec.entries == []


# ---------- renderers (3 tests) ----------


def test_render_markdown_includes_header_and_coverage():
    now = datetime(2026, 5, 20, tzinfo=timezone.utc)
    engine = _make_engine()
    with Session(engine) as s:
        _seed(s, "/a", now - timedelta(days=10), code_lines=100)
        _seed(s, "/a", now - timedelta(days=1), code_lines=350)
        report = compute_digest(s, window_days=7, now=now)
    md = render_markdown(report)
    assert "# Mettle digest" in md
    assert "Coverage:" in md
    assert "## Grown the most" in md
    assert "+250 lines" in md


def test_render_markdown_empty_section_uses_empty_message():
    engine = _make_engine()
    with Session(engine) as s:
        report = compute_digest(s)
    md = render_markdown(report)
    # All sections empty — each empty_message renders italicised
    assert "_No projects had measurable growth in this window._" in md


def test_render_json_is_serializable():
    import json

    now = datetime(2026, 5, 20, tzinfo=timezone.utc)
    engine = _make_engine()
    with Session(engine) as s:
        _seed(s, "/a", now - timedelta(days=10), code_lines=100)
        _seed(s, "/a", now - timedelta(days=1), code_lines=350)
        report = compute_digest(s, window_days=7, now=now)
    data = render_json(report)
    # Round-trip through JSON
    blob = json.dumps(data)
    parsed = json.loads(blob)
    assert parsed["window_days"] == 7
    assert parsed["total_projects"] == 1
    assert len(parsed["sections"]) == 7
