import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import dataclasses
from typing import Any

from config.settings import RISK_CONFIG
from data.downloader import get_datos_cripto_cached
from backtesting.engine import Backtester, BacktestConfig
from strategies.registry import STRATEGY_REGISTRY, create_strategy
from visualization.interactive_chart import plot_interactive_candles

# Page Config
st.set_page_config(
    page_title="Crypto Trading Bot Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Title
st.title("🚀 Crypto Trading Bot Dashboard")

# --- Sidebar Configuration ---
st.sidebar.header("⚙️ Backtest Configuration")

# 1. Strategy Selection
strategy_type = st.sidebar.selectbox(
    "Select Strategy",
    options=list(STRATEGY_REGISTRY.keys()),
    index=0
)

strategy_cls, config_cls = STRATEGY_REGISTRY[strategy_type]

st.sidebar.markdown("---")
st.sidebar.subheader("Strategy Parameters")

# 2. Dynamic Strategy Parameters
strategy_params = {}
for field in dataclasses.fields(config_cls):
    # Skip internal/hidden fields if any, or customize based on type
    default_val = field.default
    if default_val == dataclasses.MISSING:
        default_val = None # Handle missing defaults if necessary
    
    # Create input based on type
    if field.type == int:
        strategy_params[field.name] = st.sidebar.number_input(
            f"{field.name}", value=default_val or 0, step=1
        )
    elif field.type == float:
        strategy_params[field.name] = st.sidebar.number_input(
            f"{field.name}", value=default_val or 0.0, step=0.01, format="%.4f"
        )
    elif field.type == bool:
        strategy_params[field.name] = st.sidebar.checkbox(
            f"{field.name}", value=default_val
        )
    else:
        # Fallback for strings or other types
        strategy_params[field.name] = st.sidebar.text_input(
            f"{field.name}", value=str(default_val)
        )

# Instantiate Config Object
try:
    strategy_config = config_cls(**strategy_params)
except Exception as e:
    st.error(f"Error creating config: {e}")
    st.stop()

st.sidebar.markdown("---")
st.sidebar.subheader("Market Data")

# 3. Market Data Selection
symbol = st.sidebar.text_input("Symbol", value="BTC/USDT")
timeframe = st.sidebar.selectbox("Timeframe", options=["15m", "1h", "4h", "1d"], index=0)

# Date Range
col1, col2 = st.sidebar.columns(2)
start_date_input = col1.date_input("Start Date", value=datetime.now() - timedelta(days=30))
end_date_input = col2.date_input("End Date", value=datetime.now())

# Backtest Config (Capital, etc.)
st.sidebar.markdown("---")
st.sidebar.subheader("Account Settings")
initial_capital = st.sidebar.number_input("Initial Capital ($)", value=10000.0, step=1000.0)
fee_pct = st.sidebar.number_input("Fee %", value=0.0005, step=0.0001, format="%.4f")

# Run Button
if st.sidebar.button("▶️ Run Backtest", type="primary"):
    with st.spinner("Downloading data and running backtest..."):
        # 1. Prepare Dates
        start_dt = datetime.combine(start_date_input, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(end_date_input, datetime.max.time()).replace(tzinfo=timezone.utc)
        
        # 2. Download Data
        # Estimate limit based on timeframe
        # Simple heuristic: 1000 candles usually enough for recent, but let's calculate roughly
        # to ensure we cover the range + buffer
        limit = 2000 # Default safe buffer
        
        try:
            df = get_datos_cripto_cached(
                symbol=symbol,
                timeframe=timeframe,
                limit=limit,
                force_download=False
            )
            
            # Ensure UTC
            if df['timestamp'].dt.tz is None:
                df['timestamp'] = df['timestamp'].dt.tz_localize('UTC')
            
            # Filter Date Range
            mask = (df['timestamp'] >= start_dt) & (df['timestamp'] <= end_dt)
            df_filtered = df.loc[mask].copy().reset_index(drop=True)
            
            if df_filtered.empty:
                st.error("No data found for the selected date range.")
            else:
                # 3. Run Strategy
                strategy = create_strategy(strategy_type, strategy_config)
                df_signals = strategy.generate_signals(df_filtered)
                
                # 4. Run Backtest
                bt_config = BacktestConfig(
                    initial_capital=initial_capital,
                    fee_pct=fee_pct,
                    sl_pct=0.02, # Default, maybe expose later
                    tp_rr=2.0    # Default, maybe expose later
                )
                
                # Use global risk config for now, or expose it
                backtester = Backtester(
                    backtest_config=bt_config,
                    risk_config=RISK_CONFIG
                )
                
                result = backtester.run(df_signals)
                
                # 5. Display Results
                
                # Metrics
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("Total Return", f"{result.total_return_pct:.2f}%")
                m2.metric("Win Rate", f"{result.winrate_pct:.2f}%")
                m3.metric("Max Drawdown", f"{result.max_drawdown_pct:.2f}%")
                m4.metric("Profit Factor", f"{result.profit_factor:.2f}")
                m5.metric("Trades", result.num_trades)
                
                # Charts
                st.subheader("Price & Indicators")
                
                # Prepare indicators DataFrame for plotting
                # We need to extract indicators from df_signals that match the strategy
                # Usually strategies add columns to the DF. We pass the whole df_signals.
                fig = plot_interactive_candles(
                    df_signals,
                    trades=result.trades,
                    title=f"{symbol} {timeframe} - {strategy_type}",
                    indicators=df_signals # Pass the whole DF, the plotter handles specific cols if needed or we can filter
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Equity Curve
                st.subheader("Equity Curve")
                if result.equity_curve is not None:
                    st.line_chart(result.equity_curve)
                
                # Trades List
                st.subheader("Trade Log")
                if result.trades:
                    trades_data = []
                    for t in result.trades:
                        trades_data.append({
                            "Entry Time": t.entry_time,
                            "Type": t.direction,
                            "Entry Price": t.entry_price,
                            "Exit Time": t.exit_time,
                            "Exit Price": t.exit_price,
                            "PnL": t.pnl,
                            "PnL %": t.pnl_pct
                        })
                    st.dataframe(pd.DataFrame(trades_data))
                else:
                    st.info("No trades executed in this period.")
                    
        except Exception as e:
            st.error(f"An error occurred: {e}")
            # st.exception(e) # Uncomment for debugging

