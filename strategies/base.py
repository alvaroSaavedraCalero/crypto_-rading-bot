# strategies/base.py

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar

import pandas as pd

ConfigT = TypeVar("ConfigT")


@dataclass
class StrategyMetadata:
    """
    Información genérica de una estrategia.
    Se puede usar más adelante para logs, monitorización, etc.
    """
    name: str
    symbol: str | None = None
    timeframe: str | None = None


class BaseStrategy(ABC, Generic[ConfigT]):
    """
    Clase base para todas las estrategias.

    Requisitos mínimos:
    - Recibir un objeto de configuración (dataclass normalmente).
    - Exponer un método generate_signals(df) -> df_con_signal.
    - Opcionalmente, poder devolver la última señal con generate_last_signal().
    """

    def __init__(self, config: ConfigT, meta: StrategyMetadata | None = None) -> None:
        self.config: ConfigT = config
        # meta es opcional; si no se pasa, se construye con el nombre de la clase
        self.meta: StrategyMetadata = meta or StrategyMetadata(name=self.__class__.__name__)

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Debe:
        - NO modificar el df original (trabajar sobre una copia o usar assign).
        - Añadir al menos una columna 'signal' (1, -1, 0).
        - Devolver el DataFrame resultante.
        """
        raise NotImplementedError

    def generate_last_signal(self, df: pd.DataFrame) -> int:
        """
        Helper para escenarios en vivo:
        - Calcula señales sobre el df.
        - Devuelve solo la última señal (int).
        """
        df_out = self.generate_signals(df)

        if df_out.empty or "signal" not in df_out.columns:
            return 0

        sig = df_out["signal"].iloc[-1]
        try:
            return int(sig)
        except Exception:
            return 0

    def required_columns(self) -> set[str]:
        """
        Columnas mínimas que la estrategia espera encontrar en el DataFrame de entrada.
        Por defecto: OHLCV estándar.
        Las estrategias pueden sobreescribirlo si necesitan más.
        """
        return {"timestamp", "open", "high", "low", "close", "volume"}