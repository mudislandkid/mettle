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


def parse_pyproject_toml(content: str) -> list[dict]:
    try:
        import tomllib  # py311+
    except ImportError:  # pragma: no cover
        try:
            import tomli as tomllib  # type: ignore
        except ImportError:
            return []
    try:
        data = tomllib.loads(content)
    except Exception:
        return []
    out: list[dict] = []
    # PEP 621 style: [project] dependencies = ["foo", "bar>=1"]
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
    # Poetry style: [tool.poetry.dependencies] / [tool.poetry.dev-dependencies]
    tool = data.get("tool") if isinstance(data, dict) else None
    if isinstance(tool, dict):
        poetry = tool.get("poetry")
        if isinstance(poetry, dict):
            for section in ("dependencies", "dev-dependencies"):
                deps = poetry.get(section)
                if not isinstance(deps, dict):
                    continue
                for name, version in deps.items():
                    if not isinstance(name, str):
                        continue
                    if name.lower() == "python":
                        continue
                    out.append(
                        {
                            "name": name,
                            "version": _normalize(
                                version if not isinstance(version, dict) else version.get("version")
                            ),
                            "manager": "pypi",
                        }
                    )
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


def parse_requirements_txt(content: str) -> list[dict]:
    out: list[dict] = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("-"):
            # `-r other.txt`, `--extra-index-url ...`, comments — skip.
            continue
        # `pkg==1.2.3` / `pkg>=1` / `pkg @ git+https://...` / `pkg`
        head = stripped.split("#", 1)[0].strip()  # strip inline comments
        _push_pep508(out, head)
        if len(out) >= _DEPS_PER_MANIFEST:
            return out
    return out


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
            if not isinstance(name, str) or name == "php":
                continue
            out.append({"name": name, "version": _normalize(version), "manager": "composer"})
            if len(out) >= _DEPS_PER_MANIFEST:
                return out
    return out


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


# (filename, parser) — order matters: first match per directory wins so that
# a project with both pyproject.toml and requirements.txt prefers the modern one.
_MANIFEST_PARSERS: list[tuple[str, callable]] = [
    ("package.json", parse_package_json),
    ("pyproject.toml", parse_pyproject_toml),
    ("requirements.txt", parse_requirements_txt),
    ("Cargo.toml", parse_cargo_toml),
    ("go.mod", parse_go_mod),
    ("composer.json", parse_composer_json),
    ("Gemfile", parse_gemfile),
]


def detect_dependencies(project_root: str | os.PathLike) -> list[dict]:
    """Scan a project root for manifests and return a deduplicated dep list.

    Looks only at the immediate project root — sub-package manifests are
    rare enough that scanning recursively isn't worth the extra IO. The one
    exception is Cargo workspaces: if the root Cargo.toml is a workspace,
    each declared member's manifest is parsed too (without that, workspace
    projects look dependency-less even with 100+ crates). Caps the total
    to ``_DEPS_PER_PROJECT`` entries.
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
    for filename, parser in _MANIFEST_PARSERS:
        path = root / filename
        if not path.is_file():
            continue
        content = _safe_read(path)
        if content is None:
            continue
        if filename == "Cargo.toml":
            cargo_root_content = content
        if _absorb(parser(content)):
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
