# QVAC Setup For Demo

Purpose: start a real local QVAC OpenAI-compatible server so Crypto AI Trader provider telemetry shows `qvac`, not only `local_fallback`.

Status on this machine, checked 2026-06-03:

```text
qvac binary: not found on PATH
127.0.0.1:11434: not listening
GET /v1/models: connection refused
Node.js: v24.16.0
npm: 11.13.0
```

## Install QVAC CLI

Official QVAC docs state the OpenAI-compatible HTTP server is provided by `@qvac/cli` and can be installed globally with npm.

```bash
npm install -g @qvac/cli
```

Validate host requirements:

```bash
qvac doctor
```

## Create Demo Server Config

Run from the project root:

```bash
cd /home/asrory/Documents/OneDrive-Dokumen/crypto_ai_trader
```

Create `qvac.config.json` only after QVAC CLI is installed:

```bash
cat > qvac.config.json <<'JSON'
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
JSON
```

## Start QVAC Safely On Loopback

Bind to `127.0.0.1` only and require the demo bearer token expected by Crypto AI Trader:

```bash
qvac serve openai \
  --host 127.0.0.1 \
  --port 11434 \
  --api-key local-qvac-token \
  --config qvac.config.json \
  --model qvac-local
```

The QVAC docs list `--host` default as `127.0.0.1` and `--port` default as `11434`; the command above keeps both explicit for the recording.

## Verify QVAC Before Recording

In another terminal:

```bash
curl -sS http://127.0.0.1:11434/v1/models \
  -H "Authorization: Bearer local-qvac-token"
```

Expected: JSON listing `qvac-local`.

Then verify chat completions:

```bash
curl -sS http://127.0.0.1:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer local-qvac-token" \
  -d '{
    "model": "qvac-local",
    "messages": [
      {"role": "user", "content": "Return one short sentence confirming local QVAC inference."}
    ],
    "temperature": 0.2,
    "max_tokens": 80
  }'
```

Expected: JSON with `choices[0].message.content`.

## Final Crypto AI Trader Demo Cycle

Keep live trading disabled and Groq fallback disabled:

```bash
cd /home/asrory/Documents/OneDrive-Dokumen/crypto_ai_trader

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
timeout --signal=INT 90s python3 main.py
```

Success criteria in `logs/main_20260603.log`:

```text
AI inference boundary: provider=qvac endpoint=http://127.0.0.1:11434/v1/chat/completions local_only=true groq_fallback=false
AI inference completed provider=qvac
DecisionAgent ... provider='qvac'
OK: Running in PAPER/BACKTEST mode (no real trades)
```

Also verify no Groq calls:

```bash
rg -n "provider=groq|api.groq|Groq" logs/main_20260603.log
```

Expected: no real Groq inference attempts. Boundary lines containing `groq_fallback=false` are acceptable.
