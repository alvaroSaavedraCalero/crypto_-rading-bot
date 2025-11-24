
import pandas as pd
from datetime import datetime, timezone
import math

from config.settings import (
    OPTIMIZED_STRATEGIES,
    RISK_CONFIG,
)
from data.downloader import get_datos_cripto_cached
from backtesting.engine import Backtester
from reporting.summary import print_backtest_summary
from strategies.ma_rsi_strategy import MovingAverageRSIStrategy
from strategies.macd_adx_trend_strategy import MACDADXTrendStrategy
from strategies.keltner_breakout_strategy import KeltnerBreakoutStrategy
from strategies.archived.bb_trend_strategy import BBTrendStrategy
from strategies.squeeze_momentum_strategy import SqueezeMomentumStrategy


def run_single_strategy_date_range(run_cfg, start_date, end_date):
    """
    Ejecuta un backtest para una StrategyRunConfig definida en config.settings.OPTIMIZED_STRATEGIES,
    filtrando por un rango de fechas específico.
    """
    print(f"\n=== Backtest estrategia: {run_cfg.name} ({run_cfg.strategy_type}) ===")
    print(f"Rango: {start_date} - {end_date}")
    print(
        f"Símbolo: {run_cfg.symbol}, timeframe: {run_cfg.timeframe}"
    )

    # Calcular límite de velas necesario
    # Aproximación: (end - start) / timeframe
    # Convertir timeframe a minutos
    tf_str = run_cfg.timeframe
    if tf_str.endswith('m'):
        tf_minutes = int(tf_str[:-1])
    elif tf_str.endswith('h'):
        tf_minutes = int(tf_str[:-1]) * 60
    elif tf_str.endswith('d'):
        tf_minutes = int(tf_str[:-1]) * 60 * 24
    else:
        tf_minutes = 60 # Default fallback

    duration = end_date - start_date
    duration_minutes = duration.total_seconds() / 60
    required_candles = math.ceil(duration_minutes / tf_minutes)
    
    # Añadir un buffer de seguridad (ej. 20% más o 1000 velas) para indicadores previos
    limit_candles = required_candles + 2000
    
    print(f"Solicitando {limit_candles} velas para cubrir el rango...")

    print(f"Solicitando {limit_candles} velas para cubrir el rango...")

    # Primero intentamos cargar lo que haya en caché
    df = get_datos_cripto_cached(
        symbol=run_cfg.symbol,
        timeframe=run_cfg.timeframe,
        limit=limit_candles,
        force_download=False,
    )

    # Verificar si tenemos datos suficientes (si el primer timestamp es posterior a start_date)
    # Asegurar zona horaria UTC
    if df['timestamp'].dt.tz is None:
         df['timestamp'] = df['timestamp'].dt.tz_localize('UTC')
    
    first_ts = df['timestamp'].iloc[0]
    if first_ts > start_date:
        print(f"Datos en caché insuficientes (empiezan en {first_ts}, necesitamos {start_date}). Forzando descarga...")
        df = get_datos_cripto_cached(
            symbol=run_cfg.symbol,
            timeframe=run_cfg.timeframe,
            limit=limit_candles,
            force_download=True,
        )
        if df['timestamp'].dt.tz is None:
            df['timestamp'] = df['timestamp'].dt.tz_localize('UTC')
    
    # Filtrar por fecha
    mask = (df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)
    df_filtered = df.loc[mask].copy().reset_index(drop=True)
    
    print(f"Filas obtenidas (total): {len(df)}")
    print(f"Filas tras filtrar por fecha: {len(df_filtered)}")

    if df_filtered.empty:
        print("ADVERTENCIA: No hay datos en el rango de fechas especificado.")
        return None

    # Instanciamos la estrategia según el tipo
    if run_cfg.strategy_type == "MA_RSI":
        strategy = MovingAverageRSIStrategy(config=run_cfg.strategy_config)
    elif run_cfg.strategy_type == "MACD_ADX":
        strategy = MACDADXTrendStrategy(config=run_cfg.strategy_config)
    elif run_cfg.strategy_type == "KELTNER":
        strategy = KeltnerBreakoutStrategy(config=run_cfg.strategy_config)
    elif run_cfg.strategy_type == "BB_TREND":
        strategy = BBTrendStrategy(config=run_cfg.strategy_config)
    elif run_cfg.strategy_type == "SQUEEZE":
        strategy = SqueezeMomentumStrategy(config=run_cfg.strategy_config)
    else:
        raise ValueError(f"Tipo de estrategia no soportado: {run_cfg.strategy_type}")

    df_signals = strategy.generate_signals(df_filtered)

    backtester = Backtester(
        backtest_config=run_cfg.backtest_config,
        risk_config=RISK_CONFIG,
    )
    result = backtester.run(df_signals)

    print_backtest_summary(result)

    return {
        "strategy": run_cfg.name,
        "symbol": run_cfg.symbol,
        "timeframe": run_cfg.timeframe,
        "num_trades": result.num_trades,
        "total_return_pct": result.total_return_pct,
        "max_drawdown_pct": result.max_drawdown_pct,
        "winrate_pct": result.winrate_pct,
        "profit_factor": result.profit_factor,
    }


def main():
    # Definir rango de fechas: 1 de enero de 2025 hasta hoy (24 de noviembre de 2025)
    start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
    end_date = datetime(2025, 11, 24, 23, 59, 59, tzinfo=timezone.utc) # Final del día de hoy

    rows = []

    for run_cfg in OPTIMIZED_STRATEGIES:
        row = run_single_strategy_date_range(run_cfg, start_date, end_date)
        if row:
            rows.append(row)

    print("\n===== RESUMEN COMPARATIVO ESTRATEGIAS (2025) =====")
    if rows:
        df_summary = pd.DataFrame(rows)
        df_summary = df_summary.sort_values(
            by="total_return_pct",
            ascending=False,
        ).reset_index(drop=True)
        print(df_summary)
    else:
        print("No se generaron resultados.")


if __name__ == "__main__":
    main()
