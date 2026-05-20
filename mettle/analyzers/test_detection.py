"""Heuristic detection of test files vs production files.

Lives in its own module so the detection logic doesn't pull in `rich` (or any
other runtime dependency) just to be unit-tested.
"""

import re


# Directory names that, when present anywhere in a file's path components,
# mark it as a test file. Lowercase for case-insensitive matching.
TEST_DIR_NAMES = frozenset({
    'test', 'tests', '__tests__', 'spec', 'specs',
    'cypress', 'e2e', 'integration_tests', 'unit_tests',
    'testing', 'test_data',
})

# Filename patterns that mark a single file as a test, independent of its
# parent directory. Matched against the basename (stripped of its outermost
# extension) so `latest.py` doesn't match while `test_foo.py` does.
_TEST_FILENAME_RE = re.compile(
    r'(?:^|[._-])(?:'
    r'test|tests|spec|specs|e2e'
    r')(?:[._-]|$)',
    re.IGNORECASE,
)

_DOT_SUFFIX_MARKERS = {'test', 'tests', 'spec', 'specs', 'e2e'}


def is_test_file(file_path: str) -> bool:
    """Return True if `file_path` looks like a test file.

    Recognises:
    - Files in any `test/`, `tests/`, `__tests__/`, `spec/`, `cypress/`,
      `e2e/`, ... ancestor directory.
    - Filenames containing `test`, `tests`, `spec`, `specs`, or `e2e` as a
      token (so `test_foo.py`, `foo_test.go`, `foo.spec.ts`, `foo.test.tsx`,
      `e2e_login.js` all match; `latest.py` and `manifesto.md` do not).
    """
    norm = file_path.replace('\\', '/')
    parts = norm.split('/')
    basename = parts[-1]

    for part in parts[:-1]:
        if part.lower() in TEST_DIR_NAMES:
            return True

    name_no_ext = basename.rsplit('.', 1)[0] if '.' in basename else basename
    if _TEST_FILENAME_RE.search(name_no_ext):
        return True

    # `.spec.ts` / `.test.tsx` style: the test marker is the second-to-last
    # segment of a multi-dot filename.
    segments = basename.lower().split('.')
    if len(segments) >= 3 and segments[-2] in _DOT_SUFFIX_MARKERS:
        return True

    return False
