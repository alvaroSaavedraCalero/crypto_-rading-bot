# validation/validate_bb_trend.py

import pandas as pd

from backtesting.engine import BacktestConfig, Backtester
from config.settings import RISK_CONFIG
from data.downloader import get_datos_cripto_cached
from strategies.archived.bb_trend_strategy import BBTrendStrategy, BBTrendStrategyConfig


def run_bb_trend_on_market(
    symbol: str,
    timeframe: str,
    limit: int,
    cfg: BBTrendStrategyConfig,
    bt_cfg: BacktestConfig,
):
    print(f"\n=== BB_TREND_OPT en {symbol} {timeframe} (limit={limit}) ===")

    df = get_datos_cripto_cached(
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
        force_download=False,
    )
    print(f"Filas obtenidas: {len(df)}")

    strategy = BBTrendStrategy(config=cfg)
    df_signals = strategy.generate_signals(df)

    backtester = Backtester(
        backtest_config=bt_cfg,
        risk_config=RISK_CONFIG,
    )
    result = backtester.run(df_signals)

    print("Número de trades:", result.num_trades)
    print(f"Retorno total: {result.total_return_pct:.2f} %")
    print(f"Max drawdown: {result.max_drawdown_pct:.2f} %")
    print(f"Winrate: {result.winrate_pct:.2f} %")
    print(f"Profit factor: {result.profit_factor:.2f}")

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "num_trades": result.num_trades,
        "total_return_pct": result.total_return_pct,
        "max_drawdown_pct": result.max_drawdown_pct,
        "winrate_pct": result.winrate_pct,
        "profit_factor": result.profit_factor,
    }


def main():
    # Config óptima elegida del top de optimización:
    # bb_window=24, bb_std=2.0, trend_ema_window=100,
    # require_slope=True, signal_mode="pullback"
    bb_trend_cfg = BBTrendStrategyConfig(
        bb_window=24,
        bb_std=2.0,
        trend_ema_window=100,
        require_slope=True,
        allow_short=True,
        signal_mode="pullback",
    )

    # BacktestConfig igual que en el optimizador
    bt_cfg = BacktestConfig(
        initial_capital=1000.0,
        sl_pct=0.005,    # 0.5% SL
        tp_rr=2.0,       # TP 1:2
        fee_pct=0.0005,  # 0.05% comisión
        allow_short=True,
    )

    markets = [
        ("XRP/USDT", "15m", 5000),  # mercado base
        ("BTC/USDT", "15m", 5000),
        ("ETH/USDT", "15m", 5000),
        ("XRP/USDT", "1h",  5000),
        ("SOL/USDT", "15m", 5000),
        ("BNB/USDT", "15m", 5000),
    ]

    rows = []
    for symbol, timeframe, limit in markets:
        row = run_bb_trend_on_market(
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
            cfg=bb_trend_cfg,
            bt_cfg=bt_cfg,
        )
        rows.append(row)

    print("\n===== RESUMEN VALIDACIÓN CRUZADA BB_TREND_OPT =====")
    df_summary = pd.DataFrame(rows)
    df_summary = df_summary.sort_values(
        by="total_return_pct", ascending=False
    ).reset_index(drop=True)
    print(df_summary)


if __name__ == "__main__":
    main()