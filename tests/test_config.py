"""Tests for ds_agent.config — typed settings loading."""

import pytest
from ds_agent.config import Settings, get_settings


def test_settings_loads_from_env(monkeypatch):
    """Given env vars are set, Settings() picks them up correctly."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-12345")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    monkeypatch.setenv("DUCKDB_PATH", "/tmp/test.duckdb")

    settings = Settings()

    assert settings.anthropic_api_key == "sk-ant-test-12345"
    assert settings.anthropic_model == "claude-sonnet-4-6"
    assert settings.duckdb_path == "/tmp/test.duckdb"


def test_settings_uses_defaults_when_env_missing(monkeypatch):
    """Given only ANTHROPIC_API_KEY set and the other two env vars unset, the defaults from the field declarations are used."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-12345")
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
    monkeypatch.delenv("DUCKDB_PATH", raising=False)

    settings = Settings(_env_file=None)  # _env_file=None disables .env auto-loading for this test

    assert settings.anthropic_api_key == "sk-ant-test-12345"
    assert settings.anthropic_model == "claude-sonnet-4-6"
    assert settings.duckdb_path == "./data/ds_agent.duckdb"


def test_settings_raises_when_api_key_missing(monkeypatch):
    """Given no ANTHROPIC_API_KEY in env, Settings(_env_file=None) must raise an exception."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(Exception):  # we'll narrow this once the implementation exists
        Settings(_env_file=None)  # _env_file=None disables .env auto-loading for this test


def test_get_settings_returns_singleton(monkeypatch):
    """Calling get_settings() twice returns the same object."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-12345")
    a = get_settings()
    b = get_settings()
    assert a is b