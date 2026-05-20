"""Tests for mettle.secrets — regex pack, path-skip policy, file-level guards."""

from mettle.secrets import (
    MAX_FILE_SIZE_BYTES,
    SECRET_PATTERNS,
    SecretScanner,
    scan_secrets_in_text,
)

# ---------------- regex pack positive cases (9 tests) ----------------


def test_detects_aws_access_key_id():
    matches = scan_secrets_in_text("config = {'key': 'AKIAIOSFODNN7EXAMPLE'}", "src/conf.py")
    assert len(matches) == 1
    assert matches[0].kind == "aws_access_key_id"
    assert matches[0].severity == "high"


def test_detects_aws_secret_access_key():
    text = 'aws_secret_access_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"'
    matches = scan_secrets_in_text(text, "src/conf.py")
    assert any(m.kind == "aws_secret_access_key" for m in matches)


def test_detects_github_pat_classic():
    matches = scan_secrets_in_text("ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789", "src/x.py")
    assert any(m.kind == "github_pat_classic" for m in matches)


def test_detects_github_pat_fine_grained():
    tok = "github_pat_" + "A" * 82
    matches = scan_secrets_in_text(tok, "src/x.py")
    assert any(m.kind == "github_pat_fine" for m in matches)


def test_detects_openai_key():
    matches = scan_secrets_in_text("sk-" + "a" * 48, "src/x.py")
    assert any(m.kind == "openai_api_key" for m in matches)


def test_detects_anthropic_key():
    matches = scan_secrets_in_text("sk-ant-" + "A" * 50, "src/x.py")
    assert any(m.kind == "anthropic_api_key" for m in matches)


def test_detects_jwt():
    jwt = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        ".eyJzdWIiOiIxMjM0NTY3ODkwIn0"
        ".SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    )
    matches = scan_secrets_in_text(jwt, "src/x.py")
    assert any(m.kind == "jwt" for m in matches)


def test_detects_rsa_private_key():
    matches = scan_secrets_in_text("-----BEGIN RSA PRIVATE KEY-----", "src/x.pem")
    assert any(m.kind == "rsa_private_key" for m in matches)


def test_detects_generic_high_entropy():
    matches = scan_secrets_in_text('password = "X9aB2cD4eF6gH8iJ0kL1mN3oP5"', "src/conf.py")
    assert any(m.kind == "generic_high_entropy" for m in matches)


# ---------------- path-skip negative cases (7 tests) ----------------


def test_skips_test_directory():
    scanner = SecretScanner()
    assert scanner.should_skip_path("src/tests/fixtures.py") is True
    assert scanner.should_skip_path("src/__tests__/auth.spec.js") is True


def test_skips_fixture_directory():
    scanner = SecretScanner()
    assert scanner.should_skip_path("fixtures/example_keys.txt") is True


def test_skips_examples_directory():
    scanner = SecretScanner()
    assert scanner.should_skip_path("examples/aws-demo/keys.txt") is True


def test_skips_docs_directory():
    scanner = SecretScanner()
    assert scanner.should_skip_path("docs/api-keys-howto.md") is True


def test_does_not_skip_production_path():
    scanner = SecretScanner()
    assert scanner.should_skip_path("src/auth/credentials.py") is False
    assert scanner.should_skip_path("backend/config.py") is False


def test_skips_node_modules_directory():
    scanner = SecretScanner()
    assert scanner.should_skip_path("node_modules/whatever/dist/index.js") is True


def test_skips_filename_with_test_pattern():
    scanner = SecretScanner()
    assert scanner.should_skip_path("src/auth/test_credentials.py") is True
    assert scanner.should_skip_path("src/auth/credentials.test.js") is True
    assert scanner.should_skip_path("src/auth/credentials.spec.ts") is True


# ---------------- file-level guards (3 tests) ----------------


def test_skips_files_over_1mb():
    big = "x" * (MAX_FILE_SIZE_BYTES + 100)
    big += " AKIAIOSFODNN7EXAMPLE"
    matches = scan_secrets_in_text(big, "src/big.js")
    assert matches == []


def test_skips_binary_files_via_null_byte_sniff():
    binary = "\x00\x01\x02 AKIAIOSFODNN7EXAMPLE"
    matches = scan_secrets_in_text(binary, "src/blob.bin")
    assert matches == []


def test_snippet_hash_does_not_leak_secret():
    matches = scan_secrets_in_text("AKIAIOSFODNN7EXAMPLE", "src/x.py")
    assert len(matches) == 1
    assert "AKIA" not in matches[0].snippet_hash
    assert len(matches[0].snippet_hash) == 16


# ---------------- multi-match (1 test) ----------------


def test_multiple_matches_in_same_file():
    text = 'aws = "AKIAIOSFODNN7EXAMPLE"\n' 'gh = "ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789"\n'
    matches = scan_secrets_in_text(text, "src/x.py")
    kinds = {m.kind for m in matches}
    assert {"aws_access_key_id", "github_pat_classic"}.issubset(kinds)


# ---------------- regex pack sanity (1 test) ----------------


def test_regex_pack_has_expected_entries():
    """Ensure the named pattern set hasn't drifted from the spec."""
    expected = {
        "aws_access_key_id",
        "aws_secret_access_key",
        "github_pat_classic",
        "github_pat_fine",
        "openai_api_key",
        "anthropic_api_key",
        "jwt",
        "rsa_private_key",
        "generic_high_entropy",
    }
    actual = {name for name, _, _ in SECRET_PATTERNS}
    assert actual == expected
