"""
Unit Tests for MemoryGuard and Low-Memory Database/MarketFeed Optimizations
"""
import sys
import time
import os
import unittest
import tempfile
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from core.memory_guard import get_process_rss_mb, trim_memory, MemoryGuard
from core.database import ArenaDatabase
from core.market_feed import MarketFeed


class TestMemoryOptimization(unittest.TestCase):
    def setUp(self):
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        self.db = ArenaDatabase(self.temp_db_path)
        self.db.init_tournament("Test Arena", 50.0)
        self.db.register_bot("bot_test", "TestBot", "TestStrategy", "Testing", 50.0)

    def tearDown(self):
        try:
            os.close(self.temp_db_fd)
            if os.path.exists(self.temp_db_path):
                os.remove(self.temp_db_path)
        except Exception:
            pass

    def test_memory_guard_trim(self):
        rss = trim_memory()
        self.assertIsInstance(rss, float)
        self.assertGreaterEqual(rss, 0.0)

    def test_database_snapshot_pruning_and_limit(self):
        # Insert 50 snapshots
        for i in range(50):
            self.db.record_equity_snapshot("bot_test", 50.0 + i, 0.0, 50.0 + i, float(i))

        # Query with limit 10
        snaps_10 = self.db.get_equity_history("bot_test", limit=10)
        self.assertEqual(len(snaps_10), 10)
        # Should be ordered ascending by id
        self.assertLess(snaps_10[0]['id'], snaps_10[-1]['id'])

        # Test prune
        self.db.prune_old_snapshots(keep_latest=15)
        remaining = self.db.get_equity_history("bot_test", limit=100)
        self.assertEqual(len(remaining), 15)

    def test_market_feed_ttl_cache(self):
        feed = MarketFeed(exchange_id="binance", limit=20)
        # 1. Fetch synthetic/cached dataframe
        df1 = feed.fetch_ohlcv_dataframe("SOL/USDT")
        cache_time_1 = feed.candle_cache_times.get("SOL/USDT")
        self.assertIsNotNone(cache_time_1)

        # 2. Immediate second call should hit TTL cache (within 15s) and return same object
        df2 = feed.fetch_ohlcv_dataframe("SOL/USDT")
        self.assertIs(df1, df2)

        # 3. Test clear_cache
        feed.clear_cache()
        self.assertEqual(len(feed.cached_candles), 0)
        self.assertEqual(len(feed.candle_cache_times), 0)


if __name__ == "__main__":
    unittest.main()
