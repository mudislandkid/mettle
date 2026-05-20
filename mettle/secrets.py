"""Regex-based secret scanner.

Stateless per-file scan with conservative FP policy. Skips test/fixture/doc/
vendored paths, files >1 MB, and binary files. Never stores the matched
substring — only its SHA-256 prefix, the file path, the line number, and a
named match kind.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import PurePosixPath

MAX_FILE_SIZE_BYTES = 1_048_576  # 1 MB

SKIP_DIR_NAMES = frozenset(
    {
        "node_modules",
        ".venv",
        "venv",
        "__pycache__",
        ".git",
        "dist",
        "build",
        ".next",
        ".nuxt",
        "target",
        ".cache",
        "coverage",
        ".mypy_cache",
        ".pytest_cache",
        ".tox",
        "vendor",
        "bower_components",
    }
)

SKIP_PATH_SUBSTRINGS = (
    "/tests/",
    "/test/",
    "/__tests__/",
    "/fixtures/",
    "/fixture/",
    "/examples/",
    "/example/",
    "/docs/",
    "/doc/",
    "/samples/",
    "/sample/",
)

SKIP_FILENAME_PATTERNS = (
    re.compile(r"\.test\."),  # foo.test.js
    re.compile(r"\.spec\."),  # foo.spec.ts
    re.compile(r"_test\."),  # foo_test.go
    re.compile(r"^test_"),  # test_foo.py
)

SECRET_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    ("aws_access_key_id", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "high"),
    (
        "aws_secret_access_key",
        re.compile(r"(?i)aws_secret_access_key\s*[:=]\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?"),
        "high",
    ),
    ("github_pat_classic", re.compile(r"\bghp_[A-Za-z0-9]{36}\b"), "high"),
    ("github_pat_fine", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{82}\b"), "high"),
    ("openai_api_key", re.compile(r"\bsk-[A-Za-z0-9]{48}\b"), "high"),
    ("anthropic_api_key", re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{32,}\b"), "high"),
    (
        "jwt",
        re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b"),
        "medium",
    ),
    (
        "rsa_private_key",
        re.compile(r"-----BEGIN (?:RSA |DSA |EC |OPENSSH |PGP )?PRIVATE KEY-----"),
        "high",
    ),
    (
        "generic_high_entropy",
        re.compile(
            r"(?i)\b(?:password|passwd|secret|token|api[_-]?key)\b"
            r"\s*[:=]\s*['\"]([A-Za-z0-9/+=_\-]{20,})['\"]"
        ),
        "medium",
    ),
]


@dataclass(frozen=True)
class SecretMatch:
    file: str  # relative to project root, POSIX-style
    line: int  # 1-indexed
    kind: str
    snippet_hash: str  # sha256(match.group(0))[:16]
    severity: str  # "high" | "medium"


class SecretScanner:
    """Stateless. Use `scan_file(rel_path, content)` per file.

    Callers handle the directory-walk + path-skip + file open. This class
    just runs the regex pack against a string and returns match objects.
    """

    def should_skip_path(self, rel_path: str) -> bool:
        """True if this file should NOT be scanned (test/fixture/doc/vendored)."""
        parts = PurePosixPath(rel_path).parts
        if any(p in SKIP_DIR_NAMES for p in parts):
            return True
        wrapped = "/" + str(PurePosixPath(rel_path)) + "/"
        if any(s in wrapped for s in SKIP_PATH_SUBSTRINGS):
            return True
        name = PurePosixPath(rel_path).name
        if any(p.search(name) for p in SKIP_FILENAME_PATTERNS):
            return True
        return False

    def scan_file(self, rel_path: str, content: str) -> list[SecretMatch]:
        """Run the regex pack against `content`. Applies file-level guards
        (binary sniff, size cap) before iterating patterns."""
        # Binary sniff on first 8KB (encoded back to bytes)
        sample = content[:8192].encode("utf-8", errors="surrogateescape")
        if b"\x00" in sample:
            return []
        encoded_len = len(content.encode("utf-8", errors="surrogateescape"))
        if encoded_len > MAX_FILE_SIZE_BYTES:
            return []

        results: list[SecretMatch] = []
        for kind, pattern, severity in SECRET_PATTERNS:
            for m in pattern.finditer(content):
                line = content.count("\n", 0, m.start()) + 1
                matched = m.group(0)
                h = hashlib.sha256(matched.encode("utf-8")).hexdigest()[:16]
                results.append(
                    SecretMatch(
                        file=rel_path,
                        line=line,
                        kind=kind,
                        snippet_hash=h,
                        severity=severity,
                    )
                )
        return results


def scan_secrets_in_text(content: str, rel_path: str) -> list[SecretMatch]:
    """Convenience wrapper for ad-hoc / test use. Applies the path-skip
    check; production code uses `SecretScanner` directly so the path-skip
    decision can prune file opens at the walk layer.
    """
    scanner = SecretScanner()
    if scanner.should_skip_path(rel_path):
        return []
    return scanner.scan_file(rel_path, content)
