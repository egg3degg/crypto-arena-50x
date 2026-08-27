"""
Bot 1: AlphaTrend Strategy
Trend-Following & Multi-Timeframe Momentum with EMA Ribbon + ADX Filter + ATR Trailing Stop.
"""
from typing import Dict, Any, List
import pandas as pd
from .base_strategy import BaseStrategy, StrategyDecision, Signal

class AlphaTrendStrategy(BaseStrategy):
    def __init__(self, bot_id: str = "bot_1_alphatrend", params: Dict[str, Any] = None):
        default_params = {
            'ema_fast': 20,
            'ema_slow': 50,
            'adx_threshold': 22.0,
            'rsi_min': 42.0,
            'rsi_max': 68.0,
            'stop_loss_pct': 0.025,       # 2.5% SL
            'take_profit_pct': 0.045,     # 4.5% TP
            'trailing_stop_pct': 0.018,   # 1.8% Trailing SL
            'stake_usd': 25.0             # $25 per trade (2 trades max)
        }
        if params:
            default_params.update(params)
        super().__init__(
            bot_id=bot_id,
            name="AlphaTrend",
            description="Multi-timeframe EMA Ribbon + SuperTrend + ADX Trend Momentum",
            params=default_params
        )

    def evaluate(self, symbol: str, df: pd.DataFrame, ticker: Dict[str, Any],
                 open_positions: List[Dict[str, Any]], available_balance: float) -> StrategyDecision:
        if len(df) < 50:
            return StrategyDecision(Signal.HOLD, symbol, reason="Insufficient candle data")

        latest = df.iloc[-1]
        prev = df.iloc[-2]
        current_price = ticker['price']

        # Check existing positions for this symbol
        matching_positions = [p for p in open_positions if p['symbol'] == symbol]

        # 1. Check Exit Signal for Open Positions
        if matching_positions:
            # Bearish crossover or extreme overbought RSI
            if (latest['ema_20'] < latest['ema_50'] and prev['ema_20'] >= prev['ema_50']) or latest['rsi'] > 80:
                return StrategyDecision(
                    action=Signal.SELL,
                    symbol=symbol,
                    reason=f"AlphaTrend Exit: EMA Bearish Cross or Overbought RSI ({latest['rsi']:.1f})",
                    confidence=0.85
                )
            return StrategyDecision(Signal.HOLD, symbol, reason="AlphaTrend: Riding active trend")

        # 2. Check Entry Signal (Only if capital is available)
        stake = min(self.params['stake_usd'], available_balance)
        if available_balance < 10.0 or stake < 10.0:
            return StrategyDecision(Signal.HOLD, symbol, reason="Insufficient balance for minimum stake")

        # Entry Conditions:
        # 1. Price > EMA 50 and EMA 20 > EMA 50
        # 2. Strong trend: ADX > adx_threshold
        # 3. Healthy RSI momentum (not exhausted)
        # 4. Bullish candle close > EMA 20
        is_uptrend = latest['close'] > latest['ema_50'] and latest['ema_20'] > latest['ema_50']
        is_strong_trend = latest['adx'] >= self.params['adx_threshold']
        is_rsi_valid = self.params['rsi_min'] <= latest['rsi'] <= self.params['rsi_max']
        is_bullish_trigger = latest['close'] > latest['ema_20'] and prev['close'] <= prev['ema_20']

        if is_uptrend and is_strong_trend and is_rsi_valid and (is_bullish_trigger or latest['close'] > latest['ema_9']):
            confidence = min(0.95, 0.60 + (latest['adx'] / 100.0) + (0.1 if latest['close'] > latest['ema_200'] else 0.0))
            return StrategyDecision(
                action=Signal.BUY,
                symbol=symbol,
                stake_usd=stake,
                stop_loss_pct=self.params['stop_loss_pct'],
                take_profit_pct=self.params['take_profit_pct'],
                trailing_stop_pct=self.params['trailing_stop_pct'],
                reason=f"AlphaTrend Bullish Setup (ADX: {latest['adx']:.1f}, RSI: {latest['rsi']:.1f})",
                confidence=confidence,
                metadata={'adx': latest['adx'], 'rsi': latest['rsi']}
            )

        return StrategyDecision(Signal.HOLD, symbol, reason="No trend signal matching criteria")
