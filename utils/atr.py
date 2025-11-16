# utils/atr.py

import pandas as pd
import ta


def add_atr(df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    """
    Añade la columna 'atr' al DataFrame usando Average True Range (ATR).
    No modifica el DataFrame original, devuelve una copia.
    """
    data = df.copy()

    atr_ind = ta.volatility.AverageTrueRange(
        high=data["high"],
        low=data["low"],
        close=data["close"],
        window=window,
    )
    data["atr"] = atr_ind.average_true_range()

    return data
