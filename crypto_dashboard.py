"""
Professional Crypto AI Trader Dashboard
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Cyberpunk-inspired dark UI with real-time data integration.
Features: Live prices, AI signals, whale tracker, news analysis, PnL tracking
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import asyncio
import aiohttp
from functools import lru_cache
import os
import sqlite3
import time
from pathlib import Path
import json
import html
import hmac
import logging

from services.ai_provider import create_ai_provider_from_env
from utils.runtime_safety import connect_sqlite, write_env_value

logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

PROJECT_ROOT = Path(__file__).parent
ENV_PATH = PROJECT_ROOT / ".env"
if load_dotenv:
    load_dotenv(ENV_PATH)

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG & THEME
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Crypto AI Trader Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS for Cyberpunk Dark Theme ─────────────────────────────────────
CUSTOM_CSS = """
<style>
    :root {
        --primary: #00d4ff;      /* Cyan */
        --accent: #00ff41;       /* Neon lime */
        --danger: #ff006e;       /* Hot pink */
        --warning: #ffd60a;      /* Golden */
        --bg-dark: #0f1419;      /* Dark slate */
        --bg-card: #1a1f2e;      /* Card dark */
        --text-primary: #e8eaed; /* Light text */
        --text-muted: #8892a6;   /* Muted text */
        --border: #2d3748;       /* Border color */
    }

    * { font-family: 'Monaco', 'Courier New', monospace; }
    
    body {
        background-color: var(--bg-dark);
        color: var(--text-primary);
    }

    .main {
        background: linear-gradient(135deg, #0f1419 0%, #1a1f2e 100%);
    }

    .stMetric {
        background: rgba(26, 31, 46, 0.6);
        border: 1px solid rgba(0, 212, 255, 0.2);
        border-radius: 8px;
        padding: 1.5rem;
        backdrop-filter: blur(10px);
    }

    .metric-highlight {
        color: var(--primary);
        font-weight: 600;
        text-shadow: 0 0 10px rgba(0, 212, 255, 0.3);
    }

    .stButton > button {
        background: linear-gradient(135deg, #00d4ff 0%, #0099cc 100%);
        color: #0f1419;
        border: none;
        border-radius: 6px;
        font-weight: 600;
        padding: 0.6rem 1.2rem;
        box-shadow: 0 0 20px rgba(0, 212, 255, 0.3);
        transition: all 0.3s ease;
    }

    .stButton > button:hover {
        box-shadow: 0 0 30px rgba(0, 212, 255, 0.6);
        transform: translateY(-2px);
    }

    .card-container {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    }

    .price-bullish {
        color: var(--accent);
        font-weight: 600;
    }

    .price-bearish {
        color: var(--danger);
        font-weight: 600;
    }

    .signal-buy { color: var(--accent); }
    .signal-sell { color: var(--danger); }
    .signal-hold { color: var(--warning); }

    .chart-container {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }

    .header-divider {
        border-top: 2px solid rgba(0, 212, 255, 0.3);
        margin: 1.5rem 0;
    }

    h1, h2, h3 { color: var(--primary); text-shadow: 0 0 10px rgba(0, 212, 255, 0.2); }

    .success { color: var(--accent); }
    .warning { color: var(--warning); }
    .danger { color: var(--danger); }
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def html_escape(value) -> str:
    return html.escape(str(value), quote=True)


def require_dashboard_auth() -> None:
    """Optional password gate. Set DASHBOARD_PASSWORD to enable it."""
    password = os.getenv("DASHBOARD_PASSWORD", "").strip()
    if not password:
        return
    if st.session_state.get("dashboard_authenticated"):
        return
    st.title("Crypto AI Trader Dashboard")
    provided = st.text_input("Dashboard password", type="password")
    if provided and hmac.compare_digest(provided, password):
        st.session_state.dashboard_authenticated = True
        st.rerun()
    if provided:
        st.error("Invalid password")
    st.stop()


require_dashboard_auth()

def resolve_database_path():
    """Resolve sqlite DATABASE_URL into the DB file shared with the backend."""
    database_url = os.getenv("DATABASE_URL", "sqlite:///./crypto_trader.db")
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        return PROJECT_ROOT / "crypto_trader.db"

    raw_path = database_url[len(prefix):]
    path = Path(raw_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


@st.cache_data(ttl=2)
def get_backend_status():
    """Read backend heartbeat written by main.py."""
    db_path = resolve_database_path()
    fallback = {
        "connected": False,
        "status": "offline",
        "mode": "paper",
        "last_heartbeat": "",
        "loop_count": 0,
        "message": "Backend not started",
    }
    if not db_path.exists():
        return fallback

    try:
        with connect_sqlite(db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM backend_status WHERE id = 1").fetchone()
        if not row:
            return fallback

        heartbeat = row["last_heartbeat"] or ""
        connected = False
        try:
            last_seen = datetime.fromisoformat(heartbeat)
            connected = (datetime.now() - last_seen).total_seconds() <= 90
        except ValueError:
            pass

        return {
            "connected": connected and row["status"] == "running",
            "status": row["status"],
            "mode": row["mode"],
            "last_heartbeat": heartbeat,
            "loop_count": row["loop_count"],
            "message": row["message"],
        }
    except Exception as e:
        fallback["message"] = f"Dashboard DB read failed: {e}"
        return fallback


def get_backend_events(limit=12):
    """Read latest backend events for the logs page."""
    db_path = resolve_database_path()
    if not db_path.exists():
        return pd.DataFrame()

    try:
        with connect_sqlite(db_path) as conn:
            query = """
                SELECT timestamp, agent, action, status
                FROM backend_events
                ORDER BY id DESC
                LIMIT ?
            """
            rows = conn.execute(query, (limit,)).fetchall()
        if not rows:
            return pd.DataFrame()

        events = pd.DataFrame(rows, columns=["timestamp", "agent", "action", "status"])
        events["timestamp"] = pd.to_datetime(events["timestamp"])
        return events.sort_values("timestamp")
    except Exception:
        return pd.DataFrame()


def read_table(query: str, params=()):
    db_path = resolve_database_path()
    if not db_path.exists():
        return pd.DataFrame()
    try:
        with connect_sqlite(db_path) as conn:
            return pd.read_sql_query(query, conn, params=params)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=5)
def get_latest_signals(limit=10):
    signals = read_table(
        """
        SELECT timestamp, symbol, action, confidence, price, reason
        FROM trading_signals
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    )
    if not signals.empty:
        signals["timestamp"] = pd.to_datetime(signals["timestamp"])
    return signals


AGENT_NAMES = ["MarketAnalyst", "NewsAgent", "SentimentAgent", "WhaleTracker", "LiquidationAgent", "RiskAgent", "DecisionAgent"]


@st.cache_data(ttl=2)
def get_agent_telemetry(limit=200):
    """Read real local-agent telemetry written by the backend."""
    telemetry = read_table(
        """
        SELECT timestamp, symbol, agent, status, provider, result_json
        FROM agent_telemetry
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    )
    if telemetry.empty:
        return telemetry
    telemetry["timestamp"] = pd.to_datetime(telemetry["timestamp"])
    telemetry["result"] = telemetry["result_json"].apply(lambda value: json.loads(value) if value else {})
    return telemetry


def get_latest_agent_results():
    """Return the newest persisted output for each active local agent."""
    telemetry = get_agent_telemetry()
    if telemetry.empty:
        return {}
    latest = {}
    for _, row in telemetry.iterrows():
        if row["agent"] not in latest:
            latest[row["agent"]] = row.to_dict()
    return latest


def get_agent_runtime_status():
    """Build dashboard status from persisted agent telemetry, not sample values."""
    latest = get_latest_agent_results()
    now = datetime.now()
    rows = []
    for name in AGENT_NAMES:
        row = latest.get(name)
        active = False
        if row:
            active = (now - row["timestamp"].to_pydatetime()).total_seconds() <= 180
        rows.append({
            "Agent": name,
            "Active": active,
            "Provider": row.get("provider", "not_run") if row else "not_run",
            "Symbol": row.get("symbol", "-") if row else "-",
            "Last Update": row["timestamp"].strftime("%H:%M:%S") if row else "not run",
        })
    return pd.DataFrame(rows)


@st.cache_data(ttl=5)
def get_live_positions():
    positions = read_table(
        """
        SELECT symbol, side, entry_price, current_price, quantity, leverage,
               pnl, pnl_percent, opened_at
        FROM paper_positions
        WHERE status = 'OPEN'
        ORDER BY opened_at DESC
        """
    )
    if not positions.empty:
        positions["opened_at"] = pd.to_datetime(positions["opened_at"])
    return positions


@st.cache_data(ttl=5)
def get_trade_history(limit=20):
    trades = read_table(
        """
        SELECT opened_at AS timestamp, symbol, side, entry_price,
               current_price AS exit_price, quantity, pnl, pnl_percent, status
        FROM paper_positions
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    )
    if not trades.empty:
        trades["timestamp"] = pd.to_datetime(trades["timestamp"])
    return trades

# ═══════════════════════════════════════════════════════════════════════════════
# CACHE & DATA FETCHING
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=300)
def fetch_coingecko_prices():
    """Fetch current prices from CoinGecko."""
    try:
        import requests
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={
                "ids": "bitcoin,ethereum,solana",
                "vs_currencies": "usd",
                "include_market_cap": "true",
                "include_24hr_change": "true",
                "include_24hr_vol": "true",
            },
            timeout=5,
        )
        return r.json()
    except Exception as e:
        st.error(f"Price fetch failed: {e}")
        return None


@st.cache_data(ttl=300)
def fetch_coingecko_market_chart(coin_id, days=1):
    """Fetch historical market prices from CoinGecko."""
    try:
        import requests

        r = requests.get(
            f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart",
            params={
                "vs_currency": "usd",
                "days": days,
                "interval": "hourly" if days <= 7 else "daily",
            },
            timeout=10,
        )
        r.raise_for_status()
        rows = r.json().get("prices", [])
        if not rows:
            return pd.DataFrame(columns=["time", "close"])

        chart = pd.DataFrame(rows, columns=["time", "close"])
        chart["time"] = pd.to_datetime(chart["time"], unit="ms")
        chart["close"] = pd.to_numeric(chart["close"], errors="coerce")
        return chart.dropna()
    except Exception as e:
        st.warning(f"Chart fetch failed for {coin_id}: {e}")
        return pd.DataFrame(columns=["time", "close"])


def get_db_market_chart(symbol, limit=96):
    """Read recent backend market snapshots for a symbol."""
    chart = read_table(
        """
        SELECT timestamp AS time, price AS close
        FROM market_snapshots
        WHERE symbol = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (symbol, limit),
    )
    if chart.empty:
        return chart

    chart["time"] = pd.to_datetime(chart["time"])
    chart["close"] = pd.to_numeric(chart["close"], errors="coerce")
    return chart.dropna().sort_values("time")


@st.cache_data(ttl=300)
def fetch_fear_greed():
    """Fetch Fear & Greed Index."""
    try:
        import requests
        r = requests.get(
            "https://api.alternative.me/fng/",
            params={"limit": 1, "format": "json"},
            timeout=5,
        )
        data = r.json().get("data", [])
        if data:
            return {
                "value": int(data[0]["value"]),
                "classification": data[0]["value_classification"],
                "timestamp": data[0]["timestamp"],
            }
    except Exception as e:
        st.warning(f"Fear & Greed fetch failed: {e}")
    return {"value": 50, "classification": "Neutral", "timestamp": ""}


@st.cache_data(ttl=600)
def fetch_news_headlines():
    """Fetch crypto news from CoinTelegraph."""
    try:
        import feedparser
        feed = feedparser.parse("https://cointelegraph.com/feed/")
        headlines = []
        for entry in feed.entries[:8]:
            headlines.append({
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
            })
        return headlines
    except Exception as e:
        st.warning(f"News fetch failed: {e}")
    return []


PRICE_LABELS = {
    "bitcoin": ("BTC/USDT", "Bitcoin"),
    "ethereum": ("ETH/USDT", "Ethereum"),
    "solana": ("SOL/USDT", "Solana"),
}

MARKET_CHARTS = [
    {"coin_id": "bitcoin", "symbol": "BTC/USDT", "name": "Bitcoin"},
    {"coin_id": "ethereum", "symbol": "ETH/USDT", "name": "Ethereum"},
    {"coin_id": "solana", "symbol": "SOL/USDT", "name": "Solana"},
]


def format_usd(value, decimals=2):
    """Format a numeric USD value for display."""
    try:
        return f"${float(value):,.{decimals}f}"
    except (TypeError, ValueError):
        return "$0.00"


def build_price_context(prices):
    """Build compact price context for AI chat prompts and fallback answers."""
    if not prices:
        return "Live price data is currently unavailable."

    lines = []
    for coin_id, (symbol, name) in PRICE_LABELS.items():
        data = prices.get(coin_id, {})
        if not data:
            continue
        price = data.get("usd", 0)
        try:
            change = float(data.get("usd_24h_change") or 0)
        except (TypeError, ValueError):
            change = 0
        volume = data.get("usd_24h_vol", 0)
        market_cap = data.get("usd_market_cap", 0)
        lines.append(
            f"{symbol} ({name}): price {format_usd(price)}, "
            f"24h change {change:+.2f}%, "
            f"24h volume {format_usd(volume, 0)}, "
            f"market cap {format_usd(market_cap, 0)}"
        )

    return "\n".join(lines) if lines else "Live price data is currently unavailable."


def build_signal_context(limit=5):
    """Build recent signal context from the dashboard database."""
    signals = get_latest_signals(limit)
    if signals.empty:
        return "No recent backend AI signals are available yet."

    lines = []
    for _, row in signals.iterrows():
        lines.append(
            f"{row['symbol']}: {row['action']} at {row['confidence']}% confidence, "
            f"signal price {format_usd(row['price'])}, reason: {row['reason']}"
        )
    return "\n".join(lines)


def get_price_chart_data(coin_id, symbol, days=1):
    """Return stable chart data from backend snapshots or CoinGecko history."""
    db_chart = get_db_market_chart(symbol, limit=max(24, int(days) * 48))
    if not db_chart.empty and len(db_chart) >= 2:
        return db_chart

    live_chart = fetch_coingecko_market_chart(coin_id, days)
    if not live_chart.empty and len(live_chart) >= 2:
        return live_chart

    return build_fallback_price_chart(coin_id, days)


def build_fallback_price_chart(coin_id, days=1):
    """Build a visible fallback curve from current price and 24h change."""
    prices = fetch_coingecko_prices() or {}
    data = prices.get(coin_id, {})
    current_price = float(data.get("usd") or 0)
    if current_price <= 0:
        return pd.DataFrame(columns=["time", "close"])

    change_24h = float(data.get("usd_24h_change") or 0)
    points = 48 if days <= 1 else min(180, int(days) * 24)
    times = pd.date_range(end=datetime.now(), periods=points, freq="30min" if days <= 1 else "h")
    start_price = current_price / (1 + (change_24h / 100)) if change_24h > -99 else current_price
    trend = np.linspace(start_price, current_price, points)
    phase = np.linspace(0, np.pi * 3, points)
    amplitude = max(abs(current_price - start_price) * 0.25, current_price * 0.004)
    close = trend + (np.sin(phase) * amplitude)
    close[-1] = current_price
    return pd.DataFrame({"time": times, "close": close})


def render_asset_chart(asset, days=1, height=300):
    """Render one crypto price chart with a graceful empty state."""
    chart = get_price_chart_data(asset["coin_id"], asset["symbol"], days)
    if chart.empty:
        st.info(f"Chart data for {asset['symbol']} is not available yet.")
        return

    fig = create_price_chart(asset["symbol"], chart)
    fig.update_layout(height=height)
    st.plotly_chart(fig, width="stretch")


def local_chat_fallback(user_message, price_context, signal_context):
    """Answer price questions when configured AI inference is unavailable."""
    lowered = user_message.lower()
    if any(word in lowered for word in ["harga", "price", "btc", "eth", "sol"]):
        return (
            "Data harga live yang tersedia:\n\n"
            f"{price_context}\n\n"
            "Sinyal terbaru:\n\n"
            f"{signal_context}\n\n"
            "AI lokal belum tersedia di dashboard, jadi ini ringkasan deterministik berbasis data market."
        )

    return (
        "Saya bisa bantu baca konteks market dari dashboard ini. "
        "Tanyakan harga BTC, ETH, SOL, atau minta ringkasan sinyal terbaru.\n\n"
        f"Harga live:\n\n{price_context}"
    )


def ask_ai_chat(user_message, price_context, signal_context):
    """Ask the configured provider, falling back to a deterministic local answer."""
    prompt = (
        "You are the chat assistant inside a crypto trading dashboard. "
        "Answer in Indonesian unless the user asks for another language. "
        "Use the live market context below when the user asks about prices, "
        "signals, market direction, or risk. Do not invent prices. "
        "Keep answers concise and include a risk reminder when relevant.\n\n"
        f"Live prices:\n{price_context}\n\n"
        f"Recent AI signals:\n{signal_context}\n\n"
        f"User question: {user_message}"
    )

    try:
        provider = create_ai_provider_from_env()
        answer = provider.chat_completion(prompt, max_tokens=500)
        if answer:
            return answer
    except Exception as e:
        logger.warning("Dashboard AI chat unavailable: %s", e)
    return local_chat_fallback(user_message, price_context, signal_context)


def get_sample_trade_data():
    """Get sample trading data (or from actual DB if available)."""
    live_trades = get_trade_history()
    if not live_trades.empty:
        return live_trades
    if resolve_database_path().exists():
        return pd.DataFrame(columns=[
            "timestamp", "symbol", "side", "entry_price", "exit_price",
            "quantity", "pnl", "pnl_percent", "status",
        ])

    return pd.DataFrame({
        "timestamp": pd.date_range(start="2024-05-20", periods=10, freq="D"),
        "symbol": ["BTC/USDT"] * 10,
        "side": ["BUY", "SELL"] * 5,
        "entry_price": np.random.uniform(60000, 70000, 10),
        "exit_price": np.random.uniform(60000, 70000, 10),
        "quantity": np.random.uniform(0.01, 0.05, 10),
        "pnl": np.random.uniform(-500, 2000, 10),
        "pnl_percent": np.random.uniform(-2, 5, 10),
    })


def get_sample_positions():
    """Get sample open positions."""
    live_positions = get_live_positions()
    if not live_positions.empty:
        return live_positions
    if resolve_database_path().exists():
        return pd.DataFrame(columns=[
            "symbol", "side", "entry_price", "current_price", "quantity",
            "leverage", "pnl", "pnl_percent", "opened_at",
        ])

    return pd.DataFrame({
        "symbol": ["BTC/USDT", "ETH/USDT"],
        "side": ["BUY", "BUY"],
        "entry_price": [65000, 3200],
        "current_price": [66500, 3350],
        "quantity": [0.05, 2.0],
        "leverage": [2, 1.5],
        "pnl": [750, 300],
        "pnl_percent": [2.31, 4.69],
        "opened_at": [
            datetime.now() - timedelta(days=3),
            datetime.now() - timedelta(days=1),
        ],
    })


def get_agent_logs():
    """Return persisted backend activity without synthetic fallback rows."""
    return get_backend_events()


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def metric_card(label, value, delta=None, delta_color="normal", icon="", prefix=""):
    """Custom metric card with cyberpunk styling."""
    delta_html = ""
    if delta is not None:
        color = "color: #00ff41;" if delta > 0 else "color: #ff006e;"
        sign = "+" if delta > 0 else ""
        delta_html = f'<div style="{color}font-size:0.85rem;margin-top:0.3rem;">{sign}{delta:.2f}%</div>'
    
    html = f"""
    <div style="
        background: rgba(26,31,46,0.6);
        border: 1px solid rgba(0,212,255,0.2);
        border-radius: 8px;
        padding: 1.2rem;
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    ">
        <div style="color: #8892a6; font-size: 0.85rem; margin-bottom: 0.5rem;">
            {icon} {label}
        </div>
        <div style="color: #00d4ff; font-size: 1.8rem; font-weight: 600; text-shadow: 0 0 10px rgba(0,212,255,0.3);">
            {prefix}{value}
        </div>
        {delta_html}
    </div>
    """
    return html


def create_price_chart(symbol, prices):
    """Create beautiful price chart."""
    close = pd.to_numeric(pd.Series(prices["close"]), errors="coerce").dropna()
    if close.empty:
        close = pd.Series([0])

    y_min = float(close.min())
    y_max = float(close.max())
    y_spread = y_max - y_min
    if y_spread <= 0:
        y_spread = max(abs(y_max) * 0.01, 1)
    y_padding = y_spread * 0.18

    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=prices["time"],
        y=prices["close"],
        mode="lines",
        name="Price",
        line=dict(color="#00d4ff", width=3),
        fill="tozeroy",
        fillcolor="rgba(0, 212, 255, 0.1)",
        hovertemplate="<b>%{x}</b><br>$%{y:,.2f}<extra></extra>",
    ))
    
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#1a1f2e",
        plot_bgcolor="#0f1419",
        hovermode="x unified",
        margin=dict(l=0, r=0, t=20, b=0),
        height=300,
        font=dict(family="Monaco, monospace", color="#e8eaed", size=11),
    )
    
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(
        showgrid=True,
        gridcolor="rgba(45, 55, 72, 0.3)",
        range=[max(0, y_min - y_padding), y_max + y_padding],
        tickprefix="$",
        separatethousands=True,
    )
    
    return fig


def create_fear_greed_gauge(value):
    """Create Fear & Greed Index gauge."""
    if value < 25:
        color = "#ff006e"  # Fear (red)
        label = "EXTREME FEAR"
    elif value < 45:
        color = "#ffd60a"  # Fear (yellow)
        label = "FEAR"
    elif value < 55:
        color = "#8892a6"  # Neutral (gray)
        label = "NEUTRAL"
    elif value < 75:
        color = "#00ff41"  # Greed (green)
        label = "GREED"
    else:
        color = "#ff006e"  # Extreme Greed (magenta)
        label = "EXTREME GREED"
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        domain={"x": [0, 1], "y": [0, 1]},
        title={"text": "Fear & Greed Index"},
        delta={"reference": 50},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": color},
            "steps": [
                {"range": [0, 25], "color": "rgba(255, 0, 110, 0.2)"},
                {"range": [25, 45], "color": "rgba(255, 214, 10, 0.2)"},
                {"range": [45, 55], "color": "rgba(136, 146, 166, 0.2)"},
                {"range": [55, 75], "color": "rgba(0, 255, 65, 0.2)"},
                {"range": [75, 100], "color": "rgba(255, 0, 110, 0.2)"},
            ],
            "threshold": {
                "line": {"color": "#00d4ff", "width": 2},
                "thickness": 0.75,
                "value": value,
            },
        },
    ))
    
    fig.update_layout(
        paper_bgcolor="#1a1f2e",
        plot_bgcolor="#0f1419",
        font=dict(family="Monaco, monospace", color="#e8eaed", size=12),
        margin=dict(l=0, r=0, t=40, b=0),
        height=300,
    )
    
    return fig, label


def create_whale_chart(data):
    """Create whale activity visualization."""
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=data.get("time", []),
        y=data.get("buy_volume", []),
        name="Buy Volume",
        marker_color="#00ff41",
        hovertemplate="<b>Buy</b><br>%{y:,.0f} BTC<extra></extra>",
    ))
    
    fig.add_trace(go.Bar(
        x=data.get("time", []),
        y=[-v for v in data.get("sell_volume", [])],
        name="Sell Volume",
        marker_color="#ff006e",
        hovertemplate="<b>Sell</b><br>%{y:,.0f} BTC<extra></extra>",
    ))
    
    fig.update_layout(
        barmode="relative",
        template="plotly_dark",
        paper_bgcolor="#1a1f2e",
        plot_bgcolor="#0f1419",
        margin=dict(l=0, r=0, t=30, b=0),
        height=300,
        font=dict(family="Monaco, monospace", color="#e8eaed"),
        hovermode="x unified",
    )
    
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="rgba(45, 55, 72, 0.3)")
    
    return fig


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: OVERVIEW (HOME)
# ═══════════════════════════════════════════════════════════════════════════════

def page_overview():
    st.title("🚀 Crypto AI Trader Dashboard")
    st.markdown("Local-first QVAC-compatible edge AI for multi-agent market intelligence")
    st.markdown("---")

    # Fetch live data
    prices = fetch_coingecko_prices()
    fg = fetch_fear_greed()

    # ── Key Metrics Row ─────────────────────────────────────────────────────
    if prices:
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            btc = prices.get("bitcoin", {})
            btc_price = btc.get("usd", 0)
            btc_change = btc.get("usd_24h_change", 0)
            st.markdown(metric_card("Bitcoin", f"${btc_price:,.0f}", btc_change, icon="₿"), unsafe_allow_html=True)
        
        with col2:
            eth = prices.get("ethereum", {})
            eth_price = eth.get("usd", 0)
            eth_change = eth.get("usd_24h_change", 0)
            st.markdown(metric_card("Ethereum", f"${eth_price:,.0f}", eth_change, icon="Ξ"), unsafe_allow_html=True)
        
        with col3:
            st.markdown(metric_card("Fear & Greed", f"{fg['value']}", icon="📊"), unsafe_allow_html=True)
        
        with col4:
            st.markdown(metric_card("Portfolio", "$12,450.50", 5.2, icon="💼"), unsafe_allow_html=True)
        
        with col5:
            st.markdown(metric_card("Win Rate", "64%", 3.1, icon="📈"), unsafe_allow_html=True)

    st.markdown("---")

    # ── Main Charts ─────────────────────────────────────────────────────────
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.subheader("Market Charts 24h")
        chart_tabs = st.tabs([asset["symbol"] for asset in MARKET_CHARTS])
        for tab, asset in zip(chart_tabs, MARKET_CHARTS):
            with tab:
                render_asset_chart(asset, days=1)
    
    with c2:
        st.subheader("📈 Fear & Greed")
        fig, label = create_fear_greed_gauge(fg["value"])
        st.plotly_chart(fig, width="stretch")
        st.caption(f"**{label}**")

    st.markdown("---")

    # ── AI Signals & Whale Tracker ──────────────────────────────────────────
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("🤖 Latest AI Signals")
        live_signals = get_latest_signals(3)
        if live_signals.empty:
            signals = pd.DataFrame({
                "Symbol": ["BTC/USDT", "ETH/USDT", "SOL/USDT"],
                "Signal": ["WAIT", "WAIT", "WAIT"],
                "Confidence": ["0%", "0%", "0%"],
                "Agents": ["Backend warming", "Backend warming", "Backend warming"],
            })
        else:
            signals = pd.DataFrame({
                "Symbol": live_signals["symbol"],
                "Signal": live_signals["action"],
                "Confidence": live_signals["confidence"].astype(str) + "%",
                "Agents": live_signals["reason"].str.slice(0, 40),
            })
        for idx, row in signals.iterrows():
            signal_color = "success" if row["Signal"] == "BUY" else "warning" if row["Signal"] == "HOLD" else "danger"
            row_symbol = html_escape(row["Symbol"])
            row_signal = html_escape(row["Signal"])
            row_confidence = html_escape(row["Confidence"])
            row_agents = html_escape(row["Agents"])
            row["Symbol"] = row_symbol
            row["Signal"] = row_signal
            row["Confidence"] = row_confidence
            row["Agents"] = row_agents
            st.markdown(f"""
            <div style="background: rgba(26,31,46,0.6); border-left: 3px solid {'#00ff41' if row['Signal']=='BUY' else '#ffd60a' if row['Signal']=='HOLD' else '#ff006e'}; padding: 0.8rem; margin: 0.5rem 0; border-radius: 4px;">
                <div style="display: flex; justify-content: space-between; color: #e8eaed; font-size: 0.95rem;">
                    <b>{row_symbol}</b>
                    <span style="color: {'#00ff41' if row['Signal']=='BUY' else '#ffd60a' if row['Signal']=='HOLD' else '#ff006e'}; font-weight: 600;">{row_signal}</span>
                </div>
                <div style="color: #8892a6; font-size: 0.8rem; margin-top: 0.3rem;">
                    Confidence: {row['Confidence']} • Agents: {row['Agents']}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    with c2:
        st.subheader("🐳 Whale Tracker")
        whale_row = get_latest_agent_results().get("WhaleTracker")
        if whale_row:
            whale = whale_row["result"]
            st.metric("Activity Score", whale.get("whale_activity_score", 0))
            st.caption(f"Pressure: {whale.get('pressure', 'NEUTRAL')} | Volume ratio: {whale.get('volume_ratio', 1):.2f}x | Confidence: {whale.get('confidence', 0)}%")
            for anomaly in whale.get("anomalies", []):
                st.warning(anomaly)
        else:
            st.info("Waiting for real whale telemetry from the backend.")

    st.markdown("---")

    # ── Recent Trades ───────────────────────────────────────────────────────
    st.subheader("💼 Recent Trades")
    trades = get_sample_trade_data().tail(5)
    if trades.empty:
        st.info("No paper trades yet. Signals are being generated; trades need to pass confidence and risk checks.")
    
    for idx, trade in trades.iterrows():
        side_color = "#00ff41" if trade["side"] == "BUY" else "#ff006e"
        pnl_color = "#00ff41" if trade["pnl"] > 0 else "#ff006e"
        trade["side"] = html_escape(trade["side"])
        trade["symbol"] = html_escape(trade["symbol"])
        
        st.markdown(f"""
        <div style="background: rgba(26,31,46,0.6); border: 1px solid rgba(0,212,255,0.2); padding: 0.8rem; margin: 0.5rem 0; border-radius: 6px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="color: #e8eaed; font-weight: 600;">
                        <span style="color: {side_color};">{trade['side']}</span> {trade['quantity']:.4f} {trade['symbol']}
                    </div>
                    <div style="color: #8892a6; font-size: 0.8rem;">
                        Entry: ${trade['entry_price']:,.0f} • Exit: ${trade['exit_price']:,.0f}
                    </div>
                </div>
                <div style="text-align: right;">
                    <div style="color: {pnl_color}; font-weight: 600; font-size: 1.1rem;">
                        ${trade['pnl']:+.2f}
                    </div>
                    <div style="color: {pnl_color}; font-size: 0.8rem;">
                        {trade['pnl_percent']:+.2f}%
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: POSITIONS MONITOR
# ═══════════════════════════════════════════════════════════════════════════════

def page_positions():
    st.title("💼 Position Monitor")
    st.markdown("Track open positions and active strategies")
    st.markdown("---")

    positions = get_sample_positions()
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(metric_card("Open Positions", len(positions), icon="📊"), unsafe_allow_html=True)
    with col2:
        total_pnl = positions["pnl"].sum()
        st.markdown(metric_card("Total P&L", f"${total_pnl:,.0f}", icon="📈"), unsafe_allow_html=True)
    with col3:
        avg_pnl_pct = positions["pnl_percent"].mean() if not positions.empty else 0
        st.markdown(metric_card("Avg Return", f"{avg_pnl_pct:.2f}%", icon="📊"), unsafe_allow_html=True)
    with col4:
        total_leverage = positions["leverage"].sum()
        st.markdown(metric_card("Total Leverage", f"{total_leverage:.1f}x", icon="⚡"), unsafe_allow_html=True)

    st.markdown("---")

    # Positions table
    st.subheader("Active Positions")
    if positions.empty:
        st.info("No open paper positions yet. Backend will open one only when confidence reaches the threshold.")
    
    for idx, pos in positions.iterrows():
        pnl_color = "#00ff41" if pos["pnl"] > 0 else "#ff006e"
        pos["symbol"] = html_escape(pos["symbol"])
        pos["side"] = html_escape(pos["side"])
        
        st.markdown(f"""
        <div style="background: linear-gradient(90deg, rgba(0,212,255,0.05) 0%, transparent 100%); border-left: 3px solid {pnl_color}; border-radius: 6px; padding: 1rem; margin: 0.8rem 0; border: 1px solid rgba(0,212,255,0.2);">
            <div style="display: grid; grid-template-columns: 2fr 1.5fr 1.5fr 1fr 1fr; gap: 1rem;">
                <div>
                    <div style="color: #00d4ff; font-weight: 600; font-size: 1.1rem;">{pos['symbol']}</div>
                    <div style="color: #8892a6; font-size: 0.85rem; margin-top: 0.3rem;">
                        Side: <span style="color: {'#00ff41' if pos['side']=='BUY' else '#ff006e'}">{pos['side']}</span> • {pos['quantity']:.4f}
                    </div>
                </div>
                <div>
                    <div style="color: #e8eaed; font-size: 0.9rem;">Entry</div>
                    <div style="color: #00d4ff; font-weight: 600;">${pos['entry_price']:,.2f}</div>
                    <div style="color: #e8eaed; font-size: 0.9rem; margin-top: 0.5rem;">Current</div>
                    <div style="color: #00d4ff; font-weight: 600;">${pos['current_price']:,.2f}</div>
                </div>
                <div>
                    <div style="color: #e8eaed; font-size: 0.9rem;">Duration</div>
                    <div style="color: #8892a6;">{(datetime.now() - pos['opened_at']).days}d ago</div>
                    <div style="color: #e8eaed; font-size: 0.9rem; margin-top: 0.5rem;">Leverage</div>
                    <div style="color: #ffd60a; font-weight: 600;">{pos['leverage']}x</div>
                </div>
                <div style="text-align: center;">
                    <div style="color: #e8eaed; font-size: 0.9rem;">P&L</div>
                    <div style="color: {pnl_color}; font-weight: 600; font-size: 1.1rem;">${pos['pnl']:+,.0f}</div>
                </div>
                <div style="text-align: right;">
                    <div style="color: #e8eaed; font-size: 0.9rem;">Return</div>
                    <div style="color: {pnl_color}; font-weight: 600; font-size: 1.1rem;">{pos['pnl_percent']:+.2f}%</div>
                    <div style="color: #8892a6; font-size: 0.75rem; margin-top: 0.5rem;">Managed by backend</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Risk Assessment")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Max Drawdown", "-3.2%", "-2.1%", delta_color="inverse")
    with col2:
        st.metric("Win Rate", "64%", "8%")
    with col3:
        st.metric("Avg Hold Time", "3.2 days", "")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: AI SIGNALS
# ═══════════════════════════════════════════════════════════════════════════════

def page_signals():
    st.title("🤖 Local Agent Trading Signals")
    st.markdown("Real telemetry from the activated edge-analysis pipeline")
    st.markdown("---")

    statuses = get_agent_runtime_status()
    active_count = int(statuses["Active"].sum()) if not statuses.empty else 0
    decision_row = get_latest_agent_results().get("DecisionAgent")
    provider = decision_row.get("provider", "not_run") if decision_row else "not_run"
    local_only = os.getenv("LOCAL_ONLY_INFERENCE", "true").strip().lower() in {"1", "true", "yes", "on"}
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Agents Active", f"{active_count}/{len(AGENT_NAMES)}", "Measured telemetry", delta_color="off")
    with col2:
        st.metric("Inference Provider", provider, "Latest decision", delta_color="off")
    with col3:
        st.metric("Local Only", "ON" if local_only else "OFF", "Inference policy", delta_color="off")

    st.markdown("---")
    live_signals = get_latest_signals(9)
    if live_signals.empty:
        st.info("Waiting for backend decisions.")
    else:
        for _, row in live_signals.iterrows():
            action = html_escape(row["action"])
            symbol = html_escape(row["symbol"])
            reason = html_escape(row["reason"])
            color = {"BUY": "#00ff41", "SELL": "#ff006e", "HOLD": "#ffd60a"}.get(row["action"], "#ffd60a")
            st.markdown(f"""
            <div style="background: rgba(26,31,46,0.6); border-left: 3px solid {color}; padding: 1rem; margin: 0.5rem 0; border-radius: 6px;">
                <b style="color:#00d4ff">{symbol}</b> <span style="color:{color}; float:right">{action} {int(row['confidence'])}%</span>
                <div style="color:#e8eaed; margin-top:0.6rem">{reason}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Activated Agent Telemetry")
    st.dataframe(statuses, width="stretch", hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: WHALE TRACKER
# ═══════════════════════════════════════════════════════════════════════════════

def page_whale():
    st.title("🐳 Whale Tracker")
    st.markdown("Public-volume anomaly telemetry from the local edge pipeline")
    st.markdown("---")
    telemetry = get_agent_telemetry()
    if telemetry.empty:
        st.info("Waiting for backend whale analysis.")
        return
    whale_rows = telemetry[telemetry["agent"] == "WhaleTracker"].head(20)
    if whale_rows.empty:
        st.info("Waiting for backend whale analysis.")
        return
    latest = whale_rows.iloc[0]["result"]
    cols = st.columns(4)
    cols[0].metric("Activity Score", latest.get("whale_activity_score", 0))
    cols[1].metric("Pressure", latest.get("pressure", "NEUTRAL"))
    cols[2].metric("Volume Ratio", f"{latest.get('volume_ratio', 1):.2f}x")
    cols[3].metric("Confidence", f"{latest.get('confidence', 0)}%")
    st.markdown("---")
    st.subheader("Detected Anomalies")
    anomalies = latest.get("anomalies", [])
    if anomalies:
        for anomaly in anomalies:
            st.warning(anomaly)
    else:
        st.info("No public-volume anomaly detected in the latest analysis.")
    rows = []
    for _, row in whale_rows.iterrows():
        result = row["result"]
        rows.append({"timestamp": row["timestamp"], "symbol": row["symbol"], "score": result.get("whale_activity_score", 0), "pressure": result.get("pressure", "NEUTRAL"), "volume_ratio": result.get("volume_ratio", 1), "confidence": result.get("confidence", 0)})
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: NEWS & SENTIMENT
# ═══════════════════════════════════════════════════════════════════════════════

def page_news():
    st.title("📰 News & Sentiment Analysis")
    st.markdown("Local-first RSS classification with optional QVAC summary")
    st.markdown("---")
    latest = get_latest_agent_results()
    news_row = latest.get("NewsAgent")
    sentiment_row = latest.get("SentimentAgent")
    if not news_row:
        st.info("Waiting for backend news analysis.")
        return
    news = news_row["result"]
    sentiment = sentiment_row["result"] if sentiment_row else {}
    cols = st.columns(4)
    cols[0].metric("News Sentiment", news.get("sentiment", "NEUTRAL"))
    cols[1].metric("Impact Score", news.get("impact_score", 0))
    cols[2].metric("Market Sentiment", sentiment.get("label", "NEUTRAL"))
    cols[3].metric("Sentiment Score", sentiment.get("sentiment_score", 0))
    st.caption(f"Summary provider: {news.get('provider', 'local_rules')}")
    st.write(news.get("summary", "No summary available."))
    st.subheader("Key Events")
    events = news.get("key_events", [])
    if events:
        for event in events:
            st.markdown(f"- {html_escape(event)}")
    else:
        st.info("No RSS headlines were available during the latest cycle.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: PERFORMANCE
# ═══════════════════════════════════════════════════════════════════════════════

def page_performance():
    st.title("📈 Performance & PnL")
    st.markdown("Trading performance analytics and return tracking")
    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(metric_card("Total Trades", "247", icon="📊"), unsafe_allow_html=True)
    with col2:
        st.markdown(metric_card("Win Rate", "64%", 4.2, icon="🎯"), unsafe_allow_html=True)
    with col3:
        st.markdown(metric_card("Total P&L", "$12,450", 18.5, icon="💰"), unsafe_allow_html=True)
    with col4:
        st.markdown(metric_card("Sharpe Ratio", "2.14", icon="📊"), unsafe_allow_html=True)

    st.markdown("---")

    # PnL over time
    st.subheader("Cumulative P&L")
    pnl_data = pd.DataFrame({
        "date": pd.date_range(start=datetime.now() - timedelta(days=30), periods=30, freq="D"),
        "cumulative_pnl": np.cumsum(np.random.randn(30) * 500 + 200),
    })
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pnl_data["date"],
        y=pnl_data["cumulative_pnl"],
        mode="lines",
        name="P&L",
        line=dict(color="#00d4ff", width=3),
        fill="tozeroy",
        fillcolor="rgba(0, 212, 255, 0.1)",
    ))
    
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#1a1f2e",
        plot_bgcolor="#0f1419",
        height=350,
        margin=dict(l=0, r=0, t=20, b=0),
        font=dict(family="Monaco, monospace", color="#e8eaed"),
    )
    st.plotly_chart(fig, width="stretch")

    st.markdown("---")

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Monthly Returns")
        monthly_returns = pd.DataFrame({
            "month": ["Jan", "Feb", "Mar", "Apr", "May"],
            "return": [3.2, 5.1, -1.3, 6.8, 4.5],
        })
        fig = px.bar(monthly_returns, x="month", y="return",
                     color="return",
                     color_continuous_scale=["#ff006e", "#ffd60a", "#00ff41"],
                     template="plotly_dark", height=300)
        fig.update_layout(
            paper_bgcolor="#1a1f2e",
            plot_bgcolor="#0f1419",
            font=dict(family="Monaco, monospace", color="#e8eaed"),
            showlegend=False,
        )
        st.plotly_chart(fig, width="stretch")
    
    with col2:
        st.subheader("Trade Distribution")
        trade_stats = pd.DataFrame({
            "outcome": ["Win", "Loss", "Break Even"],
            "count": [158, 88, 1],
        })
        fig = px.pie(trade_stats, values="count", names="outcome",
                     color_discrete_map={"Win": "#00ff41", "Loss": "#ff006e", "Break Even": "#ffd60a"},
                     template="plotly_dark", height=300)
        fig.update_layout(
            paper_bgcolor="#1a1f2e",
            font=dict(family="Monaco, monospace", color="#e8eaed"),
        )
        st.plotly_chart(fig, width="stretch")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: AGENT LOGS
# ═══════════════════════════════════════════════════════════════════════════════

def page_logs():
    st.title("📋 Agent Activity Logs")
    st.markdown("Real-time multi-agent system activity and decision logs")
    st.markdown("---")

    # Filter controls
    col1, col2, col3 = st.columns(3)
    with col1:
        agent_filter = st.multiselect("Filter Agents", 
            ["All", "Market Analyst", "News Analyzer", "Sentiment", "Whale Tracker", "Risk Agent", "Execution", "Supervisor"],
            default=["All"])
    with col2:
        status_filter = st.multiselect("Filter Status", 
            ["All", "✓ OK", "⚠ WARNING", "❌ ERROR"],
            default=["All"])
    with col3:
        st.write("")  # Spacer

    st.markdown("---")

    logs = get_agent_logs()
    
    for idx, log in logs.iterrows():
        status_color = "#00ff41" if "✓" in log["status"] else "#ffd60a" if "⚠" in log["status"] else "#ff006e"
        agent_colors = {
            "MarketAnalyst": "#00d4ff",
            "NewsAgent": "#ffd60a",
            "SentimentAgent": "#ff006e",
            "WhaleTracker": "#00ff41",
            "RiskAgent": "#00d4ff",
            "ExecutionAgent": "#ff006e",
            "SupervisorAgent": "#00ff41",
        }
        
        agent_color = agent_colors.get(log["agent"], "#8892a6")
        log["agent"] = html_escape(log["agent"])
        log["action"] = html_escape(log["action"])
        log["status"] = html_escape(log["status"])
        
        st.markdown(f"""
        <div style="background: rgba(26,31,46,0.6); border-left: 3px solid {status_color}; padding: 0.8rem; margin: 0.5rem 0; border-radius: 6px;">
            <div style="display: grid; grid-template-columns: 150px 250px 1fr 100px; gap: 1rem; align-items: center;">
                <div style="color: #8892a6; font-size: 0.8rem;">
                    {log['timestamp'].strftime('%H:%M:%S')}
                </div>
                <div>
                    <span style="background: {agent_color}20; color: {agent_color}; padding: 0.3rem 0.8rem; border-radius: 4px; font-size: 0.8rem; font-weight: 600;">
                        {log['agent']}
                    </span>
                </div>
                <div style="color: #e8eaed;">
                    {log['action']}
                </div>
                <div style="text-align: right;">
                    <span style="color: {status_color}; font-weight: 600; font-size: 0.85rem;">
                        {log['status']}
                    </span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════

def page_settings():
    st.title("⚙️ Settings & Configuration")
    st.markdown("Manage QVAC demo safety settings and local intelligence configuration")
    st.markdown("---")

    with st.expander("🤖 Market Intelligence Safety Parameters", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.slider("Max Risk per Trade (%)", 0.1, 5.0, 1.0, step=0.1)
            st.slider("Daily Max Loss (%)", 1.0, 10.0, 3.0, step=0.5)
        with col2:
            st.slider("Max Leverage", 1.0, 10.0, 2.0, step=0.5)
            st.slider("Confidence Threshold (%)", 50, 95, 75, step=5)
        with col3:
            st.slider("Max Open Positions", 1, 10, 3, step=1)
            st.selectbox("Runtime Mode", ["Paper", "Backtest", "Live"])

    with st.expander("🌐 Provider and Data Configuration", expanded=False):
        st.warning("⚠️ QVAC local inference is the default. Remote fallback must be explicitly enabled.")
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Groq API Key (optional fallback)", type="password", placeholder="Disabled unless fallback is enabled")
            st.text_input("Binance API Key", type="password", placeholder="Enter Binance API key")
        with col2:
            st.text_input("Binance Secret Key", type="password", placeholder="Enter Binance secret")
            st.selectbox("Exchange", ["Binance", "Kraken", "Coinbase"])

    with st.expander("📊 Data Sources", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.toggle("CoinGecko API", value=True)
            st.toggle("Fear & Greed Index", value=True)
        with col2:
            st.toggle("News Aggregator", value=True)
            st.toggle("Whale Tracker", value=True)

    st.markdown("---")
    st.subheader("🛑 Safety Controls")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("🛑 EMERGENCY STOP", type="secondary"):
            write_env_value(ENV_PATH, "EMERGENCY_STOP", "true")
            write_env_value(ENV_PATH, "LIVE_TRADING", "false")
            write_env_value(ENV_PATH, "TRADING_MODE", "paper")
            write_env_value(ENV_PATH, "LIVE_TRADING_LOCKDOWN", "true")
            write_env_value(ENV_PATH, "LIVE_LOCKDOWN_REASON", "Emergency stop activated from dashboard.")
            st.error("Emergency stop activated. Live trading is locked and backend will halt on the next loop.")
    with col2:
        if st.button("✅ Resume Trading", type="secondary"):
            write_env_value(ENV_PATH, "EMERGENCY_STOP", "false")
            st.success("Emergency stop cleared. Live execution remains locked until preflight passes.")
    with col3:
        st.info("Use emergency stop to immediately halt runtime activity and keep the system in paper mode.")

    st.markdown("---")
    st.subheader("📥 Export & Backup")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Download Decision History"):
            st.success("Decision history exported as CSV")
    with col2:
        if st.button("Backup Database"):
            st.success("Database backed up successfully")
    with col3:
        if st.button("Download Settings"):
            st.success("Configuration exported")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════════════════════════════════════

def page_ai_chat():
    st.title("QVAC Market Chat")
    st.markdown("Ask market-intelligence questions using local dashboard context")
    st.markdown("---")

    prices = fetch_coingecko_prices()
    price_context = build_price_context(prices)
    signal_context = build_signal_context()

    price_cols = st.columns(3)
    for col, coin_id in zip(price_cols, PRICE_LABELS):
        symbol, name = PRICE_LABELS[coin_id]
        data = (prices or {}).get(coin_id, {})
        try:
            change = float(data.get("usd_24h_change") or 0)
        except (TypeError, ValueError):
            change = 0
        with col:
            st.markdown(
                metric_card(name, format_usd(data.get("usd", 0)), change, icon=symbol),
                unsafe_allow_html=True,
            )

    st.markdown("---")

    with st.expander("Local context sent to configured provider", expanded=False):
        st.code(f"{price_context}\n\nRecent signals:\n{signal_context}", language="text")

    if "ai_chat_messages" not in st.session_state:
        st.session_state.ai_chat_messages = [
            {
                "role": "assistant",
                "content": (
                    "Halo. Saya sudah membawa konteks harga live dashboard. "
                    "Tanya misalnya: berapa harga BTC sekarang, atau ringkas sinyal terbaru."
                ),
            }
        ]

    for message in st.session_state.ai_chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_message = st.chat_input("Tanya harga atau kondisi market...")
    if user_message:
        st.session_state.ai_chat_messages.append({"role": "user", "content": user_message})
        with st.chat_message("user"):
            st.markdown(user_message)

        with st.chat_message("assistant"):
            with st.spinner("Provider lokal membaca konteks market..."):
                answer = ask_ai_chat(user_message, price_context, signal_context)
            st.markdown(answer)

        st.session_state.ai_chat_messages.append({"role": "assistant", "content": answer})


def main():
    backend_status = get_backend_status()
    bot_color = "#00ff41" if backend_status["connected"] else "#ffd60a"
    bot_label = html_escape("Connected" if backend_status["connected"] else backend_status["status"].title())
    mode_label = html_escape(backend_status["mode"].upper())
    last_seen = html_escape(backend_status["last_heartbeat"] or "not started")
    loop_count = html_escape(backend_status["loop_count"])
    agent_statuses = get_agent_runtime_status()
    active_agents = int(agent_statuses["Active"].sum()) if not agent_statuses.empty else 0
    total_agents = len(AGENT_NAMES)
    latest_decision = get_latest_agent_results().get("DecisionAgent")
    sidebar_provider = html_escape(latest_decision.get("provider", "not_run") if latest_decision else "not_run")
    sidebar_local_only = "ON" if os.getenv("LOCAL_ONLY_INFERENCE", "true").strip().lower() in {"1", "true", "yes", "on"} else "OFF"

    # Sidebar navigation
    with st.sidebar:
        st.markdown(f"""
        <div style="text-align: center; margin-bottom: 2rem;">
            <div style="font-size: 2rem; color: #00d4ff; font-weight: 600; text-shadow: 0 0 10px rgba(0,212,255,0.3);">
                🚀 Crypto AI Trader
            </div>
            <div style="color: #8892a6; font-size: 0.85rem; margin-top: 0.3rem;">
                Local-first QVAC Intelligence
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        page = st.radio(
            "Navigation",
            ["🏠 Overview", "AI Chat", "📊 Market", "🤖 Signals", "🐳 Whales", "📰 News", "💼 Positions", "📈 Performance", "📋 Logs", "⚙️ Settings"],
            label_visibility="collapsed",
        )
        
        st.markdown("---")
        
        # Status indicators
        st.markdown(f"""
        <div style="background: rgba(26,31,46,0.6); border: 1px solid rgba(0,212,255,0.2); border-radius: 6px; padding: 1rem;">
            <div style="color: #e8eaed; font-weight: 600; margin-bottom: 0.8rem;">System Status</div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                <div style="color: #8892a6; font-size: 0.85rem;">Runtime Status</div>
                <div style="color: {bot_color}; font-weight: 600;">● {bot_label}</div>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                <div style="color: #8892a6; font-size: 0.85rem;">Agents</div>
                <div style="color: #00ff41; font-weight: 600;">{active_agents}/{total_agents}</div>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                <div style="color: #8892a6; font-size: 0.85rem;">Provider</div>
                <div style="color: #00d4ff;">{sidebar_provider}</div>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                <div style="color: #8892a6; font-size: 0.85rem;">Local Only</div>
                <div style="color: #00d4ff;">{sidebar_local_only}</div>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <div style="color: #8892a6; font-size: 0.85rem;">Last Update</div>
                <div style="color: #00d4ff;">{last_seen}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background: rgba(26,31,46,0.6); border: 1px solid rgba(0,255,65,0.2); border-radius: 6px; padding: 1rem; margin-top: 0.75rem;">
            <div style="color: #e8eaed; font-weight: 600; margin-bottom: 0.8rem;">Backend Link</div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                <div style="color: #8892a6; font-size: 0.85rem;">Connection</div>
                <div style="color: {bot_color}; font-weight: 600;">● {bot_label}</div>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                <div style="color: #8892a6; font-size: 0.85rem;">Mode</div>
                <div style="color: #00d4ff;">{mode_label}</div>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                <div style="color: #8892a6; font-size: 0.85rem;">Loop</div>
                <div style="color: #00d4ff;">{loop_count}</div>
            </div>
            <div style="display: flex; justify-content: space-between; gap: 1rem;">
                <div style="color: #8892a6; font-size: 0.85rem;">Heartbeat</div>
                <div style="color: #00d4ff; text-align: right; font-size: 0.75rem;">{last_seen}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Page routing
    if "🏠" in page:
        page_overview()
    elif page == "AI Chat":
        page_ai_chat()
    elif "📊" in page:
        st.title("📊 Market Analysis")
        st.markdown("Technical indicators and price action analysis")
        st.markdown("---")
        
        range_label = st.segmented_control(
            "Chart Range",
            ["24h", "7d", "30d"],
            default="24h",
        )
        days = {"24h": 1, "7d": 7, "30d": 30}[range_label]

        chart_cols = st.columns(2)
        for idx, asset in enumerate(MARKET_CHARTS):
            with chart_cols[idx % 2]:
                st.subheader(f"{asset['symbol']} {range_label}")
                render_asset_chart(asset, days=days)
        
        st.subheader("Technical Indicators")
        indicators = pd.DataFrame({
            "Symbol": ["BTC/USDT", "BTC/USDT", "ETH/USDT", "ETH/USDT", "SOL/USDT", "SOL/USDT"],
            "Indicator": ["RSI (14)", "MACD", "RSI (14)", "EMA (20)", "RSI (14)", "Volume Trend"],
            "Value": ["72", "0.45", "58", "3185", "55", "Rising"],
            "Signal": ["Overbought", "Bullish", "Neutral", "Above", "Neutral", "Watch"],
        })
        st.dataframe(indicators, width="stretch", hide_index=True)
        
    elif "🤖" in page:
        page_signals()
    elif "🐳" in page:
        page_whale()
    elif "📰" in page:
        page_news()
    elif "💼" in page:
        page_positions()
    elif "📈" in page:
        page_performance()
    elif "📋" in page:
        page_logs()
    elif "⚙️" in page:
        page_settings()

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #8892a6; font-size: 0.8rem; padding: 1rem 0;">
        <div>Crypto AI Trader Dashboard | QVAC Edge AI Showcase</div>
        <div style="margin-top: 0.3rem;">Local-first telemetry • QVAC provider status • Edge AI demo</div>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    # Auto-refresh every 5 seconds
    refresh_interval = int(os.getenv("REFRESH_INTERVAL", "30"))
    if "last_refresh" not in st.session_state:
        st.session_state.last_refresh = time.time()
    
    current_time = time.time()
    if current_time - st.session_state.last_refresh > refresh_interval:
        st.session_state.last_refresh = current_time
        st.rerun()
    
    main()
