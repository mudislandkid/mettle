"""Tests for AnalyzerService.discover_projects wrapper-repo expansion."""

from pathlib import Path

from web.backend.services.analyzer_service import (
    CATEGORY_MIN_CHILDREN,
    WRAPPER_REPO_MIN_CHILDREN,
    AnalyzerService,
    _category_dir_children,
    _wrapper_repo_children,
)


def _mkrepo(parent: Path, name: str) -> Path:
    repo = parent / name
    repo.mkdir(parents=True)
    (repo / ".git").mkdir()
    # Add a code file so is_project_directory() returns True.
    (repo / "main.py").write_text("print('hi')\n")
    return repo


def test_wrapper_expands_to_nested_repos(tmp_path: Path) -> None:
    """A directory with 3+ child git repos is expanded to its children."""
    wrapper = tmp_path / "gentlewatch"
    wrapper.mkdir()
    (wrapper / ".git").mkdir()
    (wrapper / "README.md").write_text("wrapper repo\n")
    children = [_mkrepo(wrapper, f"child-{i}") for i in range(WRAPPER_REPO_MIN_CHILDREN)]

    svc = AnalyzerService()
    result = svc.discover_projects(str(tmp_path))

    # Wrapper itself is replaced by its children.
    assert wrapper not in result
    for child in children:
        assert child in result


def test_two_child_repos_does_not_expand(tmp_path: Path) -> None:
    """Below the threshold, the wrapper is kept as a single project."""
    wrapper = tmp_path / "small-wrapper"
    wrapper.mkdir()
    (wrapper / ".git").mkdir()
    (wrapper / "main.py").write_text("x = 1\n")
    for i in range(WRAPPER_REPO_MIN_CHILDREN - 1):
        _mkrepo(wrapper, f"child-{i}")

    svc = AnalyzerService()
    result = svc.discover_projects(str(tmp_path))

    assert wrapper in result


def test_wrapper_helper_returns_none_for_regular_project(tmp_path: Path) -> None:
    """A normal project (no nested git repos) doesn't trip the helper."""
    project = tmp_path / "normal-project"
    project.mkdir()
    (project / ".git").mkdir()
    (project / "main.py").write_text("y = 2\n")
    # Just code subfolders, not nested repos.
    (project / "src").mkdir()
    (project / "src" / "utils.py").write_text("\n")

    assert _wrapper_repo_children(project, include_internal=False) is None


def _mkproject(parent: Path, name: str, marker: str = "pyproject.toml") -> Path:
    """A non-git project dir that passes is_project_directory via its marker."""
    p = parent / name
    p.mkdir(parents=True)
    (p / marker).write_text('[project]\nname = "x"\n')
    (p / "main.py").write_text("x = 1\n")
    return p


def test_category_folder_expanded_when_filtered(tmp_path: Path) -> None:
    """A category folder like apps/ that would otherwise be filtered out by
    INTERNAL_FOLDER_NAMES is expanded into its child projects."""
    root = tmp_path / "monorepo"
    apps = root / "apps"
    [_mkproject(apps, name) for name in ("api", "web", "worker")]

    svc = AnalyzerService()
    result = svc.discover_projects(str(root), include_internal=False)
    # apps/ itself isn't a project, but its 3 children are.
    assert apps not in result
    assert (apps / "api") in result
    assert (apps / "web") in result
    assert (apps / "worker") in result


def test_category_folder_expanded_alongside_other_projects(tmp_path: Path) -> None:
    """Mixed monorepo: top-level real projects + a packages/ category folder."""
    root = tmp_path / "mixed"
    root.mkdir()
    _mkproject(root, "service-a")
    pkgs = root / "packages"
    [_mkproject(pkgs, name) for name in ("core", "ui")]

    svc = AnalyzerService()
    result = svc.discover_projects(str(root))
    names = {p.name for p in result}
    assert names == {"service-a", "core", "ui"}


def test_category_folder_below_threshold_not_expanded(tmp_path: Path) -> None:
    """A single child isn't a category folder — leave it alone."""
    root = tmp_path / "small"
    root.mkdir()
    pkgs = root / "packages"
    _mkproject(pkgs, "solo")

    svc = AnalyzerService()
    result = svc.discover_projects(str(root))
    # packages/ filtered out, solo not surfaced (only 1 child < CATEGORY_MIN_CHILDREN)
    assert (pkgs / "solo") not in result
    assert pkgs not in result
    assert CATEGORY_MIN_CHILDREN == 2  # pin the threshold


def test_category_helper_returns_none_for_non_container(tmp_path: Path) -> None:
    """A dir not in _CATEGORY_FOLDERS returns None even if it has 5 children."""
    misc = tmp_path / "misc"
    misc.mkdir()
    for name in ("a", "b", "c"):
        _mkproject(misc, name)
    assert _category_dir_children(misc) is None


def test_direct_wrapper_target_lists_its_children(tmp_path: Path) -> None:
    """Pointing AT a wrapper (not at its parent) returns the nested repos.

    discover_projects() iterates `directory`'s direct subdirs, so a wrapper
    target naturally hands back the children — no expansion needed at this
    level. The test pins the behaviour so refactors can't regress it.
    """
    wrapper = tmp_path / "gentlewatch"
    wrapper.mkdir()
    (wrapper / ".git").mkdir()
    children = [_mkrepo(wrapper, f"child-{i}") for i in range(WRAPPER_REPO_MIN_CHILDREN)]

    svc = AnalyzerService()
    result = svc.discover_projects(str(wrapper))

    for child in children:
        assert child in result
