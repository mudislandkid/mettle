from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.box import ROUNDED
from datetime import datetime
from .base import BaseReporter
import os

class ConsoleReporter(BaseReporter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.console = Console()

    def generate_report(self, output_path: str = None):
        """Generate a console report."""
        console = Console()
        
        # Create summary table
        summary_table = Table(show_header=True, header_style="bold magenta")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", justify="right", style="green")
        summary_table.add_column("Percentage", justify="right", style="blue")
        
        # Add summary metrics
        summary_table.add_row("Total Directories", str(self.total_dirs), "")
        summary_table.add_row("Total Files", str(self.total_files), "")
        summary_table.add_row("Total Lines", str(self.total_lines), "100%")
        
        if self.total_lines > 0:
            code_percent = f"{(self.total_code_lines / self.total_lines) * 100:.1f}%"
            comment_percent = f"{(self.total_comment_lines / self.total_lines) * 100:.1f}%"
            blank_percent = f"{(self.total_blank_lines / self.total_lines) * 100:.1f}%"
            
            summary_table.add_row("  ├─ Code Lines", str(self.total_code_lines), code_percent)
            summary_table.add_row("  ├─ Comment Lines", str(self.total_comment_lines), comment_percent)
            summary_table.add_row("  └─ Blank Lines", str(self.total_blank_lines), blank_percent)
        
        # Add other metrics
        summary_table.add_row("Total Characters", str(self.total_characters), "")
        summary_table.add_row("Total Words", str(self.total_words), "")
        summary_table.add_row("Functions", str(self.total_functions), "")
        summary_table.add_row("Classes", str(self.total_classes), "")
        summary_table.add_row("TODOs", str(self.total_todos), "")
        summary_table.add_row("Imports", str(self.total_imports), "")
        
        # Add averages if there are files
        if self.total_files > 0:
            avg_lines = self.total_lines / self.total_files
            avg_code_lines = self.total_code_lines / self.total_files
            summary_table.add_row("Average Total Lines/File", f"{avg_lines:.1f}", "")
            summary_table.add_row("Average Code Lines/File", f"{avg_code_lines:.1f}", "")
        
        # Print the summary table
        console.print()
        console.print(summary_table)
        console.print()

        # Detailed language statistics
        for language, metrics in self.metrics_by_language.items():
            language_table = Table(show_header=True, header_style="bold magenta")
            language_table.add_column(f"{language} Metrics", style="cyan")
            language_table.add_column("Value", justify="right", style="green")
            
            # Add file statistics
            stats = self.language_stats.get(language, {})
            language_table.add_row("Total Files", str(stats.get('total_files', 0)))
            language_table.add_row("Average Lines/File", f"{stats.get('avg_lines_per_file', 0):.1f}")
            language_table.add_row("Median Lines/File", f"{stats.get('median_lines_per_file', 0):.1f}")
            
            # Add largest file information
            if language in self.largest_line_files:
                file_path, line_count = self.largest_line_files[language]
                basename = os.path.basename(file_path)
                language_table.add_row("Largest File", basename)
                language_table.add_row("Largest File Path", file_path)
                language_table.add_row("Largest File Lines", str(line_count))
            
            # Add common metrics
            language_table.add_row("Total Lines", str(metrics.total_lines))
            language_table.add_row("Code Lines", str(metrics.code_lines))
            language_table.add_row("Comment Lines", str(metrics.comment_lines))
            language_table.add_row("Blank Lines", str(metrics.blank_lines))
            language_table.add_row("Total Characters", str(metrics.characters))
            language_table.add_row("Total Words", str(metrics.words))
            
            if metrics.total_lines > 0:
                avg_line_length = metrics.characters / (metrics.total_lines - metrics.blank_lines) if (metrics.total_lines - metrics.blank_lines) > 0 else 0
                language_table.add_row("Average Line Length", f"{avg_line_length:.2f}")
            
            language_table.add_row("Functions", str(metrics.functions))
            language_table.add_row("Classes", str(metrics.classes))
            language_table.add_row("TODOs", str(metrics.todos))
            language_table.add_row("Imports", str(metrics.imports))
            
            # Add language-specific metrics
            if language == 'Python':
                language_table.add_row("Decorators", str(getattr(metrics, 'decorators', 0)))
                language_table.add_row("List Comprehensions", str(getattr(metrics, 'list_comprehensions', 0)))
                language_table.add_row("Lambda Functions", str(getattr(metrics, 'lambda_functions', 0)))
                language_table.add_row("f-strings", str(getattr(metrics, 'f_strings', 0)))
            
            elif language in ['HTML', 'CSS']:
                language_table.add_row("Elements", str(getattr(metrics, 'elements', 0)))
                language_table.add_row("Attributes", str(getattr(metrics, 'attributes', 0)))
                language_table.add_row("Media Queries", str(getattr(metrics, 'media_queries', 0)))
                language_table.add_row("Selectors", str(getattr(metrics, 'selectors', 0)))
            
            console.print(Panel(language_table, title=language, border_style="blue"))
            console.print() 