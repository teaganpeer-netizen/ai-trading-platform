#!/usr/bin/env python
"""
Test AI decision maker on historical data.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

import logging
from config.settings import settings
from data import get_session, BarRepository, BarProcessor
from ai_engine import AIDecisionMaker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Analyze symbols using AI."""
    session = get_session()
    bar_repo = BarRepository(session)

    # Get data for a symbol
    symbol = "SPY"
    bars = bar_repo.get_bars(symbol, limit=100)
    if not bars:
        logger.error(f"No data for {symbol}")
        return

    df = BarProcessor.to_dataframe(bars)
    df = df.sort_index()
    df = BarProcessor.enrich_bars(df)

    current_price = df.iloc[-1]["close"]

    logger.info(f"\nAnalyzing {symbol} at ${current_price:.2f}")
    logger.info(f"Data range: {df.index[0].date()} to {df.index[-1].date()}")

    # Initialize AI decision maker
    try:
        ai = AIDecisionMaker(api_key=settings.groq_api_key)
    except Exception as e:
        logger.error(f"Failed to initialize AI: {e}")
        session.close()
        return

    # Get portfolio context
    portfolio_context = {
        "cash": 75_000,
        "open_positions": 0,
        "portfolio_value": 100_000,
        "exposure_pct": 0.0,
        "daily_pnl": 0.0,
    }

    # Get AI decision
    logger.info("\nRequesting AI analysis...")
    try:
        decision = ai.analyze_symbol(symbol, df, current_price, portfolio_context)

        print("\n" + "=" * 60)
        print(f"AI Decision for {decision.symbol}")
        print("=" * 60)
        print(f"Action:     {decision.action}")
        print(f"Confidence: {decision.confidence:.0%}")
        print(f"\nReasoning:  {decision.reasoning}")

        if decision.entry_price:
            print(f"\nEntry:      ${decision.entry_price:.2f}")
        if decision.stop_loss:
            print(f"Stop Loss:  ${decision.stop_loss:.2f}")
        if decision.take_profit:
            print(f"Target:     ${decision.take_profit:.2f}")

        if decision.entry_price and decision.stop_loss:
            risk = abs(decision.entry_price - decision.stop_loss)
            if decision.take_profit:
                reward = abs(decision.take_profit - decision.entry_price)
                rr = reward / risk if risk > 0 else 0
                print(f"\nRisk:Risk:  {rr:.2f}")

        print("=" * 60)

    except Exception as e:
        logger.error(f"AI analysis failed: {e}", exc_info=True)
    finally:
        session.close()


if __name__ == "__main__":
    main()
