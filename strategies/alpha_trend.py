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
            'ema_fast': 12,
            'ema_slow': 34,
            'adx_threshold': 18.0,
            'rsi_min': 38.0,
            'rsi_max': 72.0,
            'stop_loss_pct': 0.018,       # 1.8% SL
            'take_profit_pct': 0.028,     # 2.8% TP for faster trade realization
            'trailing_stop_pct': 0.012,   # 1.2% Trailing SL
            'stake_usd': 25.0             # $25 per trade
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
            for pos in matching_positions:
                is_short = (pos.get('side') == 'SHORT')
                if is_short:
                    # Exit Short on Bullish Crossover or deeply oversold RSI
                    if (latest['ema_20'] > latest['ema_50'] and prev['ema_20'] <= prev['ema_50']) or latest['rsi'] < 22:
                        return StrategyDecision(
                            action=Signal.COVER,
                            symbol=symbol,
                            reason=f"AlphaTrend Short Exit: Bullish Cross or Oversold RSI ({latest['rsi']:.1f})",
                            confidence=0.85
                        )
                else:
                    # Exit Long on Bearish Crossover or extreme overbought RSI
                    if (latest['ema_20'] < latest['ema_50'] and prev['ema_20'] >= prev['ema_50']) or latest['rsi'] > 78:
                        return StrategyDecision(
                            action=Signal.SELL,
                            symbol=symbol,
                            reason=f"AlphaTrend Long Exit: Bearish Cross or Overbought RSI ({latest['rsi']:.1f})",
                            confidence=0.85
                        )
            return StrategyDecision(Signal.HOLD, symbol, reason="AlphaTrend: Riding active trend position")

        # 2. Check Entry Signal (Only if capital is available)
        stake = min(self.params['stake_usd'], available_balance)
        if available_balance < 10.0 or stake < 10.0:
            return StrategyDecision(Signal.HOLD, symbol, reason="Insufficient balance for minimum stake")

        # --- A. Bullish Trend Entry (LONG) ---
        is_uptrend = latest['close'] > latest['ema_50'] and latest['ema_20'] > latest['ema_50']
        is_strong_trend = latest['adx'] >= self.params['adx_threshold']
        is_rsi_valid_long = self.params['rsi_min'] <= latest['rsi'] <= self.params['rsi_max']
        is_bullish_trigger = latest['close'] > latest['ema_20'] and prev['close'] <= prev['ema_20']

        if is_uptrend and is_strong_trend and is_rsi_valid_long and (is_bullish_trigger or latest['close'] > latest['ema_9']):
            confidence = min(0.95, 0.60 + (latest['adx'] / 100.0) + (0.1 if latest['close'] > latest['ema_200'] else 0.0))
            return StrategyDecision(
                action=Signal.BUY,
                symbol=symbol,
                stake_usd=stake,
                side="LONG",
                stop_loss_pct=self.params['stop_loss_pct'],
                take_profit_pct=self.params['take_profit_pct'],
                trailing_stop_pct=self.params['trailing_stop_pct'],
                reason=f"AlphaTrend Bullish Momentum (ADX: {latest['adx']:.1f}, RSI: {latest['rsi']:.1f})",
                confidence=confidence,
                metadata={'adx': latest['adx'], 'rsi': latest['rsi']}
            )

        # --- B. Bearish Trend Entry (SHORT) ---
        is_downtrend = latest['close'] < latest['ema_50'] and latest['ema_20'] < latest['ema_50']
        is_rsi_valid_short = 28.0 <= latest['rsi'] <= 58.0
        is_bearish_trigger = latest['close'] < latest['ema_20'] and prev['close'] >= prev['ema_20']

        if is_downtrend and is_strong_trend and is_rsi_valid_short and (is_bearish_trigger or latest['close'] < latest['ema_9']):
            confidence = min(0.95, 0.60 + (latest['adx'] / 100.0))
            return StrategyDecision(
                action=Signal.SHORT,
                symbol=symbol,
                stake_usd=stake,
                side="SHORT",
                stop_loss_pct=self.params['stop_loss_pct'],
                take_profit_pct=self.params['take_profit_pct'],
                trailing_stop_pct=self.params['trailing_stop_pct'],
                reason=f"AlphaTrend Bearish Breakdown (ADX: {latest['adx']:.1f}, RSI: {latest['rsi']:.1f})",
                confidence=confidence,
                metadata={'adx': latest['adx'], 'rsi': latest['rsi']}
            )

        return StrategyDecision(Signal.HOLD, symbol, reason="No trend signal matching criteria")
