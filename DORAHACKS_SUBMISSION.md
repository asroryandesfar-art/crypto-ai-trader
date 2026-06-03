# Crypto AI Trader DoraHacks Submission

## One-Line Pitch

Crypto AI Trader is a local-first QVAC-compatible Edge AI market intelligence platform that keeps multi-agent reasoning private, local, and verifiable.

## Full Project Description

Crypto AI Trader demonstrates how an existing market-analysis workflow can be transformed into a QVAC-powered Edge AI intelligence system. The platform runs a local multi-agent pipeline for market signals, news context, sentiment, anomaly activity, liquidation risk, and deterministic safety checks. QVAC provides local reasoning and explanation through an OpenAI-compatible loopback endpoint, while the dashboard proves active agents, provider status, local-only mode, and structured decision output.

The project is intentionally positioned as a market risk intelligence showcase, not as an automated trading product. Paper mode is default, live trading is disabled for the demo, and deterministic safety controls remain authoritative. The system makes no profit guarantees and does not provide financial advice.

## Problem

AI market tools often depend on cloud inference, which can expose sensitive prompts, increase latency, create provider lock-in, and make it hard to prove where reasoning happened. Multi-agent workflows amplify this problem because each agent can generate context that should remain local.

## Solution

Crypto AI Trader moves reasoning to the edge with QVAC. Local agents generate structured signals, QVAC performs local synthesis and explanation, and the dashboard displays proof of provider usage. If QVAC is unavailable, the system falls back to deterministic local logic instead of silently using cloud inference.

## Technical Architecture

- Python backend with local multi-agent analysis
- QVAC-first AI provider adapter using `http://127.0.0.1:11434/v1/chat/completions`
- Local-only inference enforcement through `LOCAL_ONLY_INFERENCE=true`
- Optional Groq fallback disabled by default through `ENABLE_GROQ_FALLBACK=false`
- SQLite telemetry for agent output and provider proof
- Streamlit dashboard for market intelligence, agent status, provider status, and structured decisions
- Deterministic risk gate that AI cannot override

## Why QVAC

QVAC makes the project credible as an Edge AI showcase because it allows reasoning to run locally while preserving compatibility with the existing OpenAI-style chat-completion interface. The project can demonstrate real local inference without a rewrite, and judges can verify the provider boundary directly from configuration, logs, and dashboard telemetry.

## Demo Flow

1. Show `AI_PROVIDER=qvac`, `LOCAL_ONLY_INFERENCE=true`, and `ENABLE_GROQ_FALLBACK=false`.
2. Show `TRADING_MODE=paper`, `LIVE_TRADING=false`, and `LIVE_TRADING_LOCKDOWN=true`.
3. Run or display one paper-mode analysis cycle.
4. Open the dashboard and show active agent telemetry.
5. Show provider telemetry reporting `qvac` or `local_fallback`.
6. Show structured decision JSON with `action`, `confidence`, `risk_level`, `rationale`, `agent_votes`, and `safety_flags`.
7. Explain that QVAC provides local reasoning while deterministic safety remains authoritative.

## Future Roadmap

- Package a reproducible edge-node demo profile.
- Add model-performance telemetry for different local QVAC models.
- Expand local news and market-data cache controls.
- Add privacy audit views showing exactly what context is sent to QVAC.
- Add offline replay mode for deterministic demo runs.
- Improve deployment guides for laptops, mini PCs, and edge servers.
