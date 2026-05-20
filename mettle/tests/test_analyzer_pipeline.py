"""End-to-end tests: planted secret + LICENSE flow through the analyzer
pipeline and surface in ProjectSummary."""


def test_planted_secret_surfaces_in_analyze_project(tmp_path):
    """A planted AKIA secret + MIT LICENSE produces the expected ProjectSummary."""
    project = tmp_path / "myapp"
    project.mkdir()
    (project / "config.py").write_text('AWS_KEY = "AKIAIOSFODNN7EXAMPLE"\n')
    from mettle.license_corpus import SPDX_CORPUS

    (project / "LICENSE").write_text(SPDX_CORPUS["MIT"])

    from batch_analyze import analyze_project
    from mettle.analyzers.code_analyzer import CodeAnalyzer

    summary = analyze_project(project, CodeAnalyzer())
    assert summary is not None
    assert summary.secrets_found == 1
    assert summary.license_spdx == "MIT"
    assert summary.secrets_detail is not None
    assert summary.secrets_detail[0]["kind"] == "aws_access_key_id"
    # The hash must be deterministic and not contain the original
    assert "AKIA" not in summary.secrets_detail[0]["snippet_hash"]


def test_test_directory_secrets_dont_count(tmp_path):
    """A planted secret inside a tests/ directory should be filtered out."""
    project = tmp_path / "myapp"
    tests_dir = project / "tests"
    tests_dir.mkdir(parents=True)
    (tests_dir / "test_aws.py").write_text('FAKE = "AKIAIOSFODNN7EXAMPLE"\n')
    # Add a real source file so total_files > 0
    src = project / "app.py"
    src.write_text("print('hi')\n")

    from batch_analyze import analyze_project
    from mettle.analyzers.code_analyzer import CodeAnalyzer

    summary = analyze_project(project, CodeAnalyzer())
    assert summary is not None
    assert summary.secrets_found == 0
    assert summary.secrets_detail is None


def test_no_secret_no_license_clean_project(tmp_path):
    """A clean project with no secret and no LICENSE produces zeroes + None."""
    project = tmp_path / "myapp"
    project.mkdir()
    (project / "app.py").write_text("print('hello')\n")

    from batch_analyze import analyze_project
    from mettle.analyzers.code_analyzer import CodeAnalyzer

    summary = analyze_project(project, CodeAnalyzer())
    assert summary is not None
    assert summary.secrets_found == 0
    assert summary.secrets_detail is None
    assert summary.license_spdx is None
