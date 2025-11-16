# strategies/donchian_breakout_strategy.py

from dataclasses import dataclass

import pandas as pd

from strategies.base import BaseStrategy


@dataclass
class DonchianBreakoutStrategyConfig:
    channel_window: int = 20  # número de velas para el canal
    allow_short: bool = True


class DonchianBreakoutStrategy(BaseStrategy):
    """
    Estrategia de breakout basada en canales de Donchian (máximos/mínimos N-periodos).

    Reglas:
    - close > max(high últimos N, excluyendo la vela actual)  -> signal = 1
    - close < min(low últimos N, excluyendo la vela actual)   -> signal = -1 (si allow_short)
    """

    name: str = "Donchian_Breakout"

    def __init__(self, config: DonchianBreakoutStrategyConfig | None = None) -> None:
        self.config = config or DonchianBreakoutStrategyConfig()

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        required_cols = {"timestamp", "open", "high", "low", "close", "volume"}
        if not required_cols.issubset(df.columns):
            missing = required_cols - set(df.columns)
            raise ValueError(f"Faltan columnas necesarias en el DataFrame: {missing}")

        data = df.copy()

        w = self.config.channel_window

        # Canal calculado sobre las N velas anteriores (shift(1))
        data["donchian_high"] = (
            data["high"]
            .rolling(window=w, min_periods=w)
            .max()
            .shift(1)
        )
        data["donchian_low"] = (
            data["low"]
            .rolling(window=w, min_periods=w)
            .min()
            .shift(1)
        )

        data["signal"] = 0

        # Solo podemos generar señal donde el canal está definido
        valid = data["donchian_high"].notna() & data["donchian_low"].notna()

        breakout_up = valid & (data["close"] > data["donchian_high"])
        breakout_down = valid & (data["close"] < data["donchian_low"])

        data.loc[breakout_up, "signal"] = 1

        if self.config.allow_short:
            data.loc[breakout_down, "signal"] = -1

        return data
