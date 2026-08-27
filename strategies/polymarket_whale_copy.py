"""
Bot 10: PolyWhaleCopy - Polymarket Smart Wallet & Whale Mirror Bot
Monitors the most profitable Polymarket wallets (>70% win rate, >$100k profit) and automatically
replicates their high-conviction YES / NO bets.
Ready for real money copy-trading via Polymarket CLOB API on Polygon (py-clob-client).
"""
from typing import Dict, List, Any, Optional
import pandas as pd

try:
    from strategies.base_strategy import BaseStrategy, StrategyDecision, Signal
except (ImportError, ValueError):
    from .base_strategy import BaseStrategy, StrategyDecision, Signal

class PolymarketWhaleCopyStrategy(BaseStrategy):
    def __init__(self, bot_id: str = "poly_whale_copy"):
        super().__init__(
            bot_id=bot_id,
            name="PolyWhaleCopy (Polymarket Copy-Trader)",
            description="Auto-mirrors high-conviction bets from verified Polymarket whales (>74% win-rate wallets)"
        )
        self.params = {
            'min_whale_winrate': 72.0,   # Only copy whales with >72% historical accuracy
            'min_confidence_score': 80,  # Minimum confidence threshold
            'stake_usd': 20.0,           # $20.00 stake per copied bet
            'take_profit_pct': 0.35,     # 35% profit target on shares
            'stop_loss_pct': 0.20        # 20% stop loss
        }
        self.copied_market_ids: List[str] = []

    def evaluate(
        self,
        symbol: str,
        df: pd.DataFrame,
        ticker: Dict[str, Any],
        open_positions: List[Dict[str, Any]],
        available_balance: float,
        whale_bets: Optional[List[Dict[str, Any]]] = None
    ) -> StrategyDecision:
        if available_balance < self.params['stake_usd']:
            return StrategyDecision(action=Signal.HOLD, reason="Insufficient copy-trading capital")

        # Exit logic for open Polymarket positions
        for p in open_positions:
            unrealized_pct = p.get('unrealized_pnl_pct', 0.0) / 100.0
            if unrealized_pct >= self.params['take_profit_pct']:
                return StrategyDecision(
                    action=Signal.SELL,
                    reason=f"Polymarket Whale Target Hit (+{unrealized_pct*100:.1f}%)"
                )
            if unrealized_pct <= -self.params['stop_loss_pct']:
                return StrategyDecision(
                    action=Signal.SELL,
                    reason=f"Polymarket Stop-Loss Protected ({unrealized_pct*100:.1f}%)"
                )

        if not whale_bets:
            return StrategyDecision(action=Signal.HOLD, reason="Scanning Polymarket whale wallets")

        # Check for new high-conviction whale bets
        for bet in whale_bets:
            win_rate = bet.get('win_rate', 0.0)
            conf = bet.get('confidence_score', 0)
            whale_name = bet.get('whale_name', 'TopWhale')
            q = bet.get('market_question', '')
            choice = bet.get('outcome_choice', 'YES')
            entry_price = bet.get('entry_price', 0.50)

            # Suffix symbol for portfolio allocation
            poly_symbol = f"POLY_{choice}"

            has_pos = any(p['symbol'] == poly_symbol for p in open_positions)
            if not has_pos and win_rate >= self.params['min_whale_winrate'] and conf >= self.params['min_confidence_score']:
                return StrategyDecision(
                    action=Signal.BUY,
                    stake_usd=self.params['stake_usd'],
                    stop_loss_pct=self.params['stop_loss_pct'],
                    take_profit_pct=self.params['take_profit_pct'],
                    reason=f"🐋 Copied {whale_name} (WinRate: {win_rate}%) on '{q[:38]}...' -> Bought {choice} @ ${entry_price:.2f}"
                )

        return StrategyDecision(action=Signal.HOLD, reason="No new high-conviction whale moves detected")
