from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseReporter(ABC):
    """Base class for all reporters."""
    
    def __init__(self, metrics_by_language: dict, language_stats: dict, total_files: int, total_dirs: int, largest_line_files: dict = None):
        """Initialize reporter with metrics.
        
        Args:
            metrics_by_language: Dictionary containing metrics per language
            language_stats: Dictionary containing language-specific statistics
            total_files: Total number of files analyzed
            total_dirs: Total number of directories analyzed
            largest_line_files: Dictionary mapping language to (file_path, line_count) tuples
        """
        self.metrics_by_language = metrics_by_language
        self.language_stats = language_stats
        self.total_files = total_files
        self.total_dirs = total_dirs
        self.largest_line_files = largest_line_files or {}
        
        # Calculate totals
        self.total_lines = 0
        self.total_code_lines = 0
        self.total_comment_lines = 0
        self.total_blank_lines = 0
        self.total_characters = 0
        self.total_words = 0
        self.total_functions = 0
        self.total_classes = 0
        self.total_todos = 0
        self.total_imports = 0
        
        self._calculate_totals()
    
    def _calculate_totals(self):
        """Calculate total metrics from language-specific metrics."""
        for metrics in self.metrics_by_language.values():
            self.total_lines += metrics.total_lines
            self.total_code_lines += metrics.code_lines
            self.total_comment_lines += metrics.comment_lines
            self.total_blank_lines += metrics.blank_lines
            self.total_characters += metrics.characters
            self.total_words += metrics.words
            self.total_functions += metrics.functions
            self.total_classes += metrics.classes
            self.total_todos += metrics.todos
            self.total_imports += metrics.imports
    
    @abstractmethod
    def generate_report(self, output_path: str = None):
        """Generate the report.
        
        Args:
            output_path: Optional path to save the report to
        """
        pass 