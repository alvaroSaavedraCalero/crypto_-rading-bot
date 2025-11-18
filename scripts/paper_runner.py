# scripts/paper_runner.py

"""
Paper runner sencillo: reproduce el comportamiento del backtest,
pero usando la arquitectura de ejecución (PaperBroker + BaseStrategy).

De momento ejecuta UNA estrategia run_config a la vez.
Puedes cambiar RUN_CONFIG para probar otras.
"""

import pandas as pd

from config.settings import (
    MA_RSI_BTC15M_RUN,
    MACD_ADX_ETH15M_RUN,
    KELTNER_SOL15M_RUN,
    RISK_CONFIG,
)
from data.downloader import get_datos_cripto_cached
from execution.paper_broker import PaperBroker
from strategies.registry import create_strategy

# Elige aquí qué estrategia quieres lanzar en modo "paper"
RUN_CONFIG = MA_RSI_BTC15M_RUN
# RUN_CONFIG = MACD_ADX_ETH15M_RUN
# RUN_CONFIG = KELTNER_SOL15M_RUN

# Parámetros de mercado simulados
SLIPPAGE_PCT = 0.0005   # 0.05 %
SPREAD_PCT = 0.0005     # 0.05 %


def run_paper_for_config(run_cfg) -> None:
    print(f"\n=== PAPER TRADING {run_cfg.name} ===")
    print(f"Símbolo: {run_cfg.symbol}, timeframe: {run_cfg.timeframe}, límite velas: {run_cfg.limit_candles}")

    df = get_datos_cripto_cached(
        symbol=run_cfg.symbol,
        timeframe=run_cfg.timeframe,
        limit=run_cfg.limit_candles,
        force_download=False,
    )
    print(f"Filas obtenidas: {len(df)}")

    # 1) Crear estrategia a partir del registry
    strategy = create_strategy(run_cfg.strategy_type, run_cfg.strategy_config)

    # 2) Generar señales para TODO el histórico
    df_signals = strategy.generate_signals(df)

    if "signal" not in df_signals.columns:
        raise ValueError("La estrategia no ha generado columna 'signal'.")

    # 3) Crear broker de paper
    broker = PaperBroker(
        symbol=run_cfg.symbol,
        backtest_config=run_cfg.backtest_config,
        risk_config=RISK_CONFIG,
        slippage_pct=SLIPPAGE_PCT,
        spread_pct=SPREAD_PCT,
    )

    # 4) Reproducir vela a vela
    for _, row in df_signals.iterrows():
        signal = int(row["signal"]) if not pd.isna(row["signal"]) else 0
        # Aquí podrías pasar ATR u otros datos si quisieras SL/TP por ATR
        broker.on_bar(row=row, signal=signal, atr_value=None)

    # 5) Resumen
    broker.print_summary()


def main():
    run_paper_for_config(RUN_CONFIG)


if __name__ == "__main__":
    main()