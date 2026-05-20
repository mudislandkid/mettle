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
        project, analyzed_at = row[0], row[1]
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


# ---------------------------------------------------------------- public API

SECTION_ORDER: list[tuple[str, str, str]] = [
    ("grown_most", "Grown the most", "Code-line increase since {window}"),
    (
        "biggest_swing",
        "Biggest LOC swing",
        "Largest absolute change in code lines (either direction)",
    ),
    ("dependency_drift", "Dependency drift", "Most package additions, removals, and version bumps"),
    (
        "stalled_with_todos",
        "Stalled with TODOs",
        "No commits in {stale_days}d but TODOs still open",
    ),
    ("newly_stale", "Newly stale", "Crossed the {stale_days}d-no-commit line during the window"),
    ("new_since", "New since {window}", "First analyzed inside the digest window"),
    ("no_recent_activity", "No recent activity", "All analyses older than {window}"),
]

EMPTY_MESSAGES: dict[str, str] = {
    "grown_most": "No projects had measurable growth in this window.",
    "biggest_swing": "No projects had measurable code-line changes.",
    "dependency_drift": "No dependency changes in this window.",
    "stalled_with_todos": "No stalled projects with open TODOs.",
    "newly_stale": "No projects crossed the stale-quiet line in this window.",
    "new_since": "No projects first appeared in this window.",
    "no_recent_activity": "All tracked projects have been analyzed in this window.",
}


def _format_window(days: int) -> str:
    if days <= 1:
        return "last day"
    if days == 7:
        return "last 7 days"
    if days == 14:
        return "last 2 weeks"
    if days == 30:
        return "last month"
    if days == 90:
        return "last quarter"
    if days % 7 == 0:
        return f"last {days // 7} weeks"
    if days % 30 == 0:
        return f"last {days // 30} months"
    return f"last {days} days"


def compute_digest(
    session: Session,
    *,
    window_days: int = 7,
    stale_days: int = 30,
    top_n: int = 5,
    now: datetime | None = None,
) -> DigestReport:
    """Read-only computation. Produces a DigestReport with 7 sections in
    fixed order (empty sections still appear with empty_message)."""
    now = now or datetime.now(timezone.utc)
    window_start = now - timedelta(days=window_days)

    history, analyzed_at_by_id = _project_history(session)

    with_baseline_pairs: list[tuple[Project, Project]] = []
    new_projects: list[Project] = []
    no_recent_projects: list[Project] = []
    for _path, project_history in history.items():
        bucket, current, baseline = _classify_project(
            project_history, analyzed_at_by_id, window_start
        )
        if bucket == "with_baseline":
            with_baseline_pairs.append((current, baseline))
        elif bucket == "new":
            new_projects.append(current)
        else:
            no_recent_projects.append(current)

    window_str = _format_window(window_days)
    sections: list[DigestSection] = []
    for kind, title_tmpl, desc_tmpl in SECTION_ORDER:
        title = title_tmpl.format(window=window_str, stale_days=stale_days)
        description = desc_tmpl.format(window=window_str, stale_days=stale_days)

        if kind == "grown_most":
            entries = _section_grown_most(with_baseline_pairs, top_n)
        elif kind == "biggest_swing":
            entries = _section_biggest_swing(with_baseline_pairs, top_n)
        elif kind == "dependency_drift":
            entries = _section_dependency_drift(with_baseline_pairs, top_n)
        elif kind == "stalled_with_todos":
            entries = _section_stalled_with_todos(with_baseline_pairs, top_n, now, stale_days)
        elif kind == "newly_stale":
            entries = _section_newly_stale(
                with_baseline_pairs, top_n, now, window_start, stale_days
            )
        elif kind == "new_since":
            entries = _section_new_since(new_projects, analyzed_at_by_id)
        else:  # no_recent_activity
            entries = _section_no_recent_activity(no_recent_projects, analyzed_at_by_id, now)

        sections.append(
            DigestSection(
                kind=kind,
                title=title,
                description=description,
                entries=entries,
                empty_message=EMPTY_MESSAGES[kind],
            )
        )

    return DigestReport(
        generated_at=now,
        window_days=window_days,
        window_start=window_start,
        stale_days=stale_days,
        top_n=top_n,
        total_projects=len(history),
        projects_with_baseline=len(with_baseline_pairs),
        projects_new=len(new_projects),
        projects_no_recent=len(no_recent_projects),
        sections=sections,
    )


# ---------------------------------------------------------------- renderers


def render_markdown(report: DigestReport) -> str:
    """Render a DigestReport as Markdown."""
    out: list[str] = []
    window_str = _format_window(report.window_days)
    out.append(f"# Mettle digest — {window_str}")
    out.append("")
    out.append(
        f"Generated {report.generated_at.strftime('%Y-%m-%d %H:%M UTC')}. "
        f"Window: {window_str} "
        f"({report.window_start.strftime('%Y-%m-%d')} → {report.generated_at.strftime('%Y-%m-%d')}). "
        f"Stale threshold: {report.stale_days}d."
    )
    out.append("")
    out.append(
        f"**Coverage:** {report.total_projects} projects total · "
        f"{report.projects_with_baseline} with baseline · "
        f"{report.projects_new} new in window · "
        f"{report.projects_no_recent} no recent activity"
    )
    out.append("")

    for section in report.sections:
        out.append(f"## {section.title}")
        out.append(f"*{section.description}*")
        out.append("")
        if not section.entries:
            out.append(f"_{section.empty_message}_")
            out.append("")
            continue
        for entry in section.entries:
            out.append(_render_entry_md(entry, section.kind))
        out.append("")

    return "\n".join(out).rstrip() + "\n"


def _render_entry_md(entry: DigestEntry, section_kind: str) -> str:
    link = entry.repo_url or f"./projects/{entry.project_id}"
    head = f"- **[{entry.project_name}]({link})** — {entry.headline_label}"

    if section_kind == "dependency_drift" and entry.extra:
        bits = []
        if entry.extra.get("added"):
            names = ", ".join(d["name"] for d in entry.extra["added"][:5])
            suffix = (
                f" (+{len(entry.extra['added']) - 5} more)" if len(entry.extra["added"]) > 5 else ""
            )
            bits.append(f"  - Added: {names}{suffix}")
        if entry.extra.get("removed"):
            names = ", ".join(d["name"] for d in entry.extra["removed"][:5])
            suffix = (
                f" (+{len(entry.extra['removed']) - 5} more)"
                if len(entry.extra["removed"]) > 5
                else ""
            )
            bits.append(f"  - Removed: {names}{suffix}")
        if entry.extra.get("bumped"):
            ups = ", ".join(f"{b['name']} {b['from']}→{b['to']}" for b in entry.extra["bumped"][:5])
            suffix = (
                f" (+{len(entry.extra['bumped']) - 5} more)"
                if len(entry.extra["bumped"]) > 5
                else ""
            )
            bits.append(f"  - Bumped: {ups}{suffix}")
        if bits:
            head += "\n" + "\n".join(bits)

    if section_kind in ("grown_most", "biggest_swing") and entry.baseline_value is not None:
        head += f"  \n  *({int(entry.baseline_value):,} → {int(entry.current_value):,})*"

    return head


def render_json(report: DigestReport) -> dict:
    """Recursive walk: datetime → ISO-8601 string; dataclass → dict."""
    from dataclasses import asdict

    def _convert(value):
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, dict):
            return {k: _convert(v) for k, v in value.items()}
        if isinstance(value, list):
            return [_convert(v) for v in value]
        return value

    return _convert(asdict(report))
