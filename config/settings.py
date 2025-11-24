# config/settings.py

from dataclasses import dataclass

from backtesting.engine import BacktestConfig

from strategies.macd_adx_trend_strategy import MACDADXTrendStrategyConfig

from utils.risk import RiskManagementConfig


# ==========================
# Configuración general
# ==========================

# Velas máximas por defecto para backtests
DEFAULT_LIMIT_CANDLES: int = 5000

# Config base de backtest (se usa como "plantilla" en optimizadores)
BACKTEST_CONFIG = BacktestConfig(
    initial_capital=1000.0,
    sl_pct=0.005,      # valor por defecto; los optimizadores lo sobreescriben con replace(...)
    tp_rr=2.0,
    fee_pct=0.0005,
    allow_short=True,
    atr_window=None,
    atr_mult_sl=None,
    atr_mult_tp=None,
)

# Riesgo general (spot): 1% por operación
RISK_CONFIG = RiskManagementConfig(
    risk_pct=0.01,
)


# ==========================
# Tipo genérico de "run" de estrategia
# ==========================

@dataclass
class StrategyRunConfig:
    name: str
    symbol: str
    timeframe: str
    limit_candles: int
    strategy_type: str       # "MA_RSI", "MACD_ADX", "KELTNER", etc.
    strategy_config: object
    backtest_config: BacktestConfig





# ==========================
# Estrategia 2: MACD+ADX+Trend (ETH/USDT 15m)
# ==========================

MACD_ADX_ETH15M_CONFIG = MACDADXTrendStrategyConfig(
    fast_ema=12,
    slow_ema=20,
    signal_ema=6,
    trend_ema_window=100,
    adx_window=14,
    adx_threshold=20.0,
    allow_short=False,
)

MACD_ADX_ETH15M_BT_CONFIG = BacktestConfig(
    initial_capital=1000.0,
    sl_pct=0.01,     # 1% SL
    tp_rr=2.5,       # TP 1:2.5
    fee_pct=0.0005,
    allow_short=False,
    atr_window=None,
    atr_mult_sl=None,
    atr_mult_tp=None,
)

MACD_ADX_ETH15M_RUN = StrategyRunConfig(
    name="MACD_ADX_TREND_OPT_ETHUSDT_15m",
    symbol="ETH/USDT",
    timeframe="15m",
    limit_candles=DEFAULT_LIMIT_CANDLES,
    strategy_type="MACD_ADX",
    strategy_config=MACD_ADX_ETH15M_CONFIG,
    backtest_config=MACD_ADX_ETH15M_BT_CONFIG,
)





# ==========================
# Registro de estrategias optimizadas
# (usado por backtest_strategies.py)
# ==========================

OPTIMIZED_STRATEGIES = [
    MACD_ADX_ETH15M_RUN,
]
