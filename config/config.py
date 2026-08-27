"""
CryptoArena Configuration File
"""
import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True, parents=True)
DB_PATH = DATA_DIR / "crypto_arena.db"

# Tournament Settings
TOURNAMENT_NAME = "CryptoArena 50X - 7-Day Alpha Cup"
INITIAL_CAPITAL_USD = 50.00
FEE_RATE = 0.00075  # 0.075% standard maker/taker fee
SLIPPAGE_RATE = 0.0005  # 0.05% realistic slippage simulation
MIN_ORDER_USD = 10.00  # Minimum order size per trade ($10-$25)
MAX_OPEN_TRADES_PER_BOT = 2  # Allows 2 concurrent $25 positions or 1 $50 position

# Trading Pairs (High Liquidity, low spread)
TRADING_PAIRS = [
    "SOL/USDT",
    "ETH/USDT",
    "BTC/USDT",
    "AVAX/USDT",
    "NEAR/USDT",
]

# Market Data Settings
TIMEFRAME = "15m"  # Primary strategy timeframe
DATA_EXCHANGE = "binance"  # "binance" or "bybit"
UPDATE_INTERVAL_SECONDS = 15  # Ticker update cycle
CANDLE_LIMIT = 100

# Research & Self-Improvement Interval
RESEARCH_CYCLE_SECONDS = 60 * 30  # Every 30 minutes
SELF_IMPROVE_CYCLE_SECONDS = 60 * 60 * 2  # Every 2 hours

# Telegram Notification Settings (Optional - can be set via env vars)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Web Dashboard Settings
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("PORT", os.getenv("WEB_PORT", "8088")))

