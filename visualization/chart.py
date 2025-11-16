# visualization/chart.py

from typing import Optional, List

import matplotlib.pyplot as plt
import mplfinance as mpf
import pandas as pd

from strategies.ma_rsi_strategy import MovingAverageRSIStrategyConfig
from backtesting.engine import BacktestResult, Trade


def _prepare_ohlcv_for_mplfinance(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepara el DataFrame para mplfinance:
    - Index: timestamp
    - Columnas: Open, High, Low, Close, Volume
    """
    required_cols = {"timestamp", "open", "high", "low", "close", "volume"}
    if not required_cols.issubset(df.columns):
        missing = required_cols - set(df.columns)
        raise ValueError(f"Faltan columnas necesarias en el DataFrame: {missing}")

    data = df.copy()
    data = data.set_index("timestamp")
    data = data.rename(
        columns={
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        }
    )
    return data


def plot_candles(df: pd.DataFrame, title: str = "Velas OHLCV") -> None:
    """
    Muestra un gráfico de velas con volumen usando mplfinance.
    """
    data = _prepare_ohlcv_for_mplfinance(df)

    mpf.plot(
        data,
        type="candle",
        volume=True,
        title=title,
        show_nontrading=False,
    )


def plot_ma_rsi_indicators(
    df: pd.DataFrame,
    config: Optional[MovingAverageRSIStrategyConfig] = None,
    title: str = "Indicadores MA + RSI",
) -> None:
    """
    Muestra:
    - Subplot 1: Precio de cierre + SMA rápida + SMA lenta
    - Subplot 2: RSI

    Asume que el DataFrame ya tiene columnas:
    - close
    - sma_fast
    - sma_slow
    - rsi
    """
    config = config or MovingAverageRSIStrategyConfig()

    required_cols = {"timestamp", "close", "sma_fast", "sma_slow", "rsi"}
    if not required_cols.issubset(df.columns):
        missing = required_cols - set(df.columns)
        raise ValueError(
            f"Faltan columnas necesarias para los indicadores MA+RSI: {missing}. "
            "Asegúrate de haber pasado antes la estrategia para generar estas columnas."
        )

    data = df.copy()

    # Usamos timestamp como eje X
    x = data["timestamp"]

    fig, (ax_price, ax_rsi) = plt.subplots(
        2,
        1,
        sharex=True,
        figsize=(12, 8),
        gridspec_kw={"height_ratios": [3, 1]},
    )
    fig.suptitle(title)

    # --- Subplot 1: precio + MAs ---
    ax_price.plot(x, data["close"], label="Close")
    ax_price.plot(x, data["sma_fast"], label=f"SMA {config.fast_window}")
    ax_price.plot(x, data["sma_slow"], label=f"SMA {config.slow_window}")
    ax_price.set_ylabel("Precio")
    ax_price.legend(loc="best")
    ax_price.grid(True)

    # --- Subplot 2: RSI ---
    ax_rsi.plot(x, data["rsi"], label=f"RSI {config.rsi_window}")
    ax_rsi.axhline(config.rsi_overbought, linestyle="--")
    ax_rsi.axhline(config.rsi_oversold, linestyle="--")
    ax_rsi.set_ylabel("RSI")
    ax_rsi.set_xlabel("Tiempo")
    ax_rsi.legend(loc="best")
    ax_rsi.grid(True)

    plt.tight_layout()
    plt.show()


def _build_marker_series(
    df_candles: pd.DataFrame,
    trades: List[Trade],
    field: str,
) -> pd.Series:
    """
    Construye una serie para marcar puntos (entrada/salida) en el gráfico de velas.
    - df_candles: DataFrame ya preparado para mplfinance (index = timestamp).
    - trades: lista de Trade.
    - field: 'entry' o 'exit' para decidir qué timestamp/precio usar.
    """
    # Serie llena de NaN, mismo índice que las velas
    s = pd.Series(index=df_candles.index, dtype="float64")

    for t in trades:
        if field == "entry":
            ts = t.entry_time
            price = t.entry_price
        elif field == "exit":
            # Puede haber trades sin cerrar (exit_time None)
            if t.exit_time is None or t.exit_price is None:
                continue
            ts = t.exit_time
            price = t.exit_price
        else:
            continue

        # Alinear timestamp del trade al índice del DataFrame
        if ts in s.index:
            s.loc[ts] = price
        else:
            # Si no coincide exactamente (por seguridad), buscamos el timestamp más cercano
            # Esto puede ocurrir según cómo se construyan los datos en el futuro.
            nearest_idx = s.index.get_indexer([ts], method="nearest")[0]
            s.iloc[nearest_idx] = price

    return s

def _has_valid_points(series: pd.Series) -> bool:
    """
    Verifica si la serie tiene al menos un punto no NaN.
    """
    return series.notna().any()

def plot_candles_with_trades(
    df: pd.DataFrame,
    result: BacktestResult,
    title: str = "Velas con operaciones",
) -> None:
    """
    Dibuja velas OHLCV y marca entradas/salidas de los trades del backtest.

    - Triángulos hacia arriba para entradas de largos.
    - Triángulos hacia abajo para entradas de cortos.
    - Puntos para salidas.
    """
    if not result.trades:
        print("No hay trades en el resultado del backtest para visualizar.")
        return

    df_candles = _prepare_ohlcv_for_mplfinance(df)

    # Separamos trades largos y cortos
    longs = [t for t in result.trades if t.direction == "long"]
    shorts = [t for t in result.trades if t.direction == "short"]

    # Series para entradas y salidas
    long_entries = _build_marker_series(df_candles, longs, field="entry")
    short_entries = _build_marker_series(df_candles, shorts, field="entry")
    exits = _build_marker_series(df_candles, result.trades, field="exit")

    apds = []

    # Solo añadimos addplot si hay al menos un punto válido

    if _has_valid_points(long_entries):
        apds.append(
            mpf.make_addplot(
                long_entries,
                type="scatter",
                marker="^",
                markersize=50,
            )
        )

    if _has_valid_points(short_entries):
        apds.append(
            mpf.make_addplot(
                short_entries,
                type="scatter",
                marker="v",
                markersize=50,
            )
        )

    if _has_valid_points(exits):
        apds.append(
            mpf.make_addplot(
                exits,
                type="scatter",
                marker="o",
                markersize=30,
            )
        )

    mpf.plot(
        df_candles,
        type="candle",
        volume=True,
        title=title,
        show_nontrading=False,
        addplot=apds if apds else None,
    )

