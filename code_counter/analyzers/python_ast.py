"""AST-based Python analyzer.

The regex-based :class:`PythonAnalyzer` is fast and language-agnostic but it
has well-known blind spots:

- triple-quoted strings used as data (not docstrings) are miscounted as
  comments,
- nested ``def``/``class`` are counted the same as top-level,
- async functions are detected by ``def`` alone — the ``async`` modifier
  doesn't change the count,
- ``f"..."`` inside other expressions can be missed or over-counted,
- decorators applied with arguments (``@deco(x)``) can match twice.

This analyzer uses the stdlib :mod:`ast` module, which is the same parser
that CPython itself uses, so the structural counts are exact for any valid
Python source. We fall back to :class:`PythonAnalyzer` on ``SyntaxError`` so
Python-2 files or partial fragments still produce a reasonable answer.
"""

from __future__ import annotations

import ast
from typing import Tuple

from .base import BaseAnalyzer, classify_lines
from .python import PythonAnalyzer
from ..metrics.file_metrics import FileMetrics


# Shared regex (line classification) — comment markers we treat as block
# comments are docstrings, which the AST visitor handles via Expr/Constant nodes.
_DOCSTRING = PythonAnalyzer.DOCSTRING
_SINGLE_COMMENT = PythonAnalyzer.SINGLE_COMMENT


def _function_complexity(node: ast.AST) -> int:
    """Cyclomatic complexity of a function body.

    Standard formulation: 1 base + 1 per decision point. Decision points are
    ``if`` / ``elif``, ``for``, ``while``, ``except``, boolean ``and`` / ``or``,
    ternary expressions, comprehension ``if`` clauses, ``assert``, and each
    arm of a ``match``. ``with`` statements don't add complexity (the runtime
    branches but the control flow doesn't).
    """
    complexity = 1
    for child in ast.walk(node):
        # Skip nested function bodies — they get their own complexity count.
        if child is node:
            continue
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            # Don't double-count: ast.walk descends into nested defs.
            # We can't prune the walk cheaply, so we re-call ourselves and
            # subtract via the early `continue`. Easiest: skip the body of
            # nested defs by not counting their inner branches at all.
            # Detect "are we inside a nested def?" by checking ancestry —
            # but ast.walk doesn't give us ancestry. Trade-off accepted:
            # nested functions inflate the outer's complexity slightly.
            continue
        if isinstance(child, (ast.If, ast.For, ast.AsyncFor, ast.While)):
            complexity += 1
        elif isinstance(child, ast.ExceptHandler):
            complexity += 1
        elif isinstance(child, ast.BoolOp):
            # `a and b and c` → 2 extra paths.
            complexity += len(child.values) - 1
        elif isinstance(child, ast.IfExp):
            complexity += 1
        elif isinstance(child, ast.comprehension):
            complexity += 1
            complexity += len(child.ifs)
        elif isinstance(child, ast.Assert):
            complexity += 1
        elif hasattr(ast, "Match") and isinstance(child, getattr(ast, "Match")):
            complexity += len(child.cases)
    return complexity


class _PythonVisitor(ast.NodeVisitor):
    # Capture per-file complexity hotspots. Top-N is decided by the caller.
    COMPLEX_CAP = 50

    def __init__(self) -> None:
        self.functions = 0
        self.classes = 0
        self.imports = 0
        self.decorators = 0
        self.list_comprehensions = 0
        self.lambda_functions = 0
        self.f_strings = 0
        self.async_functions = 0
        self.complex_functions: list[tuple[str, str, int, int]] = []
        # Class-name stack so qualnames look like ``ClassName.method``.
        self._class_stack: list[str] = []

    # --------------- definitions

    def _record_function(self, node: ast.AST, name: str) -> None:
        self.functions += 1
        cx = _function_complexity(node)
        qualname = ".".join(self._class_stack + [name]) if self._class_stack else name
        if len(self.complex_functions) < self.COMPLEX_CAP:
            self.complex_functions.append((name, qualname, cx, getattr(node, "lineno", 0)))

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self._record_function(node, node.name)
        self.decorators += len(node.decorator_list)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self._record_function(node, node.name)
        self.async_functions += 1
        self.decorators += len(node.decorator_list)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        self.classes += 1
        self.decorators += len(node.decorator_list)
        self._class_stack.append(node.name)
        try:
            self.generic_visit(node)
        finally:
            self._class_stack.pop()

    # --------------- imports

    def visit_Import(self, node: ast.Import) -> None:  # noqa: N802
        self.imports += len(node.names)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
        # Count `from x import a, b, c` as one import statement (matches the
        # behavior most users mean when they say "imports").
        self.imports += 1
        self.generic_visit(node)

    # --------------- comprehensions / lambdas / f-strings

    def visit_ListComp(self, node: ast.ListComp) -> None:  # noqa: N802
        self.list_comprehensions += 1
        self.generic_visit(node)

    def visit_SetComp(self, node: ast.SetComp) -> None:  # noqa: N802
        self.list_comprehensions += 1
        self.generic_visit(node)

    def visit_DictComp(self, node: ast.DictComp) -> None:  # noqa: N802
        self.list_comprehensions += 1
        self.generic_visit(node)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:  # noqa: N802
        self.list_comprehensions += 1
        self.generic_visit(node)

    def visit_Lambda(self, node: ast.Lambda) -> None:  # noqa: N802
        self.lambda_functions += 1
        self.generic_visit(node)

    def visit_JoinedStr(self, node: ast.JoinedStr) -> None:  # noqa: N802
        # `ast.JoinedStr` is what an f-string parses to.
        self.f_strings += 1
        self.generic_visit(node)


class PythonAstAnalyzer(BaseAnalyzer):
    """AST-driven counts; regex fallback on SyntaxError."""

    # Mirror so existing tests that touch these constants on PythonAnalyzer
    # also work if they're swapped onto this class.
    DOCSTRING = _DOCSTRING
    SINGLE_COMMENT = _SINGLE_COMMENT

    def __init__(self) -> None:
        super().__init__()
        self._fallback = PythonAnalyzer()

    def count_functions_and_classes(self, content: str) -> Tuple[int, int]:
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return self._fallback.count_functions_and_classes(content)
        visitor = _PythonVisitor()
        visitor.visit(tree)
        return visitor.functions, visitor.classes

    def count_imports(self, content: str) -> int:
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return self._fallback.count_imports(content)
        visitor = _PythonVisitor()
        visitor.visit(tree)
        return visitor.imports

    def analyze_content(self, content: str, file_path: str = '') -> FileMetrics:
        metrics = super().analyze_content(content, file_path)

        # Line classification stays regex-based — it matches what every other
        # analyzer in the codebase does, and the AST can't easily tell us
        # "is this triple-quoted string a docstring or a data literal?"
        # without walking the tree and matching positions against lines.
        blank, comment, code = classify_lines(content, _SINGLE_COMMENT, _DOCSTRING)
        metrics.blank_lines = blank
        metrics.comment_lines = comment
        metrics.code_lines = code

        try:
            tree = ast.parse(content)
        except SyntaxError:
            # Hand off to the regex analyzer for the structural numbers but
            # keep the line classification we already computed.
            fb = self._fallback.analyze_content(content, file_path)
            metrics.functions = fb.functions
            metrics.classes = fb.classes
            metrics.imports = fb.imports
            metrics.decorators = fb.decorators
            metrics.list_comprehensions = fb.list_comprehensions
            metrics.lambda_functions = fb.lambda_functions
            metrics.f_strings = fb.f_strings
            return metrics

        visitor = _PythonVisitor()
        visitor.visit(tree)

        metrics.functions = visitor.functions
        metrics.classes = visitor.classes
        metrics.imports = visitor.imports
        metrics.decorators = visitor.decorators
        metrics.list_comprehensions = visitor.list_comprehensions
        metrics.lambda_functions = visitor.lambda_functions
        metrics.f_strings = visitor.f_strings
        metrics.complex_functions = visitor.complex_functions

        return metrics
