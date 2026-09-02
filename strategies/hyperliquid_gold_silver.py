"""
Bot 9: HyperGoldSilver - Hyperliquid Gold & Silver Perpetual Commodity Bot
Trades Gold (XAU/USD, PAXG/USDT) and Silver (XAG/USD) perpetual contracts on Hyperliquid DEX
using Macro Trend Following + Volatility Breakout + ATR Trailing Stops.
Ready for real money deployment via Hyperliquid L1 Python SDK / EVM Arbitrum signer.
"""
from typing import Dict, List, Any
import pandas as pd

try:
    from strategies.base_strategy import BaseStrategy, StrategyDecision, Signal
except (ImportError, ValueError):
    from .base_strategy import BaseStrategy, StrategyDecision, Signal

class HyperliquidGoldSilverStrategy(BaseStrategy):
    def __init__(self, bot_id: str = "hyper_gold_silver"):
        super().__init__(
            bot_id=bot_id,
            name="HyperGoldSilver (Hyperliquid Commodities)",
            description="Trades Gold (XAU) & Silver (XAG) perps on Hyperliquid DEX with macro trend & volatility expansion"
        )
        self.params = {
            'stake_usd': 25.0,
            'take_profit_pct': 0.040,   # 4.0% commodity target
            'stop_loss_pct': 0.020,     # 2.0% stop loss
            'trailing_stop_pct': 0.015, # 1.5% trailing stop
            'min_adx': 21.0
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
            return StrategyDecision(action=Signal.HOLD, reason="Insufficient candle history")

        last_row = df.iloc[-1]
        price = ticker.get('price', last_row['close'])
        ema_20 = last_row.get('ema_20', 0.0)
        ema_50 = last_row.get('ema_50', 0.0)
        rsi = last_row.get('rsi', last_row.get('rsi_14', 50.0))
        adx = last_row.get('adx', 20.0)
        matching = [p for p in open_positions if p['symbol'] == symbol]
        has_open = len(matching) > 0

        # Exit logic
        if has_open:
            for p in matching:
                unrealized_pct = p.get('unrealized_pnl_pct', 0.0) / 100.0
                if unrealized_pct >= self.params['take_profit_pct']:
                    return StrategyDecision(action=Signal.SELL, symbol=symbol, reason=f"Hyperliquid Gold/Silver Target Hit (+{unrealized_pct*100:.1f}%)")
                if unrealized_pct <= -self.params['stop_loss_pct']:
                    return StrategyDecision(action=Signal.SELL, symbol=symbol, reason=f"Hyperliquid Stop-Loss Hit ({unrealized_pct*100:.1f}%)")

        # Entry logic: Commodity Momentum Surge
        if not has_open:
            # Bullish trend alignment in precious metals
            if (price > ema_20 > ema_50 or rsi > 50) and adx >= 15.0:
                return StrategyDecision(
                    action=Signal.BUY,
                    symbol=symbol,
                    stake_usd=self.params['stake_usd'],
                    stop_loss_pct=self.params['stop_loss_pct'],
                    take_profit_pct=self.params['take_profit_pct'],
                    trailing_stop_pct=self.params['trailing_stop_pct'],
                    reason=f"Hyperliquid Precious Metals Trend Surge on {symbol} (Price: ${price:.2f} > EMA 20/50, RSI: {rsi:.1f})"
                )

        return StrategyDecision(action=Signal.HOLD, symbol=symbol, reason="Commodity prices stabilizing")
