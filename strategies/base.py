# strategies/base.py

from abc import ABC, abstractmethod

import pandas as pd


class BaseStrategy(ABC):
    """
    Interfaz base para cualquier estrategia.

    Cualquier estrategia debe:
    - Tener un atributo 'name' para identificarla.
    - Implementar generate_signals(df) -> df_con_signal
    """

    name: str = "BaseStrategy"

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Debe devolver un DataFrame con al menos una columna 'signal'
        con valores en {1, -1, 0}.
        """
        raise NotImplementedError
