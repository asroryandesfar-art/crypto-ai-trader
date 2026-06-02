"""Strict live Binance Futures executor.

This module intentionally supports only one conservative behavior:
open a long on BUY, close that long on SELL, and never open shorts.
"""

import logging
import ipaddress
import json
import os
import ssl
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)
_DNS_OVERRIDE_INSTALLED = False
_DYNAMIC_SYMBOLS = {"ALL", "ALL_USDT", "ALL_BINANCE", "ALL_BINANCE_USDT"}


def _resolve_a_records_via_doh(host: str) -> list[str]:
    """Resolve Binance hosts through DoH when local DNS is intercepted."""
    endpoints = (
        "https://dns.google/resolve",
        "https://cloudflare-dns.com/dns-query",
    )
    for endpoint in endpoints:
        query = urllib.parse.urlencode({"name": host, "type": "A"})
        request = urllib.request.Request(
            f"{endpoint}?{query}",
            headers={
                "Accept": "application/dns-json",
                "User-Agent": "crypto-ai-trader/1.0",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            logger.info("DoH lookup skipped via %s for %s: %s", endpoint, host, exc)
            continue

        addresses: list[str] = []
        for answer in payload.get("Answer", []) or []:
            if answer.get("type") != 1:
                continue
            data = str(answer.get("data", "")).strip()
            try:
                parsed = ipaddress.ip_address(data)
            except ValueError:
                continue
            if isinstance(parsed, ipaddress.IPv4Address) and parsed.is_global:
                addresses.append(data)
        if addresses:
            return addresses
    return []


def _install_binance_doh_dns_override() -> None:
    """Patch urllib3 socket creation for Binance Futures when OS DNS is poisoned."""
    global _DNS_OVERRIDE_INSTALLED
    if _DNS_OVERRIDE_INSTALLED:
        return
    if os.getenv("BINANCE_DOH_DNS", "auto").strip().lower() in {"0", "false", "no", "off", "disabled"}:
        return

    host = "fapi.binance.com"
    addresses = _resolve_a_records_via_doh(host)
    if not addresses:
        return

    try:
        import urllib3.connection as urllib3_connection
        import urllib3.util.connection as urllib3_util_connection
    except Exception as exc:
        logger.info("Could not install Binance DoH DNS override: %s", exc)
        return

    original_create_connection = urllib3_util_connection.create_connection
    if getattr(original_create_connection, "_binance_doh_override", False):
        _DNS_OVERRIDE_INSTALLED = True
        return

    host_map = {host: addresses}

    def create_connection(address, *args, **kwargs):
        try:
            target_host, target_port = address
        except Exception:
            return original_create_connection(address, *args, **kwargs)

        override_addresses = host_map.get(str(target_host).lower())
        if not override_addresses:
            return original_create_connection(address, *args, **kwargs)

        last_error = None
        for override_address in override_addresses:
            try:
                return original_create_connection((override_address, target_port), *args, **kwargs)
            except OSError as exc:
                last_error = exc
        if os.getenv("BINANCE_DOH_DNS", "auto").strip().lower() == "force" and last_error is not None:
            raise last_error
        logger.info("Binance DoH DNS override failed for %s; falling back to system DNS", target_host)
        return original_create_connection(address, *args, **kwargs)

    create_connection._binance_doh_override = True
    urllib3_util_connection.create_connection = create_connection
    urllib3_connection.create_connection = create_connection
    _DNS_OVERRIDE_INSTALLED = True
    logger.info("Installed Binance DoH DNS override for %s -> %s", host, ", ".join(addresses))


class LiveExecutionError(RuntimeError):
    """Raised when a live exchange operation cannot be completed safely."""


@dataclass
class AccountSnapshot:
    free_usdt: float
    total_usdt: float


@dataclass
class LiveOrderResult:
    symbol: str
    exchange_symbol: str
    side: str
    quantity: float
    entry_price: float
    notional_usdt: float
    entry_order_id: str
    stop_loss_price: Optional[float] = None
    stop_order_id: str = ""
    take_profit_price: Optional[float] = None
    take_profit_order_id: str = ""
    close_order_id: str = ""
    realized_pnl: float = 0.0


class BinanceFuturesLiveExecutor:
    """Small CCXT wrapper with hard caps and exchange-side protective orders."""

    def __init__(
        self,
        api_key: str,
        secret_key: str,
        leverage: float,
        max_order_usdt: float,
        min_order_usdt: float,
        max_risk_per_trade: float,
        stop_loss_pct: float,
        take_profit_pct: float,
        account_type: str = "futures",
    ):
        if not api_key or not secret_key:
            raise LiveExecutionError("Binance API key and secret are required")

        self.account_type = self._normalize_account_type(account_type)
        self.is_portfolio_margin = self.account_type == "portfolio_margin"
        self.position_side = "BOTH"
        self.hedged_position_mode = False
        self.leverage = max(1, int(leverage))
        self.max_order_usdt = float(max_order_usdt)
        self.min_order_usdt = float(min_order_usdt)
        self.max_risk_per_trade = float(max_risk_per_trade)
        self.stop_loss_pct = float(stop_loss_pct)
        self.take_profit_pct = float(take_profit_pct)
        self.ca_bundle = ""
        self.exchange = self._create_exchange(api_key, secret_key)
        self._markets: dict[str, Any] = {}
        self._symbol_map: dict[str, str] = {}

    def _create_exchange(self, api_key: str, secret_key: str):
        self.ca_bundle = self._configure_ca_bundle()
        _install_binance_doh_dns_override()

        try:
            import ccxt
        except Exception as exc:  # pragma: no cover - dependency/environment guard
            raise LiveExecutionError("ccxt is required for live trading") from exc

        exchange_cls = ccxt.binance if self.is_portfolio_margin else getattr(ccxt, "binanceusdm", ccxt.binance)
        exchange = exchange_cls(
            {
                "apiKey": api_key,
                "secret": secret_key,
                "enableRateLimit": True,
                "options": {
                    "defaultType": "future",
                    "adjustForTimeDifference": True,
                    "fetchCurrencies": False,
                },
            }
        )
        if self.is_portfolio_margin:
            exchange.options["portfolioMargin"] = True
        exchange.options["fetchCurrencies"] = False
        if hasattr(exchange, "has"):
            exchange.has["fetchCurrencies"] = False
        if self.ca_bundle and hasattr(exchange, "session"):
            exchange.session.verify = self.ca_bundle
        return exchange

    @staticmethod
    def _normalize_account_type(account_type: str) -> str:
        normalized = str(account_type or "futures").strip().lower().replace("-", "_")
        aliases = {
            "future": "futures",
            "usd_m": "futures",
            "usdm": "futures",
            "portfolio": "portfolio_margin",
            "papi": "portfolio_margin",
            "pm": "portfolio_margin",
        }
        normalized = aliases.get(normalized, normalized)
        if normalized not in {"futures", "portfolio_margin"}:
            raise LiveExecutionError(f"Unsupported Binance account type: {account_type}")
        return normalized

    def _configure_ca_bundle(self) -> str:
        """Use certifi plus Windows certificate stores when available."""
        cert_paths: list[str] = []
        try:
            import certifi

            cert_paths.append(certifi.where())
        except Exception:
            pass

        bundle_path: Optional[Path] = None
        if os.name == "nt" and hasattr(ssl, "enum_certificates"):
            try:
                project_root = Path(__file__).resolve().parents[1]
                runtime_dir = project_root / "runtime"
                runtime_dir.mkdir(exist_ok=True)
                bundle_path = runtime_dir / "windows_ca_bundle.pem"
                seen: set[str] = set()
                with bundle_path.open("w", encoding="ascii", newline="\n") as bundle:
                    for cert_path in cert_paths:
                        with open(cert_path, "r", encoding="ascii") as source:
                            bundle.write(source.read())
                            bundle.write("\n")
                    for store_name in ("ROOT", "CA"):
                        for cert, encoding, _trust in ssl.enum_certificates(store_name):
                            if encoding != "x509_asn":
                                continue
                            pem = ssl.DER_cert_to_PEM_cert(cert)
                            if pem in seen:
                                continue
                            seen.add(pem)
                            bundle.write(pem)
                            bundle.write("\n")
            except Exception as exc:
                logger.info("Windows CA bundle setup skipped: %s", exc)
                bundle_path = None

        ca_bundle = str(bundle_path) if bundle_path else (cert_paths[0] if cert_paths else "")
        if ca_bundle:
            os.environ["SSL_CERT_FILE"] = ca_bundle
            os.environ["REQUESTS_CA_BUNDLE"] = ca_bundle
        return ca_bundle

    def connect(self, symbols: list[str], prepare_exchange: bool = True) -> AccountSnapshot:
        """Load markets, resolve symbols, set leverage, and fetch account balance."""
        self._markets = self.exchange.load_markets()
        if self.is_portfolio_margin:
            self._configure_portfolio_margin_mode()
        if not self._uses_dynamic_symbols(symbols):
            for symbol in symbols:
                exchange_symbol = self.resolve_symbol(symbol)
                if prepare_exchange:
                    self._prepare_symbol(exchange_symbol)
        snapshot = self.fetch_account_snapshot()
        logger.info(
            "Live preflight OK (%s): USDT free=%.2f total=%.2f max_order=%.2f leverage=%sx",
            self.account_type,
            snapshot.free_usdt,
            snapshot.total_usdt,
            self.max_order_usdt,
            self.leverage,
        )
        return snapshot

    def _configure_portfolio_margin_mode(self) -> None:
        """Read Portfolio Margin UM settings and choose the safe long-only side."""
        try:
            config = self.exchange.papiGetUmAccountConfig({"recvWindow": 10000})
        except Exception as exc:
            raise LiveExecutionError(f"Could not read Portfolio Margin UM config: {exc}") from exc

        if not config.get("canTrade", False):
            raise LiveExecutionError("Portfolio Margin UM account cannot trade")

        self.hedged_position_mode = bool(config.get("dualSidePosition", False))
        self.position_side = "LONG" if self.hedged_position_mode else "BOTH"
        logger.info(
            "Portfolio Margin UM mode detected: dualSidePosition=%s positionSide=%s",
            self.hedged_position_mode,
            self.position_side,
        )

    def fetch_open_positions(self, configured_symbols: list[str]) -> list[dict[str, Any]]:
        """Return non-zero exchange positions for configured symbols."""
        exchange_symbols = None
        if not self._uses_dynamic_symbols(configured_symbols):
            exchange_symbols = [self.resolve_symbol(symbol) for symbol in configured_symbols]
        try:
            positions = self.exchange.fetch_positions(exchange_symbols, self._portfolio_params())
        except Exception as exc:
            raise LiveExecutionError(f"Could not fetch exchange positions: {exc}") from exc

        open_positions = []
        for position in positions or []:
            contracts = self._float_or_zero(
                position.get("contracts")
                or position.get("info", {}).get("positionAmt")
            )
            if abs(contracts) > 0:
                open_positions.append(position)
        return open_positions

    def resolve_symbol(self, configured_symbol: str) -> str:
        """Resolve BTC/USDT-style config into the exact CCXT futures symbol."""
        if configured_symbol in self._markets:
            self._symbol_map[configured_symbol] = configured_symbol
            return configured_symbol

        base, quote = configured_symbol.split("/", 1)
        preferred = f"{base}/{quote}:{quote}"
        if preferred in self._markets:
            self._symbol_map[configured_symbol] = preferred
            return preferred

        for market_symbol, market in self._markets.items():
            if (
                market.get("base") == base
                and market.get("quote") == quote
                and (market.get("swap") or market.get("future"))
            ):
                self._symbol_map[configured_symbol] = market_symbol
                return market_symbol

        raise LiveExecutionError(f"Could not resolve Binance Futures symbol for {configured_symbol}")

    @staticmethod
    def _uses_dynamic_symbols(symbols: list[str]) -> bool:
        return any(str(symbol).strip().upper() in _DYNAMIC_SYMBOLS for symbol in symbols)

    def _prepare_symbol(self, exchange_symbol: str) -> None:
        """Best-effort margin/leverage setup; already-set errors are non-fatal."""
        if not self.is_portfolio_margin:
            try:
                self.exchange.set_margin_mode("ISOLATED", exchange_symbol)
            except Exception as exc:
                logger.info("Margin mode setup skipped for %s: %s", exchange_symbol, exc)

        try:
            self.exchange.set_leverage(self.leverage, exchange_symbol, self._portfolio_params())
        except Exception as exc:
            raise LiveExecutionError(f"Could not set leverage for {exchange_symbol}: {exc}") from exc

    def fetch_account_snapshot(self) -> AccountSnapshot:
        balance = self.exchange.fetch_balance(self._portfolio_params())
        usdt = balance.get("USDT") or {}
        free = self._float_or_zero(usdt.get("free") or balance.get("free", {}).get("USDT"))
        total = self._float_or_zero(usdt.get("total") or balance.get("total", {}).get("USDT"))
        return AccountSnapshot(free_usdt=free, total_usdt=total)

    def calculate_order_notional(self, free_usdt: float) -> float:
        if free_usdt <= 0:
            raise LiveExecutionError("No free USDT balance is available for live trading")
        risk_budget = free_usdt * (self.max_risk_per_trade / 100)
        risk_sized_notional = risk_budget / (self.stop_loss_pct / 100)
        margin_capped_notional = free_usdt * self.leverage * 0.90
        return min(self.max_order_usdt, risk_sized_notional, margin_capped_notional)

    def _portfolio_params(self, extra: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if self.is_portfolio_margin:
            params["portfolioMargin"] = True
        if extra:
            params.update(extra)
        return params

    def _position_order_params(self, extra: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        params = self._portfolio_params(extra)
        if self.is_portfolio_margin:
            params["positionSide"] = self.position_side
        return params

    def _closing_order_params(self, extra: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        params = self._position_order_params(extra)
        if not self.is_portfolio_margin:
            params["reduceOnly"] = True
        return params

    def open_long(self, configured_symbol: str, reference_price: float) -> LiveOrderResult:
        exchange_symbol = self.resolve_symbol(configured_symbol)
        self._prepare_symbol(exchange_symbol)
        snapshot = self.fetch_account_snapshot()
        notional = self.calculate_order_notional(snapshot.free_usdt)
        if notional < self.min_order_usdt:
            raise LiveExecutionError(
                f"Calculated live order {notional:.2f} USDT is below MIN_LIVE_ORDER_USDT={self.min_order_usdt:.2f}"
            )

        amount = self._amount_from_notional(exchange_symbol, notional, reference_price)
        entry_order: Optional[dict[str, Any]] = None
        try:
            entry_order = self.exchange.create_order(
                exchange_symbol,
                "MARKET",
                "buy",
                amount,
                None,
                self._position_order_params({
                    "newOrderRespType": "RESULT",
                    "newClientOrderId": self._client_order_id("entry", configured_symbol),
                }),
            )
            entry_price = self._order_average(entry_order) or float(reference_price)
            stop_loss_price = self._price_to_precision(
                exchange_symbol, entry_price * (1 - self.stop_loss_pct / 100)
            )
            stop_order = self.exchange.create_order(
                exchange_symbol,
                "STOP_MARKET",
                "sell",
                amount,
                None,
                self._closing_order_params({
                    "stopPrice": stop_loss_price,
                    "workingType": "MARK_PRICE",
                    "newClientOrderId": self._client_order_id("stop", configured_symbol),
                }),
            )

            take_profit_price = None
            take_profit_order_id = ""
            if self.take_profit_pct > 0:
                take_profit_price = self._price_to_precision(
                    exchange_symbol, entry_price * (1 + self.take_profit_pct / 100)
                )
                try:
                    take_profit_order = self.exchange.create_order(
                        exchange_symbol,
                        "TAKE_PROFIT_MARKET",
                        "sell",
                        amount,
                        None,
                        self._closing_order_params({
                            "stopPrice": take_profit_price,
                            "workingType": "MARK_PRICE",
                            "newClientOrderId": self._client_order_id("take", configured_symbol),
                        }),
                    )
                    take_profit_order_id = str(take_profit_order.get("id") or "")
                except Exception as exc:
                    logger.warning("Take-profit order failed for %s; stop-loss remains active: %s", exchange_symbol, exc)

            return LiveOrderResult(
                symbol=configured_symbol,
                exchange_symbol=exchange_symbol,
                side="BUY",
                quantity=amount,
                entry_price=entry_price,
                notional_usdt=amount * entry_price,
                entry_order_id=str(entry_order.get("id") or ""),
                stop_loss_price=stop_loss_price,
                stop_order_id=str(stop_order.get("id") or ""),
                take_profit_price=take_profit_price,
                take_profit_order_id=take_profit_order_id,
            )
        except Exception as exc:
            if entry_order is not None:
                self._emergency_reduce_only_close(exchange_symbol, amount)
            raise LiveExecutionError(f"Live BUY failed for {exchange_symbol}: {exc}") from exc

    def close_long(
        self,
        configured_symbol: str,
        quantity: float,
        entry_price: float,
        stop_order_id: str = "",
        take_profit_order_id: str = "",
    ) -> LiveOrderResult:
        exchange_symbol = self.resolve_symbol(configured_symbol)
        amount = self._amount_to_precision(exchange_symbol, quantity)
        order = self.exchange.create_order(
            exchange_symbol,
            "MARKET",
            "sell",
            amount,
            None,
            self._closing_order_params({
                "newOrderRespType": "RESULT",
                "newClientOrderId": self._client_order_id("close", configured_symbol),
            }),
        )
        close_price = self._order_average(order) or float(entry_price)
        self._cancel_if_open(stop_order_id, exchange_symbol)
        self._cancel_if_open(take_profit_order_id, exchange_symbol)
        realized_pnl = (close_price - float(entry_price)) * amount
        return LiveOrderResult(
            symbol=configured_symbol,
            exchange_symbol=exchange_symbol,
            side="SELL",
            quantity=amount,
            entry_price=close_price,
            notional_usdt=amount * close_price,
            entry_order_id="",
            close_order_id=str(order.get("id") or ""),
            realized_pnl=realized_pnl,
        )

    def _emergency_reduce_only_close(self, exchange_symbol: str, amount: float) -> None:
        try:
            self.exchange.create_order(
                exchange_symbol,
                "MARKET",
                "sell",
                amount,
                None,
                self._closing_order_params({
                    "newOrderRespType": "RESULT",
                    "newClientOrderId": self._client_order_id("emergency", exchange_symbol),
                }),
            )
        except Exception as close_exc:
            logger.critical("Emergency reduce-only close failed for %s: %s", exchange_symbol, close_exc)

    def _cancel_if_open(self, order_id: str, exchange_symbol: str) -> None:
        if not order_id:
            return
        try:
            self.exchange.cancel_order(order_id, exchange_symbol, self._portfolio_params({"trigger": True}))
        except Exception as exc:
            logger.info("Order cancel skipped for %s %s: %s", exchange_symbol, order_id, exc)

    def _amount_from_notional(self, exchange_symbol: str, notional: float, reference_price: float) -> float:
        if reference_price <= 0:
            raise LiveExecutionError("Reference price must be positive")
        amount = self._amount_to_precision(exchange_symbol, notional / reference_price)
        market = self._markets[exchange_symbol]
        min_amount = self._float_or_zero(market.get("limits", {}).get("amount", {}).get("min"))
        min_cost = self._float_or_zero(market.get("limits", {}).get("cost", {}).get("min"))
        if min_amount and amount < min_amount:
            raise LiveExecutionError(f"Order amount {amount} is below exchange minimum {min_amount}")
        if min_cost and amount * reference_price < min_cost:
            raise LiveExecutionError(f"Order notional {amount * reference_price:.2f} is below exchange minimum {min_cost}")
        return amount

    def _amount_to_precision(self, exchange_symbol: str, amount: float) -> float:
        precise = self.exchange.amount_to_precision(exchange_symbol, amount)
        parsed = float(precise)
        if parsed <= 0:
            raise LiveExecutionError(f"Rounded amount for {exchange_symbol} is zero")
        return parsed

    def _price_to_precision(self, exchange_symbol: str, price: float) -> float:
        precise = self.exchange.price_to_precision(exchange_symbol, price)
        parsed = float(precise)
        if parsed <= 0:
            raise LiveExecutionError(f"Rounded price for {exchange_symbol} is zero")
        return parsed

    def _order_average(self, order: dict[str, Any]) -> Optional[float]:
        for key in ("average", "avgPrice", "price"):
            value = order.get(key)
            if value:
                parsed = self._float_or_zero(value)
                if parsed > 0:
                    return parsed
        info = order.get("info") or {}
        for key in ("avgPrice", "price"):
            value = info.get(key)
            if value:
                parsed = self._float_or_zero(value)
                if parsed > 0:
                    return parsed
        return None

    def _client_order_id(self, prefix: str, symbol: str) -> str:
        clean_symbol = "".join(ch for ch in symbol.upper() if ch.isalnum())[:12]
        return f"cat_{prefix}_{clean_symbol}_{int(time.time() * 1000)}"[:36]

    @staticmethod
    def _float_or_zero(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
