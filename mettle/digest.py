"""Cross-project digest — read-only computation over completed analyses.

Produces a DigestReport containing 7 fixed-order sections that narrate
what's changed across the portfolio in a given time window. Consumed by:

    mettle digest               (CLI subcommand, render_markdown)
    GET /api/digest/            (HTTP endpoint, render_json)
    DigestView.vue              (frontend, fetches the JSON)

See docs/superpowers/specs/2026-05-20-phase-d-digest-design.md for the
data contract and algorithm rationale.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from web.backend.database.models import Analysis, Project

# ---------------------------------------------------------------- data shape


@dataclass(frozen=True)
class DigestEntry:
    project_id: int
    project_name: str
    project_path: str
    repo_url: str | None
    headline_value: float
    headline_label: str
    baseline_value: float | None = None
    current_value: float | None = None
    extra: dict | None = None


@dataclass(frozen=True)
class DigestSection:
    kind: str
    title: str
    description: str
    entries: list[DigestEntry]
    empty_message: str | None = None


@dataclass(frozen=True)
class DigestReport:
    generated_at: datetime
    window_days: int
    window_start: datetime
    stale_days: int
    top_n: int
    total_projects: int
    projects_with_baseline: int
    projects_new: int
    projects_no_recent: int
    sections: list[DigestSection]


# ---------------------------------------------------------------- helpers


def _diff_dependencies(baseline: list[dict], current: list[dict]) -> dict:
    """Compute added / removed / bumped given two dependency lists.

    Identity tuple is (name, manager). Same name under a different manager
    is treated as a different dep.
    """

    def _k(d: dict) -> tuple[str, str]:
        return (d.get("name", ""), d.get("manager", ""))

    baseline_map = {_k(d): d.get("version", "") for d in baseline}
    current_map = {_k(d): d.get("version", "") for d in current}

    added = [{"name": n, "manager": m} for (n, m) in current_map.keys() - baseline_map.keys()]
    removed = [{"name": n, "manager": m} for (n, m) in baseline_map.keys() - current_map.keys()]
    bumped = [
        {"name": n, "manager": m, "from": baseline_map[(n, m)], "to": current_map[(n, m)]}
        for (n, m) in baseline_map.keys() & current_map.keys()
        if baseline_map[(n, m)] != current_map[(n, m)]
    ]
    return {"added": added, "removed": removed, "bumped": bumped}


# ---------------------------------------------------------------- DB readers


def _project_history(session: Session) -> tuple[dict[str, list[Project]], dict[int, datetime]]:
    """Return ({project_path: [Project rows DESC by analyzed_at]}, {analysis_id: analyzed_at}).

    Only completed analyses. Deduped by path — same on-disk path is the
    stable identity (matches the existing /api/projects/highlights/ pattern).
    """
    rows = session.exec(
        select(Project, Analysis.analyzed_at)
        .join(Analysis, Analysis.id == Project.analysis_id)
        .where(Analysis.status == "completed")
        .order_by(Analysis.analyzed_at.desc())
    ).all()
    history: dict[str, list[Project]] = {}
    analyzed_at_by_id: dict[int, datetime] = {}
    for row in rows:
        if isinstance(row, tuple):
            project, analyzed_at = row[0], row[1]
        else:
            project = row
            analyzed_at = session.get(Analysis, project.analysis_id).analyzed_at
        history.setdefault(project.path, []).append(project)
        analyzed_at_by_id[project.analysis_id] = analyzed_at
    return history, analyzed_at_by_id


def _classify_project(
    history: list[Project],
    analyzed_at_by_id: dict[int, datetime],
    window_start: datetime,
) -> tuple[str, Project, Project | None]:
    """Three-bucket classification per the spec.

    Returns (bucket, current, baseline_or_none) where bucket is one of:
    "with_baseline", "new", "no_recent".
    """
    current = history[0]  # history is DESC

    def _at(p: Project) -> datetime:
        dt = analyzed_at_by_id[p.analysis_id]
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    ws = window_start if window_start.tzinfo else window_start.replace(tzinfo=timezone.utc)
    has_inside = any(_at(p) >= ws for p in history)
    has_outside = any(_at(p) < ws for p in history)

    if has_inside and has_outside:
        baseline = next(p for p in history if _at(p) < ws)
        return ("with_baseline", current, baseline)
    if not has_outside:
        return ("new", current, None)
    return ("no_recent", current, None)


# ---------------------------------------------------------------- sections


def _entry(
    project: Project,
    *,
    headline_value,
    headline_label,
    baseline_value=None,
    current_value=None,
    extra=None,
) -> DigestEntry:
    return DigestEntry(
        project_id=project.id,
        project_name=project.name,
        project_path=project.path,
        repo_url=project.repo_url,
        headline_value=float(headline_value),
        headline_label=headline_label,
        baseline_value=None if baseline_value is None else float(baseline_value),
        current_value=None if current_value is None else float(current_value),
        extra=extra,
    )


def _section_grown_most(pairs, top_n: int) -> list[DigestEntry]:
    rows = []
    for current, baseline in pairs:
        delta = (current.code_lines or 0) - (baseline.code_lines or 0)
        if delta <= 0:
            continue
        rows.append(
            _entry(
                current,
                headline_value=delta,
                headline_label=f"+{delta:,} lines",
                baseline_value=baseline.code_lines,
                current_value=current.code_lines,
            )
        )
    rows.sort(key=lambda e: e.headline_value, reverse=True)
    return rows[:top_n]


def _section_biggest_swing(pairs, top_n: int) -> list[DigestEntry]:
    rows = []
    for current, baseline in pairs:
        delta = (current.code_lines or 0) - (baseline.code_lines or 0)
        if delta == 0:
            continue
        sign = "+" if delta > 0 else "-"
        rows.append(
            _entry(
                current,
                headline_value=abs(delta),
                headline_label=f"{sign}{abs(delta):,} lines",
                baseline_value=baseline.code_lines,
                current_value=current.code_lines,
            )
        )
    rows.sort(key=lambda e: e.headline_value, reverse=True)
    return rows[:top_n]


def _format_drift_label(diff: dict) -> str:
    parts = []
    if diff["added"]:
        parts.append(f"{len(diff['added'])} added")
    if diff["removed"]:
        parts.append(f"{len(diff['removed'])} removed")
    if diff["bumped"]:
        parts.append(f"{len(diff['bumped'])} bumped")
    return " · ".join(parts)


def _section_dependency_drift(pairs, top_n: int) -> list[DigestEntry]:
    rows = []
    for current, baseline in pairs:
        diff = _diff_dependencies(baseline.dependencies or [], current.dependencies or [])
        total = len(diff["added"]) + len(diff["removed"]) + len(diff["bumped"])
        if total == 0:
            continue
        rows.append(
            _entry(
                current,
                headline_value=total,
                headline_label=_format_drift_label(diff),
                extra=diff,
            )
        )
    rows.sort(key=lambda e: e.headline_value, reverse=True)
    return rows[:top_n]


def _section_stalled_with_todos(
    pairs, top_n: int, now: datetime, stale_days: int
) -> list[DigestEntry]:
    threshold = now - timedelta(days=stale_days)
    rows = []
    for current, _baseline in pairs:
        last = current.last_commit_at
        if last is None or current.todos == 0:
            continue
        last_tz = last if last.tzinfo else last.replace(tzinfo=timezone.utc)
        if last_tz >= threshold:
            continue
        days_stale = (now - last_tz).days
        rows.append(
            _entry(
                current,
                headline_value=current.todos,
                headline_label=f"{current.todos} TODOs · {days_stale}d quiet",
                extra={"last_commit_at": last_tz.isoformat(), "days_stale": days_stale},
            )
        )
    rows.sort(key=lambda e: e.headline_value, reverse=True)
    return rows[:top_n]


def _section_newly_stale(
    pairs, top_n: int, now: datetime, window_start: datetime, stale_days: int
) -> list[DigestEntry]:
    threshold_now = now - timedelta(days=stale_days)
    threshold_window_start = window_start - timedelta(days=stale_days)
    rows = []
    for current, _baseline in pairs:
        last = current.last_commit_at
        if last is None:
            continue
        last_tz = last if last.tzinfo else last.replace(tzinfo=timezone.utc)
        if not (threshold_window_start <= last_tz < threshold_now):
            continue
        days_stale = (now - last_tz).days
        rows.append(
            _entry(
                current,
                headline_value=days_stale,
                headline_label=f"crossed {stale_days}d line; now {days_stale}d quiet",
                extra={"last_commit_at": last_tz.isoformat(), "days_stale": days_stale},
            )
        )
    rows.sort(key=lambda e: e.headline_value, reverse=True)
    return rows[:top_n]


def _section_new_since(
    new_projects: list[Project], analyzed_at_by_id: dict[int, datetime]
) -> list[DigestEntry]:
    """Full list — no top_n cap. Sorted by code_lines DESC."""
    rows = []
    for current in new_projects:
        first_at = analyzed_at_by_id[current.analysis_id]
        rows.append(
            _entry(
                current,
                headline_value=current.code_lines or 0,
                headline_label=f"{(current.code_lines or 0):,} lines",
                extra={"first_analyzed_at": first_at.isoformat()},
            )
        )
    rows.sort(key=lambda e: e.headline_value, reverse=True)
    return rows


def _section_no_recent_activity(
    no_recent_projects: list[Project],
    analyzed_at_by_id: dict[int, datetime],
    now: datetime,
) -> list[DigestEntry]:
    rows = []
    for current in no_recent_projects:
        last_at = analyzed_at_by_id[current.analysis_id]
        last_tz = last_at if last_at.tzinfo else last_at.replace(tzinfo=timezone.utc)
        days_since = (now - last_tz).days
        rows.append(
            _entry(
                current,
                headline_value=days_since,
                headline_label=f"last analyzed {days_since}d ago",
                extra={"last_analyzed_at": last_tz.isoformat()},
            )
        )
    rows.sort(key=lambda e: e.headline_value, reverse=True)
    return rows
