# ⚡ Claude-Powered Crypto Trading Bot — Setup Guide

## What This Bot Does

| Feature | Detail |
|---|---|
| 📡 Live Data | Binance public API — BTC, ETH, SOL (or any pair) |
| 🤖 AI Brain | Claude analyzes RSI, MACD, Bollinger Bands, EMA every 5 min |
| 📊 Indicators | RSI-14, MACD, Bollinger Bands (20), EMA-20/50, ATR |
| 💸 Trading | Paper (simulated) — $10,000 virtual USDT by default |
| 🖥️ Terminal | Live refreshing dashboard — prices, signals, portfolio, log |

> ⚠️ **This is a paper trading bot.** No real money is used or at risk.

---

## Step 1 — Install Python

Make sure you have **Python 3.10+** installed.

```bash
python3 --version
```

---

## Step 2 — Install Dependencies

```bash
pip install -r requirements.txt
```

Or install manually:

```bash
pip install anthropic requests pandas numpy rich
```

---

## Step 3 — Get Your Anthropic API Key

1. Go to [https://console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys)
2. Click **"Create Key"**
3. Copy the key — it starts with `sk-ant-...`

> You get free credits when you sign up. The bot uses ~$0.005 per analysis call.

---

## Step 4 — Set Your API Key

**Mac / Linux:**
```bash
export ANTHROPIC_API_KEY="sk-ant-your-key-here"
```

**Windows (Command Prompt):**
```cmd
set ANTHROPIC_API_KEY=sk-ant-your-key-here
```

**Windows (PowerShell):**
```powershell
$env:ANTHROPIC_API_KEY="sk-ant-your-key-here"
```

To make it permanent, add the export line to your `~/.bashrc` or `~/.zshrc`.

---

## Step 5 — Run the Bot

```bash
python trading_bot.py
```

Press **Ctrl+C** to stop. Your final P&L and trade count will be shown.

---

## Optional Flags

| Flag | Default | Example |
|---|---|---|
| `--pairs` | BTC ETH SOL | `--pairs BTC ETH ADA DOGE` |
| `--balance` | 10000 | `--balance 50000` |
| `--interval` | 300 (5 min) | `--interval 120` (2 min) |
| `--risk` | 0.10 (10%) | `--risk 0.20` (20% per trade) |

### Examples

Trade only Bitcoin with $25,000:
```bash
python trading_bot.py --pairs BTC --balance 25000
```

Trade BTC, ETH, SOL, ADA with faster 2-minute analysis:
```bash
python trading_bot.py --pairs BTC ETH SOL ADA --interval 120
```

---

## Understanding the Dashboard

```
╔════════════════════════════════════════════════╗
║  ⚡ CLAUDE TRADING BOT │ PAPER TRADING │ ...  ║
╠════════════════════════╦═══════════════════════╣
║  📈 Prices & Signals   ║  💼 Portfolio         ║
║  📊 Indicators         ║  📋 Trade History     ║
╠════════════════════════╩═══════════════════════╣
║  🤖 Activity Log                               ║
╠════════════════════════════════════════════════╣
║  Claude's Market View summary                  ║
╚════════════════════════════════════════════════╝
```

**Signal colors:**
- 🟢 Green `BUY` = Claude recommends buying (confidence ≥ 6/10)
- 🔴 Red `SELL` = Claude recommends selling
- 🟡 Yellow `HOLD` = No strong signal

**RSI colors:**
- Green = RSI < 40 (oversold — potential buy zone)
- Red = RSI > 70 (overbought — potential sell zone)

**MACD Hist:**
- Green = Positive momentum (bullish)
- Red = Negative momentum (bearish)

---

## How Claude Makes Decisions

Every 5 minutes (configurable), Claude receives:
- Current price, 24h change, 24h volume, 24h high/low
- RSI-14, MACD line, signal line, and histogram
- Bollinger Bands (upper, mid, lower)
- EMA-20, EMA-50, price vs EMA-20 %
- ATR (Average True Range — volatility)
- Your current portfolio state

Claude then returns for each coin:
- **Action**: BUY / SELL / HOLD
- **Confidence**: 1–10 score
- **Reasoning**: 1-2 sentence explanation
- **Price Target**: Predicted price in 1–4 hours

The bot only executes trades when confidence ≥ 6.

---

## API Costs (Approximate)

| Setting | Cost per day |
|---|---|
| Default (5 min interval, 3 pairs) | ~$0.14/day |
| 2 min interval, 5 pairs | ~$0.50/day |

---

## Notes & Disclaimers

- **Paper trading only** — no real money involved
- Past performance of this bot does not guarantee future results
- Crypto markets are highly volatile
- This is for educational and research purposes
- Never invest more than you can afford to lose in real trading
