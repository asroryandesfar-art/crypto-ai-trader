"""OpenAI-compatible AI provider routing for local QVAC and optional Groq."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

DEFAULT_QVAC_BASE_URL = "http://127.0.0.1:11434/v1"
DEFAULT_QVAC_MODEL = "qvac-local"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
PLACEHOLDER_KEYS = {"", "your_groq_api_key_here", "your_groq_key_here"}


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _chat_completions_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/chat/completions"):
        return normalized
    return f"{normalized}/chat/completions"


def _is_loopback_url(url: str) -> bool:
    return urlparse(url).hostname in {"127.0.0.1", "localhost", "::1"}


@dataclass(frozen=True)
class ProviderSettings:
    ai_provider: str = "qvac"
    qvac_base_url: str = DEFAULT_QVAC_BASE_URL
    qvac_api_key: str = "local-qvac-token"
    qvac_model: str = DEFAULT_QVAC_MODEL
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"
    local_only_inference: bool = True
    enable_groq_fallback: bool = False


class OpenAICompatibleProvider:
    """Minimal adapter for OpenAI-compatible chat completion endpoints."""

    def __init__(self, name: str, base_url: str, api_key: str, model: str):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.chat_completions_url = _chat_completions_url(base_url)
        self.api_key = api_key.strip()
        self.model = model.strip()

    def chat_completion(self, prompt: str, max_tokens: int = 350) -> str:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        response = requests.post(
            self.chat_completions_url,
            headers=headers,
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "Be concise, risk-aware, and factual."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "max_tokens": max_tokens,
            },
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


class LocalQVACProvider(OpenAICompatibleProvider):
    """Local QVAC server provider."""

    def __init__(self, base_url: str, api_key: str, model: str):
        super().__init__("qvac", base_url, api_key, model)


class GroqProvider(OpenAICompatibleProvider):
    """Remote Groq provider retained as an explicit opt-in fallback."""

    def __init__(self, api_key: str, model: str):
        super().__init__("groq", GROQ_BASE_URL, api_key, model)


class AIProviderAdapter:
    """Route inference through the selected provider and controlled fallback."""

    def __init__(self, primary, groq_fallback=None, local_only_inference: bool = True):
        self.primary = primary
        self.groq_fallback = groq_fallback
        self.local_only_inference = local_only_inference
        self.last_provider = ""
        logger.info(
            "AI provider configured: primary=%s endpoint=%s local_only=%s groq_fallback=%s",
            self.primary.name,
            self.primary.chat_completions_url,
            str(self.local_only_inference).lower(),
            str(self.groq_fallback is not None).lower(),
        )

    def chat_completion(self, prompt: str, max_tokens: int = 350) -> Optional[str]:
        providers = [self.primary]
        if self.groq_fallback is not None:
            providers.append(self.groq_fallback)
        for provider in providers:
            logger.info("AI inference attempt provider=%s", provider.name)
            try:
                response = provider.chat_completion(prompt, max_tokens=max_tokens)
            except Exception as exc:
                logger.warning("AI inference failed provider=%s: %s", provider.name, exc)
                continue
            self.last_provider = provider.name
            logger.info("AI inference completed provider=%s", provider.name)
            return response
        self.last_provider = "local_fallback"
        logger.warning("AI inference unavailable; using deterministic local fallback")
        return None

    async def trading_decision(self, market_payload: dict) -> Optional[dict]:
        """Return a constrained signal or None so the caller uses its local rule."""
        prompt = (
            "You are a cautious crypto trading assistant. "
            "Return only valid JSON with keys action, confidence, reason. "
            "action must be BUY, SELL, or HOLD. confidence is 0-100. "
            "Prefer HOLD unless the signal is clear. Market data:\n"
            f"{json.dumps(market_payload, separators=(',', ':'))}"
        )
        response = await asyncio.to_thread(self.chat_completion, prompt, 350)
        if not response:
            return None
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            parsed = json.loads(response[start:end])
            action = str(parsed.get("action", "HOLD")).upper()
            if action not in {"BUY", "SELL", "HOLD"}:
                action = "HOLD"
            confidence = max(0, min(100, int(float(parsed.get("confidence", 0)))))
            return {
                "action": action,
                "confidence": confidence,
                "reason": str(parsed.get("reason", "No reason returned"))[:500],
                "raw": response[:1000],
                "provider": self.last_provider,
            }
        except Exception as exc:
            logger.warning("Could not parse %s trading decision: %s", self.last_provider, exc)
            return {
                "action": "HOLD", "confidence": 0, "reason": response[:500],
                "raw": response[:1000], "provider": self.last_provider,
            }


def create_ai_provider(settings: ProviderSettings) -> AIProviderAdapter:
    """Build the configured provider graph without silently enabling cloud calls."""
    selected = settings.ai_provider.strip().lower()
    if selected == "local_qvac":
        selected = "qvac"
    if selected not in {"qvac", "groq"}:
        raise ValueError("AI_PROVIDER must be 'qvac', 'local_qvac', or 'groq'")
    if settings.local_only_inference and selected != "qvac":
        raise ValueError("LOCAL_ONLY_INFERENCE=true requires AI_PROVIDER=qvac")
    if selected == "qvac":
        if settings.local_only_inference and not _is_loopback_url(settings.qvac_base_url):
            raise ValueError("LOCAL_ONLY_INFERENCE=true requires QVAC_BASE_URL to use loopback")
        primary = LocalQVACProvider(settings.qvac_base_url, settings.qvac_api_key, settings.qvac_model)
    else:
        if settings.groq_api_key.strip() in PLACEHOLDER_KEYS:
            raise ValueError("GROQ_API_KEY is required when AI_PROVIDER=groq")
        primary = GroqProvider(settings.groq_api_key, settings.groq_model)
    groq_fallback = None
    fallback_requested = settings.enable_groq_fallback and selected != "groq"
    if fallback_requested and settings.local_only_inference:
        logger.warning("Groq fallback requested but blocked because LOCAL_ONLY_INFERENCE=true")
    elif fallback_requested:
        if settings.groq_api_key.strip() in PLACEHOLDER_KEYS:
            logger.warning("Groq fallback requested but GROQ_API_KEY is missing")
        else:
            groq_fallback = GroqProvider(settings.groq_api_key, settings.groq_model)
    return AIProviderAdapter(primary, groq_fallback, settings.local_only_inference)


def create_ai_provider_from_env() -> AIProviderAdapter:
    """Build an adapter from environment variables for the dashboard."""
    return create_ai_provider(ProviderSettings(
        ai_provider=os.getenv("AI_PROVIDER", "qvac"),
        qvac_base_url=os.getenv("QVAC_BASE_URL", DEFAULT_QVAC_BASE_URL),
        qvac_api_key=os.getenv("QVAC_API_KEY", "local-qvac-token"),
        qvac_model=os.getenv("QVAC_MODEL", DEFAULT_QVAC_MODEL),
        groq_api_key=os.getenv("GROQ_API_KEY", ""),
        groq_model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
        local_only_inference=_env_bool("LOCAL_ONLY_INFERENCE", True),
        enable_groq_fallback=_env_bool("ENABLE_GROQ_FALLBACK", False),
    ))
