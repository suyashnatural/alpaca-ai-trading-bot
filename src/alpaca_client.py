"""
src/alpaca_client.py
Thin wrapper around alpaca-py TradingClient & StockHistoricalDataClient.
All Alpaca interactions go through this module.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    MarketOrderRequest,
    GetOrdersRequest,
)
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest, StockBarsRequest
from alpaca.data.timeframe import TimeFrame

import config.settings as cfg
from src.logger import logger


# ── Singletons ────────────────────────────────────────────────────────────────

_trading_client: Optional[TradingClient] = None
_data_client: Optional[StockHistoricalDataClient] = None


def get_trading_client() -> TradingClient:
    global _trading_client
    if _trading_client is None:
        _trading_client = TradingClient(
            api_key=cfg.ALPACA_API_KEY,
            secret_key=cfg.ALPACA_SECRET_KEY,
            paper=cfg.ALPACA_PAPER,
        )
        mode = "PAPER" if cfg.ALPACA_PAPER else "LIVE"
        logger.info(f"Alpaca TradingClient initialised [{mode}]")
    return _trading_client


def get_data_client() -> StockHistoricalDataClient:
    global _data_client
    if _data_client is None:
        _data_client = StockHistoricalDataClient(
            api_key=cfg.ALPACA_API_KEY,
            secret_key=cfg.ALPACA_SECRET_KEY,
        )
        logger.info("Alpaca DataClient initialised")
    return _data_client


# ── Account ───────────────────────────────────────────────────────────────────

def get_account() -> dict:
    """Return a plain dict with key account fields."""
    client = get_trading_client()
    acc = client.get_account()
    return {
        "cash":            float(acc.cash),
        "portfolio_value": float(acc.portfolio_value),
        "buying_power":    float(acc.buying_power),
        "equity":          float(acc.equity),
        "status":          acc.status,
    }


# ── Positions ─────────────────────────────────────────────────────────────────

def get_all_positions() -> list[dict]:
    """Return a list of current open positions as plain dicts."""
    client = get_trading_client()
    positions = client.get_all_positions()
    result = []
    for p in positions:
        entry_price   = float(p.avg_entry_price)
        current_price = float(p.current_price)
        pnl_pct = ((current_price - entry_price) / entry_price) * 100 if entry_price else 0.0
        result.append({
            "symbol":        p.symbol,
            "qty":           float(p.qty),
            "market_value":  float(p.market_value),
            "avg_entry":     entry_price,
            "current_price": current_price,
            "unrealized_pl": float(p.unrealized_pl),
            "pnl_pct":       round(pnl_pct, 2),
        })
    return result


def get_position(symbol: str) -> Optional[dict]:
    """Return a single position dict or None if not held."""
    for pos in get_all_positions():
        if pos["symbol"] == symbol:
            return pos
    return None


# ── Orders ────────────────────────────────────────────────────────────────────

def place_market_buy(symbol: str, notional_usd: float) -> dict:
    """
    Buy `notional_usd` dollars worth of `symbol` at market price.
    Returns order dict.
    """
    client = get_trading_client()
    order_data = MarketOrderRequest(
        symbol=symbol,
        notional=round(notional_usd, 2),
        side=OrderSide.BUY,
        time_in_force=TimeInForce.DAY,
    )
    order = client.submit_order(order_data)
    logger.info(f"BUY  {symbol:6s}  notional=${notional_usd:.2f}  order_id={order.id}")
    return {
        "order_id": str(order.id),
        "symbol":   order.symbol,
        "side":     "BUY",
        "notional": notional_usd,
        "status":   order.status,
    }


def place_market_sell_qty(symbol: str, qty: float) -> dict:
    """
    Sell `qty` shares of `symbol` at market price.
    Returns order dict.
    """
    client = get_trading_client()
    order_data = MarketOrderRequest(
        symbol=symbol,
        qty=round(qty, 9),
        side=OrderSide.SELL,
        time_in_force=TimeInForce.DAY,
    )
    order = client.submit_order(order_data)
    logger.info(f"SELL {symbol:6s}  qty={qty:.4f}  order_id={order.id}")
    return {
        "order_id": str(order.id),
        "symbol":   order.symbol,
        "side":     "SELL",
        "qty":      qty,
        "status":   order.status,
    }


def get_latest_price(symbol: str) -> float:
    """Return the latest ask price for a symbol."""
    dc = get_data_client()
    req = StockLatestQuoteRequest(symbol_or_symbols=symbol)
    quotes = dc.get_stock_latest_quote(req)
    quote = quotes[symbol]
    return float(quote.ask_price) if quote.ask_price else float(quote.bid_price)


def get_open_orders() -> list[dict]:
    """Return all currently open (pending) orders."""
    client = get_trading_client()
    req = GetOrdersRequest(status=QueryOrderStatus.OPEN)
    orders = client.get_orders(req)
    return [
        {
            "order_id": str(o.id),
            "symbol":   o.symbol,
            "side":     o.side.value,
            "qty":      float(o.qty) if o.qty else None,
            "notional": float(o.notional) if o.notional else None,
            "status":   o.status.value,
        }
        for o in orders
    ]
