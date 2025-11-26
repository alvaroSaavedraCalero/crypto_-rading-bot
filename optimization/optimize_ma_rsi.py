# optimization/optimize_ma_rsi.py

from dataclasses import replace
from itertools import product
from typing import Iterable

import pandas as pd

from config.settings import BACKTEST_CONFIG, RISK_CONFIG
from data.downloader import get_datos_cripto_cached
from backtesting.engine import Backtester, BacktestConfig
from strategies.ma_rsi_strategy import (
    MovingAverageRSIStrategy,
    MovingAverageRSIStrategyConfig,
)
from utils.risk import RiskManagementConfig


def run_ma_rsi_grid_search(
    df: pd.DataFrame,
    fast_windows: Iterable[int],
    slow_windows: Iterable[int],
    signal_modes: Iterable[str],
    use_trend_filter_options: Iterable[bool],
    trend_ma_windows: Iterable[int],
    sl_pcts: Iterable[float],
    tp_rrs: Iterable[float],
    base_backtest_config: BacktestConfig,
    base_risk_config: RiskManagementConfig,
    min_trades: int = 20,
) -> pd.DataFrame:
    """
    Grid search para la estrategia MA_RSI con filtro de tendencia opcional.

    df: DataFrame OHLCV con columnas: timestamp, open, high, low, close, volume
    """
    rows: list[dict] = []

    for fast, slow, signal_mode, use_trend_filter, trend_win, sl_pct, tp_rr in product(
        fast_windows,
        slow_windows,
        signal_modes,
        use_trend_filter_options,
        trend_ma_windows,
        sl_pcts,
        tp_rrs,
    ):
        # descartamos combinaciones poco lógicas
        if fast >= slow:
            continue

        # Config estrategia
        strat_cfg = MovingAverageRSIStrategyConfig(
            fast_window=fast,
            slow_window=slow,
            rsi_window=10,          # puedes parametrizarlo después si quieres
            rsi_overbought=70.0,
            rsi_oversold=30.0,
            use_rsi_filter=False,   # de momento desactivado
            signal_mode=signal_mode,
            use_trend_filter=use_trend_filter,
            trend_ma_window=trend_win,
        )
        strategy = MovingAverageRSIStrategy(config=strat_cfg)

        df_signals = strategy.generate_signals(df)

        # Config backtest (adaptamos sl_pct y tp_rr)
        bt_cfg = replace(
            base_backtest_config,
            sl_pct=sl_pct,
            tp_rr=tp_rr,
            atr_mult_sl=None,
            atr_mult_tp=None,
        )

        backtester = Backtester(
            backtest_config=bt_cfg,
            risk_config=base_risk_config,
        )

        result = backtester.run(df_signals)

        if result.num_trades < min_trades:
            continue

        rows.append(
            {
                "fast_window": fast,
                "slow_window": slow,
                "signal_mode": signal_mode,
                "use_trend_filter": use_trend_filter,
                "trend_ma_window": trend_win,
                "sl_pct": sl_pct,
                "tp_rr": tp_rr,
                "num_trades": result.num_trades,
                "total_return_pct": result.total_return_pct,
                "max_drawdown_pct": result.max_drawdown_pct,
                "winrate_pct": result.winrate_pct,
                "profit_factor": result.profit_factor,
            }
        )

    if not rows:
        return pd.DataFrame()

    df_results = pd.DataFrame(rows)

    # Orden: más retorno, mejor PF, menor drawdown
    df_results = df_results.sort_values(
        by=["total_return_pct", "profit_factor", "max_drawdown_pct"],
        ascending=[False, False, True],
    ).reset_index(drop=True)

    return df_results


def main():
    # ========== CONFIGURATION ==========
    SYMBOL = "BTC/USDT"
    TIMEFRAME = "1m"
    LIMIT = 10000
    MIN_TRADES = 20
    # ===================================

    print(f"Optimizing MA_RSI Strategy for {SYMBOL} {TIMEFRAME}...")
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
    fast_windows = [5, 10, 20]
    slow_windows = [50, 100, 200]
    signal_modes = ["cross", "both"]
    use_trend_filter_options = [True, False]
    trend_ma_windows = [200]
    sl_pcts = [0.01, 0.015, 0.02]
    tp_rrs = [1.5, 2.0, 2.5]

    df_results = run_ma_rsi_grid_search(
        df=df,
        fast_windows=fast_windows,
        slow_windows=slow_windows,
        signal_modes=signal_modes,
        use_trend_filter_options=use_trend_filter_options,
        trend_ma_windows=trend_ma_windows,
        sl_pcts=sl_pcts,
        tp_rrs=tp_rrs,
        base_backtest_config=BACKTEST_CONFIG,
        base_risk_config=RISK_CONFIG,
        min_trades=MIN_TRADES,
    )

    if df_results.empty:
        print("MA_RSI: sin resultados.")
        return

    top_n = 20
    print(f"\nTop {top_n} MA_RSI {SYMBOL} {TIMEFRAME}:")
    print(df_results.head(top_n))

    out_path = f"opt_ma_rsi_{SYMBOL.replace('/', '')}_{TIMEFRAME}.csv"
    df_results.to_csv(out_path, index=False)
    print(f"\nResultados guardados en {out_path}")


if __name__ == "__main__":
    main()