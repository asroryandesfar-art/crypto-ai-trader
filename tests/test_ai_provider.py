"""Tests for AI provider factory and routing (no network calls)."""

import pytest
from unittest.mock import patch, MagicMock
from services.ai_provider import (
    ProviderSettings,
    create_ai_provider,
    _chat_completions_url,
    _is_loopback_url,
    LocalQVACProvider,
    GroqProvider,
    AIProviderAdapter,
)


# ── URL helpers ───────────────────────────────────────────────────────────────

def test_chat_completions_url_appends_path():
    assert _chat_completions_url("http://127.0.0.1:11434/v1") == "http://127.0.0.1:11434/v1/chat/completions"


def test_chat_completions_url_strips_trailing_slash():
    assert _chat_completions_url("http://127.0.0.1:11434/v1/") == "http://127.0.0.1:11434/v1/chat/completions"


def test_chat_completions_url_no_duplicate_path():
    url = "http://127.0.0.1:11434/v1/chat/completions"
    assert _chat_completions_url(url) == url


def test_is_loopback_localhost():
    assert _is_loopback_url("http://localhost:11434") is True


def test_is_loopback_127():
    assert _is_loopback_url("http://127.0.0.1:11434/v1") is True


def test_is_loopback_ipv6():
    assert _is_loopback_url("http://[::1]:11434") is True


def test_is_loopback_remote_false():
    assert _is_loopback_url("http://192.168.1.100:11434") is False


# ── create_ai_provider factory ────────────────────────────────────────────────

def _ps(**kwargs):
    defaults = dict(
        ai_provider="qvac",
        qvac_base_url="http://127.0.0.1:11434/v1",
        qvac_api_key="local-qvac-token",
        qvac_model="qvac-local",
        groq_api_key="",
        groq_model="llama-3.1-8b-instant",
        local_only_inference=True,
        enable_groq_fallback=False,
    )
    defaults.update(kwargs)
    return ProviderSettings(**defaults)


def test_create_qvac_provider():
    adapter = create_ai_provider(_ps())
    assert adapter.primary.name == "qvac"
    assert isinstance(adapter.primary, LocalQVACProvider)


def test_create_groq_provider():
    adapter = create_ai_provider(_ps(
        ai_provider="groq",
        groq_api_key="real_groq_key_1234567890",
        local_only_inference=False,
    ))
    assert adapter.primary.name == "groq"
    assert isinstance(adapter.primary, GroqProvider)


def test_invalid_provider_raises():
    with pytest.raises(ValueError, match="qvac.*groq"):
        create_ai_provider(_ps(ai_provider="openai"))


def test_groq_with_local_only_raises():
    with pytest.raises(ValueError, match="LOCAL_ONLY_INFERENCE"):
        create_ai_provider(_ps(ai_provider="groq", local_only_inference=True))


def test_remote_qvac_with_local_only_raises():
    with pytest.raises(ValueError, match="loopback"):
        create_ai_provider(_ps(qvac_base_url="http://192.168.1.100:11434/v1", local_only_inference=True))


def test_placeholder_groq_key_raises():
    with pytest.raises(ValueError):
        create_ai_provider(_ps(
            ai_provider="groq",
            groq_api_key="your_groq_api_key_here",
            local_only_inference=False,
        ))


def test_groq_fallback_blocked_by_local_only():
    adapter = create_ai_provider(_ps(
        enable_groq_fallback=True,
        groq_api_key="real_groq_key_1234567890",
        local_only_inference=True,
    ))
    assert adapter.groq_fallback is None


def test_groq_fallback_enabled_when_allowed():
    adapter = create_ai_provider(_ps(
        enable_groq_fallback=True,
        groq_api_key="real_groq_key_1234567890",
        local_only_inference=False,
    ))
    assert adapter.groq_fallback is not None
    assert isinstance(adapter.groq_fallback, GroqProvider)


def test_local_qvac_alias_resolves():
    adapter = create_ai_provider(_ps(ai_provider="local_qvac"))
    assert adapter.primary.name == "qvac"


# ── AIProviderAdapter.chat_completion ─────────────────────────────────────────

def test_chat_completion_returns_primary_response():
    primary = MagicMock()
    primary.name = "qvac"
    primary.chat_completion.return_value = "Signal is HOLD."
    primary.chat_completions_url = "http://127.0.0.1:11434/v1/chat/completions"

    adapter = AIProviderAdapter(primary=primary, groq_fallback=None, local_only_inference=True)
    result = adapter.chat_completion("test prompt")
    assert result == "Signal is HOLD."
    assert adapter.last_provider == "qvac"


def test_chat_completion_falls_back_to_groq():
    primary = MagicMock()
    primary.name = "qvac"
    primary.chat_completion.side_effect = ConnectionError("QVAC offline")
    primary.chat_completions_url = "http://127.0.0.1:11434/v1/chat/completions"

    fallback = MagicMock()
    fallback.name = "groq"
    fallback.chat_completion.return_value = "Fallback response."

    adapter = AIProviderAdapter(primary=primary, groq_fallback=fallback, local_only_inference=False)
    result = adapter.chat_completion("test prompt")
    assert result == "Fallback response."
    assert adapter.last_provider == "groq"


def test_chat_completion_returns_none_when_all_fail():
    primary = MagicMock()
    primary.name = "qvac"
    primary.chat_completion.side_effect = ConnectionError("offline")
    primary.chat_completions_url = "http://127.0.0.1:11434/v1/chat/completions"

    adapter = AIProviderAdapter(primary=primary, groq_fallback=None, local_only_inference=True)
    result = adapter.chat_completion("test prompt")
    assert result is None
    assert adapter.last_provider == "local_fallback"


# ── AIProviderAdapter.trading_decision ────────────────────────────────────────

@pytest.mark.asyncio
async def test_trading_decision_parses_valid_json():
    primary = MagicMock()
    primary.name = "qvac"
    primary.chat_completion.return_value = '{"action":"BUY","confidence":82,"reason":"Momentum is positive."}'
    primary.chat_completions_url = "http://127.0.0.1:11434/v1/chat/completions"

    adapter = AIProviderAdapter(primary=primary, groq_fallback=None, local_only_inference=True)
    result = await adapter.trading_decision({"symbol": "BTC/USDT", "price": 50000})
    assert result is not None
    assert result["action"] == "BUY"
    assert result["confidence"] == 82
    assert "Momentum" in result["reason"]


@pytest.mark.asyncio
async def test_trading_decision_clamps_invalid_action_to_hold():
    primary = MagicMock()
    primary.name = "qvac"
    primary.chat_completion.return_value = '{"action":"LONG","confidence":90,"reason":"Go long"}'
    primary.chat_completions_url = "http://127.0.0.1:11434/v1/chat/completions"

    adapter = AIProviderAdapter(primary=primary, groq_fallback=None, local_only_inference=True)
    result = await adapter.trading_decision({})
    assert result["action"] == "HOLD"


@pytest.mark.asyncio
async def test_trading_decision_returns_none_when_provider_fails():
    primary = MagicMock()
    primary.name = "qvac"
    primary.chat_completion.side_effect = ConnectionError("offline")
    primary.chat_completions_url = "http://127.0.0.1:11434/v1/chat/completions"

    adapter = AIProviderAdapter(primary=primary, groq_fallback=None, local_only_inference=True)
    result = await adapter.trading_decision({})
    assert result is None


@pytest.mark.asyncio
async def test_trading_decision_clamps_confidence():
    primary = MagicMock()
    primary.name = "qvac"
    primary.chat_completion.return_value = '{"action":"SELL","confidence":999,"reason":"extreme"}'
    primary.chat_completions_url = "http://127.0.0.1:11434/v1/chat/completions"

    adapter = AIProviderAdapter(primary=primary, groq_fallback=None, local_only_inference=True)
    result = await adapter.trading_decision({})
    assert result["confidence"] == 100
