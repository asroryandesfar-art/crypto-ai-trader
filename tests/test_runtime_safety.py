"""Tests for runtime_safety utilities."""

import logging
import os
import pathlib
import tempfile

import pytest

from utils.runtime_safety import (
    SecretRedactionFilter,
    connect_sqlite,
    write_env_value,
    safe_bool_env,
)


# ── SecretRedactionFilter ─────────────────────────────────────────────────────

class _Record:
    def __init__(self, msg: str):
        self.msg = msg
        self.args = ()

    def getMessage(self) -> str:
        return self.msg


def test_redacts_known_secret():
    filt = SecretRedactionFilter(secrets=["supersecret12345"])
    r = _Record("key=supersecret12345 was sent")
    filt.filter(r)
    assert "supersecret12345" not in r.msg
    assert "[REDACTED]" in r.msg


def test_redacts_bearer_token():
    filt = SecretRedactionFilter()
    r = _Record("Authorization: Bearer abc.def.ghi1234")
    filt.filter(r)
    assert "abc.def.ghi1234" not in r.msg


def test_ignores_short_secrets():
    filt = SecretRedactionFilter(secrets=["short"])
    r = _Record("short is not redacted")
    filt.filter(r)
    assert r.msg == "short is not redacted"


def test_multiple_secrets_all_redacted():
    filt = SecretRedactionFilter(secrets=["secret_alpha_1234", "secret_beta_5678"])
    r = _Record("a=secret_alpha_1234 b=secret_beta_5678")
    filt.filter(r)
    assert "secret_alpha_1234" not in r.msg
    assert "secret_beta_5678" not in r.msg


def test_empty_secret_not_redacted():
    filt = SecretRedactionFilter(secrets=[""])
    r = _Record("nothing special here")
    filt.filter(r)
    assert r.msg == "nothing special here"


def test_filter_always_returns_true():
    filt = SecretRedactionFilter()
    r = _Record("any message")
    assert filt.filter(r) is True


# ── connect_sqlite ────────────────────────────────────────────────────────────

def test_connect_sqlite_creates_connection():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = pathlib.Path(tmpdir) / "test.db"
        conn = connect_sqlite(db_path)
        row = conn.execute("SELECT 1").fetchone()
        assert row[0] == 1
        conn.close()


def test_connect_sqlite_wal_mode():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = pathlib.Path(tmpdir) / "test.db"
        conn = connect_sqlite(db_path)
        journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert journal_mode == "wal"
        conn.close()


def test_connect_sqlite_foreign_keys_on():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = pathlib.Path(tmpdir) / "test.db"
        conn = connect_sqlite(db_path)
        fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        assert fk == 1
        conn.close()


# ── write_env_value ───────────────────────────────────────────────────────────

def test_write_env_value_updates_existing_key():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as tmp:
        tmp.write("AI_PROVIDER=qvac\nFOO=bar\n")
        path = pathlib.Path(tmp.name)
    try:
        write_env_value(path, "AI_PROVIDER", "groq")
        content = path.read_text()
        assert "AI_PROVIDER=groq" in content
        assert "qvac" not in content
        assert "FOO=bar" in content
    finally:
        path.unlink()


def test_write_env_value_appends_new_key():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as tmp:
        tmp.write("FOO=bar\n")
        path = pathlib.Path(tmp.name)
    try:
        write_env_value(path, "NEW_KEY", "new_value")
        content = path.read_text()
        assert "NEW_KEY=new_value" in content
        assert "FOO=bar" in content
    finally:
        path.unlink()


def test_write_env_value_creates_file_when_missing():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = pathlib.Path(tmpdir) / "new.env"
        write_env_value(path, "HELLO", "world")
        assert "HELLO=world" in path.read_text()


def test_write_env_value_rejects_invalid_key():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as tmp:
        path = pathlib.Path(tmp.name)
    try:
        with pytest.raises(ValueError, match="Invalid env key"):
            write_env_value(path, "bad key!", "value")
    finally:
        path.unlink()


def test_write_env_value_rejects_lowercase_key():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as tmp:
        path = pathlib.Path(tmp.name)
    try:
        with pytest.raises(ValueError):
            write_env_value(path, "lowercase", "value")
    finally:
        path.unlink()


# ── safe_bool_env ─────────────────────────────────────────────────────────────

def test_safe_bool_env_true_variants(monkeypatch):
    for val in ("1", "true", "True", "TRUE", "yes", "Yes", "on", "ON"):
        monkeypatch.setenv("_TEST_BOOL", val)
        assert safe_bool_env("_TEST_BOOL") is True


def test_safe_bool_env_false_variants(monkeypatch):
    for val in ("0", "false", "False", "no", "off", "OFF"):
        monkeypatch.setenv("_TEST_BOOL", val)
        assert safe_bool_env("_TEST_BOOL") is False


def test_safe_bool_env_missing_uses_default(monkeypatch):
    monkeypatch.delenv("_TEST_BOOL_MISSING", raising=False)
    assert safe_bool_env("_TEST_BOOL_MISSING", default=True) is True
    assert safe_bool_env("_TEST_BOOL_MISSING", default=False) is False
