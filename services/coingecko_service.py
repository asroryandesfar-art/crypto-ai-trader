"""CoinGecko API service for market data."""
import asyncio
import logging
import time

import requests

logger = logging.getLogger(__name__)


class CoinGeckoService:
    def __init__(self):
        self.base_url = "https://api.coingecko.com/api/v3"
        self.binance_futures_url = "https://fapi.binance.com/fapi/v1"
        self.symbol_map = {
            "BTC/USDT": "bitcoin",
            "ETH/USDT": "ethereum",
            "SOL/USDT": "solana",
            "BNB/USDT": "binancecoin",
            "XRP/USDT": "ripple",
            "ADA/USDT": "cardano",
            "DOGE/USDT": "dogecoin",
        }
        logger.info("CoinGecko service initialized")

    async def fetch_prices(self, symbols: list[str], max_symbols: int = 50) -> dict:
        """Fetch current USD price, 24h change, market cap, and volume."""
        return await asyncio.to_thread(self._fetch_prices_sync, symbols, max_symbols)

    def _fetch_prices_sync(self, symbols: list[str], max_symbols: int = 50) -> dict:
        if self._uses_dynamic_symbols(symbols):
            return self._fetch_binance_usdt_prices(max_symbols=max_symbols)

        result = self._fetch_coingecko_prices(symbols)
        missing = [symbol for symbol in symbols if symbol not in result]
        if missing:
            result.update(self._fetch_binance_specific_prices(missing))
        return result

    @staticmethod
    def _uses_dynamic_symbols(symbols: list[str]) -> bool:
        return any(str(symbol).strip().upper() in {"ALL", "ALL_USDT", "ALL_BINANCE", "ALL_BINANCE_USDT"} for symbol in symbols)

    def _fetch_coingecko_prices(self, symbols: list[str]) -> dict:
        ids = [self.symbol_map[s] for s in symbols if s in self.symbol_map]
        if not ids:
            return {}

        params = {
            "ids": ",".join(ids),
            "vs_currencies": "usd",
            "include_market_cap": "true",
            "include_24hr_change": "true",
            "include_24hr_vol": "true",
        }
        last_error = None
        for attempt in range(3):
            try:
                response = requests.get(f"{self.base_url}/simple/price", params=params, timeout=15)
                response.raise_for_status()
                break
            except requests.RequestException as exc:
                last_error = exc
                if attempt == 2:
                    raise
                time.sleep(0.5 * (attempt + 1))
        if last_error and "response" not in locals():
            raise last_error
        by_id = response.json()
        result = {}
        for symbol in symbols:
            coin_id = self.symbol_map.get(symbol)
            if coin_id and coin_id in by_id:
                item = by_id[coin_id]
                result[symbol] = {
                    "price": float(item.get("usd") or 0),
                    "change_24h": float(item.get("usd_24h_change") or 0),
                    "market_cap": float(item.get("usd_market_cap") or 0),
                    "volume_24h": float(item.get("usd_24h_vol") or 0),
                    "source": "coingecko",
                }
        return result

    def _fetch_binance_usdt_prices(self, max_symbols: int = 50) -> dict:
        active_symbols = self._fetch_active_binance_usdt_symbols()
        tickers = self._fetch_binance_24hr_tickers()
        rows = []
        for raw_symbol, ticker in tickers.items():
            if raw_symbol not in active_symbols:
                continue
            price = self._float_or_zero(ticker.get("lastPrice"))
            if price <= 0:
                continue
            rows.append((self._float_or_zero(ticker.get("quoteVolume")), raw_symbol, ticker))

        rows.sort(reverse=True)
        selected = rows[:max_symbols]
        result = {}
        for _volume, raw_symbol, ticker in selected:
            symbol = self._format_usdt_symbol(raw_symbol)
            result[symbol] = self._ticker_to_market(symbol, ticker)
        return result

    def _fetch_binance_specific_prices(self, symbols: list[str]) -> dict:
        requested = {self._raw_usdt_symbol(symbol): symbol.upper() for symbol in symbols}
        tickers = self._fetch_binance_24hr_tickers()
        result = {}
        for raw_symbol, symbol in requested.items():
            ticker = tickers.get(raw_symbol)
            if ticker:
                result[symbol] = self._ticker_to_market(symbol, ticker)
        return result

    def _fetch_active_binance_usdt_symbols(self) -> set[str]:
        response = requests.get(f"{self.binance_futures_url}/exchangeInfo", timeout=20)
        response.raise_for_status()
        active = set()
        for item in response.json().get("symbols", []):
            if (
                item.get("status") == "TRADING"
                and item.get("quoteAsset") == "USDT"
                and item.get("contractType") == "PERPETUAL"
            ):
                active.add(str(item.get("symbol", "")).upper())
        return active

    def _fetch_binance_24hr_tickers(self) -> dict:
        response = requests.get(f"{self.binance_futures_url}/ticker/24hr", timeout=20)
        response.raise_for_status()
        return {str(item.get("symbol", "")).upper(): item for item in response.json()}

    def _ticker_to_market(self, symbol: str, ticker: dict) -> dict:
        return {
            "price": self._float_or_zero(ticker.get("lastPrice")),
            "change_24h": self._float_or_zero(ticker.get("priceChangePercent")),
            "market_cap": 0.0,
            "volume_24h": self._float_or_zero(ticker.get("quoteVolume")),
            "source": "binance_futures",
        }

    @staticmethod
    def _format_usdt_symbol(raw_symbol: str) -> str:
        raw = str(raw_symbol).upper()
        if raw.endswith("USDT"):
            return f"{raw[:-4]}/USDT"
        return raw

    @staticmethod
    def _raw_usdt_symbol(symbol: str) -> str:
        return str(symbol).upper().replace("/", "").replace(":USDT", "")

    @staticmethod
    def _float_or_zero(value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
