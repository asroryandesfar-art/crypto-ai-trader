# Crypto AI Trader

**Local-first QVAC-compatible edge AI for multi-agent market intelligence.**

Crypto AI Trader is a QVAC-compatible Edge AI intelligence showcase built from the existing `crypto_ai_trader` codebase. It demonstrates local-first multi-agent reasoning for crypto market intelligence while keeping inference private by default through a local QVAC endpoint.

This project is positioned for the QVAC Hackathon as an Edge AI showcase, not as an automated trading product. The repository keeps the existing `crypto_ai_trader` codebase name to avoid risky folder-level changes.

Hackathon materials: [QVAC Positioning](CRYPTO_AI_TRADER_QVAC_POSITIONING.md), [DoraHacks Submission](DORAHACKS_SUBMISSION.md), and [60-Second Demo Script](DEMO_SCRIPT.md).

## ✨ Features

### 🧠 Local Multi-Agent Intelligence
- **Market Analyst Agent**: Multi-timeframe technical analysis (EMA, RSI, MACD, Bollinger Bands, ATR)
- **News Agent**: Fetches and analyzes crypto news from RSS feeds
- **Sentiment Agent**: Combines Fear & Greed Index with market sentiment
- **Whale Tracker Agent**: Monitors large transactions and buying/selling pressure
- **Liquidation Agent**: Detects liquidation clusters and volatility spikes
- **Risk Agent**: Calculates position sizing and risk parameters
- **Hedge Agent**: Manages hedging strategies during high volatility
- **Execution Agent**: Records paper-mode execution telemetry; live execution remains explicitly gated and disabled by default
- **Supervisor Agent**: Orchestrates all agents and produces structured market-intelligence decisions

### 🛡️ Safety and Scope
- **Default Paper Mode**: No real trades in the QVAC demo path
- **Daily Loss Limits**: Deterministic guardrail enforced by local risk logic
- **Position Size Limits**: Max 1% risk per paper decision, configurable leverage
- **Confidence Threshold**: Low-confidence decisions are rejected by the safety gate
- **Emergency Stop Switch**: Immediately locks runtime into safe paper-mode behavior
- **Multi-level Validation**: Every decision goes through deterministic risk checks

### 📊 Dashboard
- Real-time market-intelligence metrics
- Portfolio monitoring
- Paper-mode decision history and analytics
- Fear & Greed Index tracking
- Risk metrics visualization
- Alert system

### 💱 Data and Runtime Context
- **Binance public market data** where configured
- CCXT-compatible data access where configured
- Paper-mode analysis for safe demonstration

### 🔗 Data Sources
- CoinGecko API (market data)
- Binance API (public price and volume data where configured)
- Alternative.me (Fear & Greed Index)
- RSS Feeds (crypto news)
- Local QVAC server (default LLM inference)
- Groq API (optional explicit fallback)

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Binance API keys only if you intentionally test exchange integrations outside the QVAC demo
- Local QVAC OpenAI-compatible server for AI analysis
- Groq API key only when remote Groq fallback is explicitly enabled
- Internet connection

### Installation

1. **Extract the project**
```bash
unzip crypto_ai_trader.zip
cd crypto_ai_trader
```

2. **Create virtual environment**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env
# or open with any text editor
```

### Environment Configuration

Edit `.env` file:

```env
# Default: private local inference through QVAC
AI_PROVIDER=qvac
QVAC_BASE_URL=http://127.0.0.1:11434/v1
QVAC_API_KEY=local-qvac-token
QVAC_MODEL=qvac-local
LOCAL_ONLY_INFERENCE=true

# Optional remote fallback. Disabled unless explicitly enabled.
ENABLE_GROQ_FALLBACK=false
GROQ_API_KEY=your_groq_key_here

# Optional exchange integration keys. Not required for the QVAC demo.
BINANCE_API_KEY=your_binance_key
BINANCE_SECRET_KEY=your_binance_secret

# Runtime mode for the QVAC demo
TRADING_MODE=paper

# QVAC demo safety defaults
LIVE_TRADING=false
LIVE_TRADING_LOCKDOWN=true

# Risk parameters
MAX_RISK_PER_TRADE=1       # 1% max per trade
DAILY_MAX_LOSS=3           # 3% daily loss limit
MAX_LEVERAGE=2             # 2x leverage max
CONFIDENCE_THRESHOLD=75    # 75% min confidence

# Market symbols
SYMBOLS=BTC/USDT,ETH/USDT,SOL/USDT
```

## 🎯 Runtime Modes

### Paper Mode (Default for QVAC Demo)
```bash
TRADING_MODE=paper
LIVE_TRADING=false
```
- No real money at risk
- Full local intelligence cycle without live execution
- Suitable for hackathon demo, validation, and replay

### Live Mode (Not Part of Hackathon Demo)
```bash
TRADING_MODE=live
LIVE_TRADING=true  # MUST be true
BINANCE_API_KEY=...
BINANCE_SECRET_KEY=...
```
- Not part of the Crypto AI Trader QVAC showcase
- Requires explicit keys and safety unlocks
- All existing safety checks remain enforced

## 🏃 Running the Edge AI Showcase

### Start Paper-Mode Intelligence Cycle
```bash
python main.py
```

Output:
```
============================================================
CRYPTO AI TRADER INITIALIZED
============================================================
Mode: PAPER
Symbols: ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
Max Risk per Trade: 1%
Daily Max Loss: 3%
✓ Startup validation passed
✓ Services initialized
✓ Paper-mode intelligence loop started
```

### Start Dashboard (in another terminal)
```bash
streamlit run dashboard/app.py
```

Visit `http://localhost:8501` in your browser.

## Local QVAC Inference

QVAC is the default AI provider. Crypto AI Trader sends chat-completion requests only to the loopback endpoint `http://127.0.0.1:11434/v1/chat/completions`. Start a QVAC OpenAI-compatible server separately and configure a model alias named `qvac-local`, or change `QVAC_MODEL` to your configured alias.

Example QVAC server configuration:

```json
{
  "serve": {
    "models": {
      "qvac-local": {
        "model": "QWEN3_600M_INST_Q4",
        "default": true
      }
    }
  }
}
```

Start the local server with bearer-token protection:

```bash
qvac serve openai --api-key local-qvac-token
```

Privacy defaults:

- `AI_PROVIDER=qvac` selects local QVAC inference. `AI_PROVIDER=local_qvac` is also accepted.
- `LOCAL_ONLY_INFERENCE=true` requires a loopback QVAC URL and blocks Groq fallback.
- Set `LOCAL_ONLY_INFERENCE=false` and `ENABLE_GROQ_FALLBACK=true` only when remote fallback is explicitly intended.
- If QVAC is unavailable, decisions use deterministic local fallback logic and provider telemetry reports `local_fallback`.

## Activated Local Agents

The paper-mode backend runs deterministic edge analysis before any execution step. For the QVAC showcase, the focus is local intelligence and telemetry:

- Market Analyst: RSI, SMA, EMA, momentum, and volatility from cached public snapshots.
- News Agent: RSS ingestion with keyword fallback and optional QVAC summary.
- Sentiment Agent: local news scoring combined with optional Fear & Greed data.
- Whale Tracker: public-volume anomaly detection from cached market snapshots.
- Liquidation Agent: volatility and pressure-based liquidation-risk estimate.
- Risk Agent: hard deterministic gate for paper mode, live lockdown, emergency stop, confidence threshold, daily loss budget, and liquidation risk.
- Decision Agent: deterministic vote synthesis with optional QVAC explanation only.

The dashboard reads persisted `agent_telemetry` rows and reports real agent activity and provider usage.

## 🔐 API Key Security

### Getting Groq API Key (Optional Remote Fallback)
1. Visit https://console.groq.com
2. Sign up for free
3. Create new API key
4. Add to `.env` file: `GROQ_API_KEY=your_key`

### Getting Binance API Keys (For Live Trading)
1. Log in to Binance account (https://www.binance.com)
2. Settings → API Management
3. Create new key with:
   - ✓ Enable Reading
   - ✓ Enable Spot & Margin Trading
   - ✗ Enable Withdrawals (for security)
4. Set IP whitelist to your IP only
5. Add to `.env` file

### Security Best Practices
- ✅ Never commit `.env` file with real keys
- ✅ Use IP whitelisting on Binance
- ✅ Use restricted API keys (no withdrawal permission)
- ✅ Rotate keys regularly
- ✅ Monitor unusual account activity
- ✅ Start with small amounts for testing

## 📈 How Market Intelligence Decisions Are Made

```
1. Market Analyst → Technical Analysis (EMA, RSI, MACD, etc)
   ↓
2. News Agent → Fetch & analyze crypto news
   ↓
3. Sentiment Agent → Fear & Greed + news sentiment
   ↓
4. Whale Tracker → Detect public-volume anomaly signals
   ↓
5. Liquidation Agent → Check volatility & liquidation risk
   ↓
6. Risk Agent → Apply deterministic safety gate
   ↓
7. Supervisor Agent → Combine all inputs into structured decision JSON
   ↓
8. Execution Agent → Record paper-mode execution telemetry; live execution remains gated
```

## 🎯 Decision Semantics

### Structured Output
- **BUY**: Local signals indicate constructive market conditions, subject to risk gate
- **SELL**: Local signals indicate defensive market conditions, subject to risk gate
- **HOLD**: Mixed signals, low confidence, local fallback, or safety flags are present

### Deterministic Risk Gate
```
Risk = Max 1% per paper decision
Daily Loss Limit = Max 3% per day
Confidence Required = Min 75%
AI Override = Not allowed
```

## 📊 Dashboard Features

- 📈 **Market Overview**: Current prices, charts, and local indicators
- 😊 **Sentiment Analysis**: Fear & Greed Index, news sentiment
- 🎯 **Structured Decisions**: Recent JSON decisions, confidence, and safety flags
- 💼 **Paper Runtime State**: Demo balance, paper positions, and local state
- 📜 **Decision History**: Paper-mode decision history and telemetry
- ⚠️ **Risk Metrics**: Daily loss tracking, position limits
- 🔔 **Alerts**: Real-time notifications and warnings

## 📁 Project Structure

```
crypto_ai_trader/
├── main.py                    # Entry point
├── config.py                  # Configuration management
├── requirements.txt           # Python dependencies
├── .env.example              # Environment template
├── README.md                 # This file
│
├── agents/                   # 9 specialized trading agents
│   ├── supervisor_agent.py   # Main orchestrator
│   ├── market_analyst_agent.py
│   ├── news_agent.py
│   ├── sentiment_agent.py
│   ├── whale_tracker_agent.py
│   ├── liquidation_agent.py
│   ├── risk_agent.py
│   ├── hedge_agent.py
│   └── execution_agent.py
│
├── services/                 # External API services
│   ├── ai_provider.py        # Local QVAC and optional Groq routing
│   ├── groq_service.py       # Legacy Groq service
│   ├── binance_service.py    # Binance REST API
│   ├── coingecko_service.py  # CoinGecko API
│   ├── fear_greed_service.py # Fear & Greed Index
│   └── ccxt_exchange.py      # CCXT exchange wrapper
│
├── strategies/               # Trading strategies
│   ├── ema_rsi_strategy.py   # EMA + RSI
│   ├── breakout_strategy.py  # Breakout detection
│   └── trend_following_strategy.py  # Trend following
│
├── risk/                     # Risk management
│   ├── position_sizing.py    # Position size calculation
│   ├── stop_loss.py          # Stop loss management
│   ├── take_profit.py        # Take profit management
│   └── daily_loss_guard.py   # Daily loss limiting
│
├── database/                 # Data persistence
│   ├── models.py             # SQLAlchemy models
│   └── db.py                 # Database management
│
├── dashboard/                # Streamlit dashboard
│   └── app.py                # Dashboard UI
│
├── utils/                    # Utility functions
│   ├── logger.py             # Logging configuration
│   ├── helpers.py            # Helper functions
│   └── notifier.py           # Notifications
│
└── logs/                     # Log files (auto-created)
    └── crypto_trader_*.log
```

## ⚠️ Safety and Non-Financial-Advice Notice

Crypto AI Trader is a QVAC Edge AI market intelligence demo. It is not financial advice, not a profit system, and not submitted as an automated trading product. The hackathon demo uses paper mode, live trading disabled, and live lockdown enabled.

### QVAC Demo Safety Checklist
- ✅ Keep `TRADING_MODE=paper`
- ✅ Keep `LIVE_TRADING=false`
- ✅ Keep `LIVE_TRADING_LOCKDOWN=true`
- ✅ Keep `LOCAL_ONLY_INFERENCE=true`
- ✅ Keep `ENABLE_GROQ_FALLBACK=false` unless explicitly testing remote fallback
- ✅ Verify dashboard provider telemetry shows `qvac` or `local_fallback`
- ✅ Do not present outputs as financial advice

### Hard Safety Rules
- AI cannot override the deterministic risk gate
- Cloud inference is disabled by default
- Live execution is outside the QVAC demo scope
- No profit guarantees are made
- Outputs are market-intelligence signals only

## 🐛 Troubleshooting

### Bot won't start
```
Error: AI inference unavailable; using deterministic local fallback
Fix: Start the local QVAC server and verify QVAC_BASE_URL, QVAC_API_KEY, and QVAC_MODEL.
```

### API connection errors
```
Error: Connection to Binance failed
Fix: Check internet, verify API keys, check IP whitelisting
```

### Paper trading not working
```
Check: Confidence threshold, market conditions, risk parameters in logs
```

## 📞 Operational Checks

- Check logs in `logs/` folder for detailed information
- Verify `.env` configuration is correct
- Ensure QVAC is running locally or expect deterministic fallback
- Check internet connection and API rate limits

## 📚 Resources

- [DoraHacks Submission](DORAHACKS_SUBMISSION.md)
- [60-Second Demo Script](DEMO_SCRIPT.md)
- [QVAC Positioning Package](CRYPTO_AI_TRADER_QVAC_POSITIONING.md)
- [CCXT Documentation](https://docs.ccxt.com/)
- [CoinGecko API](https://www.coingecko.com/api)
- [Fear & Greed Index](https://alternative.me/fear-and-greed-index)

## 📄 License

Educational and hackathon demonstration use only. This repository does not provide financial advice.

---

**Crypto AI Trader** - QVAC-compatible Edge AI market intelligence demo.
