# optimization/ma_rsi_optimizer.py

from dataclasses import replace
from itertools import product
from typing import Iterable

import pandas as pd

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