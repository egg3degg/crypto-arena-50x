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

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from ..core.engine import TournamentEngine
from ..config import config

logger = logging.getLogger("CryptoArena.WebServer")

app = FastAPI(title="CryptoArena 50X Control Dashboard", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global engine reference
engine: TournamentEngine = None

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
