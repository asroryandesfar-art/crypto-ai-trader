"""Local-first market sentiment aggregation."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class SentimentAgent:
    """Combine local news scoring with optional Fear & Greed data."""

    name = "SentimentAgent"

    def __init__(self, fear_greed_service=None, news_agent=None, ai_service=None):
        self.fear_greed = fear_greed_service
        self.news_agent = news_agent
        self.ai_service = ai_service
        logger.info("SentimentAgent initialized")

    def analyze(self, news_result: dict, fear_greed: dict | None = None, use_qvac_summary: bool = False) -> dict:
        fg = fear_greed or {"value": 50, "classification": "Neutral", "source": "local_default"}
        fg_value = max(0, min(100, int(fg.get("value", 50))))
        news_direction = 1 if news_result.get("sentiment") == "BULLISH" else -1 if news_result.get("sentiment") == "BEARISH" else 0
        news_component = news_direction * float(news_result.get("impact_score", 0))
        score = round(max(-100, min(100, ((fg_value - 50) * 1.2) + (news_component * 0.4))), 2)
        label = "BULLISH" if score >= 18 else "BEARISH" if score <= -18 else "NEUTRAL"
        rationale = f"Fear & Greed {fg_value} ({fg.get('classification', 'Neutral')}), news {news_result.get('sentiment', 'NEUTRAL')} impact {news_result.get('impact_score', 0)}."
        provider = "local_rules"
        if use_qvac_summary and self.ai_service:
            summary = self.ai_service.chat_completion("Summarize this sentiment assessment in one sentence: " + rationale, max_tokens=80)
            if summary:
                rationale, provider = summary[:500], self.ai_service.last_provider
            else:
                provider = self.ai_service.last_provider or "local_fallback"
        result = {"sentiment_score": score, "label": label, "rationale": rationale, "fear_greed": fg_value, "provider": provider}
        logger.info("%s result=%s", self.name, result)
        return result
