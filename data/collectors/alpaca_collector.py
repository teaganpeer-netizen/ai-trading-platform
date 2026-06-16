"""
Fetches market data from Alpaca API.
"""

from datetime import datetime, timedelta
import logging
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from config.settings import settings
from data.storage.models import Bar
from data.storage.repositories import BarRepository

logger = logging.getLogger(__name__)


class AlpacaCollector:
    """Fetches historical and streaming bars from Alpaca."""

    def __init__(self):
        self.client = StockHistoricalDataClient(
            api_key=settings.alpaca_api_key,
            secret_key=settings.alpaca_secret_key,
            raw_data=False,
        )

    def fetch_bars(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        timeframe: TimeFrame = TimeFrame.Day,
    ) -> list[Bar]:
        """
        Fetch bars from Alpaca for a given symbol and date range.

        Args:
            symbol: Stock symbol (e.g., "AAPL")
            start: Start datetime (inclusive)
            end: End datetime (inclusive)
            timeframe: Bar timeframe (Day, Hour, Minute, etc.)

        Returns:
            List of Bar objects.
        """
        try:
            request = StockBarsRequest(
                symbol_or_symbols=[symbol],
                timeframe=timeframe,
                start=start,
                end=end,
            )
            bars_data = self.client.get_stock_bars(request)

            bars = []
            for timestamp, bar_data in bars_data[symbol].df.iterrows():
                bar = Bar(
                    symbol=symbol,
                    timestamp=timestamp,
                    open=float(bar_data["open"]),
                    high=float(bar_data["high"]),
                    low=float(bar_data["low"]),
                    close=float(bar_data["close"]),
                    volume=int(bar_data["volume"]),
                    vwap=float(bar_data["vwap"]) if "vwap" in bar_data else None,
                )
                bars.append(bar)

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
        timeframe: TimeFrame = TimeFrame.Day,
    ) -> int:
        """
        Backfill historical data for a symbol.

        Args:
            symbol: Stock symbol
            bar_repo: BarRepository instance for storing bars
            days_back: Number of days of history to fetch
            timeframe: Bar timeframe

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

        bars = self.fetch_bars(symbol, start, end, timeframe)
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
