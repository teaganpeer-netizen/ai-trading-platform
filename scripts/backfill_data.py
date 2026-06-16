#!/usr/bin/env python
"""
Backfill historical market data for watchlist symbols.

Usage:
    python scripts/backfill_data.py                 # Use symbols from .env
    python scripts/backfill_data.py AAPL MSFT GOOGL # Specific symbols
"""

import sys
import os
from pathlib import Path

# Add project root to path so imports work
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

import logging
from datetime import datetime
from config.settings import settings
from data import YFinanceCollector, BarRepository, get_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    symbols = sys.argv[1:] if len(sys.argv) > 1 else settings.watchlist

    if not symbols:
        logger.error("No symbols specified and WATCHLIST is empty")
        return 1

    logger.info(f"Backfilling {len(symbols)} symbols: {', '.join(symbols)}")

    try:
        collector = YFinanceCollector()
        session = get_session()
        bar_repo = BarRepository(session)

        results = collector.backfill_watchlist(symbols, bar_repo, days_back=252)

        logger.info("\n" + "=" * 50)
        logger.info("Backfill Results")
        logger.info("=" * 50)
        for symbol, count in sorted(results.items()):
            logger.info(f"{symbol}: {count} bars")

        total = sum(results.values())
        logger.info(f"\nTotal bars backfilled: {total}")

        session.close()
        return 0

    except Exception as e:
        logger.error(f"Backfill failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
