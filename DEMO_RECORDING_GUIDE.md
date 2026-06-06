# Crypto AI Trader QVAC Demo Recording Guide

Target duration: **60-90 seconds**. Record at 1080p or higher, keep browser zoom consistent, and avoid showing `.env`, API keys, terminal history, exchange accounts, or unrelated desktop content.

## 1. What To Open

Prepare these tabs before recording:

1. GitHub repository README.
2. GitHub Pages: `https://asroryandesfar-art.github.io/crypto-ai-trader/`.
3. Lightweight Streamlit dashboard: `http://localhost:8501`.
4. Optional terminal showing only the safe launcher output.

Start the replay-only dashboard with:

```bash
./scripts/start_recording_demo.sh
```

Expected safety output:

```text
Backend loop: NOT STARTED
Dashboard URL: http://localhost:8501
Status: READY_FOR_RECORDING
```

The launcher checks QVAC and `/v1/models`, but the dashboard replays saved verified telemetry. It does not start the full trading loop or enable live execution.

## 2. What To Show First

Open with the GitHub README hero so judges immediately understand:

- Local-first multi-agent market intelligence.
- QVAC is the local inference provider.
- Paper mode is active.
- Live trading is disabled.
- The project makes no profit claim.

Move quickly to the GitHub Pages architecture view. Do not spend the first 20 seconds on installation steps or terminal setup.

## 3. What Judges Care About

Prioritize evidence over feature narration:

- **QVAC integration:** `qvac-local`, loopback endpoint, and `provider=qvac` telemetry.
- **Why local matters:** privacy, auditability, and reduced cloud dependency.
- **System design:** specialist agents, bounded QVAC synthesis, deterministic risk gate, and decision ledger.
- **Verifiability:** active-agent rows, structured decision JSON, safety flags, and persisted telemetry.
- **Safety:** paper mode, live trading disabled, lockdown active, and no backend loop in recording mode.
- **Execution quality:** clear README, static judge demo, responsive UI, tests, and reproducible commands.

Do not claim profitability, prediction accuracy, autonomous live execution, or performance that is not directly verified.

## 4. Recommended Recording Order

| Time | Screen | What to show |
| --- | --- | --- |
| 0-8s | GitHub README | Project name, local-first value proposition, QVAC and paper-mode badges |
| 8-18s | GitHub Pages | Architecture and verified system status |
| 18-28s | Dashboard | Judge Demo Mode and replay-only status |
| 28-38s | QVAC Status | `provider=qvac`, `qvac-local`, local-only inference |
| 38-50s | Workflow | Seven active agents and orchestration flow |
| 50-63s | Decision Ledger | Structured decision JSON, votes, provider, timestamp |
| 63-75s | AI Reasoning | Bounded local synthesis and auditable rationale |
| 75-88s | Safety Controls | Paper mode, live trading disabled, lockdown, deterministic risk gate |

## 5. Recording Script

> Crypto AI Trader QVAC is a local-first multi-agent market intelligence system. Instead of sending agent context to centralized inference, the project uses the `qvac-local` model through a loopback QVAC endpoint.
>
> Market, news, sentiment, whale, and liquidation agents produce structured signals. QVAC performs bounded local synthesis, while a deterministic risk gate remains authoritative.
>
> The dashboard shows active agents, `provider=qvac` telemetry, the structured decision ledger, agent votes, and the AI reasoning view. Every decision remains auditable through persisted local telemetry.
>
> For safety, this demo is paper mode only. Live trading is disabled and locked down, and this recording mode does not start the backend trading loop.
>
> The repository includes 149 passing tests, a reproducible local setup, and a static GitHub Pages demo that judges can inspect without running QVAC.

## 6. Capture Checklist

Before the final take:

- Close notifications and unrelated applications.
- Confirm the browser contains no saved credentials or personal tabs.
- Use the lightweight recording launcher, not `main.py`.
- Confirm the dashboard displays saved `provider=qvac` telemetry.
- Keep `PAPER_MODE_ACTIVE` and `LIVE_TRADING_DISABLED` visible.
- Record one clean take without scrolling past empty or loading states.
- Export in 16:9 and verify text remains readable on mobile.
