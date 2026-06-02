"""
Groq LLM service for AI analysis and decision making.
"""

import logging
import json
from typing import Optional
import asyncio
import time

import requests

logger = logging.getLogger(__name__)


class GroqService:
    """Service for interacting with Groq API."""

    def __init__(self, api_key: str, model: str = "llama-3.1-8b-instant"):
        """
        Initialize Groq service.
        
        Args:
            api_key: Groq API key
            model: Model to use
        """
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        self.failure_count = 0
        self.circuit_open_until = 0.0
        logger.info(f"Groq service initialized with model: {model}")

    async def analyze_text(self, text: str) -> Optional[str]:
        """
        Analyze text using Groq API.
        
        Args:
            text: Text to analyze
        
        Returns:
            Analysis response or None if error
        """
        try:
            return await asyncio.to_thread(self._chat_completion, text)
        except Exception as e:
            logger.error(f"Error analyzing text: {e}")
            return None

    async def trading_decision(self, market_payload: dict) -> Optional[dict]:
        """Ask Groq for a compact trading decision JSON."""
        if time.time() < self.circuit_open_until:
            return None
        prompt = (
            "You are a cautious crypto trading assistant. "
            "Return only valid JSON with keys action, confidence, reason. "
            "action must be BUY, SELL, or HOLD. confidence is 0-100. "
            "Prefer HOLD unless the signal is clear. Market data:\n"
            f"{json.dumps(market_payload, separators=(',', ':'))}"
        )
        response = await self.analyze_text(prompt)
        if not response:
            return None

        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            parsed = json.loads(response[start:end])
            action = str(parsed.get("action", "HOLD")).upper()
            if action not in {"BUY", "SELL", "HOLD"}:
                action = "HOLD"
            confidence = int(float(parsed.get("confidence", 0)))
            confidence = max(0, min(100, confidence))
            return {
                "action": action,
                "confidence": confidence,
                "reason": str(parsed.get("reason", "No reason returned"))[:500],
                "raw": response[:1000],
            }
        except Exception as e:
            logger.warning(f"Could not parse Groq trading decision: {e}")
            return {
                "action": "HOLD",
                "confidence": 0,
                "reason": response[:500],
                "raw": response[:1000],
            }

    def _chat_completion(self, text: str) -> Optional[str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Be concise, risk-aware, and factual."},
                {"role": "user", "content": text},
            ],
            "temperature": 0.2,
            "max_tokens": 350,
        }
        try:
            response = requests.post(self.base_url, headers=headers, json=payload, timeout=20)
            response.raise_for_status()
            data = response.json()
            self.failure_count = 0
            self.circuit_open_until = 0.0
            return data["choices"][0]["message"]["content"]
        except requests.RequestException:
            self.failure_count += 1
            if self.failure_count >= 3:
                self.circuit_open_until = time.time() + 300
                logger.warning("Groq circuit breaker opened for 300 seconds after repeated API failures")
            raise
