"""
CryptoArena $300 Monthly Side Income Engine
Calculates daily run-rates, 30-day income projections, profit harvesting, and capital allocation models.
"""
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger("CryptoArena.IncomeEngine")

class MonthlyIncomeEngine:
    def __init__(self, db, monthly_target_usd: float = 300.0):
        self.db = db
        self.monthly_target_usd = monthly_target_usd
        self.daily_target_usd = monthly_target_usd / 30.0 # $10.00 / day
        self.harvested_vault_usd = 0.0
        self.last_harvest_time = 0.0

    def calculate_income_metrics(self, wallets: Dict[str, Any]) -> Dict[str, Any]:
        """Calculates current daily run-rate, projected monthly income, and progress toward $300/mo."""
        bots = self.db.get_all_bots()
        trades = self.db.get_trades(limit=200)

        total_equity = sum(w.get_total_equity() for w in wallets.values()) if wallets else sum(b.get('current_balance', 50.0) for b in bots)
        initial_capital = sum(b.get('initial_capital', 50.0) for b in bots)
        total_pnl = total_equity - initial_capital

        # Calculate 24h Realized PnL from recent trades
        now = time.time()
        one_day_ago = datetime.fromtimestamp(now - 86400, timezone.utc).isoformat()
        recent_24h_trades = [t for t in trades if t.get('timestamp', '') >= one_day_ago and t.get('realized_pnl') is not None]
        
        realized_24h_pnl = sum(t.get('realized_pnl', 0.0) for t in recent_24h_trades)
        
        # If running less than 24h, estimate run-rate based on active winning bots and trade frequency
        active_bots = [b for b in bots if b.get('is_active', 1)]
        winning_trades_count = sum(b.get('winning_trades', 0) for b in bots)
        total_trades_count = sum(b.get('total_trades', 0) for b in bots)
        overall_winrate = (winning_trades_count / total_trades_count * 100.0) if total_trades_count > 0 else 65.0

        # Estimated daily yield run rate
        daily_run_rate = max(realized_24h_pnl, max(0.0, total_pnl) / max(1.0, len(trades) / 10.0) if len(trades) > 0 else 2.50)
        projected_monthly_income = daily_run_rate * 30.0
        progress_pct = min(100.0, (projected_monthly_income / self.monthly_target_usd) * 100.0)

        # Capital Tiers Blueprint for $300/month
        capital_scenarios = [
            {
                "capital": 300.0,
                "monthly_target": 300.0,
                "required_monthly_roi": 100.0,
                "daily_roi": 3.33,
                "strategy": "Aggressive 5m Scalping on High-Beta Memes (SOL, PEPE, DOGE, SUI)",
                "recommended_stake": 35.0,
                "risk_profile": "High Alpha / Compounding"
            },
            {
                "capital": 500.0,
                "monthly_target": 300.0,
                "required_monthly_roi": 60.0,
                "daily_roi": 2.0,
                "strategy": "Balanced Multi-Bot Trio (MeanRevert 40% + Breakout 40% + AlphaTrend 20%)",
                "recommended_stake": 45.0,
                "risk_profile": "Optimal Risk-Adjusted Side Income"
            },
            {
                "capital": 1000.0,
                "monthly_target": 300.0,
                "required_monthly_roi": 30.0,
                "daily_roi": 1.0,
                "strategy": "Conservative Institutional Yield (ATR Volatility Sizing + Breakeven Stops)",
                "recommended_stake": 50.0,
                "risk_profile": "Low Risk / High Consistency"
            }
        ]

        # Top 3 Champion Allocation Fund
        sorted_bots = sorted(bots, key=lambda b: (b.get('total_pnl', 0.0), b.get('win_rate', 0.0)), reverse=True)
        top_3 = sorted_bots[:3] if len(sorted_bots) >= 3 else bots

        champion_fund = [
            {
                "bot_id": b.get('bot_id'),
                "name": b.get('name'),
                "strategy_name": b.get('strategy_name'),
                "equity": b.get('current_balance', 50.0),
                "win_rate": b.get('win_rate', 0.0),
                "pnl": b.get('total_pnl', 0.0),
                "role": "Lead Cash Flow Scalper" if i == 0 else ("Trend & Momentum Runner" if i == 1 else "Market Maker / Spread Harvester")
            }
            for i, b in enumerate(top_3)
        ]

        return {
            "monthly_target_usd": self.monthly_target_usd,
            "daily_target_usd": round(self.daily_target_usd, 2),
            "current_daily_yield": round(daily_run_rate, 2),
            "projected_monthly_income": round(projected_monthly_income, 2),
            "progress_to_goal_pct": round(progress_pct, 1),
            "total_arena_equity": round(total_equity, 2),
            "total_arena_pnl": round(total_pnl, 2),
            "harvested_vault_usd": round(self.harvested_vault_usd, 2),
            "overall_winrate": round(overall_winrate, 1),
            "capital_scenarios": capital_scenarios,
            "champion_fund": champion_fund
        }

    def harvest_profits(self, wallets: Dict[str, Any]) -> Dict[str, Any]:
        """Harvests accumulated profits above the initial $50 baseline into the Side Income Vault."""
        total_harvested = 0.0
        for bot_id, wallet in wallets.items():
            excess = wallet.current_balance - wallet.initial_capital
            if excess > 0.05:
                wallet.current_balance -= excess
                wallet.available_balance = max(wallet.initial_capital * 0.5, wallet.available_balance - excess)
                total_harvested += excess

        self.harvested_vault_usd += total_harvested
        self.last_harvest_time = time.time()
        
        self.db.log_research(
            category="PROFIT_HARVEST",
            title=f"Harvested ${total_harvested:.2f} to Monthly Side Income Vault",
            details={"harvested_amount": total_harvested, "total_vault": self.harvested_vault_usd}
        )
        return {
            "harvested_amount": round(total_harvested, 2),
            "total_vault_usd": round(self.harvested_vault_usd, 2)
        }
