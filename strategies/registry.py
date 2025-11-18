# strategies/registry.py

from __future__ import annotations

from typing import Dict, Tuple, Type

from .base import BaseStrategy
from .ma_rsi_strategy import (
    MovingAverageRSIStrategy,
    MovingAverageRSIStrategyConfig,
)
from .macd_adx_trend_strategy import (
    MACDADXTrendStrategy,
    MACDADXTrendStrategyConfig,
)
from .keltner_breakout_strategy import (
    KeltnerBreakoutStrategy,
    KeltnerBreakoutStrategyConfig,
)
from strategies.archived.bb_trend_strategy import BBTrendStrategy, BBTrendStrategyConfig

# Mapa: tipo_de_estrategia -> (ClaseEstrategia, ClaseConfig)
# Los strings deben coincidir con los strategy_type que usas en config/settings.py
STRATEGY_REGISTRY: Dict[str, Tuple[Type[BaseStrategy], Type]] = {
    "MA_RSI": (MovingAverageRSIStrategy, MovingAverageRSIStrategyConfig),
    "MACD_ADX": (MACDADXTrendStrategy, MACDADXTrendStrategyConfig),
    "KELTNER": (KeltnerBreakoutStrategy, KeltnerBreakoutStrategyConfig),
    "BB_TREND": (BBTrendStrategy, BBTrendStrategyConfig),
}


def create_strategy(strategy_type: str, config_obj) -> BaseStrategy:
    """
    Factory sencillo: recibe un tipo ('MA_RSI', 'MACD_ADX', 'KELTNER')
    y un objeto de configuración ya construido, y devuelve la instancia
    de la estrategia correspondiente.

    Ejemplo:
        strat = create_strategy("MA_RSI", MA_RSI_BTC15M_CONFIG)
    """
    try:
        strategy_cls, cfg_cls = STRATEGY_REGISTRY[strategy_type]
    except KeyError:
        raise ValueError(f"Estrategia no registrada: {strategy_type!r}")

    if not isinstance(config_obj, cfg_cls):
        raise TypeError(
            f"Config no válida para {strategy_type}. "
            f"Esperado {cfg_cls.__name__}, recibido {type(config_obj).__name__}."
        )

    return strategy_cls(config=config_obj)