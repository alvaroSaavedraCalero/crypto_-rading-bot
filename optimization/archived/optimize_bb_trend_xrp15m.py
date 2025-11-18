# optimization/optimize_bb_trend_xrp15m.py

"""
Optimización de parámetros para BB_TREND en XRP/USDT 15m.

Estrategia: Bollinger + Tendencia (EMA larga).
"""

import itertools
from pathlib import Path

import pandas as pd

from backtesting.engine import BacktestConfig, Backtester
from config.settings import RISK_CONFIG
from data.downloader import get_datos_cripto_cached
from strategies.archived.bb_trend_strategy import BBTrendStrategy, BBTrendStrategyConfig


# Parámetros de mercado
SYMBOL = "XRP/USDT"
TIMEFRAME = "15m"
LIMIT = 5000

# BacktestConfig específico para esta optimización
BACKTEST_CFG = BacktestConfig(
    initial_capital=1000.0,
    sl_pct=0.005,       # 0.5% SL
    tp_rr=2.0,          # TP 1:2
    fee_pct=0.0005,     # 0.05% comisión
    allow_short=True,
)

# Espacio de búsqueda
BB_WINDOWS = [14, 20, 24]
BB_STDS = [1.8, 2.0, 2.2]
TREND_EMA_WINDOWS = [100, 150, 200]
REQUIRE_SLOPE_OPTIONS = [True, False]
SIGNAL_MODES = ["breakout", "pullback"]

MIN_TRADES = 20
MAX_DD_LIMIT = -35.0  # descartar configuraciones con DD peor que -35%


def run_single_config(df: pd.DataFrame, cfg: BBTrendStrategyConfig) -> dict | None:
    strategy = BBTrendStrategy(config=cfg)
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
        "bb_std": cfg.bb_std,
        "trend_ema_window": cfg.trend_ema_window,
        "require_slope": cfg.require_slope,
        "signal_mode": cfg.signal_mode,
        "num_trades": result.num_trades,
        "total_return_pct": result.total_return_pct,
        "max_drawdown_pct": result.max_drawdown_pct,
        "winrate_pct": result.winrate_pct,
        "profit_factor": result.profit_factor,
    }


def main():
    print(f"Obteniendo datos de {SYMBOL} en timeframe {TIMEFRAME}...")
    df = get_datos_cripto_cached(
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        limit=LIMIT,
        force_download=False,
    )
    print(f"Filas obtenidas: {len(df)}")

    results = []
    combos = list(
        itertools.product(
            BB_WINDOWS,
            BB_STDS,
            TREND_EMA_WINDOWS,
            REQUIRE_SLOPE_OPTIONS,
            SIGNAL_MODES,
        )
    )
    total = len(combos)
    print(f"Total combinaciones: {total}")

    for idx, (bb_win, bb_std, trend_win, req_slope, sig_mode) in enumerate(combos, start=1):
        cfg = BBTrendStrategyConfig(
            bb_window=bb_win,
            bb_std=bb_std,
            trend_ema_window=trend_win,
            require_slope=req_slope,
            allow_short=True,
            signal_mode=sig_mode,  # "breakout" o "pullback"
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

    print("\nTop 20 BB_TREND XRP/USDT 15m:")
    print(df_res.head(20))

    out_path = Path("optimization") / "opt_bb_trend_XRPUSDT_15m.csv"
    df_res.to_csv(out_path, index=False)
    print(f"Resultados guardados en {out_path.resolve()}")


if __name__ == "__main__":
    main()