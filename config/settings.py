# config/settings.py

from dataclasses import dataclass

from backtesting.engine import BacktestConfig

from strategies.ma_rsi_strategy import MovingAverageRSIStrategyConfig
from strategies.macd_adx_trend_strategy import MACDADXTrendStrategyConfig
from strategies.supertrend_strategy import SupertrendStrategyConfig
from strategies.keltner_breakout_strategy import KeltnerBreakoutStrategyConfig
from strategies.bollinger_mean_reversion import BollingerMeanReversionStrategyConfig
from strategies.squeeze_momentum_strategy import SqueezeMomentumConfig
from strategies.archived.bb_trend_strategy import BBTrendStrategyConfig

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
# Estrategia 1: MA + RSI (BTC/USDT 15m)
# ==========================

MA_RSI_BTC15M_CONFIG = MovingAverageRSIStrategyConfig(
    fast_window=10,
    slow_window=30,
    rsi_window=10,
    rsi_overbought=70.0,
    rsi_oversold=30.0,
    use_rsi_filter=False,
    signal_mode="cross",
    use_trend_filter=False,
    trend_ma_window=200,
)

MA_RSI_BTC15M_BT_CONFIG = BacktestConfig(
    initial_capital=1000.0,
    sl_pct=0.01,    # 1% SL
    tp_rr=2.5,       # TP 1:2.5
    fee_pct=0.0005,
    allow_short=True,
    atr_window=None,
    atr_mult_sl=None,
    atr_mult_tp=None,
)

MA_RSI_BTC15M_RUN = StrategyRunConfig(
    name="MA_RSI_OPT_BTCUSDT_15m",
    symbol="BTC/USDT",
    timeframe="15m",
    limit_candles=DEFAULT_LIMIT_CANDLES,
    strategy_type="MA_RSI",
    strategy_config=MA_RSI_BTC15M_CONFIG,
    backtest_config=MA_RSI_BTC15M_BT_CONFIG,
)
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
# Estrategia 3: Supertrend (BTC/USDT 15m)
# ==========================

SUPERTREND_BTC15M_CONFIG = SupertrendStrategyConfig(
    atr_period=14,
    atr_multiplier=3.0,
    use_adx_filter=False,
    adx_period=14,
    adx_threshold=20.0,
)

SUPERTREND_BTC15M_BT_CONFIG = BacktestConfig(
    initial_capital=1000.0,
    sl_pct=0.02,     # 2% SL
    tp_rr=3.0,       # TP 1:3
    fee_pct=0.0005,
    allow_short=True,
)

SUPERTREND_BTC15M_RUN = StrategyRunConfig(
    name="SUPERTREND_OPT_BTCUSDT_15m",
    symbol="BTC/USDT",
    timeframe="15m",
    limit_candles=DEFAULT_LIMIT_CANDLES,
    strategy_type="SUPERTREND",
    strategy_config=SUPERTREND_BTC15M_CONFIG,
    backtest_config=SUPERTREND_BTC15M_BT_CONFIG,
)


# ==========================
# Estrategia 4: Keltner Breakout (SOL/USDT 15m)
# ==========================

KELTNER_SOL15M_CONFIG = KeltnerBreakoutStrategyConfig(
    kc_window=30,
    kc_mult=2.5,
    atr_window=20,
    atr_min_percentile=0.4,
    use_trend_filter=True,
    trend_ema_window=150,
    allow_short=True,
    side_mode="both",
)

KELTNER_SOL15M_BT_CONFIG = BacktestConfig(
    initial_capital=1000.0,
    sl_pct=0.0075,   # 0.75% SL
    tp_rr=1.5,       # TP 1:1.5
    fee_pct=0.0005,
    allow_short=True,
    atr_window=None,
    atr_mult_sl=None,
    atr_mult_tp=None,
)

KELTNER_SOL15M_RUN = StrategyRunConfig(
    name="KELTNER_BREAKOUT_OPT_SOLUSDT_15m",
    symbol="SOL/USDT",
    timeframe="15m",
    limit_candles=DEFAULT_LIMIT_CANDLES,
    strategy_type="KELTNER",
    strategy_config=KELTNER_SOL15M_CONFIG,
    backtest_config=KELTNER_SOL15M_BT_CONFIG,
)


# ==========================
# Estrategia 5: Bollinger Mean Reversion (BNB/USDT 15m)
# ==========================

BOLLINGER_MR_BNB15M_CONFIG = BollingerMeanReversionStrategyConfig(
    bb_window=30,
    bb_std=2.0,
    rsi_window=14,
    rsi_oversold=30.0,
    rsi_overbought=65.0,
)

BOLLINGER_MR_BNB15M_BT_CONFIG = BacktestConfig(
    initial_capital=1000.0,
    sl_pct=0.02,   # 2% SL
    tp_rr=1.0,      # TP 1:1
    fee_pct=0.0005,
    allow_short=True,
)

BOLLINGER_MR_BNB15M_RUN = StrategyRunConfig(
    name="BOLLINGER_MR_OPT_BNBUSDT_15m",
    symbol="BNB/USDT",
    timeframe="15m",
    limit_candles=10000,
    strategy_type="BOLLINGER_MR",
    strategy_config=BOLLINGER_MR_BNB15M_CONFIG,
    backtest_config=BOLLINGER_MR_BNB15M_BT_CONFIG,
)


# ==========================
# Estrategia 6: Squeeze Momentum (BNB/USDT 15m)
# ==========================

SQUEEZE_BNB15M_CONFIG = SqueezeMomentumConfig(
    bb_window=20,
    bb_mult=1.8,
    kc_window=14,
    kc_mult=2.0,
    mom_window=10,
    atr_window=14,
    atr_min_percentile=0.3,
    min_squeeze_bars=5,
    allow_short=True,
)

SQUEEZE_BNB15M_BT_CONFIG = BacktestConfig(
    initial_capital=1000.0,
    sl_pct=0.005,   # 0.5% SL
    tp_rr=2.0,      # TP 1:2
    fee_pct=0.0005,
    allow_short=True,
)

SQUEEZE_BNB15M_RUN = StrategyRunConfig(
    name="SQUEEZE_OPT_BNBUSDT_15m",
    symbol="BNB/USDT",
    timeframe="15m",
    limit_candles=DEFAULT_LIMIT_CANDLES,
    strategy_type="SQUEEZE",
    strategy_config=SQUEEZE_BNB15M_CONFIG,
    backtest_config=SQUEEZE_BNB15M_BT_CONFIG,
)


# ==========================
# Estrategia 7: Bollinger + Tendencia (XRP/USDT 15m)
# ==========================

BB_TREND_XRP15M_CONFIG = BBTrendStrategyConfig(
    bb_window=24,
    bb_std=2.0,
    trend_ema_window=100,
    require_slope=True,
    allow_short=True,
    signal_mode="pullback",
)

BB_TREND_XRP15M_BT_CONFIG = BacktestConfig(
    initial_capital=1000.0,
    sl_pct=0.005,   # 0.5% SL
    tp_rr=2.0,      # TP 1:2
    fee_pct=0.0005,
    allow_short=True,
)

BB_TREND_XRP15M_RUN = StrategyRunConfig(
    name="BB_TREND_OPT_XRPUSDT_15m",
    symbol="XRP/USDT",
    timeframe="15m",
    limit_candles=DEFAULT_LIMIT_CANDLES,
    strategy_type="BB_TREND",
    strategy_config=BB_TREND_XRP15M_CONFIG,
    backtest_config=BB_TREND_XRP15M_BT_CONFIG,
)


# ==========================
# Registro de estrategias optimizadas
# (usado por backtest_strategies.py)
# ==========================

OPTIMIZED_STRATEGIES = [
    MA_RSI_BTC15M_RUN,
    MACD_ADX_ETH15M_RUN,
    SUPERTREND_BTC15M_RUN,
    KELTNER_SOL15M_RUN,
    BOLLINGER_MR_BNB15M_RUN,
    SQUEEZE_BNB15M_RUN,
    BB_TREND_XRP15M_RUN,
]
