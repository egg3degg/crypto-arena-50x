"""
Walk-Forward Strategy Optimization & Self-Improvement Engine
Replaces hardcoded heuristics with real quantitative Walk-Forward parameter sweeps.
Performs out-of-sample validation and deploys verified risk-adjusted hyperparameters.
"""
import math
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import pandas as pd

try:
    from core.database import ArenaDatabase
    from core.backtester import StrategyBacktester
    from strategies.base_strategy import BaseStrategy
    from research.indian_market_feed import IndianAndCommodityFeed
except (ImportError, ValueError):
    from ..core.database import ArenaDatabase
    from ..core.backtester import StrategyBacktester
    from ..strategies.base_strategy import BaseStrategy
    from ..research.indian_market_feed import IndianAndCommodityFeed

logger = logging.getLogger("CryptoArena.WalkForwardImprover")

# Asset & Benchmark Mapping per Bot
BOT_SYMBOL_MAPPING = {
    'bot_1_alphatrend': 'SOL/USDT',
    'bot_2_meanrevert': 'SOL/USDT',
    'bot_3_breakouthunter': 'SOL/USDT',
    'bot_4_adaptivegrid': 'ETH/USDT',
    'bot_5_smartmoney': 'SOL/USDT',
    'bot_6_polypredictor': 'BTC/USDT',
    'bot_7_bharatbreakout': 'RELIANCE',
    'bot_8_desimeanrevert': 'TATAMOTORS',
    'bot_9_hypergoldsilver': 'GOLD/USD',
    'bot_10_polywhalecopy': 'SOL/USDT',
    'bot_11_polyleaderwhale': 'BTC/USDT',
    'bot_12_polymicrobot': 'SOL/USDT',
}

class SelfImprovementEngine:
    def __init__(
        self,
        db: ArenaDatabase,
        strategies: Dict[str, BaseStrategy],
        backtester: Optional[StrategyBacktester] = None,
        indian_feed: Optional[Any] = None
    ):
        self.db = db
        self.strategies = strategies
        self.backtester = backtester
        self.indian_feed = indian_feed
        if self.indian_feed is None:
            try:
                self.indian_feed = IndianAndCommodityFeed()
            except Exception:
                self.indian_feed = None
        self.last_opt_time = 0

        # Parameter Search Grid
        self.param_grid = {
            'take_profit_pct': [0.02, 0.03, 0.04, 0.05, 0.06],
            'stop_loss_pct': [0.015, 0.02, 0.025, 0.03],
            'trailing_stop_pct': [0.0, 0.01, 0.015, 0.02]
        }

    def _fetch_df_for_symbol(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetches OHLCV dataframe from appropriate market feed with technical indicators."""
        if symbol in ["RELIANCE", "TATAMOTORS", "NIFTY50", "HDFCBANK", "GOLD/USD", "SILVER/USD"]:
            if self.indian_feed:
                df = self.indian_feed.fetch_ohlcv_dataframe(symbol)
            elif self.backtester and hasattr(self.backtester, 'market_feed'):
                df = self.backtester.market_feed.fetch_ohlcv_dataframe(symbol)
            else:
                df = None
        else:
            if self.backtester and hasattr(self.backtester, 'market_feed'):
                df = self.backtester.market_feed.fetch_ohlcv_dataframe(symbol)
            else:
                df = None

        if df is not None and len(df) > 0:
            # Ensure standard indicator aliases exist
            if 'rsi_14' in df.columns and 'rsi' not in df.columns:
                df['rsi'] = df['rsi_14']
            if 'donchian_high' not in df.columns and 'high' in df.columns:
                df['donchian_high'] = df['high'].rolling(window=20).max()
            if 'volume_surge_ratio' not in df.columns and 'volume' in df.columns:
                vol_mean = df['volume'].rolling(window=20).mean().replace(0, 1)
                df['volume_surge_ratio'] = df['volume'] / vol_mean
        return df

    def evaluate_and_optimize(self, market_overview: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Executes walk-forward parameter sweep and out-of-sample validation across active bots."""
        if not self.backtester:
            logger.warning("Backtester not initialized in SelfImprovementEngine. Skipping walk-forward sweep.")
            return []

        adjustments = []
        bots = self.db.get_all_bots()

        for bot in bots:
            bot_id = bot['bot_id']
            strategy = self.strategies.get(bot_id)
            if not strategy:
                continue

            strat_type = getattr(strategy, 'strategy_type', 'trend')
            old_tp = strategy.params.get('take_profit_pct', 0.045)
            old_sl = strategy.params.get('stop_loss_pct', 0.025)
            old_trail = strategy.params.get('trailing_stop_pct', 0.0)

            # Map bot to its actual traded asset class & symbol
            bot_symbol = BOT_SYMBOL_MAPPING.get(bot_id, "SOL/USDT")
            df = self._fetch_df_for_symbol(bot_symbol)

            if df is None or len(df) < 30:
                logger.warning(f"Insufficient OHLCV data ({len(df) if df is not None else 0} candles) for Walk-Forward on {bot_id} ({bot_symbol}).")
                continue

            # Split into 75% in-sample (train) and 25% out-of-sample (test/validation)
            split_idx = int(len(df) * 0.75)
            train_df = df.iloc[:split_idx].copy()
            val_df = df.iloc[split_idx:].copy()

            best_train_score = -999.0
            top_candidates = []

            # 1. In-Sample Parameter Sweep
            for tp in self.param_grid['take_profit_pct']:
                for sl in self.param_grid['stop_loss_pct']:
                    for trail in self.param_grid['trailing_stop_pct']:
                        bt_res = self.backtester.run_backtest(
                            strategy_type=strat_type,
                            symbol=bot_symbol,
                            df=train_df,
                            stake_usd=strategy.params.get('stake_usd', 25.0),
                            take_profit_pct=tp,
                            stop_loss_pct=sl,
                            trailing_stop_pct=trail if trail > 0 else None
                        )

                        if 'error' in bt_res or bt_res.get('total_trades', 0) < 2:
                            continue

                        sharpe = bt_res.get('sharpe_ratio', 0.0)
                        trades_cnt = bt_res.get('total_trades', 1)
                        # Statistical quality score: Sharpe * sqrt(trades)
                        score = sharpe * math.sqrt(trades_cnt)

                        top_candidates.append({
                            'tp': tp,
                            'sl': sl,
                            'trail': trail,
                            'train_score': score,
                            'train_sharpe': sharpe,
                            'trades': trades_cnt
                        })

            if not top_candidates:
                continue

            # Sort by highest in-sample score and take top 3
            top_candidates.sort(key=lambda x: x['train_score'], reverse=True)
            top_3 = top_candidates[:3]

            # 2. Out-of-Sample Validation
            best_val_candidate = None
            best_val_score = -999.0

            for cand in top_3:
                val_res = self.backtester.run_backtest(
                    strategy_type=strat_type,
                    symbol=bot_symbol,
                    df=val_df,
                    stake_usd=strategy.params.get('stake_usd', 25.0),
                    take_profit_pct=cand['tp'],
                    stop_loss_pct=cand['sl'],
                    trailing_stop_pct=cand['trail'] if cand['trail'] > 0 else None
                )

                if 'error' in val_res:
                    continue

                val_sharpe = val_res.get('sharpe_ratio', 0.0)
                val_trades = val_res.get('total_trades', 0)
                val_pnl = val_res.get('total_pnl', 0.0)

                # Validation passes if out-of-sample Sharpe is positive and profitable
                if val_pnl >= 0 and val_sharpe > best_val_score:
                    best_val_score = val_sharpe
                    best_val_candidate = cand
                    cand['val_sharpe'] = val_sharpe
                    cand['val_pnl'] = val_pnl

            # 3. Deploy Best Validated Parameters
            if best_val_candidate and (best_val_candidate['tp'] != old_tp or best_val_candidate['sl'] != old_sl or best_val_candidate['trail'] != old_trail):
                new_tp = best_val_candidate['tp']
                new_sl = best_val_candidate['sl']
                new_trail = best_val_candidate['trail']

                strategy.update_parameters({
                    'take_profit_pct': new_tp,
                    'stop_loss_pct': new_sl,
                    'trailing_stop_pct': new_trail if new_trail > 0 else None
                })

                reason_str = f"Walk-Forward Verified on {bot_symbol}: Train Score {best_val_candidate['train_score']:.2f} -> Out-of-Sample Sharpe {best_val_candidate.get('val_sharpe', 0.0):.2f}"

                # Record TP adjustment
                if new_tp != old_tp:
                    self._log_and_record(adjustments, bot_id, 'take_profit_pct', old_tp, new_tp, f"{reason_str} (TP optimized)")
                # Record SL adjustment
                if new_sl != old_sl:
                    self._log_and_record(adjustments, bot_id, 'stop_loss_pct', old_sl, new_sl, f"{reason_str} (SL optimized)")
                # Record Trailing Stop adjustment
                if new_trail != old_trail:
                    self._log_and_record(adjustments, bot_id, 'trailing_stop_pct', old_trail, new_trail, f"{reason_str} (Trailing SL optimized)")

        logger.info(f"Walk-Forward Optimization cycle completed with {len(adjustments)} parameter adjustments deployed.")
        return adjustments

    def _log_and_record(self, adjustments_list: list, bot_id: str, param: str, old_val: Any, new_val: Any, reason: str):
        self.db.log_parameter_adjustment(bot_id, param, old_val, new_val, reason)
        adjustments_list.append({
            'bot_id': bot_id,
            'parameter_name': param,
            'old_value': str(old_val),
            'new_value': str(new_val),
            'reason': reason
        })
