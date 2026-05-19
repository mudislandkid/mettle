"""
Analyzer Factory Module

This module provides the AnalyzerFactory class which is responsible for:
1. Registering and managing language-specific analyzers
2. Determining the appropriate analyzer for a given file
3. Mapping file extensions to programming languages

The factory uses a cache file (.analyzer_cache.json) to store registered analyzers
between runs, improving performance by avoiding the need to rediscover analyzers each time.
"""

import os
import json
import importlib
import inspect
import logging
from pathlib import Path
from typing import Dict, Set, Type
from .base import BaseAnalyzer
from .javascript import JavaScriptAnalyzer
from .python import PythonAnalyzer
from .python_ast import PythonAstAnalyzer
from .html_css import HTMLCSSAnalyzer
from .c_style import CStyleAnalyzer, ShellAnalyzer, ObjectiveCAnalyzer

ENTRY_POINT_GROUP = "code_counter.analyzers"
_log = logging.getLogger(__name__)


def _user_cache_path() -> Path:
    """Return a per-user cache file location that won't try to mutate the
    installed package directory."""
    base = os.environ.get('XDG_CACHE_HOME') or os.path.expanduser('~/.cache')
    cache_dir = Path(base) / 'code_counter'
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        # Fall back to the platform's tmp dir if ~/.cache is unwritable.
        import tempfile
        cache_dir = Path(tempfile.gettempdir()) / 'code_counter'
        cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / 'analyzer_cache.json'

class AnalyzerFactory:
    """
    Factory class for creating and managing language-specific analyzers.
    
    This class is responsible for:
    - Mapping file extensions to programming languages
    - Determining the appropriate analyzer for a given file
    - Registering new analyzers dynamically
    - Caching analyzer registrations for performance
    
    The .analyzer_cache.json file is used to store registered analyzers between runs.
    This improves performance by avoiding the need to rediscover analyzers each time.
    """
    def __init__(self):
        self.file_extensions: Dict[str, Set[str]] = {
            'Python': {'.py', '.pyw', '.pyx', '.pyi'},
            'JavaScript': {'.js', '.jsx', '.mjs', '.cjs'},
            'TypeScript': {'.ts', '.tsx'},
            'HTML': {'.html', '.htm', '.xhtml', '.jinja', '.jinja2', '.j2'},
            'CSS': {'.css', '.scss', '.sass', '.less', '.postcss'},
            'JSON': {'.json', '.jsonc', '.json5', '.geojson'},
            'YAML': {'.yml', '.yaml'},
            'Markdown': {'.md', '.markdown', '.mdown', '.mkd'},
            'SQL': {'.sql', '.psql', '.plsql'},
            'Shell': {'.sh', '.bash', '.zsh', '.fish'},
            'Docker': {'Dockerfile', '.dockerfile', '.containerfile'},
            'XML': {'.xml', '.xsl', '.xslt', '.wsdl', '.xlf'},
            'Config': {'.ini', '.cfg', '.conf', '.config', '.properties', '.env', '.toml'},
            'Ruby': {'.rb', '.erb', '.rake'},
            'Java': {'.java', '.jsp', '.jspx'},
            'C/C++': {'.c', '.cpp', '.cc', '.cxx', '.h', '.hpp', '.hxx', '.ino'},
            'Go': {'.go'},
            'Rust': {'.rs'},
            'PHP': {'.php', '.phtml', '.php3', '.php4', '.php5'},
            'Swift': {'.swift'},
            'Objective-C': {'.m', '.mm'},
            'Kotlin': {'.kt', '.kts'},
            'GraphQL': {'.graphql', '.gql'},
            'Protocol Buffers': {'.proto'},
            'Vue': {'.vue'},
            'Terraform': {'.tf', '.tfvars'},
            'Documentation': {'.rst', '.rdoc', '.adoc', '.asciidoc', '.tex'},
            'Data': {'.csv', '.tsv'},
            'Mako': {'.mako'},
        }
        
        self.analyzers: Dict[str, Type[BaseAnalyzer]] = {
            'Python': PythonAstAnalyzer,
            'JavaScript': JavaScriptAnalyzer,
            'TypeScript': JavaScriptAnalyzer,
            'HTML': HTMLCSSAnalyzer,
            'CSS': HTMLCSSAnalyzer,
            'Vue': HTMLCSSAnalyzer,
            # C-style comment languages (// and /* */)
            'Rust': CStyleAnalyzer,
            'Go': CStyleAnalyzer,
            'C/C++': CStyleAnalyzer,
            'Java': CStyleAnalyzer,
            'Swift': CStyleAnalyzer,
            'Objective-C': ObjectiveCAnalyzer,
            'Kotlin': CStyleAnalyzer,
            'Terraform': CStyleAnalyzer,
            'PHP': CStyleAnalyzer,
            # Hash-comment languages
            'Shell': ShellAnalyzer,
            'YAML': ShellAnalyzer,
            'Config': ShellAnalyzer,
        }
        
        # Cache file lives under the user's cache dir, NOT inside the installed
        # package (which may be read-only on pip / Docker installs).
        self._cache_file = _user_cache_path()
        self._analyzer_instances: Dict[str, BaseAnalyzer] = {}
        # Track which languages are owned by entry-point plugins so they
        # always win over auto-discovery / cache and aren't persisted as
        # opaque module paths (we re-resolve via entry points each run).
        self._entry_point_languages: Set[str] = set()
        self._load_cached_registrations()
        self._discover_analyzers()
        self._discover_entry_point_plugins()
    
    def _load_cached_registrations(self):
        """Load previously registered analyzers from cache."""
        if not self._cache_file.exists():
            return
            
        try:
            with open(self._cache_file, 'r') as f:
                cached_data = json.load(f)
                
            for language, data in cached_data.items():
                # Try to import the analyzer module
                try:
                    module = importlib.import_module(data['module'])
                    analyzer_class = getattr(module, data['class_name'])
                    extensions = set(data['extensions'])
                    
                    # Only register if it's a valid analyzer
                    if (inspect.isclass(analyzer_class) and 
                        issubclass(analyzer_class, BaseAnalyzer) and 
                        analyzer_class != BaseAnalyzer):
                        self.file_extensions[language] = extensions
                        self.analyzers[language] = analyzer_class
                except (ImportError, AttributeError):
                    continue
        except (json.JSONDecodeError, IOError):
            pass
    
    def _save_registrations(self):
        """Save current analyzer registrations to cache."""
        cache_data = {}

        for language, analyzer_class in self.analyzers.items():
            # Only cache custom analyzers (not built-in ones). Entry-point
            # plugins are also skipped — they're re-resolved on each run via
            # `importlib.metadata.entry_points()` and shouldn't get pinned
            # to a stale module path in the cache.
            if language in self._entry_point_languages:
                continue
            if analyzer_class not in [PythonAnalyzer, PythonAstAnalyzer, JavaScriptAnalyzer, HTMLCSSAnalyzer, CStyleAnalyzer, ShellAnalyzer, ObjectiveCAnalyzer]:
                cache_data[language] = {
                    'module': analyzer_class.__module__,
                    'class_name': analyzer_class.__name__,
                    'extensions': list(self.file_extensions.get(language, set()))
                }
        
        try:
            with open(self._cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
        except IOError:
            pass
    
    def _discover_analyzers(self):
        """Auto-discover analyzer classes in the analyzers directory."""
        analyzers_dir = Path(__file__).parent
        
        for file_path in analyzers_dir.glob('*.py'):
            # Skip built-in files and non-python files
            if file_path.stem in ['__init__', 'base', 'factory', 'template_analyzer',
                                  'c_style', 'cache', 'test_detection', 'python_ast']:
                continue
                
            try:
                # Import the module
                module_name = f".{file_path.stem}"
                module = importlib.import_module(module_name, package="code_counter.analyzers")
                
                # Look for analyzer classes
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (issubclass(obj, BaseAnalyzer) and 
                        obj != BaseAnalyzer and 
                        obj not in self.analyzers.values()):
                        
                        # Extract language name from class name
                        language = name.replace('Analyzer', '')
                        
                        # Register if not already registered
                        if language not in self.analyzers:
                            self.register_analyzer(language, obj, [])
            except ImportError:
                continue
        
        # Save any newly discovered analyzers
        self._save_registrations()
    
    def _discover_entry_point_plugins(self) -> None:
        """Load third-party analyzers registered via the `code_counter.analyzers` entry point.

        Plugins declare themselves in their own pyproject.toml::

            [project.entry-points."code_counter.analyzers"]
            cobol = "my_pkg.cobol:CobolAnalyzer"

        Each entry point must resolve to a `BaseAnalyzer` subclass that exposes
        `LANGUAGE: str` and `EXTENSIONS: Iterable[str]` class attributes.
        Plugins always override built-in / cached registrations for the same
        language so users can swap in a stricter analyzer for a language we
        already cover. Failures (import errors, missing metadata, wrong base
        class) are logged and skipped — one broken plugin must not break the
        whole tool.
        """
        try:
            from importlib.metadata import entry_points
        except ImportError:  # pragma: no cover — stdlib since 3.8
            return

        # The keyword API (`group=...`) is the canonical form from Python 3.10
        # onwards (3.10+ is our minimum per pyproject.toml).
        try:
            eps = entry_points(group=ENTRY_POINT_GROUP)
        except TypeError:
            # Some older selectable-entry-points backports return a dict.
            eps = entry_points().get(ENTRY_POINT_GROUP, [])  # type: ignore[union-attr]

        for ep in eps:
            try:
                obj = ep.load()
            except Exception as exc:
                _log.warning("code_counter analyzer plugin %r failed to load: %s", ep.name, exc)
                continue

            if not (inspect.isclass(obj) and issubclass(obj, BaseAnalyzer) and obj is not BaseAnalyzer):
                _log.warning(
                    "code_counter analyzer plugin %r resolved to %r which isn't a BaseAnalyzer subclass; skipping.",
                    ep.name, obj,
                )
                continue

            language = getattr(obj, 'LANGUAGE', None) or ep.name
            extensions = getattr(obj, 'EXTENSIONS', None)
            if not extensions:
                _log.warning(
                    "code_counter analyzer plugin %r (language %r) declares no EXTENSIONS; skipping.",
                    ep.name, language,
                )
                continue

            # Normalise: every entry starts with a dot, lowercased — matches
            # how `get_language()` looks them up.
            ext_set: Set[str] = set()
            for raw in extensions:
                e = str(raw).strip().lower()
                if e and not e.startswith('.'):
                    e = '.' + e
                if e:
                    ext_set.add(e)

            self.file_extensions[language] = ext_set
            self.analyzers[language] = obj
            self._entry_point_languages.add(language)
            # Clear any pre-instantiated cached instance for this language so
            # the new class actually gets used.
            self._analyzer_instances.pop(language, None)

    def register_analyzer(self, language: str, analyzer_class: type, file_extensions: list[str]) -> None:
        """Register a new language analyzer.
        
        Args:
            language: Name of the language
            analyzer_class: The analyzer class to use
            file_extensions: List of file extensions for this language
        """
        if not isinstance(file_extensions, set):
            file_extensions = set(file_extensions)
            
        self.file_extensions[language] = file_extensions
        self.analyzers[language] = analyzer_class
        self._save_registrations()
    
    def get_language(self, file_path: str) -> str:
        """Determine the programming language based on file extension."""
        # Get the basename and extension
        basename = os.path.basename(file_path)
        
        # Special case for Dockerfile
        if basename.lower() == 'dockerfile' or basename.lower().endswith('.dockerfile'):
            return 'Docker'
            
        # TypeScript declaration files must be checked BEFORE the .json blanket
        # so `foo.d.ts.json` corner cases don't confuse the order.
        if basename.lower().endswith('.d.ts'):
            return 'TypeScript'

        # Special case for package.json, tsconfig.json, etc.
        if basename.lower().endswith('.json'):
            return 'JSON'

        # Special case for .gitignore, .npmignore, etc.
        if basename.startswith('.') and '.' not in basename[1:]:
            return 'Config'

        # Get the extension
        ext = os.path.splitext(file_path.lower())[1]
        if not ext and '.' in basename:
            # Handle files like .gitignore
            ext = f'.{basename.split(".", 1)[1]}'
            
        if not ext:
            # Try to detect by filename
            lower_basename = basename.lower()
            if lower_basename in {'makefile', 'gnumakefile', 'vagrantfile', 'jenkinsfile', 'rakefile', 'procfile'}:
                return 'Config'
            if lower_basename in {'dockerfile'}:
                return 'Docker'
            return 'Other'
            
        # Check against known extensions
        for language, extensions in self.file_extensions.items():
            if ext in extensions or basename in extensions:
                return language
                
        # Additional checks for common data files
        if ext in {'.csv', '.tsv', '.dat', '.db', '.sqlite', '.sqlite3'}:
            return 'Data'

        # Additional checks for binary files
        if ext in {'.bin', '.exe', '.dll', '.so', '.dylib', '.class', '.jar',
                  '.war', '.ear', '.o', '.obj', '.a', '.lib', '.elf',
                  '.rmeta', '.rlib', '.pyd',
                  '.zip', '.tar', '.gz', '.bz2', '.xz', '.7z', '.rar', '.iso',
                  '.tgz', '.zst', '.lz4',
                  '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.svg',
                  '.webp', '.tiff', '.tif', '.psd',
                  '.mp3', '.mp4', '.wav', '.avi', '.mov', '.flv', '.mkv',
                  '.webm', '.ogg', '.flac', '.aac', '.m4a',
                  '.ttf', '.woff', '.woff2', '.eot', '.otf',
                  '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                  '.pyc', '.pyo'}:
            return 'Binary'

        # Generated / non-source files
        if ext in {'.map', '.d', '.timestamp', '.fingerprint', '.sample',
                  '.tfstate', '.pen', '.backup'}:
            return 'Generated'

        # CAD / EDA files (tool-generated, not hand-written source)
        if ext in {'.step', '.stp', '.kicad_pcb', '.kicad_sch', '.kicad_mod',
                  '.kicad_sym', '.kicad_pro', '.net', '.brd', '.sch',
                  '.gbr', '.drl'}:
            return 'Generated'

        return 'Other'
    
    def get_analyzer(self, file_path: str) -> BaseAnalyzer:
        """Get the appropriate analyzer for a given file (cached by language)."""
        language = self.get_language(file_path)
        instance = self._analyzer_instances.get(language)
        if instance is None:
            analyzer_class = self.analyzers.get(language, BaseAnalyzer)
            instance = analyzer_class()
            self._analyzer_instances[language] = instance
        return instance
