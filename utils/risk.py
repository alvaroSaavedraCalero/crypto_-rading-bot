# utils/risk.py

from dataclasses import dataclass


@dataclass
class RiskManagementConfig:
    """
    Configuración de gestión de riesgo para cada operación.
    """
    risk_pct: float = 0.01  # 1% del capital por operación


def calculate_position_size_spot(
    capital: float,
    entry_price: float,
    stop_price: float,
    config: RiskManagementConfig | None = None,
) -> float:
    """
    Calcula el tamaño de la posición (en unidades del activo, ej. BTC)
    para arriesgar un porcentaje fijo del capital en función del stop.

    Fórmula:
        riesgo_monetario = capital * risk_pct
        riesgo_por_unidad = |entry_price - stop_price|
        tamaño = riesgo_monetario / riesgo_por_unidad

    Devuelve:
        tamaño de la posición (float). Si no se puede calcular, devuelve 0.
    """
    if config is None:
        config = RiskManagementConfig()

    if capital <= 0:
        return 0.0

    risk_amount = capital * config.risk_pct
    risk_per_unit = abs(entry_price - stop_price)

    if risk_per_unit <= 0:
        # Evitar divisiones por cero o stops iguales al entry
        return 0.0

    position_size = risk_amount / risk_per_unit
    return position_size
