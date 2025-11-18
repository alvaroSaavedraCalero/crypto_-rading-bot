# validation/validate_squezze_momentum.py

import pandas as pd

from backtesting.engine import BacktestConfig, Backtester
from config.settings import RISK_CONFIG
from data.downloader import get_datos_cripto_cached
from strategies.squeeze_momentum_strategy import (
    SqueezeMomentumStrategy,
    SqueezeMomentumConfig,
)


def run_squeeze_on_market(
    symbol: str,
    timeframe: str,
    limit: int,
    cfg: SqueezeMomentumConfig,
    bt_cfg: BacktestConfig,
):
    print(f"\n=== SQUEEZE_OPT en {symbol} {timeframe} (limit={limit}) ===")

    df = get_datos_cripto_cached(
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
        force_download=False,
    )
    print(f"Filas obtenidas: {len(df)}")

    strategy = SqueezeMomentumStrategy(config=cfg)
    df_signals = strategy.generate_signals(df)

    bt = Backtester(
        backtest_config=bt_cfg,
        risk_config=RISK_CONFIG,
    )
    result = bt.run(df_signals)

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
    # Config óptima elegida de la fila 0 de opt_squeeze_BNBUSDT_15m.csv
    # Si en tu CSV ves otros valores para mom_window, atr_min_percentile,
    # min_squeeze_bars, etc., cámbialos aquí.
    squeeze_cfg = SqueezeMomentumConfig(
        bb_window=20,
        bb_mult=1.8,
        kc_window=14,
        kc_mult=2.0,
        mom_window=10, # 10
        atr_window=14,
        atr_min_percentile=0.3, # 0.3
        min_squeeze_bars=5, # 5
        allow_short=True,
    )

    bt_cfg = BacktestConfig(
        initial_capital=1000.0,
        sl_pct=0.005,    # 0.5% SL
        tp_rr=2.0,       # TP 1:2
        fee_pct=0.0005,
        allow_short=True,
    )

    markets = [
        ("BNB/USDT", "15m", 5000),  # mercado base (donde has optimizado)
        ("BTC/USDT", "15m", 5000),
        ("ETH/USDT", "15m", 5000),
        ("SOL/USDT", "15m", 5000),
        ("XRP/USDT", "15m", 5000),
        ("BNB/USDT", "1h",  5000),
    ]

    rows = []
    for symbol, timeframe, limit in markets:
        row = run_squeeze_on_market(
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
            cfg=squeeze_cfg,
            bt_cfg=bt_cfg,
        )
        rows.append(row)

    print("\n===== RESUMEN VALIDACIÓN CRUZADA SQUEEZE_OPT =====")
    df_summary = pd.DataFrame(rows)
    df_summary = df_summary.sort_values(
        by="total_return_pct", ascending=False
    ).reset_index(drop=True)
    print(df_summary)


if __name__ == "__main__":
    main()