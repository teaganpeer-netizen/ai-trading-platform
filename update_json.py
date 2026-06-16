#!/usr/bin/env python
"""
Updates get_latest_positions.json from latest CSV export.
Run this periodically (or in a loop) to keep HTML dashboard updated.
"""

import sys
from pathlib import Path
import json
import csv
from datetime import datetime
import glob

sys.path.insert(0, str(Path(__file__).parent))

from data import get_session, BarRepository, TradeRepository

def update_json():
    """Update positions JSON from latest data."""
    session = get_session()
    bar_repo = BarRepository(session)
    trade_repo = TradeRepository(session)

    # Get data
    open_trades = trade_repo.get_open_trades()
    open_trades = sorted(open_trades, key=lambda t: t.entry_time, reverse=True)

    # Build positions array
    positions = []
    total_open_value = 0
    total_unrealized_pnl = 0

    for trade in open_trades:
        bars = bar_repo.get_bars(trade.symbol, limit=1)
        current_price = bars[0].close if bars else trade.entry_price

        pnl = (current_price - trade.entry_price) * trade.quantity
        pnl_pct = ((current_price - trade.entry_price) / trade.entry_price * 100) if trade.entry_price else 0
        position_value = trade.quantity * current_price

        total_open_value += position_value
        total_unrealized_pnl += pnl

        positions.append({
            "symbol": trade.symbol,
            "shares": f"{trade.quantity:.2f}",
            "entryPrice": f"{trade.entry_price:.2f}",
            "currentPrice": f"{current_price:.2f}",
            "entryTime": trade.entry_time.strftime('%m/%d/%y %H:%M'),
            "entryConfidence": "70%",
            "unrealizedPnl": f"{pnl:.2f}",
            "pnlPct": f"{pnl_pct:.2f}",
            "positionValue": f"{position_value:.2f}",
        })

    # Create JSON data
    data = {
        "timestamp": datetime.now().isoformat(),
        "openPositions": len(open_trades),
        "positionValue": f"{total_open_value:.2f}",
        "unrealizedPnl": f"{total_unrealized_pnl:.2f}",
        "totalReturnPct": f"{(total_unrealized_pnl / 100000 * 100):.2f}",
        "positions": positions,
    }

    # Write JSON file
    json_path = Path(__file__).parent / "get_latest_positions.json"
    with open(json_path, 'w') as f:
        json.dump(data, f, indent=2)

    session.close()
    return len(positions)

if __name__ == "__main__":
    count = update_json()
    print(f"✓ Updated JSON with {count} positions")
