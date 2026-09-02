"""
Bot 4: AdaptiveGrid Strategy
Dynamic Micro-Grid Market Maker with ATR-spaced Grid Layers & Auto-Rebalancing.
"""
from typing import Dict, Any, List
import pandas as pd
from .base_strategy import BaseStrategy, StrategyDecision, Signal

class AdaptiveGridStrategy(BaseStrategy):
    def __init__(self, bot_id: str = "bot_4_adaptivegrid", params: Dict[str, Any] = None):
        default_params = {
            'grid_step_pct': 0.004,       # 0.4% rapid grid spacing on 1m candles
            'grid_levels': 2,             # Up to 2 active grid positions for $50 capital
            'take_profit_pct': 0.008,     # 0.8% grid take profit per level
            'stop_loss_pct': 0.018,       # 1.8% grid stop loss
            'trailing_stop_pct': None,    # Fixed profit targets for grid
            'stake_per_grid_usd': 20.0    # $20 per grid tier
        }
        if params:
            default_params.update(params)
        super().__init__(
            bot_id=bot_id,
            name="AdaptiveGrid",
            description="Dynamic ATR Micro-Grid Market Maker for Sideways Accumulation",
            params=default_params
        )

    def evaluate(self, symbol: str, df: pd.DataFrame, ticker: Dict[str, Any],
                 open_positions: List[Dict[str, Any]], available_balance: float) -> StrategyDecision:
        if len(df) < 30:
            return StrategyDecision(Signal.HOLD, symbol, reason="Insufficient candle data")

        latest = df.iloc[-1]
        current_price = ticker['price']

        matching_positions = [p for p in open_positions if p['symbol'] == symbol]
        active_grid_count = len(matching_positions)

        # 1. Check Exit for existing grid positions
        for pos in matching_positions:
            profit_pct = (current_price - pos['entry_price']) / pos['entry_price']
            if profit_pct >= self.params['take_profit_pct']:
                return StrategyDecision(
                    action=Signal.SELL,
                    symbol=symbol,
                    reason=f"AdaptiveGrid TP: Reached +{profit_pct*100:.2f}% grid level target",
                    confidence=0.90
                )

        # 2. Check if we can place a new grid tier
        if active_grid_count >= self.params['grid_levels']:
            return StrategyDecision(Signal.HOLD, symbol, reason="Max grid levels active")

        stake = min(self.params['stake_per_grid_usd'], available_balance)
        if available_balance < 10.0 or stake < 10.0:
            return StrategyDecision(Signal.HOLD, symbol, reason="Insufficient balance for grid order")

        center_price = latest.get('ema_20', current_price)
        rsi = latest.get('rsi', 50.0)

        if active_grid_count == 0:
            # Level 1 Entry: Price slightly under EMA 20 or RSI under 50 in ranging market
            if (current_price <= center_price * 0.998 or rsi <= 48.0) and latest.get('adx', 20.0) < 40.0:
                return StrategyDecision(
                    action=Signal.BUY,
                    symbol=symbol,
                    stake_usd=stake,
                    stop_loss_pct=self.params['stop_loss_pct'],
                    take_profit_pct=self.params['take_profit_pct'],
                    reason=f"AdaptiveGrid Level 1 Entry (RSI: {rsi:.1f}, Price near EMA 20)",
                    confidence=0.80,
                    metadata={'grid_tier': 1, 'center_price': center_price}
                )
        elif active_grid_count == 1:
            # Level 2 Entry: Price dropped another grid step below lowest open position
            lowest_entry = min(p['entry_price'] for p in matching_positions)
            if current_price <= lowest_entry * (1 - atr_grid_step):
                return StrategyDecision(
                    action=Signal.BUY,
                    symbol=symbol,
                    stake_usd=stake,
                    stop_loss_pct=self.params['stop_loss_pct'],
                    take_profit_pct=self.params['take_profit_pct'],
                    reason=f"AdaptiveGrid Level 2 DCA Entry (Averaging down in channel)",
                    confidence=0.82,
                    metadata={'grid_tier': 2}
                )

        return StrategyDecision(Signal.HOLD, symbol, reason="Grid conditions not satisfied")
