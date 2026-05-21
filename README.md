# 🚀 Alpaca AI Trading Bot

> **A professional automated trading bot powered by [Alpaca Markets](https://alpaca.markets) + [Claude AI (Anthropic)](https://anthropic.com)**

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![Alpaca](https://img.shields.io/badge/Alpaca-Markets-yellow)
![Claude](https://img.shields.io/badge/Claude-AI-purple)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ Features

| Feature | Details |
|---|---|
| 📅 **Weekly DCA** | Auto-buys a rotating basket of stocks every Monday at market open |
| 🛑 **Stop-Loss** | Automatically sells entire position if it falls ≥ 20% |
| 🎯 **Take-Profit** | Sells half the position when it gains ≥ 40% |
| 🤖 **AI Analysis** | Daily Claude AI market analysis + recommendations |
| 📧 **Email Reports** | Beautiful HTML daily report sent to your inbox |
| 🔁 **Scheduler** | Fully automated — runs 24/7 with APScheduler |
| 🧪 **Paper Trading** | Safe testing with Alpaca's paper environment |

---

## 📦 Portfolio Stocks

| Symbol | Company | Category |
|---|---|---|
| `NVDA` | NVIDIA | AI / Semiconductors |
| `PLTR` | Palantir | AI / Government |
| `AMD` | Advanced Micro Devices | AI Chips |
| `CRWD` | CrowdStrike | Cybersecurity |
| `TSLA` | Tesla | EV / Tech |
| `COIN` | Coinbase | Crypto |
| `IVV` | iShares S&P 500 ETF | Safety Net |

---

## 🗂 Project Structure

```
alpaca-trading-bot/
├── main.py                  # Entry point & CLI
├── config/
│   └── settings.py          # All configuration from .env
├── src/
│   ├── alpaca_client.py     # Alpaca API wrapper (buy/sell/positions)
│   ├── strategy.py          # Trading logic (DCA + risk rules)
│   ├── market_analysis.py   # Claude AI market analysis
│   ├── notifications.py     # Email reports & trade alerts
│   ├── scheduler.py         # APScheduler job runner
│   └── logger.py            # Loguru logging setup
├── tests/
│   └── test_strategy.py     # Unit tests
├── logs/                    # Auto-generated daily log files
├── .env.example             # Config template
├── .gitignore
└── requirements.txt
```

---

## ⚙️ Setup

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/alpaca-trading-bot.git
cd alpaca-trading-bot
```

### 2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
```bash
cp .env.example .env
# Open .env and fill in your credentials:
#   ALPACA_API_KEY, ALPACA_SECRET_KEY  →  from app.alpaca.markets
#   ANTHROPIC_API_KEY                  →  from console.anthropic.com
#   EMAIL_SENDER, EMAIL_PASSWORD       →  Gmail + App Password
```

### 5. Test your setup
```bash
python main.py --status      # View your paper portfolio
python main.py --dry-run     # Simulate a weekly buy
python main.py --analysis    # Run AI market analysis
```

### 6. Start the bot
```bash
python main.py               # Starts the fully automated scheduler
```

---

## 🖥 CLI Commands

```bash
python main.py                   # Start scheduler (runs 24/7)
python main.py --status          # Print live portfolio snapshot
python main.py --buy             # Execute this week's buy orders NOW
python main.py --dry-run         # Simulate buys (no real orders)
python main.py --risk            # Run stop-loss / take-profit check
python main.py --analysis        # Run Claude AI market analysis
python main.py --check NVDA      # Quick AI check on a single stock
```

---

## 📅 Automated Schedule (ET)

| Time | Job |
|---|---|
| Mon–Fri 9:30 AM | Daily AI analysis + email report |
| Mon–Fri 3:45 PM | Risk check (stop-loss / take-profit) |
| Monday 9:35 AM | Weekly buy orders |

---

## 📊 Weekly Buy Schedule (4-Week Rotation)

| Week | Stocks | Budget % |
|---|---|---|
| 1 | NVDA + PLTR + AMD + CRWD + IVV | 26.7 / 20 / 20 / 20 / 13.3 |
| 2 | NVDA + TSLA + PLTR + AMD + IVV | 26.7 / 26.7 / 20 / 13.3 / 13.3 |
| 3 | NVDA + COIN + TSLA + PLTR + IVV | 26.7 / 20 / 20 / 20 / 13.3 |
| 4 | NVDA + CRWD + COIN + TSLA + IVV | 26.7 / 26.7 / 20 / 13.3 / 13.3 |

---

## 🛡 Risk Rules

- **Stop-Loss**: Any position down ≥ **20%** → sell 100%
- **Take-Profit**: Any position up ≥ **40%** → sell 50% (let the rest run)
- All thresholds configurable in `.env`

---

## 🧪 Testing

```bash
pytest tests/ -v
```

---

## ☁️ Deploy to a Server (Keep it Running 24/7)

### Option A — Run with screen (Linux VPS)
```bash
screen -S trading-bot
python main.py
# Ctrl+A then D to detach
```

### Option B — systemd service
```ini
[Unit]
Description=Alpaca Trading Bot
After=network.target

[Service]
WorkingDirectory=/path/to/alpaca-trading-bot
ExecStart=/path/to/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Option C — Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

---

## ⚠️ Disclaimer

> This bot is built for **educational and paper-trading purposes**. It is **not financial advice**.
> Algorithmic trading involves significant risk. Always test thoroughly with paper money before
> risking real capital. The authors are not responsible for any financial losses.

---

## 📄 License

MIT — free to use, modify, and distribute.
