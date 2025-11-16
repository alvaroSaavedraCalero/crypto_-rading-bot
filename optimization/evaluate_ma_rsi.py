# optimization/evaluate_ma_rsi.py

from dataclasses import replace

import pandas as pd

from backtesting.engine import Backtester
from config.settings import RunConfig
from optimization.ma_rsi_optimizer import run_ma_rsi_grid_search
from reporting.summary import print_backtest_summary
from strategies.ma_rsi_strategy import (
    MovingAverageRSIStrategy,
    MovingAverageRSIStrategyConfig,
)
from utils.risk import RiskManagementConfig


def train_test_split_time(df: pd.DataFrame, train_ratio: float = 0.7) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Divide el DataFrame en train/test manteniendo el orden temporal.
    train_ratio = 0.7 -> 70% train, 30% test.
    """
    df_sorted = df.sort_values("timestamp").reset_index(drop=True)
    n = len(df_sorted)
    split_idx = int(n * train_ratio)
    df_train = df_sorted.iloc[:split_idx].reset_index(drop=True)
    df_test = df_sorted.iloc[split_idx:].reset_index(drop=True)
    return df_train, df_test


def run_train_test_evaluation(
    df_full: pd.DataFrame,
    run_cfg: RunConfig,
    fast_windows: list[int],
    slow_windows: list[int],
    rsi_windows: list[int],
    sl_pcts: list[float],
    tp_rrs: list[float],
    train_ratio: float = 0.7,
    min_trades: int = 10,
) -> None:
    """
    Flujo completo:
        1) Split df en train/test.
        2) Grid search en train.
        3) Elegir mejor configuración.
        4) Evaluar esa configuración en test.
    """
    print(f"Dividiendo datos en train/test con ratio {train_ratio:.0%} ...")
    df_train, df_test = train_test_split_time(df_full, train_ratio=train_ratio)
    print(f"Train: {len(df_train)} velas, Test: {len(df_test)} velas")

    # --- 1) OPTIMIZACIÓN EN TRAIN ---
    print("\n=== OPTIMIZACIÓN EN TRAIN ===")
    df_results_train = run_ma_rsi_grid_search(
        df=df_train,
        fast_windows=fast_windows,
        slow_windows=slow_windows,
        rsi_windows=rsi_windows,
        sl_pcts=sl_pcts,
        tp_rrs=tp_rrs,
        base_backtest_config=run_cfg.backtest_config,
        base_risk_config=run_cfg.risk_config,
        min_trades=min_trades,
    )

    if df_results_train.empty:
        print("No se han encontrado configuraciones válidas en TRAIN (quizá min_trades es demasiado alto).")
        return

    print("\nTop 5 configuraciones en TRAIN:")
    print(df_results_train.head(5))

    # Elegimos la mejor (primera fila tras el sort)
    best_row = df_results_train.iloc[0]
    print("\nMejor configuración en TRAIN:")
    print(best_row)

    best_fast = int(best_row["fast_window"])
    best_slow = int(best_row["slow_window"])
    best_rsi = int(best_row["rsi_window"])
    best_sl = float(best_row["sl_pct"])
    best_tp_rr = float(best_row["tp_rr"])

    # --- 2) EVALUACIÓN EN TEST CON ESA CONFIGURACIÓN ---
    print("\n=== EVALUACIÓN EN TEST CON LA MEJOR CONFIGURACIÓN ===")

    # Config estrategia para test
    best_strategy_config = replace(
        run_cfg.strategy_config,
        fast_window=best_fast,
        slow_window=best_slow,
        rsi_window=best_rsi,
    )

    strategy = MovingAverageRSIStrategy(config=best_strategy_config)
    df_test_signals = strategy.generate_signals(df_test)

    # Config backtest para test
    best_backtest_config = replace(
        run_cfg.backtest_config,
        sl_pct=best_sl,
        tp_rr=best_tp_rr,
    )

    backtester_test = Backtester(
        backtest_config=best_backtest_config,
        risk_config=run_cfg.risk_config,
    )

    result_test = backtester_test.run(df_test_signals)

    print("\nResultados en TEST:")
    print_backtest_summary(result_test)

    print("\nResumen de comparación:")
    print(f"- Mejor config TRAIN: fast={best_fast}, slow={best_slow}, rsi={best_rsi}, "
          f"sl_pct={best_sl}, tp_rr={best_tp_rr}")
    print(f"- Velas TRAIN: {len(df_train)}, Velas TEST: {len(df_test)}")
    print(f"- Trades TEST: {result_test.num_trades}")
