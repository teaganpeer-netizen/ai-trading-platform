"""
Risk management system with position sizing, stops, and limits.
"""

from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk profile levels."""
    CONSERVATIVE = 0.01  # 1% per trade
    MODERATE = 0.02  # 2% per trade
    AGGRESSIVE = 0.05  # 5% per trade


@dataclass
class RiskMetrics:
    """Risk metrics for a trade or portfolio."""
    entry_price: float
    stop_loss_price: float
    take_profit_price: float
    position_size: float
    risk_per_trade: float  # Dollar amount at risk
    risk_pct: float  # % of portfolio at risk
    reward_risk_ratio: float  # R:R ratio


class RiskManager:
    """Manages portfolio risk, position sizing, and trade limits."""

    def __init__(
        self,
        portfolio_value: float,
        risk_per_trade_pct: float = 0.02,  # 2% of portfolio per trade
        max_daily_loss_pct: float = 0.05,  # Max 5% daily loss
        max_portfolio_exposure_pct: float = 0.80,  # Max 80% deployed
        max_open_positions: int = 5,
    ):
        self.portfolio_value = portfolio_value
        self.risk_per_trade_pct = risk_per_trade_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_portfolio_exposure_pct = max_portfolio_exposure_pct
        self.max_open_positions = max_open_positions

        self.daily_loss = 0.0
        self.daily_loss_reset_date = datetime.utcnow().date()

    def update_portfolio_value(self, new_value: float) -> None:
        """Update portfolio value for position sizing calculations."""
        self.portfolio_value = new_value

    def reset_daily_loss(self) -> None:
        """Reset daily loss tracking (call at market open)."""
        self.daily_loss = 0.0
        self.daily_loss_reset_date = datetime.utcnow().date()

    def add_loss(self, loss: float) -> None:
        """Track a realized loss."""
        if loss < 0:
            self.daily_loss += abs(loss)

    def can_trade(self, num_open_positions: int, current_exposure_pct: float) -> tuple[bool, str]:
        """
        Check if a new trade is allowed based on risk limits.

        Returns:
            (allowed: bool, reason: str)
        """
        # Check max open positions
        if num_open_positions >= self.max_open_positions:
            return False, f"Max open positions ({self.max_open_positions}) reached"

        # Check daily loss limit
        daily_loss_pct = self.daily_loss / self.portfolio_value if self.portfolio_value > 0 else 0
        if daily_loss_pct >= self.max_daily_loss_pct:
            return False, f"Daily loss limit ({self.max_daily_loss_pct*100:.1f}%) reached"

        # Check portfolio exposure
        if current_exposure_pct >= self.max_portfolio_exposure_pct:
            return False, f"Max portfolio exposure ({self.max_portfolio_exposure_pct*100:.0f}%) reached"

        return True, "OK"

    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss_price: float,
        use_pct: float = None,
    ) -> float:
        """
        Calculate position size based on risk.

        Args:
            entry_price: Entry price
            stop_loss_price: Stop loss price
            use_pct: Override risk % (if None, uses self.risk_per_trade_pct)

        Returns:
            Position size (number of shares)
        """
        risk_pct = use_pct or self.risk_per_trade_pct
        risk_amount = self.portfolio_value * risk_pct

        # Risk per share = entry - stop
        risk_per_share = abs(entry_price - stop_loss_price)

        if risk_per_share <= 0:
            logger.warning(f"Invalid stop loss: entry={entry_price}, stop={stop_loss_price}")
            return 0

        position_size = risk_amount / risk_per_share
        return position_size

    def calculate_risk_metrics(
        self,
        entry_price: float,
        stop_loss_price: float,
        take_profit_price: float = None,
        position_size: float = None,
    ) -> RiskMetrics:
        """
        Calculate complete risk metrics for a trade.

        Args:
            entry_price: Entry price
            stop_loss_price: Stop loss price
            take_profit_price: Target profit price (optional)
            position_size: Position size (if None, calculated from risk)

        Returns:
            RiskMetrics object
        """
        # Calculate position size if not provided
        if position_size is None:
            position_size = self.calculate_position_size(entry_price, stop_loss_price)

        # Risk per trade
        risk_per_share = abs(entry_price - stop_loss_price)
        risk_per_trade = risk_per_share * position_size

        # Risk as % of portfolio
        risk_pct = (risk_per_trade / self.portfolio_value * 100) if self.portfolio_value > 0 else 0

        # Reward:Risk ratio
        if take_profit_price and risk_per_share > 0:
            profit_per_share = abs(take_profit_price - entry_price)
            reward_risk_ratio = profit_per_share / risk_per_share
        else:
            reward_risk_ratio = 0

        return RiskMetrics(
            entry_price=entry_price,
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price or entry_price,
            position_size=position_size,
            risk_per_trade=risk_per_trade,
            risk_pct=risk_pct,
            reward_risk_ratio=reward_risk_ratio,
        )

    def get_suggested_stops(
        self,
        entry_price: float,
        atr: float = None,
        atr_multiple: float = 2.0,
    ) -> tuple[float, float]:
        """
        Calculate suggested stop loss and take profit using ATR.

        Args:
            entry_price: Entry price
            atr: Average True Range (if None, returns None)
            atr_multiple: Multiplier for ATR (default 2.0x for stop, 3.0x for target)

        Returns:
            (stop_loss_price, take_profit_price)
        """
        if atr is None or atr <= 0:
            return entry_price * 0.95, entry_price * 1.05  # Default 5% stops

        stop_loss = entry_price - (atr * atr_multiple)
        take_profit = entry_price + (atr * atr_multiple * 1.5)

        return stop_loss, take_profit

    def get_exposure(
        self,
        open_positions: dict = None,
    ) -> float:
        """
        Calculate current portfolio exposure %.

        Args:
            open_positions: {symbol: (quantity, entry_price)} or empty dict

        Returns:
            Exposure as fraction (0.0 to 1.0)
        """
        if not open_positions:
            return 0.0

        # Simplified: assume each position is 20% of portfolio
        return min(len(open_positions) * 0.20, 1.0)

    def get_position_exposure(
        self,
        current_prices: dict[str, float],
        open_positions: dict[str, tuple[float, float]],
    ) -> float:
        """
        Calculate current portfolio exposure %.

        Args:
            current_prices: {symbol: price}
            open_positions: {symbol: (quantity, entry_price)}

        Returns:
            Exposure as fraction (0.0 to 1.0)
        """
        positions_value = sum(
            qty * current_prices.get(symbol, entry_price)
            for symbol, (qty, entry_price) in open_positions.items()
        )

        if self.portfolio_value <= 0:
            return 0.0

        return positions_value / self.portfolio_value

    def get_risk_summary(self, current_exposure_pct: float) -> dict:
        """Get current risk status."""
        daily_loss_pct = self.daily_loss / self.portfolio_value if self.portfolio_value > 0 else 0

        return {
            "portfolio_value": self.portfolio_value,
            "risk_per_trade_pct": self.risk_per_trade_pct * 100,
            "daily_loss": self.daily_loss,
            "daily_loss_pct": daily_loss_pct * 100,
            "daily_loss_remaining_pct": (self.max_daily_loss_pct - daily_loss_pct) * 100,
            "current_exposure_pct": current_exposure_pct * 100,
            "max_exposure_pct": self.max_portfolio_exposure_pct * 100,
        }
