# execution/models.py

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List

import pandas as pd


class Side(str, Enum):
    LONG = "long"
    SHORT = "short"


@dataclass
class Position:
    symbol: str
    side: Side
    entry_time: pd.Timestamp
    entry_price: float
    size: float
    stop_price: float
    tp_price: float


@dataclass
class TradeLogEntry:
    symbol: str
    side: Side
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    entry_price: float
    exit_price: float
    size: float
    pnl: float
    pnl_pct: float
    reason: str  # "SL" / "TP" / "MANUAL" / etc.


@dataclass
class AccountState:
    """
    Estado de la cuenta para paper trading.
    Por simplicidad:
    - capital: efectivo disponible
    - equity: capital + PnL no realizado (aquí lo igualamos a capital)
    - open_positions: máximo 1 por símbolo
    """
    capital: float
    equity: float
    open_positions: Dict[str, Position] = field(default_factory=dict)
    history: List[TradeLogEntry] = field(default_factory=list)