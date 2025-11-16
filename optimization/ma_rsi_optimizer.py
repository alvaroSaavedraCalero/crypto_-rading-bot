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
    rsi_windows: Iterable[int],
    sl_pcts: Iterable[float],
    tp_rrs: Iterable[float],
    base_backtest_config: BacktestConfig,
    base_risk_config: RiskManagementConfig,
    min_trades: int = 5,
    signal_modes: Iterable[str] = ("cross", "trend"),
    use_rsi_filter_options: Iterable[bool] = (False, True),
) -> pd.DataFrame:
    """
    Ejecuta una búsqueda por grid para la estrategia MA+RSI.
    """
    results_rows = []

    for fast, slow, rsi_win, sl_pct, tp_rr, signal_mode, use_rsi_filter in product(
        fast_windows, slow_windows, rsi_windows, sl_pcts, tp_rrs, signal_modes, use_rsi_filter_options
    ):
        # Evitar combinaciones poco lógicas
        if fast >= slow:
            continue

        # Configuración de estrategia
        strat_cfg = MovingAverageRSIStrategyConfig(
            fast_window=fast,
            slow_window=slow,
            rsi_window=rsi_win,
            rsi_overbought=70.0,
            rsi_oversold=30.0,
            use_rsi_filter=use_rsi_filter,
            signal_mode=signal_mode,
        )

        strategy = MovingAverageRSIStrategy(config=strat_cfg)

        # Generar señales
        df_signals = strategy.generate_signals(df)

        # Configuración de backtest adaptando SL/TP
        bt_cfg = replace(base_backtest_config, sl_pct=sl_pct, tp_rr=tp_rr)

        backtester = Backtester(
            backtest_config=bt_cfg,
            risk_config=base_risk_config,
        )

        result = backtester.run(df_signals)

        # Filtramos combinaciones con muy pocos trades
        if result.num_trades < min_trades:
            continue

        results_rows.append(
            {
                "fast_window": fast,
                "slow_window": slow,
                "rsi_window": rsi_win,
                "sl_pct": sl_pct,
                "tp_rr": tp_rr,
                "signal_mode": signal_mode,
                "use_rsi_filter": use_rsi_filter,
                "num_trades": result.num_trades,
                "total_return_pct": result.total_return_pct,
                "max_drawdown_pct": result.max_drawdown_pct,
                "winrate_pct": result.winrate_pct,
                "profit_factor": result.profit_factor,
            }
        )

    if not results_rows:
        return pd.DataFrame()

    df_results = pd.DataFrame(results_rows)

    df_results = df_results.sort_values(
        by=["total_return_pct", "profit_factor", "max_drawdown_pct"],
        ascending=[False, False, True],
    ).reset_index(drop=True)

    return df_results
