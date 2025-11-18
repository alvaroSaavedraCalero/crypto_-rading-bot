# execution/paper_broker.py

from __future__ import annotations

from typing import Optional, List

import numpy as np
import pandas as pd

from backtesting.engine import BacktestConfig, compute_sl_tp
from execution.models import AccountState, Position, Side, TradeLogEntry
from utils.risk import RiskManagementConfig, calculate_position_size_spot


class PaperBroker:
    """
    Broker de paper trading muy simple:
    - Solo spot.
    - Máximo 1 posición abierta por símbolo.
    - SL/TP según BacktestConfig (sl_pct/tp_rr o ATR si se configura).
    - Comisiones según BacktestConfig.fee_pct.
    - Slippage y spread configurables:
        * spread_pct: se reparte mitad-mitad entre bid/ask en la entrada.
        * slippage_pct: empeora el precio de entrada y el de salida
          en el sentido contrario a tu operación.
    """

    def __init__(
        self,
        symbol: str,
        backtest_config: BacktestConfig,
        risk_config: RiskManagementConfig,
        slippage_pct: float = 0.0,   # p.ej. 0.0005 = 0.05%
        spread_pct: float = 0.0,     # p.ej. 0.0005 = 0.05%
    ) -> None:
        self.symbol = symbol
        self.bt_cfg = backtest_config
        self.risk_cfg = risk_config

        self.slippage_pct = slippage_pct
        self.spread_pct = spread_pct

        self.state = AccountState(
            capital=self.bt_cfg.initial_capital,
            equity=self.bt_cfg.initial_capital,
        )

        # Para poder calcular métricas luego
        self._equity_times: List[pd.Timestamp] = []
        self._equity_values: List[float] = []

    # ------------------------------------------------------------------ #
    #  MÉTODOS PÚBLICOS
    # ------------------------------------------------------------------ #

    def on_bar(self, row: pd.Series, signal: int, atr_value: Optional[float] = None) -> None:
        """
        Procesa una vela (row) y una señal asociada:
        - row: debe tener timestamp, high, low, close
        - signal: 1 (long), -1 (short), 0 (nada)
        - atr_value: opcional, por si quieres usar ATR para SL/TP
        """
        ts = pd.to_datetime(row["timestamp"])
        high = float(row["high"])
        low = float(row["low"])
        close = float(row["close"])

        # 1) Gestionar cierre de posición abierta (SL / TP)
        self._process_existing_position(ts, high, low)

        # 2) Registrar equity tras el posible cierre
        self._equity_times.append(ts)
        self._equity_values.append(self.state.capital)  # sin PnL no realizado

        # 3) Gestionar nuevas entradas
        if signal != 0:
            self._maybe_open_position(ts, close, signal, atr_value)

    def get_equity_series(self) -> pd.Series:
        if not self._equity_times:
            return pd.Series(dtype=float)
        return pd.Series(self._equity_values, index=pd.to_datetime(self._equity_times))

    def print_summary(self) -> None:
        """
        Imprime métricas similares al backtester.
        """
        trades = self.state.history
        equity_curve = self.get_equity_series()

        num_trades = len(trades)

        if len(equity_curve) == 0:
            total_return_pct = 0.0
            max_drawdown_pct = 0.0
        else:
            initial = equity_curve.iloc[0]
            final = equity_curve.iloc[-1]
            total_return_pct = (final / initial - 1.0) * 100.0

            running_max = equity_curve.cummax()
            drawdown = (equity_curve - running_max) / running_max
            max_drawdown_pct = drawdown.min() * 100.0

        pnl_array = np.array([t.pnl for t in trades]) if trades else np.array([])

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

        print("\n===== RESUMEN PAPER TRADING =====")
        print(f"Número de trades: {num_trades}")
        print(f"Retorno total: {total_return_pct:.2f} %")
        print(f"Max drawdown: {max_drawdown_pct:.2f} %")
        print(f"Winrate: {winrate_pct:.2f} %")
        print(f"Profit factor: {profit_factor:.2f}")

    # ------------------------------------------------------------------ #
    #  MÉTODOS PRIVADOS
    # ------------------------------------------------------------------ #

    def _process_existing_position(
        self,
        ts: pd.Timestamp,
        high: float,
        low: float,
    ) -> None:
        pos = self.state.open_positions.get(self.symbol)
        if pos is None:
            return

        hit_sl = False
        hit_tp = False
        raw_exit_price = None
        reason = ""

        if pos.side == Side.LONG:
            hit_sl = low <= pos.stop_price
            hit_tp = high >= pos.tp_price
            if hit_sl:
                raw_exit_price = pos.stop_price
                reason = "SL"
            elif hit_tp:
                raw_exit_price = pos.tp_price
                reason = "TP"
        else:  # SHORT
            hit_sl = high >= pos.stop_price
            hit_tp = low <= pos.tp_price
            if hit_sl:
                raw_exit_price = pos.stop_price
                reason = "SL"
            elif hit_tp:
                raw_exit_price = pos.tp_price
                reason = "TP"

        if raw_exit_price is None:
            return

        # Aplicar slippage en la salida (siempre en contra de la posición)
        if self.slippage_pct > 0.0:
            if pos.side == Side.LONG:
                exit_price = raw_exit_price * (1.0 - self.slippage_pct)
            else:  # SHORT
                exit_price = raw_exit_price * (1.0 + self.slippage_pct)
        else:
            exit_price = raw_exit_price

        # Cálculo de PnL
        if pos.side == Side.LONG:
            pnl = (exit_price - pos.entry_price) * pos.size
        else:
            pnl = (pos.entry_price - exit_price) * pos.size

        fee_entry = pos.entry_price * pos.size * self.bt_cfg.fee_pct
        fee_exit = exit_price * pos.size * self.bt_cfg.fee_pct
        pnl_after_fees = pnl - fee_entry - fee_exit

        self.state.capital += pnl_after_fees
        self.state.equity = self.state.capital

        pnl_pct = pnl_after_fees / self.bt_cfg.initial_capital * 100.0

        trade_log = TradeLogEntry(
            symbol=self.symbol,
            side=pos.side,
            entry_time=pos.entry_time,
            exit_time=ts,
            entry_price=pos.entry_price,
            exit_price=exit_price,
            size=pos.size,
            pnl=pnl_after_fees,
            pnl_pct=pnl_pct,
            reason=reason,
        )
        self.state.history.append(trade_log)
        self.state.open_positions.pop(self.symbol, None)

    def _maybe_open_position(
        self,
        ts: pd.Timestamp,
        close: float,
        signal: int,
        atr_value: Optional[float],
    ) -> None:
        if self.symbol in self.state.open_positions:
            return  # ya hay una posición abierta

        if signal == 1:
            side = Side.LONG
        elif signal == -1 and self.bt_cfg.allow_short:
            side = Side.SHORT
        else:
            return

        side_str = "long" if side == Side.LONG else "short"

        # SL/TP teóricos (sin slippage/spread) basados en close
        sl_price, tp_price = compute_sl_tp(
            cfg=self.bt_cfg,
            side=side_str,
            entry_price=close,
            atr=atr_value,
        )

        # Precio efectivo de entrada con spread + slippage
        entry_price = close
        if self.spread_pct > 0.0:
            # asumimos mitad del spread en contra en la entrada
            half_spread = self.spread_pct / 2.0
            if side == Side.LONG:
                entry_price *= (1.0 + half_spread)
            else:  # SHORT
                entry_price *= (1.0 - half_spread)

        if self.slippage_pct > 0.0:
            if side == Side.LONG:
                entry_price *= (1.0 + self.slippage_pct)
            else:
                entry_price *= (1.0 - self.slippage_pct)

        # Recalcular SL/TP alrededor del entry_price efectivo
        # (manteniendo la misma distancia relativa que el diseño original)
        # Distancia en % al SL según el cfg (si no ATR)
        # Para no complicar: volvemos a usar compute_sl_tp, pero con entry_price efectivo.
        sl_price_eff, tp_price_eff = compute_sl_tp(
            cfg=self.bt_cfg,
            side=side_str,
            entry_price=entry_price,
            atr=atr_value,
        )

        size = calculate_position_size_spot(
            capital=self.state.capital,
            entry_price=entry_price,
            stop_price=sl_price_eff,
            config=self.risk_cfg,
        )

        if size <= 0:
            return

        # Comisiones de entrada
        fee_entry = entry_price * size * self.bt_cfg.fee_pct
        self.state.capital -= fee_entry
        self.state.equity = self.state.capital

        pos = Position(
            symbol=self.symbol,
            side=side,
            entry_time=ts,
            entry_price=entry_price,
            size=size,
            stop_price=sl_price_eff,
            tp_price=tp_price_eff,
        )
        self.state.open_positions[self.symbol] = pos