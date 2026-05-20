"""Tests for the composite project-health score."""

import unittest
from datetime import datetime, timedelta, timezone

from web.backend.database.models import Project
from web.backend.services.health_score import compute_health


def make_project(**overrides) -> Project:
    defaults = dict(
        id=1,
        analysis_id=1,
        name="demo",
        path="/tmp/demo",
        total_dirs=10,
        total_files=50,
        total_lines=5000,
        code_lines=4000,
        comment_lines=500,
        blank_lines=500,
        characters=200_000,
        words=20_000,
        functions=120,
        classes=40,
        todos=2,
        imports=80,
        languages=["Python"],
        avg_lines_per_file=100,
        test_files=10,
        test_total_lines=1500,
        test_code_lines=1200,
        repo_url="git@github.com:demo/demo.git",
        last_commit_at=datetime.now(timezone.utc) - timedelta(days=5),
    )
    defaults.update(overrides)
    return Project(**defaults)


class TestHealthScore(unittest.TestCase):
    def test_healthy_project_scores_high(self):
        score = compute_health(make_project()).score
        self.assertGreater(score, 70)

    def test_stale_project_with_no_tests_scores_low(self):
        score = compute_health(
            make_project(
                test_files=0,
                test_total_lines=0,
                test_code_lines=0,
                last_commit_at=datetime.now(timezone.utc) - timedelta(days=500),
                todos=200,
                avg_lines_per_file=1200,
                comment_lines=0,
            )
        ).score
        self.assertLess(score, 30)

    def test_score_components_sum_with_weights(self):
        breakdown = compute_health(make_project())
        self.assertEqual(len(breakdown.components), 6)
        recomputed = sum(c.score * c.weight for c in breakdown.components)
        # Rounded to 1 decimal; allow tiny float wiggle.
        self.assertAlmostEqual(breakdown.score, round(recomputed, 1), places=1)

    def test_zero_total_lines_is_safe(self):
        p = make_project(
            total_lines=0,
            code_lines=0,
            comment_lines=0,
            blank_lines=0,
            total_files=0,
            test_files=0,
            test_total_lines=0,
            test_code_lines=0,
        )
        # Must not raise and must return a finite score.
        score = compute_health(p).score
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)


if __name__ == "__main__":
    unittest.main()
