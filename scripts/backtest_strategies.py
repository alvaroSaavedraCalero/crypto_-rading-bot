# backtest_strategies.py

import pandas as pd

from config.settings import (
    OPTIMIZED_STRATEGIES,
    RISK_CONFIG,
)
from data.downloader import get_datos_cripto_cached
from backtesting.engine import Backtester
from reporting.summary import print_backtest_summary
from strategies.registry import create_strategy


def run_single_strategy(run_cfg):
    """
    Ejecuta un backtest para una StrategyRunConfig definida en config.settings.OPTIMIZED_STRATEGIES.
    """
    print(f"\n=== Backtest estrategia: {run_cfg.name} ({run_cfg.strategy_type}) ===")
    print(
        f"Símbolo: {run_cfg.symbol}, timeframe: {run_cfg.timeframe}, "
        f"límite velas: {run_cfg.limit_candles}"
    )

    df = get_datos_cripto_cached(
        symbol=run_cfg.symbol,
        timeframe=run_cfg.timeframe,
        limit=run_cfg.limit_candles,
        force_download=False,
    )
    print(f"Filas obtenidas: {len(df)}")

    strategy = create_strategy(run_cfg.strategy_type, run_cfg.strategy_config)

    df_signals = strategy.generate_signals(df)

    backtester = Backtester(
        backtest_config=run_cfg.backtest_config,
        risk_config=RISK_CONFIG,
    )
    result = backtester.run(df_signals)

    print_backtest_summary(result)

    return {
        "strategy": run_cfg.name,
        "symbol": run_cfg.symbol,
        "timeframe": run_cfg.timeframe,
        "num_trades": result.num_trades,
        "total_return_pct": result.total_return_pct,
        "max_drawdown_pct": result.max_drawdown_pct,
        "winrate_pct": result.winrate_pct,
        "profit_factor": result.profit_factor,
    }


def main():
    rows = []

    for run_cfg in OPTIMIZED_STRATEGIES:
        row = run_single_strategy(run_cfg)
        rows.append(row)

    print("\n===== RESUMEN COMPARATIVO ESTRATEGIAS (OPTIMIZADAS) =====")
    df_summary = pd.DataFrame(rows)
    df_summary = df_summary.sort_values(
        by="total_return_pct",
        ascending=False,
    ).reset_index(drop=True)
    print(df_summary)


if __name__ == "__main__":
    main()
