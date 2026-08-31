"""
Dynamic Capital Allocator & Strategy Health Monitor
Tracks rolling Sharpe ratios, win-rates, and dynamically redistributes stake sizing
while capping simulated feeds and flagging decaying strategies.
"""
import math
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("CryptoArena.CapitalAllocator")

class CapitalAllocator:
    def __init__(self, db, base_stake_usd: float = 25.0):
        self.db = db
        self.base_stake_usd = base_stake_usd
        self.bot_allocations: Dict[str, float] = {}
        self.bot_health_status: Dict[str, str] = {} # 'HEALTHY', 'DEGRADING', 'PAUSED_DECAY'
        self.last_rebalance_time = 0

        # Synthetic/simulated feed bots that must be restricted to 50% max stake
        self.synthetic_feed_bots = {
            'bot_7_bharatbreakout',
            'bot_8_desimeanrevert',
            'bot_9_hypergoldsilver'
        }

    def calculate_rolling_sharpe(self, bot_id: str, lookback_hours: int = 24) -> Dict[str, float]:
        """Calculates rolling annualized Sharpe and Sortino ratio for a bot from its trade history."""
        trades = self.db.get_trades(bot_id, limit=50)
        closed_trades = [t for t in trades if t['side'] == 'SELL']

        if not closed_trades or len(closed_trades) < 2:
            return {'sharpe': 0.0, 'sortino': 0.0, 'win_rate': 0.0, 'trade_count': len(closed_trades)}

        # Filter by lookback window if timestamps exist
        now = datetime.now(timezone.utc)
        recent_trades = []
        for t in closed_trades:
            try:
                t_time = datetime.fromisoformat(t['timestamp'].replace('Z', '+00:00'))
                if (now - t_time).total_seconds() <= lookback_hours * 3600:
                    recent_trades.append(t)
            except Exception:
                recent_trades.append(t)

        if not recent_trades:
            recent_trades = closed_trades[-5:] # Fallback to latest 5 trades

        pnls = [t.get('realized_pnl', 0.0) for t in recent_trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]

        mean_pnl = sum(pnls) / len(pnls)
        variance = sum((p - mean_pnl) ** 2 for p in pnls) / max(1, len(pnls) - 1)
        std_pnl = math.sqrt(variance) if variance > 0 else 0.0001

        downside_variance = sum(p ** 2 for p in losses) / max(1, len(pnls) - 1) if losses else 0.0001
        downside_std = math.sqrt(downside_variance)

        # Annualized approx factor (based on ~10 trades/day)
        annual_factor = math.sqrt(365 * 12)
        sharpe = (mean_pnl / std_pnl) * annual_factor if std_pnl > 0 else 0.0
        sortino = (mean_pnl / downside_std) * annual_factor if downside_std > 0 else 0.0
        win_rate = (len(wins) / len(pnls) * 100.0) if pnls else 0.0

        return {
            'sharpe': round(max(-5.0, min(5.0, sharpe)), 2),
            'sortino': round(max(-5.0, min(5.0, sortino)), 2),
            'win_rate': round(win_rate, 1),
            'trade_count': len(recent_trades),
            'avg_pnl': round(mean_pnl, 2)
        }

    def rebalance_allocations(self, strategies: Dict[str, Any], force: bool = False) -> Dict[str, Any]:
        """Redistributes capital sizing based on risk-adjusted performance."""
        now = datetime.now(timezone.utc).timestamp()
        if not force and (now - self.last_rebalance_time < 3600 * 6):
            return self.bot_allocations

        self.last_rebalance_time = now
        bots = self.db.get_all_bots()
        reallocations = {}
        health_updates = {}

        for bot in bots:
            bot_id = bot['bot_id']
            # If bot was killed/eliminated, freeze allocation to $0
            if not bot.get('is_active', 1) or float(bot.get('current_balance', 50.0)) <= 0.0:
                self.bot_allocations[bot_id] = 0.0
                self.bot_health_status[bot_id] = 'KILLED_BUST'
                reallocations[bot_id] = {
                    'stake_usd': 0.0,
                    'multiplier': 0.0,
                    'health': 'KILLED_BUST',
                    'sharpe': 0.0,
                    'win_rate': 0.0
                }
                continue

            perf_24h = self.calculate_rolling_sharpe(bot_id, lookback_hours=24)
            sharpe = perf_24h['sharpe']
            win_rate = perf_24h['win_rate']
            trade_count = perf_24h['trade_count']
            max_dd = bot.get('max_drawdown', 0.0)

            # Determine Base Allocation Multiplier
            if sharpe >= 1.5 and win_rate >= 55.0 and max_dd < 3.0:
                multiplier = 1.5 # High alpha multiplier
                health = 'HEALTHY'
            elif sharpe >= 0.5 and win_rate >= 50.0:
                multiplier = 1.2 # Moderate boost
                health = 'HEALTHY'
            elif sharpe < 0.0 and trade_count >= 4 and max_dd > 4.0:
                multiplier = 0.5 # Defensive cut
                health = 'DEGRADING'
            elif sharpe < -1.0 and trade_count >= 6:
                multiplier = 0.4
                health = 'PAUSED_DECAY'
            else:
                multiplier = 1.0 # Standard base
                health = 'HEALTHY'

            # Dynamic Fractional Compounding: Scale base stake with growing equity (45% of total equity)
            bot_equity = float(bot.get('current_balance', 50.0))
            dynamic_base = max(self.base_stake_usd, bot_equity * 0.45)

            # Apply Hard Rule: Synthetic/Simulated Feeds capped at max $12.50
            if bot_id in self.synthetic_feed_bots:
                target_stake = min(12.50, round(self.base_stake_usd * min(multiplier, 0.5), 2))
            else:
                target_stake = round(dynamic_base * multiplier, 2)
                # Ensure stake is bounded between $10 floor and 50% of bot equity
                target_stake = max(10.0, min(max(45.0, bot_equity * 0.50), target_stake))

            self.bot_allocations[bot_id] = target_stake
            self.bot_health_status[bot_id] = health
            reallocations[bot_id] = {
                'stake_usd': target_stake,
                'multiplier': multiplier,
                'health': health,
                'sharpe': sharpe,
                'win_rate': win_rate
            }

            # Update strategy parameters live
            if bot_id in strategies:
                strat = strategies[bot_id]
                strat.params['stake_usd'] = target_stake
                strat.params['health_status'] = health

        # Log allocation event to research logs
        summary_msg = f"Rebalanced capital for {len(bots)} bots. Top alloc: ${max(self.bot_allocations.values()):.2f}, Min alloc: ${min(self.bot_allocations.values()):.2f}"
        self.db.log_research(
            category="CAPITAL_ALLOCATION",
            title="Automated Risk-Adjusted Capital Rebalance",
            details={"summary": summary_msg, "allocations": reallocations}
        )
        logger.info(f"Capital Rebalance Completed: {summary_msg}")
        return reallocations

    def get_bot_stake(self, bot_id: str) -> float:
        """Returns the current dynamically assigned stake for a given bot."""
        if bot_id in self.synthetic_feed_bots:
            return min(self.bot_allocations.get(bot_id, 12.50), 12.50)
        return self.bot_allocations.get(bot_id, self.base_stake_usd)

    def get_bot_health(self, bot_id: str) -> str:
        """Returns HEALTHY, DEGRADING, or PAUSED_DECAY for UI badge rendering."""
        return self.bot_health_status.get(bot_id, 'HEALTHY')
