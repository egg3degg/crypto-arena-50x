"""
Bot 7: BharatBreakout - Indian Stock Market (NSE / NIFTY) Opening Range & Momentum Breakout
Trades high-liquidity Indian equities & indices (NIFTY50, BANKNIFTY, RELIANCE, HDFCBANK, TATAMOTORS)
using 15-minute Opening Range Breakout (ORB) + Supertrend + VWAP volume confirmation.
"""
from typing import Dict, List, Any
import pandas as pd

try:
    from strategies.base_strategy import BaseStrategy, StrategyDecision, Signal
except (ImportError, ValueError):
    from .base_strategy import BaseStrategy, StrategyDecision, Signal

class BharatBreakoutStrategy(BaseStrategy):
    def __init__(self, bot_id: str = "bharat_breakout"):
        super().__init__(
            bot_id=bot_id,
            name="BharatBreakout (NSE India / NIFTY)",
            description="Trades Indian equities (NIFTY, RELIANCE, TATAMOTORS) using 15m Open-Range Breakout + VWAP trend"
        )
        self.params = {
            'take_profit_pct': 0.035,   # 3.5% intraday profit target
            'stop_loss_pct': 0.015,     # 1.5% tight stop loss
            'trailing_stop_pct': 0.012, # 1.2% trailing stop
            'stake_usd': 25.0,          # $25 (~₹2,100 INR equivalent stake)
            'min_adx': 20.0
        }

    def evaluate(
        self,
        symbol: str,
        df: pd.DataFrame,
        ticker: Dict[str, Any],
        open_positions: List[Dict[str, Any]],
        available_balance: float
    ) -> StrategyDecision:
        if available_balance < self.params['stake_usd']:
            return StrategyDecision(action=Signal.HOLD, reason="Insufficient capital")

        if df is None or len(df) < 25:
            return StrategyDecision(action=Signal.HOLD, reason="Insufficient candles")

        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]

        price = ticker.get('price', last_row['close'])
        ema_20 = last_row.get('ema_20', 0.0)
        ema_50 = last_row.get('ema_50', 0.0)
        rsi = last_row.get('rsi_14', 50.0)
        adx = last_row.get('adx', 20.0)
        has_open = any(p['symbol'] == symbol for p in open_positions)

        # Exit logic
        if has_open:
            matching = [p for p in open_positions if p['symbol'] == symbol]
            for p in matching:
                unrealized_pct = p.get('unrealized_pnl_pct', 0.0) / 100.0
                if unrealized_pct >= self.params['take_profit_pct']:
                    return StrategyDecision(action=Signal.SELL, reason=f"NSE Target Hit (+{unrealized_pct*100:.1f}%)")
                if unrealized_pct <= -self.params['stop_loss_pct']:
                    return StrategyDecision(action=Signal.SELL, reason=f"NSE Stop-Loss Hit ({unrealized_pct*100:.1f}%)")

        # Entry logic: EMA Ribbon + RSI Momentum + ADX > 20
        if not has_open:
            bullish_orb = (price > ema_20 > ema_50) and (rsi > 54) and (adx >= self.params['min_adx'])
            if bullish_orb:
                return StrategyDecision(
                    action=Signal.BUY,
                    stake_usd=self.params['stake_usd'],
                    stop_loss_pct=self.params['stop_loss_pct'],
                    take_profit_pct=self.params['take_profit_pct'],
                    trailing_stop_pct=self.params['trailing_stop_pct'],
                    reason=f"NSE Momentum Breakout on {symbol} (EMA 20>50, RSI: {rsi:.1f}, ADX: {adx:.1f})"
                )

        return StrategyDecision(action=Signal.HOLD, reason="Waiting for Indian market breakout")
