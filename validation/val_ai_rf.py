
import sys
import os
import pandas as pd
from rich.console import Console
from rich.table import Table

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.settings import AI_RF_BTC15M_RUN, RISK_CONFIG
from data.downloader import get_datos_cripto_cached
from backtesting.engine import Backtester
from strategies.registry import create_strategy

console = Console()

def run_validation():
    run_config = AI_RF_BTC15M_RUN
    
    console.print(f"[bold cyan]Validating {run_config.name}...[/bold cyan]")
    
    # 1. Get Data
    df = get_datos_cripto_cached(
        symbol=run_config.symbol,
        timeframe=run_config.timeframe,
        limit=run_config.limit_candles,
        force_download=False
    )
    
    # 2. Run Strategy
    strategy = create_strategy(run_config.strategy_type, run_config.strategy_config)
    df_signals = strategy.generate_signals(df)
    
    # 3. Backtest
    backtester = Backtester(run_config.backtest_config, RISK_CONFIG)
    result = backtester.run(df_signals)
    
    # 4. Show Results
    table = Table(title=f"Validation Results: {run_config.name}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")
    
    table.add_row("Total Return %", f"{result.total_return_pct:.2f}%")
    table.add_row("Win Rate %", f"{result.winrate_pct:.2f}%")
    table.add_row("Max Drawdown %", f"{result.max_drawdown_pct:.2f}%")
    table.add_row("Profit Factor", f"{result.profit_factor:.2f}")
    table.add_row("Num Trades", str(result.num_trades))
    
    console.print(table)
    
    # Show last 5 trades
    if result.trades:
        console.print("\n[bold]Last 5 Trades:[/bold]")
        trades_table = Table(show_header=True)
        trades_table.add_column("Type")
        trades_table.add_column("Entry Time")
        trades_table.add_column("PnL %")
        
        for t in result.trades[-5:]:
            pnl_color = "green" if (t.pnl_pct or 0) > 0 else "red"
            trades_table.add_row(
                t.direction,
                str(t.entry_time),
                f"[{pnl_color}]{t.pnl_pct:.2f}%[/{pnl_color}]"
            )
        console.print(trades_table)

if __name__ == "__main__":
    run_validation()
