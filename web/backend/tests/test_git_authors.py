"""Tests for the per-author git stats aggregation."""

import unittest

from web.backend.services.git_analyzer_service import GitAnalyzerService, GitCommitData


def _commit(hash_: str, date: str, author: str, added: int = 0, deleted: int = 0) -> GitCommitData:
    c = GitCommitData(hash_, date, author)
    c.lines_added = added
    c.lines_deleted = deleted
    return c


class TestAuthorAggregation(unittest.TestCase):
    def test_groups_by_author_and_sorts_by_commit_count(self):
        commits = [
            _commit("a1", "2024-01-01T00:00:00+00:00", "Greg", added=10, deleted=2),
            _commit("a2", "2024-01-02T00:00:00+00:00", "Greg", added=4, deleted=1),
            _commit("a3", "2024-01-03T00:00:00+00:00", "Alex", added=3, deleted=0),
        ]
        result = GitAnalyzerService.aggregate_by_author(commits)
        self.assertEqual([a["author"] for a in result], ["Greg", "Alex"])
        greg = result[0]
        self.assertEqual(greg["commits"], 2)
        self.assertEqual(greg["lines_added"], 14)
        self.assertEqual(greg["lines_deleted"], 3)
        self.assertEqual(greg["net_lines"], 11)
        self.assertEqual(greg["first_commit_date"], "2024-01-01T00:00:00+00:00")
        self.assertEqual(greg["last_commit_date"], "2024-01-02T00:00:00+00:00")

    def test_unknown_author_handled(self):
        commits = [
            _commit("a1", "2024-01-01T00:00:00+00:00", "", added=1, deleted=0),
        ]
        result = GitAnalyzerService.aggregate_by_author(commits)
        self.assertEqual(result[0]["author"], "(unknown)")

    def test_top_n_limit(self):
        commits = [_commit(f"h{i}", "2024-01-01T00:00:00+00:00", f"u{i}") for i in range(30)]
        result = GitAnalyzerService.aggregate_by_author(commits, top_n=5)
        self.assertEqual(len(result), 5)


if __name__ == "__main__":
    unittest.main()
