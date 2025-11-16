# config/settings.py

from dataclasses import dataclass

from backtesting.engine import BacktestConfig
from strategies.ma_rsi_strategy import MovingAverageRSIStrategyConfig
from utils.risk import RiskManagementConfig


# Parámetros generales de mercado
SYMBOL: str = "BTC/USDT"
TIMEFRAME: str = "15m"       # antes era "1h"
LIMIT_CANDLES: int = 5000    # más velas para tener más operaciones


# Configuración de la estrategia MA + RSI
MA_RSI_CONFIG = MovingAverageRSIStrategyConfig(
    fast_window=10,      # un poco más rápidas
    slow_window=30,
    rsi_window=14,
    rsi_overbought=80.0, # filtro mucho más laxo
    rsi_oversold=20.0,
    use_rsi_filter=False,   # desactivamos filtro RSI por ahora
    signal_mode="trend",    # usar modo tendencia
)


# Configuración de gestión de riesgo
RISK_CONFIG = RiskManagementConfig(
    risk_pct=0.01,  # 1% del capital por operación
)


# Configuración del backtest
BACKTEST_CONFIG = BacktestConfig(
    initial_capital=1000.0,
    sl_pct=0.005,    # 0.5% de stop
    tp_rr=2.0,       # TP a 1:2
    fee_pct=0.0005,
    allow_short=True,
    atr_window=None,      # por defecto no exigimos ATR
    atr_mult_sl=None,     # None => SL fijo
    atr_mult_tp=None,     # None => TP fijo
)



@dataclass
class RunConfig:
    symbol: str
    timeframe: str
    limit_candles: int
    strategy_config: MovingAverageRSIStrategyConfig
    risk_config: RiskManagementConfig
    backtest_config: BacktestConfig


DEFAULT_RUN_CONFIG = RunConfig(
    symbol=SYMBOL,
    timeframe=TIMEFRAME,
    limit_candles=LIMIT_CANDLES,
    strategy_config=MA_RSI_CONFIG,
    risk_config=RISK_CONFIG,
    backtest_config=BACKTEST_CONFIG,
)
