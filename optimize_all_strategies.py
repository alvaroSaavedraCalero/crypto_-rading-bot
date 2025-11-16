# optimize_all_strategies.py

from pathlib import Path

from config.settings import DEFAULT_RUN_CONFIG
from data.downloader import get_datos_cripto_cached
from optimization.ma_rsi_optimizer import run_ma_rsi_grid_search
from optimization.rsi_reversion_optimizer import run_rsi_reversion_grid_search
from optimization.donchian_optimizer import run_donchian_grid_search


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

    # === 1) MA_RSI ===
    print("\n=== OPTIMIZACIÓN MA_RSI ===")
    fast_windows = [5, 10, 15]
    slow_windows = [20, 30, 40]
    rsi_windows = [10, 14]
    sl_pcts = [0.003, 0.005, 0.01]
    tp_rrs = [1.5, 2.0, 3.0]

    df_ma_rsi = run_ma_rsi_grid_search(
        df=df,
        fast_windows=[5, 10, 15],
        slow_windows=[20, 30, 40],
        rsi_windows=[10, 14],
        sl_pcts=[0.003, 0.005, 0.01],
        tp_rrs=[1.5, 2.0, 3.0],
        base_backtest_config=run_cfg.backtest_config,
        base_risk_config=run_cfg.risk_config,
        min_trades=3,  # más laxo
        signal_modes=("cross", "trend"),
        use_rsi_filter_options=(False, True),
    )


    if df_ma_rsi.empty:
        print("MA_RSI: sin resultados (revisa min_trades o rangos).")
    else:
        print("\nTop 5 MA_RSI:")
        print(df_ma_rsi.head(5))
        out_ma = Path(f"opt_ma_rsi_{symbol.replace('/', '')}_{timeframe}.csv")
        df_ma_rsi.to_csv(out_ma, index=False)
        print(f"Resultados MA_RSI guardados en {out_ma.resolve()}")

    # === 2) RSI_Reversion ===
    print("\n=== OPTIMIZACIÓN RSI_Reversion ===")
    rsi_windows = [10, 14, 21]
    rsi_overbought_levels = [65, 70, 75]
    rsi_oversold_levels = [25, 30, 35]
    allow_short_options = [True, False]

    df_rsi_rev = run_rsi_reversion_grid_search(
        df=df,
        rsi_windows=rsi_windows,
        rsi_overbought_levels=rsi_overbought_levels,
        rsi_oversold_levels=rsi_oversold_levels,
        allow_short_options=allow_short_options,
        base_backtest_config=run_cfg.backtest_config,
        base_risk_config=run_cfg.risk_config,
        min_trades=5,
    )

    if df_rsi_rev.empty:
        print("RSI_Reversion: sin resultados (revisa min_trades o rangos).")
    else:
        print("\nTop 5 RSI_Reversion:")
        print(df_rsi_rev.head(5))
        out_rsi = Path(f"opt_rsi_rev_{symbol.replace('/', '')}_{timeframe}.csv")
        df_rsi_rev.to_csv(out_rsi, index=False)
        print(f"Resultados RSI_Reversion guardados en {out_rsi.resolve()}")

    # === 3) Donchian_Breakout ===
    print("\n=== OPTIMIZACIÓN Donchian_Breakout ===")
    channel_windows = [5, 10, 15, 20]
    allow_short_options = [True, False]


    df_donch = run_donchian_grid_search(
        df=df,
        channel_windows=channel_windows,
        allow_short_options=allow_short_options,
        base_backtest_config=run_cfg.backtest_config,
        base_risk_config=run_cfg.risk_config,
        min_trades=1,
    )

    if df_donch.empty:
        print("Donchian_Breakout: sin resultados (revisa min_trades o rangos).")
    else:
        print("\nTop 5 Donchian_Breakout:")
        print(df_donch.head(5))
        out_don = Path(f"opt_donchian_{symbol.replace('/', '')}_{timeframe}.csv")
        df_donch.to_csv(out_don, index=False)
        print(f"Resultados Donchian_Breakout guardados en {out_don.resolve()}")


if __name__ == "__main__":
    main()
