"""
src/scheduler.py
APScheduler-based job runner.
Jobs:
  1. Daily analysis + email report  (configurable time, weekdays only)
  2. Risk check (stop-loss / take-profit)  (configurable time, weekdays)
  3. Weekly buy order execution  (Monday by default)
"""

from __future__ import annotations

import datetime

import pytz
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

import config.settings as cfg
from src.logger import logger


# ── Job Implementations ───────────────────────────────────────────────────────

def job_daily_analysis_and_report():
    """Run market analysis and send email report."""
    from src.alpaca_client import get_account, get_all_positions
    from src.market_analysis import run_daily_analysis
    from src.notifications import send_daily_report

    logger.info("▶  JOB: daily_analysis_and_report")
    try:
        account   = get_account()
        positions = get_all_positions()
        analysis  = run_daily_analysis()
        send_daily_report(account, positions, analysis, [])
    except Exception as exc:
        logger.error(f"daily_analysis_and_report failed: {exc}")


def job_risk_check():
    """Run stop-loss / take-profit checks and send alerts for actions taken."""
    from src.strategy import run_risk_checks
    from src.notifications import send_trade_alert

    logger.info("▶  JOB: risk_check")
    try:
        actions = run_risk_checks()
        for action in actions:
            send_trade_alert(
                subject=f"{action['action']} — {action['symbol']}",
                body=(
                    f"Symbol: {action['symbol']}\n"
                    f"Action: {action['action']}\n"
                    f"P&L:    {action['pnl_pct']:+.2f}%\n"
                    f"Reason: {action['reason']}\n"
                ),
            )
    except Exception as exc:
        logger.error(f"risk_check job failed: {exc}")


def job_weekly_buy():
    """Execute the weekly buy schedule (runs only on the configured day)."""
    from src.strategy import execute_weekly_buys
    from src.notifications import send_trade_alert

    today = datetime.date.today()
    if today.weekday() != cfg.BUY_DAY_OF_WEEK:
        logger.debug("job_weekly_buy: not the configured buy day, skipping.")
        return

    logger.info("▶  JOB: weekly_buy")
    try:
        orders = execute_weekly_buys()
        summary = "\n".join(
            f"  {o.get('symbol')}: ${o.get('notional','?'):.2f} — {o.get('status','?')}"
            for o in orders
        )
        send_trade_alert(
            subject=f"Weekly Buy Complete — {today.isoformat()}",
            body=f"Weekly buy orders placed:\n\n{summary}",
        )
    except Exception as exc:
        logger.error(f"weekly_buy job failed: {exc}")


# ── Scheduler Setup ───────────────────────────────────────────────────────────

def build_scheduler() -> BlockingScheduler:
    tz = pytz.timezone(cfg.TIMEZONE)
    scheduler = BlockingScheduler(timezone=tz)

    # Parse configured times
    analysis_h, analysis_m = map(int, cfg.DAILY_ANALYSIS_TIME.split(":"))
    risk_h, risk_m         = map(int, cfg.RISK_CHECK_TIME.split(":"))

    # Daily analysis — Mon–Fri
    scheduler.add_job(
        job_daily_analysis_and_report,
        CronTrigger(
            day_of_week="mon-fri",
            hour=analysis_h,
            minute=analysis_m,
            timezone=tz,
        ),
        id="daily_analysis",
        name="Daily Analysis & Report",
        misfire_grace_time=300,
    )

    # Risk check — Mon–Fri, near close
    scheduler.add_job(
        job_risk_check,
        CronTrigger(
            day_of_week="mon-fri",
            hour=risk_h,
            minute=risk_m,
            timezone=tz,
        ),
        id="risk_check",
        name="Risk Check (Stop-Loss / Take-Profit)",
        misfire_grace_time=300,
    )

    # Weekly buy — configurable weekday
    day_names = ["mon", "tue", "wed", "thu", "fri"]
    buy_day   = day_names[min(cfg.BUY_DAY_OF_WEEK, 4)]
    scheduler.add_job(
        job_weekly_buy,
        CronTrigger(
            day_of_week=buy_day,
            hour=9,
            minute=35,        # 5 min after open
            timezone=tz,
        ),
        id="weekly_buy",
        name="Weekly Buy Orders",
        misfire_grace_time=600,
    )

    logger.info("Scheduler built with jobs:")
    for job in scheduler.get_jobs():
        logger.info(f"  • {job.name}  next run: {job.next_run_time}")

    return scheduler


def start():
    """Start the blocking scheduler. This call never returns."""
    logger.info("═══════════════════════════════════════════")
    logger.info("   Alpaca Trading Bot — Scheduler Starting  ")
    logger.info("═══════════════════════════════════════════")
    scheduler = build_scheduler()
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped by user.")
