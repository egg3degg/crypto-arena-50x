"""
Bot 3: BreakoutHunter Strategy
Donchian Channel Breakout + Volume Surge Expansion + ATR Volatility Filter.
"""
from typing import Dict, Any, List
import pandas as pd
from .base_strategy import BaseStrategy, StrategyDecision, Signal

class BreakoutHunterStrategy(BaseStrategy):
    def __init__(self, bot_id: str = "bot_3_breakouthunter", params: Dict[str, Any] = None):
        default_params = {
            'volume_surge_multiplier': 1.8,  # Volume > 1.8x 20-period average
            'donchian_period': 20,
            'rsi_breakout_min': 52.0,        # Bullish momentum behind breakout
            'stop_loss_pct': 0.022,          # 2.2% SL
            'take_profit_pct': 0.055,        # 5.5% TP
            'trailing_stop_pct': 0.018,      # 1.8% Trailing SL
            'stake_usd': 25.0                # $25 per breakout
        }
        if params:
            default_params.update(params)
        super().__init__(
            bot_id=bot_id,
            name="BreakoutHunter",
            description="Donchian Channel High Breakout + Volume Spike Surge Momentum",
            params=default_params
        )

    def evaluate(self, symbol: str, df: pd.DataFrame, ticker: Dict[str, Any],
                 open_positions: List[Dict[str, Any]], available_balance: float) -> StrategyDecision:
        if len(df) < 30:
            return StrategyDecision(Signal.HOLD, symbol, reason="Insufficient candle data")

        latest = df.iloc[-1]
        prev = df.iloc[-2]
        current_price = ticker['price']

        matching_positions = [p for p in open_positions if p['symbol'] == symbol]

        # 1. Check Exit for Open Positions (Breakout failure or breakdown below Donchian mid)
        if matching_positions:
            if latest['close'] < latest['donchian_mid']:
                return StrategyDecision(
                    action=Signal.SELL,
                    symbol=symbol,
                    reason=f"BreakoutHunter Exit: Price lost Donchian Mid (${latest['donchian_mid']:.2f})",
                    confidence=0.82
                )
            return StrategyDecision(Signal.HOLD, symbol, reason="BreakoutHunter: Holding breakout rally")

        # 2. Check Entry Signal
        stake = min(self.params['stake_usd'], available_balance)
        if available_balance < 10.0 or stake < 10.0:
            return StrategyDecision(Signal.HOLD, symbol, reason="Insufficient balance for minimum stake")

        # Entry Criteria:
        # 1. Current High/Close >= Prev Donchian High (New 20-period High breakout)
        # 2. Volume Surge > volume_surge_multiplier
        # 3. RSI > 52 (Positive upward push)
        is_breakout = latest['close'] >= prev['donchian_high'] or latest['high'] >= prev['donchian_high']
        is_volume_surge = latest['volume_surge_ratio'] >= self.params['volume_surge_multiplier']
        is_rsi_strong = latest['rsi'] >= self.params['rsi_breakout_min'] and latest['rsi'] < 82.0

        if is_breakout and is_volume_surge and is_rsi_strong:
            confidence = min(0.96, 0.70 + (latest['volume_surge_ratio'] / 10.0))
            return StrategyDecision(
                action=Signal.BUY,
                symbol=symbol,
                stake_usd=stake,
                stop_loss_pct=self.params['stop_loss_pct'],
                take_profit_pct=self.params['take_profit_pct'],
                trailing_stop_pct=self.params['trailing_stop_pct'],
                reason=f"BreakoutHunter Surge Setup (Vol Ratio: {latest['volume_surge_ratio']:.2f}x, 20-High Breakout)",
                confidence=confidence,
                metadata={'vol_ratio': latest['volume_surge_ratio'], 'donchian_high': prev['donchian_high']}
            )

        return StrategyDecision(Signal.HOLD, symbol, reason="No volume-backed breakout")
