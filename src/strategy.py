"""
src/strategy.py
Core trading strategy:
  - Weekly dollar-cost averaging across a rotating 4-week allocation schedule
  - Stop-loss: sell entire position if unrealised P&L <= -STOP_LOSS_PCT
  - Take-profit: sell half the position if unrealised P&L >= TAKE_PROFIT_PCT
"""

from __future__ import annotations

import datetime
from typing import Optional

import config.settings as cfg
from src.alpaca_client import (
    get_all_positions,
    place_market_buy,
    place_market_sell_qty,
    get_account,
)
from src.logger import logger


# ── Helper ────────────────────────────────────────────────────────────────────

def _current_week_index() -> int:
    """Return 0-3 based on ISO week number, cycling every 4 weeks."""
    iso_week = datetime.date.today().isocalendar().week
    return (iso_week - 1) % 4


# ── Weekly Buy ────────────────────────────────────────────────────────────────

def execute_weekly_buys(dry_run: bool = False) -> list[dict]:
    """
    Place notional market-buy orders according to this week's allocation.
    If dry_run=True, log the plan but don't place real orders.
    Returns a list of order result dicts.
    """
    account = get_account()
    buying_power = account["buying_power"]

    budget = min(cfg.WEEKLY_BUDGET, buying_power * 0.95)   # never use >95% of buying power
    if budget < 1:
        logger.warning("Insufficient buying power for weekly buys. Skipping.")
        return []

    week_idx = _current_week_index()
    allocation = cfg.WEEKLY_ALLOCATIONS[week_idx]

    logger.info(f"═══ Weekly Buy — Week {week_idx + 1}/4 — Budget ${budget:.2f} ═══")

    orders = []
    for symbol, fraction in allocation.items():
        notional = round(budget * fraction, 2)
        if notional < 1:
            continue
        logger.info(f"  {'[DRY-RUN] ' if dry_run else ''}Buying ${notional:.2f} of {symbol}")
        if not dry_run:
            try:
                result = place_market_buy(symbol, notional)
                orders.append(result)
            except Exception as exc:
                logger.error(f"  Failed to buy {symbol}: {exc}")
                orders.append({"symbol": symbol, "error": str(exc)})
        else:
            orders.append({"symbol": symbol, "notional": notional, "dry_run": True})

    return orders


# ── Risk Management ───────────────────────────────────────────────────────────

def _should_stop_loss(pnl_pct: float) -> bool:
    return pnl_pct <= -abs(cfg.STOP_LOSS_PCT)


def _should_take_profit(pnl_pct: float) -> bool:
    return pnl_pct >= abs(cfg.TAKE_PROFIT_PCT)


def run_risk_checks(dry_run: bool = False) -> list[dict]:
    """
    Scan all open positions and apply stop-loss / take-profit rules.
    Returns a list of action dicts describing what was done (or would be done).
    """
    positions = get_all_positions()
    actions = []

    logger.info(f"═══ Risk Check — {len(positions)} open position(s) ═══")

    for pos in positions:
        symbol   = pos["symbol"]
        qty      = pos["qty"]
        pnl_pct  = pos["pnl_pct"]
        mkt_val  = pos["market_value"]

        if _should_stop_loss(pnl_pct):
            reason = f"STOP-LOSS triggered ({pnl_pct:.2f}% ≤ -{cfg.STOP_LOSS_PCT}%)"
            logger.warning(f"  {symbol}: {reason} — selling ALL {qty:.4f} shares")
            action = {
                "symbol":  symbol,
                "action":  "STOP_LOSS",
                "qty":     qty,
                "pnl_pct": pnl_pct,
                "reason":  reason,
            }
            if not dry_run:
                try:
                    order = place_market_sell_qty(symbol, qty)
                    action["order"] = order
                except Exception as exc:
                    logger.error(f"  Stop-loss sell failed for {symbol}: {exc}")
                    action["error"] = str(exc)
            actions.append(action)

        elif _should_take_profit(pnl_pct):
            sell_qty = round(qty / 2, 9)
            reason   = f"TAKE-PROFIT triggered ({pnl_pct:.2f}% ≥ {cfg.TAKE_PROFIT_PCT}%)"
            logger.success(f"  {symbol}: {reason} — selling HALF ({sell_qty:.4f} shares)")
            action = {
                "symbol":  symbol,
                "action":  "TAKE_PROFIT",
                "qty":     sell_qty,
                "pnl_pct": pnl_pct,
                "reason":  reason,
            }
            if not dry_run:
                try:
                    order = place_market_sell_qty(symbol, sell_qty)
                    action["order"] = order
                except Exception as exc:
                    logger.error(f"  Take-profit sell failed for {symbol}: {exc}")
                    action["error"] = str(exc)
            actions.append(action)

        else:
            logger.info(f"  {symbol}: P&L {pnl_pct:+.2f}% — HOLD (no action)")

    return actions
