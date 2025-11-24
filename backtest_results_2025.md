# Resultados de Backtest: 2025

**Periodo:** 1 de Enero de 2025 - 24 de Noviembre de 2025

Se ha ejecutado un backtest de las estrategias optimizadas utilizando datos históricos de Binance para el año en curso.

## Resumen Comparativo

| Estrategia | Símbolo | Timeframe | Trades | Retorno Total | Max Drawdown | Winrate | Profit Factor |
|---|---|---|---|---|---|---|---|
| **MACD_ADX_TREND_OPT_ETHUSDT_15m** | ETH/USDT | 15m | 273 | **11.65%** | -29.15% | 32.97% | 1.14 |
| **MA_RSI_OPT_BTCUSDT_15m** | BTC/USDT | 15m | 497 | -40.73% | -65.28% | 27.77% | 0.96 |
| **SQUEEZE_MOMENTUM_OPT_BNBUSDT_15m** | BNB/USDT | 15m | 332 | -51.26% | -53.93% | 33.13% | 0.82 |
| **KELTNER_BREAKOUT_SOLUSDT_15m** | SOL/USDT | 15m | 1200 | -52.90% | -68.94% | 30.00% | 0.96 |

## Análisis Preliminar

*   **MACD_ADX_TREND (ETH)** es la única estrategia con rendimiento positivo en lo que va de año (+11.65%).
*   Las estrategias de **RSI (BTC)**, **Squeeze Momentum (BNB)** y **Keltner Breakout (SOL)** han sufrido pérdidas significativas y drawdowns profundos (>50%).
*   El alto número de trades en la estrategia Keltner (1200) sugiere una operativa muy activa que, combinada con un bajo winrate (30%), ha erosionado el capital, posiblemente debido a comisiones y falsas rupturas en mercados laterales.

## Notas Técnicas
*   Se descargaron aproximadamente 33,500 velas de 15 minutos para cubrir el periodo.
*   Los datos incluyen un buffer previo para el cálculo inicial de indicadores.
