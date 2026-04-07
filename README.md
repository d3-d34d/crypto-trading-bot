# ⚡ Claude-Powered Crypto Trading Bot

> A live terminal trading bot powered by Claude AI — collects real-world crypto market data, analyzes technical indicators, predicts short-term price movements, and paper-trades automatically.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![Powered by Claude](https://img.shields.io/badge/Powered%20by-Claude%20AI-orange?logo=anthropic)
![Paper Trading](https://img.shields.io/badge/Mode-Paper%20Trading-green)
![Live Data](https://img.shields.io/badge/Data-Binance%20Live-yellow?logo=binance)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

---

## 📺 Live Terminal Preview

```
╔══════════════════════════════════════════════════════════════════════════════════════╗
║  ⚡ CLAUDE TRADING BOT │ PAPER TRADING │  2026-04-07  14:32:07                      ║
║  Portfolio: $10,284.37  │  P&L: +$284.37  (+2.84%)                                 ║
╠═════════════════════════════════════╦════════════════════════════════════════════════╣
║  📈 Live Prices & AI Signals        ║  💼 Portfolio                                 ║
║ ─────────────────────────────────── ║ ────────────────────────────────────────────  ║
║  Pair       Price      24h%  Action ║  Asset    Qty           Value        P&L      ║
║  BTC/USDT   $83,412    +2.1%  BUY  ║  USDT     —            $7,284.37     —        ║
║  ETH/USDT   $3,201     -0.4%  HOLD ║  BTC      0.012140     $1,013.44    +$13.44   ║
║  SOL/USDT   $142.50    +1.8%  SELL ║  ETH      0.295000     $944.30      +$5.60    ║
╠═════════════════════════════════════╬════════════════════════════════════════════════╣
║  📊 Technical Indicators            ║  📋 Trade History                             ║
║ ─────────────────────────────────── ║ ────────────────────────────────────────────  ║
║  Pair       RSI    MACD     EMA20   ║  Time     Side   Symbol   USDT      Reason    ║
║  BTC/USDT   38.2   +0.0012  +1.2%  ║  14:30:01 BUY    BTC      $1,000    RSI low   ║
║  ETH/USDT   51.7   -0.0004  -0.1%  ║  14:30:01 BUY    ETH      $938      MACD↑     ║
║  SOL/USDT   74.1   -0.0091  +3.4%  ║  14:25:00 SELL   SOL      $212      RSI>70    ║
╠══════════════════════════════════════════════════════════════════════════════════════╣
║  🤖 Activity Log — Next analysis in 47s                                             ║
║  14:30:01  ✅ BUY  BTCUSDT  $83,412  (conf=8)                                      ║
║  14:30:01  ✅ BUY  ETHUSDT  $3,201   (conf=7)                                      ║
║  14:25:00  🔴 SELL SOLUSDT  $143.10  P&L: +$5.20                                  ║
║  14:25:00  ⏸  HOLD ETHUSDT  (conf=4)                                               ║
╠══════════════════════════════════════════════════════════════════════════════════════╣
║  🤖 Claude's View: BTC showing oversold RSI (38) with positive MACD crossover.     ║
║     SOL overbought above Bollinger upper band. ETH neutral — awaiting confirmation. ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
```

---

## 🧠 How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                    BOT ARCHITECTURE                         │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  Binance     │    │  Technical   │    │  Claude AI   │  │
│  │  Public API  │───▶│  Analysis    │───▶│  Analysis    │  │
│  │  (free, no   │    │  Engine      │    │  Engine      │  │
│  │   key needed)│    │              │    │              │  │
│  └──────────────┘    └──────────────┘    └──────┬───────┘  │
│       │                    │                    │           │
│   Live prices          RSI, MACD,          BUY/SELL/HOLD   │
│   OHLCV data           Bollinger,          + confidence    │
│   Volume, 24h          EMA, ATR            + reasoning     │
│                                                 │           │
│                                    ┌────────────▼─────────┐ │
│                                    │  Paper Trading       │ │
│                                    │  Engine              │ │
│                                    │  (simulated $10k)    │ │
│                                    └────────────┬─────────┘ │
│                                                 │           │
│                                    ┌────────────▼─────────┐ │
│                                    │  Live Terminal UI    │ │
│                                    │  (Rich dashboard)    │ │
│                                    └──────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Analysis Cycle (every 5 minutes)

```
Every 5 min:
  1. Fetch 60 hourly candles per coin from Binance
  2. Compute: RSI-14, MACD(12,26,9), Bollinger(20), EMA-20/50, ATR-14
  3. Send all data + portfolio state to Claude
  4. Claude returns JSON signal per coin:
       { "action": "BUY", "confidence": 8, "reasoning": "...", "price_target": 84000 }
  5. If confidence >= 6:  execute paper trade
  6. Update terminal dashboard
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- An Anthropic API key (free to get)
- Internet connection (for live market data)

---

### Step 1 — Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/claude-trading-bot.git
cd claude-trading-bot
```

---

### Step 2 — Install Dependencies

```bash
pip install -r requirements.txt
```

Expected output:
```
Successfully installed anthropic-0.25.0 requests-2.31.0 pandas-2.0.3 numpy-1.24.4 rich-13.7.0
```

---

### Step 3 — Get Your Anthropic API Key

1. Visit 👉 [https://console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys)
2. Click **"Create Key"** → give it a name like `trading-bot`
3. Copy the key — it looks like: `sk-ant-api03-...`

> 💡 New accounts get free credits. Each Claude analysis call costs ~$0.003–0.005.

---

### Step 4 — Configure Your API Key

**Option A — Environment variable (recommended):**

```bash
# Mac / Linux
export ANTHROPIC_API_KEY="sk-ant-your-key-here"

# Windows Command Prompt
set ANTHROPIC_API_KEY=sk-ant-your-key-here

# Windows PowerShell
$env:ANTHROPIC_API_KEY="sk-ant-your-key-here"
```

**Option B — .env file (persistent):**

```bash
cp .env.example .env
# Open .env and paste your key
```

Contents of `.env`:
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

---

### Step 5 — Run the Bot

```bash
# Mac / Linux
./run.sh

# Windows
run.bat

# Or directly with Python
python trading_bot.py
```

Press **`Ctrl+C`** to stop. Your final P&L summary will be printed.

---

## ⚙️ Configuration Options

| Flag | Default | Description | Example |
|------|---------|-------------|---------|
| `--pairs` | BTC ETH SOL | Coins to trade | `--pairs BTC ETH ADA DOGE` |
| `--balance` | 10000 | Starting paper USDT | `--balance 50000` |
| `--interval` | 300 | Seconds between AI analyses | `--interval 120` |
| `--risk` | 0.10 | Fraction of balance per trade | `--risk 0.20` |

### Example Configurations

```bash
# Trade only Bitcoin, $25k balance
python trading_bot.py --pairs BTC --balance 25000

# Trade 5 coins with faster 2-minute analysis
python trading_bot.py --pairs BTC ETH SOL ADA DOGE --interval 120

# Conservative — 5% risk per trade, slow analysis
python trading_bot.py --risk 0.05 --interval 600

# Aggressive — 20% risk, 90-second analysis
python trading_bot.py --risk 0.20 --interval 90
```

---

## 📊 Dashboard Explained

### Prices & Signals Panel

| Column | Meaning |
|--------|---------|
| `Pair` | Crypto pair (e.g. BTC/USDT) |
| `Price` | Current live price |
| `24h %` | 24-hour price change (🟢 positive / 🔴 negative) |
| `Action` | Claude's signal: 🟢 BUY / 🔴 SELL / 🟡 HOLD |
| `Conf` | Confidence score (1–10). Trades only execute at ≥ 6 |
| `AI Prediction` | Claude's predicted price in 1–4 hours |

### Technical Indicators Panel

| Indicator | What It Means |
|-----------|---------------|
| `RSI` | 🟢 < 40 = oversold (buy signal) · 🔴 > 70 = overbought (sell signal) |
| `MACD Hist` | 🟢 positive = bullish momentum · 🔴 negative = bearish |
| `BB %` | Bollinger Band position (0% = lower band, 100% = upper band) |
| `vs EMA20` | How far price is from 20-period moving average |
| `ATR` | Volatility measure (Average True Range) |

### Claude's Decision Logic

```
BUY  conditions:  RSI < 65  AND  price near lower Bollinger  AND  MACD histogram turning positive
SELL conditions:  RSI > 70  OR   price above upper Bollinger  OR   strong downside momentum
HOLD:             Anything else, or confidence < 6
```

---

## 💰 API Cost Estimate

| Usage | Daily Cost |
|-------|-----------|
| Default (5 min, 3 pairs) | ~$0.14/day |
| 2 min interval, 5 pairs | ~$0.50/day |
| 90 sec interval, 5 pairs | ~$1.20/day |

---

## 📁 Project Structure

```
claude-trading-bot/
├── trading_bot.py      # Main bot (all logic in one file)
├── requirements.txt    # Python dependencies
├── run.sh              # Mac/Linux one-click launcher
├── run.bat             # Windows one-click launcher
├── .env.example        # API key template
├── .gitignore          # Ignores .env and __pycache__
└── README.md           # This file
```

---

## ⚠️ Disclaimer

This is a **paper trading bot** — it uses simulated money only. No real funds are ever at risk.

- Past performance does not guarantee future results
- Crypto markets are highly volatile
- This project is for **educational and research purposes only**
- Never invest money you cannot afford to lose in real trading
- Always do your own research (DYOR)

---

## 🛠️ Troubleshooting

**`ANTHROPIC_API_KEY not set` error:**
```bash
export ANTHROPIC_API_KEY="sk-ant-your-key-here"
```

**`ModuleNotFoundError: No module named 'rich'`:**
```bash
pip install -r requirements.txt
```

**`ConnectionError` / Binance unreachable:**
- Check your internet connection
- Binance may be blocked in some regions — try a VPN

**Terminal display looks broken:**
- Use a modern terminal: iTerm2 (Mac), Windows Terminal, or any Linux terminal
- Make sure your terminal window is at least 120 characters wide

---

## 📜 License

MIT License — free to use, modify, and distribute.
