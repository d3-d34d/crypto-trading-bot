#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║         CLAUDE-POWERED CRYPTO TRADING BOT  (Paper Mode)         ║
║  Real-time market data + AI analysis + simulated trading         ║
╚══════════════════════════════════════════════════════════════════╝

HOW IT WORKS:
  1. Fetches live OHLCV data from Binance public API (no key needed)
  2. Computes RSI, MACD, Bollinger Bands, EMA indicators
  3. Sends all market context to Claude every 5 minutes for analysis
  4. Claude returns BUY / SELL / HOLD signals with reasoning
  5. Bot executes paper trades and tracks your portfolio P&L
  6. Everything is displayed in a live, auto-refreshing terminal UI

USAGE:
  export ANTHROPIC_API_KEY="your-key-here"
  python trading_bot.py

  Optional flags:
    --pairs   BTC ETH SOL ADA      # Which coins to trade (default: BTC ETH SOL)
    --balance 50000                 # Starting paper balance in USDT (default: 10000)
    --interval 300                  # Claude analysis interval in seconds (default: 300)
    --risk 0.15                     # Fraction of balance per trade (default: 0.10)
"""

import os
import sys
import time
import json
import argparse
import threading
import requests
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Optional
from collections import deque

try:
    from rich.live import Live
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.console import Console
    from rich import box
    from rich.rule import Rule
    from rich.align import Align
except ImportError:
    print("Missing dependency: pip install rich")
    sys.exit(1)

try:
    import anthropic
except ImportError:
    print("Missing dependency: pip install anthropic")
    sys.exit(1)


# ─────────────────────────────────────────────
# CONFIG (overridden by CLI args)
# ─────────────────────────────────────────────
DEFAULT_PAIRS     = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
DEFAULT_BALANCE   = 10_000.0
DEFAULT_INTERVAL  = 300        # seconds between Claude analyses
DEFAULT_RISK      = 0.10       # 10% of USDT balance per BUY trade
MIN_CONFIDENCE    = 6          # Claude must score >= this to trigger a trade
LOG_LINES         = 12         # number of log messages to keep visible
REFRESH_SECS      = 8          # how often to refresh prices (seconds)
KLINE_LIMIT       = 60         # candles fetched per request (1-hour candles)


# ─────────────────────────────────────────────
# BINANCE PUBLIC DATA FETCHER
# ─────────────────────────────────────────────
class BinanceFetcher:
    BASE = "https://api.binance.com/api/v3"
    HEADERS = {"User-Agent": "claude-trading-bot/1.0"}

    def _get(self, endpoint: str, params: dict) -> dict | list:
        r = requests.get(f"{self.BASE}/{endpoint}", params=params,
                         headers=self.HEADERS, timeout=10)
        r.raise_for_status()
        return r.json()

    def price(self, symbol: str) -> float:
        data = self._get("ticker/price", {"symbol": symbol})
        return float(data["price"])

    def stats_24h(self, symbol: str) -> dict:
        return self._get("ticker/24hr", {"symbol": symbol})

    def klines(self, symbol: str, interval: str = "1h", limit: int = KLINE_LIMIT) -> pd.DataFrame:
        raw = self._get("klines", {"symbol": symbol, "interval": interval, "limit": limit})
        df = pd.DataFrame(raw, columns=[
            "ts", "open", "high", "low", "close", "volume",
            "close_ts", "quote_vol", "trades", "tb_base", "tb_quote", "ignore"
        ])
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)
        return df


# ─────────────────────────────────────────────
# TECHNICAL ANALYSIS
# ─────────────────────────────────────────────
class TA:
    @staticmethod
    def rsi(s: pd.Series, period: int = 14) -> float:
        delta = s.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / (loss + 1e-9)
        return float((100 - 100 / (1 + rs)).iloc[-1])

    @staticmethod
    def macd(s: pd.Series):
        e12 = s.ewm(span=12, adjust=False).mean()
        e26 = s.ewm(span=26, adjust=False).mean()
        m = e12 - e26
        sig = m.ewm(span=9, adjust=False).mean()
        return float(m.iloc[-1]), float(sig.iloc[-1]), float((m - sig).iloc[-1])

    @staticmethod
    def bollinger(s: pd.Series, period: int = 20):
        sma = s.rolling(period).mean()
        std = s.rolling(period).std()
        return float((sma + 2 * std).iloc[-1]), float(sma.iloc[-1]), float((sma - 2 * std).iloc[-1])

    @staticmethod
    def ema(s: pd.Series, span: int) -> float:
        return float(s.ewm(span=span, adjust=False).mean().iloc[-1])

    @staticmethod
    def atr(df: pd.DataFrame, period: int = 14) -> float:
        h, l, c = df["high"], df["low"], df["close"]
        tr = pd.concat([
            h - l,
            (h - c.shift()).abs(),
            (l - c.shift()).abs()
        ], axis=1).max(axis=1)
        return float(tr.rolling(period).mean().iloc[-1])


# ─────────────────────────────────────────────
# PAPER TRADING ENGINE
# ─────────────────────────────────────────────
class PaperEngine:
    def __init__(self, initial_usdt: float):
        self.usdt       = initial_usdt
        self.initial    = initial_usdt
        self.holdings: dict[str, float] = {}   # symbol -> crypto quantity
        self.trades: list[dict]          = []   # full trade log
        self.open_positions: dict[str, float] = {}  # symbol -> entry price

    # ── trade execution ──────────────────────
    def buy(self, symbol: str, price: float, usdt_amount: float, reason: str) -> Optional[dict]:
        usdt_amount = min(usdt_amount, self.usdt * 0.99)
        if usdt_amount < 5 or price <= 0:
            return None
        qty = usdt_amount / price
        self.usdt -= usdt_amount
        self.holdings[symbol] = self.holdings.get(symbol, 0) + qty
        self.open_positions[symbol] = price
        t = dict(time=datetime.now().strftime("%H:%M:%S"), side="BUY",
                 symbol=symbol, price=price, qty=qty, usdt=usdt_amount,
                 reason=reason[:80])
        self.trades.append(t)
        return t

    def sell(self, symbol: str, price: float, reason: str) -> Optional[dict]:
        qty = self.holdings.get(symbol, 0)
        if qty <= 0 or price <= 0:
            return None
        usdt = qty * price
        self.usdt += usdt
        self.holdings[symbol] = 0
        entry = self.open_positions.pop(symbol, price)
        pnl = (price - entry) * qty
        t = dict(time=datetime.now().strftime("%H:%M:%S"), side="SELL",
                 symbol=symbol, price=price, qty=qty, usdt=usdt,
                 reason=reason[:80], pnl=pnl)
        self.trades.append(t)
        return t

    # ── portfolio metrics ─────────────────────
    def total_value(self, prices: dict) -> float:
        return self.usdt + sum(
            qty * prices.get(sym, 0)
            for sym, qty in self.holdings.items()
        )

    def pnl(self, prices: dict) -> float:
        return self.total_value(prices) - self.initial

    def pnl_pct(self, prices: dict) -> float:
        return self.pnl(prices) / self.initial * 100


# ─────────────────────────────────────────────
# CLAUDE AI MARKET ANALYST
# ─────────────────────────────────────────────
class ClaudeAnalyst:
    SYSTEM = """You are an expert algorithmic crypto trading analyst.
You receive structured market data (price, volume, RSI, MACD, Bollinger Bands, EMA)
and must respond with a precise JSON trading signal.
Be data-driven, concise, and decisive. Never hedge or be vague."""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-latest"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model  = model

    def analyze(self, market_data: dict, portfolio: dict) -> dict:
        pairs = list(market_data.keys())
        pair_schema = {p: {
            "action": "BUY | SELL | HOLD",
            "confidence": "1-10 integer",
            "reasoning": "1-2 sentence data-driven justification",
            "price_target": "your predicted price in the next 1-4 hours (number)"
        } for p in pairs}
        pair_schema["market_summary"] = "2-3 sentence overall market read"

        prompt = f"""Analyze this live crypto market snapshot and return a trading signal.

## Portfolio State
{json.dumps(portfolio, indent=2)}

## Market Data
{json.dumps(market_data, indent=2)}

## Signal Rules
- Only recommend BUY if RSI < 65, price is near or below lower Bollinger Band,
  MACD histogram is positive or turning positive, and confidence >= 6.
- Only recommend SELL if RSI > 70, price above upper Bollinger Band,
  or strong downside momentum detected.
- Default to HOLD when signals are mixed or confidence < 6.
- Factor in 24h volume and trend direction.

## Required JSON Response (strict, no extra text):
{json.dumps(pair_schema, indent=2)}"""

        try:
            msg = self.client.messages.create(
                model=self.model,
                max_tokens=1200,
                system=self.SYSTEM,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = msg.content[0].text.strip()
            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            return json.loads(raw.strip())
        except json.JSONDecodeError as e:
            return {"error": f"JSON parse error: {e}", "market_summary": "Analysis failed – JSON error"}
        except Exception as e:
            with open("error_log.txt", "w") as f:
                f.write(str(e))
            return {"error": str(e), "market_summary": f"Analysis failed: {e}"}


# ─────────────────────────────────────────────
# MAIN TRADING BOT
# ─────────────────────────────────────────────
class TradingBot:
    def __init__(self, pairs: list[str], balance: float, interval: int,
                 risk: float, api_key: str):
        self.pairs      = pairs
        self.interval   = interval
        self.risk       = risk

        self.fetcher    = BinanceFetcher()
        self.engine     = PaperEngine(balance)
        self.analyst    = ClaudeAnalyst(api_key)
        self.console    = Console()

        # Shared state (updated by background threads)
        self.prices:     dict[str, float]  = {}
        self.indicators: dict[str, dict]   = {}
        self.signals:    dict[str, dict]   = {}
        self.market_summary: str           = "Waiting for first Claude analysis…"
        self.status:     str               = "Starting up…"
        self.log:        deque             = deque(maxlen=LOG_LINES)
        self.next_analysis_at: float       = time.time()   # run immediately
        self.analysis_count:  int          = 0
        self.lock        = threading.Lock()

    # ── logging helper ────────────────────────
    def _log(self, msg: str, style: str = "white"):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log.appendleft(f"[dim]{ts}[/dim]  [{style}]{msg}[/{style}]")

    # ── market data collection ────────────────
    def _refresh_prices(self):
        for sym in self.pairs:
            try:
                df    = self.fetcher.klines(sym)
                stats = self.fetcher.stats_24h(sym)
                price = float(stats["lastPrice"])

                rsi              = TA.rsi(df["close"])
                macd, sig, hist  = TA.macd(df["close"])
                bb_up, bb_mid, bb_lo = TA.bollinger(df["close"])
                ema20            = TA.ema(df["close"], 20)
                ema50            = TA.ema(df["close"], 50)
                atr_val          = TA.atr(df)
                chg24            = float(stats["priceChangePercent"])
                vol24            = float(stats["volume"])

                with self.lock:
                    self.prices[sym] = price
                    self.indicators[sym] = dict(
                        price       = price,
                        change_24h  = chg24,
                        volume_24h  = vol24,
                        high_24h    = float(stats["highPrice"]),
                        low_24h     = float(stats["lowPrice"]),
                        rsi         = round(rsi, 2),
                        macd        = round(macd, 6),
                        macd_signal = round(sig, 6),
                        macd_hist   = round(hist, 6),
                        bb_upper    = round(bb_up, 4),
                        bb_mid      = round(bb_mid, 4),
                        bb_lower    = round(bb_lo, 4),
                        ema20       = round(ema20, 4),
                        ema50       = round(ema50, 4),
                        atr         = round(atr_val, 4),
                        vs_ema20_pct= round((price - ema20) / ema20 * 100, 3),
                    )
            except Exception as e:
                self._log(f"⚠ Data fetch error [{sym}]: {e}", "yellow")

    # ── Claude analysis cycle ─────────────────
    def _run_analysis(self):
        self.status = "🤖  Claude is thinking…"
        self._log("Requesting Claude market analysis…", "cyan")
        try:
            with self.lock:
                mkt_snapshot = dict(self.indicators)
                portfolio_state = dict(
                    usdt_balance = round(self.engine.usdt, 2),
                    holdings     = {s: round(q, 8) for s, q in self.engine.holdings.items() if q > 0},
                    open_positions = {s: round(p, 4) for s, p in self.engine.open_positions.items()},
                )

            result = self.analyst.analyze(mkt_snapshot, portfolio_state)

            with self.lock:
                if "error" not in result:
                    self.analysis_count += 1
                    self.market_summary = result.get("market_summary", "")
                    for sym in self.pairs:
                        if sym in result:
                            self.signals[sym] = result[sym]

                    # ── execute signals ──────────────────
                    for sym in self.pairs:
                        sig = self.signals.get(sym, {})
                        action     = sig.get("action", "HOLD").upper()
                        confidence = int(sig.get("confidence", 0))
                        reason     = sig.get("reasoning", "")

                        if action == "BUY" and confidence >= MIN_CONFIDENCE:
                            usdt_to_spend = self.engine.usdt * self.risk
                            t = self.engine.buy(sym, self.prices.get(sym, 0), usdt_to_spend, reason)
                            if t:
                                self._log(f"✅ BUY  {sym}  ${t['price']:,.2f}  (conf={confidence})", "green")
                        elif action == "SELL" and confidence >= MIN_CONFIDENCE:
                            t = self.engine.sell(sym, self.prices.get(sym, 0), reason)
                            if t:
                                pnl_str = f"P&L: ${t.get('pnl', 0):+.2f}"
                                self._log(f"🔴 SELL {sym}  ${t['price']:,.2f}  {pnl_str}", "red")
                        else:
                            self._log(f"⏸  HOLD {sym}  (conf={confidence})", "dim")

                    self.status = f"Last analysis: {datetime.now().strftime('%H:%M:%S')}  (#{self.analysis_count})"
                else:
                    self._log(f"Claude error: {result.get('error')}", "yellow")
                    self.status = "⚠ Analysis error – retrying next cycle"

        except Exception as e:
            self._log(f"Analysis exception: {e}", "red")
            self.status = f"Error: {e}"

    # ── Rich terminal dashboard ───────────────
    def _build_layout(self) -> Layout:
        with self.lock:
            prices      = dict(self.prices)
            indicators  = dict(self.indicators)
            signals     = dict(self.signals)
            trades      = list(self.engine.trades)
            holdings    = dict(self.engine.holdings)
            usdt_bal    = self.engine.usdt
            total_val   = self.engine.total_value(prices)
            pnl         = self.engine.pnl(prices)
            pnl_pct     = self.engine.pnl_pct(prices)
            log_lines   = list(self.log)
            summary     = self.market_summary
            status_msg  = self.status
            next_at     = self.next_analysis_at

        secs_left  = max(0, int(next_at - time.time()))
        pnl_color  = "bright_green" if pnl >= 0 else "bright_red"

        # ── HEADER ────────────────────────────────────────
        now_str = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
        header = Text(justify="center")
        header.append("⚡ CLAUDE TRADING BOT ", style="bold bright_cyan")
        header.append("│ PAPER TRADING │ ", style="bold yellow")
        header.append(f"{now_str}  ", style="dim white")
        header.append(f"│  Portfolio: ${total_val:,.2f}  ", style="bold white")
        header.append(f"│  P&L: ", style="white")
        header.append(f"${pnl:+,.2f}  ({pnl_pct:+.2f}%)", style=f"bold {pnl_color}")

        # ── PRICES & SIGNALS TABLE ────────────────────────
        pt = Table(box=box.SIMPLE_HEAD, show_header=True,
                   header_style="bold bright_cyan", expand=True)
        pt.add_column("Pair",       style="cyan",        width=12)
        pt.add_column("Price",      justify="right",     width=14)
        pt.add_column("24h %",      justify="right",     width=8)
        pt.add_column("Action",     justify="center",    width=7)
        pt.add_column("Conf",       justify="center",    width=5)
        pt.add_column("AI Prediction",                   width=30)

        for sym in self.pairs:
            ind  = indicators.get(sym, {})
            sig  = signals.get(sym, {})
            p    = prices.get(sym, 0)
            chg  = ind.get("change_24h", 0)
            act  = sig.get("action", "—").upper()
            conf = sig.get("confidence", 0)
            pred = str(sig.get("price_target", "—"))

            chg_style = "bright_green" if chg >= 0 else "bright_red"
            act_style = {"BUY": "bold bright_green", "SELL": "bold bright_red",
                         "HOLD": "bold yellow"}.get(act, "dim white")
            pt.add_row(
                sym.replace("USDT", "/USDT"),
                f"${p:,.4f}" if p < 1 else f"${p:,.2f}",
                Text(f"{chg:+.2f}%", style=chg_style),
                Text(act, style=act_style),
                str(conf) if conf else "–",
                pred,
            )

        # ── INDICATORS TABLE ───────────────────────────────
        it = Table(box=box.SIMPLE_HEAD, show_header=True,
                   header_style="bold magenta", expand=True)
        it.add_column("Pair",      style="cyan",   width=12)
        it.add_column("RSI",       justify="right", width=7)
        it.add_column("MACD Hist", justify="right", width=11)
        it.add_column("BB %",      justify="right", width=8)
        it.add_column("vs EMA20",  justify="right", width=9)
        it.add_column("ATR",       justify="right", width=10)

        for sym in self.pairs:
            ind = indicators.get(sym, {})
            rsi = ind.get("rsi", 0)
            hist= ind.get("macd_hist", 0)
            p   = ind.get("price", 0)
            bb_up = ind.get("bb_upper", 0)
            bb_lo = ind.get("bb_lower", 0)
            vs20  = ind.get("vs_ema20_pct", 0)
            atr   = ind.get("atr", 0)

            # Bollinger position %
            bb_width = bb_up - bb_lo
            bb_pos   = ((p - bb_lo) / bb_width * 100) if bb_width else 0

            rsi_style  = ("bright_green" if rsi < 40 else
                          "bright_red"   if rsi > 70 else "white")
            hist_style = "bright_green" if hist > 0 else "bright_red"
            vs_style   = "bright_green" if vs20 > 0 else "bright_red"

            it.add_row(
                sym.replace("USDT", "/USDT"),
                Text(f"{rsi:.1f}", style=rsi_style),
                Text(f"{hist:+.5f}", style=hist_style),
                f"{bb_pos:.1f}%",
                Text(f"{vs20:+.2f}%", style=vs_style),
                f"{atr:.4f}",
            )

        # ── PORTFOLIO TABLE ────────────────────────────────
        ptf = Table(box=box.SIMPLE_HEAD, show_header=True,
                    header_style="bold bright_green", expand=True)
        ptf.add_column("Asset",    style="cyan",    width=10)
        ptf.add_column("Qty",      justify="right",  width=14)
        ptf.add_column("Value",    justify="right",  width=14)
        ptf.add_column("Entry",    justify="right",  width=12)
        ptf.add_column("P&L",      justify="right",  width=10)

        ptf.add_row("USDT", "—", f"${usdt_bal:,.2f}", "—", "—")
        for sym, qty in holdings.items():
            if qty > 0.0000001:
                p     = prices.get(sym, 0)
                val   = qty * p
                entry = self.engine.open_positions.get(sym, 0)
                pos_pnl = (p - entry) * qty if entry else 0
                pnl_sty = "bright_green" if pos_pnl >= 0 else "bright_red"
                ptf.add_row(
                    sym.replace("USDT", ""),
                    f"{qty:.6f}",
                    f"${val:,.2f}",
                    f"${entry:,.2f}",
                    Text(f"${pos_pnl:+.2f}", style=pnl_sty),
                )

        # ── TRADE LOG TABLE ────────────────────────────────
        tlt = Table(box=box.SIMPLE_HEAD, show_header=True,
                    header_style="bold yellow", expand=True)
        tlt.add_column("Time",   width=8)
        tlt.add_column("Side",   width=5)
        tlt.add_column("Symbol", width=9)
        tlt.add_column("Price",  justify="right", width=12)
        tlt.add_column("USDT",   justify="right", width=11)
        tlt.add_column("Reason", width=40)

        for t in reversed(trades[-10:]):
            side_sty = "bold bright_green" if t["side"] == "BUY" else "bold bright_red"
            tlt.add_row(
                t["time"],
                Text(t["side"], style=side_sty),
                t["symbol"].replace("USDT", ""),
                f"${t['price']:,.2f}",
                f"${t['usdt']:,.2f}",
                t.get("reason", "")[:40],
            )

        # ── AI LOG ────────────────────────────────────────
        ai_log = "\n".join(log_lines) if log_lines else "[dim]No events yet[/dim]"

        # ── ASSEMBLE LAYOUT ───────────────────────────────
        layout = Layout()
        layout.split_column(
            Layout(name="header",  size=3),
            Layout(name="body"),
            Layout(name="ai",      size=5),
            Layout(name="footer",  size=3),
        )
        layout["body"].split_row(
            Layout(name="left"),
            Layout(name="right"),
        )
        layout["left"].split_column(
            Layout(name="prices",     ratio=2),
            Layout(name="indicators", ratio=2),
        )
        layout["right"].split_column(
            Layout(name="portfolio",  ratio=2),
            Layout(name="tradelog",   ratio=3),
        )

        layout["header"].update(Panel(header, style="bold"))
        layout["prices"].update(Panel(pt,  title="[bold bright_cyan]📈 Live Prices & AI Signals[/]"))
        layout["indicators"].update(Panel(it, title="[bold magenta]📊 Technical Indicators[/]"))
        layout["portfolio"].update(Panel(ptf, title="[bold bright_green]💼 Portfolio[/]"))
        layout["tradelog"].update(Panel(tlt, title="[bold yellow]📋 Trade History (latest 10)[/]"))
        layout["ai"].update(Panel(
            ai_log,
            title=f"[bold cyan]🤖 Activity Log  —  Next analysis in {secs_left}s[/]",
        ))
        layout["footer"].update(Panel(
            Text.from_markup(f"[bold cyan]Claude's Market View:[/bold cyan]  {summary}\n"
                             f"[dim]{status_msg}[/dim]"),
        ))
        return layout

    # ── background threads ────────────────────
    def _price_loop(self):
        while self._running:
            self._refresh_prices()
            time.sleep(REFRESH_SECS)

    def _analysis_loop(self):
        while self._running:
            now = time.time()
            if now >= self.next_analysis_at:
                if self.prices:        # only analyze once we have price data
                    self._run_analysis()
                    self.next_analysis_at = time.time() + self.interval
                else:
                    time.sleep(2)
            else:
                time.sleep(1)

    # ── entry point ───────────────────────────
    def run(self):
        self._running = True
        self._log("Bot started. Fetching initial market data…", "cyan")

        # Start background threads
        t1 = threading.Thread(target=self._price_loop,    daemon=True)
        t2 = threading.Thread(target=self._analysis_loop, daemon=True)
        t1.start()
        t2.start()

        # Initial data load – wait until we have prices
        self.console.print("[cyan]Loading market data…[/cyan]")
        for _ in range(30):
            if len(self.prices) == len(self.pairs):
                break
            time.sleep(1)

        # Live display loop
        try:
            with Live(self._build_layout(), refresh_per_second=0.5,
                      screen=True, redirect_stderr=False) as live:
                while True:
                    live.update(self._build_layout())
                    time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self._running = False
            self.console.print("\n[yellow]Bot stopped. Goodbye![/yellow]")
            pnl = self.engine.pnl(self.prices)
            self.console.print(f"Final P&L: [{'green' if pnl >= 0 else 'red'}]${pnl:+,.2f}[/]")
            self.console.print(f"Total trades: {len(self.engine.trades)}")


# ─────────────────────────────────────────────
# CLI ENTRY POINT
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Claude-Powered Crypto Paper Trading Bot"
    )
    parser.add_argument("--pairs",    nargs="+", default=None,
                        help="Coin symbols e.g. BTC ETH SOL (USDT pairs)")
    parser.add_argument("--balance",  type=float, default=DEFAULT_BALANCE,
                        help=f"Starting paper USDT (default: {DEFAULT_BALANCE})")
    parser.add_argument("--interval", type=int,   default=DEFAULT_INTERVAL,
                        help=f"Claude analysis interval in seconds (default: {DEFAULT_INTERVAL})")
    parser.add_argument("--risk",     type=float, default=DEFAULT_RISK,
                        help=f"Fraction of USDT to risk per trade (default: {DEFAULT_RISK})")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("\n❌  ANTHROPIC_API_KEY environment variable is not set.")
        print("    Get your key at: https://console.anthropic.com/settings/keys")
        print("    Then run:  export ANTHROPIC_API_KEY='sk-ant-...'")
        sys.exit(1)

    if args.pairs:
        pairs = [p.upper() + ("USDT" if not p.upper().endswith("USDT") else "")
                 for p in args.pairs]
    else:
        pairs = DEFAULT_PAIRS

    console = Console()
    console.print(f"\n[bold bright_cyan]⚡ Claude-Powered Crypto Trading Bot[/bold bright_cyan]")
    console.print(f"   Pairs:    [cyan]{', '.join(pairs)}[/cyan]")
    console.print(f"   Balance:  [green]${args.balance:,.2f} USDT (paper)[/green]")
    console.print(f"   Interval: [yellow]{args.interval}s between AI analyses[/yellow]")
    console.print(f"   Risk:     [yellow]{args.risk*100:.0f}% per trade[/yellow]")
    console.print(f"\n[dim]Press Ctrl+C to stop.[/dim]\n")
    time.sleep(1.5)

    bot = TradingBot(
        pairs    = pairs,
        balance  = args.balance,
        interval = args.interval,
        risk     = args.risk,
        api_key  = api_key,
    )
    bot.run()


if __name__ == "__main__":
    main()
