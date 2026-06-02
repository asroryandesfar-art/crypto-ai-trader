"""Database management."""
import logging
from pathlib import Path

from utils.runtime_safety import connect_sqlite

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, url="sqlite:///./crypto_trader.db"):
        self.url = url
        self.path = self._resolve_sqlite_path(url)
        logger.info("Database initialized")

    @staticmethod
    def _resolve_sqlite_path(url: str) -> Path:
        prefix = "sqlite:///"
        if not url.startswith(prefix):
            return Path("crypto_trader.db").resolve()
        path = Path(url[len(prefix):])
        return path if path.is_absolute() else path.resolve()

    def connect(self):
        return connect_sqlite(self.path)

    def execute(self, sql: str, params=()):
        with self.connect() as conn:
            cursor = conn.execute(sql, params)
            conn.commit()
            return cursor
