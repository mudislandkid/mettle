"""Composite project-health score.

Returns a 0-100 number plus a per-component breakdown so the UI can show
*why* a project scored what it did. Everything here is a pure function over
the Project row, so it's cheap to recompute and easy to test.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from ..database.models import Project

# Component weights. Sum to 1.0 so the final score lives on a 0-100 scale.
WEIGHTS = {
    "comment_ratio": 0.15,
    "test_ratio": 0.20,
    "commit_recency": 0.20,
    "todo_density": 0.10,
    "file_size": 0.20,
    "metadata": 0.15,
}


@dataclass
class HealthComponent:
    name: str
    score: float  # 0-100
    weight: float  # 0-1
    detail: str  # short human-readable explanation


@dataclass
class HealthBreakdown:
    score: float  # 0-100, rounded to one decimal
    components: list[HealthComponent]


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def _comment_ratio_score(project: Project) -> tuple[float, str]:
    """Reward 5-25% comments. Penalise <2% (no docs) and >40% (over-commented or auto-gen)."""
    if project.total_lines == 0:
        return 0.0, "no source"
    ratio = project.comment_lines / project.total_lines
    pct = ratio * 100
    if 0.05 <= ratio <= 0.25:
        return 100.0, f"{pct:.1f}% comments (healthy)"
    if 0.02 <= ratio < 0.05:
        return 60.0, f"{pct:.1f}% comments (light)"
    if 0.25 < ratio <= 0.40:
        return 70.0, f"{pct:.1f}% comments (heavy)"
    if ratio < 0.02:
        return 20.0, f"{pct:.1f}% comments (sparse)"
    return 30.0, f"{pct:.1f}% comments (excessive)"


def _test_ratio_score(project: Project) -> tuple[float, str]:
    """Reward presence of tests; ramp up to "good" at ~20% test lines."""
    if project.total_lines == 0:
        return 0.0, "no source"
    if project.test_files == 0:
        return 0.0, "no test files detected"
    ratio = project.test_total_lines / project.total_lines
    pct = ratio * 100
    if ratio >= 0.30:
        return 100.0, f"{pct:.1f}% test lines"
    if ratio >= 0.15:
        return 80.0, f"{pct:.1f}% test lines"
    if ratio >= 0.05:
        return 50.0, f"{pct:.1f}% test lines"
    return 25.0, f"{pct:.1f}% test lines (very light)"


def _commit_recency_score(project: Project, now: datetime) -> tuple[float, str]:
    """Newer commits ⇒ higher score. No git data ⇒ neutral 50."""
    if project.last_commit_at is None:
        return 50.0, "no git history available"
    last = project.last_commit_at
    # SQLite stores naive UTC; coerce so the math works either way.
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    days = (now - last).days
    if days <= 7:
        return 100.0, f"last commit {days}d ago"
    if days <= 30:
        return 90.0, f"last commit {days}d ago"
    if days <= 90:
        return 75.0, f"last commit {days}d ago"
    if days <= 180:
        return 55.0, f"last commit {days}d ago"
    if days <= 365:
        return 30.0, f"last commit {days}d ago"
    return 10.0, f"last commit {days}d ago (stale)"


def _todo_density_score(project: Project) -> tuple[float, str]:
    """Lower TODO density per 1k code lines = healthier. Big bonus for zero."""
    if project.code_lines == 0:
        return 50.0, "no code lines"
    density = (project.todos / project.code_lines) * 1000  # per 1k LOC
    if project.todos == 0:
        return 100.0, "no TODOs"
    if density <= 2:
        return 90.0, f"{density:.1f} TODOs / 1k LOC"
    if density <= 5:
        return 75.0, f"{density:.1f} TODOs / 1k LOC"
    if density <= 10:
        return 55.0, f"{density:.1f} TODOs / 1k LOC"
    if density <= 20:
        return 35.0, f"{density:.1f} TODOs / 1k LOC"
    return 15.0, f"{density:.1f} TODOs / 1k LOC (very high)"


def _file_size_score(project: Project) -> tuple[float, str]:
    """Smaller average files (within reason) = healthier separation of concerns."""
    if project.total_files == 0:
        return 0.0, "no files"
    avg = project.avg_lines_per_file or 0
    if avg <= 0:
        return 50.0, "unknown"
    if avg <= 150:
        return 100.0, f"avg {avg:.0f} lines/file"
    if avg <= 300:
        return 85.0, f"avg {avg:.0f} lines/file"
    if avg <= 500:
        return 60.0, f"avg {avg:.0f} lines/file"
    if avg <= 1000:
        return 35.0, f"avg {avg:.0f} lines/file"
    return 15.0, f"avg {avg:.0f} lines/file (very large)"


def _metadata_score(project: Project) -> tuple[float, str]:
    """Rough proxy: do we have a remote URL? Did we manage to read git? Are there
    any source files at all?"""
    points = 0.0
    detail_bits: list[str] = []
    if project.total_files > 0:
        points += 50
        detail_bits.append("has source files")
    if project.repo_url:
        points += 30
        detail_bits.append("has remote")
    if project.last_commit_at is not None:
        points += 20
        detail_bits.append("has git history")
    detail = ", ".join(detail_bits) if detail_bits else "minimal metadata"
    return _clamp(points), detail


def compute_health(project: Project, now: datetime | None = None) -> HealthBreakdown:
    """Compute the composite 0-100 health score and its component breakdown."""
    now = now or datetime.now(timezone.utc)

    parts = [
        ("comment_ratio", _comment_ratio_score(project)),
        ("test_ratio", _test_ratio_score(project)),
        ("commit_recency", _commit_recency_score(project, now)),
        ("todo_density", _todo_density_score(project)),
        ("file_size", _file_size_score(project)),
        ("metadata", _metadata_score(project)),
    ]

    components = []
    total = 0.0
    for name, (score, detail) in parts:
        weight = WEIGHTS[name]
        total += score * weight
        components.append(HealthComponent(name=name, score=score, weight=weight, detail=detail))

    return HealthBreakdown(score=round(total, 1), components=components)
