# optimization/donchian_optimizer.py

from itertools import product
from typing import Iterable

import pandas as pd

from backtesting.engine import Backtester, BacktestConfig
from strategies.donchian_breakout_strategy import (
    DonchianBreakoutStrategy,
    DonchianBreakoutStrategyConfig,
)
from utils.risk import RiskManagementConfig


def run_donchian_grid_search(
    df: pd.DataFrame,
    channel_windows: Iterable[int],
    allow_short_options: Iterable[bool],
    base_backtest_config: BacktestConfig,
    base_risk_config: RiskManagementConfig,
    min_trades: int = 1,  # MUY laxo a propósito
) -> pd.DataFrame:
    """
    Grid search para la estrategia Donchian_Breakout.
    """
    rows = []

    for win, allow_short in product(channel_windows, allow_short_options):
        cfg = DonchianBreakoutStrategyConfig(
            channel_window=win,
            allow_short=allow_short,
        )
        strat = DonchianBreakoutStrategy(config=cfg)

        df_signals = strat.generate_signals(df)

        backtester = Backtester(
            backtest_config=base_backtest_config,
            risk_config=base_risk_config,
        )
        result = backtester.run(df_signals)

        rows.append(
            {
                "channel_window": win,
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

    # Filtro por min_trades al final (para poder ver qué hay aunque sea 0–1 trades)
    df_res_filtered = df_res[df_res["num_trades"] >= min_trades].copy()

    if df_res_filtered.empty:
        # Si no hay ninguna combinación con min_trades o más, dejamos el DF completo
        # para que puedas ver al menos los num_trades de cada config.
        print("Donchian: ninguna combinación supera min_trades, mostrando todas las combinaciones.")
        return df_res.sort_values("num_trades", ascending=False).reset_index(drop=True)

    df_res_filtered = df_res_filtered.sort_values(
        by=["total_return_pct", "profit_factor", "max_drawdown_pct"],
        ascending=[False, False, True],
    ).reset_index(drop=True)

    return df_res_filtered
