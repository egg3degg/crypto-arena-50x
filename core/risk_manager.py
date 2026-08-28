"""
Portfolio-Level Risk Manager & Drawdown Circuit Breaker
Enforces cross-bot correlation limits, directional exposure caps (70%),
and tournament drawdown circuit breaker (10% max DD).
"""
import logging
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timezone

logger = logging.getLogger("CryptoArena.RiskManager")

class PortfolioRiskManager:
    def __init__(self, max_exposure_ratio: float = 0.70, max_drawdown_pct: float = 0.10, circuit_breaker_threshold: Optional[float] = None):
        self.max_exposure_ratio = max_exposure_ratio
        self.max_drawdown_pct = max_drawdown_pct
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_active = False
        self.circuit_breaker_triggered_at: Optional[float] = None
        self.circuit_breaker_cooldown_seconds = 1800 # 30 minutes cooldown

        # Asset Correlation Clusters
        self.correlation_clusters = {
            'LARGE_CAP_CRYPTO': {'SOL/USDT', 'ETH/USDT', 'BTC/USDT', 'AVAX/USDT', 'NEAR/USDT', 'SUI/USDT'},
            'MEME_COINS': {'DOGE/USDT', 'PENGU/USDT', 'PEPE/USDT', 'WIF/USDT'},
            'NSE_STOCKS': {'RELIANCE', 'TATAMOTORS', 'NIFTY50', 'HDFCBANK'},
            'COMMODITIES': {'GOLD/USD', 'SILVER/USD'},
            'AI_TOKENS': {'RENDER/USDT', 'NEAR/USDT'}
        }
        self.max_positions_per_cluster = 3

    def get_asset_cluster(self, symbol: str) -> Optional[str]:
        """Maps a trading symbol to its correlation cluster."""
        for cluster_name, symbols in self.correlation_clusters.items():
            if symbol in symbols:
                return cluster_name
        return 'OTHER'

    def check_circuit_breaker(self, total_portfolio_equity: float, total_initial_capital: float = 600.0) -> Tuple[bool, str]:
        """Checks if the tournament 10% drawdown circuit breaker is triggered or cooling down."""
        now = datetime.now(timezone.utc).timestamp()

        # Check if cooling down
        if self.circuit_breaker_active:
            if self.circuit_breaker_triggered_at and (now - self.circuit_breaker_triggered_at > self.circuit_breaker_cooldown_seconds):
                self.circuit_breaker_active = False
                self.circuit_breaker_triggered_at = None
                logger.info("🟢 Portfolio Drawdown Circuit Breaker reset after 30-minute cooldown.")
            else:
                elapsed = int(now - (self.circuit_breaker_triggered_at or now))
                remaining = max(0, (self.circuit_breaker_cooldown_seconds - elapsed) // 60)
                return False, f"Portfolio Drawdown Circuit Breaker ACTIVE ({remaining}m cooling period remaining)"

        # Threshold is either explicitly set or 10% below total initial capital
        threshold = self.circuit_breaker_threshold if self.circuit_breaker_threshold is not None else (total_initial_capital * (1.0 - self.max_drawdown_pct))

        # Check threshold
        if total_portfolio_equity < threshold and total_initial_capital > 0:
            self.circuit_breaker_active = True
            self.circuit_breaker_triggered_at = now
            logger.warning(f"🚨 PORTFOLIO CIRCUIT BREAKER TRIGGERED! Total Equity (${total_portfolio_equity:.2f}) dropped below ${threshold:.2f} (10% DD threshold). Pausing new BUYs for 30m.")
            return False, f"Portfolio Drawdown Circuit Breaker Triggered (Equity: ${total_portfolio_equity:.2f} < ${threshold:.2f})"

        return True, "OK"

    def calculate_portfolio_metrics(self, wallets: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregates portfolio-wide capital, open positions, cluster distribution, and directional exposure."""
        total_equity = 0.0
        total_open_cost = 0.0
        cluster_counts: Dict[str, int] = {k: 0 for k in self.correlation_clusters}
        cluster_counts['OTHER'] = 0
        all_open_positions = []

        for bot_id, wallet in wallets.items():
            total_equity += wallet.get_total_equity()
            positions = wallet.get_open_positions()
            for p in positions:
                all_open_positions.append(p)
                cost = p.get('cost_basis', 0.0)
                total_open_cost += cost
                cluster = self.get_asset_cluster(p.get('symbol', ''))
                cluster_counts[cluster] = cluster_counts.get(cluster, 0) + 1

        exposure_ratio = (total_open_cost / total_equity) if total_equity > 0 else 0.0

        return {
            'total_equity': total_equity,
            'total_open_cost': total_open_cost,
            'exposure_ratio': exposure_ratio,
            'exposure_pct': round(exposure_ratio * 100.0, 1),
            'open_positions_count': len(all_open_positions),
            'cluster_counts': cluster_counts,
            'circuit_breaker_active': self.circuit_breaker_active
        }

    def should_allow_trade(
        self,
        bot_id: str,
        symbol: str,
        usd_amount: float,
        wallets: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Enforces all portfolio risk constraints prior to order execution."""
        metrics = self.calculate_portfolio_metrics(wallets)
        total_equity = metrics['total_equity']
        total_initial_cap = sum(w.initial_capital for w in wallets.values()) if wallets else 600.0

        # 1. Circuit Breaker Check
        cb_ok, cb_msg = self.check_circuit_breaker(total_equity, total_initial_capital=total_initial_cap)
        if not cb_ok:
            return False, cb_msg

        # 2. Maximum Directional Exposure Check (70% Max)
        projected_open_cost = metrics['total_open_cost'] + usd_amount
        projected_exposure = projected_open_cost / total_equity if total_equity > 0 else 1.0
        if projected_exposure > self.max_exposure_ratio:
            return False, f"Portfolio exposure cap exceeded (Projected: {projected_exposure*100:.1f}% > Max: {self.max_exposure_ratio*100:.0f}%)"

        # 3. Sector & Asset Correlation Cluster Check (Max 3 per cluster)
        target_cluster = self.get_asset_cluster(symbol)
        if target_cluster != 'OTHER':
            current_cluster_count = metrics['cluster_counts'].get(target_cluster, 0)
            if current_cluster_count >= self.max_positions_per_cluster:
                return False, f"Sector correlation limit reached for '{target_cluster}' ({current_cluster_count}/{self.max_positions_per_cluster} open positions)"

        return True, "OK"
