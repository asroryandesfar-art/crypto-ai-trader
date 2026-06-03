# Crypto AI Trader 60-Second Demo Script

## 0-10s: Positioning

"This is Crypto AI Trader, a local-first QVAC-compatible Edge AI market intelligence platform. It is not an automated trading product; it demonstrates private multi-agent market reasoning at the edge."

## 10-20s: Local-Only Configuration

"The environment is configured for QVAC: `AI_PROVIDER=qvac`, `LOCAL_ONLY_INFERENCE=true`, and `ENABLE_GROQ_FALLBACK=false`. Live trading is disabled with `TRADING_MODE=paper`, `LIVE_TRADING=false`, and `LIVE_TRADING_LOCKDOWN=true`."

## 20-35s: Active Local Agents

"The dashboard shows real agent telemetry from local modules: Market Analyst, News Analyzer, Sentiment Agent, Whale Tracker, Liquidation Detector, Risk Manager, and Decision Agent. These agents compute structured analysis locally before any explanation step."

## 35-45s: Provider Telemetry

"The provider field proves whether the latest reasoning used `qvac` or `local_fallback`. With local-only inference enabled, Groq is not used unless the operator explicitly disables local-only mode and enables fallback."

## 45-55s: Structured Decision JSON

"The Decision Agent emits structured JSON: action, confidence, risk level, rationale, agent votes, and safety flags. QVAC can explain the synthesis, but the deterministic Risk Manager remains the hard gate."

Example:

```json
{
  "action": "HOLD",
  "confidence": 68,
  "risk_level": "MEDIUM",
  "rationale": "Local agents show mixed momentum and moderate liquidation pressure; safety gate keeps the system in paper mode.",
  "agent_votes": {
    "market_analyst": "HOLD",
    "news_analyzer": "NEUTRAL",
    "sentiment_ai": "NEUTRAL",
    "whale_tracker": "WATCH",
    "liquidation_detector": "CAUTION",
    "risk_manager": "ALLOW_PAPER_ONLY"
  },
  "safety_flags": [
    "TRADING_MODE_PAPER",
    "LIVE_TRADING_DISABLED",
    "LOCAL_ONLY_INFERENCE"
  ]
}
```

## 55-60s: Close

"Crypto AI Trader shows why QVAC matters: private reasoning, local fallback, edge deployment, and verifiable provider telemetry for a real multi-agent intelligence workflow."
