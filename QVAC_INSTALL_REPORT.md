# QVAC Install Report

Verification date: 2026-06-03
Project: Crypto AI Trader
Scope: local QVAC installation and verification only. No deployment. No live trading.

## Installation Status

Status: SUCCESS

QVAC CLI was installed globally with npm and a local OpenAI-compatible QVAC server was started on loopback only.

Executed:

```bash
node --version
npm --version
npm install -g @qvac/cli
qvac --version
qvac doctor
```

Results:

```text
Node.js: v24.16.0
npm: 11.13.0
npm install: added 844 packages in 8m
```

## QVAC Version

```text
qvac --version
0.6.0
```

Installed binary:

```text
/home/asrory/.local/lib/nodejs/current/bin/qvac
```

## Doctor Results

Executed:

```bash
qvac doctor
```

Result summary:

```text
Host: linux-x64, Node 24.16.0
Runtime:
  OK Node.js version — v24.16.0
  OK CLI host — linux-x64
Disk:
  OK Free disk space — 77.97 GB
Optional:
  OK ffmpeg
Required checks:
  OK All required checks passed
```

Warnings:

```text
Total RAM — 3.53 GB
Available RAM — 0.67 GB
GPU acceleration — Vulkan ICD not found
Android adb not found
Bare runtime not found
Bun not found
@qvac/sdk resolvable from project — not found
```

Notes:

- Low RAM and no Vulkan are performance risks, not install blockers.
- `@qvac/sdk` is not required for this server-only demo path.
- No automatic system package installation was performed because required QVAC checks already passed and Vulkan would require OS package installation privileges.

## Local Configuration

Created:

```text
qvac.config.json
```

Contents:

```json
{
  "serve": {
    "models": {
      "qvac-local": {
        "model": "QWEN3_600M_INST_Q4",
        "default": true,
        "preload": true,
        "config": {
          "ctx_size": 8192
        }
      }
    }
  }
}
```

## Server Startup

Executed:

```bash
qvac serve openai \
  --host 127.0.0.1 \
  --port 11434 \
  --api-key local-qvac-token \
  --config qvac.config.json \
  --model qvac-local \
  --verbose
```

Startup logs:

```text
Preloading 1 model(s): qvac-local
Loading model "qvac-local" from registry://hf/unsloth/Qwen3-0.6B-GGUF/.../Qwen3-0.6B-Q4_0.gguf
Downloaded to /home/asrory/.qvac/models/5b8aae816570a09d_Qwen3-0.6B-Q4_0.gguf
Checksum validated for Qwen3-0.6B-Q4_0.gguf
Model "qvac-local" loaded (SDK modelId: 18e589b2877f067b).
QVAC API server listening on http://127.0.0.1:11434
```

Port binding:

```text
127.0.0.1:11434 LISTEN users:(("MainThread",pid=127345,fd=26))
```

## Available Models

Executed:

```bash
curl -sS -i http://127.0.0.1:11434/v1/models \
  -H 'Authorization: Bearer local-qvac-token'
```

Result:

```text
HTTP/1.1 200 OK
{"object":"list","data":[{"id":"qvac-local","object":"model","created":1780449926,"owned_by":"qvac"}]}
```

The unauthenticated exact check:

```bash
curl -i http://127.0.0.1:11434/v1/models
```

returned:

```text
HTTP/1.1 401 Unauthorized
{"error":{"message":"Invalid or missing API key.","type":"invalid_request_error","code":"invalid_api_key"}}
```

This is expected because the server was started with `--api-key local-qvac-token`.

## Endpoint Verification

Executed:

```bash
curl -sS http://127.0.0.1:11434/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer local-qvac-token' \
  -d '{"model":"qvac-local","messages":[{"role":"system","content":"Return concise JSON only."},{"role":"user","content":"Return {\"status\":\"qvac_ok\"}."}],"temperature":0.2,"max_tokens":80}'
```

Result:

```text
HTTP success, model=qvac-local, choices returned
```

QVAC server logs:

```text
POST /v1/chat/completions
chat model=qvac-local messages=2 stream=false
request-lifecycle kind=completion modelId=18e589b2877f067b state=completed
completion done tokens=80 finish=stop
200 POST /v1/chat/completions
```

## Crypto AI Trader Verification

Executed from project root:

```bash
AI_PROVIDER=qvac \
QVAC_BASE_URL=http://127.0.0.1:11434/v1 \
QVAC_API_KEY=local-qvac-token \
QVAC_MODEL=qvac-local \
LOCAL_ONLY_INFERENCE=true \
ENABLE_GROQ_FALLBACK=false \
TRADING_MODE=paper \
LIVE_TRADING=false \
LIVE_TRADING_LOCKDOWN=true \
SYMBOLS=BTC/USDT,ETH/USDT,SOL/USDT \
MAX_SYMBOLS_PER_CYCLE=3 \
timeout --signal=INT 120s python3 main.py
```

Result: SUCCESS

Main log proof:

```text
2026-06-03 08:28:27 - main - INFO - AI inference boundary: provider=qvac endpoint=http://127.0.0.1:11434/v1/chat/completions local_only=true groq_fallback=false
2026-06-03 08:28:27 - main - INFO - Mode: PAPER
2026-06-03 08:28:27 - main - INFO - OK: Running in PAPER/BACKTEST mode (no real trades)
2026-06-03 08:28:27 - main - INFO - OK: AI provider configured: qvac
2026-06-03 08:28:27 - main - INFO - OK: Local-only inference policy is active
2026-06-03 08:28:37 - main - INFO - BTC/USDT decision provider=qvac action=HOLD confidence=93
2026-06-03 08:28:44 - main - INFO - ETH/USDT decision provider=qvac action=HOLD confidence=93
2026-06-03 08:28:52 - main - INFO - SOL/USDT decision provider=qvac action=HOLD confidence=93
2026-06-03 08:28:52 - main - INFO - Trading loop cycle completed
2026-06-03 08:29:04 - main - INFO - Trades Executed: 0
```

QVAC server proof during the Crypto AI Trader cycle:

```text
POST /v1/chat/completions
chat model=qvac-local messages=2 stream=false genParams={"temp":0.2,"predict":120}
request-lifecycle kind=completion modelId=18e589b2877f067b state=completed
completion done tokens=120 finish=stop
200 POST /v1/chat/completions
```

SQLite telemetry proof:

```text
SOL/USDT DecisionAgent provider=qvac action=HOLD confidence=93
ETH/USDT DecisionAgent provider=qvac action=HOLD confidence=93
BTC/USDT DecisionAgent provider=qvac action=HOLD confidence=93
backend_status mode=paper live_trading=0 trades_executed=0
```

Safety gate proof:

```text
RiskAgent safety_flags:
PAPER_MODE_ACTIVE
LIVE_TRADING_DISABLED
LIVE_LOCKDOWN_ACTIVE
LOCAL_ONLY_INFERENCE
HIGH_LIQUIDATION_RISK
```

Groq request verification:

```bash
rg -n "provider=groq|api\\.groq|https://api\\.groq|AI inference attempt provider=groq|AI inference completed provider=groq" logs/main_20260603.log
```

Result:

```text
No matches. Groq requests = 0.
```

Note: the exact child logger phrase `AI inference completed provider=qvac` was not written to `logs/main_20260603.log` because `services.ai_provider` is not attached to the main file logger. Equivalent integration proof is present in:

- Main app logs: `decision provider=qvac`
- SQLite telemetry: `DecisionAgent provider=qvac`
- QVAC server logs: successful `POST /v1/chat/completions` completion requests

## Remaining Issues

- QVAC inference works, but available RAM is low. Close other apps before recording if QVAC responses become slow.
- No Vulkan ICD is installed, so QVAC is using CPU inference. This is acceptable for demo verification but slower.
- Qwen3 output includes `<think>` reasoning text in the decision rationale. This does not affect provider telemetry or risk gating, but the demo should focus on provider field, safety flags, and structured decision JSON.
- `feedparser` is missing in the current Python runtime, so news RSS falls back safely to local empty headline handling.
- `.env` contains secrets. Do not display `.env` during recording.

## Final Status

QVAC local inference is installed, running, and verified.

Crypto AI Trader now demonstrates real `provider=qvac` telemetry in paper mode with live trading disabled and locked.
