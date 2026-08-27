"""
Bot 8: DesiMeanRevert - Indian Stock Market Bollinger & RSI Dip Scalper
Scalps extreme oversold pullbacks on high-beta Indian largecaps (TATAMOTORS, INFY, ICICIBANK, RELIANCE)
using statistical 2-sigma mean reversion.
"""
from typing import Dict, List, Any
import pandas as pd

try:
    from strategies.base_strategy import BaseStrategy, StrategyDecision, Signal
except (ImportError, ValueError):
    from .base_strategy import BaseStrategy, StrategyDecision, Signal

class DesiMeanRevertStrategy(BaseStrategy):
    def __init__(self, bot_id: str = "desi_meanrevert"):
        super().__init__(
            bot_id=bot_id,
            name="DesiMeanRevert (NSE Dip Scalper)",
            description="Scalps oversold dips on Indian stocks (TATAMOTORS, INFY, ICICIBANK) with 2-sigma Bollinger bounces"
        )
        self.params = {
            'rsi_oversold': 38.0,
            'take_profit_pct': 0.028,   # 2.8% quick scalp
            'stop_loss_pct': 0.018,     # 1.8% stop loss
            'trailing_stop_pct': 0.012,
            'stake_usd': 25.0
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
            return StrategyDecision(action=Signal.HOLD, reason="Insufficient balance")

        if df is None or len(df) < 25:
            return StrategyDecision(action=Signal.HOLD, reason="Insufficient candle history")

        last_row = df.iloc[-1]
        price = ticker.get('price', last_row['close'])
        rsi = last_row.get('rsi_14', 50.0)
        bb_lower = last_row.get('bb_lower', 0.0)
        has_open = any(p['symbol'] == symbol for p in open_positions)

        # Exit logic
        if has_open:
            matching = [p for p in open_positions if p['symbol'] == symbol]
            for p in matching:
                unrealized_pct = p.get('unrealized_pnl_pct', 0.0) / 100.0
                if unrealized_pct >= self.params['take_profit_pct']:
                    return StrategyDecision(action=Signal.SELL, reason=f"NSE Scalp Target Hit (+{unrealized_pct*100:.1f}%)")
                if unrealized_pct <= -self.params['stop_loss_pct']:
                    return StrategyDecision(action=Signal.SELL, reason=f"NSE Scalp Stop-Loss Hit ({unrealized_pct*100:.1f}%)")

        # Entry logic: Price <= lower BB and RSI < 38
        if not has_open:
            if price <= bb_lower or rsi <= self.params['rsi_oversold']:
                return StrategyDecision(
                    action=Signal.BUY,
                    stake_usd=self.params['stake_usd'],
                    stop_loss_pct=self.params['stop_loss_pct'],
                    take_profit_pct=self.params['take_profit_pct'],
                    trailing_stop_pct=self.params['trailing_stop_pct'],
                    reason=f"NSE Oversold Dip on {symbol} (RSI: {rsi:.1f} <= {self.params['rsi_oversold']}, Price at BB Lower ₹{bb_lower:.1f})"
                )

        return StrategyDecision(action=Signal.HOLD, reason="NSE prices in normal range")
