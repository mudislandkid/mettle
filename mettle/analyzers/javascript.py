import re

from ..metrics.file_metrics import FileMetrics
from .base import BaseAnalyzer, classify_lines, mask_string_literals


class JavaScriptAnalyzer(BaseAnalyzer):
    # `function foo`, `const foo = function`, arrow assigned to const/let/var,
    # method shorthand inside object literals/classes. We deliberately don't
    # match the old `\w+\s*\([^)]*\)\s*{` because it matched `if(){}` /
    # `for(){}` / `while(){}` and grossly inflated counts.
    # Tokens that look like method shorthand at a line start but are actually
    # control-flow / built-in expressions, not function definitions.
    _CONTROL_KEYWORDS = (
        "if",
        "else",
        "for",
        "while",
        "do",
        "switch",
        "case",
        "catch",
        "finally",
        "return",
        "throw",
        "typeof",
        "instanceof",
        "new",
        "delete",
        "in",
        "of",
        "await",
        "yield",
        "with",
        "void",
        "super",
    )
    FUNCTION_PATTERN = re.compile(
        r"(?:"
        r"\bfunction\s*\*?\s+\w+|"  # function foo / function* foo
        r"\bfunction\s*\*?\s*\(|"  # anonymous function expr
        r"\b(?:const|let|var)\s+\w+\s*=\s*(?:async\s*)?(?:function\b|\([^)]*\)\s*=>|\w+\s*=>)|"
        r"^\s*(?:async\s+)?(?!(?:" + r"|".join(_CONTROL_KEYWORDS) + r")\b)"
        r"\w+\s*\([^)]*\)\s*\{"  # method shorthand at line start
        r")",
        re.MULTILINE,
    )
    CLASS_PATTERN = re.compile(r"\bclass\s+\w+")

    IMPORT_PATTERN = re.compile(
        r"(?:"
        r"^\s*import\s+[^;]*?\bfrom\b|"  # import x from "..."
        r'^\s*import\s+["\']|'  # import "side-effect"
        r"\brequire\s*\(|"  # require(...)
        r"\bimport\s*\("  # dynamic import(...)
        r")",
        re.MULTILINE,
    )

    SINGLE_COMMENT = re.compile(r"//")
    MULTI_COMMENT = re.compile(r"/\*[\s\S]*?\*/")
    TODO_PATTERN = re.compile(r"\b(?:TODO|FIXME|XXX|HACK)\b", re.IGNORECASE)

    # JSX opening tag with an uppercase-leading name. Self-closing or with
    # children both qualify. Excludes lowercase HTML tags (`<div>`) since
    # those aren't user-defined components.
    JSX_COMPONENT_PATTERN = re.compile(r"<([A-Z][A-Za-z0-9_.]*)\b")
    # React hook usage: `useState(`, `useEffect(`, etc.
    REACT_HOOK_PATTERN = re.compile(r"\b(use[A-Z][A-Za-z0-9]*)\s*\(")
    # `async function`, `async (...) =>`, `async name() {`, `async ident =>`.
    ASYNC_FUNCTION_PATTERN = re.compile(
        r"\basync\s+(?:function\b|\([^)]*\)\s*=>|\w+\s*\([^)]*\)\s*\{|\w+\s*=>)"
    )
    # TypeScript declarations. `interface Foo`, `type Foo =`, `enum Foo`.
    INTERFACE_PATTERN = re.compile(
        r"^\s*(?:export\s+)?(?:declare\s+)?interface\s+([A-Za-z_$][\w$]*)", re.MULTILINE
    )
    TYPE_ALIAS_PATTERN = re.compile(
        r"^\s*(?:export\s+)?(?:declare\s+)?type\s+([A-Za-z_$][\w$]*)\s*[=<]", re.MULTILINE
    )
    ENUM_PATTERN = re.compile(
        r"^\s*(?:export\s+)?(?:const\s+|declare\s+)?enum\s+([A-Za-z_$][\w$]*)", re.MULTILINE
    )

    def _strip_for_pattern_scan(self, content: str) -> str:
        masked = mask_string_literals(content)
        masked = self.MULTI_COMMENT.sub(
            lambda m: "".join("\n" if c == "\n" else " " for c in m.group()),
            masked,
        )
        masked = re.sub(r"//[^\n]*", "", masked)
        return masked

    def count_functions_and_classes(self, content: str) -> tuple[int, int]:
        clean = self._strip_for_pattern_scan(content)
        return len(self.FUNCTION_PATTERN.findall(clean)), len(self.CLASS_PATTERN.findall(clean))

    def count_imports(self, content: str) -> int:
        clean = self._strip_for_pattern_scan(content)
        return len(self.IMPORT_PATTERN.findall(clean))

    def analyze_content(self, content: str, file_path: str = None) -> FileMetrics:
        metrics = super().analyze_content(content, file_path)

        blank, comment, code = classify_lines(content, self.SINGLE_COMMENT, self.MULTI_COMMENT)
        metrics.blank_lines = blank
        metrics.comment_lines = comment
        metrics.code_lines = code

        functions, classes = self.count_functions_and_classes(content)
        metrics.functions = functions
        metrics.classes = classes
        metrics.imports = self.count_imports(content)

        # TODOs counted in `super().analyze_content` already via word-bounded
        # regex; keep this here so an explicit override returns the same answer.
        metrics.todos = len(self.TODO_PATTERN.findall(content))

        # JSX / React / TS specifics. Strip strings + comments so e.g. an
        # `<Foo />` token inside a docblock doesn't inflate the count.
        clean = self._strip_for_pattern_scan(content)
        metrics.jsx_components = len(self.JSX_COMPONENT_PATTERN.findall(clean))
        metrics.react_hooks = len(self.REACT_HOOK_PATTERN.findall(clean))
        metrics.async_functions = len(self.ASYNC_FUNCTION_PATTERN.findall(clean))
        # TypeScript declarations only make sense in .ts / .tsx files but the
        # patterns are cheap to run unconditionally and false positives in
        # plain JS would require literal `interface X` / `type X = ...` at
        # statement position, which is itself a syntax error.
        metrics.interfaces = len(self.INTERFACE_PATTERN.findall(clean))
        metrics.type_aliases = len(self.TYPE_ALIAS_PATTERN.findall(clean))
        metrics.enums = len(self.ENUM_PATTERN.findall(clean))

        return metrics
