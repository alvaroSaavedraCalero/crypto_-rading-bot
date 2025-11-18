# backtest_strategies.py

import pandas as pd

from config.settings import (
    OPTIMIZED_STRATEGIES,
    RISK_CONFIG,
)
from data.downloader import get_datos_cripto_cached
from backtesting.engine import Backtester
from reporting.summary import print_backtest_summary
from strategies.ma_rsi_strategy import MovingAverageRSIStrategy
from strategies.macd_adx_trend_strategy import MACDADXTrendStrategy
from strategies.keltner_breakout_strategy import KeltnerBreakoutStrategy
from strategies.archived.bb_trend_strategy import BBTrendStrategy
from strategies.squeeze_momentum_strategy import SqueezeMomentumStrategy


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

    # Instanciamos la estrategia según el tipo
    if run_cfg.strategy_type == "MA_RSI":
        strategy = MovingAverageRSIStrategy(config=run_cfg.strategy_config)
    elif run_cfg.strategy_type == "MACD_ADX":
        strategy = MACDADXTrendStrategy(config=run_cfg.strategy_config)
    elif run_cfg.strategy_type == "KELTNER":
        strategy = KeltnerBreakoutStrategy(config=run_cfg.strategy_config)
    elif run_cfg.strategy_type == "BB_TREND":
        strategy = BBTrendStrategy(config=run_cfg.strategy_config)
    elif run_cfg.strategy_type == "SQUEEZE":
        strategy = SqueezeMomentumStrategy(config=run_cfg.strategy_config)
    else:
        raise ValueError(f"Tipo de estrategia no soportado: {run_cfg.strategy_type}")

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