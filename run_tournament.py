"""
CryptoArena 50X - Main Tournament Runner
Launches the 5-Bot Championship Engine, Web Dashboard, and Terminal Telemetry.
"""
import sys
import os
import asyncio
import logging
from pathlib import Path

# Force UTF-8 on Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import uvicorn
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Ensure root dir is in path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import config
from core.database import ArenaDatabase
from core.engine import TournamentEngine
import web.server as web_server

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(config.DATA_DIR / "arena.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
# Reduce noisy logs
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("ccxt").setLevel(logging.WARNING)

console = Console()

def generate_terminal_table(engine: TournamentEngine) -> Table:
    table = Table(title="CryptoArena 50X - 7-Day $50 Championship Leaderboard", title_style="bold cyan", border_style="blue")
    table.add_column("Rank", justify="center", style="bold")
    table.add_column("Bot Name", style="bold white")
    table.add_column("Strategy", style="dim")
    table.add_column("Total Equity", justify="right", style="bold")
    table.add_column("PnL ($)", justify="right")
    table.add_column("ROI (%)", justify="right")
    table.add_column("Win Rate", justify="right")
    table.add_column("Trades (W/L)", justify="center")
    table.add_column("Max DD", justify="right")
    table.add_column("Open Trades", justify="center")

    leaderboard = engine.get_leaderboard_data()
    for idx, b in enumerate(leaderboard):
        rank = idx + 1
        rank_str = "#1 Leader" if rank == 1 else f"#{rank}"
        pnl_style = "bold green" if b['total_pnl'] >= 0 else "bold red"
        pnl_sign = "+" if b['total_pnl'] >= 0 else ""

        table.add_row(
            rank_str,
            b['name'],
            b['strategy_name'][:28],
            f"${b['current_equity']:.2f}",
            f"[{pnl_style}]{pnl_sign}${b['total_pnl']:.2f}[/{pnl_style}]",
            f"[{pnl_style}]{pnl_sign}{b['roi_pct']:.2f}%[/{pnl_style}]",
            f"{b['win_rate']:.1f}%",
            f"{b['winning_trades']}/{b['losing_trades']}",
            f"{b['max_drawdown']:.2f}%",
            str(b['open_positions_count'])
        )
    return table

async def start_web_server(engine: TournamentEngine):
    web_server.engine = engine
    uvicorn_config = uvicorn.Config(
        app=web_server.app,
        host=config.WEB_HOST,
        port=config.WEB_PORT,
        log_level="warning",
        access_log=False
    )
    server = uvicorn.Server(uvicorn_config)
    await server.serve()

async def main():
    console.print(Panel(
        f"[bold cyan]CryptoArena 50X - Multi-Bot Autonomous Championship Engine[/bold cyan]\n"
        f"[yellow]• Capital Allocation:[/yellow] $50.00 Paper Money per Bot ($250.00 Total Testbed)\n"
        f"[yellow]• Bots Active:[/yellow] 5 Unique AI Strategies (Trend, Mean-Reversion, Breakout, Grid, Smart Money)\n"
        f"[yellow]• Autonomous Research & Self-Improvement:[/yellow] 24/7 Live\n"
        f"[green]• Web Dashboard:[/green] http://{config.WEB_HOST}:{config.WEB_PORT}",
        border_style="cyan"
    ))

    db = ArenaDatabase(config.DB_PATH)
    engine = TournamentEngine(db)

    # Start Web Dashboard in background
    asyncio.create_task(start_web_server(engine))

    # Start Tournament Engine in background
    asyncio.create_task(engine.start())

    # Terminal Dashboard Live Loop
    try:
        while True:
            await asyncio.sleep(5)
            table = generate_terminal_table(engine)
            console.clear()
            console.print(table)
            console.print(f"\n[dim]Web Dashboard: http://{config.WEB_HOST}:{config.WEB_PORT} | Press Ctrl+C to stop[/dim]")
    except (KeyboardInterrupt, asyncio.CancelledError):
        console.print("\n[yellow]Shutting down CryptoArena...[/yellow]")
        engine.stop()

if __name__ == "__main__":
    asyncio.run(main())
