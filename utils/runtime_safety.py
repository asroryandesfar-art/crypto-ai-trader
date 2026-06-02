"""Runtime safety helpers for secrets, SQLite, and .env kill switches."""

import logging
import os
import re
import sqlite3
from pathlib import Path
from typing import Iterable


class SecretRedactionFilter(logging.Filter):
    """Redact known API keys and bearer tokens before records hit any handler."""

    GENERIC_PATTERNS = (
        re.compile(r"Bearer\s+[A-Za-z0-9._\-]+"),
        re.compile(r"(api[_-]?key['\"]?\s*[:=]\s*['\"]?)[A-Za-z0-9._\-]{12,}", re.IGNORECASE),
        re.compile(r"(secret(?:[_-]?key)?['\"]?\s*[:=]\s*['\"]?)[A-Za-z0-9._\-]{12,}", re.IGNORECASE),
        re.compile(r"(token['\"]?\s*[:=]\s*['\"]?)[A-Za-z0-9._\-]{12,}", re.IGNORECASE),
    )

    def __init__(self, secrets: Iterable[str] = ()):
        super().__init__()
        self.secrets = tuple(secret for secret in secrets if secret and len(secret) >= 8)

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        for secret in self.secrets:
            message = message.replace(secret, "[REDACTED]")
        for pattern in self.GENERIC_PATTERNS:
            message = pattern.sub(lambda match: f"{match.group(1) if match.lastindex else 'Bearer '}[REDACTED]", message)
        record.msg = message
        record.args = ()
        return True


def install_secret_redaction(logger: logging.Logger, secrets: Iterable[str]) -> None:
    redaction_filter = SecretRedactionFilter(secrets)
    logger.addFilter(redaction_filter)
    for handler in logger.handlers:
        handler.addFilter(redaction_filter)


def connect_sqlite(db_path: Path) -> sqlite3.Connection:
    """Open SQLite with production-friendly timeout and WAL settings."""
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def write_env_value(env_path: Path, key: str, value: str) -> None:
    """Update or append one .env key without touching unrelated secrets."""
    if not re.match(r"^[A-Z0-9_]+$", key):
        raise ValueError(f"Invalid env key: {key}")
    lines = []
    found = False
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
    updated = []
    for line in lines:
        if line.strip().startswith(f"{key}="):
            updated.append(f"{key}={value}")
            found = True
        else:
            updated.append(line)
    if not found:
        updated.append(f"{key}={value}")
    env_path.write_text("\n".join(updated) + "\n", encoding="utf-8")


def safe_bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
