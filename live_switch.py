"""
Live Switch Exporter
Audits the 7-day tournament results, selects the #1 winning bot strategy,
and generates a production-ready live trading configuration for real $50 capital.
"""
import sys
import os
import json
import argparse
from pathlib import Path

# Force UTF-8 on Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Ensure root dir in path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import config
from core.database import ArenaDatabase

console = Console()

def audit_and_export():
    db = ArenaDatabase(config.DB_PATH)
    bots = db.get_all_bots()

    if not bots:
        console.print("[red]No tournament bot data found. Run the tournament first via python run_tournament.py[/red]")
        return

    table = Table(title="[TOURNAMENT CHAMPIONSHIP AUDIT RESULTS]", title_style="bold yellow")
    table.add_column("Rank", justify="center")
    table.add_column("Bot Name", style="bold")
    table.add_column("Strategy", style="dim")
    table.add_column("Final Equity", justify="right")
    table.add_column("Total PnL", justify="right")
    table.add_column("ROI (%)", justify="right")
    table.add_column("Win Rate", justify="right")
    table.add_column("Trades (W/L)", justify="center")
    table.add_column("Max DD", justify="right")

    for idx, b in enumerate(bots):
        rank = idx + 1
        rank_str = "[WINNER #1]" if rank == 1 else f"#{rank}"
        pnl_style = "green" if b['total_pnl'] >= 0 else "red"
        pnl_sign = "+" if b['total_pnl'] >= 0 else ""

        table.add_row(
            rank_str,
            b['name'],
            b['strategy_name'],
            f"${b['current_balance']:.2f}",
            f"[{pnl_style}]{pnl_sign}${b['total_pnl']:.2f}[/{pnl_style}]",
            f"[{pnl_style}]{pnl_sign}{b['roi_pct']:.2f}%[/{pnl_style}]",
            f"{b['win_rate']:.1f}%",
            f"{b['winning_trades']}/{b['losing_trades']}",
            f"{b['max_drawdown']:.2f}%"
        )

    console.print(table)

    winner = bots[0]
    console.print(Panel(
        f"[bold yellow]OFFICIAL TOURNAMENT WINNER: {winner['name']} ({winner['strategy_name']})[/bold yellow]\n"
        f"• Final Equity: ${winner['current_balance']:.2f} (ROI: {winner['roi_pct']:+.2f}%)\n"
        f"• Win Rate: {winner['win_rate']:.1f}% ({winner['winning_trades']} Wins / {winner['losing_trades']} Losses)\n"
        f"• Max Drawdown: {winner['max_drawdown']:.2f}%\n\n"
        f"[bold cyan]Ready for Live $50 Deployment with Winning Strategy![/bold cyan]",
        border_style="yellow"
    ))

    # Export configuration file
    export_config = {
        "champion_bot_id": winner['bot_id'],
        "champion_name": winner['name'],
        "strategy_name": winner['strategy_name'],
        "initial_capital_usd": 50.0,
        "max_concurrent_trades": 2,
        "stake_per_trade_usd": 25.0,
        "trading_pairs": config.TRADING_PAIRS,
        "status": "READY_FOR_REAL_TRADING"
    }

    export_path = config.DATA_DIR / "champion_strategy_config.json"
    with open(export_path, "w") as f:
        json.dump(export_config, f, indent=2)

    console.print(f"[green]✔ Exported champion configuration to:[/green] [dim]{export_path}[/dim]")

if __name__ == "__main__":
    audit_and_export()
