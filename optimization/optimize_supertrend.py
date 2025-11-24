
from dataclasses import replace
from itertools import product
from multiprocessing import Pool, cpu_count
from typing import Iterable
import random
import pandas as pd

from config.settings import BACKTEST_CONFIG, RISK_CONFIG
from data.downloader import get_datos_cripto_cached
from backtesting.engine import Backtester
from strategies.supertrend_strategy import (
    SupertrendStrategy,
    SupertrendStrategyConfig,
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
        atr_period,
        atr_multiplier,
        use_adx_filter,
        adx_period,
        adx_threshold,
        sl_pct,
        tp_rr,
        min_trades,
    ) = args

    strat_cfg = SupertrendStrategyConfig(
        atr_period=atr_period,
        atr_multiplier=atr_multiplier,
        use_adx_filter=use_adx_filter,
        adx_period=adx_period,
        adx_threshold=adx_threshold,
    )

    strategy = SupertrendStrategy(config=strat_cfg)

    # Supertrend es "siempre en mercado" si no hay TP/SL o filtros.
    # Pero aquí usaremos TP/SL fijos para asegurar gestión de riesgo.
    # Allow short siempre True para Supertrend (sigue tendencia)
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
        "atr_period": atr_period,
        "atr_multiplier": atr_multiplier,
        "use_adx_filter": use_adx_filter,
        "adx_period": adx_period,
        "adx_threshold": adx_threshold,
        "sl_pct": sl_pct,
        "tp_rr": tp_rr,
        "num_trades": result.num_trades,
        "total_return_pct": result.total_return_pct,
        "max_drawdown_pct": result.max_drawdown_pct,
        "winrate_pct": result.winrate_pct,
        "profit_factor": result.profit_factor,
    }


def _build_param_grid(
    atr_periods: Iterable[int],
    atr_multipliers: Iterable[float],
    use_adx_filters: Iterable[bool],
    adx_periods: Iterable[int],
    adx_thresholds: Iterable[float],
    sl_pcts: Iterable[float],
    tp_rrs: Iterable[float],
    min_trades: int,
) -> list[tuple]:
    combos: list[tuple] = []

    for (
        atr_period,
        atr_multiplier,
        use_adx_filter,
        adx_period,
        adx_threshold,
        sl_pct,
        tp_rr,
    ) in product(
        atr_periods,
        atr_multipliers,
        use_adx_filters,
        adx_periods,
        adx_thresholds,
        sl_pcts,
        tp_rrs,
    ):
        # Si no se usa filtro ADX, adx_threshold es irrelevante (evitar duplicados)
        if not use_adx_filter and adx_threshold != adx_thresholds[0]:
            continue

        combos.append(
            (
                atr_period,
                atr_multiplier,
                use_adx_filter,
                adx_period,
                adx_threshold,
                sl_pct,
                tp_rr,
                min_trades,
            )
        )

    return combos


def main():
    symbol = "BTC/USDT"
    timeframe = "15m"
    limit = 50000 # Más datos para capturar tendencias largas

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
    atr_periods = [10, 14, 20]
    atr_multipliers = [2.0, 3.0, 4.0]
    
    use_adx_filters = [True, False]
    adx_periods = [14]
    adx_thresholds = [20.0, 25.0]

    sl_pcts = [0.01, 0.02] # 1%, 2%
    tp_rrs = [2.0, 3.0, 5.0] # Supertrend busca recorridos largos

    min_trades = 30

    param_grid = _build_param_grid(
        atr_periods=atr_periods,
        atr_multipliers=atr_multipliers,
        use_adx_filters=use_adx_filters,
        adx_periods=adx_periods,
        adx_thresholds=adx_thresholds,
        sl_pcts=sl_pcts,
        tp_rrs=tp_rrs,
        min_trades=min_trades,
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
        print("Supertrend: sin resultados.")
        return

    df_results = pd.DataFrame(rows)
    df_results = df_results.sort_values(
        by=["total_return_pct", "profit_factor", "max_drawdown_pct"],
        ascending=[False, False, True],
    ).reset_index(drop=True)

    top_n = 20
    print(f"\nTop {top_n} Supertrend {symbol} {timeframe}:")
    print(df_results.head(top_n))

    out_path = f"opt_supertrend_{symbol.replace('/', '')}_{timeframe}.csv"
    df_results.to_csv(out_path, index=False)
    print(f"\nResultados guardados en {out_path}")


if __name__ == "__main__":
    main()
