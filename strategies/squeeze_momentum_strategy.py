# strategies/squeeze_momentum_strategy.py

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from strategies.base import BaseStrategy


@dataclass
class SqueezeMomentumConfig:
    """
    Estrategia Squeeze Momentum (tipo TTM Squeeze simplificado):

    - Bollinger Bands (BB): mide contracción/expansión de volatilidad.
    - Keltner Channels (KC): referencia de rango medio (ATR).
    - Squeeze ON: BB dentro de KC  -> baja volatilidad.
    - Squeeze OFF: BB sale de KC   -> inicio de expansión.

    Entradas:
      - Tras un periodo en squeeze (min_squeeze_bars),
      - Cuando el squeeze se libera (OFF),
      - Y el momentum apunta en una dirección.
    """
    bb_window: int = 20
    bb_mult: float = 2.0
    kc_window: int = 20
    kc_mult: float = 1.5
    mom_window: int = 20          # ventana para momentum
    atr_window: int = 14          # ATR para KC y filtro de volatilidad
    atr_min_percentile: float = 0.2  # solo operar cuando ATR > percentil global
    min_squeeze_bars: int = 3        # nº mínimo de velas en squeeze antes de liberar
    allow_short: bool = True         # permitir cortos o no


class SqueezeMomentumStrategy(BaseStrategy):
    def __init__(self, config: SqueezeMomentumConfig) -> None:
        self.config = config

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Devuelve un DataFrame con:
        - columnas originales (timestamp, open, high, low, close, volume si existe)
        - columnas técnicas: bb_mid/up/low, kc_mid/up/low, atr, momentum, squeeze_on
        - columna 'signal' con valores {1, -1, 0}
        """
        required = {"timestamp", "open", "high", "low", "close"}
        if not required.issubset(df.columns):
            missing = required - set(df.columns)
            raise ValueError(f"Faltan columnas necesarias en el DataFrame de entrada: {missing}")

        data = df.sort_values("timestamp").reset_index(drop=True).copy()

        close = data["close"]
        high = data["high"]
        low = data["low"]

        # === ATR ===
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        data["atr"] = (
            true_range.rolling(self.config.atr_window, min_periods=self.config.atr_window)
            .mean()
        )

        # Umbral de ATR (percentil global)
        atr_valid = data["atr"].dropna()
        if len(atr_valid) > 0:
            atr_threshold = atr_valid.quantile(self.config.atr_min_percentile)
        else:
            atr_threshold = np.nan

        # === Bandas de Bollinger ===
        bb_mid = close.rolling(self.config.bb_window, min_periods=self.config.bb_window).mean()
        bb_std = close.rolling(self.config.bb_window, min_periods=self.config.bb_window).std(ddof=0)

        data["bb_mid"] = bb_mid
        data["bb_up"] = bb_mid + self.config.bb_mult * bb_std
        data["bb_low"] = bb_mid - self.config.bb_mult * bb_std

        # === Keltner Channels ===
        kc_mid = close.rolling(self.config.kc_window, min_periods=self.config.kc_window).mean()
        data["kc_mid"] = kc_mid
        data["kc_up"] = kc_mid + self.config.kc_mult * data["atr"]
        data["kc_low"] = kc_mid - self.config.kc_mult * data["atr"]

        # === Estado de squeeze ===
        squeeze_on = (
            (data["bb_up"] < data["kc_up"]) &
            (data["bb_low"] > data["kc_low"])
        )
        squeeze_on = squeeze_on.fillna(False)
        data["squeeze_on"] = squeeze_on

        # contador de velas consecutivas en squeeze
        squeeze_count = []
        count = 0
        for is_sq in squeeze_on:
            if is_sq:
                count += 1
            else:
                count = 0
            squeeze_count.append(count)
        data["squeeze_count"] = squeeze_count

        # squeeze se libera cuando pasa de ON -> OFF
        # shift con fill_value evita warnings de downcasting en pandas>=2.2
        just_released = (~squeeze_on) & squeeze_on.shift(1, fill_value=False)
        enough_squeeze = (
            data["squeeze_count"].shift(1, fill_value=0) >= self.config.min_squeeze_bars
        )

        # === Momentum (muy simplificado) ===
        mom_mean = close.rolling(self.config.mom_window, min_periods=self.config.mom_window).mean()
        momentum = close - mom_mean
        mom_slope = momentum.diff()

        data["momentum"] = momentum
        data["momentum_slope"] = mom_slope

        long_mom = (momentum > 0) & (mom_slope > 0)
        short_mom = (momentum < 0) & (mom_slope < 0)

        # Filtro ATR: solo operar si ATR por encima del umbral
        if not np.isnan(atr_threshold):
            high_vol = data["atr"] > atr_threshold
        else:
            high_vol = pd.Series(True, index=data.index)

        # === Señales ===
        signal = np.zeros(len(data), dtype=int)

        base_cond = just_released & enough_squeeze & high_vol

        long_cond = base_cond & long_mom
        short_cond = base_cond & short_mom & self.config.allow_short

        signal[long_cond] = 1
        signal[short_cond] = -1

        data["signal"] = signal.astype(int)

        return data
