"""
Bot 5: SmartMoneyTracker Strategy
On-Chain Smart Money & Whale Inflows + Orderbook Imbalance Momentum Tracker.
"""
from typing import Dict, Any, List, Optional
import pandas as pd
from .base_strategy import BaseStrategy, StrategyDecision, Signal

class SmartMoneyTrackerStrategy(BaseStrategy):
    def __init__(self, bot_id: str = "bot_5_smartmoney", params: Dict[str, Any] = None):
        default_params = {
            'min_smart_score': 65.0,      # Smart Money Score threshold (0-100)
            'volume_delta_min': 1.4,      # 1.4x volume surge
            'stop_loss_pct': 0.020,       # 2.0% SL
            'take_profit_pct': 0.048,     # 4.8% TP
            'trailing_stop_pct': 0.015,   # 1.5% Trailing SL
            'stake_usd': 25.0             # $25 per smart money setup
        }
        if params:
            default_params.update(params)
        super().__init__(
            bot_id=bot_id,
            name="SmartMoneyTracker",
            description="On-Chain Whale Flow + Smart Wallet Inflows & Orderflow Imbalance",
            params=default_params
        )
        self.smart_money_signals: Dict[str, Dict[str, Any]] = {}

    def update_smart_signals(self, signals: Dict[str, Dict[str, Any]]):
        """Called by the research engine when new on-chain smart wallet scans complete."""
        self.smart_money_signals.update(signals)

    def evaluate(self, symbol: str, df: pd.DataFrame, ticker: Dict[str, Any],
                 open_positions: List[Dict[str, Any]], available_balance: float) -> StrategyDecision:
        if len(df) < 30:
            return StrategyDecision(Signal.HOLD, symbol, reason="Insufficient candle data")

        latest = df.iloc[-1]
        prev = df.iloc[-2]
        current_price = ticker['price']

        matching_positions = [p for p in open_positions if p['symbol'] == symbol]
        smart_signal = self.smart_money_signals.get(symbol, {
            'score': 50.0,
            'whale_sentiment': 'NEUTRAL',
            'net_flow_usd': 0.0
        })

        # 1. Check Exit for Open Positions
        if matching_positions:
            # If smart money sentiment flipped bearish or score dumped below 40
            if smart_signal.get('score', 50.0) < 40.0 or latest['rsi'] > 78.0:
                return StrategyDecision(
                    action=Signal.SELL,
                    symbol=symbol,
                    reason=f"SmartMoney Exit: Score decayed to {smart_signal.get('score', 50):.1f} or Overbought RSI",
                    confidence=0.85
                )
            return StrategyDecision(Signal.HOLD, symbol, reason="SmartMoney: Whale accumulation intact")

        # 2. Check Entry Signal
        stake = min(self.params['stake_usd'], available_balance)
        if available_balance < 10.0 or stake < 10.0:
            return StrategyDecision(Signal.HOLD, symbol, reason="Insufficient balance for minimum stake")

        # Entry Criteria:
        # 1. Smart Money Score >= min_smart_score
        # 2. Bullish candle: Close > Open and Close > EMA 20
        # 3. Volume ratio >= volume_delta_min
        # 4. RSI between 45 and 70 (Healthy markup stage)
        has_smart_inflow = smart_signal.get('score', 50.0) >= self.params['min_smart_score']
        is_bullish_structure = latest['close'] > latest['open'] and latest['close'] > latest['ema_20']
        is_volume_confirmed = latest['volume_surge_ratio'] >= self.params['volume_delta_min']
        is_rsi_favorable = 45.0 <= latest['rsi'] <= 70.0

        if has_smart_inflow and is_bullish_structure and is_volume_confirmed and is_rsi_favorable:
            confidence = min(0.98, 0.65 + (smart_signal.get('score', 50.0) / 200.0) + (latest['volume_surge_ratio'] / 10.0))
            return StrategyDecision(
                action=Signal.BUY,
                symbol=symbol,
                stake_usd=stake,
                stop_loss_pct=self.params['stop_loss_pct'],
                take_profit_pct=self.params['take_profit_pct'],
                trailing_stop_pct=self.params['trailing_stop_pct'],
                reason=f"SmartMoney Inflow Trigger (Score: {smart_signal.get('score', 50.0):.1f}, Vol: {latest['volume_surge_ratio']:.2f}x)",
                confidence=confidence,
                metadata={
                    'smart_score': smart_signal.get('score', 50.0),
                    'whale_sentiment': smart_signal.get('whale_sentiment', 'BULLISH')
                }
            )

        return StrategyDecision(Signal.HOLD, symbol, reason="No smart money accumulation trigger")
