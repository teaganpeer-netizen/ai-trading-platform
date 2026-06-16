"""
Portfolio and position tracking for backtesting.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Open position in a symbol."""
    symbol: str
    quantity: float
    entry_price: float
    entry_time: datetime
    entry_bar_idx: int

    @property
    def entry_value(self) -> float:
        return self.quantity * self.entry_price

    def unrealized_pnl(self, current_price: float) -> float:
        return (current_price - self.entry_price) * self.quantity

    def unrealized_pnl_pct(self, current_price: float) -> float:
        if self.entry_price == 0:
            return 0.0
        return ((current_price - self.entry_price) / self.entry_price)


@dataclass
class Portfolio:
    """Tracks positions, cash, and portfolio metrics."""
    initial_cash: float
    cash: float = field(init=False)
    positions: dict = field(default_factory=dict)
    closed_trades: list = field(default_factory=list)  # List of closed trade dicts
    peak_value: float = field(init=False)
    max_drawdown: float = 0.0
    trade_count: int = 0

    def __post_init__(self):
        self.cash = self.initial_cash
        self.peak_value = self.initial_cash

    def get_position(self, symbol: str) -> Optional[Position]:
        """Get open position for a symbol."""
        return self.positions.get(symbol)

    def open_position(
        self,
        symbol: str,
        quantity: float,
        price: float,
        timestamp: datetime,
        bar_idx: int,
    ) -> Position:
        """Open a new position."""
        if quantity <= 0:
            raise ValueError(f"Quantity must be positive, got {quantity}")

        position = Position(
            symbol=symbol,
            quantity=quantity,
            entry_price=price,
            entry_time=timestamp,
            entry_bar_idx=bar_idx,
        )
        self.positions[symbol] = position
        self.cash -= position.entry_value
        return position

    def close_position(
        self,
        symbol: str,
        price: float,
        timestamp: datetime,
    ) -> dict:
        """Close an open position."""
        position = self.positions.pop(symbol, None)
        if not position:
            raise ValueError(f"No open position for {symbol}")

        pnl = position.unrealized_pnl(price)
        pnl_pct = position.unrealized_pnl_pct(price)
        exit_value = position.quantity * price

        trade = {
            "symbol": symbol,
            "quantity": position.quantity,
            "entry_price": position.entry_price,
            "entry_time": position.entry_time,
            "exit_price": price,
            "exit_time": timestamp,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "is_win": pnl > 0,
        }

        self.cash += exit_value
        self.closed_trades.append(trade)
        self.trade_count += 1

        return trade

    def get_total_value(self, current_prices: dict[str, float]) -> float:
        """Get total portfolio value (cash + unrealized P&L)."""
        positions_value = sum(
            pos.quantity * current_prices.get(symbol, pos.entry_price)
            for symbol, pos in self.positions.items()
        )
        return self.cash + positions_value

    def update_max_drawdown(self, current_value: float) -> None:
        """Track peak value and calculate max drawdown."""
        if current_value > self.peak_value:
            self.peak_value = current_value

        if self.peak_value > 0:
            drawdown = (self.peak_value - current_value) / self.peak_value
            self.max_drawdown = max(self.max_drawdown, drawdown)

    def get_exposure(self, current_prices: dict[str, float]) -> float:
        """Get percentage of portfolio deployed in positions."""
        total_value = self.get_total_value(current_prices)
        positions_value = sum(
            pos.quantity * current_prices.get(symbol, pos.entry_price)
            for symbol, pos in self.positions.items()
        )
        if total_value <= 0:
            return 0.0
        return positions_value / total_value

    def get_stats(self) -> dict:
        """Get portfolio statistics."""
        if not self.closed_trades:
            total_return = 0.0
            win_rate = 0.0
            avg_win = 0.0
            avg_loss = 0.0
        else:
            total_pnl = sum(t["pnl"] for t in self.closed_trades)
            total_return = total_pnl / self.initial_cash
            wins = [t for t in self.closed_trades if t["is_win"]]
            losses = [t for t in self.closed_trades if not t["is_win"]]
            win_rate = len(wins) / len(self.closed_trades) if self.closed_trades else 0.0
            avg_win = sum(t["pnl"] for t in wins) / len(wins) if wins else 0.0
            avg_loss = sum(t["pnl"] for t in losses) / len(losses) if losses else 0.0

        return {
            "initial_cash": self.initial_cash,
            "final_value": self.cash,
            "total_return": total_return,
            "total_return_pct": total_return * 100,
            "max_drawdown": self.max_drawdown * 100,
            "trades": self.trade_count,
            "win_rate": win_rate * 100,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": abs(sum(t["pnl"] for t in self.closed_trades if t["is_win"]) / sum(t["pnl"] for t in self.closed_trades if not t["is_win"])) if any(t for t in self.closed_trades if not t["is_win"]) else float('inf'),
        }
