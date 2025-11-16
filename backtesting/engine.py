# backtesting/engine.py

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np
import pandas as pd

from utils.risk import RiskManagementConfig, calculate_position_size_spot


@dataclass
class BacktestConfig:
    initial_capital: float
    sl_pct: Optional[float] = 0.01      # stop loss fijo (puede ser None)
    tp_rr: Optional[float] = 2.0        # ratio TP:SL (solo si sl_pct no es None)
    fee_pct: float = 0.0005
    allow_short: bool = True

    # Parámetros ATR opcionales
    atr_window: Optional[int] = None    # si None, no se exige columna 'atr'
    atr_mult_sl: Optional[float] = None # si no es None -> usar ATR para SL
    atr_mult_tp: Optional[float] = None # idem para TP


def compute_sl_tp(
    cfg: BacktestConfig,
    side: str,
    entry_price: float,
    atr: float | None,
) -> tuple[float, float]:
    """
    Calcula SL y TP según la configuración:
    - Si cfg.atr_mult_sl no es None -> usa ATR.
    - Si no -> usa sl_pct y tp_rr.

    side: "long" o "short".
    """
    # Modo ATR dinámico
    if cfg.atr_mult_sl is not None and cfg.atr_mult_tp is not None:
        if atr is None or np.isnan(atr):
            raise ValueError(
                "Se ha solicitado usar ATR para SL/TP, pero no hay columna 'atr' válida en el DataFrame."
            )

        if side == "long":
            sl_price = entry_price - atr * cfg.atr_mult_sl
            tp_price = entry_price + atr * cfg.atr_mult_tp
        else:  # short
            sl_price = entry_price + atr * cfg.atr_mult_sl
            tp_price = entry_price - atr * cfg.atr_mult_tp

        return sl_price, tp_price

    # Modo SL fijo por porcentaje
    if cfg.sl_pct is None or cfg.tp_rr is None:
        raise ValueError(
            "Ni ATR ni SL fijo están correctamente configurados. "
            "Configura atr_mult_sl/atr_mult_tp o sl_pct/tp_rr."
        )

    if side == "long":
        sl_price = entry_price * (1.0 - cfg.sl_pct)
        tp_price = entry_price * (1.0 + cfg.sl_pct * cfg.tp_rr)
    else:  # short
        sl_price = entry_price * (1.0 + cfg.sl_pct)
        tp_price = entry_price * (1.0 - cfg.sl_pct * cfg.tp_rr)

    return sl_price, tp_price


@dataclass
class Trade:
    """
    Representa una operación individual.
    """
    entry_time: pd.Timestamp
    exit_time: Optional[pd.Timestamp]
    direction: str  # "long" o "short"
    entry_price: float
    exit_price: Optional[float]
    size: float
    stop_price: float
    tp_price: float
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None


@dataclass
class BacktestResult:
    """
    Resultado del backtest.
    """
    trades: List[Trade] = field(default_factory=list)
    equity_curve: pd.Series | None = None
    total_return_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    winrate_pct: float = 0.0
    profit_factor: float = 0.0
    num_trades: int = 0


class Backtester:
    """
    Motor de backtesting simple basado en señales:
    - Usa la columna 'signal' (1, -1, 0) del DataFrame.
    - Usa reglas de SL/TP basadas en porcentaje o ATR dinámico.
    - Usa gestión de riesgo separada (utils.risk).
    """

    def __init__(
        self,
        backtest_config: BacktestConfig,
        risk_config: RiskManagementConfig,
    ) -> None:
        if backtest_config is None:
            raise ValueError("backtest_config no puede ser None")
        if risk_config is None:
            raise ValueError("risk_config no puede ser None")

        self.backtest_config = backtest_config
        self.risk_config = risk_config

    def run(self, df: pd.DataFrame) -> BacktestResult:
        """
        Ejecuta el backtest sobre un DataFrame que debe contener al menos:
        - timestamp
        - open
        - high
        - low
        - close
        - signal

        Si se usan parámetros ATR (atr_mult_*), el DataFrame debe tener una
        columna 'atr' coherente con atr_window (esto se comprueba en compute_sl_tp).

        Devuelve un BacktestResult con trades, equity curve y métricas.
        """
        required_cols = {"timestamp", "open", "high", "low", "close", "signal"}
        if not required_cols.issubset(df.columns):
            missing = required_cols - set(df.columns)
            raise ValueError(f"Faltan columnas necesarias en el DataFrame: {missing}")

        # Ordenamos por tiempo y reseteamos índice
        data = df.sort_values("timestamp").reset_index(drop=True).copy()

        cfg = self.backtest_config

        capital = cfg.initial_capital
        equity_list: List[float] = []
        equity_times: List[pd.Timestamp] = []
        trades: List[Trade] = []

        open_trade: Optional[Trade] = None

        for i in range(len(data)):
            row = data.iloc[i]
            timestamp = row["timestamp"]
            close = float(row["close"])
            high = float(row["high"])
            low = float(row["low"])
            signal = int(row["signal"])

            # ATR actual (si existe)
            atr_value = None
            if "atr" in row.index:
                atr_value = float(row["atr"])

            # 1) Actualizar trade abierto (si lo hay)
            if open_trade is not None:
                exit_price = None
                reason = None

                if open_trade.direction == "long":
                    # Conservador: primero SL, luego TP
                    hit_sl = low <= open_trade.stop_price
                    hit_tp = high >= open_trade.tp_price

                    if hit_sl:
                        exit_price = open_trade.stop_price
                        reason = "SL"
                    elif hit_tp:
                        exit_price = open_trade.tp_price
                        reason = "TP"

                else:  # short
                    # Para cortos, SL si el precio sube hasta stop; TP si baja hasta tp
                    hit_sl = high >= open_trade.stop_price
                    hit_tp = low <= open_trade.tp_price

                    if hit_sl:
                        exit_price = open_trade.stop_price
                        reason = "SL"
                    elif hit_tp:
                        exit_price = open_trade.tp_price
                        reason = "TP"

                if exit_price is not None:
                    # Cerrar trade
                    if open_trade.direction == "long":
                        pnl = (exit_price - open_trade.entry_price) * open_trade.size
                    else:
                        pnl = (open_trade.entry_price - exit_price) * open_trade.size

                    # Comisiones: entrada (ya descontada) + salida
                    fee_exit = exit_price * open_trade.size * cfg.fee_pct
                    pnl_after_fees = pnl - fee_exit

                    capital += pnl_after_fees

                    open_trade.exit_time = timestamp
                    open_trade.exit_price = exit_price
                    open_trade.pnl = pnl_after_fees
                    open_trade.pnl_pct = pnl_after_fees / cfg.initial_capital * 100.0

                    trades.append(open_trade)
                    # print(f"Closed {open_trade.direction} at {exit_price} ({reason}), PnL: {pnl_after_fees:.2f}")

                    open_trade = None

            # Registramos equity tras gestionar el posible cierre
            equity_list.append(capital)
            equity_times.append(timestamp)

            # 2) Gestionar nuevas entradas según 'signal'
            #    Solo si NO hay trade abierto
            if open_trade is None and signal != 0:
                if signal == 1:
                    direction = "long"
                elif signal == -1 and cfg.allow_short:
                    direction = "short"
                else:
                    direction = None

                if direction is not None:
                    entry_price = close

                    # Calcular SL/TP dinámico (ATR o fijo) según config
                    sl_price, tp_price = compute_sl_tp(
                        cfg=cfg,
                        side=direction,
                        entry_price=entry_price,
                        atr=atr_value,
                    )

                    # Tamaño de la posición en unidades
                    size = calculate_position_size_spot(
                        capital=capital,
                        entry_price=entry_price,
                        stop_price=sl_price,
                        config=self.risk_config,
                    )

                    if size > 0:
                        # Comisión de entrada
                        fee_entry = entry_price * size * cfg.fee_pct
                        capital -= fee_entry  # restamos comisión de entrada

                        open_trade = Trade(
                            entry_time=timestamp,
                            exit_time=None,
                            direction=direction,
                            entry_price=entry_price,
                            exit_price=None,
                            size=size,
                            stop_price=sl_price,
                            tp_price=tp_price,
                        )
                        # print(f"Opened {direction} at {entry_price}, size {size:.6f}")

        # Equity curve
        equity_series = pd.Series(equity_list, index=pd.to_datetime(equity_times))

        # Cálculo de métricas
        result = self._calculate_metrics(trades, equity_series)
        return result

    def _calculate_metrics(
        self,
        trades: List[Trade],
        equity_curve: pd.Series,
    ) -> BacktestResult:
        """
        Calcula métricas básicas a partir de la lista de trades y la equity curve.
        """
        num_trades = len(trades)

        if len(equity_curve) == 0:
            total_return_pct = 0.0
        else:
            initial = equity_curve.iloc[0]
            final = equity_curve.iloc[-1]
            total_return_pct = (final / initial - 1.0) * 100.0

        # Max drawdown
        if len(equity_curve) > 0:
            running_max = equity_curve.cummax()
            drawdown = (equity_curve - running_max) / running_max
            max_drawdown_pct = drawdown.min() * 100.0
        else:
            max_drawdown_pct = 0.0

        # Winrate y profit factor
        pnl_list = [t.pnl for t in trades if t.pnl is not None]
        pnl_array = np.array(pnl_list) if pnl_list else np.array([])

        if len(pnl_array) > 0:
            wins = pnl_array[pnl_array > 0]
            losses = pnl_array[pnl_array < 0]

            winrate_pct = (len(wins) / len(pnl_array)) * 100.0 if len(pnl_array) > 0 else 0.0
            gross_profit = wins.sum() if len(wins) > 0 else 0.0
            gross_loss = losses.sum() if len(losses) > 0 else 0.0

            if gross_loss < 0:
                profit_factor = gross_profit / abs(gross_loss) if abs(gross_loss) > 0 else np.nan
            else:
                profit_factor = np.nan
        else:
            winrate_pct = 0.0
            profit_factor = 0.0

        return BacktestResult(
            trades=trades,
            equity_curve=equity_curve,
            total_return_pct=total_return_pct,
            max_drawdown_pct=max_drawdown_pct,
            winrate_pct=winrate_pct,
            profit_factor=profit_factor,
            num_trades=num_trades,
        )
