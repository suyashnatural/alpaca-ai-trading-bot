"""
src/market_analysis.py
Uses Claude Opus via Amazon Bedrock to analyse current market conditions
and generate daily commentary + trading recommendations for the portfolio.
"""

from __future__ import annotations

import json
import datetime
import boto3

import config.settings as cfg
from src.alpaca_client import get_all_positions, get_account, get_latest_price
from src.logger import logger

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = boto3.client(
            service_name="bedrock-runtime",
            region_name=cfg.AWS_REGION,
            aws_access_key_id=cfg.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=cfg.AWS_SECRET_ACCESS_KEY,
        )
        logger.info("Amazon Bedrock client initialised (Claude Opus)")
    return _client


def _invoke(prompt: str, max_tokens: int = 1500) -> str:
    """Send a prompt to Claude Opus via Bedrock and return the text response."""
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    })
    response = _get_client().invoke_model(
        modelId=cfg.BEDROCK_MODEL_ID,
        body=body,
        contentType="application/json",
        accept="application/json",
    )
    result = json.loads(response["body"].read())
    return result["content"][0]["text"]


def _build_portfolio_snapshot() -> dict:
    account   = get_account()
    positions = get_all_positions()
    return {
        "date":            datetime.date.today().isoformat(),
        "portfolio_value": account["portfolio_value"],
        "cash":            account["cash"],
        "buying_power":    account["buying_power"],
        "positions":       positions,
    }


def run_daily_analysis() -> str:
    snapshot = _build_portfolio_snapshot()
    today    = datetime.date.today().strftime("%A, %B %d %Y")

    prompt = f"""
You are an expert algorithmic trading assistant managing a short-term aggressive growth portfolio.

Today is {today}.

## Current Portfolio Snapshot
```json
{json.dumps(snapshot, indent=2)}
```

## Portfolio Strategy
- Weekly dollar-cost averaging into: NVDA, PLTR, AMD, CRWD, TSLA, COIN, IVV
- Stop-loss: sell entire position at -{cfg.STOP_LOSS_PCT}% P&L
- Take-profit: sell half the position at +{cfg.TAKE_PROFIT_PCT}% P&L
- Time horizon: 1-2 years
- Risk tolerance: Aggressive

## Your Task
1. **Market Sentiment** — Briefly assess today's likely market conditions for each held symbol.
2. **Portfolio Health** — Comment on each position's P&L and whether to HOLD, add more, or watch closely.
3. **Risk Alerts** — Flag any positions approaching stop-loss or take-profit thresholds.
4. **Today's Recommendation** — One clear action sentence per symbol (HOLD / WATCH / APPROACHING STOP-LOSS / APPROACHING TAKE-PROFIT).
5. **Weekly Outlook** — A 2-3 sentence market outlook for the next 7 days relevant to this portfolio.

Keep your response concise, data-driven, and actionable. Use bullet points.
"""

    logger.info("Running daily AI market analysis with Claude Opus (Bedrock)...")
    try:
        analysis = _invoke(prompt, max_tokens=1500)
        logger.success("Daily AI analysis complete.")
        return analysis
    except Exception as exc:
        logger.error(f"Bedrock analysis failed: {exc}")
        return f"⚠️  Analysis unavailable: {exc}"


def quick_symbol_check(symbol: str) -> str:
    try:
        price = get_latest_price(symbol)
    except Exception:
        price = "unavailable"

    prompt = f"""
You are a professional stock analyst. Give a concise 3-5 sentence assessment of {symbol} today.
Current price: {price}
Cover: recent price action, key catalysts, short-term outlook (1-4 weeks), and a clear BUY/HOLD/AVOID verdict.
"""
    try:
        return _invoke(prompt, max_tokens=400)
    except Exception as exc:
        return f"⚠️  Check unavailable: {exc}"
