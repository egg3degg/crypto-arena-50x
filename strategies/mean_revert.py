"""
Bot 2: MeanRevert Strategy
Statistical Arbitrage & Range Scalper with Bollinger Bands + Oversold RSI + Stochastic Bounce.
"""
from typing import Dict, Any, List
import pandas as pd
from .base_strategy import BaseStrategy, StrategyDecision, Signal

class MeanRevertStrategy(BaseStrategy):
    def __init__(self, bot_id: str = "bot_2_meanrevert", params: Dict[str, Any] = None):
        default_params = {
            'bb_pct_b_entry': 0.20,       # Within bottom 20% of Bollinger Band
            'rsi_oversold': 42.0,         # Oversold RSI threshold (captures quick dips)
            'rsi_exit': 60.0,             # Mean-reverted exit threshold
            'stoch_oversold': 30.0,       # Stochastic oversold threshold
            'stop_loss_pct': 0.015,       # 1.5% tight SL
            'take_profit_pct': 0.024,     # 2.4% TP
            'trailing_stop_pct': 0.010,   # 1.0% Trailing SL
            'stake_usd': 25.0             # $25 per scalp
        }
        if params:
            default_params.update(params)
        super().__init__(
            bot_id=bot_id,
            name="MeanRevert",
            description="Bollinger Bands + RSI Oversold Bounce & Mean-Reversion Scalper",
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

        # 1. Check Exit for Open Positions (Target reached mid-band or RSI normalized)
        if matching_positions:
            for pos in matching_positions:
                is_short = (pos.get('side') == 'SHORT')
                if is_short:
                    if latest['close'] <= latest['bb_mid'] or latest['rsi'] <= 40.0:
                        return StrategyDecision(
                            action=Signal.COVER,
                            symbol=symbol,
                            reason=f"MeanRevert Short TP: Price returned to mean (BB Mid: ${latest['bb_mid']:.2f}, RSI: {latest['rsi']:.1f})",
                            confidence=0.88
                        )
                else:
                    if latest['close'] >= latest['bb_mid'] or latest['rsi'] >= self.params['rsi_exit']:
                        return StrategyDecision(
                            action=Signal.SELL,
                            symbol=symbol,
                            reason=f"MeanRevert Long TP: Price returned to mean (BB Mid: ${latest['bb_mid']:.2f}, RSI: {latest['rsi']:.1f})",
                            confidence=0.88
                        )
            return StrategyDecision(Signal.HOLD, symbol, reason="MeanRevert: Waiting for mean bounce")

        # 2. Check Entry Signal
        stake = min(self.params['stake_usd'], available_balance)
        if available_balance < 10.0 or stake < 10.0:
            return StrategyDecision(Signal.HOLD, symbol, reason="Insufficient balance for minimum stake")

        # --- A. Oversold Dip Entry (LONG) ---
        is_bb_oversold = latest['bb_pct_b'] <= self.params['bb_pct_b_entry'] or latest['low'] <= latest['bb_lower']
        is_rsi_oversold = latest['rsi'] <= self.params['rsi_oversold']
        is_stoch_turning = latest['stoch_k'] < self.params['stoch_oversold'] or (latest['stoch_k'] > prev['stoch_k'] and prev['stoch_k'] < 35)
        is_not_crash = latest['adx'] < 38.0

        if is_bb_oversold and is_rsi_oversold and is_stoch_turning and is_not_crash:
            confidence = min(0.92, 0.65 + ((self.params['rsi_oversold'] - latest['rsi']) / 100.0))
            return StrategyDecision(
                action=Signal.BUY,
                symbol=symbol,
                stake_usd=stake,
                side="LONG",
                stop_loss_pct=self.params['stop_loss_pct'],
                take_profit_pct=self.params['take_profit_pct'],
                trailing_stop_pct=self.params['trailing_stop_pct'],
                reason=f"MeanRevert Dip Setup (RSI: {latest['rsi']:.1f}, BB %B: {latest['bb_pct_b']:.2f})",
                confidence=confidence,
                metadata={'rsi': latest['rsi'], 'bb_lower': latest['bb_lower']}
            )

        # --- B. Overbought Top Fade Entry (SHORT) ---
        is_bb_overbought = latest['bb_pct_b'] >= 0.80 or latest['high'] >= latest['bb_upper']
        is_rsi_overbought = latest['rsi'] >= 62.0
        is_stoch_topping = latest['stoch_k'] > 70.0 or (latest['stoch_k'] < prev['stoch_k'] and prev['stoch_k'] > 65)

        if is_bb_overbought and is_rsi_overbought and is_stoch_topping and is_not_crash:
            confidence = min(0.92, 0.65 + ((latest['rsi'] - 60.0) / 100.0))
            return StrategyDecision(
                action=Signal.SHORT,
                symbol=symbol,
                stake_usd=stake,
                side="SHORT",
                stop_loss_pct=self.params['stop_loss_pct'],
                take_profit_pct=self.params['take_profit_pct'],
                trailing_stop_pct=self.params['trailing_stop_pct'],
                reason=f"MeanRevert Overbought Fade (RSI: {latest['rsi']:.1f}, BB %B: {latest['bb_pct_b']:.2f})",
                confidence=confidence,
                metadata={'rsi': latest['rsi'], 'bb_upper': latest['bb_upper']}
            )

        return StrategyDecision(Signal.HOLD, symbol, reason="No mean-reversion setup detected")
