"""Tests for web.backend.security.settings — env-var parsing + cache behaviour."""

from web.backend.security import settings


def test_token_unset_returns_none(security_env):
    security_env()  # clears METTLE_TOKEN
    assert settings.token() is None


def test_token_whitespace_returns_none(security_env):
    security_env(TOKEN="   ")
    assert settings.token() is None


def test_token_set_returns_value(security_env):
    security_env(TOKEN="abc123")
    assert settings.token() == "abc123"


def test_cors_origins_default_when_unset(security_env):
    security_env()
    assert settings.cors_origins() == list(settings.DEFAULT_CORS_ORIGINS)


def test_cors_origins_custom_list(security_env):
    security_env(CORS_ORIGINS="https://a.example.com, https://b.example.com")
    assert settings.cors_origins() == ["https://a.example.com", "https://b.example.com"]


def test_scan_roots_unset_returns_none(security_env, tmp_path):
    security_env()
    assert settings.scan_roots() is None


def test_scan_roots_parses_list(security_env, tmp_path):
    root_a = tmp_path / "a"
    root_a.mkdir()
    root_b = tmp_path / "b"
    root_b.mkdir()
    security_env(SCAN_ROOTS=f"{root_a},{root_b}")
    parsed = settings.scan_roots()
    assert parsed is not None
    assert root_a.resolve() in parsed
    assert root_b.resolve() in parsed


def test_is_debug_truthy_values(security_env):
    for v in ("1", "true", "yes", "TRUE", "Yes"):
        security_env(DEBUG=v)
        assert settings.is_debug(), f"{v!r} should be truthy"
    for v in ("", "0", "false", "no"):
        security_env(DEBUG=v)
        assert not settings.is_debug(), f"{v!r} should be falsy"
