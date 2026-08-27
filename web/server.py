"""
Web Dashboard Server (FastAPI + WebSockets)
Provides real-time REST and WebSocket feeds for the CryptoArena Tournament.
"""
import os
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

try:
    from core.database import ArenaDatabase
    from core.engine import TournamentEngine
    from config import config
except (ImportError, ValueError):
    from ..core.database import ArenaDatabase
    from ..core.engine import TournamentEngine
    from ..config import config

logger = logging.getLogger("CryptoArena.WebServer")

# Global engine reference
engine: TournamentEngine = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI Lifespan: Initializes database, starts tournament engine 24/7 background loop."""
    global engine
    logger.info("Initializing CryptoArena Tournament Engine via FastAPI Lifespan...")
    db = ArenaDatabase(config.DB_PATH)
    engine = TournamentEngine(db)
    
    # Start 24/7 tournament loop in background
    tournament_task = asyncio.create_task(engine.start())
    yield
    # Graceful shutdown
    if engine:
        engine.stop()
    tournament_task.cancel()

app = FastAPI(title="CryptoArena 50X Control Dashboard", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

# Static files directory
STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(exist_ok=True, parents=True)

# REST Endpoints
@app.get("/api/leaderboard")
async def get_leaderboard():
    if not engine:
        return []
    return engine.get_leaderboard_data()

@app.get("/api/bots/{bot_id}")
async def get_bot_details(bot_id: str):
    if not engine:
        return {}
    bot = engine.db.get_bot(bot_id)
    if not bot:
        return JSONResponse(status_code=404, content={"error": "Bot not found"})

    wallet = engine.wallets.get(bot_id)
    strategy = engine.strategies.get(bot_id)
    positions = wallet.get_open_positions() if wallet else []
    trades = engine.db.get_trades(bot_id, limit=30)
    adjustments = engine.db.get_parameter_adjustments(bot_id, limit=20)
    equity_history = engine.db.get_equity_history(bot_id, limit=100)

    return {
        'bot': bot,
        'open_positions': positions,
        'trades': trades,
        'adjustments': adjustments,
        'strategy_params': strategy.params if strategy else {},
        'equity_history': equity_history
    }

@app.get("/api/positions")
async def get_positions():
    if not engine:
        return []
    return engine.db.get_open_positions()

@app.get("/api/trades")
async def get_trades():
    if not engine:
        return []
    return engine.db.get_trades(limit=50)

@app.get("/api/research")
async def get_research_logs():
    if not engine:
        return []
    return engine.db.get_research_logs(limit=25)

@app.get("/api/adjustments")
async def get_adjustments():
    if not engine:
        return []
    return engine.db.get_parameter_adjustments(limit=30)

@app.get("/api/equity-history")
async def get_equity_history():
    if not engine:
        return []
    return engine.db.get_equity_history(limit=200)

@app.get("/api/market-overview")
async def get_market_overview():
    if not engine:
        return {}
    return {
        'overview': engine.latest_market_overview,
        'tickers': engine.market_feed.cached_tickers
    }

@app.post("/api/export-winner")
async def export_winner():
    if not engine:
        return JSONResponse(status_code=500, content={"error": "Engine not running"})
    leaderboard = engine.get_leaderboard_data()
    if not leaderboard:
        return JSONResponse(status_code=400, content={"error": "No bot data available"})

    winner = leaderboard[0]
    export_payload = {
        'winner_bot_id': winner['bot_id'],
        'winner_name': winner['name'],
        'strategy_name': winner['strategy_name'],
        'roi_pct': winner['roi_pct'],
        'win_rate': winner['win_rate'],
        'total_pnl': winner['total_pnl'],
        'optimized_parameters': winner['active_strategy_params'],
        'recommended_stake_usd': 25.0,
        'trading_pairs': config.TRADING_PAIRS,
        'live_readiness': "READY_FOR_$50_DEPLOYMENT"
    }
    return export_payload

# --- Bot Control Endpoints ---
@app.post("/api/bots/{bot_id}/toggle")
async def toggle_bot(bot_id: str, payload: Dict[str, Any]):
    if not engine:
        return JSONResponse(status_code=500, content={"error": "Engine not running"})
    is_active = payload.get("is_active", True)
    success = engine.toggle_bot(bot_id, is_active)
    return {"bot_id": bot_id, "is_active": is_active, "success": success}

@app.post("/api/bots/{bot_id}/liquidate")
async def liquidate_bot(bot_id: str):
    if not engine:
        return JSONResponse(status_code=500, content={"error": "Engine not running"})
    closed_trades = engine.liquidate_bot(bot_id)
    return {"bot_id": bot_id, "closed_trades_count": len(closed_trades), "trades": closed_trades}

@app.post("/api/bots/{bot_id}/params")
async def update_bot_params(bot_id: str, payload: Dict[str, Any]):
    if not engine:
        return JSONResponse(status_code=500, content={"error": "Engine not running"})
    success = engine.update_bot_params(bot_id, payload)
    return {"bot_id": bot_id, "success": success, "updated_params": payload}

@app.post("/api/bots/create")
async def create_bot(payload: Dict[str, Any]):
    if not engine:
        return JSONResponse(status_code=500, content={"error": "Engine not running"})
    name = payload.get("name", "New Bot")
    strat_type = payload.get("strategy_type", "trend")
    description = payload.get("description", "")
    capital = float(payload.get("initial_capital", 50.0))
    params = payload.get("params", {})
    
    bot_info = engine.create_custom_bot(
        name=name,
        strategy_type=strat_type,
        description=description,
        initial_capital=capital,
        params=params
    )
    return {"success": True, "bot": bot_info}

@app.post("/api/bots/{bot_id}/manual-order")
async def manual_order(bot_id: str, payload: Dict[str, Any]):
    if not engine:
        return JSONResponse(status_code=500, content={"error": "Engine not running"})
    symbol = payload.get("symbol", "SOL/USDT")
    side = payload.get("side", "BUY")
    usd_amount = float(payload.get("usd_amount", 25.0))
    result = engine.execute_manual_trade(bot_id, symbol, side, usd_amount)
    return {"success": bool(result), "result": result}

@app.post("/api/tournament/reset")
async def reset_tournament_api(payload: Dict[str, Any] = None):
    if not engine:
        return JSONResponse(status_code=500, content={"error": "Engine not running"})
    capital = float(payload.get("capital_per_bot", 50.0)) if payload else 50.0
    engine.reset_tournament(capital)
    return {"success": True, "message": f"Tournament reset with ${capital} per bot"}

# WebSocket Endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Send live telemetry every 3 seconds
            if engine:
                payload = {
                    'type': 'TELEMETRY_UPDATE',
                    'leaderboard': engine.get_leaderboard_data(),
                    'market_overview': engine.latest_market_overview,
                    'tickers': engine.market_feed.cached_tickers,
                    'open_positions_count': len(engine.db.get_open_positions()),
                    'timestamp': asyncio.get_event_loop().time()
                }
                await websocket.send_text(json.dumps(payload))
            await asyncio.sleep(3)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

# Mount static folder
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
