"""
SQLAlchemy models for market data and trade journal.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, Text, Boolean, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Bar(Base):
    """Market data bar (OHLCV)."""
    __tablename__ = "bars"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False)
    timestamp = Column(DateTime, nullable=False)  # Bar open time
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False, default=0)
    vwap = Column(Float)  # Volume-weighted average price (optional)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_symbol_timestamp", "symbol", "timestamp", unique=True),
        Index("idx_symbol", "symbol"),
        Index("idx_timestamp", "timestamp"),
    )

    def __repr__(self):
        return f"<Bar {self.symbol} {self.timestamp} O:{self.open} C:{self.close}>"


class Trade(Base):
    """Trade journal entry."""
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False)
    entry_time = Column(DateTime, nullable=False)
    exit_time = Column(DateTime)  # Null if still open

    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float)
    quantity = Column(Float, nullable=False)

    pnl = Column(Float)  # P&L in dollars (null if still open)
    pnl_pct = Column(Float)  # P&L as percentage

    trade_type = Column(String(10), nullable=False)  # "long" or "short"
    status = Column(String(20), nullable=False, default="open")  # "open", "closed", "cancelled"

    # AI decision context
    strategy = Column(String(100))  # Which strategy triggered this
    signal_reason = Column(Text)  # Why the AI recommended this trade
    risk_metric = Column(Float)  # Position sizing metric used

    # Metadata
    is_win = Column(Boolean)  # True if profitable
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("idx_symbol_status", "symbol", "status"),
        Index("idx_entry_time", "entry_time"),
    )

    def __repr__(self):
        status_str = f"{self.status}"
        if self.pnl is not None:
            status_str += f" PnL: {self.pnl_pct:+.2f}%"
        return f"<Trade {self.symbol} {self.trade_type} {status_str}>"
