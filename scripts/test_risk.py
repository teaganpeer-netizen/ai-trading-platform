#!/usr/bin/env python
"""
Test and demonstrate the risk management system.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

from risk import RiskManager, CircuitBreaker, RiskLevel


def test_risk_manager():
    """Test position sizing and risk calculations."""
    print("=" * 60)
    print("Risk Manager Test")
    print("=" * 60)

    risk_mgr = RiskManager(
        portfolio_value=100_000,
        risk_per_trade_pct=0.02,  # 2% per trade
        max_daily_loss_pct=0.05,
        max_portfolio_exposure_pct=0.80,
    )

    # Test 1: Position sizing
    print("\n1. Position Sizing")
    print(f"   Portfolio: ${risk_mgr.portfolio_value:,.0f}")
    print(f"   Risk per trade: {risk_mgr.risk_per_trade_pct*100:.1f}%")

    entry = 100
    stop = 95
    position_size = risk_mgr.calculate_position_size(entry, stop)
    print(f"\n   Entry: ${entry}, Stop: ${stop}")
    print(f"   Position size: {position_size:.2f} shares")
    print(f"   Risk per trade: ${position_size * (entry - stop):,.2f}")

    # Test 2: Risk metrics with R:R
    print("\n2. Risk Metrics with Target")
    metrics = risk_mgr.calculate_risk_metrics(
        entry_price=100,
        stop_loss_price=95,
        take_profit_price=110,
        position_size=position_size,
    )
    print(f"   Entry: ${metrics.entry_price}")
    print(f"   Stop: ${metrics.stop_loss_price}")
    print(f"   Target: ${metrics.take_profit_price}")
    print(f"   Position: {metrics.position_size:.2f} shares")
    print(f"   Risk: ${metrics.risk_per_trade:,.2f} ({metrics.risk_pct:.2f}%)")
    print(f"   Reward:Risk: {metrics.reward_risk_ratio:.2f}")

    # Test 3: ATR-based stops
    print("\n3. ATR-Based Stops")
    stop, target = risk_mgr.get_suggested_stops(entry_price=100, atr=2.0, atr_multiple=2.0)
    print(f"   Entry: $100")
    print(f"   ATR: $2.00")
    print(f"   Stop (2x ATR): ${stop:.2f}")
    print(f"   Target (3x ATR): ${target:.2f}")

    # Test 4: Trading limits
    print("\n4. Trading Limits Check")
    can_trade, reason = risk_mgr.can_trade(num_open_positions=2, current_exposure_pct=0.5)
    print(f"   Open positions: 2 / {risk_mgr.max_open_positions}")
    print(f"   Exposure: 50% / 80%")
    print(f"   Daily loss: $0 / ${risk_mgr.portfolio_value * risk_mgr.max_daily_loss_pct:,.0f}")
    print(f"   Can trade: {can_trade} ({reason})")

    # Test 5: Risk summary
    print("\n5. Risk Summary")
    summary = risk_mgr.get_risk_summary(current_exposure_pct=0.65)
    print(f"   Portfolio value: ${summary['portfolio_value']:,.0f}")
    print(f"   Current exposure: {summary['current_exposure_pct']:.1f}%")
    print(f"   Daily loss: ${summary['daily_loss']:,.2f} ({summary['daily_loss_pct']:.2f}%)")
    print(f"   Remaining daily limit: {summary['daily_loss_remaining_pct']:.2f}%")


def test_circuit_breaker():
    """Test circuit breaker conditions."""
    print("\n" + "=" * 60)
    print("Circuit Breaker Test")
    print("=" * 60)

    cb = CircuitBreaker(
        initial_portfolio_value=100_000,
        halt_drawdown_pct=0.10,
        halt_daily_loss_pct=0.05,
        halt_consecutive_losses=3,
    )

    print("\nInitial state:")
    print(f"   State: {cb.state.value}")
    can_trade, msg = cb.can_open_position()
    print(f"   Can trade: {can_trade}")

    # Simulate losses
    print("\n1. Simulate 5% daily loss:")
    state = cb.update(current_portfolio_value=95_000, daily_loss_pct=0.05)
    print(f"   Portfolio: $95,000 (5% loss)")
    print(f"   State: {state.value}")
    can_trade, msg = cb.can_open_position()
    print(f"   Can trade: {can_trade} ({msg})")

    # Reset and test consecutive losses
    print("\n2. Simulate 3 consecutive losses:")
    cb = CircuitBreaker(
        initial_portfolio_value=100_000,
        halt_consecutive_losses=3,
    )
    for i in range(3):
        state = cb.update(current_portfolio_value=95_000, daily_loss_pct=0.0, trade_was_loss=True)
        print(f"   Loss {i+1}: State = {state.value}")
    can_trade, msg = cb.can_open_position()
    print(f"   Can trade: {can_trade} ({msg})")

    # Test recovery
    print("\n3. Simulate recovery:")
    state = cb.update(current_portfolio_value=96_000, daily_loss_pct=0.0, trade_was_loss=False)
    print(f"   After winning trade: State = {state.value}")

    # Show status
    print("\n4. Circuit Breaker Status:")
    status = cb.get_status()
    print(f"   State: {status['state']}")
    print(f"   Can trade: {status['can_trade']}")
    print(f"   Peak value: ${status['peak_value']:,.0f}")
    print(f"   Consecutive losses: {status['consecutive_losses']}")


if __name__ == "__main__":
    test_risk_manager()
    test_circuit_breaker()
    print("\n" + "=" * 60)
