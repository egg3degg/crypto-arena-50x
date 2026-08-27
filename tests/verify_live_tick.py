import sys
from pathlib import Path

# Add root project dir to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import asyncio
from crypto_arena.core.engine import TournamentEngine
from crypto_arena.core.database import ArenaDatabase
from crypto_arena.config import config

async def test_live():
    db = ArenaDatabase(config.DB_PATH)
    engine = TournamentEngine(db)
    print("Testing live market feed & initial tick...")
    await engine.run_tick()
    print("\n--- Live Tournament Leaderboard Snapshot ---")
    for b in engine.get_leaderboard_data():
        print(f"[{b['name']}] Equity: ${b['current_equity']:.2f} | PnL: ${b['total_pnl']:+.2f} | Win Rate: {b['win_rate']:.1f}% | Open Trades: {b['open_positions_count']}")
    print("--- End Snapshot ---\n")

if __name__ == "__main__":
    asyncio.run(test_live())
