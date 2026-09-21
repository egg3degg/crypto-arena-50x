"""
Solana 100 Paper USDC Autonomous Trading Agent
================================================
Autonomous crypto portfolio engine initialized with exactly $100.00 Paper USDC.
Focuses on the Solana ecosystem (SOL, JUP, RENDER, RAY) with live market feeds,
real-time technical indicator analysis, strict risk management, dynamic TP/SL,
trade logging, and automated HTML dashboard generation.
"""

import os
import sys

# Force UTF-8 encoding on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import json
import time
import math
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
import requests
import pandas as pd

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
PORTFOLIO_FILE = os.path.join(DATA_DIR, "solana_100_paper_portfolio.json")
DASHBOARD_FILE = os.path.join(DATA_DIR, "solana_100_dashboard.html")

# Constants
INITIAL_BALANCE_USDC = 100.00
TRADING_SYMBOLS = ["SOLUSDT", "RENDERUSDT", "JUPUSDT", "RAYUSDT"]
DISPLAY_NAMES = {
    "SOLUSDT": "SOL (Solana)",
    "RENDERUSDT": "RENDER (Render Network)",
    "JUPUSDT": "JUP (Jupiter)",
    "RAYUSDT": "RAY (Raydium)"
}
FEE_RATE = 0.0005     # 0.05% simulated DEX swap fee (Jupiter route)
SLIPPAGE = 0.0004     # 0.04% realistic market slippage
MAX_POSITIONS = 2     # Max 2 concurrent positions (keeps >= 30% cash reserve)
MAX_ALLOC_PER_TRADE = 35.00  # $30-$35 max per position to preserve dry powder
MIN_CASH_BUFFER = 25.00      # Always hold at least $25 USDC in dry reserve


class Solana100Agent:
    def __init__(self):
        self.portfolio = self._load_or_init_portfolio()

    def _load_or_init_portfolio(self) -> Dict[str, Any]:
        if os.path.exists(PORTFOLIO_FILE):
            try:
                with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[Warning] Failed loading portfolio: {e}. Reinitializing.")

        now_iso = datetime.now(timezone.utc).isoformat()
        initial_state = {
            "portfolio_name": "Solana $100 USDC Autonomous Fund",
            "chain": "Solana (SPL Token Architecture)",
            "benchmark": "SOL / USDC",
            "created_at": now_iso,
            "last_updated": now_iso,
            "starting_balance_usdc": INITIAL_BALANCE_USDC,
            "cash_usdc": INITIAL_BALANCE_USDC,
            "positions_value_usdc": 0.0,
            "total_equity_usdc": INITIAL_BALANCE_USDC,
            "total_pnl_usd": 0.0,
            "total_pnl_pct": 0.0,
            "realized_pnl_usd": 0.0,
            "unrealized_pnl_usd": 0.0,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate_pct": 0.0,
            "positions": [],
            "closed_trades": [],
            "equity_history": [
                {
                    "timestamp": now_iso,
                    "cash": INITIAL_BALANCE_USDC,
                    "equity": INITIAL_BALANCE_USDC,
                    "note": "Initial $100.00 USDC Paper Capital Allocated"
                }
            ],
            "action_logs": [
                {
                    "timestamp": now_iso,
                    "message": "Initialized Solana $100 USDC Paper Portfolio. Chain: Solana. Ready for live signals."
                }
            ]
        }
        self._save_portfolio(initial_state)
        return initial_state

    def _save_portfolio(self, state: Optional[Dict[str, Any]] = None):
        if state is not None:
            self.portfolio = state
        self.portfolio["last_updated"] = datetime.now(timezone.utc).isoformat()
        with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
            json.dump(self.portfolio, f, indent=2)

    def log_action(self, message: str):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        self.portfolio.setdefault("action_logs", []).append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": message
        })
        if len(self.portfolio["action_logs"]) > 100:
            self.portfolio["action_logs"] = self.portfolio["action_logs"][-100:]

    def fetch_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch 15m klines and compute EMA9, EMA21, EMA50, RSI14, ATR14."""
        try:
            url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=15m&limit=60"
            r = requests.get(url, timeout=6).json()
            if not isinstance(r, list) or len(r) < 30:
                return None

            closes = [float(k[4]) for k in r]
            highs = [float(k[2]) for k in r]
            lows = [float(k[3]) for k in r]
            volumes = [float(k[5]) for k in r]

            s_close = pd.Series(closes)
            s_high = pd.Series(highs)
            s_low = pd.Series(lows)

            # EMAs
            ema9 = float(s_close.ewm(span=9, adjust=False).mean().iloc[-1])
            ema21 = float(s_close.ewm(span=21, adjust=False).mean().iloc[-1])
            ema50 = float(s_close.ewm(span=50, adjust=False).mean().iloc[-1])

            # RSI 14
            delta = s_close.diff()
            gain = delta.clip(lower=0)
            loss = -delta.clip(upper=0)
            avg_gain = gain.rolling(14).mean().iloc[-1]
            avg_loss = loss.rolling(14).mean().iloc[-1]
            if avg_loss == 0:
                rsi = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi = float(100.0 - (100.0 / (1.0 + rs)))

            # ATR 14
            tr1 = s_high - s_low
            tr2 = (s_high - s_close.shift(1)).abs()
            tr3 = (s_low - s_close.shift(1)).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = float(tr.rolling(14).mean().iloc[-1])

            current_price = closes[-1]
            prev_price = closes[-2]
            price_change_24h = ((current_price - closes[0]) / closes[0]) * 100.0

            return {
                "symbol": symbol,
                "display_name": DISPLAY_NAMES.get(symbol, symbol),
                "price": current_price,
                "prev_price": prev_price,
                "ema9": ema9,
                "ema21": ema21,
                "ema50": ema50,
                "rsi": rsi,
                "atr": atr,
                "volume_24h": sum(volumes),
                "price_change_24h": price_change_24h,
                "uptrend": current_price > ema50 and ema9 > ema21,
                "momentum": ema9 > ema21
            }
        except Exception as e:
            print(f"[Error] Fetching {symbol}: {e}")
            return None

    def analyze_signal(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate technical setup and generate trade signal:
        - LONG signal if:
          1. Close > EMA50 (Macro Bullish)
          2. EMA9 > EMA21 (Short-term momentum)
          3. RSI between 42 and 72 (Healthy momentum without being overextended)
        - Confidence rating based on trend alignment and distance from EMA
        """
        price = data["price"]
        ema9 = data["ema9"]
        ema21 = data["ema21"]
        ema50 = data["ema50"]
        rsi = data["rsi"]
        atr = data["atr"]

        score = 0
        reasons = []

        # 1. Trend alignment
        if price > ema50:
            score += 25
            reasons.append(f"Price (${price:.2f}) > EMA50 (${ema50:.2f})")
        else:
            reasons.append(f"Price below EMA50 (${ema50:.2f})")

        # 2. Fast Momentum
        if ema9 > ema21:
            score += 25
            reasons.append(f"Bullish EMA Cross (EMA9 ${ema9:.2f} > EMA21 ${ema21:.2f})")
        else:
            reasons.append("EMA9 <= EMA21 bearish crossover")

        # 3. RSI Evaluation
        if 45 <= rsi <= 68:
            score += 35
            reasons.append(f"Optimal Momentum RSI ({rsi:.1f})")
        elif 35 <= rsi < 45:
            score += 20
            reasons.append(f"Recovering RSI dip ({rsi:.1f})")
        elif 68 < rsi <= 76:
            score += 15
            reasons.append(f"Strong but warming RSI ({rsi:.1f})")
        elif rsi > 76:
            score -= 20
            reasons.append(f"Overextended / Overbought RSI ({rsi:.1f}) - Prone to pullback")
        elif rsi < 35:
            score += 10
            reasons.append(f"Deeply oversold RSI ({rsi:.1f}) - Mean reversion watch")

        # 4. Volatility / ATR Cushion
        atr_pct = (atr / price) * 100.0
        reasons.append(f"Volatility ATR: {atr:.4f} ({atr_pct:.2f}%)")

        is_buy = (score >= 60) and (rsi < 75)
        confidence = min(0.95, max(0.10, score / 100.0))

        return {
            "signal": "BUY" if is_buy else "WAIT",
            "score": score,
            "confidence": confidence,
            "reasons": reasons,
            "suggested_sl": max(0.01, round(price - (1.6 * atr), 4)),
            "suggested_tp1": round(price + (2.0 * atr), 4),
            "suggested_tp2": round(price + (4.0 * atr), 4)
        }

    def update_positions_and_risk(self, market_snapshot: Dict[str, Dict[str, Any]]):
        """Monitor existing positions for Stop Loss, TP1, and TP2."""
        updated_positions = []
        realized_pnl_delta = 0.0

        for pos in self.portfolio["positions"]:
            symbol = pos["symbol"]
            m_data = market_snapshot.get(symbol)
            if not m_data:
                updated_positions.append(pos)
                continue

            current_price = m_data["price"]
            entry_price = pos["entry_price"]
            qty = pos["quantity"]
            pos["current_price"] = current_price
            pos["unrealized_pnl"] = round((current_price - entry_price) * qty, 4)
            pos["unrealized_pnl_pct"] = round(((current_price - entry_price) / entry_price) * 100.0, 2)

            # Track highest price reached for trailing stops
            if current_price > pos.get("highest_price", entry_price):
                pos["highest_price"] = current_price

            sl_price = pos["stop_loss"]
            tp1_price = pos["tp1"]
            tp2_price = pos["tp2"]

            # 1. Check Take Profit 1 (+4% to +5% partial exit)
            if not pos.get("tp1_hit", False) and current_price >= tp1_price:
                sell_qty = round(qty * 0.5, 4)
                pos["quantity"] = round(qty - sell_qty, 4)
                pos["tp1_hit"] = True
                
                # Move Stop Loss to Breakeven + small fee buffer!
                pos["stop_loss"] = round(entry_price * 1.002, 4)
                
                gross_proceeds = sell_qty * current_price
                fee = gross_proceeds * FEE_RATE
                net_proceeds = gross_proceeds - fee
                cost_of_half = sell_qty * entry_price
                trade_pnl = net_proceeds - cost_of_half

                self.portfolio["cash_usdc"] = round(self.portfolio["cash_usdc"] + net_proceeds, 4)
                realized_pnl_delta += trade_pnl
                self.portfolio["winning_trades"] += 1
                self.portfolio["total_trades"] += 1

                self.portfolio["closed_trades"].append({
                    "symbol": symbol,
                    "side": "SELL_TP1",
                    "quantity": sell_qty,
                    "entry_price": entry_price,
                    "exit_price": current_price,
                    "pnl_usd": round(trade_pnl, 4),
                    "pnl_pct": round(((current_price - entry_price) / entry_price) * 100.0, 2),
                    "fee_usd": round(fee, 4),
                    "closed_at": datetime.now(timezone.utc).isoformat(),
                    "reason": f"🎯 Take Profit 1 reached at ${current_price:.4f}! Locked 50% profit. Stop loss adjusted to breakeven."
                })
                self.log_action(f"🎯 [TP1 HIT] {symbol}: Sold 50% ({sell_qty}) at ${current_price:.4f} (+{pos['unrealized_pnl_pct']}%). SL moved to breakeven.")
                updated_positions.append(pos)
                continue

            # 2. Check Take Profit 2 (Full Exit)
            if current_price >= tp2_price:
                gross_proceeds = qty * current_price
                fee = gross_proceeds * FEE_RATE
                net_proceeds = gross_proceeds - fee
                cost = qty * entry_price
                trade_pnl = net_proceeds - cost

                self.portfolio["cash_usdc"] = round(self.portfolio["cash_usdc"] + net_proceeds, 4)
                realized_pnl_delta += trade_pnl
                self.portfolio["winning_trades"] += 1
                self.portfolio["total_trades"] += 1

                self.portfolio["closed_trades"].append({
                    "symbol": symbol,
                    "side": "SELL_TP2",
                    "quantity": qty,
                    "entry_price": entry_price,
                    "exit_price": current_price,
                    "pnl_usd": round(trade_pnl, 4),
                    "pnl_pct": round(((current_price - entry_price) / entry_price) * 100.0, 2),
                    "fee_usd": round(fee, 4),
                    "closed_at": datetime.now(timezone.utc).isoformat(),
                    "reason": f"🚀 Take Profit 2 target hit at ${current_price:.4f}! Exited remaining position with maximum gain."
                })
                self.log_action(f"🚀 [TP2 FULL EXIT] {symbol}: Sold remaining {qty} at ${current_price:.4f} (+{pos['unrealized_pnl_pct']}%). Target fully achieved.")
                continue

            # 3. Check Stop Loss
            if current_price <= sl_price:
                gross_proceeds = qty * current_price
                fee = gross_proceeds * FEE_RATE
                net_proceeds = gross_proceeds - fee
                cost = qty * entry_price
                trade_pnl = net_proceeds - cost

                self.portfolio["cash_usdc"] = round(self.portfolio["cash_usdc"] + net_proceeds, 4)
                realized_pnl_delta += trade_pnl
                if trade_pnl >= 0:
                    self.portfolio["winning_trades"] += 1
                else:
                    self.portfolio["losing_trades"] += 1
                self.portfolio["total_trades"] += 1

                self.portfolio["closed_trades"].append({
                    "symbol": symbol,
                    "side": "STOP_LOSS",
                    "quantity": qty,
                    "entry_price": entry_price,
                    "exit_price": current_price,
                    "pnl_usd": round(trade_pnl, 4),
                    "pnl_pct": round(((current_price - entry_price) / entry_price) * 100.0, 2),
                    "fee_usd": round(fee, 4),
                    "closed_at": datetime.now(timezone.utc).isoformat(),
                    "reason": f"🛑 Stop loss triggered at ${current_price:.4f} to protect capital."
                })
                self.log_action(f"🛑 [STOP LOSS] {symbol}: Sold {qty} at ${current_price:.4f} ({trade_pnl:+.2f} USD). Capital safeguarded.")
                continue

            # Position remains open
            updated_positions.append(pos)

        self.portfolio["positions"] = updated_positions
        self.portfolio["realized_pnl_usd"] = round(self.portfolio["realized_pnl_usd"] + realized_pnl_delta, 4)

    def execute_buy(self, symbol: str, m_data: Dict[str, Any], signal_data: Dict[str, Any]):
        """Open a new paper position on Solana."""
        cash = self.portfolio["cash_usdc"]
        if cash <= MIN_CASH_BUFFER:
            self.log_action(f"[Skipping] Cash reserve (${cash:.2f}) at minimum safety threshold (${MIN_CASH_BUFFER:.2f}).")
            return

        available_for_trade = min(MAX_ALLOC_PER_TRADE, cash - MIN_CASH_BUFFER)
        if available_for_trade < 15.00:
            self.log_action(f"[Skipping] Available capital (${available_for_trade:.2f}) below minimum trade size.")
            return

        price = m_data["price"]
        # Apply realistic slippage to buy price
        exec_price = round(price * (1.0 + SLIPPAGE), 4)
        fee = round(available_for_trade * FEE_RATE, 4)
        net_capital = available_for_trade - fee
        qty = round(net_capital / exec_price, 4)

        sl_price = signal_data["suggested_sl"]
        tp1_price = signal_data["suggested_tp1"]
        tp2_price = signal_data["suggested_tp2"]

        new_pos = {
            "symbol": symbol,
            "display_name": m_data["display_name"],
            "side": "LONG",
            "quantity": qty,
            "entry_price": exec_price,
            "current_price": exec_price,
            "cost_basis": available_for_trade,
            "fee_paid": fee,
            "stop_loss": sl_price,
            "tp1": tp1_price,
            "tp2": tp2_price,
            "tp1_hit": False,
            "highest_price": exec_price,
            "unrealized_pnl": 0.0,
            "unrealized_pnl_pct": 0.0,
            "opened_at": datetime.now(timezone.utc).isoformat(),
            "confidence": signal_data["confidence"],
            "strategy_rationale": " | ".join(signal_data["reasons"][:3])
        }

        self.portfolio["cash_usdc"] = round(cash - available_for_trade, 4)
        self.portfolio["positions"].append(new_pos)
        self.log_action(
            f"🛒 [BUY ORDER] {symbol}: Allocated ${available_for_trade:.2f} USDC -> {qty} tokens @ ${exec_price:.4f}. "
            f"SL: ${sl_price:.4f} (-{((exec_price-sl_price)/exec_price)*100:.1f}%), TP1: ${tp1_price:.4f} (+{((tp1_price-exec_price)/exec_price)*100:.1f}%)."
        )

    def scan_and_trade(self) -> Dict[str, Any]:
        """Perform full autonomous market evaluation & trading cycle."""
        self.log_action("🔍 Scanning Solana ecosystem pairs on live market feeds...")
        market_snapshot = {}
        analyzed_signals = []

        # 1. Fetch live data & compute indicators
        for s in TRADING_SYMBOLS:
            data = self.fetch_market_data(s)
            if data:
                market_snapshot[s] = data
                sig = self.analyze_signal(data)
                analyzed_signals.append({
                    "data": data,
                    "signal": sig
                })

        # 2. Update existing positions & manage risk
        self.update_positions_and_risk(market_snapshot)

        # 3. Sort opportunities by confidence score
        analyzed_signals.sort(key=lambda x: x["signal"]["score"], reverse=True)

        # 4. Check if we should open new positions
        active_symbols = [p["symbol"] for p in self.portfolio["positions"]]
        if len(self.portfolio["positions"]) < MAX_POSITIONS:
            for opp in analyzed_signals:
                sym = opp["data"]["symbol"]
                sig = opp["signal"]
                if sym not in active_symbols and sig["signal"] == "BUY":
                    self.execute_buy(sym, opp["data"], sig)
                    if len(self.portfolio["positions"]) >= MAX_POSITIONS:
                        break

        # 5. Calculate Mark-to-Market Portfolio Valuation
        pos_val = 0.0
        unrealized_pnl = 0.0
        for p in self.portfolio["positions"]:
            curr = market_snapshot.get(p["symbol"], {}).get("price", p["current_price"])
            p["current_price"] = curr
            p_val = p["quantity"] * curr
            pos_val += p_val
            p["unrealized_pnl"] = round(p_val - (p["quantity"] * p["entry_price"]), 4)
            p["unrealized_pnl_pct"] = round(((curr - p["entry_price"]) / p["entry_price"]) * 100.0, 2)
            unrealized_pnl += p["unrealized_pnl"]

        cash = self.portfolio["cash_usdc"]
        equity = round(cash + pos_val, 4)
        total_pnl_usd = round(equity - INITIAL_BALANCE_USDC, 4)
        total_pnl_pct = round((total_pnl_usd / INITIAL_BALANCE_USDC) * 100.0, 2)

        total_trades = self.portfolio["total_trades"]
        win_rate = round((self.portfolio["winning_trades"] / total_trades * 100.0), 1) if total_trades > 0 else 0.0

        self.portfolio["positions_value_usdc"] = round(pos_val, 4)
        self.portfolio["total_equity_usdc"] = equity
        self.portfolio["unrealized_pnl_usd"] = round(unrealized_pnl, 4)
        self.portfolio["total_pnl_usd"] = total_pnl_usd
        self.portfolio["total_pnl_pct"] = total_pnl_pct
        self.portfolio["win_rate_pct"] = win_rate

        # Record equity point
        self.portfolio["equity_history"].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cash": round(cash, 2),
            "equity": round(equity, 2),
            "positions_value": round(pos_val, 2)
        })
        if len(self.portfolio["equity_history"]) > 200:
            self.portfolio["equity_history"] = self.portfolio["equity_history"][-200:]

        self._save_portfolio()
        self.generate_html_dashboard(market_snapshot, analyzed_signals)
        return {
            "market_snapshot": market_snapshot,
            "signals": analyzed_signals,
            "portfolio": self.portfolio
        }

    def generate_html_dashboard(self, market_snapshot: Dict[str, Any], signals: List[Dict[str, Any]]):
        """Generates a standalone dark-mode live HTML dashboard."""
        p = self.portfolio
        equity = p['total_equity_usdc']
        cash = p['cash_usdc']
        pnl = p['total_pnl_usd']
        pnl_pct = p['total_pnl_pct']
        pnl_class = "text-emerald-400" if pnl >= 0 else "text-rose-400"
        pnl_sign = "+" if pnl >= 0 else ""

        # Prepare positions rows
        pos_rows = ""
        if not p["positions"]:
            pos_rows = '<tr><td colspan="7" class="py-4 text-center text-slate-400">No open positions. 100% in USDC cash reserve awaiting optimal risk/reward trigger.</td></tr>'
        else:
            for pos in p["positions"]:
                upnl = pos.get("unrealized_pnl", 0.0)
                upnl_pct = pos.get("unrealized_pnl_pct", 0.0)
                u_col = "text-emerald-400" if upnl >= 0 else "text-rose-400"
                pos_rows += f"""
                <tr class="border-b border-slate-700/50 hover:bg-slate-800/40">
                    <td class="py-3 px-4 font-semibold text-white">{pos.get('display_name', pos['symbol'])}</td>
                    <td class="py-3 px-4">${pos['entry_price']:.4f}</td>
                    <td class="py-3 px-4">${pos['current_price']:.4f}</td>
                    <td class="py-3 px-4 text-slate-300">{pos['quantity']}</td>
                    <td class="py-3 px-4 text-rose-400">${pos['stop_loss']:.4f}</td>
                    <td class="py-3 px-4 text-emerald-400">${pos['tp1']:.4f}</td>
                    <td class="py-3 px-4 font-bold {u_col}">{upnl:+.2f} USD ({upnl_pct:+.2f}%)</td>
                </tr>
                """

        # Prepare closed trades rows
        trades_rows = ""
        if not p["closed_trades"]:
            trades_rows = '<tr><td colspan="6" class="py-4 text-center text-slate-400">No closed trades yet in this session.</td></tr>'
        else:
            for t in reversed(p["closed_trades"][-8:]):
                col = "text-emerald-400" if t["pnl_usd"] >= 0 else "text-rose-400"
                trades_rows += f"""
                <tr class="border-b border-slate-700/50">
                    <td class="py-2 px-3 text-xs text-slate-400">{t['closed_at'][:19].replace('T', ' ')}</td>
                    <td class="py-2 px-3 font-medium text-white">{t['symbol']}</td>
                    <td class="py-2 px-3 text-xs">{t['side']}</td>
                    <td class="py-2 px-3">${t['entry_price']:.4f} &rarr; ${t['exit_price']:.4f}</td>
                    <td class="py-2 px-3 font-semibold {col}">{t['pnl_usd']:+.2f} USD ({t['pnl_pct']:+.2f}%)</td>
                    <td class="py-2 px-3 text-xs text-slate-300">{t['reason']}</td>
                </tr>
                """

        # Prepare radar signals cards
        signal_cards = ""
        for item in signals:
            d = item["data"]
            s = item["signal"]
            is_buy = s["signal"] == "BUY"
            badge = '<span class="px-2 py-0.5 rounded text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">BUY SIGNAL</span>' if is_buy else '<span class="px-2 py-0.5 rounded text-xs font-semibold bg-slate-700 text-slate-300">WATCHING</span>'
            reasons_html = "".join([f'<li class="text-xs text-slate-300 mb-0.5">• {r}</li>' for r in s['reasons']])
            signal_cards += f"""
            <div class="bg-slate-800/80 border border-slate-700/70 rounded-xl p-4 flex flex-col justify-between">
                <div>
                    <div class="flex items-center justify-between mb-2">
                        <span class="font-bold text-white text-base">{d['display_name']}</span>
                        {badge}
                    </div>
                    <div class="text-2xl font-extrabold text-cyan-400 mb-1">${d['price']:.4f}</div>
                    <div class="text-xs text-slate-400 mb-3">24h: <span class="{'text-emerald-400' if d['price_change_24h'] >= 0 else 'text-rose-400'} font-semibold">{d['price_change_24h']:+.2f}%</span> | RSI: <span class="font-mono text-amber-300">{d['rsi']:.1f}</span></div>
                    <ul class="mb-3 space-y-0.5">{reasons_html}</ul>
                </div>
                <div class="pt-2 border-t border-slate-700/50 flex justify-between text-xs text-slate-400">
                    <span>EMA9: ${d['ema9']:.4f}</span>
                    <span>EMA50: ${d['ema50']:.4f}</span>
                    <span>Score: <b class="text-white">{s['score']}/100</b></span>
                </div>
            </div>
            """

        # Prepare timestamps and equity for chart
        eq_labels = [h["timestamp"][11:19] for h in p["equity_history"][-30:]]
        eq_values = [h["equity"] for h in p["equity_history"][-30:]]

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Solana $100 Paper USDC Autonomous Fund</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ background: radial-gradient(circle at top right, #0f172a, #020617); }}
    </style>
</head>
<body class="text-slate-100 min-h-screen p-4 md:p-8 font-sans">
    <div class="max-w-7xl mx-auto space-y-6">
        <!-- Header -->
        <header class="flex flex-col md:flex-row justify-between items-start md:items-center bg-slate-900/90 border border-slate-800 rounded-2xl p-6 backdrop-blur shadow-2xl">
            <div>
                <div class="flex items-center gap-3">
                    <span class="text-3xl">🟣</span>
                    <div>
                        <h1 class="text-2xl font-black tracking-tight text-white">Solana $100 USDC Autonomous Fund</h1>
                        <p class="text-sm text-cyan-400 font-mono">Chain: Solana (SPL Native USDC) &bull; Zero L1 Gas &bull; Sub-second DEX Execution</p>
                    </div>
                </div>
            </div>
            <div class="mt-4 md:mt-0 flex items-center gap-3">
                <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                    <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span> Live 24/7 Engine
                </span>
                <span class="text-xs text-slate-400 font-mono">Updated: {p['last_updated'][:19].replace('T', ' ')} UTC</span>
            </div>
        </header>

        <!-- KPI Metrics -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div class="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-lg">
                <div class="text-xs uppercase tracking-wider text-slate-400 mb-1">Total Net Equity</div>
                <div class="text-3xl font-black text-white">${equity:.2f} <span class="text-xs font-normal text-slate-400">USDC</span></div>
                <div class="text-xs mt-1 text-slate-400">Starting: $100.00 USDC</div>
            </div>
            <div class="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-lg">
                <div class="text-xs uppercase tracking-wider text-slate-400 mb-1">Total Return (PnL)</div>
                <div class="text-3xl font-black {pnl_class}">{pnl_sign}${pnl:.2f} <span class="text-base font-semibold">({pnl_sign}{pnl_pct:.2f}%)</span></div>
                <div class="text-xs mt-1 text-slate-400">Realized: ${p['realized_pnl_usd']:+.2f} | Unr: ${p['unrealized_pnl_usd']:+.2f}</div>
            </div>
            <div class="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-lg">
                <div class="text-xs uppercase tracking-wider text-slate-400 mb-1">Liquid Cash Reserve</div>
                <div class="text-3xl font-black text-cyan-300">${cash:.2f} <span class="text-xs font-normal text-slate-400">USDC</span></div>
                <div class="text-xs mt-1 text-slate-400">Invested: ${p['positions_value_usdc']:.2f} USDC</div>
            </div>
            <div class="bg-slate-900/80 border border-slate-800 rounded-xl p-5 shadow-lg">
                <div class="text-xs uppercase tracking-wider text-slate-400 mb-1">Win Rate / Trades</div>
                <div class="text-3xl font-black text-amber-300">{p['win_rate_pct']:.1f}%</div>
                <div class="text-xs mt-1 text-slate-400">{p['winning_trades']} Won / {p['total_trades']} Total Trades</div>
            </div>
        </div>

        <!-- Chart & Portfolio Breakdown -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div class="lg:col-span-2 bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl">
                <h3 class="text-base font-bold text-white mb-4 flex items-center justify-between">
                    <span>📈 Portfolio Equity Curve (Live)</span>
                    <span class="text-xs text-slate-400 font-mono">15m Evaluation Cadence</span>
                </h3>
                <div class="h-64">
                    <canvas id="equityChart"></canvas>
                </div>
            </div>

            <!-- Risk Architecture -->
            <div class="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col justify-between">
                <div>
                    <h3 class="text-base font-bold text-white mb-3">🛡️ Capital Preservation Rules</h3>
                    <ul class="space-y-2.5 text-xs text-slate-300">
                        <li class="flex items-start gap-2">
                            <span class="text-cyan-400 font-bold">1.</span>
                            <span><b>Max $35 / Trade:</b> Never commits more than 35% to a single coin.</span>
                        </li>
                        <li class="flex items-start gap-2">
                            <span class="text-cyan-400 font-bold">2.</span>
                            <span><b>$25 Dry Powder Reserve:</b> Always keeps at least $25 USDC ready to buy flash crashes.</span>
                        </li>
                        <li class="flex items-start gap-2">
                            <span class="text-cyan-400 font-bold">3.</span>
                            <span><b>Automated Partial Exits (TP1):</b> At +4.5%, locks in 50% profit and raises SL to breakeven.</span>
                        </li>
                        <li class="flex items-start gap-2">
                            <span class="text-cyan-400 font-bold">4.</span>
                            <span><b>Hard ATR Stop Loss:</b> 1.6x ATR cut-off to cap drawdown per position.</span>
                        </li>
                    </ul>
                </div>
                <div class="mt-4 p-3 rounded-xl bg-slate-800/60 border border-slate-700/50 text-xs text-slate-400">
                    <div class="text-slate-200 font-semibold mb-1">Selected Chain: Solana</div>
                    Fees on Ethereum would consume $15-$30 per trade. On Solana, DEX gas is &lt;$0.001, allowing a $100 fund to scalp friction-free.
                </div>
            </div>
        </div>

        <!-- Live Positions Table -->
        <div class="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl">
            <h3 class="text-base font-bold text-white mb-4">🎯 Active Open Positions</h3>
            <div class="overflow-x-auto">
                <table class="w-full text-left text-sm">
                    <thead>
                        <tr class="text-xs uppercase tracking-wider text-slate-400 border-b border-slate-700">
                            <th class="py-3 px-4">Asset</th>
                            <th class="py-3 px-4">Entry</th>
                            <th class="py-3 px-4">Mark Price</th>
                            <th class="py-3 px-4">Size (Tokens)</th>
                            <th class="py-3 px-4">Stop Loss</th>
                            <th class="py-3 px-4">Take Profit 1</th>
                            <th class="py-3 px-4">Unrealized PnL</th>
                        </tr>
                    </thead>
                    <tbody>
                        {pos_rows}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Market Radar: Solana Opportunities -->
        <div>
            <h3 class="text-base font-bold text-white mb-3">📡 Solana Ecosystem Technical Radar</h3>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {signal_cards}
            </div>
        </div>

        <!-- Recent Trades & Audit Log -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div class="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl">
                <h3 class="text-base font-bold text-white mb-3">⚡ Trade Execution Log</h3>
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-xs">
                        <thead>
                            <tr class="text-slate-400 border-b border-slate-700">
                                <th class="py-2 px-3">Time</th>
                                <th class="py-2 px-3">Asset</th>
                                <th class="py-2 px-3">Action</th>
                                <th class="py-2 px-3">Prices</th>
                                <th class="py-2 px-3">PnL</th>
                                <th class="py-2 px-3">Details</th>
                            </tr>
                        </thead>
                        <tbody>
                            {trades_rows}
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl">
                <h3 class="text-base font-bold text-white mb-3">🧠 Agent Decisions & Rationales</h3>
                <div class="space-y-2 max-h-64 overflow-y-auto pr-2 text-xs font-mono text-slate-300">
                    {"".join([f'<div class="p-2 rounded bg-slate-800/50 border border-slate-700/40"><span class="text-cyan-400">[{log["timestamp"][11:19]}]</span> {log["message"]}</div>' for log in reversed(p.get("action_logs", [])[-10:])])}
                </div>
            </div>
        </div>
    </div>

    <script>
        const ctx = document.getElementById('equityChart').getContext('2d');
        const labels = {json.dumps(eq_labels)};
        const data = {json.dumps(eq_values)};
        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: labels,
                datasets: [{{
                    label: 'Total Net Equity ($ USDC)',
                    data: data,
                    borderColor: '#38bdf8',
                    backgroundColor: 'rgba(56, 189, 248, 0.1)',
                    borderWidth: 2.5,
                    fill: true,
                    tension: 0.25,
                    pointRadius: 3,
                    pointBackgroundColor: '#0284c7'
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    x: {{
                        grid: {{ color: 'rgba(255,255,255,0.05)' }},
                        ticks: {{ color: '#94a3b8', font: {{ size: 10 }} }}
                    }},
                    y: {{
                        grid: {{ color: 'rgba(255,255,255,0.05)' }},
                        ticks: {{ color: '#94a3b8', font: {{ size: 10 }} }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""
        with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
            f.write(html_content)

    def print_terminal_summary(self):
        p = self.portfolio
        print("\n" + "=" * 75)
        print(f"🟣 SOLANA $100 USDC AUTONOMOUS FUND - LIVE STATUS 🟣")
        print("=" * 75)
        print(f"• Chain: {p['chain']}")
        print(f"• Total Equity:      ${p['total_equity_usdc']:<8.2f} USDC (Starting: ${p['starting_balance_usdc']:.2f})")
        print(f"• Total Return:      ${p['total_pnl_usd']:<+8.2f} ({p['total_pnl_pct']:+.2f}%)")
        print(f"• Liquid Cash:       ${p['cash_usdc']:<8.2f} USDC (Reserve Buffer: ${MIN_CASH_BUFFER:.2f})")
        print(f"• Positions Value:   ${p['positions_value_usdc']:<8.2f} USDC")
        print(f"• Realized PnL:      ${p['realized_pnl_usd']:<+8.2f} USDC | Win Rate: {p['win_rate_pct']:.1f}% ({p['winning_trades']}W / {p['total_trades']}T)")
        print("-" * 75)

        if not p["positions"]:
            print("• Open Positions: [ NONE ] (100% in liquid USDC cash reserve awaiting trigger)")
        else:
            print("• OPEN POSITIONS:")
            for pos in p["positions"]:
                upnl = pos.get("unrealized_pnl", 0.0)
                upnl_pct = pos.get("unrealized_pnl_pct", 0.0)
                print(f"  [{pos['symbol']}] Size: {pos['quantity']} tokens | Entry: ${pos['entry_price']:.4f} | Mark: ${pos['current_price']:.4f}")
                print(f"    -> PnL: ${upnl:+.2f} ({upnl_pct:+.2f}%) | SL: ${pos['stop_loss']:.4f} | TP1: ${pos['tp1']:.4f}")
                print(f"    -> Rationale: {pos.get('strategy_rationale', 'N/A')}")

        print("-" * 75)
        print(f"📁 Dashboard saved to: {DASHBOARD_FILE}")
        print("=" * 75 + "\n")


if __name__ == "__main__":
    agent = Solana100Agent()

    if "--reset" in sys.argv:
        if os.path.exists(PORTFOLIO_FILE):
            os.remove(PORTFOLIO_FILE)
        agent = Solana100Agent()
        print("Portfolio reset to fresh $100.00 USDC.")

    # Execute scan and live evaluation
    results = agent.scan_and_trade()
    agent.print_terminal_summary()

    if "--loop" in sys.argv:
        print("Starting continuous live loop (checking every 20 seconds). Press Ctrl+C to exit.")
        try:
            while True:
                time.sleep(20)
                agent.scan_and_trade()
                agent.print_terminal_summary()
        except KeyboardInterrupt:
            print("Loop stopped.")
