from ..metrics.file_metrics import FileMetrics
from .base import BaseAnalyzer


class MarkdownAnalyzer(BaseAnalyzer):
    """Markdown is documentation, not code. We track total_lines so the file
    still shows up in markdown-specific stats, but leave code/comment/blank
    at zero so it never inflates the project's lines-of-code totals.
    """

    def analyze_content(self, content: str, file_path: str) -> FileMetrics:
        metrics = FileMetrics()
        metrics.total_lines = len(content.splitlines())
        return metrics
