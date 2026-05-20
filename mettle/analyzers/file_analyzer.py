"""
File Analyzer Module

This module contains the FileAnalyzer class responsible for analyzing
individual files. It handles:
1. Determining if a file should be analyzed
2. Detecting binary files
3. Reading file content
4. Delegating to language-specific analyzers
5. Collecting metrics for a single file
"""

import os
from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console

from ..config_manager import ConfigManager
from ..metrics.file_metrics import FileMetrics
from .cache import FileMetricsCache, get_default_cache
from .factory import AnalyzerFactory
from .test_detection import is_test_file as is_test_file  # noqa: F401

if TYPE_CHECKING:
    from ..secrets import SecretScanner


class FileAnalyzer:
    """
    Class for analyzing individual files.

    This class is responsible for:
    - Determining if a file should be analyzed
    - Detecting binary files
    - Reading file content
    - Delegating to language-specific analyzers
    - Collecting metrics for a single file

    Attributes:
        debug (bool): Whether to enable debug logging
        max_lines (int): Maximum number of lines for a file to be analyzed
        exclude_types (list): List of file types to exclude
    """

    def __init__(
        self,
        debug=False,
        max_lines=0,
        exclude_types=None,
        cache: FileMetricsCache | None = None,
        secret_scanner: "SecretScanner | None" = None,
        project_root: "Path | None" = None,
    ):
        """
        Initialize the FileAnalyzer.

        Args:
            debug: Whether to enable debug logging.
            max_lines: Maximum number of lines for a file to be analyzed.
            exclude_types: List of file types to exclude.
            cache: Optional FileMetricsCache. Defaults to the process-wide
                singleton; pass `FileMetricsCache(enabled=False)` to bypass.
            secret_scanner: Optional SecretScanner. When provided, every
                analysed file is also scanned for secrets and the findings
                are appended to `self.secret_findings`. Cached files reuse
                the cached findings without re-reading the file.
            project_root: Required when `secret_scanner` is set. Used to
                compute the file path relative to the project root for
                inclusion in SecretMatch entries.
        """
        self.console = Console()
        self.config_manager = ConfigManager()
        self.debug = debug
        self.max_lines = max_lines
        self.exclude_types = exclude_types or []
        self.analyzer_factory = AnalyzerFactory()
        self.cache = cache if cache is not None else get_default_cache()
        self._secret_scanner = secret_scanner
        self._project_root = project_root
        self.secret_findings: list[dict] = []

    # Extensions that are always binary (compiled, compressed, media, etc.)
    BINARY_EXTENSIONS = {
        # Images
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".ico",
        ".bmp",
        ".tiff",
        ".tif",
        ".webp",
        ".svg",
        ".psd",
        ".ai",
        ".sketch",
        # Documents
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        # Compiled bytecode / objects
        ".pyc",
        ".pyo",
        ".pyd",
        ".o",
        ".obj",
        ".a",
        ".lib",
        ".class",
        ".jar",
        ".war",
        ".ear",
        # Native binaries / shared libraries
        ".exe",
        ".dll",
        ".so",
        ".dylib",
        ".bin",
        ".elf",
        # Rust build artifacts
        ".rmeta",
        ".rlib",
        # Archives
        ".zip",
        ".tar",
        ".gz",
        ".bz2",
        ".xz",
        ".7z",
        ".rar",
        ".iso",
        ".tgz",
        ".tbz2",
        ".txz",
        ".zst",
        ".lz4",
        # Media
        ".mp3",
        ".mp4",
        ".avi",
        ".mov",
        ".wav",
        ".flac",
        ".ogg",
        ".mkv",
        ".wmv",
        ".flv",
        ".webm",
        ".aac",
        ".m4a",
        # Fonts
        ".ttf",
        ".woff",
        ".woff2",
        ".eot",
        ".otf",
        # Databases
        ".db",
        ".sqlite",
        ".sqlite3",
        ".mdb",
        # OS files
        ".DS_Store",
    }

    # Extensions for generated/non-source files that are text but shouldn't count
    GENERATED_EXTENSIONS = {
        ".map",  # Source maps
        ".d",  # Dependency files (make/Rust)
        ".timestamp",  # Build timestamps
        ".fingerprint",  # Build fingerprints
        ".sample",  # Sample/template files (e.g. git hooks)
        ".tfstate",  # Terraform state (generated)
        ".pen",  # Pencil design files (not source code)
        # CAD / EDA files (generated or tool-specific binary-like text)
        ".step",
        ".stp",  # 3D CAD models
        ".kicad_pcb",  # KiCad PCB layout
        ".kicad_sch",  # KiCad schematics
        ".kicad_mod",  # KiCad footprints
        ".kicad_sym",  # KiCad symbols
        ".kicad_pro",  # KiCad project
        ".net",  # Netlist files
        ".brd",  # Board layout files
        ".sch",  # Schematic files (Eagle etc.)
        ".gbr",
        ".drl",  # Gerber / drill files
        ".backup",  # Backup files
    }

    # Lock files are generated, not hand-written source
    LOCK_FILES = {
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "cargo.lock",
        "poetry.lock",
        "gemfile.lock",
        "composer.lock",
        "pipfile.lock",
        "bun.lockb",
        "shrinkwrap.json",
    }

    def is_binary_file(self, file_path: str) -> bool:
        """
        Check if a file is binary or a generated non-source file.

        Args:
            file_path: Path to the file to check

        Returns:
            True if the file is binary or generated, False otherwise
        """
        basename = os.path.basename(file_path)
        ext = os.path.splitext(file_path)[1].lower()

        # Quick check: known binary extensions
        if ext in self.BINARY_EXTENSIONS:
            return True

        # Quick check: generated non-source files
        if ext in self.GENERATED_EXTENSIONS:
            if self.debug:
                self.console.print(f"[yellow]Skipping generated file: {file_path}[/yellow]")
            return True

        # Quick check: lock files
        if basename.lower() in self.LOCK_FILES:
            if self.debug:
                self.console.print(f"[yellow]Skipping lock file: {file_path}[/yellow]")
            return True

        # Get excluded file patterns from config
        excluded_files = self.config_manager.get_excluded_files()

        # Check if the file matches any excluded pattern
        if excluded_files:
            import fnmatch

            for pattern in excluded_files:
                if fnmatch.fnmatch(basename, pattern):
                    return True

        # Check file size - large files are likely binary
        try:
            file_size = os.path.getsize(file_path)
            # Files larger than 10MB are likely binary
            if file_size > 10 * 1024 * 1024:  # 10MB
                if self.debug:
                    self.console.print(
                        f"[yellow]Skipping large file (likely binary): {file_path} ({file_size / (1024*1024):.2f} MB)[/yellow]"
                    )
                return True
        except OSError:
            pass

        # Try to detect binary content by reading a small sample. We also
        # use this sample to spot minified / generated text files so the
        # analyzer doesn't waste time crunching `bundle.min.js` or `*.map`.
        try:
            with open(file_path, "rb") as f:
                sample = f.read(8192)
                if b"\x00" in sample:
                    if self.debug:
                        self.console.print(
                            f"[yellow]Detected binary content in: {file_path}[/yellow]"
                        )
                    return True
                if self._looks_generated(sample, file_path):
                    return True
        except OSError:
            pass

        return False

    # Markers commonly emitted by code generators and lockfile-style tools.
    _GENERATED_MARKERS = (
        b"@generated",
        b"@generated\n",
        b"DO NOT EDIT",
        b"AUTOGENERATED",
        b"autogenerated",
        b"auto-generated",
        b"This file is automatically generated",
        b"Code generated by",
        b"// Generated by ",
    )

    # First bytes of a v3 sourcemap file. Don't bother peeking deeper.
    _SOURCEMAP_PREFIX = b'{"version":3'

    def _looks_generated(self, sample: bytes, file_path: str) -> bool:
        """Best-effort sniff: long-line minification, sourcemaps, `@generated` headers."""
        # Generator markers (case-sensitive, kept tight to avoid false matches in prose).
        for marker in self._GENERATED_MARKERS:
            if marker in sample:
                if self.debug:
                    self.console.print(
                        f"[yellow]Skipping generated file ({marker.decode('utf-8', 'replace').strip()}): {file_path}[/yellow]"
                    )
                return True
        # Sourcemap shape (most are >100kB single-line JSON).
        if sample.lstrip().startswith(self._SOURCEMAP_PREFIX):
            if self.debug:
                self.console.print(f"[yellow]Skipping sourcemap-shaped file: {file_path}[/yellow]")
            return True
        # Long-line heuristic: minified bundles often have a single line >5000
        # chars or an average line length above ~500 chars. Operating on the
        # 8 kB sample is enough to catch this without reading the whole file.
        newlines = sample.count(b"\n")
        if newlines == 0 and len(sample) >= 4096:
            # 4kB+ with no newline = almost certainly minified or a hash blob.
            if self.debug:
                self.console.print(
                    f"[yellow]Skipping single-line file (likely minified): {file_path}[/yellow]"
                )
            return True
        if newlines > 0:
            avg_line = len(sample) / (newlines + 1)
            if avg_line > 800:
                if self.debug:
                    self.console.print(
                        f"[yellow]Skipping file with avg line {avg_line:.0f} chars (likely minified): {file_path}[/yellow]"
                    )
                return True
        return False

    def should_analyze_file(self, file_path: str) -> bool:
        """
        Determine if a file should be analyzed.

        Args:
            file_path: Path to the file to check

        Returns:
            True if the file should be analyzed, False otherwise
        """
        # Skip binary files
        if self.is_binary_file(file_path):
            if self.debug:
                self.console.print(
                    f"[blue]Skipping binary file: {os.path.basename(file_path)}[/blue]"
                )
            return False

        # Check if file type is in excluded types
        language = self.analyzer_factory.get_language(file_path)
        if language in self.exclude_types:
            if self.debug:
                self.console.print(
                    f"[blue]Skipping excluded file type ({language}): {file_path}[/blue]"
                )
            return False

        # Check for large data files that should be excluded
        try:
            file_size = os.path.getsize(file_path)
        except OSError:
            return False
        basename = os.path.basename(file_path)

        # Generalised "this isn't source" size caps. Data-shaped extensions
        # (JSON / CSV / XML / SQL dump) hit a much lower ceiling than real
        # source. Hand-written code rarely exceeds 500kB in a single file.
        ext = os.path.splitext(basename)[1].lower()
        DATA_EXTS = {
            ".json",
            ".jsonl",
            ".ndjson",
            ".csv",
            ".tsv",
            ".xml",
            ".yaml",
            ".yml",
            ".geojson",
            ".sql",
            ".sarif",
        }
        if ext in DATA_EXTS and file_size > 1 * 1024 * 1024:
            if self.debug:
                self.console.print(
                    f"[yellow]Skipping large data file: {file_path} ({file_size / (1024*1024):.2f} MB)[/yellow]"
                )
            return False

        # Large text files (>500KB) with no extension are likely data files
        if "." not in basename and file_size > 500 * 1024:
            if self.debug:
                self.console.print(
                    f"[yellow]Skipping large text data file: {file_path} ({file_size / 1024:.2f} KB)[/yellow]"
                )
            return False

        # Anything over 2 MB that wasn't already a known data ext is suspicious.
        # Hand-written source over 2 MB exists but is rare enough that this
        # gives a much better signal-to-noise ratio for batch scans.
        if file_size > 2 * 1024 * 1024:
            if self.debug:
                self.console.print(
                    f"[yellow]Skipping very large text file: {file_path} ({file_size / (1024*1024):.2f} MB)[/yellow]"
                )
            return False

        return True

    def _relative_to_project_root(self, file_path: str) -> str:
        """Return file_path relative to the project root in POSIX style.
        Falls back to the absolute path when relativisation fails."""
        if self._project_root is None:
            return file_path
        try:
            return str(Path(file_path).relative_to(self._project_root).as_posix())
        except ValueError:
            return file_path

    def analyze_file(self, file_path: str) -> tuple[str, FileMetrics]:
        """Analyze a single file and return ``(language, metrics)``.

        Hits the per-file cache when `mtime + size` are unchanged so a
        re-scan of the same directory skips both the disk read and the regex
        passes for unchanged files.
        """
        if not self.should_analyze_file(file_path):
            return None, FileMetrics()

        # Stat first so we have a cache key even for tiny files. If stat fails,
        # there's nothing to analyze anyway.
        try:
            stat = os.stat(file_path)
        except (FileNotFoundError, PermissionError, OSError):
            return None, FileMetrics()

        # `mtime_ns` is filesystem-native nanosecond precision, much safer
        # than `mtime` seconds for fast successive edits.
        cache_key_mtime = int(stat.st_mtime_ns)
        cache_key_size = int(stat.st_size)

        cached = self.cache.get(file_path, cache_key_mtime, cache_key_size)
        if cached is not None:
            language, cached_metrics, cached_findings = cached
            if cached_findings:
                self.secret_findings.extend(cached_findings)
            return language, cached_metrics

        try:
            with open(file_path, encoding="utf-8", errors="replace") as f:
                content = f.read()

            line_count = len(content.splitlines())
            if self.max_lines > 0 and line_count > self.max_lines:
                if self.debug:
                    self.console.print(
                        f"[yellow]Skipping large file: {file_path} ({line_count} lines)[/yellow]"
                    )
                return None, FileMetrics()

            language = self.analyzer_factory.get_language(file_path)
            analyzer = self.analyzer_factory.get_analyzer(file_path)
            file_metrics = analyzer.analyze_content(content, file_path)

            if self.debug and file_metrics.total_lines > 1000:
                self.console.print(f"[yellow]Large file detected: {file_path}[/yellow]")
                self.console.print(f"  - Total lines: {file_metrics.total_lines}")
                self.console.print(f"  - Code lines: {file_metrics.code_lines}")
                self.console.print(f"  - Comment lines: {file_metrics.comment_lines}")
                self.console.print(f"  - Blank lines: {file_metrics.blank_lines}")
                self.console.print(f"  - File size: {cache_key_size / 1024:.1f} KB")

            # Scan for secrets while we have the content in memory.
            file_findings: list[dict] = []
            if self._secret_scanner is not None and self._project_root is not None:
                rel = self._relative_to_project_root(file_path)
                if not self._secret_scanner.should_skip_path(rel):
                    matches = self._secret_scanner.scan_file(rel, content)
                    file_findings = [
                        {
                            "file": m.file,
                            "line": m.line,
                            "kind": m.kind,
                            "snippet_hash": m.snippet_hash,
                            "severity": m.severity,
                        }
                        for m in matches
                    ]
                    self.secret_findings.extend(file_findings)

            self.cache.put(
                file_path,
                cache_key_mtime,
                cache_key_size,
                language,
                file_metrics,
                secret_findings=file_findings,
            )
            return language, file_metrics

        except (FileNotFoundError, PermissionError):
            return None, FileMetrics()

        except Exception as e:
            if self.debug:
                self.console.print(f"[red]Error analyzing file {file_path}: {str(e)}[/red]")
            return None, FileMetrics()
