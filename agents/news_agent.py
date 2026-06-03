"""Local-first RSS news analysis with optional QVAC summarization."""

from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)

POSITIVE = {"approval", "adoption", "bull", "breakout", "gain", "growth", "launch", "partnership", "rally", "record", "surge"}
NEGATIVE = {"ban", "bear", "crash", "decline", "exploit", "fraud", "hack", "lawsuit", "liquidation", "loss", "risk", "selloff"}


class NewsAgent:
    """Fetch RSS headlines and classify them locally before optional local AI summary."""

    name = "NewsAgent"

    def __init__(self, ai_service=None, feed_url: str = "https://cointelegraph.com/feed/"):
        self.ai_service = ai_service
        self.feed_url = feed_url
        self._cache = None
        self._cached_at = 0.0
        logger.info("NewsAgent initialized")

    def fetch_headlines(self, limit: int = 8) -> list[dict]:
        try:
            import feedparser
            feed = feedparser.parse(self.feed_url)
            return [{"title": entry.get("title", ""), "published": entry.get("published", ""), "link": entry.get("link", "")} for entry in feed.entries[:limit]]
        except Exception as exc:
            logger.warning("News RSS unavailable: %s", exc)
            return []

    def analyze(self, headlines: list[dict] | None = None, use_qvac_summary: bool = True) -> dict:
        if headlines is None and self._cache and time.time() - self._cached_at < 600:
            return self._cache
        rows = self.fetch_headlines() if headlines is None else headlines
        scored = []
        for row in rows[:8]:
            title = str(row.get("title", "")).strip()
            words = {word.strip(".,:;!?()[]{}\"\'").lower() for word in title.split()}
            score = sum(word in POSITIVE for word in words) - sum(word in NEGATIVE for word in words)
            if title:
                scored.append((title, score))
        total = sum(score for _, score in scored)
        sentiment = "BULLISH" if total > 0 else "BEARISH" if total < 0 else "NEUTRAL"
        impact = min(100, abs(total) * 15 + min(len(scored), 8) * 3)
        provider = "local_rules"
        summary = f"{len(scored)} headlines classified locally: {sentiment.lower()} impact {impact}."
        if use_qvac_summary and self.ai_service and scored:
            prompt = "Summarize these crypto headlines in one short factual sentence. Do not give trading instructions:\n" + "\n".join(f"- {title}" for title, _ in scored[:5])
            ai_summary = self.ai_service.chat_completion(prompt, max_tokens=120)
            if ai_summary:
                summary = ai_summary[:500]
                provider = self.ai_service.last_provider
            else:
                provider = self.ai_service.last_provider or "local_fallback"
        result = {"impact_score": impact, "sentiment": sentiment, "key_events": [title for title, _ in scored[:5]], "summary": summary, "provider": provider, "headline_count": len(scored)}
        self._cache, self._cached_at = result, time.time()
        logger.info("%s result=%s", self.name, result)
        return result
