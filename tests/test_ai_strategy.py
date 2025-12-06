
import sys
import os
import pandas as pd
import numpy as np

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from strategies.ai_strategy import AIStrategy, AIStrategyConfig

def test_ai_strategy():
    print("Testing AI Strategy...")
    
    # Create dummy data
    dates = pd.date_range(start="2023-01-01", periods=200, freq="1h")
    data = pd.DataFrame({
        "timestamp": dates,
        "open": np.random.uniform(100, 200, 200),
        "high": np.random.uniform(100, 200, 200),
        "low": np.random.uniform(100, 200, 200),
        "close": np.random.uniform(100, 200, 200),
        "volume": np.random.uniform(1000, 5000, 200)
    })
    
    # Ensure High is highest and Low is lowest
    data["high"] = data[["open", "close", "high"]].max(axis=1)
    data["low"] = data[["open", "close", "low"]].min(axis=1)
    
    # Initialize Strategy
    config = AIStrategyConfig(lookback_window=14, n_estimators=10, training_size_pct=0.6)
    strategy = AIStrategy(config)
    
    # Generate Signals
    print("Generating signals...")
    result = strategy.generate_signals(data)
    
    # Verify
    print("Columns:", result.columns)
    if "signal" not in result.columns:
        print("FAIL: 'signal' column missing")
        return
        
    signals = result["signal"].unique()
    print("Unique signals:", signals)
    
    if not set(signals).issubset({-1, 0, 1}):
        print("FAIL: Invalid signals found")
        return
        
    # Check training period signals (should be 0)
    split_idx = int(len(data) * 0.6)
    train_signals = result["signal"].iloc[:split_idx]
    if train_signals.abs().sum() != 0:
        print("FAIL: Signals found in training period (should be 0)")
        print(train_signals[train_signals != 0])
        return
        
    print("PASS: AI Strategy test passed")

if __name__ == "__main__":
    test_ai_strategy()
