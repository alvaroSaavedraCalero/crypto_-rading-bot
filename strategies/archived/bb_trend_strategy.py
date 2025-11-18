# strategies/bb_trend_strategy.py

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from strategies.base import BaseStrategy


SignalMode = Literal["breakout", "pullback"]


@dataclass
class BBTrendStrategyConfig:
    """
    Estrategia Bollinger + Tendencia:

    - Tendencia por EMA de largo plazo (trend_ema_window).
    - Señales:
      * breakout: entradas cuando el precio rompe la banda media en dirección de la tendencia.
      * pullback: entradas cuando el precio toca banda inferior/superior en tendencia y vuelve hacia la media.

    El SL/TP lo define el BacktestConfig (sl_pct / tp_rr).
    """
    bb_window: int = 20
    bb_std: float = 2.0
    trend_ema_window: int = 200
    require_slope: bool = True        # exige EMA con pendiente a favor
    allow_short: bool = True
    signal_mode: SignalMode = "breakout"  # "breakout" o "pullback"


class BBTrendStrategy(BaseStrategy):
    def __init__(self, config: BBTrendStrategyConfig) -> None:
        self.config = config

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Devuelve un DataFrame con columna 'signal' (1, -1, 0) usando:

        - 'timestamp', 'open', 'high', 'low', 'close' del df original.
        - EMA de tendencia.
        - Bandas de Bollinger sobre el cierre.
        """
        required = {"timestamp", "open", "high", "low", "close"}
        if not required.issubset(df.columns):
            missing = required - set(df.columns)
            raise ValueError(f"Faltan columnas necesarias en el DataFrame de entrada: {missing}")

        data = df.sort_values("timestamp").reset_index(drop=True).copy()

        close = data["close"]

        # 1) EMA de tendencia
        trend_ema = close.ewm(span=self.config.trend_ema_window, adjust=False).mean()
        data["trend_ema"] = trend_ema

        # 2) Bandas de Bollinger
        ma = close.rolling(self.config.bb_window, min_periods=self.config.bb_window).mean()
        std = close.rolling(self.config.bb_window, min_periods=self.config.bb_window).std(ddof=0)

        data["bb_mid"] = ma
        data["bb_up"] = ma + self.config.bb_std * std
        data["bb_low"] = ma - self.config.bb_std * std

        # 3) Tendencia
        if self.config.require_slope:
            ema_slope = trend_ema.diff()
            uptrend = (close > trend_ema) & (ema_slope > 0)
            downtrend = (close < trend_ema) & (ema_slope < 0)
        else:
            uptrend = close > trend_ema
            downtrend = close < trend_ema

        # 4) Señales
        signal = np.zeros(len(data), dtype=int)

        if self.config.signal_mode == "breakout":
            # LONG: tendencia alcista y cierre cruza por encima de la banda media
            long_cond = (
                uptrend &
                (close.shift(1) <= data["bb_mid"].shift(1)) &
                (close > data["bb_mid"])
            )

            # SHORT: tendencia bajista y cierre cruza por debajo de la banda media
            short_cond = np.zeros(len(data), dtype=bool)
            if self.config.allow_short:
                short_cond = (
                    downtrend &
                    (close.shift(1) >= data["bb_mid"].shift(1)) &
                    (close < data["bb_mid"])
                )

        elif self.config.signal_mode == "pullback":
            # LONG: en tendencia alcista, precio rebota desde banda baja hacia arriba
            long_cond = (
                uptrend &
                (close.shift(1) <= data["bb_low"].shift(1)) &
                (close > data["bb_low"])
            )

            short_cond = np.zeros(len(data), dtype=bool)
            if self.config.allow_short:
                # SHORT: en tendencia bajista, rebote desde banda alta hacia abajo
                short_cond = (
                    downtrend &
                    (close.shift(1) >= data["bb_up"].shift(1)) &
                    (close < data["bb_up"])
                )
        else:
            raise ValueError(f"signal_mode no soportado: {self.config.signal_mode}")

        signal[long_cond] = 1
        signal[short_cond] = -1

        data["signal"] = signal.astype(int)

        return data