"""Parse common dependency manifests for a project.

Lives in its own module (no `rich` or other heavy deps) so it can be unit-
tested in minimal environments. Returns a normalized list of:

    {"name": str, "version": str | None, "manager": str}

`manager` is one of: ``npm``, ``pypi``, ``cargo``, ``go``, ``composer``,
``rubygems``. Locked-version files (``yarn.lock``, ``Cargo.lock`` …) are
deliberately ignored — we want the *declared* deps, not the resolved tree.

Each parser is best-effort: it must never raise on malformed input, and it
should clamp its output to avoid choking on someone's 5000-dep monorepo.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Iterable
from pathlib import Path

# Per-manifest cap so a runaway lockfile-style declaration can't bloat the DB.
_DEPS_PER_MANIFEST = 500
# Hard cap on the per-project total. The UI panel groups by manager.
_DEPS_PER_PROJECT = 1500


_NAME_VERSION_KEYS = ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies")


def _safe_read(path: Path, max_bytes: int = 512_000) -> str | None:
    """Read at most ``max_bytes`` from a manifest file, or return None on error."""
    try:
        with open(path, "rb") as f:
            data = f.read(max_bytes + 1)
    except (OSError, PermissionError):
        return None
    if len(data) > max_bytes:
        # Manifest is suspiciously large; bail rather than choke a parser.
        return None
    try:
        return data.decode("utf-8", errors="replace")
    except UnicodeDecodeError:
        return None


def _normalize(raw_version: object) -> str | None:
    """Clamp version strings to something small + printable."""
    if raw_version is None:
        return None
    s = str(raw_version).strip()
    if not s:
        return None
    return s[:80]


def parse_package_json(content: str) -> list[dict]:
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return []
    out: list[dict] = []
    for key in _NAME_VERSION_KEYS:
        section = data.get(key)
        if not isinstance(section, dict):
            continue
        for name, version in section.items():
            if not isinstance(name, str):
                continue
            out.append({"name": name, "version": _normalize(version), "manager": "npm"})
            if len(out) >= _DEPS_PER_MANIFEST:
                return out
    return out


def npm_workspace_patterns(root: Path) -> list[str]:
    """Collect workspace member globs from any of the three JS monorepo
    conventions:

      - npm / yarn / yarn-berry: ``"workspaces"`` in root ``package.json``
        (array form or ``{"packages": [...]}`` object form).
      - pnpm: top-level ``packages:`` list in ``pnpm-workspace.yaml``.
      - Legacy Lerna: ``packages`` in ``lerna.json`` (defaults to
        ``["packages/*"]`` if missing). Only consulted when neither of the
        above produced any patterns, to avoid double-counting on modern
        Lerna setups that piggyback on the npm workspaces field.

    Negation entries (``"!packages/legacy"``) are silently dropped — npm
    supports them but full negation handling adds complexity for very little
    real-world payoff.
    """
    patterns: list[str] = []

    pkg = root / "package.json"
    if pkg.is_file():
        content = _safe_read(pkg)
        if content is not None:
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                data = None
            if isinstance(data, dict):
                ws = data.get("workspaces")
                if isinstance(ws, list):
                    patterns.extend(p for p in ws if isinstance(p, str) and not p.startswith("!"))
                elif isinstance(ws, dict):
                    pkgs = ws.get("packages") or []
                    if isinstance(pkgs, list):
                        patterns.extend(
                            p for p in pkgs if isinstance(p, str) and not p.startswith("!")
                        )

    pnpm = root / "pnpm-workspace.yaml"
    if not pnpm.is_file():
        pnpm = root / "pnpm-workspace.yml"
    if pnpm.is_file():
        content = _safe_read(pnpm)
        if content is not None:
            try:
                import yaml  # already a project dep

                data = yaml.safe_load(content) or {}
            except (ImportError, Exception):
                data = {}
            if isinstance(data, dict):
                pkgs = data.get("packages") or []
                if isinstance(pkgs, list):
                    patterns.extend(p for p in pkgs if isinstance(p, str) and not p.startswith("!"))

    if not patterns:
        lerna = root / "lerna.json"
        if lerna.is_file():
            content = _safe_read(lerna)
            if content is not None:
                try:
                    data = json.loads(content)
                except json.JSONDecodeError:
                    data = None
                if isinstance(data, dict):
                    pkgs = data.get("packages") or ["packages/*"]
                    if isinstance(pkgs, list):
                        patterns.extend(p for p in pkgs if isinstance(p, str))

    return patterns


def _pyproject_load(content: str) -> dict | None:
    try:
        import tomllib  # py311+
    except ImportError:  # pragma: no cover
        try:
            import tomli as tomllib  # type: ignore
        except ImportError:
            return None
    try:
        return tomllib.loads(content)
    except Exception:
        return None


def parse_pyproject_toml(content: str) -> list[dict]:
    data = _pyproject_load(content)
    if data is None:
        return []
    out: list[dict] = []

    # PEP 621: [project] dependencies = ["foo", "bar>=1"]
    project = data.get("project") if isinstance(data, dict) else None
    if isinstance(project, dict):
        deps = project.get("dependencies")
        if isinstance(deps, list):
            for d in deps:
                _push_pep508(out, d)
        opt = project.get("optional-dependencies")
        if isinstance(opt, dict):
            for spec_list in opt.values():
                if isinstance(spec_list, list):
                    for d in spec_list:
                        _push_pep508(out, d)

    # PEP 735: top-level [dependency-groups]. Each value is a list of PEP 508
    # strings OR `{include-group = "other"}` tables. We ignore the include
    # tables — they're cross-references, not deps.
    dep_groups = data.get("dependency-groups") if isinstance(data, dict) else None
    if isinstance(dep_groups, dict):
        for group in dep_groups.values():
            if not isinstance(group, list):
                continue
            for entry in group:
                if isinstance(entry, str):
                    _push_pep508(out, entry)

    tool = data.get("tool") if isinstance(data, dict) else None
    if isinstance(tool, dict):
        # Poetry: legacy [tool.poetry.dependencies] / dev-dependencies, plus
        # modern [tool.poetry.group.<name>.dependencies] (Poetry 1.2+).
        poetry = tool.get("poetry")
        if isinstance(poetry, dict):
            for section in ("dependencies", "dev-dependencies"):
                _absorb_poetry_dep_table(out, poetry.get(section))
            groups = poetry.get("group")
            if isinstance(groups, dict):
                for grp in groups.values():
                    if isinstance(grp, dict):
                        _absorb_poetry_dep_table(out, grp.get("dependencies"))

        # PDM dev dependencies: [tool.pdm.dev-dependencies] is a dict of
        # `{group_name: [pep508 strings]}` (same shape as PEP 735 groups).
        pdm = tool.get("pdm")
        if isinstance(pdm, dict):
            pdm_dev = pdm.get("dev-dependencies")
            if isinstance(pdm_dev, dict):
                for group in pdm_dev.values():
                    if isinstance(group, list):
                        for entry in group:
                            if isinstance(entry, str):
                                _push_pep508(out, entry)

    return out


def _absorb_poetry_dep_table(out: list[dict], table: object) -> None:
    """Poetry dependency tables map `{name: spec}` where `spec` is a version
    string or an inline table like `{version = "...", extras = [...]}`.
    Skips the `python` entry (it's a Python version constraint, not a dep)."""
    if not isinstance(table, dict):
        return
    for name, version in table.items():
        if not isinstance(name, str):
            continue
        if name.lower() == "python":
            continue
        if isinstance(version, dict):
            version = version.get("version")
        out.append({"name": name, "version": _normalize(version), "manager": "pypi"})
        if len(out) >= _DEPS_PER_MANIFEST:
            return


def uv_workspace_patterns(content: str) -> tuple[list[str], list[str]]:
    """Return `(members, exclude)` from `[tool.uv.workspace]`. The uv
    workspace spec mirrors cargo's: `members` is a list of glob/path strings,
    `exclude` is a list to drop from the resolved set."""
    data = _pyproject_load(content)
    if data is None:
        return [], []
    ws = ((data.get("tool") or {}).get("uv") or {}).get("workspace") or {}
    if not isinstance(ws, dict):
        return [], []
    members = [m for m in (ws.get("members") or []) if isinstance(m, str)]
    exclude = [m for m in (ws.get("exclude") or []) if isinstance(m, str)]
    return members, exclude


def parse_pipfile(content: str) -> list[dict]:
    """Parse a Pipfile (pipenv). Reads `[packages]` and `[dev-packages]`.

    Values may be a plain version spec (`"*"` for any) or an inline table
    `{version = "..."}`. `"*"` is treated as no version constraint."""
    data = _pyproject_load(content)
    if data is None:
        return []
    out: list[dict] = []
    for section in ("packages", "dev-packages"):
        d = data.get(section) if isinstance(data, dict) else None
        if not isinstance(d, dict):
            continue
        for name, v in d.items():
            if not isinstance(name, str):
                continue
            ver = v if not isinstance(v, dict) else v.get("version")
            if ver == "*":
                ver = None
            out.append({"name": name, "version": _normalize(ver), "manager": "pypi"})
            if len(out) >= _DEPS_PER_MANIFEST:
                return out
    return out


def parse_setup_cfg(content: str) -> list[dict]:
    """Parse a setuptools setup.cfg. Reads `[options] install_requires` and
    every key under `[options.extras_require]`. Pure declarative INI — safe
    to parse without executing anything (unlike setup.py)."""
    import configparser
    import io

    cp = configparser.ConfigParser()
    try:
        cp.read_file(io.StringIO(content))
    except configparser.Error:
        return []
    out: list[dict] = []
    blocks: list[str] = []
    if cp.has_option("options", "install_requires"):
        blocks.append(cp.get("options", "install_requires"))
    if cp.has_section("options.extras_require"):
        for key in cp.options("options.extras_require"):
            blocks.append(cp.get("options.extras_require", key))
    for block in blocks:
        for line in block.splitlines():
            spec = line.strip()
            if not spec:
                continue
            _push_pep508(out, spec)
            if len(out) >= _DEPS_PER_MANIFEST:
                return out
    return out


_PEP508_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(.*)$")


def _push_pep508(out: list[dict], spec: object) -> None:
    if not isinstance(spec, str):
        return
    # Trim extras/markers: e.g. `requests[security]>=2,<3; python_version>='3.10'`
    main = spec.split(";", 1)[0]
    main = re.sub(r"\[[^\]]*\]", "", main)
    m = _PEP508_RE.match(main)
    if not m:
        return
    name = m.group(1)
    rest = m.group(2).strip()
    out.append({"name": name, "version": _normalize(rest or None), "manager": "pypi"})


_MAX_REQUIREMENTS_INCLUDES = 20


def parse_requirements_txt(
    content: str,
    *,
    _base: Path | None = None,
    _visited: set[Path] | None = None,
) -> list[dict]:
    """Parse a requirements file. When ``_base`` is given, ``-r path`` /
    ``--requirement path`` directives are resolved relative to it and followed
    once each, with cycle protection. ``-c`` (constraints), ``-e`` (editable),
    and any other ``--option`` lines are skipped."""
    out: list[dict] = []
    visited: set[Path] = _visited if _visited is not None else set()
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # Follow `-r other.txt` / `--requirement other.txt` when we know the
        # base dir and haven't blown the include budget.
        if _base is not None and (
            stripped.startswith("-r ") or stripped.startswith("--requirement ")
        ):
            if len(visited) >= _MAX_REQUIREMENTS_INCLUDES:
                continue
            target = stripped.split(None, 1)[1].split("#", 1)[0].strip()
            if not target:
                continue
            try:
                ref = (_base / target).resolve()
            except (OSError, ValueError):
                continue
            if not ref.is_file() or ref in visited:
                continue
            visited.add(ref)
            nested = _safe_read(ref)
            if nested is None:
                continue
            for dep in parse_requirements_txt(nested, _base=ref.parent, _visited=visited):
                out.append(dep)
                if len(out) >= _DEPS_PER_MANIFEST:
                    return out
            continue
        if stripped.startswith("-"):
            # -c constraints, -e editable, --extra-index-url etc. — not deps.
            continue
        head = stripped.split("#", 1)[0].strip()
        _push_pep508(out, head)
        if len(out) >= _DEPS_PER_MANIFEST:
            return out
    return out


def _discover_requirements_files(root: Path) -> list[Path]:
    """Find `requirements*.txt` at root and `requirements/*.txt` one level
    deep. No deeper — the convention is well-bounded."""
    files: list[Path] = []
    for candidate in sorted(root.glob("requirements*.txt")):
        if candidate.is_file():
            files.append(candidate)
    sub = root / "requirements"
    if sub.is_dir():
        for candidate in sorted(sub.glob("*.txt")):
            if candidate.is_file():
                files.append(candidate)
    return files[:_MAX_REQUIREMENTS_INCLUDES]


def _cargo_load(content: str) -> dict | None:
    try:
        import tomllib
    except ImportError:  # pragma: no cover
        try:
            import tomli as tomllib  # type: ignore
        except ImportError:
            return None
    try:
        return tomllib.loads(content)
    except Exception:
        return None


def parse_cargo_toml(content: str) -> list[dict]:
    """Parse `[dependencies]`, `[dev-dependencies]`, `[build-dependencies]`,
    plus the workspace equivalents (`[workspace.dependencies]` etc.).

    Workspace dependencies are declared once at the workspace root and inherited
    by member crates via `name.workspace = true`. Without this, workspace
    projects look dependency-less even when they pull in 100+ crates."""
    data = _cargo_load(content)
    if data is None:
        return []
    out: list[dict] = []
    sections: list[dict] = []
    for key in ("dependencies", "dev-dependencies", "build-dependencies"):
        sec = data.get(key)
        if isinstance(sec, dict):
            sections.append(sec)
    workspace = data.get("workspace")
    if isinstance(workspace, dict):
        for key in ("dependencies", "dev-dependencies", "build-dependencies"):
            sec = workspace.get(key)
            if isinstance(sec, dict):
                sections.append(sec)
    for deps in sections:
        for name, value in deps.items():
            if not isinstance(name, str):
                continue
            version = value if not isinstance(value, dict) else value.get("version")
            out.append({"name": name, "version": _normalize(version), "manager": "cargo"})
            if len(out) >= _DEPS_PER_MANIFEST:
                return out
    return out


def cargo_workspace_members(content: str) -> list[str]:
    """Return the `workspace.members` patterns from a root Cargo.toml.

    Patterns may be plain paths (`"crates/foo"`) or globs (`"crates/*"`);
    the caller is responsible for resolving them against the project root."""
    data = _cargo_load(content)
    if data is None:
        return []
    workspace = data.get("workspace")
    if not isinstance(workspace, dict):
        return []
    members = workspace.get("members") or []
    if not isinstance(members, list):
        return []
    return [m for m in members if isinstance(m, str)]


_GO_REQUIRE_LINE = re.compile(r"^\s*(\S+)\s+(v\S+)\s*(?://.*)?$")


def go_workspace_uses(content: str) -> list[str]:
    """Parse a go.work file and return the directories listed under `use`.

    Handles both `use ./path` single-line form and `use (\\n  ./a\\n  ./b\\n)`
    block form, plus trailing `// comment` annotations and blank lines.
    """
    out: list[str] = []
    in_block = False
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        if line.startswith("use ("):
            in_block = True
            continue
        if in_block:
            if line.startswith(")"):
                in_block = False
                continue
            path = line.split("//", 1)[0].strip()
            if path:
                out.append(path)
            continue
        if line.startswith("use "):
            after = line[len("use ") :].split("//", 1)[0].strip()
            if after and not after.startswith("("):
                out.append(after)
    return out


def parse_go_mod(content: str) -> list[dict]:
    out: list[dict] = []
    in_require_block = False
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        if line.startswith("require ("):
            in_require_block = True
            continue
        if in_require_block:
            if line.startswith(")"):
                in_require_block = False
                continue
            m = _GO_REQUIRE_LINE.match(line)
            if m:
                out.append({"name": m.group(1), "version": _normalize(m.group(2)), "manager": "go"})
                if len(out) >= _DEPS_PER_MANIFEST:
                    return out
            continue
        if line.startswith("require "):
            after = line[len("require ") :].strip()
            m = _GO_REQUIRE_LINE.match(after)
            if m:
                out.append({"name": m.group(1), "version": _normalize(m.group(2)), "manager": "go"})
    return out


def parse_composer_json(content: str) -> list[dict]:
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return []
    out: list[dict] = []
    for key in ("require", "require-dev"):
        section = data.get(key)
        if not isinstance(section, dict):
            continue
        for name, version in section.items():
            if not isinstance(name, str):
                continue
            # Skip PHP itself and "platform packages" — `ext-mbstring`,
            # `lib-openssl` etc. They're environment requirements, not deps.
            if (
                name == "php"
                or name.startswith("ext-")
                or name.startswith("lib-")
                or name.startswith("php-")
            ):
                continue
            out.append({"name": name, "version": _normalize(version), "manager": "composer"})
            if len(out) >= _DEPS_PER_MANIFEST:
                return out
    return out


def composer_path_repos(content: str) -> list[str]:
    """Extract `url` values from `composer.json` `repositories` entries of
    type `path`. Composer uses these to point at sibling packages in a
    monorepo. URLs can be plain paths or globs (`packages/*`)."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return []
    repos = data.get("repositories")
    # `repositories` can be a list OR a dict keyed by name.
    entries: list = []
    if isinstance(repos, list):
        entries = repos
    elif isinstance(repos, dict):
        entries = list(repos.values())
    paths: list[str] = []
    for entry in entries:
        if isinstance(entry, dict) and entry.get("type") == "path":
            url = entry.get("url")
            if isinstance(url, str):
                paths.append(url)
    return paths


_GEMFILE_RE = re.compile(
    r"""^\s*gem\s+['"]([^'"]+)['"]""" r"""(?:\s*,\s*['"]([^'"]+)['"])?""",
    re.MULTILINE,
)


def parse_gemfile(content: str) -> list[dict]:
    out: list[dict] = []
    for match in _GEMFILE_RE.finditer(content):
        out.append(
            {"name": match.group(1), "version": _normalize(match.group(2)), "manager": "rubygems"}
        )
        if len(out) >= _DEPS_PER_MANIFEST:
            return out
    return out


_GEMSPEC_DEP_RE = re.compile(
    r"""\.\s*add_(?:runtime_|development_)?dependency\s*\(?\s*['"]([^'"]+)['"]"""
    r"""(?:\s*,\s*['"]([^'"]+)['"])?""",
    re.MULTILINE,
)


def parse_gemspec(content: str) -> list[dict]:
    """Parse a .gemspec file's `add_dependency` / `add_runtime_dependency` /
    `add_development_dependency` calls. This is the source of truth for gem
    libraries — a project's Gemfile typically just contains `gemspec` to
    re-export them."""
    out: list[dict] = []
    for match in _GEMSPEC_DEP_RE.finditer(content):
        out.append(
            {
                "name": match.group(1),
                "version": _normalize(match.group(2)),
                "manager": "rubygems",
            }
        )
        if len(out) >= _DEPS_PER_MANIFEST:
            return out
    return out


_GEMFILE_GEMSPEC_PATH_RE = re.compile(
    r"""gemspec[^#\n]*?\bpath:\s*['"]([^'"]+)['"]""",
)
_GEMFILE_EVAL_RE = re.compile(
    r"""^\s*eval_gemfile\s+['"]([^'"]+)['"]""",
    re.MULTILINE,
)


def gemfile_gemspec_paths(content: str) -> list[str]:
    """Extract `gemspec path: "subdir"` directives — used by Rails-style
    multi-gem repos to declare which sub-directories house additional gem
    libraries."""
    return _GEMFILE_GEMSPEC_PATH_RE.findall(content)


def gemfile_eval_paths(content: str) -> list[str]:
    """Extract `eval_gemfile 'path/to/Gemfile'` references."""
    return _GEMFILE_EVAL_RE.findall(content)


# (filename, parser) — order matters: first match per directory wins so that
# a project with both pyproject.toml and requirements.txt prefers the modern one.
# `requirements.txt` is deliberately NOT here — it's handled by the Python
# requirements-discovery block in detect_dependencies(), which also walks
# `requirements*.txt` and `requirements/*.txt` and follows `-r` includes.
_MANIFEST_PARSERS: list[tuple[str, callable]] = [
    ("package.json", parse_package_json),
    ("pyproject.toml", parse_pyproject_toml),
    ("Pipfile", parse_pipfile),
    ("setup.cfg", parse_setup_cfg),
    ("Cargo.toml", parse_cargo_toml),
    ("go.mod", parse_go_mod),
    ("composer.json", parse_composer_json),
    ("Gemfile", parse_gemfile),
    ("gems.rb", parse_gemfile),  # Bundler 2+ alias for Gemfile, same syntax.
]


def detect_dependencies(project_root: str | os.PathLike) -> list[dict]:
    """Scan a project root for manifests and return a deduplicated dep list.

    Looks at the immediate project root for each ecosystem's primary
    manifest. Workspace-aware ecosystems (Cargo workspaces, npm/yarn/pnpm
    workspaces, uv workspaces) additionally recurse into their declared
    members so projects don't look dependency-less just because they're
    multi-package monorepos. Python's per-file split (`requirements*.txt` +
    `requirements/*.txt` + `-r` includes) is also handled.

    Caps the total at ``_DEPS_PER_PROJECT`` entries.
    """
    root = Path(project_root)
    if not root.is_dir():
        return []

    collected: list[dict] = []
    seen: set[tuple[str, str]] = set()  # (name, manager) → dedup

    def _absorb(deps: Iterable[dict]) -> bool:
        """Append unique deps, return True when the per-project cap is hit."""
        for dep in deps:
            key = (dep["name"], dep["manager"])
            if key in seen:
                continue
            seen.add(key)
            collected.append(dep)
            if len(collected) >= _DEPS_PER_PROJECT:
                return True
        return False

    cargo_root_content: str | None = None
    pyproject_root_content: str | None = None
    composer_root_content: str | None = None
    gemfile_root_content: str | None = None
    gemfile_root_path: Path | None = None
    for filename, parser in _MANIFEST_PARSERS:
        path = root / filename
        if not path.is_file():
            continue
        content = _safe_read(path)
        if content is None:
            continue
        if filename == "Cargo.toml":
            cargo_root_content = content
        elif filename == "pyproject.toml":
            pyproject_root_content = content
        elif filename == "composer.json":
            composer_root_content = content
        elif filename in ("Gemfile", "gems.rb"):
            gemfile_root_content = content
            gemfile_root_path = path
        if _absorb(parser(content)):
            return collected

    # Root *.gemspec files. For a published gem library these are the source
    # of truth for declared dependencies (the Gemfile usually just contains
    # `gemspec` to re-export them).
    for gemspec_path in sorted(root.glob("*.gemspec")):
        if not gemspec_path.is_file():
            continue
        content = _safe_read(gemspec_path)
        if content is None:
            continue
        if _absorb(parse_gemspec(content)):
            return collected

    # Python: multi-file requirements discovery (root + requirements/*.txt)
    # with `-r` include-following per file (cycle-protected).
    for req_path in _discover_requirements_files(root):
        content = _safe_read(req_path)
        if content is None:
            continue
        if _absorb(parse_requirements_txt(content, _base=req_path.parent, _visited=set())):
            return collected

    # Cargo workspaces: recurse into each declared member crate.
    if cargo_root_content is not None:
        for member_path in _resolve_cargo_workspace_members(root, cargo_root_content):
            content = _safe_read(member_path)
            if content is None:
                continue
            if _absorb(parse_cargo_toml(content)):
                return collected

    # npm / yarn / pnpm / lerna workspaces: recurse into each member package.
    npm_members = _resolve_workspace_manifests(root, npm_workspace_patterns(root), "package.json")
    for member_path in npm_members:
        content = _safe_read(member_path)
        if content is None:
            continue
        if _absorb(parse_package_json(content)):
            return collected

    # Go workspaces: `go.work` lists `use ./module-a` paths to nested modules.
    go_work_path = root / "go.work"
    if go_work_path.is_file():
        go_work_content = _safe_read(go_work_path)
        if go_work_content is not None:
            uses = go_workspace_uses(go_work_content)
            go_members = _resolve_workspace_manifests(root, uses, "go.mod")
            for member_path in go_members:
                content = _safe_read(member_path)
                if content is None:
                    continue
                if _absorb(parse_go_mod(content)):
                    return collected

    # Composer monorepos: `repositories` with type "path" point at local
    # sibling packages — each with its own composer.json.
    if composer_root_content is not None:
        composer_patterns = composer_path_repos(composer_root_content)
        if composer_patterns:
            composer_members = _resolve_workspace_manifests(
                root, composer_patterns, "composer.json"
            )
            for member_path in composer_members:
                content = _safe_read(member_path)
                if content is None:
                    continue
                if _absorb(parse_composer_json(content)):
                    return collected

    # Ruby multi-gem repos: Gemfile may carry `gemspec path: "subdir"` for
    # Rails-style monorepos and `eval_gemfile 'subdir/Gemfile'` for split
    # Gemfiles. Resolve relative to the root Gemfile's directory.
    if gemfile_root_content is not None and gemfile_root_path is not None:
        gem_base = gemfile_root_path.parent
        for spec_dir in gemfile_gemspec_paths(gemfile_root_content):
            try:
                target_dir = (gem_base / spec_dir).resolve()
                if not target_dir.is_relative_to(root.resolve()):
                    continue
            except (OSError, ValueError):
                continue
            for gemspec_path in sorted(target_dir.glob("*.gemspec")):
                if not gemspec_path.is_file():
                    continue
                content = _safe_read(gemspec_path)
                if content is None:
                    continue
                if _absorb(parse_gemspec(content)):
                    return collected
        for eval_path in gemfile_eval_paths(gemfile_root_content):
            try:
                target = (gem_base / eval_path).resolve()
                if not target.is_file() or not target.is_relative_to(root.resolve()):
                    continue
            except (OSError, ValueError):
                continue
            content = _safe_read(target)
            if content is None:
                continue
            if _absorb(parse_gemfile(content)):
                return collected

    # uv workspaces: recurse into each declared member pyproject.toml.
    if pyproject_root_content is not None:
        uv_members, uv_exclude = uv_workspace_patterns(pyproject_root_content)
        if uv_members:
            uv_paths = _resolve_workspace_manifests(root, uv_members, "pyproject.toml")
            if uv_exclude:
                excluded = set(
                    p.resolve()
                    for p in _resolve_workspace_manifests(root, uv_exclude, "pyproject.toml")
                )
                uv_paths = [p for p in uv_paths if p.resolve() not in excluded]
            for member_path in uv_paths:
                content = _safe_read(member_path)
                if content is None:
                    continue
                if _absorb(parse_pyproject_toml(content)):
                    return collected

    return collected


# Per-project cap on how many workspace member manifests we'll walk into.
# Each ecosystem reuses this — a runaway glob in someone's monorepo shouldn't
# blow up the analyser.
_WORKSPACE_MEMBERS_CAP = 200


def _resolve_workspace_manifests(root: Path, patterns: list[str], manifest_name: str) -> list[Path]:
    """Generic workspace-pattern resolver. Used by cargo/npm/uv/composer flows.

    For each pattern (plain path or glob like ``packages/*``), find the
    matching directories under ``root`` and return any ``manifest_name`` file
    inside them. Stays inside ``root`` (no `../` escape), caps at
    ``_WORKSPACE_MEMBERS_CAP`` entries, sorts each glob's output deterministically.
    """
    if not patterns:
        return []
    resolved: list[Path] = []
    for pattern in patterns:
        # Strip leading "./" — both cargo and npm allow it.
        clean = pattern.lstrip("./") if pattern.startswith("./") else pattern
        if not any(ch in clean for ch in "*?["):
            manifest = root / clean / manifest_name
            try:
                if manifest.is_file() and manifest.resolve().is_relative_to(root.resolve()):
                    resolved.append(manifest)
            except (OSError, ValueError):
                pass
            continue
        try:
            matches = sorted(root.glob(clean))
        except (OSError, ValueError):
            continue
        for match in matches:
            if not match.is_dir():
                continue
            manifest = match / manifest_name
            try:
                if manifest.is_file() and manifest.resolve().is_relative_to(root.resolve()):
                    resolved.append(manifest)
            except (OSError, ValueError):
                continue
        if len(resolved) >= _WORKSPACE_MEMBERS_CAP:
            break
    return resolved[:_WORKSPACE_MEMBERS_CAP]


def _resolve_cargo_workspace_members(root: Path, root_content: str) -> list[Path]:
    return _resolve_workspace_manifests(root, cargo_workspace_members(root_content), "Cargo.toml")


def aggregate_by_name(per_project: Iterable[tuple[str, list[dict]]]) -> dict[str, list[str]]:
    """Helper used by the cross-project endpoint:
    ``{"react": ["projA", "projB"], "fastapi": ["projC"], ...}``
    """
    inverse: dict[str, list[str]] = {}
    for project_name, deps in per_project:
        for dep in deps:
            inverse.setdefault(dep["name"], []).append(project_name)
    return inverse
