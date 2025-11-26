
from dataclasses import replace
from itertools import product
from multiprocessing import Pool, cpu_count
from typing import Iterable
import random
import pandas as pd

from config.settings import BACKTEST_CONFIG, RISK_CONFIG
from data.downloader import get_datos_cripto_cached
from backtesting.engine import Backtester
from strategies.bollinger_mean_reversion import (
    BollingerMeanReversionStrategy,
    BollingerMeanReversionStrategyConfig,
)

# DataFrame global para los workers
_GLOBAL_DF: pd.DataFrame | None = None


def _init_worker(df: pd.DataFrame) -> None:
    global _GLOBAL_DF
    _GLOBAL_DF = df


def _evaluate_config(args: tuple) -> dict | None:
    global _GLOBAL_DF
    df = _GLOBAL_DF
    if df is None:
        raise RuntimeError("GLOBAL DF no inicializado en worker.")

    (
        bb_window,
        bb_std,
        rsi_window,
        rsi_oversold,
        rsi_overbought,
        sl_pct,
        tp_rr,
        min_trades,
    ) = args

    strat_cfg = BollingerMeanReversionStrategyConfig(
        bb_window=bb_window,
        bb_std=bb_std,
        rsi_window=rsi_window,
        rsi_oversold=rsi_oversold,
        rsi_overbought=rsi_overbought,
    )

    strategy = BollingerMeanReversionStrategy(config=strat_cfg)

    bt_cfg = replace(
        BACKTEST_CONFIG,
        sl_pct=sl_pct,
        tp_rr=tp_rr,
        atr_mult_sl=None,
        atr_mult_tp=None,
        allow_short=True,
    )

    df_signals = strategy.generate_signals(df)

    backtester = Backtester(
        backtest_config=bt_cfg,
        risk_config=RISK_CONFIG,
    )
    result = backtester.run(df_signals)

    if result.num_trades < min_trades:
        return None

    return {
        "bb_window": bb_window,
        "bb_std": bb_std,
        "rsi_window": rsi_window,
        "rsi_oversold": rsi_oversold,
        "rsi_overbought": rsi_overbought,
        "sl_pct": sl_pct,
        "tp_rr": tp_rr,
        "num_trades": result.num_trades,
        "total_return_pct": result.total_return_pct,
        "max_drawdown_pct": result.max_drawdown_pct,
        "winrate_pct": result.winrate_pct,
        "profit_factor": result.profit_factor,
    }


def _build_param_grid(
    bb_windows: Iterable[int],
    bb_stds: Iterable[float],
    rsi_windows: Iterable[int],
    rsi_oversolds: Iterable[float],
    rsi_overboughts: Iterable[float],
    sl_pcts: Iterable[float],
    tp_rrs: Iterable[float],
    min_trades: int,
) -> list[tuple]:
    combos: list[tuple] = []

    for (
        bb_window,
        bb_std,
        rsi_window,
        rsi_oversold,
        rsi_overbought,
        sl_pct,
        tp_rr,
    ) in product(
        bb_windows,
        bb_stds,
        rsi_windows,
        rsi_oversolds,
        rsi_overboughts,
        sl_pcts,
        tp_rrs,
    ):
        combos.append(
            (
                bb_window,
                bb_std,
                rsi_window,
                rsi_oversold,
                rsi_overbought,
                sl_pct,
                tp_rr,
                min_trades,
            )
        )

    return combos




def main():
    # ========== CONFIGURATION ==========
    SYMBOL = "BNB/USDT"
    TIMEFRAME = "1m"
    LIMIT = 10000
    MIN_TRADES = 30
    # ===================================

    print(f"Optimizing Bollinger Mean Reversion for {SYMBOL} {TIMEFRAME}...")
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
    bb_windows = [20, 30, 40]
    bb_stds = [2.0, 2.5]
    
    rsi_windows = [14]
    rsi_oversolds = [25.0, 30.0, 35.0]
    rsi_overboughts = [65.0, 70.0, 75.0]

    sl_pcts = [0.01, 0.015, 0.02] 
    tp_rrs = [1.0, 1.5, 2.0] 

    MIN_TRADES = 30

    param_grid = _build_param_grid(
        bb_windows=bb_windows,
        bb_stds=bb_stds,
        rsi_windows=rsi_windows,
        rsi_oversolds=rsi_oversolds,
        rsi_overboughts=rsi_overboughts,
        sl_pcts=sl_pcts,
        tp_rrs=tp_rrs,
        min_trades=MIN_TRADES,
    )

    total_full = len(param_grid)
    print(f"Combinaciones totales generadas: {total_full}")

    MAX_COMBOS = 2000
    if total_full > MAX_COMBOS:
        print(f"Reduciendo a {MAX_COMBOS}...")
        random.seed(42)
        param_grid = random.sample(param_grid, MAX_COMBOS)

    total_combos = len(param_grid)
    n_procs = max(1, cpu_count() - 1)
    print(f"Usando {n_procs} procesos.")

    rows: list[dict] = []
    progress_step = max(1, total_combos // 20)

    with Pool(processes=n_procs, initializer=_init_worker, initargs=(df,)) as pool:
        for idx, res in enumerate(
            pool.imap_unordered(_evaluate_config, param_grid, chunksize=10),
            start=1,
        ):
            if res is not None:
                rows.append(res)

            if idx % progress_step == 0 or idx == total_combos:
                pct = idx / total_combos * 100.0
                print(f"Progreso: {idx}/{total_combos} ({pct:.1f}%) - validos: {len(rows)}", flush=True)

    if not rows:
        print("Bollinger MR: sin resultados.")
        return

    df_results = pd.DataFrame(rows)
    df_results = df_results.sort_values(
        by=["total_return_pct", "profit_factor", "max_drawdown_pct"],
        ascending=[False, False, True],
    ).reset_index(drop=True)

    top_n = 20
    print(f"\nTop {top_n} Bollinger MR {SYMBOL} {TIMEFRAME}:")
    print(df_results.head(top_n))

    out_path = f"opt_bollinger_{SYMBOL.replace('/', '')}_{TIMEFRAME}.csv"
    df_results.to_csv(out_path, index=False)
    print(f"\nResultados guardados en {out_path}")


if __name__ == "__main__":
    main()
