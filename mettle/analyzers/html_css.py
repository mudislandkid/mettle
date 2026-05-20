import re
from typing import Tuple
from .base import BaseAnalyzer, classify_lines
from ..metrics.file_metrics import FileMetrics


class HTMLCSSAnalyzer(BaseAnalyzer):
    ELEMENT_PATTERN = re.compile(r'<([a-zA-Z][a-zA-Z0-9-]*)')
    ATTRIBUTE_PATTERN = re.compile(r'\s([a-zA-Z][a-zA-Z0-9-:]*)\s*=\s*["\']')

    MEDIA_QUERY_PATTERN = re.compile(r'@media\b[^{]*\{')
    # Match a CSS rule head: a chunk of selector text followed by `{`, where the
    # selector lives on at most a couple of lines. Anchored against newlines on
    # the left avoids greedy multi-rule matches the old `([^{}/]+){` produced.
    SELECTOR_PATTERN = re.compile(r'(?:^|\})\s*([^{};@\n][^{};]{0,300})\{', re.MULTILINE)

    CSS_COMMENT = re.compile(r'/\*[\s\S]*?\*/')
    HTML_COMMENT = re.compile(r'<!--[\s\S]*?-->')

    def count_elements_and_attributes(self, content: str) -> Tuple[int, int]:
        return (
            len(self.ELEMENT_PATTERN.findall(content)),
            len(self.ATTRIBUTE_PATTERN.findall(content)),
        )

    def count_media_queries_and_selectors(self, content: str) -> Tuple[int, int]:
        content = self.CSS_COMMENT.sub('', content)
        # The selector pattern already excludes `@` rules so we don't have to
        # subtract them — counting both independently gives the natural answer.
        media_queries = len(self.MEDIA_QUERY_PATTERN.findall(content))
        selectors = len(self.SELECTOR_PATTERN.findall(content))
        return media_queries, selectors

    def analyze_content(self, content: str, file_path: str = '') -> FileMetrics:
        metrics = super().analyze_content(content, file_path)

        is_html = (file_path or '').lower().endswith(('.html', '.htm', '.xhtml', '.vue', '.svelte'))

        if is_html:
            blank, comment, code = classify_lines(content, None, self.HTML_COMMENT)
            elements, attributes = self.count_elements_and_attributes(
                self.HTML_COMMENT.sub('', content)
            )
            metrics.elements = elements
            metrics.attributes = attributes
            metrics.media_queries = 0
            metrics.selectors = 0
        else:
            blank, comment, code = classify_lines(content, None, self.CSS_COMMENT)
            mq, sel = self.count_media_queries_and_selectors(content)
            metrics.elements = 0
            metrics.attributes = 0
            metrics.media_queries = mq
            metrics.selectors = sel

        metrics.blank_lines = blank
        metrics.comment_lines = comment
        metrics.code_lines = code

        return metrics
