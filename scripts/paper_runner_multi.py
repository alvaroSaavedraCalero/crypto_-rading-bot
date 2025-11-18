# scripts/paper_runner_multi.py

"""
Paper runner múltiple:
Ejecuta todas las estrategias optimizadas definidas en config.settings.OPTIMIZED_STRATEGIES
cada una con su propia cuenta de paper trading.

Esto es equivalente a lo que hace backtest_strategies.py,
pero usando la arquitectura de execution (PaperBroker + BaseStrategy),
con fricción de mercado (fees + slippage + spread) más realista.
"""

import pandas as pd

from config.settings import OPTIMIZED_STRATEGIES, RISK_CONFIG
from data.downloader import get_datos_cripto_cached
from execution.paper_broker import PaperBroker
from strategies.registry import create_strategy

# Parámetros de mercado simulados (más realistas para Binance spot en pares líquidos)
SLIPPAGE_PCT = 0.0001   # 0.01 %
SPREAD_PCT = 0.0001     # 0.01 %


def run_paper_for_config(run_cfg):
    print(f"\n=== PAPER TRADING {run_cfg.name} ({run_cfg.strategy_type}) ===")
    print(f"Símbolo: {run_cfg.symbol}, timeframe: {run_cfg.timeframe}, límite velas: {run_cfg.limit_candles}")
    print(f"Slippage simulado: {SLIPPAGE_PCT * 100:.3f} %  |  Spread simulado: {SPREAD_PCT * 100:.3f} %")

    df = get_datos_cripto_cached(
        symbol=run_cfg.symbol,
        timeframe=run_cfg.timeframe,
        limit=run_cfg.limit_candles,
        force_download=False,
    )
    print(f"Filas obtenidas: {len(df)}")

    # 1) Crear estrategia desde el registry
    strategy = create_strategy(run_cfg.strategy_type, run_cfg.strategy_config)

    # 2) Generar señales
    df_signals = strategy.generate_signals(df)
    if "signal" not in df_signals.columns:
        raise ValueError(f"La estrategia {run_cfg.name} no ha generado columna 'signal'.")

    # 3) Crear broker de paper con la config de backtest adecuada
    broker = PaperBroker(
        symbol=run_cfg.symbol,
        backtest_config=run_cfg.backtest_config,
        risk_config=RISK_CONFIG,
        slippage_pct=SLIPPAGE_PCT,
        spread_pct=SPREAD_PCT,
    )

    # 4) Reproducción vela a vela
    for _, row in df_signals.iterrows():
        sig = row["signal"]
        signal = int(sig) if not pd.isna(sig) else 0
        # Si en el futuro quieres usar SL/TP basado en ATR, pásalo aquí en vez de None
        broker.on_bar(row=row, signal=signal, atr_value=None)

    # 5) Resumen por estrategia
    broker.print_summary()

    # 6) Devolver info para resumen global
    eq = broker.get_equity_series()
    initial = eq.iloc[0] if len(eq) > 0 else run_cfg.backtest_config.initial_capital
    final = eq.iloc[-1] if len(eq) > 0 else initial
    total_return_pct = (final / initial - 1.0) * 100.0 if initial > 0 else 0.0

    return {
        "strategy": run_cfg.name,
        "symbol": run_cfg.symbol,
        "timeframe": run_cfg.timeframe,
        "num_trades": len(broker.state.history),
        "total_return_pct": total_return_pct,
    }


def main():
    rows = []
    for run_cfg in OPTIMIZED_STRATEGIES:
        row = run_paper_for_config(run_cfg)
        rows.append(row)

    print("\n===== RESUMEN PAPER (MULTI ESTRATEGIA) =====")
    df_summary = pd.DataFrame(rows)
    df_summary = df_summary.sort_values(by="total_return_pct", ascending=False).reset_index(drop=True)
    print(df_summary)


if __name__ == "__main__":
    main()