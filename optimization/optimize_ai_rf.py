
from dataclasses import replace
from itertools import product
from typing import Iterable
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd

from config.settings import BACKTEST_CONFIG, RISK_CONFIG
from data.downloader import get_datos_cripto_cached
from backtesting.engine import Backtester
from strategies.ai_strategy import (
    AIStrategy,
    AIStrategyConfig,
)
from optimization.base_optimizer import run_optimization, get_global_df, save_results


def _evaluate_config(args: tuple) -> dict | None:
    df = get_global_df()

    (
        lookback_window,
        n_estimators,
        training_size_pct,
        prediction_threshold,
        sl_pct,
        tp_rr,
        min_trades,
    ) = args

    strat_cfg = AIStrategyConfig(
        lookback_window=lookback_window,
        n_estimators=n_estimators,
        training_size_pct=training_size_pct,
        prediction_threshold=prediction_threshold,
    )

    strategy = AIStrategy(config=strat_cfg)

    bt_cfg = replace(
        BACKTEST_CONFIG,
        sl_pct=sl_pct,
        tp_rr=tp_rr,
        atr_mult_sl=None,
        atr_mult_tp=None,
        allow_short=True,
    )

    # Note: AI Strategy training can be slow.
    # We might want to limit the data size or optimize carefully.
    df_signals = strategy.generate_signals(df)

    backtester = Backtester(
        backtest_config=bt_cfg,
        risk_config=RISK_CONFIG,
    )
    result = backtester.run(df_signals)

    if result.num_trades < min_trades:
        return None

    return {
        "lookback_window": lookback_window,
        "n_estimators": n_estimators,
        "training_size_pct": training_size_pct,
        "prediction_threshold": prediction_threshold,
        "sl_pct": sl_pct,
        "tp_rr": tp_rr,
        "num_trades": result.num_trades,
        "total_return_pct": result.total_return_pct,
        "max_drawdown_pct": result.max_drawdown_pct,
        "winrate_pct": result.winrate_pct,
        "profit_factor": result.profit_factor,
    }


def _build_param_grid(
    lookback_windows: Iterable[int],
    n_estimators_list: Iterable[int],
    training_size_pcts: Iterable[float],
    prediction_thresholds: Iterable[float],
    sl_pcts: Iterable[float],
    tp_rrs: Iterable[float],
    min_trades: int,
) -> list[tuple]:
    combos: list[tuple] = []

    for (
        lookback_window,
        n_estimators,
        training_size_pct,
        prediction_threshold,
        sl_pct,
        tp_rr,
    ) in product(
        lookback_windows,
        n_estimators_list,
        training_size_pcts,
        prediction_thresholds,
        sl_pcts,
        tp_rrs,
    ):
        combos.append(
            (
                lookback_window,
                n_estimators,
                training_size_pct,
                prediction_threshold,
                sl_pct,
                tp_rr,
                min_trades,
            )
        )

    return combos


def main():
    # ========== CONFIGURATION ==========
    SYMBOL = "BTC/USDT"
    TIMEFRAME = "15m"
    LIMIT = 3000 # Smaller limit for AI to be faster
    MIN_TRADES = 10
    # ===================================

    print(f"Optimizing AI Random Forest for {SYMBOL} {TIMEFRAME}...")
    print(f"Obteniendo datos de {SYMBOL} en timeframe {TIMEFRAME}...")
    df = get_datos_cripto_cached(
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        limit=LIMIT,
        force_download=False,
    )
    print(f"Filas obtenidas: {len(df)}")

    # ==============================
    # Espacio de parámetros
    # ==============================
    lookback_windows = [14, 20]
    n_estimators_list = [50, 100]
    training_size_pcts = [0.6]
    prediction_thresholds = [0.55, 0.60]

    sl_pcts = [0.01, 0.02]
    tp_rrs = [1.5, 2.0]

    param_grid = _build_param_grid(
        lookback_windows=lookback_windows,
        n_estimators_list=n_estimators_list,
        training_size_pcts=training_size_pcts,
        prediction_thresholds=prediction_thresholds,
        sl_pcts=sl_pcts,
        tp_rrs=tp_rrs,
        min_trades=MIN_TRADES,
    )

    results = run_optimization(
        evaluator_func=_evaluate_config,
        param_grid=param_grid,
        df=df,
        max_combos=500, # Limit combos
    )

    save_results(
        results=results,
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        strategy_name="AI_RF",
    )


if __name__ == "__main__":
    main()
