"""
Example trading strategies for backtesting.
"""

import pandas as pd
from backtesting.strategy import Strategy, Signal


class SMACrossoverStrategy(Strategy):
    """Simple Moving Average crossover strategy."""

    def __init__(self, fast_period: int = 20, slow_period: int = 50):
        super().__init__("SMA Crossover")
        self.fast_period = fast_period
        self.slow_period = slow_period

    def on_bar(self, symbol: str, df: pd.DataFrame) -> Signal | None:
        """
        Buy when fast MA crosses above slow MA.
        Sell when fast MA crosses below slow MA.
        """
        if len(df) < self.slow_period + 1:
            return None

        # Calculate moving averages
        df_copy = df.copy()
        df_copy["sma_fast"] = df_copy["close"].rolling(self.fast_period).mean()
        df_copy["sma_slow"] = df_copy["close"].rolling(self.slow_period).mean()

        # Current and previous bars
        current = df_copy.iloc[-1]
        previous = df_copy.iloc[-2]

        if pd.isna(current["sma_fast"]) or pd.isna(current["sma_slow"]):
            return None

        # Golden cross: fast crosses above slow
        if previous["sma_fast"] <= previous["sma_slow"] and current["sma_fast"] > current["sma_slow"]:
            return Signal(
                symbol=symbol,
                action="buy",
                confidence=0.7,
                reason=f"SMA{self.fast_period} crossed above SMA{self.slow_period}",
            )

        # Death cross: fast crosses below slow
        if previous["sma_fast"] >= previous["sma_slow"] and current["sma_fast"] < current["sma_slow"]:
            return Signal(
                symbol=symbol,
                action="close",
                confidence=0.7,
                reason=f"SMA{self.fast_period} crossed below SMA{self.slow_period}",
            )

        return None


class RSIStrategy(Strategy):
    """Relative Strength Index mean reversion strategy."""

    def __init__(self, period: int = 14, oversold: float = 30, overbought: float = 70):
        super().__init__("RSI")
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    def on_bar(self, symbol: str, df: pd.DataFrame) -> Signal | None:
        """
        Buy on oversold (RSI < 30).
        Sell on overbought (RSI > 70).
        """
        if len(df) < self.period + 1:
            return None

        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        current_rsi = rsi.iloc[-1]

        if pd.isna(current_rsi):
            return None

        if current_rsi < self.oversold:
            return Signal(
                symbol=symbol,
                action="buy",
                confidence=0.6,
                reason=f"RSI oversold ({current_rsi:.1f})",
            )

        if current_rsi > self.overbought:
            return Signal(
                symbol=symbol,
                action="close",
                confidence=0.6,
                reason=f"RSI overbought ({current_rsi:.1f})",
            )

        return None


class MACDStrategy(Strategy):
    """MACD crossover strategy."""

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        super().__init__("MACD")
        self.fast = fast
        self.slow = slow
        self.signal_period = signal

    def on_bar(self, symbol: str, df: pd.DataFrame) -> Signal | None:
        """
        Buy when MACD crosses above signal line.
        Sell when MACD crosses below signal line.
        """
        if len(df) < self.slow + 1:
            return None

        # Calculate MACD
        ema_fast = df["close"].ewm(span=self.fast, adjust=False).mean()
        ema_slow = df["close"].ewm(span=self.slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self.signal_period, adjust=False).mean()

        current_macd = macd_line.iloc[-1]
        current_signal = signal_line.iloc[-1]
        previous_macd = macd_line.iloc[-2]
        previous_signal = signal_line.iloc[-2]

        if pd.isna(current_macd) or pd.isna(current_signal):
            return None

        # MACD crosses above signal
        if previous_macd <= previous_signal and current_macd > current_signal:
            return Signal(
                symbol=symbol,
                action="buy",
                confidence=0.7,
                reason="MACD crossed above signal line",
            )

        # MACD crosses below signal
        if previous_macd >= previous_signal and current_macd < current_signal:
            return Signal(
                symbol=symbol,
                action="close",
                confidence=0.7,
                reason="MACD crossed below signal line",
            )

        return None
