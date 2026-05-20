import re

from ..metrics.file_metrics import FileMetrics
from .base import BaseAnalyzer, classify_lines, mask_string_literals


class CStyleAnalyzer(BaseAnalyzer):
    """Analyzer for languages that use C-style comments (// and /* */).

    Covers: Rust, Go, C/C++, Java, Swift, Kotlin, Terraform (HCL),
    and any other language using // single-line and /* */ multi-line comments.

    Language-specific subclasses can override function/class/import patterns
    while inheriting the comment-stripping logic.
    """

    SINGLE_COMMENT = re.compile(r"//")
    MULTI_COMMENT = re.compile(r"/\*[\s\S]*?\*/")

    FUNCTION_PATTERN = re.compile(
        r"(?:"
        r"fn\s+\w+|"  # Rust
        r"func\s+\w+|"  # Go / Swift
        r"fun\s+\w+|"  # Kotlin
        r"(?:void|int|bool|char|float|double|auto|static|inline)\s+\w+\s*\(|"
        r"(?:public|private|protected)\s+\w+\s+\w+\s*\("
        r")",
        re.MULTILINE,
    )
    CLASS_PATTERN = re.compile(
        r"(?:"
        r"(?:pub\s+)?(?:struct|enum|trait|impl)\s+\w+|"
        r"(?:type\s+\w+\s+struct)|"
        r"(?:class|interface|object)\s+\w+"
        r")",
        re.MULTILINE,
    )
    IMPORT_PATTERN = re.compile(
        r"(?:" r"^\s*use\s+\w+|" r"^\s*import\s+|" r"^\s*#include\s+" r")", re.MULTILINE
    )

    def count_functions_and_classes(self, content: str) -> tuple[int, int]:
        clean = self._strip_for_pattern_scan(content)
        functions = len(self.FUNCTION_PATTERN.findall(clean))
        classes = len(self.CLASS_PATTERN.findall(clean))
        return functions, classes

    def count_imports(self, content: str) -> int:
        clean = self._strip_for_pattern_scan(content)
        return len(self.IMPORT_PATTERN.findall(clean))

    def _strip_for_pattern_scan(self, content: str) -> str:
        """Mask strings + remove comments, preserving line layout for ^/$."""
        masked = mask_string_literals(content)
        masked = self.MULTI_COMMENT.sub(
            lambda m: "".join("\n" if c == "\n" else " " for c in m.group()),
            masked,
        )
        # remove from `//` to end of line
        masked = re.sub(r"//[^\n]*", "", masked)
        return masked

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

        return metrics


class ObjectiveCAnalyzer(CStyleAnalyzer):
    """Analyzer for Objective-C and Objective-C++ (.m, .mm)."""

    FUNCTION_PATTERN = re.compile(
        r"(?:"
        r"^[-+]\s*\([^)]+\)\s*\w+|"
        r"(?:void|int|bool|char|float|double|auto|static|inline|id)\s+\w+\s*\("
        r")",
        re.MULTILINE,
    )
    CLASS_PATTERN = re.compile(r"@(?:interface|implementation|protocol)\s+\w+", re.MULTILINE)
    IMPORT_PATTERN = re.compile(r"^\s*#(?:import|include)\s+", re.MULTILINE)


class ShellAnalyzer(BaseAnalyzer):
    """Analyzer for shell scripts (bash, zsh, fish) which use # comments."""

    # `#` not preceded by a word/$ char (to avoid `foo#bar` strings) and not
    # followed by `!` (shebang already on its own line is handled below).
    SINGLE_COMMENT = re.compile(r"(?<![\w$])#(?!!)")
    FUNCTION_PATTERN = re.compile(r"(?:function\s+\w+|\w+\s*\(\)\s*\{)", re.MULTILINE)

    def count_functions_and_classes(self, content: str) -> tuple[int, int]:
        functions = len(self.FUNCTION_PATTERN.findall(content))
        return functions, 0

    def analyze_content(self, content: str, file_path: str = None) -> FileMetrics:
        metrics = super().analyze_content(content, file_path)

        blank, comment, code = classify_lines(content, self.SINGLE_COMMENT, None)
        metrics.blank_lines = blank
        metrics.comment_lines = comment
        metrics.code_lines = code

        functions, _ = self.count_functions_and_classes(content)
        metrics.functions = functions

        return metrics
