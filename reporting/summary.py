# reporting/summary.py

from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import pandas as pd

from backtesting.engine import BacktestResult


def print_backtest_summary(result: BacktestResult) -> None:
    """
    Muestra por consola un resumen legible del backtest.
    """
    print("\n===== RESUMEN BACKTEST =====")
    print(f"Número de trades: {result.num_trades}")
    print(f"Retorno total: {result.total_return_pct:.2f} %")
    print(f"Max drawdown: {result.max_drawdown_pct:.2f} %")
    print(f"Winrate: {result.winrate_pct:.2f} %")
    print(f"Profit factor: {result.profit_factor:.2f}")


def trades_to_dataframe(result: BacktestResult) -> pd.DataFrame:
    """
    Convierte la lista de Trade en un DataFrame para inspección/export.
    """
    rows = []
    for t in result.trades:
        rows.append(
            {
                "entry_time": t.entry_time,
                "exit_time": t.exit_time,
                "direction": t.direction,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "size": t.size,
                "stop_price": t.stop_price,
                "tp_price": t.tp_price,
                "pnl": t.pnl,
                "pnl_pct": t.pnl_pct,
            }
        )

    df_trades = pd.DataFrame(rows)
    return df_trades


def save_trades_to_csv(
    result: BacktestResult,
    file_path: str | Path = "backtest_trades.csv",
) -> Path:
    """
    Guarda los trades en un CSV para análisis posterior.
    """
    file_path = Path(file_path)
    df_trades = trades_to_dataframe(result)

    df_trades.to_csv(file_path, index=False)
    print(f"Trades guardados en {file_path}")

    return file_path


def plot_equity_curve(
    result: BacktestResult,
    title: str = "Equity curve",
    show: bool = True,
) -> None:
    """
    Dibuja la equity curve del backtest.
    """
    if result.equity_curve is None or result.equity_curve.empty:
        print("No hay equity curve disponible para graficar.")
        return

    plt.figure(figsize=(10, 4))
    result.equity_curve.plot()
    plt.title(title)
    plt.xlabel("Tiempo")
    plt.ylabel("Capital")
    plt.grid(True)
    if show:
        plt.tight_layout()
        plt.show()
