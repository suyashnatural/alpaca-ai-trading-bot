"""
src/notifications.py
Sends HTML email daily reports and trade alerts via Gmail SMTP.
"""

from __future__ import annotations

import re
import smtplib
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import config.settings as cfg
from src.logger import logger


def _md_to_html(text: str) -> str:
    """Convert markdown to clean HTML — no <br> inside tables."""
    lines = text.split("\n")
    result = []
    in_table = False
    row_num = 0

    for line in lines:
        stripped = line.strip()

        # ── Table rows ────────────────────────────────────────────────────────
        if stripped.startswith("|") and stripped.count("|") > 1:
            if not in_table:
                result.append(
                    '<table cellpadding="0" cellspacing="0" '
                    'style="border-collapse:collapse;width:100%;'
                    'font-size:13px;margin:12px 0;">'
                )
                in_table = True
                row_num = 0
            # Skip separator lines like |---|---|
            if re.match(r"\|[-| :]+\|", stripped):
                continue
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if row_num == 0:
                tds = "".join(
                    f'<th style="padding:8px 12px;border:1px solid #ccc;'
                    f'background:#1a1a2e;color:white;text-align:left;">{c}</th>'
                    for c in cells
                )
            else:
                bg = "#f5f5f5" if row_num % 2 == 0 else "#ffffff"
                tds = "".join(
                    f'<td style="padding:7px 12px;border:1px solid #e0e0e0;'
                    f'background:{bg};">{c}</td>'
                    for c in cells
                )
            result.append(f"<tr>{tds}</tr>")
            row_num += 1
            continue

        # Close table if we were in one
        if in_table:
            result.append("</table>")
            in_table = False
            row_num = 0

        # ── Headers ───────────────────────────────────────────────────────────
        m = re.match(r"^(#{1,3}) (.+)$", stripped)
        if m:
            level = len(m.group(1))
            text_content = m.group(2)
            if level == 1:
                result.append(f'<h2 style="color:#1a1a2e;margin:16px 0 4px;">{text_content}</h2>')
            elif level == 2:
                result.append(
                    f'<h3 style="color:#1a1a2e;border-bottom:2px solid #6c63ff;'
                    f'padding-bottom:4px;margin:14px 0 4px;">{text_content}</h3>'
                )
            else:
                result.append(f'<h4 style="color:#333;margin:10px 0 2px;">{text_content}</h4>')
            continue

        # ── Horizontal rule ───────────────────────────────────────────────────
        if stripped == "---":
            result.append('<hr style="border:none;border-top:1px solid #eee;margin:10px 0;">')
            continue

        # ── Blockquote ────────────────────────────────────────────────────────
        if stripped.startswith("> "):
            content = stripped[2:]
            result.append(
                f'<div style="border-left:4px solid #6c63ff;padding:8px 14px;'
                f'margin:8px 0;background:#eef0ff;border-radius:0 6px 6px 0;'
                f'font-size:13px;">{content}</div>'
            )
            continue

        # ── Bullet point ──────────────────────────────────────────────────────
        if stripped.startswith("- "):
            content = stripped[2:]
            result.append(f'<div style="padding:3px 0 3px 16px;">• {content}</div>')
            continue

        # ── Empty line ────────────────────────────────────────────────────────
        if not stripped:
            result.append('<div style="height:6px;"></div>')
            continue

        # ── Normal paragraph ──────────────────────────────────────────────────
        result.append(f'<p style="margin:4px 0;">{stripped}</p>')

    if in_table:
        result.append("</table>")

    # Apply bold and italic inline
    html = "\n".join(result)
    html = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html)
    html = re.sub(r"\*(.+?)\*",     r"<i>\1</i>", html)
    return html


def _color(pnl_pct: float) -> str:
    return "#00c896" if pnl_pct >= 0 else "#ff4d4d"


def _positions_table(positions: list[dict]) -> str:
    if not positions:
        return "<p><em>No open positions.</em></p>"
    rows = ""
    for p in positions:
        color = _color(p["pnl_pct"])
        rows += (
            f"<tr>"
            f"<td style='padding:7px 12px;border:1px solid #e0e0e0;'><b>{p['symbol']}</b></td>"
            f"<td style='padding:7px 12px;border:1px solid #e0e0e0;'>${p['market_value']:,.2f}</td>"
            f"<td style='padding:7px 12px;border:1px solid #e0e0e0;'>${p['avg_entry']:,.2f}</td>"
            f"<td style='padding:7px 12px;border:1px solid #e0e0e0;'>${p['current_price']:,.2f}</td>"
            f"<td style='padding:7px 12px;border:1px solid #e0e0e0;color:{color};'><b>{p['pnl_pct']:+.2f}%</b></td>"
            f"<td style='padding:7px 12px;border:1px solid #e0e0e0;color:{color};'>${p['unrealized_pl']:+,.2f}</td>"
            f"</tr>"
        )
    header = (
        "<tr>"
        "<th style='padding:8px 12px;border:1px solid #ccc;background:#1a1a2e;color:white;text-align:left;'>Symbol</th>"
        "<th style='padding:8px 12px;border:1px solid #ccc;background:#1a1a2e;color:white;text-align:left;'>Mkt Value</th>"
        "<th style='padding:8px 12px;border:1px solid #ccc;background:#1a1a2e;color:white;text-align:left;'>Avg Entry</th>"
        "<th style='padding:8px 12px;border:1px solid #ccc;background:#1a1a2e;color:white;text-align:left;'>Current</th>"
        "<th style='padding:8px 12px;border:1px solid #ccc;background:#1a1a2e;color:white;text-align:left;'>P&L %</th>"
        "<th style='padding:8px 12px;border:1px solid #ccc;background:#1a1a2e;color:white;text-align:left;'>P&L $</th>"
        "</tr>"
    )
    return (
        '<table cellpadding="0" cellspacing="0" '
        'style="border-collapse:collapse;width:100%;font-size:13px;">'
        f"{header}{rows}</table>"
    )


def _actions_section(actions: list[dict]) -> str:
    if not actions:
        return "<p>✅ No risk-management actions taken today.</p>"
    items = "".join(
        f"<div style='padding:4px 0;'>{'🛑' if a.get('action')=='STOP_LOSS' else '🎯'} "
        f"<b>{a['symbol']}</b>: {a.get('reason','')}</div>"
        for a in actions
    )
    return items


def _build_html_report(account, positions, analysis, actions):
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
    analysis_html = _md_to_html(analysis)

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;background:#f4f6f9;padding:20px;color:#333;">
<div style="max-width:700px;margin:auto;background:white;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.1);">

  <div style="background:linear-gradient(135deg,#1a1a2e,#16213e);color:white;padding:24px 28px;">
    <h2 style="margin:0;">📈 Alpaca Trading Bot — Daily Report</h2>
    <p style="margin:4px 0 8px;opacity:.7;">{today}</p>
    {mode_badge}
  </div>

  <div style="padding:20px 28px;background:#fafafa;border-bottom:1px solid #eee;">
    <h3 style="margin-top:0;">💼 Account Summary</h3>
    <table style="width:100%;font-size:14px;border-collapse:collapse;">
      <tr>
        <td style="padding:6px 8px;">Portfolio Value</td>
        <td style="padding:6px 8px;"><b>${account['portfolio_value']:,.2f}</b></td>
        <td style="padding:6px 8px;">Cash Available</td>
        <td style="padding:6px 8px;"><b>${account['cash']:,.2f}</b></td>
      </tr>
      <tr>
        <td style="padding:6px 8px;">Buying Power</td>
        <td style="padding:6px 8px;"><b>${account['buying_power']:,.2f}</b></td>
        <td style="padding:6px 8px;">Total Unrealised P&L</td>
        <td style="padding:6px 8px;color:{total_pnl_color};"><b>${total_pnl:+,.2f}</b></td>
      </tr>
    </table>
  </div>

  <div style="padding:20px 28px;border-bottom:1px solid #eee;">
    <h3 style="margin-top:0;">📊 Open Positions ({len(positions)})</h3>
    {_positions_table(positions)}
  </div>

  <div style="padding:20px 28px;border-bottom:1px solid #eee;">
    <h3 style="margin-top:0;">⚡ Risk Management Actions</h3>
    {_actions_section(actions)}
  </div>

  <div style="padding:20px 28px;border-bottom:1px solid #eee;">
    <h3 style="margin-top:0;">🤖 Claude AI Market Analysis</h3>
    <div style="background:#f8f9ff;border-left:4px solid #6c63ff;padding:16px 20px;border-radius:0 8px 8px 0;font-size:13px;line-height:1.8;">
      {analysis_html}
    </div>
  </div>

  <div style="padding:16px 28px;background:#f4f6f9;text-align:center;font-size:11px;color:#999;">
    ⚠️ This bot is for educational purposes only. Not financial advice.<br>
    Alpaca Trading Bot • Auto-generated report
  </div>

</div>
</body>
</html>"""


def send_daily_report(account, positions, analysis, actions) -> bool:
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
