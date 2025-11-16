# strategies/rsi_reversion_strategy.py

from dataclasses import dataclass

import pandas as pd
import ta

from strategies.base import BaseStrategy


@dataclass
class RSIReversionStrategyConfig:
    rsi_window: int = 14
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    allow_short: bool = True  # si False, solo abre largos en sobreventa


class RSIReversionStrategy(BaseStrategy):
    """
    Estrategia de reversión a la media basada en RSI.

    Reglas:
    - RSI < rsi_oversold  -> signal = 1 (entrada larga)
    - RSI > rsi_overbought:
        - si allow_short: signal = -1 (entrada corta)
        - si no: signal = 0 (podrías usarlo para cerrar largos en backtester más avanzado)
    """

    name: str = "RSI_Reversion"

    def __init__(self, config: RSIReversionStrategyConfig | None = None) -> None:
        self.config = config or RSIReversionStrategyConfig()

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        required_cols = {"timestamp", "open", "high", "low", "close", "volume"}
        if not required_cols.issubset(df.columns):
            missing = required_cols - set(df.columns)
            raise ValueError(f"Faltan columnas necesarias en el DataFrame: {missing}")

        data = df.copy()

        rsi_indicator = ta.momentum.RSIIndicator(
            close=data["close"],
            window=self.config.rsi_window,
        )
        data["rsi"] = rsi_indicator.rsi()

        data["signal"] = 0

        oversold = data["rsi"] < self.config.rsi_oversold
        overbought = data["rsi"] > self.config.rsi_overbought

        # Entradas largas en sobreventa
        data.loc[oversold, "signal"] = 1

        # Entradas cortas en sobrecompra si se permite
        if self.config.allow_short:
            data.loc[overbought, "signal"] = -1

        return data
