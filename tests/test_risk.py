"""Tests for risk management modules."""

import pytest
from risk.position_sizing import PositionSizer
from risk.stop_loss import StopLossCalculator
from risk.take_profit import TakeProfitCalculator
from risk.daily_loss_guard import DailyLossGuard
from agents.risk_agent import RiskAgent


# ── PositionSizer ─────────────────────────────────────────────────────────────

class TestPositionSizer:
    def test_basic_notional(self):
        ps = PositionSizer(account_balance=1000, max_risk=1.0, max_notional=None)
        notional = ps.calculate_notional(stop_loss_pct=2.0, free_balance=1000, leverage=1.0)
        assert notional > 0

    def test_max_notional_caps_output(self):
        ps = PositionSizer(account_balance=100000, max_risk=5.0, max_notional=15.0)
        notional = ps.calculate_notional(stop_loss_pct=2.0, free_balance=100000, leverage=10.0)
        assert notional == pytest.approx(15.0)

    def test_zero_balance_returns_zero(self):
        ps = PositionSizer(account_balance=1000, max_risk=1.0)
        assert ps.calculate_notional(stop_loss_pct=2.0, free_balance=0) == 0.0

    def test_invalid_stop_loss_raises(self):
        ps = PositionSizer(account_balance=1000, max_risk=1.0)
        with pytest.raises(ValueError, match="positive"):
            ps.calculate_notional(stop_loss_pct=0)

    def test_negative_stop_loss_raises(self):
        ps = PositionSizer(account_balance=1000, max_risk=1.0)
        with pytest.raises(ValueError):
            ps.calculate_notional(stop_loss_pct=-1.0)

    def test_calculate_quantity_uses_price(self):
        ps = PositionSizer(account_balance=1000, max_risk=1.0, max_notional=100)
        qty = ps.calculate_quantity(price=50000.0, stop_loss_pct=2.0)
        assert qty > 0

    def test_calculate_quantity_zero_price_raises(self):
        ps = PositionSizer(account_balance=1000, max_risk=1.0)
        with pytest.raises(ValueError, match="positive"):
            ps.calculate_quantity(price=0, stop_loss_pct=2.0)

    def test_notional_without_max_cap(self):
        ps = PositionSizer(account_balance=1000, max_risk=1.0, max_notional=None)
        n = ps.calculate_notional(stop_loss_pct=2.0, free_balance=1000, leverage=1.0)
        risk_budget = 1000 * 0.01
        expected_risk_notional = risk_budget / 0.02
        margin_cap = 1000 * 1.0 * 0.90
        assert n == pytest.approx(min(expected_risk_notional, margin_cap))


# ── StopLossCalculator ────────────────────────────────────────────────────────

class TestStopLossCalculator:
    def test_buy_stop_below_entry(self):
        stop = StopLossCalculator.calculate_fixed_percent(100.0, 2.0, "BUY")
        assert stop == pytest.approx(98.0)

    def test_sell_stop_above_entry(self):
        stop = StopLossCalculator.calculate_fixed_percent(100.0, 2.0, "SELL")
        assert stop == pytest.approx(102.0)

    def test_zero_percent_returns_entry(self):
        stop = StopLossCalculator.calculate_fixed_percent(100.0, 0.0, "BUY")
        assert stop == pytest.approx(100.0)

    def test_large_percent(self):
        stop = StopLossCalculator.calculate_fixed_percent(1000.0, 50.0, "BUY")
        assert stop == pytest.approx(500.0)


# ── TakeProfitCalculator ──────────────────────────────────────────────────────

class TestTakeProfitCalculator:
    def test_buy_take_profit_above_entry(self):
        tp = TakeProfitCalculator.calculate_fixed_percent(100.0, 4.0, "BUY")
        assert tp == pytest.approx(104.0)

    def test_sell_take_profit_below_entry(self):
        tp = TakeProfitCalculator.calculate_fixed_percent(100.0, 4.0, "SELL")
        assert tp == pytest.approx(96.0)

    def test_zero_percent_returns_entry(self):
        tp = TakeProfitCalculator.calculate_fixed_percent(100.0, 0.0, "BUY")
        assert tp == pytest.approx(100.0)


# ── DailyLossGuard ────────────────────────────────────────────────────────────

class TestDailyLossGuard:
    def test_can_trade_initially(self):
        dlg = DailyLossGuard(max_loss=3.0, balance=1000)
        assert dlg.can_trade() is True

    def test_loss_limit_property(self):
        dlg = DailyLossGuard(max_loss=3.0, balance=1000)
        assert dlg.loss_limit == pytest.approx(30.0)

    def test_losses_block_trading(self):
        dlg = DailyLossGuard(max_loss=3.0, balance=1000)
        dlg.record_pnl(-30.0)
        assert dlg.can_trade() is False

    def test_profits_not_counted(self):
        dlg = DailyLossGuard(max_loss=3.0, balance=1000)
        dlg.record_pnl(100.0)
        assert dlg.realized_loss == 0.0
        assert dlg.can_trade() is True

    def test_partial_losses_allow_trading(self):
        dlg = DailyLossGuard(max_loss=3.0, balance=1000)
        dlg.record_pnl(-15.0)
        assert dlg.can_trade() is True
        assert dlg.remaining_loss_budget() == pytest.approx(15.0)

    def test_remaining_budget_at_limit_is_zero(self):
        dlg = DailyLossGuard(max_loss=3.0, balance=1000)
        dlg.record_pnl(-31.0)
        assert dlg.remaining_loss_budget() == 0.0

    def test_exact_limit_blocks_trading(self):
        dlg = DailyLossGuard(max_loss=3.0, balance=1000)
        dlg.record_pnl(-30.0)
        assert dlg.can_trade() is False

    def test_day_rollover_resets_loss(self):
        from datetime import date, timedelta
        dlg = DailyLossGuard(max_loss=3.0, balance=1000)
        dlg.realized_loss = 50.0
        dlg.current_date = date.today() - timedelta(days=1)
        dlg.record_pnl(-5.0)
        assert dlg.realized_loss == pytest.approx(5.0)
        assert dlg.can_trade() is True


# ── RiskAgent ─────────────────────────────────────────────────────────────────

class _FakeConfig:
    trading_mode = "paper"
    live_trading = False
    live_trading_lockdown = True
    local_only_inference = True
    emergency_stop = False
    confidence_threshold = 75
    max_risk_per_trade = 1.0
    daily_max_loss = 3.0
    max_live_order_usdt = 15.0
    live_stop_loss_pct = 2.0
    max_leverage = 1.0


class TestRiskAgent:
    def setup_method(self):
        self.agent = RiskAgent(_FakeConfig())
        self.low_liq = {"liquidation_risk": "LOW"}
        self.high_liq = {"liquidation_risk": "HIGH"}

    def test_above_threshold_buy_approved(self):
        result = self.agent.evaluate("BUY", 80, self.low_liq)
        assert result["approved"] is True
        assert result["approved_action"] == "BUY"

    def test_below_threshold_blocked(self):
        result = self.agent.evaluate("BUY", 50, self.low_liq)
        assert result["approved"] is False
        assert result["approved_action"] == "HOLD"
        assert "BELOW_CONFIDENCE_THRESHOLD" in result["safety_flags"]

    def test_high_liquidation_risk_blocks(self):
        result = self.agent.evaluate("BUY", 90, self.high_liq)
        assert result["approved"] is False
        assert "HIGH_LIQUIDATION_RISK" in result["safety_flags"]

    def test_emergency_stop_blocks(self):
        result = self.agent.evaluate("BUY", 90, self.low_liq, emergency_stop=True)
        assert result["approved"] is False
        assert "EMERGENCY_STOP_ACTIVE" in result["safety_flags"]

    def test_daily_loss_hit_blocks(self):
        result = self.agent.evaluate("BUY", 90, self.low_liq, daily_loss_hit=True)
        assert result["approved"] is False
        assert "DAILY_LOSS_LIMIT_REACHED" in result["safety_flags"]

    def test_paper_mode_flag_present(self):
        result = self.agent.evaluate("HOLD", 80, self.low_liq)
        assert "PAPER_MODE_ACTIVE" in result["safety_flags"]

    def test_sell_approved_when_not_blocked(self):
        result = self.agent.evaluate("SELL", 80, self.low_liq)
        assert result["approved_action"] == "SELL"

    def test_hold_always_approved(self):
        result = self.agent.evaluate("HOLD", 90, self.low_liq)
        assert result["approved_action"] == "HOLD"

    def test_calculate_live_notional(self):
        notional = self.agent.calculate_live_notional(1000.0)
        assert notional > 0
        assert notional <= 15.0
