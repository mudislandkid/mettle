"""
Code Analyzer Module

This module contains the main CodeAnalyzer class responsible for analyzing
code in a directory structure. It coordinates the analysis process by:
1. Walking through the directory structure
2. Identifying files to analyze
3. Delegating language-specific analysis to appropriate analyzers
4. Aggregating metrics across files and languages
5. Tracking statistics like largest files by language

The module is designed to be extensible with new language analyzers and
configurable through the config.yaml file.
"""

import os
import json
from typing import Dict, Set
from rich.console import Console

from ..metrics.file_metrics import FileMetrics
from .directory_analyzer import DirectoryAnalyzer

class CodeAnalyzer:
    """
    Main class for analyzing code in a directory structure.
    
    This class is responsible for:
    - Walking through directories and identifying files to analyze
    - Filtering out excluded files and directories
    - Delegating language-specific analysis to appropriate analyzers
    - Aggregating metrics across files and languages
    - Tracking statistics like largest files by language
    
    Attributes:
        debug (bool): Whether to enable debug logging
        max_lines (int): Maximum number of lines for a file to be analyzed
        exclude_types (list): List of file types to exclude
        exclude_dirs (list): List of directories to exclude
        metrics_by_language (dict): Metrics aggregated by language
        files_by_language (dict): Files analyzed by language
        largest_line_files (dict): Largest file by line count for each language
    """
    
    def __init__(self, debug=False, max_lines=0, exclude_types=None, exclude_dirs=None):
        self.console = Console()
        self.debug = debug
        self.max_lines = max_lines
        self.exclude_types = exclude_types or []
        self.exclude_dirs = exclude_dirs or []
        self.directory_analyzer = DirectoryAnalyzer(debug, max_lines, exclude_types, exclude_dirs)
        self._last_directory: str | None = None

    def analyze_directory(self, directory: str) -> dict:
        self._last_directory = str(directory)
        return self.directory_analyzer.analyze_directory(directory)

    def save_metrics(self, output_path: str):
        # Forward the last analyzed directory so diff-mode can match runs.
        self.directory_analyzer.save_metrics(output_path, source_directory=self._last_directory) 