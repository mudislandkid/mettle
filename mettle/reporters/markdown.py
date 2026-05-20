import os
from datetime import datetime
from pathlib import Path

from .base import BaseReporter


class MarkdownReporter(BaseReporter):
    def __init__(self, *args, **kwargs):
        # Extract project_name before passing kwargs to parent
        self.project_name = kwargs.pop("project_name", "Code Analysis")
        super().__init__(*args, **kwargs)

    def generate_report(self, output_path: str) -> None:
        """Generate a markdown report."""
        content = []

        # Project title and header
        content.append(f"# {self.project_name}\n")
        content.append("## Code Analysis Report\n")
        content.append(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # Summary statistics
        content.append("## Summary Statistics\n")
        content.append("| Metric | Value | Percentage |")
        content.append("|--------|--------|------------|")
        content.append(f"| Total Directories | {self.total_dirs} | |")
        content.append(f"| Total Files | {self.total_files} | |")
        content.append(f"| Total Lines | {self.total_lines} | 100% |")

        if self.total_lines > 0:
            code_percent = f"{(self.total_code_lines / self.total_lines) * 100:.1f}%"
            comment_percent = f"{(self.total_comment_lines / self.total_lines) * 100:.1f}%"
            blank_percent = f"{(self.total_blank_lines / self.total_lines) * 100:.1f}%"

            content.append(
                f"| &nbsp;&nbsp;├─ Code Lines | {self.total_code_lines} | {code_percent} |"
            )
            content.append(
                f"| &nbsp;&nbsp;├─ Comment Lines | {self.total_comment_lines} | {comment_percent} |"
            )
            content.append(
                f"| &nbsp;&nbsp;└─ Blank Lines | {self.total_blank_lines} | {blank_percent} |"
            )

        content.append(f"| Total Characters | {self.total_characters} | |")
        content.append(f"| Total Words | {self.total_words} | |")
        content.append(f"| Functions | {self.total_functions} | |")
        content.append(f"| Classes | {self.total_classes} | |")
        content.append(f"| TODOs | {self.total_todos} | |")
        content.append(f"| Imports | {self.total_imports} | |")

        if self.total_files > 0:
            avg_lines = self.total_lines / self.total_files
            avg_code_lines = self.total_code_lines / self.total_files
            content.append(f"| Average Lines/File | {avg_lines:.1f} | |")
            content.append(f"| Average Code Lines/File | {avg_code_lines:.1f} | |")

        content.append("\n")

        # Add language-specific sections
        content.append("## Language Statistics\n")

        for language, metrics in self.metrics_by_language.items():
            content.append(f"### {language}\n")
            content.append("| Metric | Value |")
            content.append("|--------|--------|")

            # Add file statistics
            stats = self.language_stats.get(language, {})
            content.append(f"| Total Files | {stats.get('total_files', 0)} |")
            content.append(f"| Average Lines/File | {stats.get('avg_lines_per_file', 0):.1f} |")
            content.append(f"| Median Lines/File | {stats.get('median_lines_per_file', 0):.1f} |")

            # Add largest file information
            if language in self.largest_line_files:
                file_path, line_count = self.largest_line_files[language]
                basename = os.path.basename(file_path)
                content.append(f"| Largest File | {basename} |")
                content.append(f"| Largest File Path | {file_path} |")
                content.append(f"| Largest File Lines | {line_count} |")

            # Add common metrics
            content.append(f"| Total Lines | {metrics.total_lines} |")
            content.append(f"| Code Lines | {metrics.code_lines} |")
            content.append(f"| Comment Lines | {metrics.comment_lines} |")
            content.append(f"| Blank Lines | {metrics.blank_lines} |")
            content.append(f"| Total Characters | {metrics.characters} |")
            content.append(f"| Total Words | {metrics.words} |")

            if metrics.total_lines > 0:
                avg_line_length = (
                    metrics.characters / (metrics.total_lines - metrics.blank_lines)
                    if (metrics.total_lines - metrics.blank_lines) > 0
                    else 0
                )
                content.append(f"| Average Line Length | {avg_line_length:.2f} |")

            content.append(f"| Functions | {metrics.functions} |")
            content.append(f"| Classes | {metrics.classes} |")
            content.append(f"| TODOs | {metrics.todos} |")
            content.append(f"| Imports | {metrics.imports} |")

            # Add language-specific metrics
            if language == "Python":
                content.append(f"| Decorators | {getattr(metrics, 'decorators', 0)} |")
                content.append(
                    f"| List Comprehensions | {getattr(metrics, 'list_comprehensions', 0)} |"
                )
                content.append(f"| Lambda Functions | {getattr(metrics, 'lambda_functions', 0)} |")
                content.append(f"| f-strings | {getattr(metrics, 'f_strings', 0)} |")

            elif language in ["HTML", "CSS"]:
                content.append(f"| Elements | {getattr(metrics, 'elements', 0)} |")
                content.append(f"| Attributes | {getattr(metrics, 'attributes', 0)} |")
                content.append(f"| Media Queries | {getattr(metrics, 'media_queries', 0)} |")
                content.append(f"| Selectors | {getattr(metrics, 'selectors', 0)} |")

            content.append("\n")

        # Write the report
        Path(output_path).write_text("\n".join(content))
