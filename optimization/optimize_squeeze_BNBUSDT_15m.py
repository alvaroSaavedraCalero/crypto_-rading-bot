# optimization/optimize_squeeze_BNBUSDT_15m.py

"""
Optimización de parámetros para SQUEEZE Momentum en BNB/USDT 15m.
"""

import itertools
from pathlib import Path

import pandas as pd

from backtesting.engine import BacktestConfig, Backtester
from config.settings import RISK_CONFIG
from data.downloader import get_datos_cripto_cached
from strategies.squeeze_momentum_strategy import (
    SqueezeMomentumStrategy,
    SqueezeMomentumConfig,
)

# Mercado base
SYMBOL = "BNB/USDT"
TIMEFRAME = "15m"
LIMIT = 5000

# Config de backtest para la optimización
BACKTEST_CFG = BacktestConfig(
    initial_capital=1000.0,
    sl_pct=0.005,      # 0.5% SL
    tp_rr=2.0,         # TP 1:2
    fee_pct=0.0005,    # 0.05% comisión
    allow_short=True,
)

# Espacio de búsqueda (ajustado para no tardar una eternidad)
BB_WINDOWS = [14, 20, 24]
BB_MULTS = [1.8, 2.0]
KC_MULTS = [1.5, 2.0]
MOM_WINDOWS = [10, 20]
ATR_WINDOWS = [14]          # podríamos ampliar a [10, 14, 20]
ATR_MIN_PCTS = [0.2, 0.3, 0.4]
MIN_SQUEEZE_BARS = [3, 5]

MIN_TRADES = 20
MAX_DD_LIMIT = -35.0  # descartar configs con drawdown peor que -35%


def run_single_config(df: pd.DataFrame, cfg: SqueezeMomentumConfig) -> dict | None:
    strategy = SqueezeMomentumStrategy(config=cfg)
    df_signals = strategy.generate_signals(df)

    bt = Backtester(
        backtest_config=BACKTEST_CFG,
        risk_config=RISK_CONFIG,
    )
    result = bt.run(df_signals)

    if result.num_trades < MIN_TRADES:
        return None
    if result.max_drawdown_pct < MAX_DD_LIMIT:
        return None

    return {
        "bb_window": cfg.bb_window,
        "bb_mult": cfg.bb_mult,
        "kc_window": cfg.kc_window,
        "kc_mult": cfg.kc_mult,
        "mom_window": cfg.mom_window,
        "atr_window": cfg.atr_window,
        "atr_min_percentile": cfg.atr_min_percentile,
        "min_squeeze_bars": cfg.min_squeeze_bars,
        "allow_short": cfg.allow_short,
        "num_trades": result.num_trades,
        "total_return_pct": result.total_return_pct,
        "max_drawdown_pct": result.max_drawdown_pct,
        "winrate_pct": result.winrate_pct,
        "profit_factor": result.profit_factor,
    }


def main():
    print(f"Obteniendo datos de {SYMBOL} en timeframe {TIMEFRAME}...")
    df = get_datos_cripto_cripto = get_datos_cripto_cached(
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        limit=LIMIT,
        force_download=False,
    )
    print(f"Filas obtenidas: {len(df)}")

    combos = list(
        itertools.product(
            BB_WINDOWS,
            BB_MULTS,
            KC_MULTS,
            MOM_WINDOWS,
            ATR_WINDOWS,
            ATR_MIN_PCTS,
            MIN_SQUEEZE_BARS,
        )
    )
    total = len(combos)
    print(f"Total combinaciones: {total}")

    results = []

    for idx, (bb_win, bb_mult, kc_mult, mom_win, atr_win, atr_pct, min_sq) in enumerate(combos, start=1):
        cfg = SqueezeMomentumConfig(
            bb_window=bb_win,
            bb_mult=bb_mult,
            kc_window=atr_win,      # uso mismo window para KC y ATR (estilo típico)
            kc_mult=kc_mult,
            mom_window=mom_win,
            atr_window=atr_win,
            atr_min_percentile=atr_pct,
            min_squeeze_bars=min_sq,
            allow_short=True,
        )

        row = run_single_config(df, cfg)
        if row is not None:
            results.append(row)

        if idx % 20 == 0 or idx == total:
            print(
                f"Progreso: {idx}/{total} ({idx / total * 100:.1f}%) - "
                f"resultados válidos: {len(results)}"
            )

    if not results:
        print("No se han encontrado configuraciones válidas. Revisa rangos o MIN_TRADES.")
        return

    df_res = pd.DataFrame(results)
    df_res = df_res.sort_values(
        by=["total_return_pct", "profit_factor"],
        ascending=[False, False],
    ).reset_index(drop=True)

    print("\nTop 20 SQUEEZE BNB/USDT 15m:")
    print(df_res.head(20))

    out_path = Path("optimization") / "opt_squeeze_BNBUSDT_15m.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df_res.to_csv(out_path, index=False)
    print(f"Resultados guardados en {out_path.resolve()}")


if __name__ == "__main__":
    main()