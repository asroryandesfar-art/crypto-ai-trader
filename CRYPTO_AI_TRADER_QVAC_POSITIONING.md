# Crypto AI Trader QVAC Hackathon Positioning

**Project Name:** Crypto AI Trader

**Positioning:** Local-first QVAC-compatible Edge AI market intelligence platform.

**One-line pitch:** Crypto AI Trader turns a market-analysis codebase into a privacy-preserving Edge AI showcase where local agents analyze market risk and QVAC provides local reasoning through a loopback OpenAI-compatible endpoint.

## Project Description

Crypto AI Trader is a QVAC-compatible Edge AI showcase built from the existing `crypto_ai_trader` codebase. It demonstrates how a multi-agent intelligence system can run local market analysis, preserve user privacy, and use QVAC for reasoning and explanation without depending on cloud inference by default.

The project is positioned as market risk intelligence, not as a financial advice system. It is a market risk intelligence platform for demonstrating local-first inference, agent telemetry, deterministic safety gates, and QVAC-powered local synthesis.

## Elevator Pitch

Crypto AI Trader is a local-first QVAC-compatible Edge AI market intelligence platform. Specialized local agents analyze technical indicators, public news context, sentiment, volume anomalies, liquidation pressure, and safety constraints. QVAC runs locally as the reasoning layer, while the dashboard proves which provider was used, whether local-only mode is active, and what each agent produced.

## Problem Statement

Many AI market-analysis systems rely on centralized cloud inference for every reasoning step. That creates practical problems for edge deployments:

- Decision context and prompts may leave the user's machine.
- Cloud model availability can affect core workflows.
- Latency and rate limits reduce responsiveness.
- Multi-agent systems become expensive if every agent calls a remote model.
- Users cannot easily verify whether inference happened locally or in the cloud.

Crypto AI Trader addresses this by keeping agent analysis, telemetry, structured decisions, and fallback behavior local-first by default.

## Why QVAC

QVAC is the local reasoning boundary for Crypto AI Trader. The project uses QVAC because it can expose an OpenAI-compatible local endpoint, which lets the existing AI inference path move from a cloud API to local edge execution with minimal application disruption.

QVAC enables:

- Local reasoning through `http://127.0.0.1:11434/v1/chat/completions`
- Privacy-preserving explanation and synthesis
- Cloud inference disabled by default with `LOCAL_ONLY_INFERENCE=true`
- Explicit provider telemetry: `qvac`, `local_fallback`, or opt-in `groq`
- Resilient behavior when local inference is unavailable
- Edge deployment readiness without rewriting the whole system

## What Runs Locally

- Market Analyst: RSI, SMA, EMA, momentum, volatility, and local market structure.
- Sentiment Agent: local rules plus optional local QVAC summarization.
- News Analyzer: RSS headline classification with QVAC summary when available.
- Whale Tracker: public volume and anomaly scoring from available market snapshots.
- Liquidation Detector: volatility, pressure, and price movement risk estimate.
- Risk Manager: deterministic hard safety gate.
- Decision Agent: structured decision synthesis with optional QVAC explanation.
- Dashboard Telemetry: local SQLite-backed agent status, provider status, and local-only status.

## What Data Stays Local

- Agent outputs and intermediate analysis
- Structured decision JSON
- Provider telemetry
- Dashboard chat context
- Safety flags and risk-gate results
- Local SQLite runtime state
- QVAC prompts and explanations when `LOCAL_ONLY_INFERENCE=true`

Public market data may still be fetched from public APIs such as CoinGecko, Binance, Alternative.me, and RSS feeds. The QVAC reasoning context is kept on the local machine by default.

## Cloud Inference Policy

Default configuration:

```env
AI_PROVIDER=qvac
QVAC_BASE_URL=http://127.0.0.1:11434/v1
LOCAL_ONLY_INFERENCE=true
ENABLE_GROQ_FALLBACK=false
TRADING_MODE=paper
LIVE_TRADING=false
LIVE_TRADING_LOCKDOWN=true
```

Groq is retained only as an explicit opt-in fallback for compatibility testing. With `LOCAL_ONLY_INFERENCE=true`, Groq fallback is blocked even if a key exists.

## Local Fallback

If the QVAC server is unavailable, the project does not switch silently to cloud inference. It falls back to deterministic local logic:

- local momentum rule for decision safety
- local keyword rules for news and sentiment
- deterministic risk gate remains authoritative
- dashboard provider telemetry reports `local_fallback`

## Architecture Diagram

```text
                         +------------------------------+
                         |     Crypto AI Trader UI      |
                         | Dashboard + Provider Proof   |
                         +---------------+--------------+
                                         |
                                         v
                         +------------------------------+
                         |       Local SQLite State      |
                         | Decisions, Logs, Telemetry    |
                         +---------------+--------------+
                                         |
                                         v
+------------------------------------------------------------------------+
|                    Local Multi-Agent Intelligence Layer                 |
|                                                                        |
|  +----------------+  +----------------+  +------------------------+   |
|  | Market Analyst |  | News Analyzer  |  | Sentiment Agent        |   |
|  +----------------+  +----------------+  +------------------------+   |
|                                                                        |
|  +----------------+  +----------------+  +------------------------+   |
|  | Whale Tracker  |  | Liquidation    |  | Deterministic Risk     |   |
|  | Anomaly Agent  |  | Detector       |  | Manager / Safety Gate  |   |
|  +----------------+  +----------------+  +------------------------+   |
|                                                                        |
|                         +---------------------+                        |
|                         | Decision Agent      |                        |
|                         | Structured JSON     |                        |
|                         +----------+----------+                        |
+------------------------------------+-----------------------------------+
                                     |
                                     v
                         +------------------------------+
                         |       QVAC Local AI          |
                         | 127.0.0.1 Local Inference    |
                         | OpenAI-Compatible Endpoint   |
                         +------------------------------+
```

## Judging-Focused Explanation

### Innovation

Crypto AI Trader reframes a market-analysis repository as a verifiable Edge AI intelligence showcase. The innovation is not automated execution; it is the local-first multi-agent reasoning boundary: deterministic agents produce structured market intelligence, QVAC provides local synthesis, and the dashboard proves provider and agent telemetry.

### Technical Implementation

- Generic AI provider adapter for QVAC-first inference
- OpenAI-compatible local QVAC HTTP integration
- Local-only enforcement through environment configuration
- Groq retained only as explicit opt-in fallback
- Activated local agents for market, sentiment, news, anomaly, liquidation, risk, and decision synthesis
- Structured decision JSON with `action`, `confidence`, `risk_level`, `rationale`, `agent_votes`, and `safety_flags`
- Local SQLite telemetry for active agents and provider usage
- Dashboard proof of provider status and local-only status

### QVAC Integration

QVAC is used for bounded local reasoning and explanation. It does not own safety decisions and cannot bypass the deterministic risk gate. The integration uses a local OpenAI-compatible endpoint so the application can route reasoning to QVAC without changing the rest of the agent pipeline.

### Local-First Architecture

The system computes primary signals locally. QVAC is called only for synthesis and explanations where available. If QVAC is offline, deterministic local fallback keeps the analysis cycle operational without cloud inference.

### Privacy Benefits

Prompt context, agent outputs, structured decisions, dashboard chat context, and telemetry remain local by default. Remote fallback is disabled unless the operator explicitly changes both `LOCAL_ONLY_INFERENCE` and `ENABLE_GROQ_FALLBACK`.

### Edge AI Benefits

Crypto AI Trader demonstrates lower dependency on remote inference, user-controlled reasoning boundaries, local resilience, observable provider telemetry, and deployability on a local workstation or edge node.

### Multi-Agent Pipeline

The pipeline combines specialized local modules instead of relying on a single general-purpose model. Each agent contributes a bounded signal, the Decision Agent combines those signals into structured JSON, and the Risk Manager remains the final deterministic safety gate.

### Safety Gate

Safety is deterministic and non-negotiable:

- Paper mode is default.
- Live trading is disabled for the demo.
- Live lockdown remains enabled.
- Emergency stop is enforced.
- Daily loss and confidence thresholds remain hard gates.
- AI cannot override risk controls.
- No profit guarantees or financial advice claims are made.

## 60-Second Demo Script

**0-10s: Open with positioning**

"This is Crypto AI Trader, a local-first QVAC-compatible Edge AI market intelligence platform. It is not an automated trading product; it demonstrates private multi-agent market reasoning at the edge."

**10-20s: Show local-only configuration**

"The environment is configured for QVAC: `AI_PROVIDER=qvac`, `LOCAL_ONLY_INFERENCE=true`, and `ENABLE_GROQ_FALLBACK=false`. Live trading is disabled with `TRADING_MODE=paper`, `LIVE_TRADING=false`, and `LIVE_TRADING_LOCKDOWN=true`."

**20-35s: Show active agents**

"The dashboard shows real agent telemetry from local modules: Market Analyst, News Analyzer, Sentiment Agent, Whale Tracker, Liquidation Detector, Risk Manager, and Decision Agent. These agents compute structured analysis locally before any explanation step."

**35-45s: Show provider telemetry**

"The provider field proves whether the latest reasoning used `qvac` or `local_fallback`. With local-only inference enabled, Groq is not used unless the operator explicitly disables local-only mode and enables fallback."

**45-55s: Show structured decision JSON**

"The Decision Agent emits structured JSON: action, confidence, risk level, rationale, agent votes, and safety flags. QVAC can explain the synthesis, but the deterministic Risk Manager remains the hard gate."

**55-60s: Close**

"Crypto AI Trader shows why QVAC matters: private reasoning, local fallback, edge deployment, and verifiable provider telemetry for a real multi-agent intelligence workflow."

## DoraHacks-Ready Submission Text

### One-Line Pitch

Crypto AI Trader is a local-first QVAC-compatible Edge AI market intelligence platform that keeps multi-agent reasoning private, local, and verifiable.

### Full Project Description

Crypto AI Trader demonstrates how an existing market-analysis workflow can be transformed into a QVAC-powered Edge AI intelligence system. The platform runs a local multi-agent pipeline for market signals, news context, sentiment, anomaly activity, liquidation risk, and deterministic safety checks. QVAC provides local reasoning and explanation through an OpenAI-compatible loopback endpoint, while the dashboard proves active agents, provider status, local-only mode, and structured decision output.

The project is intentionally positioned as a market risk intelligence showcase, not as an automated trading product. Paper mode is default, live trading is disabled for the demo, and deterministic safety controls remain authoritative.

### Problem

AI market tools often depend on cloud inference, which can expose sensitive prompts, increase latency, create provider lock-in, and make it hard to prove where reasoning happened. Multi-agent workflows amplify this problem because each agent can generate context that should remain local.

### Solution

Crypto AI Trader moves reasoning to the edge with QVAC. Local agents generate structured signals, QVAC performs local synthesis and explanation, and the dashboard displays proof of provider usage. If QVAC is unavailable, the system falls back to deterministic local logic instead of silently using cloud inference.

### Technical Architecture

- Python backend with local multi-agent analysis
- QVAC-first AI provider adapter using an OpenAI-compatible endpoint
- Local-only inference enforcement
- Optional Groq fallback disabled by default
- SQLite telemetry for agent output and provider proof
- Streamlit dashboard for market intelligence, agent status, provider status, and structured decisions
- Deterministic risk gate that AI cannot override

### Why QVAC

QVAC makes the project credible as an Edge AI showcase because it allows reasoning to run locally while preserving compatibility with the existing OpenAI-style chat-completion interface. That means the project can demonstrate real local inference without a rewrite, and judges can verify the local provider boundary directly from configuration and dashboard telemetry.

### Demo Flow

1. Show `AI_PROVIDER=qvac`, `LOCAL_ONLY_INFERENCE=true`, and `ENABLE_GROQ_FALLBACK=false`.
2. Show `TRADING_MODE=paper`, `LIVE_TRADING=false`, and `LIVE_TRADING_LOCKDOWN=true`.
3. Run or display one paper-mode analysis cycle.
4. Open the dashboard and show active agent telemetry.
5. Show provider telemetry reporting `qvac` or `local_fallback`.
6. Show structured decision JSON with safety flags.
7. Explain that QVAC provides local reasoning while deterministic safety remains authoritative.

### Future Roadmap

- Package a reproducible edge-node demo profile.
- Add model-performance telemetry for different local QVAC models.
- Expand local news and market-data cache controls.
- Add privacy audit views showing exactly what context is sent to QVAC.
- Add offline replay mode for deterministic demo runs.
- Improve deployment guides for laptops, mini PCs, and edge servers.
