"""Git repository analysis service for commit history and statistics."""

import re
import threading
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from .git_safe import GitTimeoutError, run_git

# Simple TTL cache for get_commit_history. lru_cache had no TTL despite the
# docstring claim, and the cache grew per distinct path forever.
_CACHE_TTL_SECONDS = 300  # 5 minutes
_CACHE_MAX_ENTRIES = 64
_commit_cache: dict[str, tuple[float, dict | None]] = {}
_commit_cache_lock = threading.Lock()


class GitCommitData:
    """Represents a single commit's data."""

    def __init__(self, hash: str, date: str, author: str):
        self.hash = hash
        self.date = date
        self.author = author
        self.lines_added = 0
        self.lines_deleted = 0
        self.files_changed = []


class GitAnalyzerService:
    """Service for analyzing Git repository commit history."""

    COMMIT_PATTERN = re.compile(r"^COMMIT:([^|]+)\|([^|]+)\|(.+)$")
    NUMSTAT_PATTERN = re.compile(r"^(\d+|-)\s+(\d+|-)\s+(.+)$")

    @staticmethod
    def is_git_repository(path: str) -> bool:
        """Check if the given path is a Git repository."""
        try:
            git_dir = Path(path) / ".git"
            return git_dir.exists() and git_dir.is_dir()
        except Exception:
            return False

    @staticmethod
    def _execute_git_command(path: str, args: list[str], timeout: int = 30) -> str | None:
        """Execute a git command in a sandboxed env with a timeout.

        Backwards-compatible thin wrapper around git_safe.run_git. The `timeout`
        argument is ignored — git_safe enforces a single project-wide value
        (GIT_TIMEOUT_SECONDS = 30). Returns stdout on success, None on non-zero
        exit, None on timeout.
        """
        try:
            result = run_git(["-C", path, *args], cwd=path)
        except GitTimeoutError as exc:
            print(f"Git command timed out: {exc}")
            return None
        except Exception as e:
            print(f"Error executing git command: {str(e)}")
            return None
        if result.returncode != 0:
            print(f"Git command failed: {result.stderr.strip()}")
            return None
        return result.stdout.strip()

    @classmethod
    def get_repository_metadata(cls, path: str) -> dict:
        """Get basic repository metadata."""
        metadata = {
            "total_commits": 0,
            "first_commit_date": None,
            "last_commit_date": None,
            "unique_authors": 0,
        }

        # Total commits
        count_output = cls._execute_git_command(path, ["rev-list", "--all", "--count"])
        if count_output:
            try:
                metadata["total_commits"] = int(count_output)
            except ValueError:
                pass

        # First commit date
        first_date = cls._execute_git_command(
            path, ["log", "--all", "--format=%aI", "--reverse", "--max-count=1"]
        )
        if first_date:
            metadata["first_commit_date"] = first_date

        # Last commit date
        last_date = cls._execute_git_command(
            path, ["log", "--all", "--format=%aI", "--max-count=1"]
        )
        if last_date:
            metadata["last_commit_date"] = last_date

        # Unique authors
        authors_output = cls._execute_git_command(path, ["log", "--all", "--format=%an"])
        if authors_output:
            authors = set(authors_output.split("\n"))
            metadata["unique_authors"] = len(authors)

        return metadata

    @classmethod
    def parse_numstat_output(cls, output: str) -> list[GitCommitData]:
        """Parse git log --numstat output into commit data."""
        commits = []
        current_commit = None

        for line in output.split("\n"):
            # Check for commit marker
            commit_match = cls.COMMIT_PATTERN.match(line)
            if commit_match:
                if current_commit:
                    commits.append(current_commit)
                hash_val, date, author = commit_match.groups()
                current_commit = GitCommitData(hash_val, date, author)
                continue

            # Check for numstat line
            if current_commit and line.strip():
                numstat_match = cls.NUMSTAT_PATTERN.match(line)
                if numstat_match:
                    added, deleted, filepath = numstat_match.groups()

                    # Skip binary files (marked with -)
                    if added == "-" or deleted == "-":
                        continue

                    try:
                        current_commit.lines_added += int(added)
                        current_commit.lines_deleted += int(deleted)
                        current_commit.files_changed.append(filepath)
                    except ValueError:
                        continue

        # Add the last commit
        if current_commit:
            commits.append(current_commit)

        return commits

    @classmethod
    def aggregate_by_date(cls, commits: list[GitCommitData]) -> dict:
        """Aggregate commits by date."""
        daily_data = defaultdict(
            lambda: {
                "commits_count": 0,
                "lines_added": 0,
                "lines_deleted": 0,
                "net_lines": 0,
                "authors": set(),
            }
        )

        for commit in commits:
            # Extract date (YYYY-MM-DD)
            try:
                date = commit.date.split("T")[0]
            except (IndexError, AttributeError):
                continue

            daily_data[date]["commits_count"] += 1
            daily_data[date]["lines_added"] += commit.lines_added
            daily_data[date]["lines_deleted"] += commit.lines_deleted
            daily_data[date]["net_lines"] += commit.lines_added - commit.lines_deleted
            daily_data[date]["authors"].add(commit.author)

        # Convert authors set to list and sort by date
        result = {}
        for date in sorted(daily_data.keys()):
            data = daily_data[date]
            result[date] = {
                "commits_count": data["commits_count"],
                "lines_added": data["lines_added"],
                "lines_deleted": data["lines_deleted"],
                "net_lines": data["net_lines"],
                "authors": list(data["authors"]),
            }

        return result

    @classmethod
    def calculate_cumulative_lines(cls, daily_data: dict) -> list[dict]:
        """Calculate cumulative lines over time."""
        cumulative = 0
        timeline = []

        for date in sorted(daily_data.keys()):
            data = daily_data[date]
            cumulative += data["net_lines"]

            timeline.append(
                {
                    "date": date,
                    "commits_count": data["commits_count"],
                    "lines_added": data["lines_added"],
                    "lines_deleted": data["lines_deleted"],
                    "net_lines": data["net_lines"],
                    "cumulative_lines": max(0, cumulative),  # Ensure non-negative
                    "authors": data["authors"],
                }
            )

        return timeline

    @classmethod
    def aggregate_monthly(cls, timeline: list[dict]) -> dict[str, int]:
        """Aggregate commits by month (YYYY-MM)."""
        monthly = defaultdict(int)

        for entry in timeline:
            try:
                month = entry["date"][:7]  # YYYY-MM
                monthly[month] += entry["commits_count"]
            except (KeyError, IndexError):
                continue

        return dict(monthly)

    @classmethod
    def aggregate_weekly(cls, timeline: list[dict]) -> dict[str, int]:
        """Aggregate commits by week (YYYY-Www)."""
        weekly = defaultdict(int)

        for entry in timeline:
            try:
                date_obj = datetime.fromisoformat(entry["date"])
                iso_calendar = date_obj.isocalendar()
                week_key = f"{iso_calendar[0]}-W{iso_calendar[1]:02d}"
                weekly[week_key] += entry["commits_count"]
            except (KeyError, ValueError):
                continue

        return dict(weekly)

    @classmethod
    def prepare_heatmap_data(cls, timeline: list[dict]) -> list[tuple[str, int]]:
        """Prepare data for calendar heatmap (last 12 months)."""
        # Get date range (last 365 days)
        if not timeline:
            return []

        # Return all data as [date, commits_count] pairs
        heatmap = []
        for entry in timeline:
            try:
                date = entry["date"]
                count = entry["commits_count"]
                heatmap.append([date, count])
            except KeyError:
                continue

        return heatmap

    @classmethod
    def aggregate_by_author(cls, commits: list[GitCommitData], top_n: int = 20) -> list[dict]:
        """Return per-author totals sorted by commit count (desc)."""
        per_author: dict[str, dict[str, int | str]] = {}
        for c in commits:
            name = c.author or "(unknown)"
            slot = per_author.setdefault(
                name,
                {
                    "author": name,
                    "commits": 0,
                    "lines_added": 0,
                    "lines_deleted": 0,
                    "net_lines": 0,
                    "first_commit_date": c.date,
                    "last_commit_date": c.date,
                },
            )
            slot["commits"] += 1
            slot["lines_added"] += c.lines_added
            slot["lines_deleted"] += c.lines_deleted
            slot["net_lines"] += c.lines_added - c.lines_deleted
            # Track first/last commit dates (ISO strings sort correctly).
            if c.date < slot["first_commit_date"]:
                slot["first_commit_date"] = c.date
            if c.date > slot["last_commit_date"]:
                slot["last_commit_date"] = c.date

        authors = sorted(per_author.values(), key=lambda a: a["commits"], reverse=True)
        return authors[:top_n]

    @classmethod
    def prepare_time_pattern_data(cls, commits: list[GitCommitData]) -> dict:
        """Prepare commit patterns by hour and day of week."""
        if not commits:
            return {"by_hour": [0] * 24, "by_weekday": [0] * 7, "heatmap": []}

        # Initialize counters
        by_hour = defaultdict(int)  # 0-23
        by_weekday = defaultdict(int)  # 0-6 (Monday=0)
        heatmap_data = defaultdict(int)  # (weekday, hour) -> count

        for commit in commits:
            try:
                # Parse ISO format datetime
                dt = datetime.fromisoformat(commit.date.replace("Z", "+00:00"))
                hour = dt.hour
                weekday = dt.weekday()  # 0=Monday, 6=Sunday

                by_hour[hour] += 1
                by_weekday[weekday] += 1
                heatmap_data[(weekday, hour)] += 1
            except (ValueError, AttributeError):
                continue

        # Convert to sorted lists
        hour_data = [by_hour.get(h, 0) for h in range(24)]
        weekday_data = [by_weekday.get(d, 0) for d in range(7)]

        # Convert heatmap to list of [weekday, hour, count]
        heatmap = [
            [day, hour, heatmap_data.get((day, hour), 0)] for day in range(7) for hour in range(24)
        ]

        return {
            "by_hour": hour_data,
            "by_weekday": weekday_data,
            "heatmap": heatmap,
        }

    @classmethod
    def get_commit_history(cls, path: str) -> dict | None:
        """
        Get complete commit history with statistics.
        Results are cached for ~5 minutes via a TTL cache.
        """
        now = time.monotonic()
        with _commit_cache_lock:
            entry = _commit_cache.get(path)
            if entry is not None:
                cached_at, cached_value = entry
                if now - cached_at < _CACHE_TTL_SECONDS:
                    return cached_value
                # stale entry
                _commit_cache.pop(path, None)

        result = cls._compute_commit_history(path)

        with _commit_cache_lock:
            if len(_commit_cache) >= _CACHE_MAX_ENTRIES:
                # evict oldest
                oldest_key = min(_commit_cache, key=lambda k: _commit_cache[k][0])
                _commit_cache.pop(oldest_key, None)
            _commit_cache[path] = (time.monotonic(), result)

        return result

    @classmethod
    def invalidate_commit_cache(cls, path: str | None = None) -> None:
        """Drop a single cached repo (or all of them) after an external change."""
        with _commit_cache_lock:
            if path is None:
                _commit_cache.clear()
            else:
                _commit_cache.pop(path, None)

    @classmethod
    def _compute_commit_history(cls, path: str) -> dict | None:
        # Validate Git repository
        if not cls.is_git_repository(path):
            return None

        # Get metadata
        metadata = cls.get_repository_metadata(path)

        # Get commit history with numstat
        numstat_output = cls._execute_git_command(
            path, ["log", "--all", "--numstat", "--format=COMMIT:%H|%aI|%an", "--reverse"]
        )

        if not numstat_output:
            return {
                "is_git_repo": True,
                "total_commits": 0,
                "commits": [],
                "monthly_commits": {},
                "weekly_commits": {},
                "heatmap_data": [],
                "authors": [],
                **metadata,
            }

        # Parse commits
        commits = cls.parse_numstat_output(numstat_output)

        # Aggregate by date
        daily_data = cls.aggregate_by_date(commits)

        # Calculate cumulative timeline
        timeline = cls.calculate_cumulative_lines(daily_data)

        # Pre-aggregate for charts
        monthly_commits = cls.aggregate_monthly(timeline)
        weekly_commits = cls.aggregate_weekly(timeline)
        heatmap_data = cls.prepare_heatmap_data(timeline)
        time_patterns = cls.prepare_time_pattern_data(commits)
        authors = cls.aggregate_by_author(commits)

        return {
            "is_git_repo": True,
            "commits": timeline,
            "monthly_commits": monthly_commits,
            "weekly_commits": weekly_commits,
            "heatmap_data": heatmap_data,
            "time_patterns": time_patterns,
            "authors": authors,
            **metadata,
        }
