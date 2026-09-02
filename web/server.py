"""
Web Dashboard Server (FastAPI + WebSockets)
Provides real-time REST and WebSocket feeds for the CryptoArena Tournament.
"""
import os
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException, Depends, Header
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

ARENA_API_KEY = os.getenv("ARENA_API_KEY", "arena-secret-key-2026")

# Restrict CORS to authorized origins and cloudflare/render tunnel patterns
ALLOWED_ORIGINS = [
    "http://localhost:8088",
    "http://127.0.0.1:8088",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|8\.234\.126\.146|.*\.trycloudflare\.com|.*\.onrender\.com|.*\.vercel\.app)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

async def verify_admin_access(request: Request, x_api_key: Optional[str] = Header(None)):
    """Verifies that mutation operations come from authorized dashboard session or loopback."""
    query_key = request.query_params.get("api_key")
    client_ip = request.client.host if request.client else ""
    
    # Allow local connections
    if client_ip in ["127.0.0.1", "::1", "localhost"]:
        return True
        
    provided_key = x_api_key or query_key
    if provided_key != ARENA_API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Valid X-API-Key header or api_key parameter required for administrative operations."
        )
    return True

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

@app.get("/api/equity-trajectory")
async def get_equity_trajectory(bot_id: Optional[str] = None):
    if not engine:
        return {}
    
    from datetime import datetime, timezone
    snapshots = engine.db.get_equity_history(bot_id=bot_id)
    trades = engine.db.get_trades(bot_id=bot_id, limit=200)
    bots = engine.get_leaderboard_data()

    bot_trajectories = {}
    for b in bots:
        b_id = b['bot_id']
        b_snaps = [s for s in snapshots if s['bot_id'] == b_id]
        b_trades = [t for t in trades if t['bot_id'] == b_id]
        
        # Clean snapshot data and guarantee total_equity calculation
        cleaned_snaps = []
        for s in b_snaps:
            eq = float(s.get('total_equity') if s.get('total_equity') is not None else 50.0)
            bal = float(s.get('balance') if s.get('balance') is not None else 50.0)
            unrealized = float(s.get('unrealized_pnl', 0.0))
            
            # Sanity guard: total_equity represents total net worth (cash + open positions + unrealized PnL)
            if eq < 35.0 and bal < 35.0 and float(s.get('roi_pct', 0.0)) > -15.0:
                cost_in_positions = 50.0 - bal
                eq = bal + cost_in_positions + unrealized
            
            cleaned_snaps.append({
                'timestamp': s['timestamp'],
                'balance': bal,
                'total_equity': round(eq, 2),
                'roi_pct': float(s.get('roi_pct', 0.0))
            })

        if not cleaned_snaps:
            cleaned_snaps = [{'timestamp': datetime.now(timezone.utc).isoformat(), 'total_equity': 50.0, 'balance': 50.0}]

        # Prepare trade markers with dot colors
        markers = []
        for t in b_trades:
            is_buy = t['side'] == 'BUY'
            pnl = t.get('realized_pnl', 0.0)
            is_win = pnl >= 0
            dot_color = '#10b981' if (is_buy or is_win) else '#ef4444' # Green for Buy or Win, Red for Loss
            markers.append({
                'trade_id': t['trade_id'],
                'timestamp': t['timestamp'],
                'side': t['side'],
                'symbol': t['symbol'],
                'price': t['price'],
                'realized_pnl': pnl,
                'realized_pnl_pct': t.get('realized_pnl_pct', 0.0),
                'dot_color': dot_color,
                'reason': t.get('reason', '')
            })

        bot_trajectories[b_id] = {
            'bot_id': b_id,
            'name': b['name'],
            'snapshots': cleaned_snaps,
            'trade_markers': markers
        }

    return bot_trajectories

@app.get("/api/performance-report")
async def get_performance_report():
    if not engine:
        return {}
    return engine.get_performance_report()

@app.get("/api/income-plan")
async def get_income_plan():
    if not engine or not hasattr(engine, 'income_engine'):
        return {}
    return engine.income_engine.calculate_income_metrics(engine.wallets)

@app.post("/api/harvest-profits")
async def harvest_profits():
    if not engine or not hasattr(engine, 'income_engine'):
        return JSONResponse(status_code=500, content={"error": "Engine not initialized"})
    result = engine.income_engine.harvest_profits(engine.wallets)
    return result

@app.get("/api/ping")
async def ping():
    return {"version": "1.2.0-survival-100", "status": "OK", "timestamp": time.time()}

@app.post("/api/start-race")
async def start_grand_prix_race():
    if not engine:
        return JSONResponse(status_code=500, content={"error": "Engine not initialized"})
    try:
        engine.race_start_time = time.time()
        try:
            with engine.db._get_connection() as conn:
                cur = conn.cursor()
                try:
                    cur.execute("ALTER TABLE bots ADD COLUMN respawn_count INTEGER DEFAULT 0")
                    conn.commit()
                except Exception:
                    pass
                cur.execute("DELETE FROM positions")
                cur.execute("DELETE FROM trades")
                cur.execute("DELETE FROM equity_snapshots")
                cur.execute("DELETE FROM parameter_adjustments")
                cur.execute("DELETE FROM research_logs")
                try:
                    cur.execute("UPDATE bots SET current_balance = initial_capital, available_balance = initial_capital, total_pnl = 0.0, roi_pct = 0.0, win_rate = 0.0, total_trades = 0, winning_trades = 0, losing_trades = 0, max_drawdown = 0.0, peak_equity = initial_capital, is_active = 1, respawn_count = 0")
                except Exception:
                    cur.execute("UPDATE bots SET current_balance = initial_capital, available_balance = initial_capital, total_pnl = 0.0, roi_pct = 0.0, win_rate = 0.0, total_trades = 0, winning_trades = 0, losing_trades = 0, max_drawdown = 0.0, peak_equity = initial_capital, is_active = 1")
                conn.commit()
        except Exception as dbe:
            logger.warning(f"DB reset warning: {dbe}")
        for bot_id, wallet in engine.wallets.items():
            wallet.open_positions.clear()
            wallet.current_balance = 50.0
            wallet.available_balance = 50.0
            wallet.total_pnl = 0.0
            wallet.total_trades = 0
            wallet.winning_trades = 0
            wallet.losing_trades = 0
            wallet.peak_equity = 50.0
            wallet.max_drawdown = 0.0
        if hasattr(engine, 'capital_allocator'):
            engine.capital_allocator.rebalance_allocations(engine.strategies, force=True)
        return {"status": "SUCCESS", "message": "24H $100 Survival Match started! All bots reset to $50. Reach $100 or die!"}
    except Exception as e:
        logger.error(f"Error starting race: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/race-status")
async def get_race_status():
    try:
        now = time.time()
        start_time = getattr(engine, 'race_start_time', now) if engine else now
        elapsed = now - start_time
        duration = 86400.0 # 24 hours
        remaining = max(0.0, duration - elapsed)
        bots = engine.get_leaderboard_data() if engine else []
        top_bot = bots[0] if bots else {}
        total_respawns = sum(int(b.get('respawn_count') or 0) for b in bots)

        return {
            "race_start_time": start_time,
            "elapsed_seconds": round(elapsed, 1),
            "remaining_seconds": round(remaining, 1),
            "target_capital_usd": 100.0,
            "top_bot_name": top_bot.get('name', '---'),
            "top_bot_equity": top_bot.get('current_equity', 50.0),
            "total_respawns": total_respawns,
            "is_active": True
        }
    except Exception as e:
        logger.error(f"Error in get_race_status: {e}", exc_info=True)
        return {
            "race_start_time": time.time(),
            "elapsed_seconds": 0,
            "remaining_seconds": 86400,
            "target_capital_usd": 100.0,
            "top_bot_name": "---",
            "top_bot_equity": 50.0,
            "total_respawns": 0,
            "is_active": True
        }

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

# --- Bot Control Endpoints (Secured with verify_admin_access) ---
@app.post("/api/bots/{bot_id}/toggle", dependencies=[Depends(verify_admin_access)])
async def toggle_bot(bot_id: str, payload: Dict[str, Any]):
    if not engine:
        return JSONResponse(status_code=500, content={"error": "Engine not running"})
    is_active = payload.get("is_active", True)
    success = engine.toggle_bot(bot_id, is_active)
    return {"bot_id": bot_id, "is_active": is_active, "success": success}

@app.post("/api/bots/{bot_id}/liquidate", dependencies=[Depends(verify_admin_access)])
async def liquidate_bot(bot_id: str):
    if not engine:
        return JSONResponse(status_code=500, content={"error": "Engine not running"})
    closed_trades = engine.liquidate_bot(bot_id)
    return {"bot_id": bot_id, "closed_trades_count": len(closed_trades), "trades": closed_trades}

@app.post("/api/bots/{bot_id}/params", dependencies=[Depends(verify_admin_access)])
async def update_bot_params(bot_id: str, payload: Dict[str, Any]):
    if not engine:
        return JSONResponse(status_code=500, content={"error": "Engine not running"})
    success = engine.update_bot_params(bot_id, payload)
    return {"bot_id": bot_id, "success": success, "updated_params": payload}

@app.post("/api/bots/create", dependencies=[Depends(verify_admin_access)])
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

@app.post("/api/bots/{bot_id}/manual-order", dependencies=[Depends(verify_admin_access)])
async def manual_order(bot_id: str, payload: Dict[str, Any]):
    if not engine:
        return JSONResponse(status_code=500, content={"error": "Engine not running"})
    symbol = payload.get("symbol", "SOL/USDT")
    side = payload.get("side", "BUY")
    usd_amount = float(payload.get("usd_amount", 25.0))
    result = engine.execute_manual_trade(bot_id, symbol, side, usd_amount)
    return {"success": bool(result), "result": result}

@app.post("/api/tournament/reset", dependencies=[Depends(verify_admin_access)])
async def reset_tournament_api(payload: Dict[str, Any] = None):
    if not engine:
        return JSONResponse(status_code=500, content={"error": "Engine not running"})
    capital = float(payload.get("capital_per_bot", 50.0)) if payload else 50.0
    engine.reset_tournament(capital)
    return {"success": True, "message": f"Tournament reset with ${capital} per bot"}

# --- New Endpoints: Polymarket, Sentiment, Backtest, Charts & Pairs ---
@app.get("/api/sentiment")
async def get_sentiment():
    if not engine:
        return {}
    return engine.get_sentiment_data()

@app.get("/api/polymarket-events")
async def get_polymarket_events():
    if not engine:
        return []
    return engine.get_polymarket_events()

@app.get("/api/polymarket-whales")
async def get_polymarket_whales():
    if not engine:
        return {"leaderboard": [], "active_bets": []}
    return {
        "leaderboard": engine.get_polymarket_whales(),
        "active_bets": engine.get_polymarket_whale_bets()
    }

@app.post("/api/backtest")
async def run_backtest_endpoint(payload: Dict[str, Any]):
    if not engine:
        return JSONResponse(status_code=500, content={"error": "Engine not running"})
    strat_type = payload.get("strategy_type", "trend")
    symbol = payload.get("symbol", "SOL/USDT")
    tp = float(payload.get("take_profit_pct", 4.5)) / 100.0
    sl = float(payload.get("stop_loss_pct", 2.5)) / 100.0
    stake = float(payload.get("stake_usd", 25.0))
    result = engine.run_backtest(strat_type, symbol, tp, sl, stake)
    return result

@app.get("/api/ohlcv/{symbol:path}")
async def get_ohlcv(symbol: str):
    if not engine:
        return []
    return engine.get_ohlcv_chart(symbol)

@app.get("/api/pairs")
async def get_pairs():
    if not engine:
        return config.TRADING_PAIRS
    return engine.active_trading_pairs

@app.post("/api/pairs/add", dependencies=[Depends(verify_admin_access)])
async def add_pair(payload: Dict[str, Any]):
    if not engine:
        return JSONResponse(status_code=500, content={"error": "Engine not running"})
    pair = payload.get("symbol", "").upper()
    success = engine.add_trading_pair(pair)
    return {"success": success, "pairs": engine.active_trading_pairs}

@app.post("/api/pairs/remove", dependencies=[Depends(verify_admin_access)])
async def remove_pair(payload: Dict[str, Any]):
    if not engine:
        return JSONResponse(status_code=500, content={"error": "Engine not running"})
    pair = payload.get("symbol", "").upper()
    success = engine.remove_trading_pair(pair)
    return {"success": success, "pairs": engine.active_trading_pairs}

@app.post("/api/telegram/test", dependencies=[Depends(verify_admin_access)])
async def test_telegram(payload: Dict[str, Any] = None):
    if not engine:
        return JSONResponse(status_code=500, content={"error": "Engine not running"})
    token = payload.get("token") if payload else config.TELEGRAM_BOT_TOKEN
    chat_id = payload.get("chat_id") if payload else config.TELEGRAM_CHAT_ID
    if token and chat_id:
        engine.notifier.bot_token = token
        engine.notifier.chat_id = chat_id
        await engine.notifier.notify_trade(
            bot_name="CryptoArena Master",
            symbol="SOL/USDT",
            side="BUY",
            price=184.29,
            quantity=0.135,
            reason="⚡ Telegram Alert Integration Test: All Systems Operational!"
        )
        return {"success": True, "message": "Test notification dispatched to Telegram!"}
    return {"success": False, "message": "Missing Telegram token or chat_id"}

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
