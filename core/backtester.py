"""
Fast Vectorized Historical Backtest Simulator
Simulates strategies on historical OHLCV data with fees, slippage, and trailing stop support.
Supports parameter sweeps for the Walk-Forward Optimization Engine.
"""
import math
from typing import Dict, Any, List, Optional
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
        df: Optional[pd.DataFrame] = None,
        initial_capital: float = 50.0,
        stake_usd: float = 25.0,
        take_profit_pct: float = 0.045,
        stop_loss_pct: float = 0.025,
        trailing_stop_pct: Optional[float] = None,
        fee_rate: float = 0.00075
    ) -> Dict[str, Any]:
        """Runs vectorized backtest on historical OHLCV candles with trailing stop support."""
        if df is None:
            df = self.market_feed.fetch_ohlcv_dataframe(symbol)
        
        if df is None or len(df) < 30:
            return {"error": f"Insufficient historical data for {symbol}"}

        balance = initial_capital
        equity_curve = []
        trades = []
        in_position = False
        entry_price = 0.0
        entry_time = ""
        highest_price = 0.0
        qty = 0.0

        for i in range(25, len(df)):
            row = df.iloc[i]
            price = row['close']
            ts = str(row['timestamp'])

            if not in_position:
                # Entry Conditions
                signal_buy = False
                if strategy_type in ["trend", "alphatrend", "bot_1_alphatrend"]:
                    signal_buy = (row.get('ema_20', 0) > row.get('ema_50', 0)) and (row.get('rsi', 50) > 50) and (row.get('adx', 20) > 20)
                elif strategy_type in ["mean_revert", "bot_2_meanrevert"]:
                    signal_buy = (price <= row.get('bb_lower', price)) and (row.get('rsi', 50) < 38)
                elif strategy_type in ["breakout", "bot_3_breakouthunter"]:
                    signal_buy = (price >= row.get('donchian_high', price * 1.05)) and (row.get('volume_surge_ratio', 1.0) >= 1.5)
                elif strategy_type in ["grid", "bot_4_adaptivegrid"]:
                    signal_buy = (price <= row.get('ema_20', price)) and (row.get('rsi', 50) < 48)
                else: # Smart money / default momentum
                    signal_buy = (row.get('rsi', 50) > 48) and (row.get('ema_9', 0) > row.get('ema_20', 0))

                if signal_buy and balance >= stake_usd:
                    fee = stake_usd * fee_rate
                    balance -= stake_usd
                    qty = (stake_usd - fee) / price
                    entry_price = price
                    highest_price = price
                    entry_time = ts
                    in_position = True

            else:
                if price > highest_price:
                    highest_price = price

                # Check Exit Condition (TP, SL, Trailing SL)
                pnl_pct = (price - entry_price) / entry_price
                trailing_hit = False
                if trailing_stop_pct and trailing_stop_pct > 0:
                    trail_drop = (highest_price - price) / highest_price
                    if trail_drop >= trailing_stop_pct and pnl_pct > 0.005:
                        trailing_hit = True

                if pnl_pct >= take_profit_pct or pnl_pct <= -stop_loss_pct or trailing_hit:
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

        # Aggregate Performance Metrics
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

        # Sharpe Ratio Calculation
        if len(trades) >= 2:
            pnls = [t['pnl'] for t in trades]
            mean_p = sum(pnls) / len(pnls)
            var_p = sum((p - mean_p) ** 2 for p in pnls) / max(1, len(pnls) - 1)
            std_p = math.sqrt(var_p) if var_p > 0 else 0.0001
            sharpe = (mean_p / std_p) * math.sqrt(len(trades))
        else:
            sharpe = 0.0

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
            "sharpe_ratio": round(sharpe, 2),
            "trades": trades[-15:],
            "equity_curve": equity_curve[-40:]
        }
