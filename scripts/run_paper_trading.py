#!/usr/bin/env python
"""
Run paper trading with AI decision engine.

Simulates real trading with risk management, position sizing, and AI signals.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

import logging
import time
from config.settings import settings
from execution import PaperTrader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Run paper trading simulation."""
    logger.info("=" * 60)
    logger.info("Paper Trading Engine Starting")
    logger.info("=" * 60)

    # Initialize trader
    trader = PaperTrader(
        initial_capital=100_000,
        watchlist=settings.watchlist,
    )

    logger.info(f"Watchlist: {', '.join(trader.watchlist)}")

    # Run iterations
    max_iterations = 10
    for iteration in range(1, max_iterations + 1):
        try:
            logger.info(f"\n--- Iteration {iteration} ---")
            result = trader.run_iteration(use_ai=True)

            logger.info(
                f"Portfolio: ${result['portfolio_value']:,.0f} | "
                f"Positions: {result['positions_open']} | "
                f"Daily P&L: ${result['daily_pnl']:+,.2f} | "
                f"Circuit: {result['circuit_state']}"
            )

            # Small delay between iterations (simulate real trading)
            time.sleep(0.5)

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            break
        except Exception as e:
            logger.error(f"Error in iteration {iteration}: {e}", exc_info=True)

    # Print final summary
    logger.info("\n" + "=" * 60)
    logger.info("Paper Trading Summary")
    logger.info("=" * 60)

    summary = trader.get_summary()
    print(f"Initial Capital:     ${summary['initial_capital']:,.2f}")
    print(f"Final Portfolio:     ${summary['current_capital']:,.2f}")
    print(f"Total Return:        {summary['total_return']:+.2f}%")
    print(f"Daily P&L:           ${summary['daily_pnl']:+,.2f}")
    print(f"Open Positions:      {summary['open_positions']}")
    print(f"Total Executions:    {summary['executions']}")
    print(f"Circuit Breaker:     {summary['circuit_state']}")

    print("\n" + "=" * 60)

    trader.close()


if __name__ == "__main__":
    main()
