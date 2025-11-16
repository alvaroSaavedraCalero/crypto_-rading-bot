# backtest_strategies.py

import pandas as pd
from dataclasses import replace

from config.settings import DEFAULT_RUN_CONFIG
from data.downloader import get_datos_cripto_cached
from backtesting.engine import Backtester, BacktestConfig
from reporting.summary import print_backtest_summary
from strategies.ma_rsi_strategy import (
    MovingAverageRSIStrategy,
    MovingAverageRSIStrategyConfig,
)
from strategies.rsi_reversion_strategy import (
    RSIReversionStrategy,
    RSIReversionStrategyConfig,
)
from strategies.donchian_breakout_strategy import (
    DonchianBreakoutStrategy,
    DonchianBreakoutStrategyConfig,
)
from utils.atr import add_atr


def main():
    run_cfg = DEFAULT_RUN_CONFIG

    symbol = run_cfg.symbol
    timeframe = run_cfg.timeframe
    limit = run_cfg.limit_candles

    print(f"Obteniendo datos de {symbol} en timeframe {timeframe}...")
    df = get_datos_cripto_cached(
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
        force_download=False,
    )
    print(f"Filas obtenidas: {len(df)}")

    # Añadimos ATR una vez (para las estrategias que lo necesiten)
    atr_window_default = 14
    df_with_atr = add_atr(df, window=atr_window_default)

    # ============================
    # 1) CONFIGS OPTIMIZADOS
    # ============================

    # --- MA_RSI: parámetros óptimos encontrados ---
    ma_rsi_config = MovingAverageRSIStrategyConfig(
        fast_window=10,
        slow_window=25,
        rsi_window=10,
        rsi_overbought=70.0,
        rsi_oversold=30.0,
        use_rsi_filter=False,
        signal_mode="cross",
        use_trend_filter=True,
        trend_ma_window=200,
    )

    # IMPORTANTE: aquí usamos directamente BACKTEST_CONFIG del settings
    # que ya tiene sl_pct=0.005 y tp_rr=3.0
    ma_rsi_bt_config = run_cfg.backtest_config

    # --- RSI_Reversion: sigue con ATR ---
    rsi_rev_config = RSIReversionStrategyConfig(
        rsi_window=21,
        rsi_overbought=65,
        rsi_oversold=35,
        allow_short=True,
    )
    rsi_rev_bt_config = BacktestConfig(
        initial_capital=run_cfg.backtest_config.initial_capital,
        sl_pct=None,
        tp_rr=None,
        fee_pct=run_cfg.backtest_config.fee_pct,
        allow_short=True,
        atr_window=atr_window_default,
        atr_mult_sl=1.0,
        atr_mult_tp=1.5,
    )

    # --- Donchian_Breakout: sigue con ATR ---
    donchian_config = DonchianBreakoutStrategyConfig(
        channel_window=10,
        allow_short=False,
    )
    donchian_bt_config = BacktestConfig(
        initial_capital=run_cfg.backtest_config.initial_capital,
        sl_pct=None,
        tp_rr=None,
        fee_pct=run_cfg.backtest_config.fee_pct,
        allow_short=False,
        atr_window=atr_window_default,
        atr_mult_sl=1.5,
        atr_mult_tp=3.0,
    )

    # ============================
    # 2) LISTA DE ESTRATEGIAS
    # ============================

    strategies = [
        {
            "name": "MA_RSI_OPT",
            "strategy": MovingAverageRSIStrategy(config=ma_rsi_config),
            "backtest_config": ma_rsi_bt_config,
            "use_atr": False,
        },
        {
            "name": "RSI_Reversion_OPT",
            "strategy": RSIReversionStrategy(config=rsi_rev_config),
            "backtest_config": rsi_rev_bt_config,
            "use_atr": True,
        },
        {
            "name": "Donchian_Breakout_OPT",
            "strategy": DonchianBreakoutStrategy(config=donchian_config),
            "backtest_config": donchian_bt_config,
            "use_atr": True,
        },
    ]

    # ============================
    # 3) BACKTEST DE CADA ESTRATEGIA
    # ============================

    rows = []

    for s in strategies:
        name = s["name"]
        strat = s["strategy"]
        bt_cfg = s["backtest_config"]
        use_atr = s["use_atr"]

        print(f"\n=== Backtest estrategia: {name} ({strat.name}) ===")
        print(
            f"BacktestConfig: sl_pct={bt_cfg.sl_pct}, tp_rr={bt_cfg.tp_rr}, "
            f"atr_mult_sl={bt_cfg.atr_mult_sl}, atr_mult_tp={bt_cfg.atr_mult_tp}"
        )

        df_input = df_with_atr if use_atr else df

        df_signals = strat.generate_signals(df_input)

        backtester = Backtester(
            backtest_config=bt_cfg,
            risk_config=run_cfg.risk_config,
        )

        result = backtester.run(df_signals)

        print_backtest_summary(result)

        rows.append(
            {
                "strategy": name,
                "num_trades": result.num_trades,
                "total_return_pct": result.total_return_pct,
                "max_drawdown_pct": result.max_drawdown_pct,
                "winrate_pct": result.winrate_pct,
                "profit_factor": result.profit_factor,
            }
        )

    # ============================
    # 4) RESUMEN COMPARATIVO
    # ============================

    print("\n===== RESUMEN COMPARATIVO ESTRATEGIAS (OPTIMIZADAS + ATR) =====")
    df_summary = pd.DataFrame(rows)
    print(df_summary.sort_values(by="total_return_pct", ascending=False).reset_index(drop=True))


if __name__ == "__main__":
    main()