
from dataclasses import replace
from itertools import product
from multiprocessing import Pool, cpu_count
from typing import Iterable
import random
import pandas as pd

from config.settings import BACKTEST_CONFIG, RISK_CONFIG
from data.downloader import get_datos_cripto_cached
from backtesting.engine import Backtester
from strategies.ict_strategy import (
    ICTStrategy,
    ICTStrategyConfig,
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
        kill_zone_start,
        kill_zone_end,
        swing_length,
        fvg_min_size_pct,
        allow_short,
        sl_pct,
        tp_rr,
        min_trades,
    ) = args

    strat_cfg = ICTStrategyConfig(
        kill_zone_start_hour=kill_zone_start,
        kill_zone_end_hour=kill_zone_end,
        swing_length=swing_length,
        fvg_min_size_pct=fvg_min_size_pct,
        allow_short=allow_short,
    )

    strategy = ICTStrategy(config=strat_cfg)

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
        "kill_zone_start": kill_zone_start,
        "kill_zone_end": kill_zone_end,
        "swing_length": swing_length,
        "fvg_min_size_pct": fvg_min_size_pct,
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
    kill_zones: Iterable[tuple[int, int]],
    swing_lengths: Iterable[int],
    fvg_min_sizes: Iterable[float],
    allow_shorts: Iterable[bool],
    sl_pcts: Iterable[float],
    tp_rrs: Iterable[float],
    min_trades: int,
) -> list[tuple]:
    combos: list[tuple] = []

    for (
        (kz_start, kz_end),
        swing_len,
        fvg_min,
        allow_short,
        sl_pct,
        tp_rr,
    ) in product(
        kill_zones,
        swing_lengths,
        fvg_min_sizes,
        allow_shorts,
        sl_pcts,
        tp_rrs,
    ):
        combos.append(
            (
                kz_start,
                kz_end,
                swing_len,
                fvg_min,
                allow_short,
                sl_pct,
                tp_rr,
                min_trades,
            )
        )

    return combos


def main():
    # ========== CONFIGURATION ==========
    SYMBOL = "BTC/USDT"
    TIMEFRAME = "1m"
    LIMIT = 10000
    MIN_TRADES = 30
    # ===================================

    print(f"Optimizing ICT Strategy for {SYMBOL} {TIMEFRAME}...")
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
    
    # Kill Zones (UTC)
    # London Open: ~07:00 - 10:00 UTC
    # NY Open: ~12:00 - 15:00 UTC
    # Asia: ~00:00 - 04:00 UTC
    kill_zones = [
        (7, 10),   # London
        (12, 15),  # NY
        (0, 23),   # All day (control)
    ]
    
    swing_lengths = [5, 10]
    fvg_min_sizes = [0.05, 0.1, 0.2]
    
    allow_shorts = [True, False]
    sl_pcts = [0.01, 0.015, 0.02]
    tp_rrs = [2.0, 3.0, 4.0] # ICT busca R:R alto

    # ==============================
    # Configuración de la optimización
    # ==============================
    MIN_TRADES_OPT = 5  # Mínimo de trades para considerar una configuración válida
    MAX_COMBOS_OPT = 2000 # Máximo de combinaciones a probar (para limitar el tiempo)

    param_grid = _build_param_grid(
        kill_zones=kill_zones,
        swing_lengths=swing_lengths,
        fvg_min_sizes=fvg_min_sizes,
        allow_shorts=allow_shorts,
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
        print("ICT: sin resultados.")
        return

    df_results = pd.DataFrame(rows)
    df_results = df_results.sort_values(
        by=["total_return_pct", "profit_factor", "max_drawdown_pct"],
        ascending=[False, False, True],
    ).reset_index(drop=True)

    top_n = 20
    print(f"\nTop {top_n} ICT {SYMBOL} {TIMEFRAME}:")
    print(df_results.head(top_n))

    safe_symbol = SYMBOL.replace("/", "")
    out_path = f"opt_ict_{safe_symbol}_{TIMEFRAME}.csv"
    df_results.to_csv(out_path, index=False)
    print(f"\nResultados guardados en {out_path}")


if __name__ == "__main__":
    main()
