import unittest

from ..analyzers.factory import AnalyzerFactory
from ..analyzers.html_css import HTMLCSSAnalyzer
from ..analyzers.javascript import JavaScriptAnalyzer
from ..analyzers.python import PythonAnalyzer
from ..analyzers.python_ast import PythonAstAnalyzer
from ..analyzers.test_detection import is_test_file


class TestTestFileDetection(unittest.TestCase):
    """The test-file detector backs the test-vs-code segregation feature."""

    def test_pytest_style(self):
        self.assertTrue(is_test_file("/proj/test_module.py"))
        self.assertTrue(is_test_file("/proj/tests/test_module.py"))
        self.assertTrue(is_test_file("/proj/src/foo_test.py"))

    def test_go_style(self):
        self.assertTrue(is_test_file("/proj/foo_test.go"))

    def test_js_spec_and_test(self):
        self.assertTrue(is_test_file("/proj/foo.spec.ts"))
        self.assertTrue(is_test_file("/proj/foo.test.tsx"))
        self.assertTrue(is_test_file("/proj/__tests__/foo.tsx"))

    def test_e2e_dir_and_cypress(self):
        self.assertTrue(is_test_file("/proj/cypress/login.js"))
        self.assertTrue(is_test_file("/proj/e2e/checkout.spec.ts"))

    def test_negatives(self):
        # Common false-positive shapes the regex needs to reject.
        self.assertFalse(is_test_file("/proj/latest.py"))
        self.assertFalse(is_test_file("/proj/manifesto.md"))
        self.assertFalse(is_test_file("/proj/src/foo.py"))
        self.assertFalse(is_test_file("/proj/contestant.go"))


class LineSumInvariant(unittest.TestCase):
    """blank + comment + code must always equal total_lines."""

    def _check(self, analyzer, content, path):
        m = analyzer.analyze_content(content, path)
        self.assertEqual(
            m.blank_lines + m.comment_lines + m.code_lines,
            m.total_lines,
            f"sum mismatch for {path}: "
            f"blank={m.blank_lines} comment={m.comment_lines} code={m.code_lines} total={m.total_lines}",
        )

    def test_python_invariant(self):
        self._check(PythonAnalyzer(), "\n\n# c\ndef f(): pass\n", "x.py")

    def test_javascript_invariant(self):
        self._check(JavaScriptAnalyzer(), "// c\nfunction f(){}\n/* m */\n", "x.js")

    def test_html_invariant(self):
        self._check(HTMLCSSAnalyzer(), "<!-- c -->\n<div>x</div>\n", "x.html")

    def test_css_invariant(self):
        self._check(HTMLCSSAnalyzer(), "/* c */\nbody { color: red; }\n", "x.css")


class TestPythonAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = PythonAnalyzer()

    def test_python_metrics(self):
        content = """
def decorator(func):
    return func

@decorator
def example():
    # TODO: implement
    pass

class MyClass:
    def __init__(self):
        self.value = [x for x in range(10)]
        self.func = lambda x: x * 2
        print(f"Value: {self.value}")

from typing import List
import os
"""
        metrics = self.analyzer.analyze_content(content, "test.py")
        # decorator, example, __init__
        self.assertEqual(metrics.functions, 3)
        self.assertEqual(metrics.classes, 1)
        self.assertEqual(metrics.decorators, 1)
        self.assertEqual(metrics.list_comprehensions, 1)
        self.assertEqual(metrics.lambda_functions, 1)
        self.assertEqual(metrics.f_strings, 1)
        self.assertEqual(metrics.imports, 2)
        self.assertEqual(metrics.todos, 1)

    def test_string_with_hash_not_counted_as_comment(self):
        # The `#` inside the string must not be treated as a comment marker.
        content = 'url = "https://example.com"  # real comment\n'
        m = self.analyzer.analyze_content(content, "x.py")
        self.assertEqual(m.code_lines, 1)
        self.assertEqual(m.comment_lines, 0)  # inline trailing comment on a code line

    def test_todo_capture(self):
        content = (
            "# TODO: refactor this\n"
            "def foo():\n"
            "    return 1  # FIXME later\n"
            "    # xxx debug\n"  # case-insensitive match
            "    # HACK: workaround\n"
        )
        m = self.analyzer.analyze_content(content, "x.py")
        self.assertEqual(m.todos, 4)
        markers = [marker for _, marker, _ in m.todo_items]
        self.assertEqual(sorted(markers), ["FIXME", "HACK", "TODO", "XXX"])
        lines = [ln for ln, _, _ in m.todo_items]
        self.assertEqual(lines, [1, 3, 4, 5])
        # Text is preserved verbatim (stripped).
        self.assertIn("refactor this", m.todo_items[0][2])


class TestPythonAstAnalyzer(unittest.TestCase):
    """AST-based Python analyzer: exact counts for things the regex one fakes."""

    def setUp(self):
        self.analyzer = PythonAstAnalyzer()

    def test_counts_async_and_nested(self):
        content = (
            "async def fetch():\n"
            "    pass\n"
            "\n"
            "def outer():\n"
            "    def inner():\n"
            "        pass\n"
            "    return inner\n"
            "\n"
            "class C:\n"
            "    async def coro(self):\n"
            "        pass\n"
        )
        m = self.analyzer.analyze_content(content, "x.py")
        # fetch, outer, inner, coro = 4 functions; coro + fetch = 2 async.
        self.assertEqual(m.functions, 4)
        self.assertEqual(m.classes, 1)

    def test_triple_quote_data_literal_not_a_decorator_inflater(self):
        content = (
            'BANNER = """\n'
            "  multi-line\n"
            "  literal data\n"
            '"""\n'
            "\n"
            "def go():\n"
            "    return BANNER\n"
        )
        m = self.analyzer.analyze_content(content, "x.py")
        # No decorators in the source; previously the regex pattern could be
        # confused by stray @ in long string literals, but the AST is exact.
        self.assertEqual(m.decorators, 0)
        self.assertEqual(m.functions, 1)

    def test_decorator_with_arguments_counted_once(self):
        content = (
            "from functools import wraps\n"
            "\n"
            "def deco(arg):\n"
            "    def wrap(f):\n"
            "        @wraps(f)\n"
            "        def inner(*a, **kw):\n"
            "            return f(*a, **kw)\n"
            "        return inner\n"
            "    return wrap\n"
            "\n"
            "@deco('x')\n"
            "def target():\n"
            "    pass\n"
        )
        m = self.analyzer.analyze_content(content, "x.py")
        # Decorators applied: @wraps(f) once, @deco('x') once → 2.
        self.assertEqual(m.decorators, 2)
        # Functions: deco, wrap, inner, target → 4.
        self.assertEqual(m.functions, 4)

    def test_comprehensions_and_lambdas(self):
        content = (
            "xs = [x for x in range(10)]\n"
            "ys = {y for y in xs}\n"
            "zs = {k: v for k, v in zip(xs, xs)}\n"
            "gs = (g for g in xs)\n"
            "fn = lambda x: x + 1\n"
            "msg = f'value={fn(1)}'\n"
        )
        m = self.analyzer.analyze_content(content, "x.py")
        # list + set + dict + generator
        self.assertEqual(m.list_comprehensions, 4)
        self.assertEqual(m.lambda_functions, 1)
        self.assertEqual(m.f_strings, 1)

    def test_syntax_error_falls_back_to_regex(self):
        # Mixed-tab nonsense → SyntaxError; AST analyzer must not crash.
        content = "def foo(:\n  pass\n"
        m = self.analyzer.analyze_content(content, "x.py")
        # Regex fallback handles this; just assert it didn't blow up.
        self.assertEqual(m.total_lines, 2)

    def test_factory_uses_ast_analyzer_for_python(self):
        factory = AnalyzerFactory()
        # `get_analyzer` caches instances; identity check should be the AST class.
        analyzer = factory.get_analyzer("foo.py")
        self.assertIsInstance(analyzer, PythonAstAnalyzer)

    def test_complexity_captures_branches(self):
        content = (
            "def simple():\n"
            "    return 1\n"
            "\n"
            "def branchy(x, y):\n"
            "    if x and y:\n"
            "        if x > 0:\n"
            "            return 1\n"
            "        elif x < 0:\n"
            "            return -1\n"
            "    for i in range(10):\n"
            "        try:\n"
            "            assert i\n"
            "        except ValueError:\n"
            "            pass\n"
            "    return 0\n"
        )
        m = self.analyzer.analyze_content(content, "x.py")
        by_name = {qual: c for _, qual, c, _ in m.complex_functions}
        self.assertEqual(by_name["simple"], 1)
        # branchy: 1 base + if + bool-and + if + elif + for + try-except + assert = 8.
        self.assertGreaterEqual(by_name["branchy"], 7)

    def test_complexity_includes_class_qualname(self):
        content = (
            "class C:\n"
            "    def m(self):\n"
            "        if True:\n"
            "            return 1\n"
            "        return 0\n"
        )
        m = self.analyzer.analyze_content(content, "x.py")
        quals = [q for _, q, _, _ in m.complex_functions]
        self.assertIn("C.m", quals)


class TestJavaScriptAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = JavaScriptAnalyzer()

    def test_function_count_excludes_control_flow(self):
        # The old regex matched every `if(){}`/`for(){}`/`while(){}` as a
        # "function". Make sure that regression doesn't come back.
        content = """
function real() {
    if (x) {}
    for (let i = 0; i < 10; i++) {}
    while (true) {}
}
const arrow = () => 1;
"""
        m = self.analyzer.analyze_content(content, "x.js")
        self.assertEqual(m.functions, 2)
        self.assertEqual(m.classes, 0)

    def test_double_slash_inside_string_not_counted(self):
        content = 'const url = "https://example.com"; // real comment\n'
        m = self.analyzer.analyze_content(content, "x.js")
        self.assertEqual(m.code_lines, 1)
        # The trailing `// real comment` is on a code line, so it's not
        # counted as a comment-only line.
        self.assertEqual(m.comment_lines, 0)

    def test_jsx_components_and_react_hooks(self):
        content = (
            "import { useState, useEffect } from 'react'\n"
            "function App() {\n"
            "  const [n, setN] = useState(0)\n"
            "  useEffect(() => {}, [])\n"
            "  const useCustom = () => 1\n"
            "  return (\n"
            "    <div>\n"
            "      <Header title='hi' />\n"
            "      <Footer><Brand /></Footer>\n"
            "    </div>\n"
            "  )\n"
            "}\n"
        )
        m = self.analyzer.analyze_content(content, "App.tsx")
        # Uppercase tags: Header, Footer, Brand = 3
        self.assertEqual(m.jsx_components, 3)
        # Hook calls: useState, useEffect = 2; `useCustom` is defined but not called.
        self.assertEqual(m.react_hooks, 2)

    def test_async_functions_counted(self):
        content = (
            "async function fetchA() {}\n"
            "const fetchB = async () => 1\n"
            "const o = {\n"
            "  async fetchC() { return 1 }\n"
            "}\n"
            "function notAsync() {}\n"
        )
        m = self.analyzer.analyze_content(content, "x.ts")
        # 3 async forms; notAsync should not be picked up.
        self.assertEqual(m.async_functions, 3)

    def test_typescript_declarations(self):
        content = (
            "export interface User { id: number; name: string }\n"
            "interface Internal { foo: boolean }\n"
            "export type Id = string | number\n"
            "type Pair<T> = [T, T]\n"
            "enum Color { Red, Green }\n"
            "export const enum Size { S, M, L }\n"
        )
        m = self.analyzer.analyze_content(content, "x.ts")
        self.assertEqual(m.interfaces, 2)
        self.assertEqual(m.type_aliases, 2)
        self.assertEqual(m.enums, 2)


class TestHTMLCSSAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = HTMLCSSAnalyzer()

    def test_html_metrics(self):
        content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Test</title>
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar">
        <a href="/" id="home">Home</a>
    </nav>
</body>
</html>
"""
        metrics = self.analyzer.analyze_content(content, "test.html")
        # html, head, meta, title, body, nav, a (closing tags and <!DOCTYPE>
        # are intentionally not counted)
        self.assertEqual(metrics.elements, 7)
        self.assertEqual(metrics.attributes, 5)  # lang, charset, class, href, id
        self.assertEqual(metrics.comment_lines, 1)

    def test_css_metrics(self):
        content = """
/* Base styles */
.navbar {
    display: flex;
}

@media screen and (max-width: 768px) {
    .navbar {
        flex-direction: column;
    }
}

.navbar a {
    color: blue;
}

#home {
    font-weight: bold;
}
"""
        metrics = self.analyzer.analyze_content(content, "test.css")
        self.assertEqual(metrics.media_queries, 1)
        # .navbar, .navbar (nested), .navbar a, #home
        self.assertEqual(metrics.selectors, 4)
        self.assertEqual(metrics.comment_lines, 1)


class TestAnalyzerFactory(unittest.TestCase):
    def setUp(self):
        self.factory = AnalyzerFactory()

    def test_language_detection(self):
        self.assertEqual(self.factory.get_language("test.py"), "Python")
        self.assertEqual(self.factory.get_language("test.js"), "JavaScript")
        self.assertEqual(self.factory.get_language("test.tsx"), "TypeScript")
        self.assertEqual(self.factory.get_language("test.d.ts"), "TypeScript")
        self.assertEqual(self.factory.get_language("test.html"), "HTML")
        self.assertEqual(self.factory.get_language("test.css"), "CSS")
        self.assertEqual(self.factory.get_language("test.unknown"), "Other")

    def test_analyzer_caching(self):
        # get_analyzer should return the same instance per language.
        a1 = self.factory.get_analyzer("test.py")
        a2 = self.factory.get_analyzer("other.py")
        self.assertIs(a1, a2)


if __name__ == "__main__":
    unittest.main()
