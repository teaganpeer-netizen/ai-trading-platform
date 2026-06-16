"""
Circuit breaker system to halt trading under extreme conditions.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    OPEN = "open"  # Trading allowed
    CAUTION = "caution"  # Limited trading
    HALT = "halt"  # No trading


@dataclass
class CircuitEvent:
    """Record of a circuit breaker event."""
    timestamp: datetime
    state: CircuitState
    reason: str
    portfolio_value: float
    daily_loss_pct: float


class CircuitBreaker:
    """Monitors portfolio health and halts trading if limits breached."""

    def __init__(
        self,
        initial_portfolio_value: float,
        halt_drawdown_pct: float = 0.10,  # Halt if 10% drawdown
        halt_daily_loss_pct: float = 0.05,  # Halt if 5% daily loss
        halt_consecutive_losses: int = 5,  # Halt after 5 consecutive losses
        recovery_grace_period_hours: int = 1,  # Allow 1 hour recovery before full halt
    ):
        self.initial_portfolio_value = initial_portfolio_value
        self.halt_drawdown_pct = halt_drawdown_pct
        self.halt_daily_loss_pct = halt_daily_loss_pct
        self.halt_consecutive_losses = halt_consecutive_losses
        self.recovery_grace_period_hours = recovery_grace_period_hours

        self.state = CircuitState.OPEN
        self.peak_value = initial_portfolio_value
        self.consecutive_losses = 0
        self.last_trade_was_loss = False
        self.halt_time = None
        self.events: list[CircuitEvent] = []

    def update(
        self,
        current_portfolio_value: float,
        daily_loss_pct: float,
        trade_was_loss: bool = False,
    ) -> CircuitState:
        """
        Update circuit breaker state based on current conditions.

        Args:
            current_portfolio_value: Current portfolio value
            daily_loss_pct: Daily loss as percentage (0.0 to 1.0)
            trade_was_loss: Whether the last trade was a loss

        Returns:
            Current circuit state
        """
        # Update peak value
        if current_portfolio_value > self.peak_value:
            self.peak_value = current_portfolio_value

        # Track consecutive losses
        if trade_was_loss:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

        # Calculate drawdown
        drawdown = (self.peak_value - current_portfolio_value) / self.peak_value if self.peak_value > 0 else 0

        # Check circuit breaker conditions
        new_state = self._evaluate_state(
            current_portfolio_value,
            daily_loss_pct,
            drawdown,
        )

        # State transition
        if new_state != self.state:
            self._record_event(new_state, current_portfolio_value, daily_loss_pct)
            self.state = new_state

            if new_state == CircuitState.HALT:
                self.halt_time = datetime.utcnow()
                logger.error(f"⚠️  CIRCUIT BREAKER HALT: {self._get_halt_reason(current_portfolio_value, daily_loss_pct, drawdown)}")
            elif new_state == CircuitState.CAUTION:
                logger.warning(f"⚠️  CIRCUIT BREAKER CAUTION: Portfolio at risk")

        return self.state

    def _evaluate_state(
        self,
        current_value: float,
        daily_loss_pct: float,
        drawdown_pct: float,
    ) -> CircuitState:
        """Determine circuit state based on conditions."""
        # If halted, check if recovery grace period has passed
        if self.state == CircuitState.HALT:
            if self.halt_time:
                elapsed = datetime.utcnow() - self.halt_time
                if elapsed < timedelta(hours=self.recovery_grace_period_hours):
                    return CircuitState.HALT
                else:
                    # Grace period passed, allow caution mode
                    logger.info("Circuit breaker recovery grace period expired, resuming caution mode")
                    return CircuitState.CAUTION
            return CircuitState.HALT

        # Check halt conditions
        if drawdown_pct >= self.halt_drawdown_pct:
            return CircuitState.HALT
        if daily_loss_pct >= self.halt_daily_loss_pct:
            return CircuitState.HALT
        if self.consecutive_losses >= self.halt_consecutive_losses:
            return CircuitState.HALT

        # Check caution conditions
        if drawdown_pct >= self.halt_drawdown_pct * 0.5:  # Half the halt threshold
            return CircuitState.CAUTION
        if daily_loss_pct >= self.halt_daily_loss_pct * 0.7:
            return CircuitState.CAUTION
        if self.consecutive_losses >= self.halt_consecutive_losses - 1:
            return CircuitState.CAUTION

        return CircuitState.OPEN

    def _get_halt_reason(self, current_value: float, daily_loss_pct: float, drawdown_pct: float) -> str:
        """Generate description of halt reason."""
        reasons = []
        if drawdown_pct >= self.halt_drawdown_pct:
            reasons.append(f"Drawdown {drawdown_pct*100:.1f}% >= {self.halt_drawdown_pct*100:.1f}%")
        if daily_loss_pct >= self.halt_daily_loss_pct:
            reasons.append(f"Daily loss {daily_loss_pct*100:.1f}% >= {self.halt_daily_loss_pct*100:.1f}%")
        if self.consecutive_losses >= self.halt_consecutive_losses:
            reasons.append(f"{self.consecutive_losses} consecutive losses")
        return " | ".join(reasons)

    def _record_event(self, new_state: CircuitState, value: float, daily_loss_pct: float) -> None:
        """Record circuit breaker event."""
        drawdown = (self.peak_value - value) / self.peak_value if self.peak_value > 0 else 0
        event = CircuitEvent(
            timestamp=datetime.utcnow(),
            state=new_state,
            reason=self._get_halt_reason(value, daily_loss_pct, drawdown),
            portfolio_value=value,
            daily_loss_pct=daily_loss_pct * 100,
        )
        self.events.append(event)

    def can_open_position(self) -> tuple[bool, str]:
        """Check if new positions are allowed."""
        if self.state == CircuitState.HALT:
            return False, f"Circuit breaker HALT (recovery in {self._recovery_time_remaining()})"
        if self.state == CircuitState.CAUTION:
            return False, "Circuit breaker CAUTION: No new positions"
        return True, "OK"

    def _recovery_time_remaining(self) -> str:
        """Time remaining in halt grace period."""
        if not self.halt_time:
            return "N/A"
        elapsed = datetime.utcnow() - self.halt_time
        remaining = timedelta(hours=self.recovery_grace_period_hours) - elapsed
        if remaining.total_seconds() <= 0:
            return "0s"
        return f"{remaining.total_seconds():.0f}s"

    def get_status(self) -> dict:
        """Get circuit breaker status."""
        return {
            "state": self.state.value,
            "can_trade": self.state == CircuitState.OPEN,
            "peak_value": self.peak_value,
            "consecutive_losses": self.consecutive_losses,
            "events": [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "state": e.state.value,
                    "reason": e.reason,
                }
                for e in self.events[-5:]  # Last 5 events
            ],
        }
