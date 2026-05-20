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
from datetime import datetime

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
