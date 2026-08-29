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
            'volume_surge_multiplier': 1.4,  # Volume > 1.4x 20-period average
            'donchian_period': 14,           # 14-period Donchian channel
            'rsi_breakout_min': 48.0,        # Momentum trigger
            'stop_loss_pct': 0.016,          # 1.6% SL
            'take_profit_pct': 0.030,        # 3.0% TP
            'trailing_stop_pct': 0.012,      # 1.2% Trailing SL
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

        # 1. Check Exit for Open Positions (Breakout failure or cross of Donchian mid)
        if matching_positions:
            for pos in matching_positions:
                is_short = (pos.get('side') == 'SHORT')
                if is_short:
                    if latest['close'] > latest['donchian_mid']:
                        return StrategyDecision(
                            action=Signal.COVER,
                            symbol=symbol,
                            reason=f"BreakoutHunter Short TP: Price reclaimed Donchian Mid (${latest['donchian_mid']:.2f})",
                            confidence=0.82
                        )
                else:
                    if latest['close'] < latest['donchian_mid']:
                        return StrategyDecision(
                            action=Signal.SELL,
                            symbol=symbol,
                            reason=f"BreakoutHunter Long Exit: Price lost Donchian Mid (${latest['donchian_mid']:.2f})",
                            confidence=0.82
                        )
            return StrategyDecision(Signal.HOLD, symbol, reason="BreakoutHunter: Holding breakout position")

        # 2. Check Entry Signal
        stake = min(self.params['stake_usd'], available_balance)
        if available_balance < 10.0 or stake < 10.0:
            return StrategyDecision(Signal.HOLD, symbol, reason="Insufficient balance for minimum stake")

        is_volume_surge = latest['volume_surge_ratio'] >= self.params['volume_surge_multiplier']

        # --- A. Bullish Channel Breakout (LONG) ---
        is_breakout = latest['close'] >= prev['donchian_high'] or latest['high'] >= prev['donchian_high']
        is_rsi_strong = latest['rsi'] >= self.params['rsi_breakout_min'] and latest['rsi'] < 82.0

        if is_breakout and is_volume_surge and is_rsi_strong:
            confidence = min(0.96, 0.70 + (latest['volume_surge_ratio'] / 10.0))
            return StrategyDecision(
                action=Signal.BUY,
                symbol=symbol,
                stake_usd=stake,
                side="LONG",
                stop_loss_pct=self.params['stop_loss_pct'],
                take_profit_pct=self.params['take_profit_pct'],
                trailing_stop_pct=self.params['trailing_stop_pct'],
                reason=f"BreakoutHunter High Breakout (Vol: {latest['volume_surge_ratio']:.2f}x)",
                confidence=confidence,
                metadata={'vol_ratio': latest['volume_surge_ratio'], 'donchian_high': prev['donchian_high']}
            )

        # --- B. Bearish Channel Breakdown (SHORT) ---
        is_breakdown = latest['close'] <= prev['donchian_low'] or latest['low'] <= prev['donchian_low']
        is_rsi_weak = latest['rsi'] <= (100.0 - self.params['rsi_breakout_min']) and latest['rsi'] > 18.0

        if is_breakdown and is_volume_surge and is_rsi_weak:
            confidence = min(0.96, 0.70 + (latest['volume_surge_ratio'] / 10.0))
            return StrategyDecision(
                action=Signal.SHORT,
                symbol=symbol,
                stake_usd=stake,
                side="SHORT",
                stop_loss_pct=self.params['stop_loss_pct'],
                take_profit_pct=self.params['take_profit_pct'],
                trailing_stop_pct=self.params['trailing_stop_pct'],
                reason=f"BreakoutHunter Low Breakdown (Vol: {latest['volume_surge_ratio']:.2f}x)",
                confidence=confidence,
                metadata={'vol_ratio': latest['volume_surge_ratio'], 'donchian_low': prev['donchian_low']}
            )

        return StrategyDecision(Signal.HOLD, symbol, reason="No volume-backed breakout")
