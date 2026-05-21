"""
main.py — Entry point for the Alpaca Trading Bot.

Usage:
  python main.py              # Start the scheduler (runs continuously)
  python main.py --status     # Print current portfolio snapshot
  python main.py --buy        # Manually trigger this week's buys (live)
  python main.py --dry-run    # Simulate buys without placing real orders
  python main.py --risk       # Run stop-loss / take-profit check now
  python main.py --analysis   # Run AI market analysis and print to console
  python main.py --check NVDA # Quick AI check on a single symbol
"""

import argparse
import sys

from src.logger import logger
import config.settings as cfg


def print_banner():
    print("""
╔══════════════════════════════════════════════════════╗
║          🚀  ALPACA  AI  TRADING  BOT  🤖            ║
║   Powered by Alpaca Markets + Claude AI (Anthropic)  ║
╚══════════════════════════════════════════════════════╝
""")


def cmd_status():
    """Print a live portfolio snapshot to the console."""
    from tabulate import tabulate
    from src.alpaca_client import get_account, get_all_positions

    account   = get_account()
    positions = get_all_positions()

    print(f"\n{'─'*55}")
    print(f"  MODE:            {'📄 PAPER' if cfg.ALPACA_PAPER else '💸 LIVE'}")
    print(f"  Portfolio Value: ${account['portfolio_value']:>12,.2f}")
    print(f"  Cash:            ${account['cash']:>12,.2f}")
    print(f"  Buying Power:    ${account['buying_power']:>12,.2f}")
    print(f"{'─'*55}")

    if not positions:
        print("  No open positions.\n")
        return

    rows = [
        [
            p["symbol"],
            f"${p['market_value']:,.2f}",
            f"${p['avg_entry']:,.2f}",
            f"${p['current_price']:,.2f}",
            f"{p['pnl_pct']:+.2f}%",
            f"${p['unrealized_pl']:+,.2f}",
        ]
        for p in positions
    ]
    print(tabulate(
        rows,
        headers=["Symbol", "Mkt Value", "Avg Entry", "Current", "P&L %", "P&L $"],
        tablefmt="rounded_outline",
    ))
    total_pnl = sum(p["unrealized_pl"] for p in positions)
    print(f"\n  Total Unrealised P&L: ${total_pnl:+,.2f}\n")


def cmd_buy(dry_run: bool = False):
    from src.strategy import execute_weekly_buys
    orders = execute_weekly_buys(dry_run=dry_run)
    print(f"\n{'[DRY-RUN] ' if dry_run else ''}Orders placed: {len(orders)}")
    for o in orders:
        print(f"  {o}")


def cmd_risk():
    from src.strategy import run_risk_checks
    actions = run_risk_checks()
    if not actions:
        print("\n✅ No risk actions triggered.\n")
    for a in actions:
        print(f"\n  ⚡ {a['action']} — {a['symbol']}: {a['reason']}")


def cmd_analysis():
    from src.market_analysis import run_daily_analysis
    print("\n🤖 Running Claude AI Market Analysis...\n")
    result = run_daily_analysis()
    print(result)


def cmd_check(symbol: str):
    from src.market_analysis import quick_symbol_check
    print(f"\n🔍 Quick check: {symbol.upper()}\n")
    print(quick_symbol_check(symbol.upper()))


def main():
    print_banner()

    # Config validation
    missing = cfg.validate_config()
    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        logger.error("Please copy .env.example to .env and fill in your credentials.")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Alpaca AI Trading Bot")
    parser.add_argument("--status",   action="store_true", help="Show portfolio snapshot")
    parser.add_argument("--buy",      action="store_true", help="Run weekly buys now")
    parser.add_argument("--dry-run",  action="store_true", help="Simulate buys (no orders)")
    parser.add_argument("--risk",     action="store_true", help="Run risk check now")
    parser.add_argument("--analysis", action="store_true", help="Run AI analysis now")
    parser.add_argument("--check",    metavar="SYMBOL",    help="Quick AI check on a symbol")
    args = parser.parse_args()

    if args.status:
        cmd_status()
    elif args.buy:
        cmd_buy(dry_run=False)
    elif getattr(args, "dry_run"):
        cmd_buy(dry_run=True)
    elif args.risk:
        cmd_risk()
    elif args.analysis:
        cmd_analysis()
    elif args.check:
        cmd_check(args.check)
    else:
        # Default: start the scheduler
        from src.scheduler import start
        start()


if __name__ == "__main__":
    main()
