"""
Web dashboard for monitoring AI trading platform.
Reads real-time data from database, not in-memory state.
"""

from flask import Flask, jsonify, render_template
from datetime import datetime
import logging
import sys
from pathlib import Path

project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

from data import get_session, BarRepository, TradeRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

# Initialize components
session = get_session()
bar_repo = BarRepository(session)
trade_repo = TradeRepository(session)

# Portfolio configuration
INITIAL_CAPITAL = 100_000


@app.route("/")
def index():
    """Dashboard home page."""
    return render_template("dashboard.html")


@app.route("/api/account")
def api_account():
    """Get account summary from database."""
    try:
        # Get all open trades
        open_trades = trade_repo.get_open_trades()

        # Calculate portfolio value
        portfolio_value = INITIAL_CAPITAL
        daily_pnl = 0

        for trade in open_trades:
            bars = bar_repo.get_bars(trade.symbol, limit=1)
            if bars:
                current_price = bars[0].close
                # Subtract cost of open positions
                cost = trade.quantity * trade.entry_price
                portfolio_value -= cost
                # Add current value
                current_value = trade.quantity * current_price
                portfolio_value += current_value
                # Track unrealized P&L
                daily_pnl += (current_price - trade.entry_price) * trade.quantity

        # Add closed trades (realized P&L)
        closed_trades = trade_repo.get_closed_trades(limit=100)
        realized_pnl = sum(t.pnl or 0 for t in closed_trades)
        daily_pnl += realized_pnl

        total_return = ((portfolio_value - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100

        return jsonify({
            "portfolio_value": round(portfolio_value, 2),
            "initial_capital": INITIAL_CAPITAL,
            "total_return_pct": round(total_return, 2),
            "daily_pnl": round(daily_pnl, 2),
            "open_positions": len(open_trades),
            "circuit_state": "open",
            "timestamp": datetime.utcnow().isoformat(),
        })
    except Exception as e:
        logger.error(f"Error in api_account: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/positions")
def api_positions():
    """Get open positions from database."""
    try:
        positions = []
        open_trades = trade_repo.get_open_trades()

        for trade in open_trades:
            bars = bar_repo.get_bars(trade.symbol, limit=1)
            current_price = bars[0].close if bars else trade.entry_price

            pnl = (current_price - trade.entry_price) * trade.quantity
            pnl_pct = ((current_price - trade.entry_price) / trade.entry_price) * 100 if trade.entry_price else 0

            positions.append({
                "symbol": trade.symbol,
                "quantity": round(trade.quantity, 2),
                "entry_price": round(trade.entry_price, 2),
                "current_price": round(current_price, 2),
                "position_value": round(trade.quantity * current_price, 2),
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl_pct, 2),
                "ai_confidence": 70,  # From database signal_reason
                "entry_time": trade.entry_time.isoformat(),
            })

        return jsonify(positions)
    except Exception as e:
        logger.error(f"Error in api_positions: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/trades")
def api_trades():
    """Get recent trades from database."""
    try:
        result = []
        trades = trade_repo.get_closed_trades(limit=20)

        for trade in trades:
            result.append({
                "symbol": trade.symbol,
                "entry_price": round(trade.entry_price, 2),
                "exit_price": round(trade.exit_price, 2) if trade.exit_price else None,
                "quantity": round(trade.quantity, 2),
                "pnl": round(trade.pnl, 2) if trade.pnl else None,
                "pnl_pct": round(trade.pnl_pct * 100, 2) if trade.pnl_pct else None,
                "status": trade.status,
                "entry_time": trade.entry_time.isoformat(),
                "exit_time": trade.exit_time.isoformat() if trade.exit_time else None,
                "is_win": "✓" if (trade.pnl and trade.pnl > 0) else "✗",
            })

        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in api_trades: {e}")
        return jsonify({"error": str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}")
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    logger.info("Starting AI Trading Dashboard on http://localhost:8080")
    app.run(debug=True, port=8080)
