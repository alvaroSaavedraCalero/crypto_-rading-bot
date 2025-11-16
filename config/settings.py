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
    fast_window=10,
    slow_window=25,
    rsi_window=10,
    rsi_overbought=70.0,
    rsi_oversold=30.0,
    use_rsi_filter=False,
    signal_mode="cross",
    use_trend_filter=True,
    trend_ma_window=200,
)


# Configuración de gestión de riesgo
RISK_CONFIG = RiskManagementConfig(
    risk_pct=0.01,  # 1% del capital por operación
)


# Configuración del backtest
BACKTEST_CONFIG = BacktestConfig(
    initial_capital=1000.0,
    sl_pct=0.005,     # 0.5%
    tp_rr=3.0,        # 1:3
    fee_pct=0.0005,
    allow_short=True,
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
