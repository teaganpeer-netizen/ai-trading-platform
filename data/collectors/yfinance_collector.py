"""
Fetches market data from Yahoo Finance (free, no subscription needed).
"""

from datetime import datetime, timedelta
import logging
import pandas as pd
import yfinance as yf
from data.storage.models import Bar
from data.storage.repositories import BarRepository

logger = logging.getLogger(__name__)


class YFinanceCollector:
    """Fetches historical bars from Yahoo Finance."""

    def fetch_bars(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        interval: str = "1d",
    ) -> list[Bar]:
        """
        Fetch bars from Yahoo Finance.

        Args:
            symbol: Stock symbol (e.g., "AAPL")
            start: Start datetime (inclusive)
            end: End datetime (inclusive)
            interval: Bar interval ("1d", "1h", "15m", etc.)

        Returns:
            List of Bar objects.
        """
        try:
            df = yf.download(symbol, start=start, end=end, interval=interval, progress=False)

            if df.empty:
                logger.warning(f"No data found for {symbol} from {start} to {end}")
                return []

            # yfinance returns MultiIndex columns when downloading a single symbol
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            bars = []
            for timestamp, row in df.iterrows():
                try:
                    bar = Bar(
                        symbol=symbol,
                        timestamp=timestamp.to_pydatetime() if hasattr(timestamp, 'to_pydatetime') else timestamp,
                        open=float(row["Open"]),
                        high=float(row["High"]),
                        low=float(row["Low"]),
                        close=float(row["Close"]),
                        volume=int(row["Volume"]),
                    )
                    bars.append(bar)
                except (TypeError, ValueError) as e:
                    logger.warning(f"Skipping bar for {symbol} at {timestamp}: {e}")
                    continue

            logger.info(f"Fetched {len(bars)} bars for {symbol} from {start} to {end}")
            return bars

        except Exception as e:
            logger.error(f"Failed to fetch bars for {symbol}: {e}")
            raise

    def backfill_symbol(
        self,
        symbol: str,
        bar_repo: BarRepository,
        days_back: int = 252,
        interval: str = "1d",
    ) -> int:
        """
        Backfill historical data for a symbol.

        Args:
            symbol: Stock symbol
            bar_repo: BarRepository instance for storing bars
            days_back: Number of days of history to fetch
            interval: Bar interval

        Returns:
            Count of bars stored.
        """
        end = datetime.utcnow()
        start = end - timedelta(days=days_back)

        # Check if we already have data for this symbol
        latest = bar_repo.get_latest_timestamp(symbol)
        if latest:
            logger.info(f"{symbol}: Latest bar is {latest}, fetching from there...")
            start = latest + timedelta(days=1)

        if start >= end:
            logger.info(f"{symbol}: Already up to date")
            return 0

        bars = self.fetch_bars(symbol, start, end, interval)
        count = bar_repo.upsert_bars(bars)
        logger.info(f"Backfilled {count} bars for {symbol}")
        return count

    def backfill_watchlist(
        self,
        symbols: list[str],
        bar_repo: BarRepository,
        days_back: int = 252,
    ) -> dict[str, int]:
        """Backfill all symbols in a watchlist. Returns symbol -> count map."""
        results = {}
        for symbol in symbols:
            try:
                count = self.backfill_symbol(symbol, bar_repo, days_back)
                results[symbol] = count
            except Exception as e:
                logger.error(f"Failed to backfill {symbol}: {e}")
                results[symbol] = 0
        return results

    @staticmethod
    def get_live_price(symbol: str) -> float | None:
        """
        Fetch the latest traded price for a symbol via yfinance.
        Returns None if the fetch fails (market closed, no internet, etc.).
        """
        try:
            info = yf.Ticker(symbol).fast_info
            price = info.get("last_price") or info.get("previousClose")
            return float(price) if price else None
        except Exception as e:
            logger.warning(f"Could not fetch live price for {symbol}: {e}")
            return None

    @staticmethod
    def get_live_prices(symbols: list[str]) -> dict[str, float]:
        """Fetch live prices for multiple symbols. Missing symbols are omitted."""
        prices = {}
        for symbol in symbols:
            price = YFinanceCollector.get_live_price(symbol)
            if price is not None:
                prices[symbol] = price
        return prices
