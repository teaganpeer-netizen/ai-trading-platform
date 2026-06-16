"""
Base strategy interface for backtesting.
"""

from dataclasses import dataclass
from typing import Optional
import pandas as pd


@dataclass
class Signal:
    """Trading signal from a strategy."""
    symbol: str
    action: str  # "buy", "sell", "hold", "close"
    confidence: float  # 0.0 to 1.0
    reason: str  # Why the signal was generated
    price_target: Optional[float] = None  # Optional stop loss / take profit


class Strategy:
    """Base class for all trading strategies."""

    def __init__(self, name: str):
        self.name = name

    def initialize(self, context: dict) -> None:
        """Called once at backtest start. Override to set up state."""
        pass

    def on_bar(self, symbol: str, df: pd.DataFrame) -> Optional[Signal]:
        """
        Called for each bar.

        Args:
            symbol: Stock symbol
            df: DataFrame of historical bars up to current (most recent row is current bar)

        Returns:
            Signal if the strategy wants to trade, None otherwise.
        """
        raise NotImplementedError

    def on_trade_closed(self, trade_id: int, pnl: float, pnl_pct: float) -> None:
        """Called when a trade closes. Override to track strategy performance."""
        pass
