# Crypto Trading Bot

Bot modular de trading y backtesting para estrategias cuantitativas en mercados cripto. Incluye motor de backtest, paper trading, optimización de parámetros y reporting.

## Características
- Estrategias incluidas: MA+RSI, MACD+ADX, Supertrend, Keltner Breakout, Bollinger Mean Reversion, Squeeze Momentum y BB Trend.
- Backtesting vectorizado con gestión de riesgo, SL/TP porcentual o por ATR, métricas (retorno, drawdown, winrate, profit factor).
- Descarga y caché de datos OHLCV vía CCXT (`data/downloader.py`).
- Scripts de optimización y validación cruzada para ajustar parámetros.
- Reporting resumido en consola y generación de comparativas.

## Estructura rápida
- `config/settings.py`: configuraciones de estrategias (StrategyRunConfig) y riesgo.
- `scripts/backtest_strategies.py`: ejecuta todas las estrategias optimizadas.
- `scripts/backtest_2025.py`: backtest de todas las estrategias en rango temporal (por defecto, 1-ene-2025 a hoy).
- `scripts/paper_runner.py`: paper trading de una estrategia.
- `optimization/`: scripts de optimización (Bollinger, Keltner, MACD/ADX, Supertrend, Squeeze, MA/RSI).
- `data/downloadedData/`: caché local de datos OHLCV.
- `strategies/`: implementación de cada estrategia y registro (`registry.py`).
- `reporting/`: utilidades de resumen y reportes.

## Requisitos
- Python 3.10+ (entorno probado con 3.14).
- Dependencias en `requeriments.txt`.
- Cuenta/credenciales CCXT si vas a descargar datos en vivo (no necesarias para usar los CSV cacheados).

## Puesta en marcha
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requeriments.txt
export PYTHONPATH="$(pwd):$PYTHONPATH"
```

## Uso
- **Backtest optimizadas (todas):**
  ```bash
  PYTHONPATH=$(pwd):$PYTHONPATH python scripts/backtest_strategies.py
  ```
- **Backtest 2025 YTD (todas):**
  ```bash
  PYTHONPATH=$(pwd):$PYTHONPATH python scripts/backtest_2025.py
  ```
- **Paper trading de una estrategia:**
  Edita `RUN_CONFIG` en `scripts/paper_runner.py` y ejecuta:
  ```bash
  PYTHONPATH=$(pwd):$PYTHONPATH python scripts/paper_runner.py
  ```
- **Optimizar una estrategia concreta:**
  ```bash
  PYTHONPATH=$(pwd):$PYTHONPATH python optimization/optimize_<estrategia>.py
  # ej: optimization/optimize_bollinger.py
  ```

## Datos
- Para ahorrar tiempo, el repositorio ya incluye datos cacheados en `data/downloadedData/`.
- Si faltan datos o quieres actualizar, los scripts los descargarán vía CCXT. Asegúrate de configurar claves si el exchange lo requiere.

## Notas
- Ajusta `OPTIMIZED_STRATEGIES` en `config/settings.py` si quieres añadir/quitar configuraciones.
- Usa `strategies/registry.py` para instanciar estrategias por tipo (`create_strategy`).
- Los CSV de optimización (`opt_*.csv`) guardan los mejores parámetros encontrados; puedes actualizar `config/settings.py` con nuevos valores tras re-optimizar.
