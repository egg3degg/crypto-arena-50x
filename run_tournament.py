"""
CryptoArena 50X - Main Runner
Launches the 5-Bot Tournament Engine and Web Dashboard.
"""
import sys
import os
from pathlib import Path

# Force UTF-8 on Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ensure root dir is in path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import uvicorn
from config import config

if __name__ == "__main__":
    host = os.getenv("WEB_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", os.getenv("WEB_PORT", "8088")))
    
    print("=" * 60)
    print("⚡ CryptoArena 50X - Multi-Bot 24/7 Autonomous Engine ⚡")
    print(f"• Listening on: http://{host}:{port}")
    print("• $50 Paper Capital Allocated per Bot ($250 Total)")
    print("• 5 Strategies Active (Trend, MeanRevert, Breakout, Grid, SmartMoney)")
    print("=" * 60)

    uvicorn.run(
        "web.server:app",
        host=host,
        port=port,
        log_level="info"
    )
