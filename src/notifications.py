"""
src/notifications.py
Sends HTML email daily reports and trade alerts via Gmail SMTP.
"""

from __future__ import annotations

import smtplib
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import config.settings as cfg
from src.logger import logger


# ── HTML Helpers ──────────────────────────────────────────────────────────────

def _color(pnl_pct: float) -> str:
    if pnl_pct >= 0:
        return "#00c896"   # green
    return "#ff4d4d"       # red


def _positions_table(positions: list[dict]) -> str:
    if not positions:
        return "<p><em>No open positions.</em></p>"
    rows = ""
    for p in positions:
        color = _color(p["pnl_pct"])
        rows += f"""
        <tr>
          <td><b>{p['symbol']}</b></td>
          <td>${p['market_value']:,.2f}</td>
          <td>${p['avg_entry']:,.2f}</td>
          <td>${p['current_price']:,.2f}</td>
          <td style="color:{color}"><b>{p['pnl_pct']:+.2f}%</b></td>
          <td style="color:{color}">${p['unrealized_pl']:+,.2f}</td>
        </tr>"""
    return f"""
    <table border="1" cellpadding="8" cellspacing="0"
           style="border-collapse:collapse;width:100%;font-family:monospace;font-size:13px;">
      <thead style="background:#1a1a2e;color:white;">
        <tr>
          <th>Symbol</th><th>Mkt Value</th><th>Avg Entry</th>
          <th>Current</th><th>P&L %</th><th>P&L $</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>"""


def _actions_section(actions: list[dict]) -> str:
    if not actions:
        return "<p>✅ No risk-management actions taken today.</p>"
    items = ""
    for a in actions:
        emoji = "🛑" if a.get("action") == "STOP_LOSS" else "🎯"
        items += f"<li>{emoji} <b>{a['symbol']}</b>: {a.get('reason','')}</li>"
    return f"<ul>{items}</ul>"


def _build_html_report(
    account:    dict,
    positions:  list[dict],
    analysis:   str,
    actions:    list[dict],
) -> str:
    today = datetime.date.today().strftime("%A, %B %d %Y")
    total_pnl = sum(p["unrealized_pl"] for p in positions)
    total_pnl_color = _color(total_pnl)
    mode_badge = (
        '<span style="background:#ff9f43;color:#000;padding:2px 8px;'
        'border-radius:4px;font-size:11px;font-weight:bold;">PAPER TRADING</span>'
        if cfg.ALPACA_PAPER else
        '<span style="background:#ee5a24;color:#fff;padding:2px 8px;'
        'border-radius:4px;font-size:11px;font-weight:bold;">LIVE TRADING</span>'
    )
    analysis_html = analysis.replace("\n", "<br>")

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;background:#f4f6f9;padding:20px;color:#333;">
<div style="max-width:700px;margin:auto;background:white;border-radius:12px;
            overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.1);">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,#1a1a2e,#16213e);
              color:white;padding:24px 28px;">
    <h2 style="margin:0;">📈 Alpaca Trading Bot — Daily Report</h2>
    <p style="margin:4px 0 8px;opacity:.7;">{today}</p>
    {mode_badge}
  </div>

  <!-- Account Summary -->
  <div style="padding:20px 28px;background:#fafafa;border-bottom:1px solid #eee;">
    <h3 style="margin-top:0;">💼 Account Summary</h3>
    <table style="width:100%;font-size:14px;">
      <tr>
        <td>Portfolio Value</td>
        <td><b>${account['portfolio_value']:,.2f}</b></td>
        <td>Cash Available</td>
        <td><b>${account['cash']:,.2f}</b></td>
      </tr>
      <tr>
        <td>Buying Power</td>
        <td><b>${account['buying_power']:,.2f}</b></td>
        <td>Total Unrealised P&L</td>
        <td style="color:{total_pnl_color}"><b>${total_pnl:+,.2f}</b></td>
      </tr>
    </table>
  </div>

  <!-- Positions -->
  <div style="padding:20px 28px;border-bottom:1px solid #eee;">
    <h3 style="margin-top:0;">📊 Open Positions ({len(positions)})</h3>
    {_positions_table(positions)}
  </div>

  <!-- Risk Actions -->
  <div style="padding:20px 28px;border-bottom:1px solid #eee;">
    <h3 style="margin-top:0;">⚡ Risk Management Actions</h3>
    {_actions_section(actions)}
  </div>

  <!-- AI Analysis -->
  <div style="padding:20px 28px;border-bottom:1px solid #eee;">
    <h3 style="margin-top:0;">🤖 Claude AI Market Analysis</h3>
    <div style="background:#f8f9ff;border-left:4px solid #6c63ff;
                padding:14px 18px;border-radius:0 8px 8px 0;font-size:13px;line-height:1.7;">
      {analysis_html}
    </div>
  </div>

  <!-- Footer -->
  <div style="padding:16px 28px;background:#f4f6f9;text-align:center;
              font-size:11px;color:#999;">
    ⚠️ This bot is for educational purposes only. Not financial advice.<br>
    Alpaca Trading Bot • Auto-generated report
  </div>
</div>
</body>
</html>"""


# ── Public API ────────────────────────────────────────────────────────────────

def send_daily_report(
    account:   dict,
    positions: list[dict],
    analysis:  str,
    actions:   list[dict],
) -> bool:
    """Build and send the daily HTML email report. Returns True on success."""
    if not cfg.EMAIL_SENDER or not cfg.EMAIL_PASSWORD:
        logger.warning("Email credentials not configured — skipping report.")
        return False

    today   = datetime.date.today().strftime("%Y-%m-%d")
    subject = f"📈 Trading Bot Report — {today}"
    html    = _build_html_report(account, positions, analysis, actions)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = cfg.EMAIL_SENDER
    msg["To"]      = cfg.EMAIL_RECEIVER
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(cfg.EMAIL_SENDER, cfg.EMAIL_PASSWORD)
            server.sendmail(cfg.EMAIL_SENDER, cfg.EMAIL_RECEIVER, msg.as_string())
        logger.success(f"Daily report sent to {cfg.EMAIL_RECEIVER}")
        return True
    except Exception as exc:
        logger.error(f"Failed to send email: {exc}")
        return False


def send_trade_alert(subject: str, body: str) -> bool:
    """Send a plain-text trade alert email."""
    if not cfg.EMAIL_SENDER or not cfg.EMAIL_PASSWORD:
        return False
    msg = MIMEMultipart()
    msg["Subject"] = f"🚨 Trade Alert: {subject}"
    msg["From"]    = cfg.EMAIL_SENDER
    msg["To"]      = cfg.EMAIL_RECEIVER
    msg.attach(MIMEText(body, "plain"))
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(cfg.EMAIL_SENDER, cfg.EMAIL_PASSWORD)
            server.sendmail(cfg.EMAIL_SENDER, cfg.EMAIL_RECEIVER, msg.as_string())
        logger.info(f"Trade alert sent: {subject}")
        return True
    except Exception as exc:
        logger.error(f"Alert email failed: {exc}")
        return False
