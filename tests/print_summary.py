import sys, os
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.database import ArenaDatabase
from config import config

db = ArenaDatabase(config.DB_PATH)
bots = db.get_all_bots()
trades = db.get_trades(limit=10)
positions = db.get_open_positions()

print("=== CURRENT 12-BOT TOURNAMENT LEADERBOARD ===")
total_pnl = sum(b['total_pnl'] for b in bots)
total_eq = sum(b['current_balance'] for b in bots)
print(f"Total Arena Capital: ${total_eq:.2f} / $600.00 | Net Tournament PnL: ${total_pnl:+.2f}")
print("-" * 75)

for i, b in enumerate(bots):
    medal = "[1]" if i == 0 else ("[2]" if i == 1 else ("[3]" if i == 2 else f"[{i+1:02d}]"))
    print(f"{medal} | {b['name']:36s} | Eq: ${b['current_balance']:6.2f} | PnL: ${b['total_pnl']:+.2f} ({b['roi_pct']:+.2f}%) | WR: {b['win_rate']:5.1f}% | Trades: {b['total_trades']}")

print("\n=== RECENT EXECUTIONS ===")
for t in trades[:6]:
    print(f"{t['timestamp'][:19]} | {t['side']:4s} {t['symbol']:14s} | ${t['price']:8.2f} | PnL: ${t.get('realized_pnl', 0.0):+.2f} | {t.get('reason', '')[:45]}")

print(f"\nTotal Active Open Positions Across Arena: {len(positions)}")
for p in positions[:5]:
    print(f"• [{p['bot_id']}] {p['side']} {p['symbol']} @ ${p['entry_price']:.2f} (Cost: ${p['cost_basis']:.2f})")
