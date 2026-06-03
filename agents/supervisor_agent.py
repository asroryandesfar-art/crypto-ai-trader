"""Deterministic decision synthesis with optional local QVAC explanation."""

from __future__ import annotations

import asyncio
import json
import logging

logger = logging.getLogger(__name__)


class SupervisorAgent:
    """Combine local agent votes; QVAC can explain but cannot override safety."""

    name = "DecisionAgent"

    def __init__(self, config, ai_service, risk_agent):
        self.config = config
        self.ai_service = ai_service
        self.risk_agent = risk_agent
        self.decision_history = []
        logger.info("SupervisorAgent initialized")

    async def analyze_and_decide(self, symbol: str, analyses: dict, emergency_stop: bool = False, daily_loss_hit: bool = False) -> dict:
        technical = analyses["market"]
        sentiment = analyses["sentiment"]
        whale = analyses["whale"]
        liquidation = analyses["liquidation"]
        votes = {
            "market": technical.get("vote", "HOLD"),
            "sentiment": "BUY" if sentiment.get("sentiment_score", 0) >= 18 else "SELL" if sentiment.get("sentiment_score", 0) <= -18 else "HOLD",
            "whale": whale.get("pressure", "NEUTRAL").replace("NEUTRAL", "HOLD"),
            "liquidation": "HOLD" if liquidation.get("liquidation_risk") == "HIGH" else technical.get("vote", "HOLD"),
        }
        buy_votes = sum(vote == "BUY" for vote in votes.values())
        sell_votes = sum(vote == "SELL" for vote in votes.values())
        candidate = "BUY" if buy_votes >= 3 else "SELL" if sell_votes >= 3 else "HOLD"
        agreement = max(buy_votes, sell_votes, sum(vote == "HOLD" for vote in votes.values()))
        confidence = min(95, int(48 + agreement * 10 + min(abs(float(technical.get("momentum_pct", 0))), 5) * 3))
        if candidate == "HOLD":
            confidence = min(confidence, 74)
        risk = self.risk_agent.evaluate(candidate, confidence, liquidation, emergency_stop, daily_loss_hit)
        action = risk["approved_action"]
        risk_level = liquidation.get("liquidation_risk", "LOW")
        rationale = f"Local synthesis: market {votes['market']}, sentiment {votes['sentiment']}, whale {votes['whale']}, liquidation risk {risk_level}."
        provider = "local_fallback"
        prompt = "Explain this deterministic crypto signal in one short factual sentence. Do not change the action or safety flags:\n" + json.dumps({"symbol": symbol, "action": action, "confidence": confidence, "risk_level": risk_level, "agent_votes": votes, "safety_flags": risk["safety_flags"]}, separators=(",", ":"))
        summary = await asyncio.to_thread(self.ai_service.chat_completion, prompt, 120)
        if summary:
            rationale, provider = summary[:500], self.ai_service.last_provider
        elif self.ai_service.last_provider:
            provider = self.ai_service.last_provider
        decision = {"action": action, "confidence": confidence, "risk_level": risk_level, "rationale": rationale, "reason": rationale, "agent_votes": votes, "safety_flags": risk["safety_flags"], "provider": provider}
        decision["raw"] = json.dumps(decision, separators=(",", ":"))
        self.decision_history.append(decision)
        logger.info("%s symbol=%s result=%s", self.name, symbol, decision)
        return decision
