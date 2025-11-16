# strategies/ma_rsi_strategy.py

from dataclasses import dataclass

import pandas as pd
import ta  # librería 'ta' para indicadores técnicos

from strategies.base import BaseStrategy


@dataclass
class MovingAverageRSIStrategyConfig:
    """
    Configuración de la estrategia MA + RSI.
    """
    fast_window: int = 20        # periodos SMA rápida
    slow_window: int = 50        # periodos SMA lenta
    rsi_window: int = 14         # periodos RSI
    rsi_overbought: float = 70.0 # umbral de sobrecompra
    rsi_oversold: float = 30.0   # umbral de sobreventa

    # parámetros extra
    use_rsi_filter: bool = True        # si False, se ignora el filtro RSI
    signal_mode: str = "cross"         # "cross" = cruces, "trend" = estado de tendencia


class MovingAverageRSIStrategy(BaseStrategy):
    """
    Estrategia basada en medias móviles + RSI.
    """

    name: str = "MA_RSI"

    def __init__(self, config: MovingAverageRSIStrategyConfig | None = None) -> None:
        self.config = config or MovingAverageRSIStrategyConfig()

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        required_cols = {"timestamp", "open", "high", "low", "close", "volume"}
        if not required_cols.issubset(df.columns):
            missing = required_cols - set(df.columns)
            raise ValueError(f"Faltan columnas necesarias en el DataFrame: {missing}")

        data = df.copy()

        # Medias móviles simples
        data["sma_fast"] = (
            data["close"]
                .rolling(window=self.config.fast_window, min_periods=self.config.fast_window)
                .mean()
        )
        data["sma_slow"] = (
            data["close"]
                .rolling(window=self.config.slow_window, min_periods=self.config.slow_window)
                .mean()
        )

        # RSI
        rsi_indicator = ta.momentum.RSIIndicator(
            close=data["close"],
            window=self.config.rsi_window,
        )
        data["rsi"] = rsi_indicator.rsi()

        # Señales inicializadas a 0
        data["signal"] = 0

        sma_fast = data["sma_fast"]
        sma_slow = data["sma_slow"]
        rsi = data["rsi"]

        valid_mask = sma_fast.notna() & sma_slow.notna() & rsi.notna()

        if self.config.signal_mode == "cross":
            sma_fast_prev = sma_fast.shift(1)
            sma_slow_prev = sma_slow.shift(1)

            cross_up = (sma_fast > sma_slow) & (sma_fast_prev <= sma_slow_prev)
            cross_down = (sma_fast < sma_slow) & (sma_fast_prev >= sma_slow_prev)

            if self.config.use_rsi_filter:
                rsi_ok = (rsi > self.config.rsi_oversold) & (rsi < self.config.rsi_overbought)
                cross_up = cross_up & rsi_ok
                cross_down = cross_down & rsi_ok

            data.loc[valid_mask & cross_up, "signal"] = 1
            data.loc[valid_mask & cross_down, "signal"] = -1

        elif self.config.signal_mode == "trend":
            trend_long = sma_fast > sma_slow
            trend_short = sma_fast < sma_slow

            if self.config.use_rsi_filter:
                rsi_ok = (rsi > self.config.rsi_oversold) & (rsi < self.config.rsi_overbought)
                trend_long = trend_long & rsi_ok
                trend_short = trend_short & rsi_ok

            raw_signal = pd.Series(0, index=data.index, dtype="int64")
            raw_signal[trend_long] = 1
            raw_signal[trend_short] = -1

            signal = pd.Series(0, index=data.index, dtype="int64")
            prev = 0
            for i in range(len(raw_signal)):
                s = raw_signal.iloc[i]
                if s != 0 and s != prev:
                    signal.iloc[i] = s
                    prev = s

            data["signal"] = signal

        else:
            raise ValueError(f"Modo de señal no soportado: {self.config.signal_mode}")

        return data
