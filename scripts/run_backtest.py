#!/usr/bin/env python
"""
Run a backtest on historical data.

Usage:
    python scripts/run_backtest.py --strategy sma --symbols SPY AAPL
    python scripts/run_backtest.py --strategy rsi --symbols MSFT GOOGL AMZN
"""

import sys
from pathlib import Path
from datetime import datetime
import logging

# Add project root to path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

import argparse
from backtesting.backtester import Backtester
from backtesting.strategies import SMACrossoverStrategy, RSIStrategy, MACDStrategy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


STRATEGIES = {
    "sma": SMACrossoverStrategy,
    "rsi": RSIStrategy,
    "macd": MACDStrategy,
}


def format_results(results: dict) -> None:
    """Print backtest results."""
    if not results:
        logger.error("No results")
        return

    stats = results.get("stats", {})

    print("\n" + "=" * 60)
    print(f"Backtest Results: {results.get('strategy', 'Unknown')}")
    print("=" * 60)

    print(f"\nCapital:")
    print(f"  Initial:     ${stats.get('initial_cash', 0):,.2f}")
    print(f"  Final:       ${stats.get('final_value', 0):,.2f}")

    print(f"\nPerformance:")
    print(f"  Total Return: {stats.get('total_return_pct', 0):+.2f}%")
    print(f"  Max Drawdown: {stats.get('max_drawdown', 0):-.2f}%")

    print(f"\nTrades:")
    print(f"  Total:       {stats.get('trades', 0)}")
    print(f"  Win Rate:    {stats.get('win_rate', 0):.1f}%")
    print(f"  Avg Win:     ${stats.get('avg_win', 0):,.2f}")
    print(f"  Avg Loss:    ${stats.get('avg_loss', 0):,.2f}")
    profit_factor = stats.get('profit_factor', 0)
    if profit_factor == float('inf'):
        print(f"  Profit Factor: ∞ (no losses)")
    else:
        print(f"  Profit Factor: {profit_factor:.2f}")

    print("\n" + "=" * 60)

    # Show recent trades
    trades = results.get("trades", [])
    if trades:
        print(f"\nLast 5 Trades:")
        for trade in trades[-5:]:
            status = "✓ WIN" if trade["is_win"] else "✗ LOSS"
            print(f"  {trade['symbol']}: {status} ${trade['pnl']:+.2f} ({trade['pnl_pct']:+.2f}%)")


def main():
    parser = argparse.ArgumentParser(description="Run a backtest")
    parser.add_argument(
        "--strategy",
        choices=list(STRATEGIES.keys()),
        default="sma",
        help="Strategy to test (default: sma)",
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=["SPY"],
        help="Symbols to trade (default: SPY)",
    )
    parser.add_argument(
        "--initial-cash",
        type=float,
        default=100_000,
        help="Initial cash (default: 100000)",
    )
    parser.add_argument(
        "--max-position-pct",
        type=float,
        default=0.10,
        help="Max position size as % of portfolio (default: 0.10)",
    )
    parser.add_argument(
        "--start-date",
        help="Start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end-date",
        help="End date (YYYY-MM-DD)",
    )

    args = parser.parse_args()

    # Create strategy
    strategy_class = STRATEGIES[args.strategy]
    strategy = strategy_class()

    # Create backtester
    backtester = Backtester(
        strategy=strategy,
        initial_cash=args.initial_cash,
        max_position_size_pct=args.max_position_pct,
    )

    # Parse dates
    start_date = datetime.strptime(args.start_date, "%Y-%m-%d") if args.start_date else None
    end_date = datetime.strptime(args.end_date, "%Y-%m-%d") if args.end_date else None

    # Run backtest
    logger.info(f"Running {args.strategy.upper()} backtest on {args.symbols}")
    results = backtester.run(
        symbols=args.symbols,
        start_date=start_date,
        end_date=end_date,
    )

    format_results(results)


if __name__ == "__main__":
    main()
