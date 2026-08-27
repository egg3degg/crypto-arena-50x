"""
Bot 12: PolyMicroBotHunter - Polymarket Automated Algo Bot Wallet Mirror ($5-$10 Micro-Trades)
Tracks and copies high-frequency algorithm bot wallets on Polymarket executing $5-$10 micro-transactions
with >83% win rate and rapid daily compounding.
"""
from typing import Dict, List, Any, Optional
import pandas as pd

try:
    from strategies.base_strategy import BaseStrategy, StrategyDecision, Signal
except (ImportError, ValueError):
    from .base_strategy import BaseStrategy, StrategyDecision, Signal

class PolyMicroBotHunterStrategy(BaseStrategy):
    def __init__(self, bot_id: str = "poly_micro_bot"):
        super().__init__(
            bot_id=bot_id,
            name="PolyMicroBotHunter ($5-$10 Algo Bot Sniper)",
            description="Auto-mirrors profitable automated algorithm bots executing $5-$10 micro-bets with >83% win rate"
        )
        self.params = {
            'min_algo_winrate': 82.0,
            'stake_usd': 8.0,            # Ultra-micro $8.00 stake per trade
            'take_profit_pct': 0.28,     # 28% rapid profit scalp
            'stop_loss_pct': 0.15        # 15% tight stop loss
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
            return StrategyDecision(action=Signal.HOLD, symbol=symbol, reason="Insufficient micro capital")

        # Exit logic
        for p in open_positions:
            unrealized_pct = p.get('unrealized_pnl_pct', 0.0) / 100.0
            if unrealized_pct >= self.params['take_profit_pct']:
                return StrategyDecision(
                    action=Signal.SELL,
                    symbol=p['symbol'],
                    reason=f"Micro Algo Scalp Hit (+{unrealized_pct*100:.1f}%)"
                )
            if unrealized_pct <= -self.params['stop_loss_pct']:
                return StrategyDecision(
                    action=Signal.SELL,
                    symbol=p['symbol'],
                    reason=f"Micro Algo Stop-Loss Hit ({unrealized_pct*100:.1f}%)"
                )

        if not whale_bets:
            return StrategyDecision(action=Signal.HOLD, symbol=symbol, reason="Scanning Algo Bot Wallets")

        # Filter specifically for ALGO_BOT tier
        algo_bets = [b for b in whale_bets if b.get('tier') == 'ALGO_BOT']
        for bet in algo_bets:
            win_rate = bet.get('win_rate', 0.0)
            bot_name = bet.get('whale_name', 'AlgoBot')
            q = bet.get('market_question', '')
            choice = bet.get('outcome_choice', 'YES')
            entry_price = bet.get('entry_price', 0.50)
            algo_stake = bet.get('whale_stake_usd', 8.0)

            poly_symbol = f"ALGO_{choice}"
            # Check if this specific bet is already active
            has_pos = any(p['symbol'] == poly_symbol for p in open_positions)

            if not has_pos and win_rate >= self.params['min_algo_winrate']:
                return StrategyDecision(
                    action=Signal.BUY,
                    symbol=poly_symbol,
                    stake_usd=min(self.params['stake_usd'], available_balance),
                    stop_loss_pct=self.params['stop_loss_pct'],
                    take_profit_pct=self.params['take_profit_pct'],
                    reason=f"🤖 Copied Algo-Bot {bot_name} (${algo_stake:.2f} txn, {win_rate}% win) on '{q[:34]}...' -> {choice} @ ${entry_price:.2f}"
                )

        return StrategyDecision(action=Signal.HOLD, symbol=symbol, reason="Waiting for $5-$10 algo bot signals")
