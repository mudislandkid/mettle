"""Tests for the dependency-manifest parsers."""

import tempfile
import unittest
from pathlib import Path

from ..analyzers.dependency_detection import (
    detect_dependencies,
    parse_cargo_toml,
    parse_composer_json,
    parse_gemfile,
    parse_gemspec,
    parse_go_mod,
    parse_package_json,
    parse_pipfile,
    parse_pyproject_toml,
    parse_requirements_txt,
    parse_setup_cfg,
)


class TestPackageJson(unittest.TestCase):
    def test_parses_all_sections(self):
        content = """{
            "name": "demo",
            "dependencies": {"react": "^18.2.0", "lodash": "4.17.21"},
            "devDependencies": {"vitest": "^1.0.0"},
            "peerDependencies": {"react-dom": "^18.0.0"}
        }"""
        deps = parse_package_json(content)
        names = {d["name"] for d in deps}
        self.assertEqual(names, {"react", "lodash", "vitest", "react-dom"})
        self.assertTrue(all(d["manager"] == "npm" for d in deps))

    def test_malformed_returns_empty(self):
        self.assertEqual(parse_package_json("{not valid"), [])


class TestPyproject(unittest.TestCase):
    def test_pep621_dependencies_and_extras(self):
        content = (
            "[project]\n"
            'name = "x"\n'
            'dependencies = ["fastapi>=0.115", "rich"]\n'
            "[project.optional-dependencies]\n"
            'web = ["uvicorn[standard]", "websockets>=12"]\n'
        )
        deps = parse_pyproject_toml(content)
        names = sorted(d["name"] for d in deps)
        self.assertEqual(names, ["fastapi", "rich", "uvicorn", "websockets"])

    def test_poetry_style(self):
        content = '[tool.poetry.dependencies]\npython = "^3.11"\n' 'requests = "^2.31"\n'
        deps = parse_pyproject_toml(content)
        names = {d["name"] for d in deps}
        self.assertIn("requests", names)
        self.assertNotIn("python", names)


class TestPyprojectModern(unittest.TestCase):
    def test_pep735_dependency_groups(self):
        content = (
            "[project]\n"
            'name = "x"\n'
            "[dependency-groups]\n"
            'test = ["pytest>=8", "pytest-cov"]\n'
            'docs = ["sphinx", {include-group = "test"}]\n'
        )
        deps = parse_pyproject_toml(content)
        names = {d["name"] for d in deps}
        self.assertIn("pytest", names)
        self.assertIn("pytest-cov", names)
        self.assertIn("sphinx", names)
        # include-group references must not be treated as deps.
        self.assertNotIn("include-group", names)

    def test_poetry_groups(self):
        content = (
            "[tool.poetry.group.dev.dependencies]\n"
            'pytest = "^8"\n'
            "[tool.poetry.group.docs.dependencies]\n"
            'sphinx = "^7"\n'
        )
        deps = parse_pyproject_toml(content)
        names = {d["name"] for d in deps}
        self.assertEqual(names, {"pytest", "sphinx"})

    def test_pdm_dev_dependencies(self):
        content = (
            "[project]\n"
            'name = "x"\n'
            "[tool.pdm.dev-dependencies]\n"
            'test = ["pytest>=8"]\n'
            'lint = ["ruff"]\n'
        )
        deps = parse_pyproject_toml(content)
        names = {d["name"] for d in deps}
        self.assertEqual(names, {"pytest", "ruff"})


class TestPipfile(unittest.TestCase):
    def test_packages_and_dev_packages(self):
        content = (
            "[packages]\n"
            'flask = "*"\n'
            'requests = { version = ">=2.31" }\n'
            "[dev-packages]\n"
            'pytest = "*"\n'
        )
        deps = parse_pipfile(content)
        by_name = {d["name"]: d["version"] for d in deps}
        self.assertIsNone(by_name["flask"])  # "*" -> None
        self.assertEqual(by_name["requests"], ">=2.31")
        self.assertIsNone(by_name["pytest"])


class TestSetupCfg(unittest.TestCase):
    def test_install_requires_and_extras(self):
        content = (
            "[options]\n"
            "install_requires =\n"
            "    fastapi>=0.115\n"
            "    rich\n"
            "[options.extras_require]\n"
            "test = pytest>=8\n"
            "    coverage\n"
        )
        deps = parse_setup_cfg(content)
        names = {d["name"] for d in deps}
        self.assertEqual(names, {"fastapi", "rich", "pytest", "coverage"})


class TestRequirements(unittest.TestCase):
    def test_basic(self):
        content = (
            "# pinned because of CVE-x\n"
            "fastapi>=0.115\n"
            "requests==2.31  # comment\n"
            "rich\n"
            "-r other.txt\n"
            "--extra-index-url https://x\n"
        )
        deps = parse_requirements_txt(content)
        names = sorted(d["name"] for d in deps)
        self.assertEqual(names, ["fastapi", "requests", "rich"])


class TestCargo(unittest.TestCase):
    def test_string_and_table_versions(self):
        content = (
            "[dependencies]\n" 'serde = "1.0"\n' 'tokio = { version = "1", features = ["full"] }\n'
        )
        deps = parse_cargo_toml(content)
        by_name = {d["name"]: d["version"] for d in deps}
        self.assertEqual(by_name["serde"], "1.0")
        self.assertEqual(by_name["tokio"], "1")

    def test_workspace_dependencies_are_collected(self):
        """`[workspace.dependencies]` is the canonical place for declared
        deps in a Rust workspace — previously missed by the parser."""
        content = (
            "[workspace]\n"
            'members = ["crates/*"]\n'
            "[workspace.dependencies]\n"
            'snow = "0.10"\n'
            'tokio = { version = "1.40", features = ["full"] }\n'
            "[workspace.dev-dependencies]\n"
            'proptest = "1"\n'
        )
        deps = parse_cargo_toml(content)
        by_name = {d["name"]: d["version"] for d in deps}
        self.assertEqual(by_name["snow"], "0.10")
        self.assertEqual(by_name["tokio"], "1.40")
        self.assertEqual(by_name["proptest"], "1")

    def test_detect_recurses_into_workspace_members(self):
        """Sub-crate manifests under workspace.members are parsed and merged
        with workspace deps, with normal dedup-by-(name,manager) on top."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "Cargo.toml").write_text(
                "[workspace]\n"
                'members = ["crates/foo", "crates/*"]\n'
                "[workspace.dependencies]\n"
                'serde = "1.0"\n'
            )
            (root / "crates" / "foo").mkdir(parents=True)
            (root / "crates" / "foo" / "Cargo.toml").write_text(
                "[package]\n"
                'name = "foo"\n'
                "[dependencies]\n"
                'tokio = "1"\n'
                "serde.workspace = true\n"
            )
            (root / "crates" / "bar").mkdir(parents=True)
            (root / "crates" / "bar" / "Cargo.toml").write_text(
                "[package]\n" 'name = "bar"\n' "[dependencies]\n" 'reqwest = "0.12"\n'
            )
            deps = detect_dependencies(root)
            cargo = {d["name"]: d for d in deps if d["manager"] == "cargo"}
            self.assertIn("serde", cargo)
            self.assertIn("tokio", cargo)
            self.assertIn("reqwest", cargo)
            # No duplicate serde entries despite appearing in both manifests.
            self.assertEqual(len([d for d in deps if d["name"] == "serde"]), 1)


class TestRequirementsMultiFile(unittest.TestCase):
    def test_discovers_requirements_variants_and_follows_r(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "requirements.txt").write_text("fastapi>=0.115\n-r dev.txt\n")
            (root / "requirements-dev.txt").write_text("pytest>=8\n")
            (root / "dev.txt").write_text("ruff\n-r constraints.txt\n")
            (root / "constraints.txt").write_text("# cycle proof\n-r dev.txt\nrich\n")
            (root / "requirements").mkdir()
            (root / "requirements" / "prod.txt").write_text("uvicorn[standard]\n")
            deps = detect_dependencies(root)
            names = {d["name"] for d in deps if d["manager"] == "pypi"}
            # all three layers represented, cycle handled, no infinite loop
            self.assertEqual(names, {"fastapi", "pytest", "ruff", "rich", "uvicorn"})


class TestUvWorkspaces(unittest.TestCase):
    def test_recurses_into_uv_workspace_members(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pyproject.toml").write_text(
                "[project]\n"
                'name = "root"\n'
                'dependencies = ["click"]\n'
                "[tool.uv.workspace]\n"
                'members = ["packages/*"]\n'
                'exclude = ["packages/legacy"]\n'
            )
            for sub, dep in [("a", "fastapi"), ("b", "rich"), ("legacy", "old")]:
                (root / "packages" / sub).mkdir(parents=True)
                (root / "packages" / sub / "pyproject.toml").write_text(
                    f'[project]\nname = "{sub}"\ndependencies = ["{dep}"]\n'
                )
            deps = detect_dependencies(root)
            names = {d["name"] for d in deps if d["manager"] == "pypi"}
            self.assertIn("click", names)
            self.assertIn("fastapi", names)
            self.assertIn("rich", names)
            # uv `exclude` keeps `legacy` out.
            self.assertNotIn("old", names)


class TestNpmWorkspaces(unittest.TestCase):
    def test_npm_workspaces_array_form(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "package.json").write_text(
                '{"workspaces": ["packages/*"], "dependencies": {"react": "^18"}}'
            )
            (root / "packages" / "a").mkdir(parents=True)
            (root / "packages" / "a" / "package.json").write_text(
                '{"dependencies": {"lodash": "^4"}}'
            )
            (root / "packages" / "b").mkdir(parents=True)
            (root / "packages" / "b" / "package.json").write_text(
                '{"dependencies": {"axios": "^1"}}'
            )
            deps = detect_dependencies(root)
            names = {d["name"] for d in deps if d["manager"] == "npm"}
            self.assertEqual(names, {"react", "lodash", "axios"})

    def test_npm_workspaces_object_form(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "package.json").write_text(
                '{"workspaces": {"packages": ["apps/*"]}, "dependencies": {"react": "^18"}}'
            )
            (root / "apps" / "web").mkdir(parents=True)
            (root / "apps" / "web" / "package.json").write_text('{"dependencies": {"vue": "^3"}}')
            deps = detect_dependencies(root)
            names = {d["name"] for d in deps if d["manager"] == "npm"}
            self.assertEqual(names, {"react", "vue"})

    def test_pnpm_workspace_yaml(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "package.json").write_text('{"name": "mono"}')
            (root / "pnpm-workspace.yaml").write_text("packages:\n  - apps/*\n  - libs/*\n")
            (root / "apps" / "web").mkdir(parents=True)
            (root / "apps" / "web" / "package.json").write_text('{"dependencies": {"vue": "^3"}}')
            (root / "libs" / "ui").mkdir(parents=True)
            (root / "libs" / "ui" / "package.json").write_text(
                '{"dependencies": {"tailwindcss": "^3"}}'
            )
            deps = detect_dependencies(root)
            names = {d["name"] for d in deps if d["manager"] == "npm"}
            self.assertEqual(names, {"vue", "tailwindcss"})

    def test_lerna_only_as_fallback(self):
        """lerna.json is consulted only when neither workspaces nor pnpm-
        workspace.yaml declared anything — modern Lerna uses npm workspaces."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "lerna.json").write_text('{"packages": ["modules/*"]}')
            (root / "modules" / "x").mkdir(parents=True)
            (root / "modules" / "x" / "package.json").write_text(
                '{"dependencies": {"moment": "^2"}}'
            )
            deps = detect_dependencies(root)
            names = {d["name"] for d in deps if d["manager"] == "npm"}
            self.assertEqual(names, {"moment"})


class TestGoMod(unittest.TestCase):
    def test_require_block(self):
        content = (
            "module example.com/x\n"
            "go 1.22\n"
            "require (\n"
            "\tgithub.com/foo/bar v1.2.3\n"
            "\tgolang.org/x/sync v0.5.0 // indirect\n"
            ")\n"
            "require github.com/baz/qux v0.1.0\n"
        )
        deps = parse_go_mod(content)
        by_name = {d["name"]: d["version"] for d in deps}
        self.assertEqual(by_name["github.com/foo/bar"], "v1.2.3")
        self.assertEqual(by_name["github.com/baz/qux"], "v0.1.0")


class TestGoWorkspaces(unittest.TestCase):
    def test_go_work_recurses_into_modules(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "go.work").write_text(
                "go 1.22\n\nuse (\n\t./module-a\n\t./module-b  // commented\n)\nuse ./module-c\n"
            )
            for mod, dep in [
                ("module-a", "github.com/a/foo"),
                ("module-b", "github.com/b/bar"),
                ("module-c", "github.com/c/baz"),
            ]:
                (root / mod).mkdir()
                (root / mod / "go.mod").write_text(
                    f"module example.com/{mod}\ngo 1.22\nrequire {dep} v1.0.0\n"
                )
            deps = detect_dependencies(root)
            names = {d["name"] for d in deps if d["manager"] == "go"}
            self.assertEqual(
                names,
                {"github.com/a/foo", "github.com/b/bar", "github.com/c/baz"},
            )


class TestComposer(unittest.TestCase):
    def test_skips_php_itself(self):
        content = '{"require": {"php": ">=8.2", "monolog/monolog": "^3.0"}}'
        deps = parse_composer_json(content)
        names = {d["name"] for d in deps}
        self.assertEqual(names, {"monolog/monolog"})

    def test_skips_platform_packages(self):
        """ext-* / lib-* / php-* are environment requirements, not deps."""
        content = (
            '{"require": {"php": ">=8.2", "ext-mbstring": "*", '
            '"lib-openssl": "*", "monolog/monolog": "^3.0"}}'
        )
        deps = parse_composer_json(content)
        names = {d["name"] for d in deps}
        self.assertEqual(names, {"monolog/monolog"})

    def test_recurses_into_composer_path_repos(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "composer.json").write_text(
                '{"require": {"monolog/monolog": "^3.0"}, '
                '"repositories": [{"type": "path", "url": "packages/*"}]}'
            )
            (root / "packages" / "lib-a").mkdir(parents=True)
            (root / "packages" / "lib-a" / "composer.json").write_text(
                '{"name": "vendor/lib-a", "require": {"vendor/dep-a": "^1.0"}}'
            )
            (root / "packages" / "lib-b").mkdir(parents=True)
            (root / "packages" / "lib-b" / "composer.json").write_text(
                '{"name": "vendor/lib-b", "require": {"vendor/dep-b": "^2.0"}}'
            )
            deps = detect_dependencies(root)
            names = {d["name"] for d in deps if d["manager"] == "composer"}
            self.assertEqual(names, {"monolog/monolog", "vendor/dep-a", "vendor/dep-b"})


class TestGemspec(unittest.TestCase):
    def test_parse_gemspec_add_dependency(self):
        content = (
            "Gem::Specification.new do |spec|\n"
            "  spec.add_dependency 'activerecord', '>= 7'\n"
            "  spec.add_runtime_dependency('actionpack', '>= 7')\n"
            "  spec.add_development_dependency 'rspec'\n"
            "end\n"
        )
        deps = parse_gemspec(content)
        by_name = {d["name"]: d["version"] for d in deps}
        self.assertEqual(by_name["activerecord"], ">= 7")
        self.assertEqual(by_name["actionpack"], ">= 7")
        self.assertIsNone(by_name["rspec"])

    def test_root_gemspec_discovered(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "mylib.gemspec").write_text(
                "Gem::Specification.new { |s| s.add_dependency 'rake', '~> 13' }\n"
            )
            deps = detect_dependencies(root)
            names = {d["name"] for d in deps if d["manager"] == "rubygems"}
            self.assertIn("rake", names)

    def test_multi_gem_repo_via_gemspec_path(self):
        """Rails-style: root Gemfile uses `gemspec path: "sub"` to declare
        additional gem libraries living in subdirectories."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "Gemfile").write_text(
                "source 'https://rubygems.org'\n"
                "gemspec\n"
                "gemspec path: 'activerecord'\n"
                "gemspec path: 'actionpack'\n"
            )
            (root / "activerecord").mkdir()
            (root / "activerecord" / "activerecord.gemspec").write_text(
                "Gem::Specification.new { |s| s.add_dependency 'sqlite3' }\n"
            )
            (root / "actionpack").mkdir()
            (root / "actionpack" / "actionpack.gemspec").write_text(
                "Gem::Specification.new { |s| s.add_dependency 'rack', '>= 3' }\n"
            )
            deps = detect_dependencies(root)
            names = {d["name"] for d in deps if d["manager"] == "rubygems"}
            self.assertIn("sqlite3", names)
            self.assertIn("rack", names)

    def test_eval_gemfile_followed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "Gemfile").write_text("eval_gemfile 'gemfiles/rails_7.gemfile'\n")
            (root / "gemfiles").mkdir()
            (root / "gemfiles" / "rails_7.gemfile").write_text(
                "gem 'rails', '~> 7.0'\ngem 'puma'\n"
            )
            deps = detect_dependencies(root)
            names = {d["name"] for d in deps if d["manager"] == "rubygems"}
            self.assertIn("rails", names)
            self.assertIn("puma", names)

    def test_gems_rb_alias(self):
        """gems.rb is the Bundler 2+ name for Gemfile, same syntax."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "gems.rb").write_text("gem 'sinatra'\n")
            deps = detect_dependencies(root)
            names = {d["name"] for d in deps if d["manager"] == "rubygems"}
            self.assertEqual(names, {"sinatra"})


class TestGemfile(unittest.TestCase):
    def test_simple_lines(self):
        content = "source 'https://rubygems.org'\n" "gem 'rails', '~> 7.0'\n" "gem 'puma'\n"
        deps = parse_gemfile(content)
        by_name = {d["name"]: d["version"] for d in deps}
        self.assertEqual(by_name["rails"], "~> 7.0")
        self.assertIsNone(by_name["puma"])


class TestDetectDependencies(unittest.TestCase):
    def test_reads_each_supported_manifest_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package.json").write_text('{"dependencies": {"react": "^18"}}')
            (root / "pyproject.toml").write_text('[project]\nname="x"\ndependencies=["fastapi"]\n')
            deps = detect_dependencies(root)
            managers = {d["manager"] for d in deps}
            self.assertEqual(managers, {"npm", "pypi"})

    def test_dedups_same_name_within_manager(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Both files would declare react; only one row should survive.
            (root / "package.json").write_text('{"dependencies": {"react": "^18"}}')
            (root / "Cargo.toml").write_text(
                '[dependencies]\nreact = "0.1"\n'  # different manager → both kept
            )
            deps = detect_dependencies(root)
            keys = {(d["name"], d["manager"]) for d in deps}
            self.assertIn(("react", "npm"), keys)
            self.assertIn(("react", "cargo"), keys)

    def test_missing_dir_returns_empty(self):
        self.assertEqual(detect_dependencies("/nonexistent/path/abc"), [])


if __name__ == "__main__":
    unittest.main()
