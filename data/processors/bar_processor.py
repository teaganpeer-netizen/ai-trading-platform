"""
Processes and enriches market bars with technical indicators.
"""

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class BarProcessor:
    """Calculate technical indicators on bar data."""

    @staticmethod
    def to_dataframe(bars: list) -> pd.DataFrame:
        """Convert Bar objects to pandas DataFrame."""
        data = {
            "timestamp": [b.timestamp for b in bars],
            "open": [b.open for b in bars],
            "high": [b.high for b in bars],
            "low": [b.low for b in bars],
            "close": [b.close for b in bars],
            "volume": [b.volume for b in bars],
        }
        df = pd.DataFrame(data)
        df.set_index("timestamp", inplace=True)
        return df.sort_index()

    @staticmethod
    def sma(df: pd.DataFrame, period: int = 20, column: str = "close") -> pd.Series:
        """Simple Moving Average."""
        return df[column].rolling(window=period).mean()

    @staticmethod
    def ema(df: pd.DataFrame, period: int = 20, column: str = "close") -> pd.Series:
        """Exponential Moving Average."""
        return df[column].ewm(span=period, adjust=False).mean()

    @staticmethod
    def rsi(df: pd.DataFrame, period: int = 14, column: str = "close") -> pd.Series:
        """Relative Strength Index (0-100)."""
        delta = df[column].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9, column: str = "close"):
        """MACD (Moving Average Convergence Divergence)."""
        ema_fast = df[column].ewm(span=fast, adjust=False).mean()
        ema_slow = df[column].ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    @staticmethod
    def bollinger_bands(df: pd.DataFrame, period: int = 20, num_std: float = 2.0, column: str = "close"):
        """Bollinger Bands (upper, middle, lower)."""
        middle = df[column].rolling(window=period).mean()
        std = df[column].rolling(window=period).std()
        upper = middle + (std * num_std)
        lower = middle - (std * num_std)
        return upper, middle, lower

    @staticmethod
    def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Average True Range."""
        df = df.copy()
        df["tr"] = np.maximum(
            df["high"] - df["low"],
            np.maximum(
                abs(df["high"] - df["close"].shift(1)),
                abs(df["low"] - df["close"].shift(1)),
            ),
        )
        return df["tr"].rolling(window=period).mean()

    @staticmethod
    def enrich_bars(df: pd.DataFrame) -> pd.DataFrame:
        """
        Add common technical indicators to DataFrame.
        Returns new DataFrame with original OHLCV + indicators.
        """
        df = df.copy()

        # Trend indicators
        df["sma_20"] = BarProcessor.sma(df, 20)
        df["sma_50"] = BarProcessor.sma(df, 50)
        df["ema_12"] = BarProcessor.ema(df, 12)
        df["ema_26"] = BarProcessor.ema(df, 26)

        # Momentum
        df["rsi_14"] = BarProcessor.rsi(df, 14)
        macd, signal, hist = BarProcessor.macd(df)
        df["macd"] = macd
        df["macd_signal"] = signal
        df["macd_hist"] = hist

        # Volatility
        upper, middle, lower = BarProcessor.bollinger_bands(df)
        df["bb_upper"] = upper
        df["bb_middle"] = middle
        df["bb_lower"] = lower
        df["atr_14"] = BarProcessor.atr(df)

        # Returns
        df["returns"] = df["close"].pct_change()
        df["log_returns"] = np.log(df["close"] / df["close"].shift(1))

        return df

    @staticmethod
    def validate_bars(df: pd.DataFrame) -> tuple[bool, str]:
        """Validate bar data for basic issues."""
        if df.empty:
            return False, "Empty DataFrame"
        if df["close"].isna().any():
            return False, "Missing close prices"
        if (df["high"] < df["low"]).any():
            return False, "High < Low in some bars"
        if (df["close"] > df["high"]).any() or (df["close"] < df["low"]).any():
            return False, "Close outside high/low range"
        return True, "Valid"
