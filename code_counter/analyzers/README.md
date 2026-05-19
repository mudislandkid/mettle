# Adding New Language Analyzers

This directory contains all per-language analyzers. New analyzers are
auto-discovered at startup — drop a file in here that defines a class ending in
`Analyzer` and inherits from `BaseAnalyzer`, and the factory will register it on
the next run.

## Quick Start

1. Copy `template_analyzer.py` (or `python.py` for a simpler example) to a new
   file: `your_language.py`.
2. Rename the class to `YourLanguageAnalyzer` (the trailing `Analyzer` matters —
   the factory uses it to derive the language name).
3. Define the language-specific patterns and `analyze_content()` method.
4. (Optional) Add an entry to `factory.py`'s `file_extensions` map if your
   extensions don't already match.
5. (Optional) Add a default-config block under `code_counter/config.yaml`.

The first time the tool runs after you add the file, the discovery code reads
the module, finds the new `Analyzer` subclass, and writes its registration into
`~/.cache/code_counter/analyzer_cache.json` for next time.

## Shared helpers (use these)

Every analyzer should use the helpers in `base.py` instead of rolling its own
line accounting:

- **`classify_lines(content, line_comment_re=None, block_comment_re=None)`**
  Returns `(blank, comment, code)` for the source. **Guarantees**
  `blank + comment + code == total_lines`, so you can never produce a
  negative `code_lines`. Lines that mix code + trailing comment are counted
  as code (the conventional LOC convention).

- **`mask_string_literals(content)`**
  Replaces the contents of `"..."`, `'...'`, and backtick strings with spaces
  while preserving line breaks. Use this before any regex that hunts for
  `//`, `#`, `/* */`, etc., so comment markers inside strings don't get
  miscounted.

Both helpers are how the rewrite stopped the entire family of bugs around
"`//` inside `https://...` was counted as a comment" and "`if (x) {}` was
counted as a function definition".

## A minimal example

A real working analyzer is rarely longer than this:

```python
import re
from .base import BaseAnalyzer, classify_lines, mask_string_literals
from ..metrics.file_metrics import FileMetrics


class RubyAnalyzer(BaseAnalyzer):
    # Compile patterns at class load, NOT in __init__ — they're shared and
    # immutable, and AnalyzerFactory caches a single instance per language.
    SINGLE_COMMENT = re.compile(r'#')
    FUNCTION_PATTERN = re.compile(r'^\s*def\s+\w+', re.MULTILINE)
    CLASS_PATTERN = re.compile(r'^\s*class\s+\w+\b', re.MULTILINE)
    IMPORT_PATTERN = re.compile(r'^\s*(?:require|require_relative|load)\s+', re.MULTILINE)

    def _strip_for_pattern_scan(self, content: str) -> str:
        masked = mask_string_literals(content)
        return re.sub(r'#[^\n]*', '', masked)

    def analyze_content(self, content: str, file_path: str = '') -> FileMetrics:
        metrics = super().analyze_content(content, file_path)

        blank, comment, code = classify_lines(content, self.SINGLE_COMMENT, None)
        metrics.blank_lines = blank
        metrics.comment_lines = comment
        metrics.code_lines = code

        clean = self._strip_for_pattern_scan(content)
        metrics.functions = len(self.FUNCTION_PATTERN.findall(clean))
        metrics.classes = len(self.CLASS_PATTERN.findall(clean))
        metrics.imports = len(self.IMPORT_PATTERN.findall(clean))

        return metrics
```

## C-style languages

If your language uses `//` for single-line comments and `/* ... */` for block
comments (Rust, Go, C/C++, Java, Swift, Kotlin, Terraform, PHP, ...) you should
subclass `CStyleAnalyzer` from `c_style.py` instead of `BaseAnalyzer` — it
already implements the correct comment / string handling. Override the
`FUNCTION_PATTERN`, `CLASS_PATTERN`, `IMPORT_PATTERN` constants for your
language's syntax. See `c_style.ObjectiveCAnalyzer` for a working example.

## Auto-discovery rules

`AnalyzerFactory._discover_analyzers()` registers a class when:

- The file is a `.py` in `code_counter/analyzers/`.
- It's not one of the framework files (`__init__`, `base`, `factory`,
  `template_analyzer`, `c_style`).
- It defines a class that inherits from `BaseAnalyzer`, has a name ending in
  `Analyzer`, and isn't already registered.

The discovered language name is the class name with `Analyzer` stripped. The
file extensions default to whatever's in the factory's `file_extensions` map
for that language — add an entry there for new file types.

## Manual registration

For runtime registration (e.g. from a downstream script or test):

```python
from code_counter.analyzers.factory import AnalyzerFactory
from your_module import YourAnalyzer

factory = AnalyzerFactory()
factory.register_analyzer("Ruby", YourAnalyzer, [".rb", ".erb", ".rake"])
```

This also persists into the user-level cache file.

## Plug-in analyzers from third-party packages

You don't have to fork this repo to add a language. Ship a pip-installable
package that exposes a `BaseAnalyzer` subclass with `LANGUAGE` and `EXTENSIONS`
class attributes, then advertise it via the `code_counter.analyzers` entry
point group in your own `pyproject.toml`:

```toml
[project.entry-points."code_counter.analyzers"]
cobol = "my_pkg.cobol:CobolAnalyzer"
```

```python
# my_pkg/cobol.py
from code_counter.analyzers.base import BaseAnalyzer, classify_lines
from code_counter.metrics.file_metrics import FileMetrics


class CobolAnalyzer(BaseAnalyzer):
    LANGUAGE = "COBOL"
    EXTENSIONS = [".cob", ".cbl"]

    def analyze_content(self, content: str, file_path: str = "") -> FileMetrics:
        metrics = super().analyze_content(content, file_path)
        # ... fill in blank/comment/code lines etc.
        return metrics
```

`pip install my-pkg` and the next `code-counter` run discovers `CobolAnalyzer`
via `importlib.metadata.entry_points()` and routes `.cob`/`.cbl` files to it.

Rules:

- Entry-point plugins **override** built-in or cached registrations for the same
  language, so you can swap in a stricter Python analyzer or a domain-specific
  Markdown variant just by installing a package.
- Extensions are normalised (lower-cased, dot-prefixed). `["cob", ".CBL"]` and
  `[".cob", ".cbl"]` produce the same registration.
- A plugin that fails to import, isn't a `BaseAnalyzer` subclass, or declares no
  `EXTENSIONS` is logged at WARNING and skipped — one broken plugin will never
  bring the whole tool down.
- Entry-point analyzers are **not** persisted to the user cache. They're
  re-resolved on each run from installed package metadata, so uninstalling the
  package drops the registration cleanly.

## Adding language-specific metrics

Add an attribute to `code_counter/metrics/file_metrics.py`:

```python
@dataclass
class FileMetrics:
    # ... existing fields ...
    your_feature: int = 0
```

Then populate it in `analyze_content()`:

```python
def analyze_content(self, content: str, file_path: str = '') -> FileMetrics:
    metrics = super().analyze_content(content, file_path)
    # ... shared classification ...
    metrics.your_feature = len(self.YOUR_FEATURE_PATTERN.findall(content))
    return metrics
```

Reporters that don't know about the new field will simply ignore it.

## Best practices

- **Compile regexes once** at class scope. The factory caches one analyzer
  instance per language, so per-instance compilation in `__init__` is wasted
  work.
- **Never strip comments without masking strings first.** `mask_string_literals`
  is cheap and prevents `"https://..."`-style false positives.
- **Always assign `blank_lines + comment_lines + code_lines`** so the totals
  add up — the unit tests assert this invariant.
- **Avoid greedy regexes that span lines unless you actually want that.**
  Patterns like `\[.*for.*in.*\]` can hit catastrophic backtracking on
  minified code; bound them with character classes (e.g. `\[[^\[\]\n]{1,300}...`).
- **Use `re.MULTILINE` with `^` anchors** for top-level declarations rather
  than over-broad patterns that match anywhere.

## Common patterns

```python
# Functions
r'^\s*def\s+\w+'                       # Python / Ruby
r'\bfunction\s+\w+'                    # JavaScript
r'\bfn\s+\w+'                          # Rust
r'\bfunc\s+\w+'                        # Go / Swift

# Classes
r'^\s*class\s+\w+\b'                   # Python / Java / many
r'\b(?:struct|enum|trait|impl)\s+\w+'  # Rust
r'@(?:interface|implementation)\s+\w+' # Objective-C

# Imports
r'^\s*(?:import|from)\s+'              # Python
r'\brequire\s*\('                      # JS / Node
r'^\s*use\s+\w+'                       # Rust
r'^\s*#include\s+'                     # C / C++
```

## Testing

`code_counter/tests/test_analyzers.py` includes a `LineSumInvariant` test
class — add a one-liner there for your language so the
`blank + comment + code == total` property is enforced for it too.
