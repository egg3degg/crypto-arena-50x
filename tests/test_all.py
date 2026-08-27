"""
Comprehensive Unit & Integration Test Suite for CryptoArena 50X
"""
import pytest
import numpy as np
import pandas as pd
from pathlib import Path
import tempfile
import shutil
import gc
import os

from crypto_arena.core.database import ArenaDatabase
from crypto_arena.core.simulator import PaperWallet
from crypto_arena.core.market_feed import MarketFeed
from crypto_arena.strategies.alpha_trend import AlphaTrendStrategy
from crypto_arena.strategies.mean_revert import MeanRevertStrategy
from crypto_arena.strategies.breakout_hunter import BreakoutHunterStrategy
from crypto_arena.strategies.adaptive_grid import AdaptiveGridStrategy
from crypto_arena.strategies.smart_money import SmartMoneyTrackerStrategy
from crypto_arena.research.regime_analyzer import MarketRegimeAnalyzer
from crypto_arena.research.smart_wallet_tracker import SmartWalletTracker
from crypto_arena.learning.self_improver import SelfImprovementEngine

@pytest.fixture
def temp_db():
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_arena.db"
    db = ArenaDatabase(db_path)
    yield db
    gc.collect()
    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass

def test_database_and_wallet_initialization(temp_db):
    temp_db.init_tournament("Test Cup", capital_per_bot=50.0)
    temp_db.register_bot("bot_1", "TestBot", "TestStrategy", "Desc", 50.0)

    wallet = PaperWallet("bot_1", temp_db, initial_capital=50.0)
    assert wallet.current_balance == 50.0
    assert wallet.available_balance == 50.0
    assert wallet.get_total_equity() == 50.0

def test_wallet_buy_and_sell_cycle(temp_db):
    temp_db.register_bot("bot_1", "TestBot", "TestStrategy", "Desc", 50.0)
    wallet = PaperWallet("bot_1", temp_db, initial_capital=50.0)

    # Execute Buy with $25
    pos = wallet.execute_buy("SOL/USDT", price=100.0, usd_amount=25.0, stop_loss_pct=0.03, take_profit_pct=0.05)
    assert pos is not None
    assert wallet.available_balance == 25.0
    assert len(wallet.get_open_positions()) == 1

    # Update price upward to 106 (should trigger Take Profit at 105+)
    wallet.update_open_positions_market_price("SOL/USDT", 106.0)
    assert len(wallet.get_open_positions()) == 0
    assert wallet.available_balance > 50.0
    assert wallet.total_pnl > 0
    assert wallet.winning_trades == 1

def test_market_feed_indicator_calculations():
    feed = MarketFeed()
    df = feed._generate_fallback_df("SOL/USDT")
    assert 'ema_20' in df.columns
    assert 'rsi' in df.columns
    assert 'bb_upper' in df.columns
    assert 'atr' in df.columns
    assert 'adx' in df.columns
    assert not df['rsi'].isna().all()

def test_strategies_evaluation():
    feed = MarketFeed()
    df = feed._generate_fallback_df("SOL/USDT")
    ticker = {'symbol': 'SOL/USDT', 'price': float(df.iloc[-1]['close'])}

    strategies = [
        AlphaTrendStrategy("bot_1"),
        MeanRevertStrategy("bot_2"),
        BreakoutHunterStrategy("bot_3"),
        AdaptiveGridStrategy("bot_4"),
        SmartMoneyTrackerStrategy("bot_5")
    ]

    for strat in strategies:
        decision = strat.evaluate("SOL/USDT", df, ticker, open_positions=[], available_balance=50.0)
        assert decision.action in ["BUY", "SELL", "HOLD"]

def test_regime_analyzer(temp_db):
    analyzer = MarketRegimeAnalyzer(temp_db)
    feed = MarketFeed()
    df = feed._generate_fallback_df("SOL/USDT")
    res = analyzer.analyze_pair("SOL/USDT", df)
    assert res['regime'] in ["STRONG_BULL_TREND", "STRONG_BEAR_TREND", "RANGING_CHOPPY", "HIGH_VOLATILITY_EXPANSION"]

def test_self_improver(temp_db):
    strat = AlphaTrendStrategy("bot_1_alphatrend")
    temp_db.register_bot("bot_1_alphatrend", "AlphaTrend", "Strategy", "Desc", 50.0)
    improver = SelfImprovementEngine(temp_db, {"bot_1_alphatrend": strat})

    market_overview = {'overall_market_state': 'BULLISH_MOMENTUM'}
    adjustments = improver.evaluate_and_optimize(market_overview)
    assert len(adjustments) > 0
    assert strat.params['take_profit_pct'] == 0.055
