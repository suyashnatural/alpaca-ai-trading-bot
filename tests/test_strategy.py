"""
tests/test_strategy.py
Unit tests for strategy logic (no real API calls).
"""

import pytest
from unittest.mock import patch, MagicMock

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.strategy import (
    _should_stop_loss,
    _should_take_profit,
    _current_week_index,
)
import config.settings as cfg


class TestRiskRules:
    def test_stop_loss_triggers_at_threshold(self):
        cfg.STOP_LOSS_PCT = 20
        assert _should_stop_loss(-20.0)  is True
        assert _should_stop_loss(-20.01) is True

    def test_stop_loss_does_not_trigger_below_threshold(self):
        cfg.STOP_LOSS_PCT = 20
        assert _should_stop_loss(-19.99) is False
        assert _should_stop_loss(0.0)    is False

    def test_take_profit_triggers_at_threshold(self):
        cfg.TAKE_PROFIT_PCT = 40
        assert _should_take_profit(40.0)  is True
        assert _should_take_profit(40.01) is True

    def test_take_profit_does_not_trigger_below_threshold(self):
        cfg.TAKE_PROFIT_PCT = 40
        assert _should_take_profit(39.99) is False
        assert _should_take_profit(0.0)   is False

    def test_week_index_in_range(self):
        idx = _current_week_index()
        assert 0 <= idx <= 3


class TestWeeklyBuys:
    @patch("src.strategy.get_account")
    @patch("src.strategy.place_market_buy")
    def test_dry_run_does_not_call_place_order(self, mock_buy, mock_account):
        mock_account.return_value = {
            "buying_power": 10_000,
            "cash": 10_000,
            "portfolio_value": 10_000,
            "equity": 10_000,
            "status": "ACTIVE",
        }
        from src.strategy import execute_weekly_buys
        orders = execute_weekly_buys(dry_run=True)
        mock_buy.assert_not_called()
        assert len(orders) > 0
        for o in orders:
            assert o.get("dry_run") is True

    @patch("src.strategy.get_account")
    def test_insufficient_buying_power_returns_empty(self, mock_account):
        mock_account.return_value = {
            "buying_power": 0.50,
            "cash": 0.50,
            "portfolio_value": 100,
            "equity": 100,
            "status": "ACTIVE",
        }
        from src.strategy import execute_weekly_buys
        orders = execute_weekly_buys(dry_run=False)
        assert orders == []
