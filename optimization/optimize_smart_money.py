
from dataclasses import replace
from itertools import product
from multiprocessing import Pool, cpu_count
from typing import Iterable
import random
import pandas as pd

from config.settings import BACKTEST_CONFIG, RISK_CONFIG
from data.downloader import get_datos_cripto_cached
from backtesting.engine import Backtester
from strategies.smart_money_strategy import (
    SmartMoneyStrategy,
    SmartMoneyStrategyConfig,
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
        fvg_min_size_pct,
        trend_ema_window,
        allow_short,
        sl_pct,
        tp_rr,
        min_trades,
    ) = args

    strat_cfg = SmartMoneyStrategyConfig(
        fvg_min_size_pct=fvg_min_size_pct,
        trend_ema_window=trend_ema_window,
        allow_short=allow_short,
        use_fvg=True,
        use_ob=False, # Por ahora solo FVG para simplificar optimización inicial
    )

    strategy = SmartMoneyStrategy(config=strat_cfg)

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
        "fvg_min_size_pct": fvg_min_size_pct,
        "trend_ema_window": trend_ema_window,
        "allow_short": allow_short,
        "sl_pct": sl_pct,
        "tp_rr": tp_rr,
        "num_trades": result.num_trades,
        "total_return_pct": result.total_return_pct,
        "max_drawdown_pct": result.max_drawdown_pct,
        "winrate_pct": result.winrate_pct,
        "profit_factor": result.profit_factor,
    }


def _build_param_grid(
    fvg_min_sizes: Iterable[float],
    trend_ema_windows: Iterable[int],
    allow_shorts: Iterable[bool],
    sl_pcts: Iterable[float],
    tp_rrs: Iterable[float],
    min_trades: int,
) -> list[tuple]:
    combos: list[tuple] = []

    for (
        fvg_min_size,
        trend_ema,
        allow_short,
        sl_pct,
        tp_rr,
    ) in product(
        fvg_min_sizes,
        trend_ema_windows,
        allow_shorts,
        sl_pcts,
        tp_rrs,
    ):
        combos.append(
            (
                fvg_min_size,
                trend_ema,
                allow_short,
                sl_pct,
                tp_rr,
                min_trades,
            )
        )

    return combos


def main():
    symbol = "BTC/USDT"
    timeframe = "1m"
    limit = 10000

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
    fvg_min_sizes = [0.05, 0.1, 0.2, 0.3]
    trend_ema_windows = [100, 200]
    allow_shorts = [True, False]
    sl_pcts = [0.01, 0.015, 0.02]
    tp_rrs = [1.5, 2.0, 3.0]

    min_trades = 10 # SMC suele tener menos trades

    param_grid = _build_param_grid(
        fvg_min_sizes=fvg_min_sizes,
        trend_ema_windows=trend_ema_windows,
        allow_shorts=allow_shorts,
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
        print("Smart Money: sin resultados.")
        return

    df_results = pd.DataFrame(rows)
    df_results = df_results.sort_values(
        by=["total_return_pct", "profit_factor", "max_drawdown_pct"],
        ascending=[False, False, True],
    ).reset_index(drop=True)

    top_n = 20
    print(f"\nTop {top_n} Smart Money {symbol} {timeframe}:")
    print(df_results.head(top_n))

    safe_symbol = symbol.replace("/", "")
    out_path = f"opt_smart_money_{safe_symbol}_{timeframe}.csv"
    df_results.to_csv(out_path, index=False)
    print(f"\nResultados guardados en {out_path}")


if __name__ == "__main__":
    main()
