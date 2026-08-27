"""
Market Regime Analyzer
Classifies current crypto market conditions into regimes:
- STRONG_BULL_TREND
- STRONG_BEAR_TREND
- RANGING_CHOPPY
- HIGH_VOLATILITY_EXPANSION
"""
import logging
from typing import Dict, List, Any
import numpy as np
import pandas as pd
try:
    from core.database import ArenaDatabase
except (ImportError, ValueError):
    from ..core.database import ArenaDatabase

logger = logging.getLogger("CryptoArena.RegimeAnalyzer")

class MarketRegimeAnalyzer:
    def __init__(self, db: ArenaDatabase):
        self.db = db
        self.current_regimes: Dict[str, Dict[str, Any]] = {}

    def analyze_pair(self, symbol: str, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyzes technical indicators to classify the market regime for a pair."""
        if len(df) < 30:
            return {
                'symbol': symbol,
                'regime': 'UNKNOWN',
                'trend_strength': 0.0,
                'volatility_pct': 0.0,
                'bias': 'NEUTRAL'
            }

        latest = df.iloc[-1]
        close = latest['close']
        adx = float(latest.get('adx', 20.0))
        atr = float(latest.get('atr', close * 0.02))
        volatility_pct = (atr / close) * 100.0

        ema_20 = float(latest.get('ema_20', close))
        ema_50 = float(latest.get('ema_50', close))
        ema_200 = float(latest.get('ema_200', close))
        rsi = float(latest.get('rsi', 50.0))

        # Determine regime
        if adx >= 25.0 and close > ema_50 and ema_20 > ema_50:
            regime = "STRONG_BULL_TREND"
            bias = "BULLISH"
        elif adx >= 25.0 and close < ema_50 and ema_20 < ema_50:
            regime = "STRONG_BEAR_TREND"
            bias = "BEARISH"
        elif volatility_pct > 3.5:
            regime = "HIGH_VOLATILITY_EXPANSION"
            bias = "VOLATILE"
        else:
            regime = "RANGING_CHOPPY"
            bias = "NEUTRAL"

        result = {
            'symbol': symbol,
            'regime': regime,
            'bias': bias,
            'adx': round(adx, 1),
            'rsi': round(rsi, 1),
            'volatility_pct': round(volatility_pct, 2),
            'price': round(close, 2)
        }
        self.current_regimes[symbol] = result
        return result

    def generate_market_overview(self, symbol_dfs: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Synthesizes market conditions across all watched pairs."""
        regimes = [self.analyze_pair(sym, df) for sym, df in symbol_dfs.items()]

        bull_count = sum(1 for r in regimes if r['bias'] == 'BULLISH')
        bear_count = sum(1 for r in regimes if r['bias'] == 'BEARISH')
        ranging_count = sum(1 for r in regimes if r['bias'] == 'NEUTRAL')

        overall_state = "BULLISH_MOMENTUM" if bull_count > bear_count and bull_count >= 2 else (
            "BEARISH_CORRECTION" if bear_count > bull_count and bear_count >= 2 else "SIDEWAYS_CONSOLIDATION"
        )

        overview = {
            'overall_market_state': overall_state,
            'bullish_pairs_count': bull_count,
            'bearish_pairs_count': bear_count,
            'ranging_pairs_count': ranging_count,
            'pair_regimes': regimes
        }

        # Log to DB
        self.db.log_research(
            category="MARKET_REGIME",
            title=f"Market Scan: {overall_state} ({bull_count} Bull, {ranging_count} Range, {bear_count} Bear)",
            details=overview
        )
        logger.info(f"Market Regime Scan completed: {overall_state}")
        return overview
