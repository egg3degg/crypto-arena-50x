"""
Bot 6: PolyPredictor - Polymarket Event Probability & Statistical Arbitrage Strategy
Trades crypto prediction markets by detecting pricing misalignments between Polymarket
implied odds and spot technical trend momentum.
"""
from typing import Dict, List, Any, Optional
import pandas as pd

try:
    from strategies.base_strategy import BaseStrategy, StrategyDecision, Signal
except (ImportError, ValueError):
    from .base_strategy import BaseStrategy, StrategyDecision, Signal

class PolymarketPredictorStrategy(BaseStrategy):
    def __init__(self, bot_id: str = "poly_predictor"):
        super().__init__(
            bot_id=bot_id,
            name="PolyPredictor (Polymarket Probability Arbitrage)",
            description="Exploits mispriced prediction market odds vs on-chain spot momentum on Polymarket"
        )
        self.params = {
            'min_probability_edge': 0.10,   # 10% edge required to enter
            'stake_usd': 20.0,              # $20 per prediction market position
            'take_profit_pct': 0.35,        # 35% profit on share appreciation
            'stop_loss_pct': 0.25,          # 25% max loss limit
            'trailing_stop_pct': 0.15
        }

    def evaluate(
        self,
        symbol: str,
        df: pd.DataFrame,
        ticker: Dict[str, Any],
        open_positions: List[Dict[str, Any]],
        available_balance: float,
        polymarket_events: Optional[List[Dict[str, Any]]] = None
    ) -> StrategyDecision:
        """
        Calculates fair-value probability from spot momentum and compares to Polymarket YES/NO prices.
        """
        if available_balance < self.params['stake_usd']:
            return StrategyDecision(action=Signal.HOLD, reason="Insufficient capital for Polymarket bet")

        if df is None or len(df) < 20:
            return StrategyDecision(action=Signal.HOLD, reason="Insufficient candle history")

        # 1. Check if we already have an open position in this asset/market
        has_open = any(p['symbol'] == symbol for p in open_positions)

        # 2. Derive Spot Momentum Implied Probability (0.0 to 1.0)
        last_row = df.iloc[-1]
        rsi = last_row.get('rsi', last_row.get('rsi_14', 50.0))
        ema_20 = last_row.get('ema_20', 0.0)
        ema_50 = last_row.get('ema_50', 0.0)
        adx = last_row.get('adx', 20.0)
        price = ticker.get('price', 0.0)

        # Quantitative Probability Score based on Multi-Factor Technical Convergence
        bullish_score = 0.50
        if rsi > 52: bullish_score += 0.14
        elif rsi < 48: bullish_score -= 0.14

        if price > ema_20 > ema_50: bullish_score += 0.18
        elif price < ema_20 < ema_50: bullish_score -= 0.18

        if adx > 20:
            bullish_score = bullish_score * 1.1 if bullish_score > 0.5 else bullish_score * 0.9

        implied_spot_prob = max(0.10, min(0.90, bullish_score))

        # 3. Match with active Polymarket market if available
        matched_event = None
        if polymarket_events:
            for ev in polymarket_events:
                q = ev.get('question', '').lower()
                sym_base = symbol.split('/')[0].lower()
                if sym_base in q or (sym_base == 'btc' and 'bitcoin' in q) or (sym_base == 'eth' and 'ethereum' in q) or (sym_base == 'sol' and 'solana' in q):
                    matched_event = ev
                    break

        market_yes_price = matched_event.get('yes_price', 0.50) if matched_event else 0.50
        market_question = matched_event.get('question', f"Polymarket {symbol} Bullish Momentum") if matched_event else f"Polymarket {symbol} Probability Play"

        edge = implied_spot_prob - market_yes_price

        # Exit Condition for existing position
        if has_open:
            matching_pos = [p for p in open_positions if p['symbol'] == symbol]
            for pos in matching_pos:
                unrealized_pct = pos.get('unrealized_pnl_pct', 0.0) / 100.0
                if unrealized_pct >= self.params['take_profit_pct']:
                    return StrategyDecision(
                        action=Signal.SELL,
                        symbol=symbol,
                        reason=f"Polymarket Share Take-Profit Target Hit (+{unrealized_pct*100:.1f}%)"
                    )
                if unrealized_pct <= -self.params['stop_loss_pct']:
                    return StrategyDecision(
                        action=Signal.SELL,
                        symbol=symbol,
                        reason=f"Polymarket Share Stop-Loss Triggered ({unrealized_pct*100:.1f}%)"
                    )

        # Entry Condition: Undervalued YES shares
        if not has_open and edge >= 0.05:
            return StrategyDecision(
                action=Signal.BUY,
                symbol=symbol,
                stake_usd=self.params['stake_usd'],
                stop_loss_pct=self.params['stop_loss_pct'],
                take_profit_pct=self.params['take_profit_pct'],
                trailing_stop_pct=self.params['trailing_stop_pct'],
                reason=f"Polymarket Edge +{edge*100:.1f}% on '{market_question[:35]}...' (Fair Prob: {implied_spot_prob:.2f} vs Market: ${market_yes_price:.2f})"
            )

        return StrategyDecision(
            action=Signal.HOLD,
            symbol=symbol,
            reason=f"Polymarket odds fair (Edge: {edge*100:.1f}%, Fair: {implied_spot_prob:.2f})"
        )
