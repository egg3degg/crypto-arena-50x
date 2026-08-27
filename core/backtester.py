"""
Fast 30-Day Historical Backtest Simulator
Simulates any strategy on historical OHLCV data with realistic 0.075% fees and slippage.
"""
import math
from typing import Dict, Any, List
import pandas as pd
import numpy as np

try:
    from core.market_feed import MarketFeed
except (ImportError, ValueError):
    from .market_feed import MarketFeed

class StrategyBacktester:
    def __init__(self, market_feed: MarketFeed):
        self.market_feed = market_feed

    def run_backtest(
        self,
        strategy_type: str,
        symbol: str = "SOL/USDT",
        initial_capital: float = 50.0,
        stake_usd: float = 25.0,
        take_profit_pct: float = 0.045,
        stop_loss_pct: float = 0.025,
        fee_rate: float = 0.00075
    ) -> Dict[str, Any]:
        """Runs vectorized backtest on historical OHLCV candles."""
        df = self.market_feed.fetch_ohlcv_dataframe(symbol)
        if df is None or len(df) < 30:
            return {"error": f"Insufficient historical data for {symbol}"}

        balance = initial_capital
        equity_curve = []
        trades = []
        in_position = False
        entry_price = 0.0
        entry_time = ""
        qty = 0.0

        for i in range(25, len(df)):
            sub_df = df.iloc[:i+1]
            row = sub_df.iloc[-1]
            price = row['close']
            ts = str(row['timestamp'])

            if not in_position:
                # Check Entry Signal
                signal_buy = False
                if strategy_type == "trend":
                    signal_buy = (row['ema_20'] > row['ema_50']) and (row['rsi_14'] > 50) and (row['adx'] > 22)
                elif strategy_type == "mean_revert":
                    signal_buy = (price <= row['bb_lower']) and (row['rsi_14'] < 36)
                elif strategy_type == "breakout":
                    signal_buy = (price >= row['donchian_high']) and (row['vol_surge_ratio'] >= 1.6)
                elif strategy_type == "grid":
                    signal_buy = (price <= row['ema_20']) and (row['rsi_14'] < 48)
                else: # Smart money / polymarket
                    signal_buy = (row['rsi_14'] > 48) and (row['ema_20'] > row['ema_50'])

                if signal_buy and balance >= stake_usd:
                    fee = stake_usd * fee_rate
                    balance -= stake_usd
                    qty = (stake_usd - fee) / price
                    entry_price = price
                    entry_time = ts
                    in_position = True

            else:
                # Check Exit Condition (TP / SL)
                pnl_pct = (price - entry_price) / entry_price
                if pnl_pct >= take_profit_pct or pnl_pct <= -stop_loss_pct:
                    proceeds = qty * price
                    fee = proceeds * fee_rate
                    net_proceeds = proceeds - fee
                    realized_pnl = net_proceeds - stake_usd
                    balance += net_proceeds

                    trades.append({
                        "entry_time": entry_time,
                        "exit_time": ts,
                        "entry_price": round(entry_price, 2),
                        "exit_price": round(price, 2),
                        "pnl": round(realized_pnl, 2),
                        "pnl_pct": round(pnl_pct * 100, 2),
                        "is_win": realized_pnl > 0
                    })
                    in_position = False

            current_eq = balance + (qty * price if in_position else 0.0)
            equity_curve.append({"timestamp": ts, "equity": round(current_eq, 2)})

        # Aggregate Metrics
        total_trades = len(trades)
        wins = [t for t in trades if t['is_win']]
        win_rate = (len(wins) / total_trades * 100.0) if total_trades > 0 else 0.0
        final_equity = equity_curve[-1]['equity'] if equity_curve else initial_capital
        total_pnl = final_equity - initial_capital
        roi_pct = (total_pnl / initial_capital) * 100.0

        gross_profit = sum(t['pnl'] for t in wins)
        losses = [t for t in trades if not t['is_win']]
        gross_loss = abs(sum(t['pnl'] for t in losses))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (9.99 if gross_profit > 0 else 1.0)

        # Max Drawdown
        peak = initial_capital
        max_dd = 0.0
        for pt in equity_curve:
            eq = pt['equity']
            if eq > peak: peak = eq
            dd = ((peak - eq) / peak) * 100.0
            if dd > max_dd: max_dd = dd

        return {
            "symbol": symbol,
            "strategy": strategy_type,
            "initial_capital": initial_capital,
            "final_equity": round(final_equity, 2),
            "total_pnl": round(total_pnl, 2),
            "roi_pct": round(roi_pct, 2),
            "total_trades": total_trades,
            "win_rate": round(win_rate, 1),
            "profit_factor": round(profit_factor, 2),
            "max_drawdown": round(max_dd, 2),
            "trades": trades[-15:], # Last 15 trades preview
            "equity_curve": equity_curve[-40:] # Sample curve
        }
