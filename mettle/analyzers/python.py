import re

from ..metrics.file_metrics import FileMetrics
from .base import BaseAnalyzer, classify_lines, mask_string_literals


class PythonAnalyzer(BaseAnalyzer):
    FUNCTION_PATTERN = re.compile(r"^\s*(?:async\s+)?def\s+\w+\s*\(", re.MULTILINE)
    CLASS_PATTERN = re.compile(r"^\s*class\s+\w+\s*[:\(]", re.MULTILINE)
    IMPORT_PATTERN = re.compile(r"^\s*(?:import|from)\s+\S+", re.MULTILINE)

    DECORATOR_PATTERN = re.compile(r"^\s*@\w", re.MULTILINE)
    # Bounded character classes guard against catastrophic backtracking on
    # minified / pathological files that the old `\[.*for.*in.*\]` could hang on.
    LIST_COMP_PATTERN = re.compile(r"\[[^\[\]\n]{1,300}\bfor\s+\w+\s+in\b[^\[\]\n]{0,300}\]")
    LAMBDA_PATTERN = re.compile(r"\blambda\b[^:\n]{0,200}:")
    F_STRING_PATTERN = re.compile(r'\bf[\'"]')

    SINGLE_COMMENT = re.compile(r"#")
    # Triple-quoted strings can act as block comments (the common docstring case)
    # but they are also legitimate string literals. We treat them as block
    # comments only when the line they start on contains nothing else, which is
    # exactly the docstring case.
    DOCSTRING = re.compile(r'(?:"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\')')

    def _strip_for_pattern_scan(self, content: str) -> str:
        masked = mask_string_literals(content)
        masked = self.DOCSTRING.sub(
            lambda m: "".join("\n" if c == "\n" else " " for c in m.group()),
            masked,
        )
        masked = re.sub(r"#[^\n]*", "", masked)
        return masked

    def count_functions_and_classes(self, content: str) -> tuple[int, int]:
        clean = self._strip_for_pattern_scan(content)
        return len(self.FUNCTION_PATTERN.findall(clean)), len(self.CLASS_PATTERN.findall(clean))

    def count_imports(self, content: str) -> int:
        clean = self._strip_for_pattern_scan(content)
        return len(self.IMPORT_PATTERN.findall(clean))

    def analyze_content(self, content: str, file_path: str = None) -> FileMetrics:
        metrics = super().analyze_content(content, file_path)

        blank, comment, code = classify_lines(content, self.SINGLE_COMMENT, self.DOCSTRING)
        metrics.blank_lines = blank
        metrics.comment_lines = comment
        metrics.code_lines = code

        functions, classes = self.count_functions_and_classes(content)
        metrics.functions = functions
        metrics.classes = classes
        metrics.imports = self.count_imports(content)

        clean = self._strip_for_pattern_scan(content)
        metrics.decorators = len(self.DECORATOR_PATTERN.findall(clean))
        metrics.list_comprehensions = len(self.LIST_COMP_PATTERN.findall(clean))
        metrics.lambda_functions = len(self.LAMBDA_PATTERN.findall(clean))
        metrics.f_strings = len(self.F_STRING_PATTERN.findall(content))

        return metrics
