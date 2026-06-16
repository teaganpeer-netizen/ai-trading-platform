"""
Web dashboard for monitoring AI trading platform.
"""

from flask import Flask, jsonify, render_template
from datetime import datetime
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

from config.settings import settings
from data import get_session, BarRepository, TradeRepository
from execution import PaperTrader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

# Initialize components
session = get_session()
bar_repo = BarRepository(session)
trade_repo = TradeRepository(session)
trader = PaperTrader(initial_capital=100_000, watchlist=settings.watchlist)


@app.route("/")
def index():
    """Dashboard home page."""
    return render_template("dashboard.html")


@app.route("/api/account")
def api_account():
    """Get account summary."""
    portfolio_value = trader._calculate_portfolio_value()
    open_positions = len(trader.open_positions)
    total_return = ((portfolio_value - trader.initial_capital) / trader.initial_capital) * 100

    return jsonify({
        "portfolio_value": round(portfolio_value, 2),
        "initial_capital": trader.initial_capital,
        "total_return_pct": round(total_return, 2),
        "daily_pnl": round(trader.daily_pnl, 2),
        "open_positions": open_positions,
        "circuit_state": trader.circuit_breaker.state.value,
        "timestamp": datetime.utcnow().isoformat(),
    })


@app.route("/api/positions")
def api_positions():
    """Get open positions."""
    positions = []
    for symbol, (qty, entry_price, entry_time, confidence) in trader.open_positions.items():
        bars = bar_repo.get_bars(symbol, limit=1)
        current_price = bars[0].close if bars else entry_price

        pnl = (current_price - entry_price) * qty
        pnl_pct = ((current_price - entry_price) / entry_price) * 100

        positions.append({
            "symbol": symbol,
            "quantity": round(qty, 2),
            "entry_price": round(entry_price, 2),
            "current_price": round(current_price, 2),
            "position_value": round(qty * current_price, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "ai_confidence": round(confidence * 100, 0),
            "entry_time": entry_time.isoformat(),
        })

    return jsonify(positions)


@app.route("/api/trades")
def api_trades():
    """Get recent trades."""
    trades = trader.trade_repo.get_closed_trades(limit=20)
    result = []

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
            "is_win": "✓" if trade.is_win else "✗",
        })

    return jsonify(result)


@app.route("/api/performance")
def api_performance():
    """Get performance metrics."""
    trades = trader.trade_repo.get_closed_trades(limit=1000)

    if not trades:
        return jsonify({
            "total_trades": 0,
            "win_rate": 0,
            "avg_win": 0,
            "avg_loss": 0,
            "profit_factor": 0,
        })

    wins = [t for t in trades if t.is_win]
    losses = [t for t in trades if not t.is_win]

    total_pnl = sum(t.pnl for t in trades if t.pnl)
    avg_win = sum(t.pnl for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t.pnl for t in losses) / len(losses) if losses else 0

    profit_factor = 0
    if losses:
        profit_factor = abs(sum(t.pnl for t in wins)) / abs(sum(t.pnl for t in losses))

    return jsonify({
        "total_trades": len(trades),
        "win_rate": round((len(wins) / len(trades) * 100) if trades else 0, 1),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": round(profit_factor, 2),
        "total_pnl": round(total_pnl, 2),
    })


@app.route("/api/health")
def api_health():
    """Health check."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "ai_enabled": trader.ai_maker is not None,
        "watchlist_size": len(trader.watchlist),
    })


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}")
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    logger.info("Starting AI Trading Dashboard on http://localhost:5000")
    app.run(debug=True, port=5000)
