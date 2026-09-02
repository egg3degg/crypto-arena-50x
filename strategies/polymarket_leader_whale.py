"""
Bot 11: PolyLeaderWhaleCopy - Polymarket Top-5 Leaderboard Whale Mirror
Monitors the #1-5 all-time most profitable accounts on Polymarket Leaderboard ($200k-$500k+ net profit)
and auto-replicates their massive high-conviction macro bets.
"""
from typing import Dict, List, Any, Optional
import pandas as pd

try:
    from strategies.base_strategy import BaseStrategy, StrategyDecision, Signal
except (ImportError, ValueError):
    from .base_strategy import BaseStrategy, StrategyDecision, Signal

class PolyLeaderWhaleStrategy(BaseStrategy):
    def __init__(self, bot_id: str = "poly_leader_whale"):
        super().__init__(
            bot_id=bot_id,
            name="PolyLeaderWhale (Top-5 Leaderboard Mirror)",
            description="Replicates high-conviction macro prediction bets from top-5 Polymarket leaderboard giants"
        )
        self.params = {
            'min_whale_winrate': 74.0,
            'stake_usd': 25.0,           # Scaled $25 stake per macro bet
            'take_profit_pct': 0.35,     # 35% profit target on shares
            'stop_loss_pct': 0.20        # 20% stop loss
        }

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
            return StrategyDecision(action=Signal.HOLD, symbol=symbol, reason="Insufficient leader copy capital")

        # Exit logic
        matching = [p for p in open_positions if p['symbol'] == symbol]
        for p in matching:
            unrealized_pct = p.get('unrealized_pnl_pct', 0.0) / 100.0
            if unrealized_pct >= self.params['take_profit_pct']:
                return StrategyDecision(
                    action=Signal.SELL,
                    symbol=symbol,
                    reason=f"Leaderboard Whale Target Hit (+{unrealized_pct*100:.1f}%)"
                )
            if unrealized_pct <= -self.params['stop_loss_pct']:
                return StrategyDecision(
                    action=Signal.SELL,
                    symbol=symbol,
                    reason=f"Leaderboard Stop-Loss Protected ({unrealized_pct*100:.1f}%)"
                )

        if not whale_bets:
            return StrategyDecision(action=Signal.HOLD, symbol=symbol, reason="Scanning Leaderboard Whales")

        # Filter specifically for LEADER_WHALE tier or any high winrate whale
        if len(matching) == 0:
            for bet in whale_bets:
                win_rate = bet.get('win_rate', 0.0)
                whale_name = bet.get('whale_name', 'LeaderWhale')
                q = bet.get('market_question', '')
                choice = bet.get('outcome_choice', 'YES')
                entry_price = bet.get('entry_price', 0.50)

                if win_rate >= 68.0:
                    return StrategyDecision(
                        action=Signal.BUY,
                        symbol=symbol,
                        stake_usd=self.params['stake_usd'],
                        stop_loss_pct=self.params['stop_loss_pct'],
                        take_profit_pct=self.params['take_profit_pct'],
                        reason=f"👑 Copied #{whale_name} (WinRate: {win_rate}%) on '{q[:36]}...' -> {choice} @ ${entry_price:.2f}"
                    )

        return StrategyDecision(action=Signal.HOLD, symbol=symbol, reason="Waiting for top leaderboard whale moves")
