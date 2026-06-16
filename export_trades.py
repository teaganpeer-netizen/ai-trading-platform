#!/usr/bin/env python
"""
Export trading data to CSV (for Excel/Google Sheets).
Run this anytime to get current positions + trade history.
"""

import sys
from pathlib import Path
import csv
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from data import get_session, BarRepository, TradeRepository

def export_trades():
    """Export all trades to CSV."""
    session = get_session()
    bar_repo = BarRepository(session)
    trade_repo = TradeRepository(session)

    # Get data
    open_trades = trade_repo.get_open_trades()
    closed_trades = trade_repo.get_closed_trades(limit=100)

    # Write to CSV
    filename = f"trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)

        # Header
        writer.writerow(['OPEN POSITIONS'])
        writer.writerow(['Symbol', 'Quantity', 'Entry Price', 'Current Price', 'Entry Time', 'P&L', 'P&L %'])

        # Open positions
        for trade in open_trades:
            bars = bar_repo.get_bars(trade.symbol, limit=1)
            current_price = bars[0].close if bars else trade.entry_price
            pnl = (current_price - trade.entry_price) * trade.quantity
            pnl_pct = ((current_price - trade.entry_price) / trade.entry_price * 100) if trade.entry_price else 0

            writer.writerow([
                trade.symbol,
                f"{trade.quantity:.2f}",
                f"${trade.entry_price:.2f}",
                f"${current_price:.2f}",
                trade.entry_time.strftime('%Y-%m-%d %H:%M:%S'),
                f"${pnl:.2f}",
                f"{pnl_pct:.2f}%",
            ])

        # Closed trades
        writer.writerow([])
        writer.writerow(['CLOSED TRADES'])
        writer.writerow(['Symbol', 'Entry Price', 'Exit Price', 'Quantity', 'P&L', 'P&L %', 'Exit Time'])

        for trade in closed_trades:
            writer.writerow([
                trade.symbol,
                f"${trade.entry_price:.2f}",
                f"${trade.exit_price:.2f}" if trade.exit_price else '',
                f"{trade.quantity:.2f}",
                f"${trade.pnl:.2f}" if trade.pnl else '',
                f"{trade.pnl_pct * 100:.2f}%" if trade.pnl_pct else '',
                trade.exit_time.strftime('%Y-%m-%d %H:%M:%S') if trade.exit_time else '',
            ])

        # Summary
        writer.writerow([])
        writer.writerow(['SUMMARY'])
        open_value = sum(trade.quantity * (bar_repo.get_bars(trade.symbol, limit=1)[0].close if bar_repo.get_bars(trade.symbol, limit=1) else trade.entry_price) for trade in open_trades)
        realized_pnl = sum(trade.pnl or 0 for trade in closed_trades)

        writer.writerow(['Open Positions Value', f"${open_value:.2f}"])
        writer.writerow(['Realized P&L', f"${realized_pnl:.2f}"])
        writer.writerow(['Total Trades', len(open_trades) + len(closed_trades)])

    print(f"✓ Exported to: {filename}")
    print(f"  Open positions: {len(open_trades)}")
    print(f"  Closed trades: {len(closed_trades)}")

    session.close()

if __name__ == "__main__":
    export_trades()
