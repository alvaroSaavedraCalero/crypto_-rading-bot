import sys
import time
import dataclasses
from datetime import datetime, timedelta, timezone
import pandas as pd
import questionary
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.layout import Layout
from rich.live import Live
from rich.text import Text

from config.settings import RISK_CONFIG
from data.downloader import get_datos_cripto_cached
from backtesting.engine import Backtester, BacktestConfig
from strategies.registry import STRATEGY_REGISTRY, create_strategy

console = Console()

def show_welcome():
    console.clear()
    title = Text("🚀 CRYPTO TRADING BOT 🚀", style="bold magenta", justify="center")
    subtitle = Text("Terminal Interface v1.1", style="dim white", justify="center")
    
    panel = Panel(
        Text.assemble(title, "\n", subtitle),
        border_style="cyan",
        padding=(1, 2)
    )
    console.print(panel)
    console.print("\n")

def get_strategy_config(strategy_type):
    """
    Returns the default configuration for the selected strategy.
    No user input required.
    """
    _, config_cls = STRATEGY_REGISTRY[strategy_type]
    
    # Instantiate with defaults
    # If config_cls has required fields without defaults, this might fail, 
    # but based on previous code, they seem to have defaults or we handle them.
    # We assume all config classes are dataclasses with defaults.
    try:
        return config_cls()
    except TypeError:
        # Fallback if some arguments are required (should not happen if designed well)
        console.print(f"[yellow]Warning: {strategy_type} config might need arguments. Using empty init.[/yellow]")
        return config_cls()

def run_backtest_flow():
    # 1. Select Strategies (Multi-select)
    strategy_types = questionary.checkbox(
        "Select Strategies to Run:",
        choices=list(STRATEGY_REGISTRY.keys())
    ).ask()
    
    if not strategy_types: 
        console.print("[yellow]No strategies selected.[/yellow]")
        return

    # 2. Market Data
    symbol = questionary.text("Symbol:", default="BTC/USDT").ask()
    timeframe = questionary.select(
        "Timeframe:",
        choices=["1m", "5m", "15m", "1h", "4h", "1d"]
    ).ask()
    
    days_back = int(questionary.text("Days to backtest:", default="30").ask())
    
    # 3. Account
    initial_capital = float(questionary.text("Initial Capital:", default="10000").ask())
    
    # --- Execution ---
    console.print("\n")
    
    results = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        task_dl = progress.add_task(description="Downloading data...", total=None)
        
        end_dt = datetime.now(timezone.utc)
        start_dt = end_dt - timedelta(days=days_back)
        
        # Calculate limit based on timeframe and days_back
        # Approximate candles per day
        candles_per_day = {
            "1m": 1440,
            "5m": 288,
            "15m": 96,
            "1h": 24,
            "4h": 6,
            "1d": 1,
        }
        
        daily_candles = candles_per_day.get(timeframe, 24) # Default to 24 if unknown
        # Add buffer
        limit = int(days_back * daily_candles * 1.1) 
        
        # Ensure minimum limit for AI strategies (e.g. 50k if possible, or just large enough)
        # But we don't want to download too much if not needed.
        # If user asks for 30 days of 1m data: 30 * 1440 = 43200 candles.
        # If user asks for 30000 days... that's too much.
        
        # Max limit safety
        limit = min(limit, 200000) # Cap at 200k to avoid issues
 
        
        try:
            df = get_datos_cripto_cached(
                symbol=symbol,
                timeframe=timeframe,
                limit=limit,
                force_download=False
            )
            
            if df['timestamp'].dt.tz is None:
                df['timestamp'] = df['timestamp'].dt.tz_localize('UTC')
                
            mask = (df['timestamp'] >= start_dt) & (df['timestamp'] <= end_dt)
            df_filtered = df.loc[mask].copy().reset_index(drop=True)
            
            if df_filtered.empty:
                console.print("[bold red]No data found for the selected range.[/bold red]")
                return

            progress.update(task_dl, completed=100, visible=False)
            
            # Loop through strategies
            task_strat = progress.add_task(description="Running Strategies...", total=len(strategy_types))
            
            for strat_type in strategy_types:
                progress.update(task_strat, description=f"Running {strat_type}...")
                
                # Config with defaults
                strategy_config = get_strategy_config(strat_type)
                strategy = create_strategy(strat_type, strategy_config)
                
                df_signals = strategy.generate_signals(df_filtered)
                
                bt_config = BacktestConfig(
                    initial_capital=initial_capital,
                    fee_pct=0.0005,
                    sl_pct=0.02,
                    tp_rr=2.0
                )
                
                backtester = Backtester(bt_config, RISK_CONFIG)
                res = backtester.run(df_signals)
                
                results.append({
                    "strategy": strat_type,
                    "result": res
                })
                progress.advance(task_strat)
                
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            return

    # --- Results ---
    show_comparison_results(results, symbol, timeframe)

def show_comparison_results(results, symbol, timeframe):
    console.print(f"\n[bold green]=== Backtest Summary: {symbol} {timeframe} ===[/bold green]\n")
    
    # Summary Table
    table = Table(title="Strategy Comparison", show_header=True, header_style="bold magenta")
    table.add_column("Strategy", style="cyan")
    table.add_column("Return %", style="white")
    table.add_column("Win Rate %", style="white")
    table.add_column("Max DD %", style="white")
    table.add_column("Profit Factor", style="white")
    table.add_column("Trades", style="white")
    
    summary_data = []
    
    for item in results:
        res = item["result"]
        strat = item["strategy"]
        
        # Colorize Return
        ret_color = "green" if res.total_return_pct > 0 else "red"
        
        table.add_row(
            strat,
            f"[{ret_color}]{res.total_return_pct:.2f}%[/{ret_color}]",
            f"{res.winrate_pct:.2f}%",
            f"{res.max_drawdown_pct:.2f}%",
            f"{res.profit_factor:.2f}",
            str(res.num_trades)
        )
        
        summary_data.append({
            "Strategy": strat,
            "Return %": res.total_return_pct,
            "Win Rate %": res.winrate_pct,
            "Max DD %": res.max_drawdown_pct,
            "Profit Factor": res.profit_factor,
            "Trades": res.num_trades
        })
        
    console.print(table)
    console.print("\n")
    
    # Options
    while True:
        choice = questionary.select(
            "Results Menu:",
            choices=[
                "View Strategy Details",
                "Export Results to CSV",
                "Back to Main Menu"
            ]
        ).ask()
        
        if choice == "Back to Main Menu":
            break
            
        elif choice == "Export Results to CSV":
            filename = f"backtest_results_{symbol.replace('/','-')}_{timeframe}_{int(time.time())}.csv"
            pd.DataFrame(summary_data).to_csv(filename, index=False)
            console.print(f"[green]Saved summary to {filename}[/green]")
            
        elif choice == "View Strategy Details":
            strat_choice = questionary.select(
                "Select Strategy to view:",
                choices=[r["strategy"] for r in results]
            ).ask()
            
            # Find result
            target_res = next(r["result"] for r in results if r["strategy"] == strat_choice)
            show_single_strategy_details(target_res, strat_choice)

def show_single_strategy_details(result, strategy_type):
    console.print(f"\n[bold cyan]--- Details for {strategy_type} ---[/bold cyan]")
    
    if result.trades:
        console.print(f"[bold]All Trades ({len(result.trades)}):[/bold]")
        trades_table = Table(show_header=True, header_style="bold yellow")
        trades_table.add_column("Type")
        trades_table.add_column("Entry Time")
        trades_table.add_column("Entry Price")
        trades_table.add_column("Exit Price")
        trades_table.add_column("PnL %")
        
        for t in result.trades:
            pnl_color = "green" if (t.pnl or 0) > 0 else "red"
            type_color = "green" if t.direction == "long" else "red"
            
            trades_table.add_row(
                f"[{type_color}]{t.direction}[/{type_color}]",
                str(t.entry_time),
                f"{t.entry_price:.2f}",
                f"{t.exit_price:.2f}" if t.exit_price else "-",
                f"[{pnl_color}]{t.pnl_pct:.2f}%[/{pnl_color}]" if t.pnl_pct else "-"
            )
        console.print(trades_table)
    else:
        console.print("[yellow]No trades executed.[/yellow]")
    
    console.print("\n")
    questionary.press_any_key_to_continue().ask()

def main():
    while True:
        show_welcome()
        choice = questionary.select(
            "Main Menu",
            choices=[
                "Run Backtest",
                "Exit"
            ]
        ).ask()
        
        if choice == "Run Backtest":
            run_backtest_flow()
        elif choice == "Exit":
            console.print("[bold cyan]Goodbye![/bold cyan]")
            sys.exit()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold red]Interrupted by user.[/bold red]")
        sys.exit()
