# 🤖 AI Multi-Agent Crypto Trading Bot

Production-ready AI-powered cryptocurrency trading bot built with Python. Features 9 specialized trading agents orchestrated by a supervisor AI to make intelligent trading decisions.

## ✨ Features

### 🧠 9 Specialized AI Agents
- **Market Analyst Agent**: Multi-timeframe technical analysis (EMA, RSI, MACD, Bollinger Bands, ATR)
- **News Agent**: Fetches and analyzes crypto news from RSS feeds
- **Sentiment Agent**: Combines Fear & Greed Index with market sentiment
- **Whale Tracker Agent**: Monitors large transactions and buying/selling pressure
- **Liquidation Agent**: Detects liquidation clusters and volatility spikes
- **Risk Agent**: Calculates position sizing and risk parameters
- **Hedge Agent**: Manages hedging strategies during high volatility
- **Execution Agent**: Executes trades with paper/live mode support
- **Supervisor Agent**: Orchestrates all agents and makes final trading decisions

### 🛡️ Safety Features
- **Default Paper Trading Mode**: No real trades unless explicitly enabled
- **Daily Loss Limits**: Stops trading if daily loss exceeds threshold
- **Position Size Limits**: Max 1% risk per trade, configurable leverage
- **Confidence Threshold**: Only trades with 75%+ confidence (configurable)
- **Emergency Stop Switch**: Instantly halt all trading
- **Multi-level Validation**: Every trade goes through risk checks

### 📊 Dashboard
- Real-time trading metrics
- Portfolio monitoring
- Trade history and analytics
- Fear & Greed Index tracking
- Risk metrics visualization
- Alert system

### 💱 Exchange Support
- **Binance Futures** (primary)
- CCXT for unified access to 100+ exchanges
- Paper trading for backtesting

### 🔗 Data Sources
- CoinGecko API (market data)
- Binance API (live price, volumes)
- Alternative.me (Fear & Greed Index)
- RSS Feeds (crypto news)
- Groq API (LLM analysis)

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Binance API keys (for live trading)
- Groq API key (for AI analysis)
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
# REQUIRED - Groq API Key (Free from https://console.groq.com)
GROQ_API_KEY=your_groq_key_here

# Optional - For live trading only
BINANCE_API_KEY=your_binance_key
BINANCE_SECRET_KEY=your_binance_secret

# Trading mode (paper, backtest, or live)
TRADING_MODE=paper

# CRITICAL - Only set to true when ready for live trading
LIVE_TRADING=false

# Risk parameters
MAX_RISK_PER_TRADE=1       # 1% max per trade
DAILY_MAX_LOSS=3           # 3% daily loss limit
MAX_LEVERAGE=2             # 2x leverage max
CONFIDENCE_THRESHOLD=75    # 75% min confidence

# Trading symbols
SYMBOLS=BTC/USDT,ETH/USDT,SOL/USDT
```

## 🎯 Trading Modes

### Paper Trading (Default - Recommended for Testing)
```bash
TRADING_MODE=paper
LIVE_TRADING=false
```
- No real money at risk
- Full simulation of trading logic
- Perfect for backtesting and validation

### Live Trading (⚠️ Use With Caution)
```bash
TRADING_MODE=live
LIVE_TRADING=true  # MUST be true
BINANCE_API_KEY=...
BINANCE_SECRET_KEY=...
```
- ⚠️ TRADES WITH REAL MONEY
- Requires valid API keys
- All safety checks are enforced

## 🏃 Running the Bot

### Start Paper Trading
```bash
python main.py
```

Output:
```
============================================================
CRYPTO AI TRADING BOT INITIALIZED
============================================================
Mode: PAPER
Symbols: ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
Max Risk per Trade: 1%
Daily Max Loss: 3%
✓ Startup validation passed
✓ Services initialized
✓ Trading loop started
```

### Start Dashboard (in another terminal)
```bash
streamlit run dashboard/app.py
```

Visit `http://localhost:8501` in your browser.

## 🔐 API Key Security

### Getting Groq API Key (FREE)
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

## 📈 How Trading Decisions Are Made

```
1. Market Analyst → Technical Analysis (EMA, RSI, MACD, etc)
   ↓
2. News Agent → Fetch & analyze crypto news
   ↓
3. Sentiment Agent → Fear & Greed + news sentiment
   ↓
4. Whale Tracker → Monitor large transactions
   ↓
5. Liquidation Agent → Check volatility & liquidation risk
   ↓
6. Risk Agent → Calculate position size & risk
   ↓
7. Supervisor Agent → Combine all inputs, make final decision
   ↓
8. Execution Agent → Execute trade in paper/live mode
```

## 🎯 Trading Strategy

### Signal Generation
- **BUY Signal**: Multiple timeframes bullish, sentiment positive, whales accumulating
- **SELL Signal**: Multiple timeframes bearish, sentiment negative, whales distributing
- **HOLD Signal**: Mixed signals, low confidence, or risk factors present

### Risk Management
```
Position Size = (Account × Risk%) / (Entry - Stop Loss)
Risk = Max 1% per trade
Daily Loss Limit = Max 3% per day
Confidence Required = Min 75%
```

## 📊 Dashboard Features

- 📈 **Market Overview**: Current prices, charts, trends
- 😊 **Sentiment Analysis**: Fear & Greed Index, news sentiment
- 🎯 **Trading Decisions**: Recent decisions and confidence scores
- 💼 **Portfolio**: Account balance, open positions, P&L
- 📜 **Trade History**: Completed trades with results
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
│   ├── groq_service.py       # Groq LLM API
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

## ⚠️ Important Warnings

### Risk Disclaimer
```
This bot trades with REAL MONEY in live mode. 
Cryptocurrency trading carries significant risk of loss. 
Past performance does not guarantee future results.
```

### Before Going Live
- ✅ Test in paper mode for at least 7 days
- ✅ Verify all calculations match your expectations
- ✅ Start with small position sizes (0.1% risk)
- ✅ Monitor performance closely
- ✅ Have emergency stop available
- ✅ Keep API keys secure
- ✅ Use dedicated trading wallet

### When NOT to Trade
- ❌ Low liquidity markets
- ❌ Extreme market volatility
- ❌ Major news/events impacting market
- ❌ Platform downtime/maintenance
- ❌ If daily loss limit is reached

## 🐛 Troubleshooting

### Bot won't start
```
Error: GROQ_API_KEY is missing
Fix: Add GROQ_API_KEY to .env file and restart
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

## 📞 Support

- Check logs in `logs/` folder for detailed information
- Verify `.env` configuration is correct
- Ensure all required API keys are set
- Check internet connection and API rate limits

## 📚 Resources

- [Groq API Docs](https://console.groq.com/docs)
- [Binance API](https://binance-docs.github.io/apidocs/)
- [CCXT Documentation](https://docs.ccxt.com/)
- [CoinGecko API](https://www.coingecko.com/api)
- [Fear & Greed Index](https://alternative.me/fear-and-greed-index)

## 📄 License

Educational use only. Trade at your own risk.

---

**Made with ❤️ for crypto traders**

*Version 1.0 - 2024*
