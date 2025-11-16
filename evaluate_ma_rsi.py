# evaluate_ma_rsi.py

from config.settings import DEFAULT_RUN_CONFIG
from data.downloader import get_datos_cripto_cached
from optimization.evaluate_ma_rsi import run_train_test_evaluation


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

    # Rango de parámetros para optimización en TRAIN
    fast_windows = [5, 10, 15]
    slow_windows = [20, 30, 40]
    rsi_windows = [10, 14]
    sl_pcts = [0.003, 0.005, 0.01]
    tp_rrs = [1.5, 2.0, 3.0]

    run_train_test_evaluation(
        df_full=df,
        run_cfg=run_cfg,
        fast_windows=fast_windows,
        slow_windows=slow_windows,
        rsi_windows=rsi_windows,
        sl_pcts=sl_pcts,
        tp_rrs=tp_rrs,
        train_ratio=0.7,
        min_trades=5,  # mínimo de trades en TRAIN para aceptar la configuración
    )


if __name__ == "__main__":
    main()
