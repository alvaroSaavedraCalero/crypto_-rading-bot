# strategies/macd_adx_trend_strategy.py

from dataclasses import dataclass
from typing import Literal

from .base import BaseStrategy, StrategyMetadata

import numpy as np
import pandas as pd


@dataclass
class MACDADXTrendStrategyConfig:
    # MACD
    fast_ema: int = 12
    slow_ema: int = 26
    signal_ema: int = 9

    # Filtro de tendencia
    trend_ema_window: int = 200      # EMA para definir tendencia principal

    # ADX (fuerza de tendencia)
    adx_window: int = 14
    adx_threshold: float = 20.0      # mínimo para considerar tendencia “fuerte”

    # Gestión de señales
    allow_short: bool = True        # permitir cortos o no


class MACDADXTrendStrategy(BaseStrategy[MACDADXTrendStrategyConfig]):
    """
    Estrategia de momentum basada en:
    - Filtro de tendencia con EMA (trend_ema_window)
    - MACD (cruces de línea MACD vs señal)
    - ADX (tendencia suficientemente fuerte)
    """

    def __init__(self, config: MACDADXTrendStrategyConfig, meta: StrategyMetadata | None = None):
        super().__init__(config=config, meta=meta)

    # ========================
    # Cálculo de indicadores
    # ========================

    @staticmethod
    def _ema(series: pd.Series, window: int) -> pd.Series:
        return series.ewm(span=window, adjust=False).mean()

    @staticmethod
    def _compute_macd(
        close: pd.Series,
        fast: int,
        slow: int,
        signal: int,
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal, adjust=False).mean()
        macd_hist = macd - macd_signal
        return macd, macd_signal, macd_hist

    @staticmethod
    def _compute_adx(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        window: int,
    ) -> pd.Series:
        """
        Cálculo típico de ADX usando fórmulas tipo Wilder.
        """
        high_shift = high.shift(1)
        low_shift = low.shift(1)
        close_shift = close.shift(1)

        up_move = high - high_shift
        down_move = low_shift - low

        plus_dm = np.where(
            (up_move > down_move) & (up_move > 0),
            up_move,
            0.0,
        )
        minus_dm = np.where(
            (down_move > up_move) & (down_move > 0),
            down_move,
            0.0,
        )

        plus_dm = pd.Series(plus_dm, index=high.index)
        minus_dm = pd.Series(minus_dm, index=high.index)

        tr1 = high - low
        tr2 = (high - close_shift).abs()
        tr3 = (low - close_shift).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Usamos ewm como aproximación al smoothing de Wilder
        atr = tr.ewm(alpha=1.0 / window, adjust=False).mean()
        plus_di = 100.0 * (plus_dm.ewm(alpha=1.0 / window, adjust=False).mean() / atr)
        minus_di = 100.0 * (minus_dm.ewm(alpha=1.0 / window, adjust=False).mean() / atr)

        dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
        adx = dx.ewm(alpha=1.0 / window, adjust=False).mean()

        return adx

    # ========================
    # Generación de señales
    # ========================

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Recibe un DataFrame con columnas:
        - timestamp
        - open, high, low, close, volume

        Devuelve una copia con columnas adicionales:
        - ema_trend
        - macd, macd_signal, macd_hist
        - adx
        - signal (1 = long, -1 = short, 0 = no operar)
        """
        required_cols = {"timestamp", "open", "high", "low", "close"}
        if not required_cols.issubset(df.columns):
            missing = required_cols - set(df.columns)
            raise ValueError(f"Faltan columnas necesarias en el DataFrame: {missing}")

        data = df.sort_values("timestamp").reset_index(drop=True).copy()

        # Filtro de tendencia
        data["ema_trend"] = self._ema(
            data["close"],
            window=self.config.trend_ema_window,
        )

        # MACD
        macd, macd_signal, macd_hist = self._compute_macd(
            close=data["close"],
            fast=self.config.fast_ema,
            slow=self.config.slow_ema,
            signal=self.config.signal_ema,
        )
        data["macd"] = macd
        data["macd_signal"] = macd_signal
        data["macd_hist"] = macd_hist

        # ADX
        data["adx"] = self._compute_adx(
            high=data["high"],
            low=data["low"],
            close=data["close"],
            window=self.config.adx_window,
        )

        # Señales
        data["signal"] = 0

        # Condición de tendencia
        trend_long = data["close"] > data["ema_trend"]
        trend_short = data["close"] < data["ema_trend"]

        # Filtro ADX
        strong_trend = data["adx"] >= self.config.adx_threshold

        # Cruce MACD alcista: MACD cruza por encima de la señal
        macd_cross_up = (data["macd"] > data["macd_signal"]) & (
            data["macd"].shift(1) <= data["macd_signal"].shift(1)
        )

        # Cruce MACD bajista
        macd_cross_down = (data["macd"] < data["macd_signal"]) & (
            data["macd"].shift(1) >= data["macd_signal"].shift(1)
        )

        # Longs: tendencia alcista + MACD cruce alcista + ADX fuerte
        long_cond = trend_long & strong_trend & macd_cross_up

        # Shorts: tendencia bajista + MACD cruce bajista + ADX fuerte
        short_cond = trend_short & strong_trend & macd_cross_down

        data.loc[long_cond, "signal"] = 1

        if self.config.allow_short:
            data.loc[short_cond, "signal"] = -1

        return data