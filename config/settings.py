"""
config/settings.py
Central configuration loaded from environment variables.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Alpaca ────────────────────────────────────────────────────────────────────
ALPACA_API_KEY    = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")
ALPACA_PAPER      = os.getenv("ALPACA_PAPER", "true").lower() == "true"

# ── Claude AI ─────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# ── Email ─────────────────────────────────────────────────────────────────────
EMAIL_SENDER   = os.getenv("EMAIL_SENDER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER", "")

# ── Strategy ──────────────────────────────────────────────────────────────────
WEEKLY_BUDGET    = float(os.getenv("WEEKLY_BUDGET", "750"))
STOP_LOSS_PCT    = float(os.getenv("STOP_LOSS_PCT", "20"))
TAKE_PROFIT_PCT  = float(os.getenv("TAKE_PROFIT_PCT", "40"))
BUY_DAY_OF_WEEK  = int(os.getenv("BUY_DAY_OF_WEEK", "0"))   # 0 = Monday

# ── Scheduling ────────────────────────────────────────────────────────────────
DAILY_ANALYSIS_TIME = os.getenv("DAILY_ANALYSIS_TIME", "09:30")
RISK_CHECK_TIME     = os.getenv("RISK_CHECK_TIME", "15:45")
TIMEZONE            = "America/New_York"

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ── Portfolio Allocation ──────────────────────────────────────────────────────
# Rotating 4-week buy schedule. Each week specifies symbol -> fraction of budget.
WEEKLY_ALLOCATIONS = [
    # Week 1 — AI Core + Safety
    {
        "NVDA": 0.267,   # $200
        "PLTR": 0.200,   # $150
        "AMD":  0.200,   # $150
        "CRWD": 0.200,   # $150
        "IVV":  0.133,   # $100
    },
    # Week 2 — Add Tesla momentum
    {
        "NVDA": 0.267,   # $200
        "TSLA": 0.267,   # $200
        "PLTR": 0.200,   # $150
        "AMD":  0.133,   # $100
        "IVV":  0.133,   # $100
    },
    # Week 3 — Add Crypto exposure
    {
        "NVDA": 0.267,   # $200
        "COIN": 0.200,   # $150
        "TSLA": 0.200,   # $150
        "PLTR": 0.133,   # $100 (via equity; COIN covers crypto)
        "IVV":  0.133,   # $100 (safe base)
    },
    # Week 4 — Rebalance & top-up laggards
    {
        "NVDA": 0.267,   # $200
        "CRWD": 0.267,   # $200
        "COIN": 0.200,   # $150
        "TSLA": 0.133,   # $100
        "IVV":  0.133,   # $100
    },
]

def validate_config() -> list[str]:
    """Return a list of missing required config keys."""
    missing = []
    required = {
        "ALPACA_API_KEY":    ALPACA_API_KEY,
        "ALPACA_SECRET_KEY": ALPACA_SECRET_KEY,
        "ANTHROPIC_API_KEY": ANTHROPIC_API_KEY,
    }
    for key, val in required.items():
        if not val:
            missing.append(key)
    return missing
