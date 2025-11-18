# strategies/keltner_breakout_strategy.py

from dataclasses import dataclass
from typing import Literal

from .base import BaseStrategy, StrategyMetadata

import numpy as np
import pandas as pd


@dataclass
class KeltnerBreakoutStrategyConfig:
    # Canal Keltner
    kc_window: int = 20          # periodo de la media
    kc_mult: float = 1.5         # multiplicador de ATR para las bandas

    # ATR para volatilidad y canal
    atr_window: int = 14
    atr_min_percentile: float = 0.2  # filtra velas con muy baja volatilidad (0–1)

    # Filtro de tendencia
    use_trend_filter: bool = True
    trend_ema_window: int = 100

    # Dirección
    allow_short: bool = True     # si queremos también romper a la baja
    side_mode: Literal["both", "long_only", "short_only"] = "both"


class KeltnerBreakoutStrategy(BaseStrategy[KeltnerBreakoutStrategyConfig]):
    """
    Estrategia de breakout de volatilidad basada en:
    - Canal de Keltner (EMA + ATR * mult)
    - Filtro de volatilidad mínima (percentil de ATR)
    - Filtro de tendencia opcional (EMA de tendencia)

    Señales:
    - Long: cierre cruza por encima de la banda superior del canal
            + volatilidad mínima
            + tendencia alcista (opcional)
    - Short: análogo con banda inferior (si allow_short=True)
    """

    def __init__(self, config: KeltnerBreakoutStrategyConfig, meta: StrategyMetadata | None = None):
        super().__init__(config=config, meta=meta)

    @staticmethod
    def _ema(series: pd.Series, window: int) -> pd.Series:
        return series.ewm(span=window, adjust=False).mean()

    @staticmethod
    def _atr(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        window: int,
    ) -> pd.Series:
        close_shift = close.shift(1)
        tr1 = high - low
        tr2 = (high - close_shift).abs()
        tr3 = (low - close_shift).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.ewm(alpha=1.0 / window, adjust=False).mean()
        return atr

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        required_cols = {"timestamp", "open", "high", "low", "close"}
        if not required_cols.issubset(df.columns):
            missing = required_cols - set(df.columns)
            raise ValueError(f"Faltan columnas necesarias en el DataFrame: {missing}")

        data = df.sort_values("timestamp").reset_index(drop=True).copy()

        # ATR
        data["atr"] = self._atr(
            high=data["high"],
            low=data["low"],
            close=data["close"],
            window=self.config.atr_window,
        )

        # Media central del canal Keltner (EMA del close)
        data["kc_mid"] = self._ema(data["close"], window=self.config.kc_window)
        data["kc_upper"] = data["kc_mid"] + self.config.kc_mult * data["atr"]
        data["kc_lower"] = data["kc_mid"] - self.config.kc_mult * data["atr"]

        # Filtro de volatilidad mínima basado en percentil del ATR
        if 0.0 <= self.config.atr_min_percentile < 1.0:
            threshold = data["atr"].quantile(self.config.atr_min_percentile)
            data["atr_ok"] = data["atr"] >= threshold
        else:
            data["atr_ok"] = True

        # Filtro de tendencia (opcional)
        if self.config.use_trend_filter:
            data["ema_trend"] = self._ema(
                data["close"],
                window=self.config.trend_ema_window,
            )
            trend_long = data["close"] > data["ema_trend"]
            trend_short = data["close"] < data["ema_trend"]
        else:
            trend_long = pd.Series(True, index=data.index)
            trend_short = pd.Series(True, index=data.index)

        # Cruces de breakout
        # Long: close cruza desde abajo a arriba la banda superior
        close = data["close"]
        upper = data["kc_upper"]
        lower = data["kc_lower"]

        cross_up = (close > upper) & (close.shift(1) <= upper.shift(1))
        cross_down = (close < lower) & (close.shift(1) >= lower.shift(1))

        data["signal"] = 0

        # Longs
        long_cond = cross_up & data["atr_ok"] & trend_long
        if self.config.side_mode in ("both", "long_only"):
            data.loc[long_cond, "signal"] = 1

        # Shorts
        short_cond = cross_down & data["atr_ok"] & trend_short
        if self.config.allow_short and self.config.side_mode in ("both", "short_only"):
            data.loc[short_cond, "signal"] = -1

        return data