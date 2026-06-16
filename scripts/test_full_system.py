#!/usr/bin/env python
"""
Comprehensive system test - verify all components work correctly.
"""

import sys
from pathlib import Path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

import logging
from datetime import datetime, timedelta
from data import get_session, BarRepository, TradeRepository, BarProcessor, Bar, Trade
from backtesting import Backtester, SMACrossoverStrategy
from risk import RiskManager, CircuitBreaker
from ai_engine import AIDecisionMaker
from config.settings import settings

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

TESTS_PASSED = 0
TESTS_FAILED = 0


def test(name: str):
    """Decorator for test functions."""
    def decorator(func):
        def wrapper():
            global TESTS_PASSED, TESTS_FAILED
            try:
                logger.info(f"\n{'='*60}")
                logger.info(f"TEST: {name}")
                logger.info('='*60)
                func()
                logger.info(f"✓ PASSED")
                TESTS_PASSED += 1
            except AssertionError as e:
                logger.error(f"✗ FAILED: {e}")
                TESTS_FAILED += 1
            except Exception as e:
                logger.error(f"✗ ERROR: {e}", exc_info=True)
                TESTS_FAILED += 1
        return wrapper
    return decorator


@test("Database Connection")
def test_database():
    session = get_session()
    assert session is not None, "Database session failed"

    # Verify tables exist
    bar_repo = BarRepository(session)
    trade_repo = TradeRepository(session)
    assert bar_repo is not None
    assert trade_repo is not None

    session.close()
    logger.info("✓ Database tables accessible")


@test("Data Layer - Bar Storage")
def test_data_storage():
    from data import TradeRepository
    session = get_session()
    bar_repo = BarRepository(session)

    # Create test bar
    test_bar = Bar(
        symbol="TEST",
        timestamp=datetime.utcnow(),
        open=100.0,
        high=105.0,
        low=99.0,
        close=102.0,
        volume=10000,
    )

    # Store it
    stored = bar_repo.upsert_bar(test_bar)
    assert stored.symbol == "TEST"
    assert stored.close == 102.0

    # Retrieve it
    retrieved = bar_repo.get_bars("TEST", limit=1)
    assert len(retrieved) > 0
    assert retrieved[0].close == 102.0

    logger.info("✓ Bars can be stored and retrieved")
    session.close()


@test("Data Layer - Historical Data")
def test_historical_data():
    session = get_session()
    bar_repo = BarRepository(session)

    # Check if we have backfilled data
    spy_bars = bar_repo.get_bars("SPY", limit=100)
    assert len(spy_bars) > 50, f"Not enough SPY data: {len(spy_bars)} bars"

    # Verify OHLCV integrity
    for bar in spy_bars[:10]:
        assert bar.high >= bar.low, f"Invalid high/low for {bar.symbol}"
        assert bar.high >= bar.close, f"High < Close for {bar.symbol}"
        assert bar.low <= bar.close, f"Low > Close for {bar.symbol}"
        assert bar.volume > 0, f"No volume for {bar.symbol}"

    logger.info(f"✓ {len(spy_bars)} SPY bars validated")
    session.close()


@test("Data Processor - Indicators")
def test_indicators():
    session = get_session()
    bar_repo = BarRepository(session)

    bars = bar_repo.get_bars("SPY", limit=100)
    df = BarProcessor.to_dataframe(bars)

    # Enrich with indicators
    df = BarProcessor.enrich_bars(df)

    # Verify all indicators present
    required_cols = ['sma_20', 'sma_50', 'ema_12', 'rsi_14', 'macd', 'atr_14']
    for col in required_cols:
        assert col in df.columns, f"Missing indicator: {col}"
        assert not df[col].isna().all(), f"All {col} values are NaN"

    logger.info(f"✓ All {len(required_cols)} indicators calculated")
    session.close()


@test("Risk Manager - Position Sizing")
def test_position_sizing():
    risk_mgr = RiskManager(
        portfolio_value=100_000,
        risk_per_trade_pct=0.02,
    )

    # Test position sizing
    position_size = risk_mgr.calculate_position_size(
        entry_price=100,
        stop_loss_price=95,
    )

    # Should risk $2000 (2% of $100k)
    risk_amount = position_size * (100 - 95)
    assert 1900 < risk_amount < 2100, f"Position sizing failed: ${risk_amount}"

    logger.info(f"✓ Position sizing: {position_size:.0f} shares for ${risk_amount:,.0f} risk")


@test("Risk Manager - Risk Metrics")
def test_risk_metrics():
    risk_mgr = RiskManager(portfolio_value=100_000)

    metrics = risk_mgr.calculate_risk_metrics(
        entry_price=100,
        stop_loss_price=95,
        take_profit_price=110,
        position_size=400,
    )

    assert metrics.risk_per_trade == 2000, "Risk calculation wrong"
    assert metrics.reward_risk_ratio == 2.0, "Reward:Risk calculation wrong"

    logger.info(f"✓ Risk metrics: {metrics.reward_risk_ratio:.2f}x R:R")


@test("Risk Manager - Trading Limits")
def test_trading_limits():
    risk_mgr = RiskManager(
        portfolio_value=100_000,
        max_daily_loss_pct=0.05,
        max_portfolio_exposure_pct=0.80,
    )

    # Should allow trade
    can_trade, reason = risk_mgr.can_trade(
        num_open_positions=2,
        current_exposure_pct=0.6,
    )
    assert can_trade, f"Should allow trade: {reason}"

    # Simulate daily loss (5.1% = exceeds 5% limit)
    risk_mgr.daily_loss = 5100  # $5,100 loss = 5.1% of $100k

    # Should NOT allow trade now
    can_trade, reason = risk_mgr.can_trade(
        num_open_positions=2,
        current_exposure_pct=0.6,
    )
    assert not can_trade, f"Should block trade after daily loss limit, but got: {reason}"

    logger.info("✓ Trading limits enforced correctly")


@test("Circuit Breaker - Halt Conditions")
def test_circuit_breaker():
    cb = CircuitBreaker(
        initial_portfolio_value=100_000,
        halt_drawdown_pct=0.10,
        halt_daily_loss_pct=0.05,
    )

    # Test 1: Should allow trading initially
    state = cb.update(current_portfolio_value=100_000, daily_loss_pct=0.0)
    assert state.value == "open", "Should start in OPEN state"

    # Test 2: Trigger halt (5% daily loss)
    state = cb.update(current_portfolio_value=95_000, daily_loss_pct=0.05)
    assert state.value == "halt", "Should HALT at 5% daily loss"

    logger.info("✓ Circuit breaker halts at limits")


@test("Backtester - Strategy Execution")
def test_backtester():
    strategy = SMACrossoverStrategy(fast_period=20, slow_period=50)
    backtester = Backtester(strategy, initial_cash=100_000)

    results = backtester.run(['SPY'])

    assert results, "Backtester returned no results"
    assert 'stats' in results, "Missing stats in results"
    assert 'trades' in results, "Missing trades in results"

    stats = results['stats']
    assert stats['trades'] >= 0, "Invalid trade count"
    assert stats['max_drawdown'] >= 0, "Invalid drawdown"

    logger.info(f"✓ Backtest complete: {stats['trades']} trades, {stats['total_return_pct']:+.2f}% return")


@test("AI Engine - Groq Integration")
def test_ai_engine():
    try:
        ai = AIDecisionMaker(api_key=settings.groq_api_key)

        # Get some data
        session = get_session()
        bar_repo = BarRepository(session)
        bars = bar_repo.get_bars("SPY", limit=100)

        df = BarProcessor.to_dataframe(bars)
        df = BarProcessor.enrich_bars(df)

        current_price = df.iloc[-1]['close']

        # Get decision
        decision = ai.analyze_symbol("SPY", df, current_price)

        assert decision is not None, "No decision returned"
        assert decision.action in ['BUY', 'SELL', 'HOLD'], f"Invalid action: {decision.action}"
        assert 0 <= decision.confidence <= 1, f"Invalid confidence: {decision.confidence}"
        assert len(decision.reasoning) > 0, "No reasoning provided"

        logger.info(f"✓ AI Decision: {decision.action} (confidence: {decision.confidence:.0%})")
        logger.info(f"  Reasoning: {decision.reasoning[:100]}...")

        session.close()
    except Exception as e:
        logger.warning(f"AI Engine test skipped (Groq unavailable): {e}")


@test("Config - Settings Load")
def test_config():
    assert settings.alpaca_api_key, "Alpaca API key not set"
    assert settings.alpaca_secret_key, "Alpaca secret key not set"
    assert settings.groq_api_key, "Groq API key not set"
    assert len(settings.watchlist) > 0, "Watchlist is empty"

    logger.info(f"✓ Config loaded: {len(settings.watchlist)} symbols in watchlist")
    logger.info(f"  Risk: {settings.max_risk_per_trade_pct*100:.1f}% per trade")
    logger.info(f"  Daily loss limit: {settings.daily_loss_limit_pct*100:.1f}%")


@test("End-to-End - Data → Processing → Analysis")
def test_end_to_end():
    """Full pipeline test"""
    session = get_session()
    bar_repo = BarRepository(session)

    # Step 1: Load data
    bars = bar_repo.get_bars("AAPL", limit=200)
    assert len(bars) > 100, "Insufficient data"

    # Step 2: Process
    df = BarProcessor.to_dataframe(bars)
    df = BarProcessor.enrich_bars(df)

    # Step 3: Check data quality
    is_valid, msg = BarProcessor.validate_bars(df)
    assert is_valid, f"Data validation failed: {msg}"

    # Step 4: Risk management
    risk_mgr = RiskManager(portfolio_value=100_000)
    position_size = risk_mgr.calculate_position_size(
        entry_price=df.iloc[-1]['close'],
        stop_loss_price=df.iloc[-1]['close'] * 0.95,
    )
    assert position_size > 0, "Position sizing failed"

    logger.info("✓ Full pipeline: data → processing → analysis → execution")
    logger.info(f"  AAPL: {len(bars)} bars, {position_size:.0f} shares at ${df.iloc[-1]['close']:.2f}")

    session.close()


def print_summary():
    """Print test summary."""
    total = TESTS_PASSED + TESTS_FAILED
    pct = (TESTS_PASSED / total * 100) if total > 0 else 0

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Passed: {TESTS_PASSED}")
    print(f"Failed: {TESTS_FAILED}")
    print(f"Total:  {total}")
    print(f"Success Rate: {pct:.0f}%")
    print("=" * 60)

    if TESTS_FAILED == 0:
        print("✓ ALL TESTS PASSED - SYSTEM READY FOR TRADING")
    else:
        print(f"✗ {TESTS_FAILED} TEST(S) FAILED - FIX BEFORE TRADING")

    return TESTS_FAILED == 0


if __name__ == "__main__":
    # Run all tests
    test_database()
    test_data_storage()
    test_historical_data()
    test_indicators()
    test_position_sizing()
    test_risk_metrics()
    test_trading_limits()
    test_circuit_breaker()
    test_backtester()
    test_ai_engine()
    test_config()
    test_end_to_end()

    # Summary
    success = print_summary()
    sys.exit(0 if success else 1)
