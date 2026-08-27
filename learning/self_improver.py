"""
Self-Improvement & Adaptation Engine
Monitors bot performance, win-rates, drawdowns, and adapts strategy hyperparameters dynamically.
"""
import logging
from typing import Dict, List, Any
from ..core.database import ArenaDatabase
from ..strategies.base_strategy import BaseStrategy

logger = logging.getLogger("CryptoArena.SelfImprover")

class SelfImprovementEngine:
    def __init__(self, db: ArenaDatabase, strategies: Dict[str, BaseStrategy]):
        self.db = db
        self.strategies = strategies

    def evaluate_and_optimize(self, market_overview: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Evaluates each bot's performance metrics and applies dynamic hyperparameter adaptations."""
        adjustments = []
        market_state = market_overview.get('overall_market_state', 'SIDEWAYS_CONSOLIDATION')
        bots = self.db.get_all_bots()

        for bot in bots:
            bot_id = bot['bot_id']
            strategy = self.strategies.get(bot_id)
            if not strategy:
                continue

            trades = self.db.get_trades(bot_id, limit=20)
            closed_trades = [t for t in trades if t['side'] == 'SELL']

            win_rate = bot['win_rate']
            total_trades = bot['total_trades']
            max_drawdown = bot['max_drawdown']

            # Adaptation 1: Market Regime Based Tuning
            if market_state == "BULLISH_MOMENTUM":
                if bot_id == "bot_1_alphatrend":
                    old_tp = strategy.params.get('take_profit_pct', 0.045)
                    new_tp = 0.055
                    if old_tp != new_tp:
                        strategy.update_parameters({'take_profit_pct': new_tp})
                        self._log_and_record(adjustments, bot_id, 'take_profit_pct', old_tp, new_tp,
                                             "Bullish momentum detected: Expanding TP to 5.5% to let winners run")

                elif bot_id == "bot_3_breakouthunter":
                    old_vol = strategy.params.get('volume_surge_multiplier', 1.8)
                    new_vol = 1.6
                    if old_vol != new_vol:
                        strategy.update_parameters({'volume_surge_multiplier': new_vol})
                        self._log_and_record(adjustments, bot_id, 'volume_surge_multiplier', old_vol, new_vol,
                                             "Bull trend: Lowering breakout volume threshold to 1.6x for earlier entries")

            elif market_state == "SIDEWAYS_CONSOLIDATION":
                if bot_id == "bot_2_meanrevert":
                    old_tp = strategy.params.get('take_profit_pct', 0.032)
                    new_tp = 0.024
                    if old_tp != new_tp:
                        strategy.update_parameters({'take_profit_pct': new_tp})
                        self._log_and_record(adjustments, bot_id, 'take_profit_pct', old_tp, new_tp,
                                             "Choppy regime: Tightening TP to 2.4% for rapid turnover")

                elif bot_id == "bot_4_adaptivegrid":
                    old_step = strategy.params.get('grid_step_pct', 0.015)
                    new_step = 0.012
                    if old_step != new_step:
                        strategy.update_parameters({'grid_step_pct': new_step})
                        self._log_and_record(adjustments, bot_id, 'grid_step_pct', old_step, new_step,
                                             "Choppy regime: Tightening grid step to 1.2% to catch micro-oscillations")

            # Adaptation 2: Risk Management / Drawdown Protection
            if max_drawdown > 4.0 or (total_trades >= 4 and win_rate < 40.0):
                # Tighten Stop Loss for risk protection
                current_sl = strategy.params.get('stop_loss_pct', 0.025)
                new_sl = max(0.015, current_sl * 0.85)
                if round(current_sl, 4) != round(new_sl, 4):
                    strategy.update_parameters({'stop_loss_pct': new_sl})
                    self._log_and_record(adjustments, bot_id, 'stop_loss_pct', round(current_sl, 4), round(new_sl, 4),
                                         f"Drawdown defense ({max_drawdown:.1f}% DD / {win_rate:.0f}% WR): Tightening Stop Loss to {new_sl*100:.2f}%")

            # Adaptation 3: High Win-Rate Alpha Boost
            elif total_trades >= 3 and win_rate >= 66.0 and max_drawdown < 2.0:
                current_stake = strategy.params.get('stake_usd', 25.0)
                # Allow sizing up to $30 if performing exceptionally well
                new_stake = min(35.0, current_stake + 5.0)
                if current_stake != new_stake:
                    strategy.update_parameters({'stake_usd': new_stake})
                    self._log_and_record(adjustments, bot_id, 'stake_usd', current_stake, new_stake,
                                         f"Alpha Performance Boost ({win_rate:.0f}% WR): Increasing stake size to ${new_stake:.2f}")

        logger.info(f"Self-Improvement evaluation completed. {len(adjustments)} parameter adjustments applied.")
        return adjustments

    def _log_and_record(self, adjustments_list: list, bot_id: str, param: str, old_val: Any, new_val: Any, reason: str):
        self.db.log_parameter_adjustment(bot_id, param, old_val, new_val, reason)
        adjustments_list.append({
            'bot_id': bot_id,
            'param': param,
            'old_value': old_val,
            'new_value': new_val,
            'reason': reason
        })
        logger.info(f"[Self-Improvement] Bot '{bot_id}' parameter '{param}' tuned: {old_val} -> {new_val} ({reason})")
