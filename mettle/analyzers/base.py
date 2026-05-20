import re
from abc import ABC

from ..metrics.file_metrics import FileMetrics

# Match TODO / FIXME / XXX / HACK as a standalone token (word-bounded, any case).
# This avoids the `todoList` / `Todo.py` false positives the old `count('todo')`
# would produce.
_TODO_RE = re.compile(r"\b(?:TODO|FIXME|XXX|HACK)\b", re.IGNORECASE)

# Quoted strings — used to mask string contents before scanning for comments so
# patterns like `//` inside `"https://..."` don't get counted as comment markers.
# Matches double, single, and backtick strings, allowing simple `\.` escapes.
_STRING_LITERAL_RE = re.compile(
    r'"(?:\\.|[^"\\\n])*"' r"|'(?:\\.|[^'\\\n])*'" r"|`(?:\\.|[^`\\])*`"
)


def mask_string_literals(content: str) -> str:
    """Replace string contents with spaces (preserving newlines / line count)."""

    def _blank_out(match: re.Match) -> str:
        text = match.group()
        return "".join("\n" if c == "\n" else " " for c in text)

    return _STRING_LITERAL_RE.sub(_blank_out, content)


def classify_lines(
    content: str,
    line_comment_re: "re.Pattern[str] | None" = None,
    block_comment_re: "re.Pattern[str] | None" = None,
) -> tuple[int, int, int]:
    """Return (blank_lines, comment_lines, code_lines) for a piece of source.

    A line that contains both code and a trailing comment is counted as code
    (matches what every reasonable "lines of code" tool does). Block comments
    that span multiple lines count their fully-blank interior lines as comment
    lines; the opening/closing lines that also contain code count as code.
    Guarantees blank + comment + code == total_lines, so callers can't end up
    with negative `code_lines`.
    """
    if not content:
        return 0, 0, 0

    lines = content.splitlines() or [""]
    total = len(lines)

    has_code = [False] * total
    has_comment = [False] * total

    # Mask out string literals first so // or # or /* inside strings don't lie.
    masked = mask_string_literals(content)

    # Mark block-comment regions.
    if block_comment_re is not None:
        for match in block_comment_re.finditer(masked):
            start_line = masked.count("\n", 0, match.start())
            end_line = masked.count("\n", 0, match.end())
            for i in range(start_line, min(end_line + 1, total)):
                has_comment[i] = True

    # Build a version of `masked` with block comments replaced by spaces so the
    # line-comment scan doesn't trip over them.
    if block_comment_re is not None:
        masked_no_block = block_comment_re.sub(
            lambda m: "".join("\n" if c == "\n" else " " for c in m.group()),
            masked,
        )
    else:
        masked_no_block = masked

    masked_lines = masked_no_block.splitlines() or [""]
    # Pad/truncate to match line count from the original splitlines.
    if len(masked_lines) < total:
        masked_lines.extend([""] * (total - len(masked_lines)))
    elif len(masked_lines) > total:
        masked_lines = masked_lines[:total]

    for i, masked_line in enumerate(masked_lines):
        if line_comment_re is not None:
            m = line_comment_re.search(masked_line)
            if m is not None:
                has_comment[i] = True
                code_part = masked_line[: m.start()]
            else:
                code_part = masked_line
        else:
            code_part = masked_line

        if code_part.strip():
            has_code[i] = True

    blank = 0
    comment_only = 0
    code_lines = 0
    for i, original in enumerate(lines):
        if not original.strip():
            blank += 1
        elif has_code[i]:
            code_lines += 1
        elif has_comment[i]:
            comment_only += 1
        else:
            # Non-blank line that didn't classify (shouldn't really happen) —
            # count it as code so totals add up.
            code_lines += 1

    return blank, comment_only, code_lines


class BaseAnalyzer(ABC):
    def count_functions_and_classes(self, content: str) -> tuple[int, int]:
        """Count functions and classes in the code.

        This base implementation returns (0, 0).
        Language-specific analyzers should override this method.
        """
        return 0, 0

    def count_imports(self, content: str) -> int:
        """Count import statements.

        This base implementation returns 0.
        Language-specific analyzers should override this method.
        """
        return 0

    def analyze_content(self, content: str, file_path: str) -> FileMetrics:
        """Analyze file content and return metrics.

        This base implementation provides basic metrics that are common across
        all languages. Language-specific analyzers should override this method
        to add their own metrics while calling super().analyze_content() first.
        """
        metrics = FileMetrics()

        lines = content.splitlines()
        metrics.total_lines = len(lines)

        blank = 0
        non_empty_lengths = []
        words = 0
        non_ws_chars = 0
        for line in lines:
            stripped = line.strip()
            if not stripped:
                blank += 1
                continue
            non_empty_lengths.append(len(line))
            tokens = stripped.split()
            words += len(tokens)
            for tok in tokens:
                non_ws_chars += len(tok)

        metrics.blank_lines = blank
        metrics.characters = non_ws_chars
        metrics.words = words

        if non_empty_lengths:
            metrics.avg_line_length = sum(non_empty_lengths) / len(non_empty_lengths)
            metrics.max_line_length = max(non_empty_lengths)

        # Count and capture TODO/FIXME/XXX/HACK markers with their line context.
        # `todo_items` is a list of (line_no, marker, full_line_text) tuples;
        # we cap it per-file so a pathological file can't blow up memory.
        TODO_PER_FILE_CAP = 50
        todo_items = []
        total_todos = 0
        for line_no, raw in enumerate(lines, start=1):
            for match in _TODO_RE.finditer(raw):
                total_todos += 1
                if len(todo_items) < TODO_PER_FILE_CAP:
                    todo_items.append((line_no, match.group(0).upper(), raw.strip()))
        metrics.todos = total_todos
        metrics.todo_items = todo_items

        # Default: non-blank lines are code lines until a language analyzer
        # subtracts its own comment count.
        metrics.code_lines = metrics.total_lines - metrics.blank_lines
        metrics.comment_lines = 0

        return metrics

    def count_blank_lines(self, content: str) -> int:
        """Count blank lines in the content."""
        return sum(1 for line in content.splitlines() if not line.strip())

    def count_todos(self, content: str) -> int:
        """Count TODO/FIXME/XXX/HACK markers."""
        return len(_TODO_RE.findall(content))
