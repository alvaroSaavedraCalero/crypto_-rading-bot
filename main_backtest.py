# main_backtest.py

from config.settings import DEFAULT_RUN_CONFIG
from data.downloader import get_datos_cripto_cached
from strategies.ma_rsi_strategy import MovingAverageRSIStrategy
from backtesting.engine import Backtester
from reporting.summary import (
    print_backtest_summary,
    save_trades_to_csv,
    plot_equity_curve,
)
from visualization.chart import plot_candles_with_trades


def main():
    run_cfg = DEFAULT_RUN_CONFIG

    symbol = run_cfg.symbol
    timeframe = run_cfg.timeframe
    limit = run_cfg.limit_candles

    # 1) Datos
    print(f"Obteniendo datos de {symbol} en timeframe {timeframe}...")
    df = get_datos_cripto_cached(
        symbol=symbol,
        timeframe=timeframe,
        limit=limit,
        force_download=False,
    )
    print(f"Filas obtenidas: {len(df)}")

    # 2) Estrategia (MA + RSI)
    strategy = MovingAverageRSIStrategy(config=run_cfg.strategy_config)
    df_signals = strategy.generate_signals(df)

    # 3) Backtest + riesgo
    backtester = Backtester(
        backtest_config=run_cfg.backtest_config,
        risk_config=run_cfg.risk_config,
    )
    result = backtester.run(df_signals)

    # 4) Reporting por consola y CSV
    print_backtest_summary(result)
    csv_name = f"trades_{symbol.replace('/', '')}_{timeframe}.csv"
    save_trades_to_csv(result, file_path=csv_name)

    # 5) Equity curve
    plot_equity_curve(result, title=f"Equity curve - {symbol} {timeframe}")

    # 6) Velas con operaciones
    plot_candles_with_trades(
        df=df_signals,
        result=result,
        title=f"{symbol} {timeframe} - Velas con trades",
    )


if __name__ == "__main__":
    main()
