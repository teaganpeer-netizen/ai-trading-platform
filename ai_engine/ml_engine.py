"""
Machine learning engine for price prediction.
Random forest regression with continuous learning pipeline.
Designed to improve as more historical data accumulates.
"""

import logging
import numpy as np
import pickle
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple
from dataclasses import dataclass

try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("sklearn not available - ML features disabled. Install via: pip install scikit-learn")

logger = logging.getLogger(__name__)


@dataclass
class MLPrediction:
    """Machine learning prediction result."""
    symbol: str
    prediction_price: float
    confidence: float
    next_move: str  # "UP", "DOWN", "NEUTRAL"
    key_features: dict
    timestamp: str


class FeatureEngineering:
    """Creates ML features from market data."""

    @staticmethod
    def create_features(
        closes: list[float],
        highs: list[float],
        lows: list[float],
        volumes: list[float],
    ) -> Tuple[np.ndarray, list[str]]:
        """Engineer ML features from OHLCV data."""
        if len(closes) < 20:
            return np.array([]), []

        features_dict = {}
        feature_names = []

        # Price features
        returns = np.diff(closes) / closes[:-1]
        features_dict["avg_return_5d"] = np.mean(returns[-5:])
        features_dict["volatility_5d"] = np.std(returns[-5:])
        features_dict["momentum_5d"] = returns[-1] / (np.std(returns) + 1e-8)

        # SMA features
        sma_5 = np.mean(closes[-5:])
        sma_10 = np.mean(closes[-10:])
        sma_20 = np.mean(closes[-20:])
        features_dict["price_vs_sma5"] = (closes[-1] - sma_5) / sma_5
        features_dict["price_vs_sma10"] = (closes[-1] - sma_10) / sma_10
        features_dict["price_vs_sma20"] = (closes[-1] - sma_20) / sma_20

        # Trend
        features_dict["sma5_vs_sma20"] = (sma_5 - sma_20) / sma_20

        # Volatility
        features_dict["high_low_ratio"] = (highs[-1] - lows[-1]) / closes[-1]
        features_dict["volatility_20d"] = np.std(returns[-20:])

        # Volume
        if len(volumes) > 0:
            volume_sma = np.mean(volumes[-20:])
            features_dict["volume_ratio"] = volumes[-1] / (volume_sma + 1e-8)

        # RSI-like feature
        gains = np.maximum(returns, 0)
        losses = np.maximum(-returns, 0)
        avg_gain = np.mean(gains[-14:]) if len(gains) >= 14 else np.mean(gains)
        avg_loss = np.mean(losses[-14:]) if len(losses) >= 14 else np.mean(losses)
        rs = avg_gain / (avg_loss + 1e-8)
        features_dict["rsi_proxy"] = 100 - (100 / (1 + rs))

        # MACD-like feature
        ema_12 = FeatureEngineering._ema(closes, 12)
        ema_26 = FeatureEngineering._ema(closes, 26)
        features_dict["macd_proxy"] = ema_12 - ema_26

        # Convert to array
        feature_array = np.array([features_dict[name] for name in sorted(features_dict.keys())])
        feature_names = sorted(features_dict.keys())

        return feature_array, feature_names

    @staticmethod
    def _ema(prices: list[float], period: int) -> float:
        """Calculate exponential moving average."""
        if len(prices) < period:
            return np.mean(prices)

        prices = np.array(prices)
        ema = prices[-period:].mean()
        multiplier = 2 / (period + 1)

        for price in prices[-period:-1:-1]:
            ema = price * multiplier + ema * (1 - multiplier)

        return float(ema)


class RandomForestPredictor:
    """Random forest price prediction model."""

    def __init__(self, symbol: str, model_dir: Optional[Path] = None):
        self.symbol = symbol
        self.model_dir = model_dir or Path(__file__).parent.parent / "data" / "ml_models"
        self.model_dir.mkdir(parents=True, exist_ok=True)

        self.model: Optional[RandomForestRegressor] = None
        self.scaler: Optional[StandardScaler] = None
        self.feature_names: list[str] = []
        self.trained = False

        self._load_model()

    def _load_model(self):
        """Load trained model from disk if exists."""
        model_path = self.model_dir / f"{self.symbol}_rf_model.pkl"
        scaler_path = self.model_dir / f"{self.symbol}_scaler.pkl"

        if model_path.exists() and scaler_path.exists():
            try:
                with open(model_path, "rb") as f:
                    self.model = pickle.load(f)
                with open(scaler_path, "rb") as f:
                    self.scaler = pickle.load(f)
                self.trained = True
                logger.info(f"Loaded existing model for {self.symbol}")
            except Exception as e:
                logger.warning(f"Failed to load model for {self.symbol}: {e}")

    def _save_model(self):
        """Save trained model to disk."""
        try:
            model_path = self.model_dir / f"{self.symbol}_rf_model.pkl"
            scaler_path = self.model_dir / f"{self.symbol}_scaler.pkl"

            with open(model_path, "wb") as f:
                pickle.dump(self.model, f)
            with open(scaler_path, "wb") as f:
                pickle.dump(self.scaler, f)

            logger.info(f"Saved model for {self.symbol}")
        except Exception as e:
            logger.warning(f"Failed to save model: {e}")

    def train(
        self,
        closes: list[float],
        highs: list[float],
        lows: list[float],
        volumes: list[float],
        min_samples: int = 50,
    ) -> bool:
        """Train random forest model on historical data."""
        if not SKLEARN_AVAILABLE:
            logger.warning("sklearn not available")
            return False

        if len(closes) < min_samples:
            logger.warning(f"Insufficient data ({len(closes)} < {min_samples})")
            return False

        try:
            # Prepare features and target
            X_list = []
            y_list = []

            for i in range(20, len(closes) - 1):
                # Use 20-day window to predict next day
                window_closes = closes[i - 20 : i]
                window_highs = highs[i - 20 : i]
                window_lows = lows[i - 20 : i]
                window_volumes = volumes[i - 20 : i] if i < len(volumes) else [0] * 20

                features, self.feature_names = FeatureEngineering.create_features(
                    window_closes, window_highs, window_lows, window_volumes
                )

                if len(features) > 0:
                    X_list.append(features)
                    # Target: next day's return
                    next_return = (closes[i + 1] - closes[i]) / closes[i]
                    y_list.append(next_return)

            if len(X_list) < 10:
                logger.warning("Not enough samples for training")
                return False

            X = np.array(X_list)
            y = np.array(y_list)

            # Scale features
            self.scaler = StandardScaler()
            X_scaled = self.scaler.fit_transform(X)

            # Train model
            self.model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                random_state=42,
                n_jobs=-1,
            )
            self.model.fit(X_scaled, y)

            # Calculate training metrics
            y_pred = self.model.predict(X_scaled)
            mse = np.mean((y - y_pred) ** 2)
            r2 = self.model.score(X_scaled, y)

            self.trained = True
            self._save_model()

            logger.info(
                f"Trained {self.symbol} model: {len(X)} samples, R²={r2:.3f}, MSE={mse:.6f}"
            )
            return True

        except Exception as e:
            logger.error(f"Training failed: {e}")
            return False

    def predict(
        self,
        closes: list[float],
        highs: list[float],
        lows: list[float],
        volumes: list[float],
    ) -> Optional[MLPrediction]:
        """Predict next day's price movement."""
        if not self.trained or self.model is None or self.scaler is None:
            return None

        try:
            if len(closes) < 20:
                return None

            features, _ = FeatureEngineering.create_features(
                closes[-20:], highs[-20:], lows[-20:], volumes[-20:]
            )

            if len(features) == 0:
                return None

            features_scaled = self.scaler.transform([features])[0]
            predicted_return = self.model.predict([features_scaled])[0]
            predicted_price = closes[-1] * (1 + predicted_return)

            # Confidence (0-100%)
            confidence = min(abs(predicted_return) * 1000, 100.0)

            # Direction
            next_move = "UP" if predicted_return > 0.001 else "DOWN" if predicted_return < -0.001 else "NEUTRAL"

            # Feature importance
            feature_importance = {}
            for name, importance in zip(self.feature_names, self.model.feature_importances_):
                if importance > 0.02:  # Only top features
                    feature_importance[name] = float(importance)

            return MLPrediction(
                symbol=self.symbol,
                prediction_price=float(predicted_price),
                confidence=float(confidence),
                next_move=next_move,
                key_features=feature_importance,
                timestamp=datetime.utcnow().isoformat(),
            )

        except Exception as e:
            logger.warning(f"Prediction failed for {self.symbol}: {e}")
            return None

    def get_feature_importance(self) -> dict:
        """Get feature importance rankings."""
        if not self.trained or self.model is None:
            return {}

        importance_dict = {}
        for name, importance in zip(self.feature_names, self.model.feature_importances_):
            importance_dict[name] = float(importance)

        return dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))


class ContinuousLearningPipeline:
    """Manages continuous model learning from new trades."""

    def __init__(self, model_dir: Optional[Path] = None):
        self.model_dir = model_dir or Path(__file__).parent.parent / "data" / "ml_models"
        self.models: dict[str, RandomForestPredictor] = {}

    def get_predictor(self, symbol: str) -> RandomForestPredictor:
        """Get or create predictor for symbol."""
        if symbol not in self.models:
            self.models[symbol] = RandomForestPredictor(symbol, self.model_dir)
        return self.models[symbol]

    def train_on_history(
        self,
        symbol: str,
        closes: list[float],
        highs: list[float],
        lows: list[float],
        volumes: list[float],
    ) -> bool:
        """Train model on historical data."""
        predictor = self.get_predictor(symbol)
        return predictor.train(closes, highs, lows, volumes)

    def predict_next_move(
        self,
        symbol: str,
        closes: list[float],
        highs: list[float],
        lows: list[float],
        volumes: list[float],
    ) -> Optional[MLPrediction]:
        """Make price prediction."""
        predictor = self.get_predictor(symbol)
        return predictor.predict(closes, highs, lows, volumes)

    def get_model_status(self) -> dict:
        """Get status of all models."""
        status = {}
        for symbol, predictor in self.models.items():
            status[symbol] = {
                "trained": predictor.trained,
                "feature_importance": predictor.get_feature_importance(),
            }
        return status

    def update_model_from_trade(
        self,
        symbol: str,
        entry_price: float,
        exit_price: float,
        holds_days: int,
    ):
        """Update model based on trade outcome (for future enhancement)."""
        # This will be expanded to incorporate trade feedback
        # into model retraining once enough historical data accumulates
        pass
