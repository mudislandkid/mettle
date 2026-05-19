"""
Directory Analyzer Module

This module contains the DirectoryAnalyzer class responsible for analyzing
directories of code. It handles:
1. Walking through directory structures
2. Filtering out excluded directories
3. Delegating file analysis to FileAnalyzer
4. Aggregating metrics across files and languages
5. Calculating statistics for each language
"""

import heapq
import os
import json
from statistics import median
from typing import Dict, List, Set, Tuple
from rich.console import Console
from ..metrics.file_metrics import FileMetrics
from .file_analyzer import FileAnalyzer, is_test_file
from ..config_manager import ConfigManager

class DirectoryAnalyzer:
    """
    Class for analyzing directories of code.
    
    This class is responsible for:
    - Walking through directory structures
    - Filtering out excluded directories
    - Delegating file analysis to FileAnalyzer
    - Aggregating metrics across files and languages
    - Calculating statistics for each language
    
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
        """
        Initialize the DirectoryAnalyzer.
        
        Args:
            debug: Whether to enable debug logging
            max_lines: Maximum number of lines for a file to be analyzed
            exclude_types: List of file types to exclude
            exclude_dirs: List of directories to exclude
        """
        self.console = Console()
        self.config_manager = ConfigManager()
        self.debug = debug
        self.max_lines = max_lines
        self.exclude_types = exclude_types or []
        self.exclude_dirs = exclude_dirs or []
        self.file_analyzer = FileAnalyzer(debug, max_lines, exclude_types)
        
        # Default excludes as a fallback (mirrors config.yaml)
        self.default_excludes = {
            # Version control
            '.git', '.svn', '.hg',
            # Package managers / dependencies
            'node_modules', 'bower_components', 'vendor',
            'venv', '.venv', '__pycache__',
            '.pio', '.platformio',
            # iOS / CocoaPods / Xcode
            'Pods', 'xcuserdata', 'DerivedData', '.expo',
            # ESP-IDF managed components
            'managed_components',
            # Build outputs and artifacts
            'build', 'dist', 'out', 'output', 'target',
            'release', 'debug', 'bin', 'obj', '.build',
            'cmake-build-debug', 'cmake-build-release',
            'site-packages', 'wheels', 'eggs', '.eggs',
            '_build', '_site',  # Sphinx / Jekyll
            'storybook-static',
            # IDE and tooling
            '.pytest_cache', '.vscode', '.idea', '.eclipse',
            'coverage', '.next', '.env', '__snapshots__',
            '.cache', '.npm', '.yarn', '.nuxt', '.output',
            '.parcel-cache', '.serverless', '.webpack',
            '.netlify', '.vercel', '.docusaurus',
            '.storybook-static', '.turbo', '.angular',
            '.sass-cache', '.tsbuildinfo', '.nyc_output',
            '.gradle', '.mvn', '.cargo',
            # OS files
            '.DS_Store', '.Trash', '.Trashes',
            # ML directories
            'models', 'weights', 'checkpoints', 'pretrained',
            'snapshots', 'blobs',
            # Generated / incremental
            'incremental', '.fingerprint',
        }
        
        # Metrics storage
        self.metrics_by_language = {}
        self.files_by_language = {}
        self.largest_files = {}
        self.largest_line_files = {}
        self.total_files = 0
        self.total_dirs = 0
    
    def _excluded_dir_set(self) -> Set[str]:
        """Cached set of excluded directory names (computed once per scan)."""
        if getattr(self, "_excluded_dir_cache", None) is None:
            excluded = self.config_manager.get_excluded_dirs() or self.default_excludes
            self._excluded_dir_cache = set(excluded) | set(self.exclude_dirs)
        return self._excluded_dir_cache

    def is_excluded(self, path: str) -> bool:
        """Check if any path segment matches a known excluded directory name."""
        excluded_dirs = self._excluded_dir_set()
        # Split on both separators so a Windows-style exclude like `bin\foo`
        # still matches a posix path component.
        parts = path.replace('\\', '/').split('/')
        for part in parts:
            if part in excluded_dirs:
                return True
        return False
    
    def get_language_stats(self, language: str) -> dict:
        """
        Get detailed statistics for a language.
        
        Args:
            language: The language to get statistics for
            
        Returns:
            A dictionary of statistics for the language
        """
        empty = {'total_files': 0, 'avg_lines_per_file': 0, 'median_lines_per_file': 0}

        files_metrics = self.files_by_language.get(language)
        if not isinstance(files_metrics, dict) or not files_metrics:
            return empty

        lines_per_file = [
            m.total_lines for m in files_metrics.values()
            if isinstance(m, FileMetrics)
        ]
        if not lines_per_file:
            return {**empty, 'total_files': len(files_metrics)}

        avg_lines = sum(lines_per_file) / len(lines_per_file)
        median_lines = median(lines_per_file)  # correct for even-length lists

        if self.debug:
            self.console.print(
                f"[blue]Debug: {language}: {len(lines_per_file)} files, "
                f"avg={avg_lines:.1f}, median={median_lines}[/blue]"
            )

        return {
            'total_files': len(files_metrics),
            'avg_lines_per_file': avg_lines,
            'median_lines_per_file': median_lines,
        }
    
    def analyze_directory(self, directory: str) -> dict:
        """
        Analyze a directory and return metrics.
        
        Args:
            directory: Path to the directory to analyze
            
        Returns:
            A dictionary of metrics for the directory
        """
        self.metrics_by_language = {}
        self.files_by_language = {}
        self.largest_files = {}            # language -> min-heap of (lines, file_path)
        self.largest_line_files = {}       # language -> (path, lines) for the single largest
        self.total_files = 0
        self.total_dirs = 0
        # Test-vs-code totals so the project breakdown can show what fraction
        # of the codebase is actually tests.
        self.test_files = 0
        self.test_total_lines = 0
        self.test_code_lines = 0
        # Captured TODOs across the whole project. Each entry:
        # {"file": str, "line": int, "marker": str, "text": str}
        self.todo_items: list[dict] = []
        # Captured complex functions across the project. Each entry:
        # {"file": str, "name": str, "qualname": str, "complexity": int, "line": int}
        self.complex_functions: list[dict] = []
        # Reset cache counters so debug output shows the savings for *this* scan.
        self.file_analyzer.cache.reset_stats()
        self._excluded_dir_cache = None    # rebuilt lazily on first is_excluded call

        TOP_N = 5
        # `onerror` keeps the walk going past unreadable subdirs (typical on
        # `~/Library`, `node_modules` on a foreign mount, etc.) instead of
        # bombing the entire scan.
        def _on_walk_error(err: OSError) -> None:
            if self.debug:
                self.console.print(f"[yellow]Walk warning: {err}[/yellow]")

        for root, dirs, files in os.walk(directory, onerror=_on_walk_error, followlinks=False):
            # Skip excluded directories in-place (so os.walk doesn't descend into them).
            dirs[:] = [d for d in dirs if not self.is_excluded(os.path.join(root, d))]
            self.total_dirs += len(dirs)

            for file in files:
                file_path = os.path.join(root, file)
                if self.is_excluded(file_path):
                    continue

                language, metrics = self.file_analyzer.analyze_file(file_path)
                if not (language and metrics.total_lines > 0):
                    continue

                self.total_files += 1

                if is_test_file(file_path):
                    self.test_files += 1
                    self.test_total_lines += metrics.total_lines
                    self.test_code_lines += metrics.code_lines

                lang_metrics = self.metrics_by_language.get(language)
                if lang_metrics is None:
                    lang_metrics = FileMetrics()
                    self.metrics_by_language[language] = lang_metrics
                    self.files_by_language[language] = {}
                    self.largest_files[language] = []
                    self.largest_line_files[language] = (file_path, metrics.total_lines)
                elif metrics.total_lines > self.largest_line_files[language][1]:
                    self.largest_line_files[language] = (file_path, metrics.total_lines)

                lang_metrics.total_lines += metrics.total_lines
                lang_metrics.code_lines += metrics.code_lines
                lang_metrics.comment_lines += metrics.comment_lines
                lang_metrics.blank_lines += metrics.blank_lines
                lang_metrics.characters += metrics.characters
                lang_metrics.words += metrics.words
                lang_metrics.functions += metrics.functions
                lang_metrics.classes += metrics.classes
                lang_metrics.todos += metrics.todos
                lang_metrics.imports += metrics.imports
                # JS/TS specifics — most analyzers leave these at zero so the
                # sum is a no-op when the language doesn't care.
                lang_metrics.jsx_components += metrics.jsx_components
                lang_metrics.react_hooks += metrics.react_hooks
                lang_metrics.async_functions += metrics.async_functions
                lang_metrics.interfaces += metrics.interfaces
                lang_metrics.type_aliases += metrics.type_aliases
                lang_metrics.enums += metrics.enums

                self.files_by_language[language][file_path] = metrics

                # Pull this file's TODOs into the project-wide list. The base
                # analyzer already caps per file; we cap the project-wide
                # list at 500 so a 5000-TODO mega-project doesn't bloat the row.
                if metrics.todo_items and len(self.todo_items) < 500:
                    for line_no, marker, text in metrics.todo_items:
                        self.todo_items.append({
                            "file": file_path,
                            "line": line_no,
                            "marker": marker,
                            "text": text[:300],  # clamp absurdly long single lines
                        })
                        if len(self.todo_items) >= 500:
                            break

                # Same shape for complexity hotspots. Only the AST Python
                # analyzer populates these; other analyzers leave the list empty.
                if getattr(metrics, 'complex_functions', None):
                    for name, qualname, complexity, line_no in metrics.complex_functions:
                        self.complex_functions.append({
                            "file": file_path,
                            "name": name,
                            "qualname": qualname,
                            "complexity": complexity,
                            "line": line_no,
                        })

                # Maintain a top-N min-heap per language instead of sorting
                # the full list on every file (was O(n² log n)).
                heap = self.largest_files[language]
                if len(heap) < TOP_N:
                    heapq.heappush(heap, (metrics.total_lines, file_path))
                elif metrics.total_lines > heap[0][0]:
                    heapq.heapreplace(heap, (metrics.total_lines, file_path))

        # Convert the per-language heaps to the (file_path, lines) descending lists
        # that the reporters expect.
        self.largest_files = {
            lang: [(p, n) for n, p in sorted(heap, key=lambda x: x[0], reverse=True)]
            for lang, heap in self.largest_files.items()
        }

        language_stats = {
            lang: self.get_language_stats(lang)
            for lang in self.metrics_by_language.keys()
        }
        
        # Debug: Print largest files by language
        if self.debug:
            self.console.print("\n[bold yellow]Largest files by language:[/bold yellow]")
            for language, files in self.largest_files.items():
                self.console.print(f"\n[bold cyan]{language}:[/bold cyan]")
                for file_path, lines in files:
                    self.console.print(f"  - {file_path}: {lines} lines")
        
        cache = self.file_analyzer.cache
        if self.debug:
            self.console.print(
                f"[dim]file-metrics cache: {cache.hits} hits, {cache.misses} misses[/dim]"
            )

        return {
            'metrics_by_language': self.metrics_by_language,
            'language_stats': language_stats,
            'total_files': self.total_files,
            'total_dirs': self.total_dirs,
            'largest_line_files': self.largest_line_files,
            'test_files': self.test_files,
            'test_total_lines': self.test_total_lines,
            'test_code_lines': self.test_code_lines,
            'todo_items': self.todo_items,
            # Top 30 by complexity, then alpha to keep ordering deterministic.
            'complex_functions': sorted(
                self.complex_functions,
                key=lambda f: (-f['complexity'], f['file'], f['line']),
            )[:30],
            'cache_hits': cache.hits,
            'cache_misses': cache.misses,
        }
    
    def save_metrics(self, output_path: str, source_directory: str | None = None):
        """Save metrics to a JSON file, optionally tagging it with the source dir.

        `source_directory` is what `code-counter --compare-to-last` uses to
        find the right previous run to diff against, so always pass it when
        you have it.
        """
        serializable_metrics = {}
        for language, metrics in self.metrics_by_language.items():
            serializable_metrics[language] = {
                'total_lines': metrics.total_lines,
                'code_lines': metrics.code_lines,
                'comment_lines': metrics.comment_lines,
                'blank_lines': metrics.blank_lines,
                'characters': metrics.characters,
                'words': metrics.words,
                'functions': metrics.functions,
                'classes': metrics.classes,
                'todos': metrics.todos,
                'imports': metrics.imports,
            }

        output_data = {
            'metrics_by_language': serializable_metrics,
            'total_files': self.total_files,
            'total_dirs': self.total_dirs,
            'test_files': self.test_files,
            'test_total_lines': self.test_total_lines,
            'test_code_lines': self.test_code_lines,
        }
        if source_directory:
            output_data['source_directory'] = str(source_directory)

        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)
