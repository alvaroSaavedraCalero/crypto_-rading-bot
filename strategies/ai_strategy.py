
from dataclasses import dataclass
import pandas as pd
import numpy as np
import ta
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import train_test_split

from strategies.base import BaseStrategy, StrategyMetadata

@dataclass
class AIStrategyConfig:
    lookback_window: int = 14
    training_size_pct: float = 0.6
    prediction_threshold: float = 0.55
    
    # Gradient Boosting Hyperparameters
    learning_rate: float = 0.1
    max_iter: int = 100
    max_depth: int = 10

class AIStrategy(BaseStrategy[AIStrategyConfig]):
    """
    AI Strategy using Gradient Boosting (HistGradientBoostingClassifier).
    Predicts if the next close will be higher than the current close.
    """
    name: str = "AI_GB_STRATEGY"

    def __init__(self, config: AIStrategyConfig, meta: StrategyMetadata | None = None):
        super().__init__(config=config, meta=meta)
        self.model = HistGradientBoostingClassifier(
            learning_rate=config.learning_rate,
            max_iter=config.max_iter,
            max_depth=config.max_depth,
            random_state=42
        )
        self.is_trained = False

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        required_cols = {"timestamp", "open", "high", "low", "close", "volume"}
        if not required_cols.issubset(df.columns):
            missing = required_cols - set(df.columns)
            raise ValueError(f"Missing columns: {missing}")

        data = df.copy()
        
        # 1. Feature Engineering
        data = self._add_features(data)
        
        valid_data = data.dropna()
        
        if len(valid_data) < 100: # Not enough data to train
             data["signal"] = 0
             return data

        # 2. Prepare Targets (1 if Close[t+1] > Close[t], else 0)
        valid_data = valid_data.copy()
        valid_data["target"] = (valid_data["close"].shift(-1) > valid_data["close"]).astype(int)
        
        # Split Train/Inference
        train_data = valid_data.iloc[:-1].copy()
        
        # Features columns
        feature_cols = [c for c in train_data.columns if c not in required_cols and c != "target" and c != "signal"]
        
        X = train_data[feature_cols]
        y = train_data["target"]
        
        # 3. Train/Test Split
        split_idx = int(len(train_data) * self.config.training_size_pct)
        
        X_train = X.iloc[:split_idx]
        y_train = y.iloc[:split_idx]
        
        # Train
        self.model.fit(X_train, y_train)
        self.is_trained = True
        
        # Predict on ALL valid data
        X_all = valid_data[feature_cols]
        all_probs = self.model.predict_proba(X_all)[:, 1]
        
        valid_data["prob_up"] = all_probs
        valid_data["signal"] = 0
        
        long_cond = valid_data["prob_up"] > self.config.prediction_threshold
        short_cond = valid_data["prob_up"] < (1 - self.config.prediction_threshold)
        
        valid_data.loc[long_cond, "signal"] = 1
        valid_data.loc[short_cond, "signal"] = -1
        
        # Zero out signals in training period
        valid_data.iloc[:split_idx, valid_data.columns.get_loc("signal")] = 0
        
        # Merge back
        data["signal"] = 0
        data.loc[valid_data.index, "signal"] = valid_data["signal"]
        
        return data

    def _add_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        # Basic Indicators
        df["rsi"] = ta.momentum.rsi(df["close"], window=self.config.lookback_window)
        
        macd = ta.trend.MACD(df["close"])
        df["macd"] = macd.macd()
        df["macd_diff"] = macd.macd_diff()
        
        bb = ta.volatility.BollingerBands(df["close"])
        df["bb_width"] = bb.bollinger_wband()
        
        df["pct_change"] = df["close"].pct_change()
        df["volatility"] = df["close"].rolling(window=self.config.lookback_window).std()
        
        # Volume Change
        df["vol_change"] = df["volume"].pct_change()
        
        # Lagged Features (Context)
        for lag in [1, 2, 3]:
            df[f"pct_change_lag_{lag}"] = df["pct_change"].shift(lag)
            df[f"rsi_lag_{lag}"] = df["rsi"].shift(lag)
            df[f"vol_change_lag_{lag}"] = df["vol_change"].shift(lag)
            
        return df
