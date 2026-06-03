"""Optional Fear & Greed Index service with local neutral fallback."""

from __future__ import annotations

import logging
import time
import requests

logger = logging.getLogger(__name__)


class FearGreedService:
    def __init__(self):
        self._cache = None
        self._cached_at = 0.0
        logger.info("Fear & Greed service initialized")

    def fetch(self) -> dict:
        if self._cache and time.time() - self._cached_at < 300:
            return self._cache
        try:
            response = requests.get("https://api.alternative.me/fng/", params={"limit": 1, "format": "json"}, timeout=5)
            response.raise_for_status()
            item = response.json().get("data", [])[0]
            result = {"value": int(item["value"]), "classification": item.get("value_classification", "Neutral"), "source": "alternative.me"}
        except Exception as exc:
            logger.warning("Fear & Greed unavailable; using neutral fallback: %s", exc)
            result = {"value": 50, "classification": "Neutral", "source": "local_default"}
        self._cache, self._cached_at = result, time.time()
        return result
