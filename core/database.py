"""
Database management module for CryptoArena.
Stores tournament state, bot statistics, trades, positions, research logs, and parameter adaptations.
"""
import sqlite3
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger("CryptoArena.Database")

class ArenaDatabase:
    def __init__(self, db_path: Path):
        self.db_path = str(db_path)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self):
        """Ensures all new columns exist on legacy tables."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(bots)")
                cols = [r['name'] for r in cursor.fetchall()]
                if 'respawn_count' not in cols:
                    cursor.execute("ALTER TABLE bots ADD COLUMN respawn_count INTEGER DEFAULT 0")
                    conn.commit()
        except Exception as e:
            logger.warning(f"Schema migration note: {e}")

    def _init_db(self):
        """Initializes tables if they do not exist."""
        self._ensure_schema()
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Tournament Meta
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tournament_meta (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    start_time TEXT,
                    duration_days INTEGER DEFAULT 7,
                    initial_capital_per_bot REAL DEFAULT 50.0,
                    status TEXT DEFAULT 'RUNNING'
                )
            """)

            # Bots Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bots (
                    bot_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    strategy_name TEXT NOT NULL,
                    description TEXT,
                    initial_capital REAL DEFAULT 50.0,
                    current_balance REAL DEFAULT 50.0,
                    available_balance REAL DEFAULT 50.0,
                    total_pnl REAL DEFAULT 0.0,
                    roi_pct REAL DEFAULT 0.0,
                    win_rate REAL DEFAULT 0.0,
                    total_trades INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    losing_trades INTEGER DEFAULT 0,
                    max_drawdown REAL DEFAULT 0.0,
                    peak_equity REAL DEFAULT 50.0,
                    is_active INTEGER DEFAULT 1,
                    respawn_count INTEGER DEFAULT 0,
                    created_at TEXT
                )
            """)

            try:
                cursor.execute("ALTER TABLE bots ADD COLUMN respawn_count INTEGER DEFAULT 0")
            except Exception:
                pass

            # Positions Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    position_id TEXT PRIMARY KEY,
                    bot_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    current_price REAL NOT NULL,
                    quantity REAL NOT NULL,
                    cost_basis REAL NOT NULL,
                    stop_loss REAL,
                    take_profit REAL,
                    trailing_stop_pct REAL,
                    highest_price REAL,
                    unrealized_pnl REAL DEFAULT 0.0,
                    unrealized_pnl_pct REAL DEFAULT 0.0,
                    status TEXT DEFAULT 'OPEN',
                    opened_at TEXT,
                    closed_at TEXT,
                    FOREIGN KEY (bot_id) REFERENCES bots (bot_id)
                )
            """)

            # Trades History Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    trade_id TEXT PRIMARY KEY,
                    bot_id TEXT NOT NULL,
                    position_id TEXT,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    price REAL NOT NULL,
                    quantity REAL NOT NULL,
                    cost_or_proceeds REAL NOT NULL,
                    fee_paid REAL NOT NULL,
                    realized_pnl REAL DEFAULT 0.0,
                    realized_pnl_pct REAL DEFAULT 0.0,
                    reason TEXT,
                    timestamp TEXT,
                    FOREIGN KEY (bot_id) REFERENCES bots (bot_id)
                )
            """)

            # Equity Snapshots (for charting equity curves)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS equity_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bot_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    balance REAL NOT NULL,
                    unrealized_pnl REAL NOT NULL,
                    total_equity REAL NOT NULL,
                    roi_pct REAL NOT NULL,
                    FOREIGN KEY (bot_id) REFERENCES bots (bot_id)
                )
            """)

            # Autonomous Research Logs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS research_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    category TEXT NOT NULL,
                    title TEXT NOT NULL,
                    details_json TEXT
                )
            """)

            # Self-Improvement Parameter Adjustments
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS parameter_adjustments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bot_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    parameter_name TEXT NOT NULL,
                    old_value TEXT,
                    new_value TEXT,
                    reason TEXT,
                    FOREIGN KEY (bot_id) REFERENCES bots (bot_id)
                )
            """)

            conn.commit()

    # --- Tournament Management ---
    def init_tournament(self, name: str, capital_per_bot: float = 50.0):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM tournament_meta WHERE id = 1")
            row = cursor.fetchone()
            now_iso = datetime.now(timezone.utc).isoformat()
            if not row:
                cursor.execute("""
                    INSERT INTO tournament_meta (id, name, start_time, duration_days, initial_capital_per_bot, status)
                    VALUES (1, ?, ?, 7, ?, 'RUNNING')
                """, (name, now_iso, capital_per_bot))
                conn.commit()

    def get_tournament_meta(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tournament_meta WHERE id = 1")
            row = cursor.fetchone()
            if row:
                return dict(row)
            return {}

    # --- Bot CRUD & Stats ---
    def register_bot(self, bot_id: str, name: str, strategy_name: str, description: str, initial_capital: float = 50.0):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now_iso = datetime.now(timezone.utc).isoformat()
            cursor.execute("""
                INSERT OR IGNORE INTO bots (
                    bot_id, name, strategy_name, description, initial_capital, current_balance,
                    available_balance, total_pnl, roi_pct, win_rate, total_trades, winning_trades,
                    losing_trades, max_drawdown, peak_equity, is_active, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0.0, 0.0, 0.0, 0, 0, 0, 0.0, ?, 1, ?)
            """, (bot_id, name, strategy_name, description, initial_capital, initial_capital, initial_capital, initial_capital, now_iso))
            conn.commit()

    def get_all_bots(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM bots ORDER BY total_pnl DESC")
            bots = []
            for row in cursor.fetchall():
                d = dict(row)
                if 'respawn_count' not in d:
                    d['respawn_count'] = 0
                bots.append(d)
            return bots

    def get_bot(self, bot_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM bots WHERE bot_id = ?", (bot_id,))
            row = cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            if 'respawn_count' not in d:
                d['respawn_count'] = 0
            return d

    def update_bot_stats(self, bot_id: str, current_balance: float, available_balance: float,
                         total_pnl: float, roi_pct: float, win_rate: float,
                         total_trades: int, winning_trades: int, losing_trades: int,
                         max_drawdown: float, peak_equity: float):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE bots SET
                    current_balance = ?,
                    available_balance = ?,
                    total_pnl = ?,
                    roi_pct = ?,
                    win_rate = ?,
                    total_trades = ?,
                    winning_trades = ?,
                    losing_trades = ?,
                    max_drawdown = ?,
                    peak_equity = ?
                WHERE bot_id = ?
            """, (current_balance, available_balance, total_pnl, roi_pct, win_rate,
                  total_trades, winning_trades, losing_trades, max_drawdown, peak_equity, bot_id))
            conn.commit()

    def set_bot_active_status(self, bot_id: str, is_active: bool):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE bots SET is_active = ? WHERE bot_id = ?", (1 if is_active else 0, bot_id))
            conn.commit()

    def delete_bot(self, bot_id: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM positions WHERE bot_id = ?", (bot_id,))
            cursor.execute("DELETE FROM trades WHERE bot_id = ?", (bot_id,))
            cursor.execute("DELETE FROM equity_snapshots WHERE bot_id = ?", (bot_id,))
            cursor.execute("DELETE FROM parameter_adjustments WHERE bot_id = ?", (bot_id,))
            cursor.execute("DELETE FROM bots WHERE bot_id = ?", (bot_id,))
            conn.commit()

    def reset_tournament(self, capital_per_bot: float = 50.0):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("ALTER TABLE bots ADD COLUMN respawn_count INTEGER DEFAULT 0")
                conn.commit()
            except Exception:
                pass
            cursor.execute("DELETE FROM positions")
            cursor.execute("DELETE FROM trades")
            cursor.execute("DELETE FROM equity_snapshots")
            cursor.execute("DELETE FROM parameter_adjustments")
            cursor.execute("DELETE FROM research_logs")
            try:
                cursor.execute("""
                    UPDATE bots SET
                        current_balance = initial_capital,
                        available_balance = initial_capital,
                        total_pnl = 0.0,
                        roi_pct = 0.0,
                        win_rate = 0.0,
                        total_trades = 0,
                        winning_trades = 0,
                        losing_trades = 0,
                        max_drawdown = 0.0,
                        peak_equity = initial_capital,
                        is_active = 1,
                        respawn_count = 0
                """)
            except Exception:
                cursor.execute("""
                    UPDATE bots SET
                        current_balance = initial_capital,
                        available_balance = initial_capital,
                        total_pnl = 0.0,
                        roi_pct = 0.0,
                        win_rate = 0.0,
                        total_trades = 0,
                        winning_trades = 0,
                        losing_trades = 0,
                        max_drawdown = 0.0,
                        peak_equity = initial_capital,
                        is_active = 1
                """)
            conn.commit()

    def respawn_bot(self, bot_id: str, capital: float = 50.0) -> int:
        """Resets bot balance to starting capital and increments respawn_count."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("ALTER TABLE bots ADD COLUMN respawn_count INTEGER DEFAULT 0")
                conn.commit()
            except Exception:
                pass
            cursor.execute("SELECT * FROM bots WHERE bot_id = ?", (bot_id,))
            row = cursor.fetchone()
            current_respawns = 0
            if row:
                d = dict(row)
                current_respawns = int(d.get('respawn_count') or 0)
            new_count = current_respawns + 1
            try:
                cursor.execute("""
                    UPDATE bots SET
                        current_balance = ?,
                        available_balance = ?,
                        total_pnl = 0.0,
                        roi_pct = 0.0,
                        is_active = 1,
                        respawn_count = ?
                    WHERE bot_id = ?
                """, (capital, capital, new_count, bot_id))
            except Exception:
                cursor.execute("""
                    UPDATE bots SET
                        current_balance = ?,
                        available_balance = ?,
                        total_pnl = 0.0,
                        roi_pct = 0.0,
                        is_active = 1
                    WHERE bot_id = ?
                """, (capital, capital, bot_id))
            cursor.execute("DELETE FROM positions WHERE bot_id = ?", (bot_id,))
            conn.commit()
            return new_count

    # --- Positions Management ---
    def save_position(self, pos: Dict[str, Any]):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO positions (
                    position_id, bot_id, symbol, side, entry_price, current_price,
                    quantity, cost_basis, stop_loss, take_profit, trailing_stop_pct,
                    highest_price, unrealized_pnl, unrealized_pnl_pct, status, opened_at, closed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pos['position_id'], pos['bot_id'], pos['symbol'], pos['side'],
                pos['entry_price'], pos['current_price'], pos['quantity'], pos['cost_basis'],
                pos.get('stop_loss'), pos.get('take_profit'), pos.get('trailing_stop_pct'),
                pos.get('highest_price', pos['entry_price']),
                pos.get('unrealized_pnl', 0.0), pos.get('unrealized_pnl_pct', 0.0),
                pos.get('status', 'OPEN'), pos['opened_at'], pos.get('closed_at')
            ))
            conn.commit()

    def get_open_positions(self, bot_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if bot_id:
                cursor.execute("SELECT * FROM positions WHERE bot_id = ? AND status = 'OPEN'", (bot_id,))
            else:
                cursor.execute("SELECT * FROM positions WHERE status = 'OPEN'")
            return [dict(row) for row in cursor.fetchall()]

    # --- Trades Recording ---
    def record_trade(self, trade: Dict[str, Any]):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trades (
                    trade_id, bot_id, position_id, symbol, side, price, quantity,
                    cost_or_proceeds, fee_paid, realized_pnl, realized_pnl_pct, reason, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade['trade_id'], trade['bot_id'], trade.get('position_id'),
                trade['symbol'], trade['side'], trade['price'], trade['quantity'],
                trade['cost_or_proceeds'], trade['fee_paid'], trade.get('realized_pnl', 0.0),
                trade.get('realized_pnl_pct', 0.0), trade.get('reason', 'MANUAL'), trade['timestamp']
            ))
            conn.commit()

    def get_trades(self, bot_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if bot_id:
                cursor.execute("SELECT * FROM trades WHERE bot_id = ? ORDER BY timestamp DESC LIMIT ?", (bot_id, limit))
            else:
                cursor.execute("SELECT * FROM trades ORDER BY timestamp DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]

    # --- Equity Snapshots ---
    def record_equity_snapshot(self, bot_id: str, balance: float, unrealized_pnl: float, total_equity: float, roi_pct: float):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now_iso = datetime.now(timezone.utc).isoformat()
            cursor.execute("""
                INSERT INTO equity_snapshots (bot_id, timestamp, balance, unrealized_pnl, total_equity, roi_pct)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (bot_id, now_iso, balance, unrealized_pnl, total_equity, roi_pct))
            conn.commit()

    def get_equity_history(self, bot_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if bot_id:
                cursor.execute("SELECT * FROM equity_snapshots WHERE bot_id = ? ORDER BY id ASC", (bot_id,))
            else:
                cursor.execute("SELECT * FROM equity_snapshots ORDER BY id ASC")
            return [dict(row) for row in cursor.fetchall()]

    # --- Research & Self-Improvement Logs ---
    def log_research(self, category: str, title: str, details: Dict[str, Any]):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now_iso = datetime.now(timezone.utc).isoformat()
            cursor.execute("""
                INSERT INTO research_logs (timestamp, category, title, details_json)
                VALUES (?, ?, ?, ?)
            """, (now_iso, category, title, json.dumps(details)))
            conn.commit()

    def get_research_logs(self, limit: int = 30) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM research_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            result = []
            for r in rows:
                d = dict(r)
                try:
                    d['details'] = json.loads(d['details_json'])
                except Exception:
                    d['details'] = {}
                result.append(d)
            return result

    def log_parameter_adjustment(self, bot_id: str, param_name: str, old_val: Any, new_val: Any, reason: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now_iso = datetime.now(timezone.utc).isoformat()
            cursor.execute("""
                INSERT INTO parameter_adjustments (bot_id, timestamp, parameter_name, old_value, new_value, reason)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (bot_id, now_iso, param_name, str(old_val), str(new_val), reason))
            conn.commit()

    def get_parameter_adjustments(self, bot_id: Optional[str] = None, limit: int = 30) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if bot_id:
                cursor.execute("SELECT * FROM parameter_adjustments WHERE bot_id = ? ORDER BY timestamp DESC LIMIT ?", (bot_id, limit))
            else:
                cursor.execute("SELECT * FROM parameter_adjustments ORDER BY timestamp DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]
