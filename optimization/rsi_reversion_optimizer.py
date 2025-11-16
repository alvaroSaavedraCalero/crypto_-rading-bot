# optimization/rsi_reversion_optimizer.py

from itertools import product
from typing import Iterable

import pandas as pd

from backtesting.engine import Backtester, BacktestConfig
from strategies.rsi_reversion_strategy import (
    RSIReversionStrategy,
    RSIReversionStrategyConfig,
)
from utils.risk import RiskManagementConfig


def run_rsi_reversion_grid_search(
    df: pd.DataFrame,
    rsi_windows: Iterable[int],
    rsi_overbought_levels: Iterable[float],
    rsi_oversold_levels: Iterable[float],
    allow_short_options: Iterable[bool],
    base_backtest_config: BacktestConfig,
    base_risk_config: RiskManagementConfig,
    min_trades: int = 10,
) -> pd.DataFrame:
    """
    Grid search para la estrategia RSI_Reversion.

    Parámetros:
        df: DataFrame OHLCV original (sin señales).
        rsi_windows: ventanas de RSI.
        rsi_overbought_levels: niveles de sobrecompra.
        rsi_oversold_levels: niveles de sobreventa.
        allow_short_options: True/False.
    """
    rows = []

    for rsi_win, overbought, oversold, allow_short in product(
        rsi_windows, rsi_overbought_levels, rsi_oversold_levels, allow_short_options
    ):
        # Evitar configuraciones absurdas
        if oversold >= overbought:
            continue

        cfg = RSIReversionStrategyConfig(
            rsi_window=rsi_win,
            rsi_overbought=overbought,
            rsi_oversold=oversold,
            allow_short=allow_short,
        )
        strat = RSIReversionStrategy(config=cfg)

        df_signals = strat.generate_signals(df)

        backtester = Backtester(
            backtest_config=base_backtest_config,
            risk_config=base_risk_config,
        )
        result = backtester.run(df_signals)

        if result.num_trades < min_trades:
            continue

        rows.append(
            {
                "rsi_window": rsi_win,
                "rsi_overbought": overbought,
                "rsi_oversold": oversold,
                "allow_short": allow_short,
                "num_trades": result.num_trades,
                "total_return_pct": result.total_return_pct,
                "max_drawdown_pct": result.max_drawdown_pct,
                "winrate_pct": result.winrate_pct,
                "profit_factor": result.profit_factor,
            }
        )

    if not rows:
        return pd.DataFrame()

    df_res = pd.DataFrame(rows)
    df_res = df_res.sort_values(
        by=["total_return_pct", "profit_factor", "max_drawdown_pct"],
        ascending=[False, False, True],
    ).reset_index(drop=True)

    return df_res
