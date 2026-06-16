"""
Data access layer for querying and storing market data.
"""

from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc
from .models import Bar, Trade


class BarRepository:
    """Access layer for OHLC bars."""

    def __init__(self, session: Session):
        self.session = session

    def get_bars(self, symbol: str, limit: int = 100) -> list[Bar]:
        """Get most recent bars for a symbol."""
        return self.session.query(Bar).filter(
            Bar.symbol == symbol
        ).order_by(desc(Bar.timestamp)).limit(limit).all()

    def get_bars_between(self, symbol: str, start: datetime, end: datetime) -> list[Bar]:
        """Get bars within a time range."""
        return self.session.query(Bar).filter(
            Bar.symbol == symbol,
            Bar.timestamp >= start,
            Bar.timestamp <= end,
        ).order_by(Bar.timestamp).all()

    def upsert_bar(self, bar: Bar) -> Bar:
        """Insert or update a bar (by symbol + timestamp uniqueness)."""
        existing = self.session.query(Bar).filter(
            Bar.symbol == bar.symbol,
            Bar.timestamp == bar.timestamp,
        ).first()

        if existing:
            existing.open = bar.open
            existing.high = bar.high
            existing.low = bar.low
            existing.close = bar.close
            existing.volume = bar.volume
            existing.vwap = bar.vwap
            self.session.commit()
            return existing
        else:
            self.session.add(bar)
            self.session.commit()
            return bar

    def upsert_bars(self, bars: list[Bar]) -> int:
        """Bulk insert/update bars. Returns count of upserted rows."""
        for bar in bars:
            self.upsert_bar(bar)
        return len(bars)

    def get_latest_timestamp(self, symbol: str) -> datetime | None:
        """Get the most recent bar timestamp for a symbol."""
        latest = self.session.query(Bar).filter(
            Bar.symbol == symbol
        ).order_by(desc(Bar.timestamp)).first()
        return latest.timestamp if latest else None


class TradeRepository:
    """Access layer for trade journal."""

    def __init__(self, session: Session):
        self.session = session

    def create_trade(self, trade: Trade) -> Trade:
        """Open a new trade."""
        self.session.add(trade)
        self.session.commit()
        return trade

    def update_trade(self, trade_id: int, **kwargs) -> Trade:
        """Update a trade (typically when closing)."""
        trade = self.session.query(Trade).get(trade_id)
        for key, value in kwargs.items():
            if hasattr(trade, key):
                setattr(trade, key, value)
        self.session.commit()
        return trade

    def get_open_trades(self, symbol: str = None) -> list[Trade]:
        """Get all open trades, optionally filtered by symbol."""
        query = self.session.query(Trade).filter(Trade.status == "open")
        if symbol:
            query = query.filter(Trade.symbol == symbol)
        return query.all()

    def get_closed_trades(self, symbol: str = None, limit: int = 100) -> list[Trade]:
        """Get closed trades, optionally filtered by symbol."""
        query = self.session.query(Trade).filter(
            Trade.status == "closed"
        ).order_by(desc(Trade.exit_time))
        if symbol:
            query = query.filter(Trade.symbol == symbol)
        return query.limit(limit).all()

    def get_pnl_today(self) -> float:
        """Sum P&L for trades closed today."""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        trades = self.session.query(Trade).filter(
            Trade.status == "closed",
            Trade.exit_time >= today,
        ).all()
        return sum(t.pnl for t in trades if t.pnl is not None)
