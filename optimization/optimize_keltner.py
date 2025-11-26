# optimization/optimize_keltner_sol15m.py

from dataclasses import replace
from itertools import product
from multiprocessing import Pool, cpu_count
from typing import Iterable
import random

import pandas as pd

from config.settings import BACKTEST_CONFIG, RISK_CONFIG
from data.downloader import get_datos_cripto_cached
from backtesting.engine import Backtester
from strategies.keltner_breakout_strategy import (
    KeltnerBreakoutStrategy,
    KeltnerBreakoutStrategyConfig,
)

# DataFrame global compartido por los workers
_GLOBAL_DF: pd.DataFrame | None = None


def _init_worker(df: pd.DataFrame) -> None:
    """
    Inicializador de procesos: recibe el DataFrame y lo guarda
    en una variable global para no tener que pasarlo en cada tarea.
    """
    global _GLOBAL_DF
    _GLOBAL_DF = df


def _evaluate_config(args: tuple) -> dict | None:
    """
    Función que se ejecuta en paralelo en cada worker.
    Recibe una tupla con todos los parámetros de la estrategia
    y del backtest, construye la estrategia, la ejecuta,
    y devuelve un diccionario con resultados.

    Devuelve None si no cumple min_trades.
    """
    global _GLOBAL_DF
    df = _GLOBAL_DF
    if df is None:
        raise RuntimeError("GLOBAL DF no inicializado en worker.")

    (
        kc_window,
        kc_mult,
        atr_window,
        atr_min_percentile,
        use_trend_filter,
        trend_ema_window,
        allow_short,
        side_mode,
        sl_pct,
        tp_rr,
        min_trades,
    ) = args

    strat_cfg = KeltnerBreakoutStrategyConfig(
        kc_window=kc_window,
        kc_mult=kc_mult,
        atr_window=atr_window,
        atr_min_percentile=atr_min_percentile,
        use_trend_filter=use_trend_filter,
        trend_ema_window=trend_ema_window,
        allow_short=allow_short,
        side_mode=side_mode,
    )

    strategy = KeltnerBreakoutStrategy(config=strat_cfg)

    bt_cfg = replace(
        BACKTEST_CONFIG,
        sl_pct=sl_pct,
        tp_rr=tp_rr,
        atr_mult_sl=None,
        atr_mult_tp=None,
        allow_short=allow_short,
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
        "kc_window": kc_window,
        "kc_mult": kc_mult,
        "atr_window": atr_window,
        "atr_min_percentile": atr_min_percentile,
        "use_trend_filter": use_trend_filter,
        "trend_ema_window": trend_ema_window,
        "allow_short": allow_short,
        "side_mode": side_mode,
        "sl_pct": sl_pct,
        "tp_rr": tp_rr,
        "num_trades": result.num_trades,
        "total_return_pct": result.total_return_pct,
        "max_drawdown_pct": result.max_drawdown_pct,
        "winrate_pct": result.winrate_pct,
        "profit_factor": result.profit_factor,
    }


def _build_param_grid(
    kc_windows: Iterable[int],
    kc_mults: Iterable[float],
    atr_windows: Iterable[int],
    atr_min_percentiles: Iterable[float],
    use_trend_filters: Iterable[bool],
    trend_ema_windows: Iterable[int],
    allow_shorts: Iterable[bool],
    side_modes: Iterable[str],
    sl_pcts: Iterable[float],
    tp_rrs: Iterable[float],
    min_trades: int,
) -> list[tuple]:
    """
    Construye la lista de tuplas de parámetros que se pasará al Pool.
    """
    combos: list[tuple] = []

    for (
        kc_window,
        kc_mult,
        atr_window,
        atr_min_percentile,
        use_trend_filter,
        trend_ema_window,
        allow_short,
        side_mode,
        sl_pct,
        tp_rr,
    ) in product(
        kc_windows,
        kc_mults,
        atr_windows,
        atr_min_percentiles,
        use_trend_filters,
        trend_ema_windows,
        allow_shorts,
        side_modes,
        sl_pcts,
        tp_rrs,
    ):
        combos.append(
            (
                kc_window,
                kc_mult,
                atr_window,
                atr_min_percentile,
                use_trend_filter,
                trend_ema_window,
                allow_short,
                side_mode,
                sl_pct,
                tp_rr,
                min_trades,
            )
        )

    return combos


def main():
    symbol = "SOL/USDT"
    timeframe = "1m"
    limit = 5000

    print(f"Obteniendo datos de {symbol} en timeframe {timeframe}...")
    df = get_datos_cripto_cached(
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
        force_download=False,
    )
    print(f"Filas obtenidas: {len(df)}")

    # ==============================
    # Espacio de parámetros
    # ==============================

    kc_windows = [10, 20, 30]
    kc_mults = [1.0, 1.5, 2.0, 2.5]

    atr_windows = [10, 14, 20]
    atr_min_percentiles = [0.2, 0.3, 0.4]  # filtramos 20–40% de menor volatilidad

    use_trend_filters = [True, False]
    trend_ema_windows = [50, 100, 150, 200]

    allow_shorts = [True, False]
    side_modes = ["both", "long_only"]  # probamos operar ambas direcciones o solo largos

    sl_pcts = [0.005, 0.0075, 0.01]  # 0.5%, 0.75%, 1.0%
    tp_rrs = [1.5, 2.0, 2.5]

    # requerimos mínimo de trades para que tenga sentido
    min_trades = 30

    param_grid = _build_param_grid(
        kc_windows=kc_windows,
        kc_mults=kc_mults,
        atr_windows=atr_windows,
        atr_min_percentiles=atr_min_percentiles,
        use_trend_filters=use_trend_filters,
        trend_ema_windows=trend_ema_windows,
        allow_shorts=allow_shorts,
        side_modes=side_modes,
        sl_pcts=sl_pcts,
        tp_rrs=tp_rrs,
        min_trades=min_trades,
    )

    total_full = len(param_grid)
    print(f"Combinaciones totales generadas (antes de muestreo): {total_full}")

    # ==============================
    # Límite máximo de combinaciones
    # ==============================
    MAX_COMBOS = 2500  # ajustable

    if total_full > MAX_COMBOS:
        print(f"Reduciendo combinaciones mediante muestreo aleatorio a {MAX_COMBOS}...")
        random.seed(42)
        param_grid = random.sample(param_grid, MAX_COMBOS)

    total_combos = len(param_grid)
    print(f"Número de combinaciones a evaluar finalmente: {total_combos}")

    # Número de procesos: todos los cores menos 1
    n_procs = max(1, cpu_count() - 1)
    print(f"Usando {n_procs} procesos en paralelo.")

    rows: list[dict] = []

    # Para ver el progreso (~5% por log)
    progress_step = max(1, total_combos // 20)

    with Pool(
        processes=n_procs,
        initializer=_init_worker,
        initargs=(df,),
    ) as pool:
        for idx, res in enumerate(
            pool.imap_unordered(_evaluate_config, param_grid, chunksize=10),
            start=1,
        ):
            if res is not None:
                rows.append(res)

            if idx % progress_step == 0 or idx == total_combos:
                pct = idx / total_combos * 100.0
                print(
                    f"Progreso: {idx}/{total_combos} combinaciones "
                    f"({pct:.1f}%) - resultados válidos: {len(rows)}",
                    flush=True,
                )

    if not rows:
        print("Keltner Breakout SOL: sin resultados (revisa min_trades o rangos).")
        return

    df_results = pd.DataFrame(rows)

    # Ordenamos por retorno, PF y DD (DD ascendente)
    df_results = df_results.sort_values(
        by=["total_return_pct", "profit_factor", "max_drawdown_pct"],
        ascending=[False, False, True],
    ).reset_index(drop=True)

    top_n = 20
    print(f"\nTop {top_n} Keltner Breakout SOL/USDT {timeframe}:")
    print(df_results.head(top_n))

    out_path = f"opt_keltner_SOLUSDT_{timeframe}.csv"
    df_results.to_csv(out_path, index=False)
    print(f"\nResultados guardados en {out_path}")


if __name__ == "__main__":
    main()