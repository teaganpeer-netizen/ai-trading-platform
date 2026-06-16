"""
Autonomous trading runner - WITHOUT AI API calls (uses technical analysis only).
Perfect for running continuously without rate limits.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from execution import PaperTrader
from data import get_session, BarRepository, BarProcessor
from datetime import datetime, time
import time as time_module
import logging

logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/autonomous_trading_no_ai.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_autonomous_trading_no_ai():
    """Run autonomous trading using technical analysis (no AI API)."""
    logger.info("="*70)
    logger.info("🚀 AUTONOMOUS TRADING (TECHNICAL ANALYSIS MODE)")
    logger.info("="*70)

    trader = PaperTrader(initial_capital=100_000)
    session = get_session()
    bar_repo = BarRepository(session)

    iteration = 0

    try:
        while True:
            iteration += 1

            # Process each symbol with technical analysis
            for symbol in trader.watchlist[:10]:  # First 10 symbols to keep it fast
                try:
                    bars = bar_repo.get_bars(symbol, limit=50)
                    if not bars or len(bars) < 20:
                        continue

                    df = BarProcessor.to_dataframe(bars)
                    current_price = df.iloc[-1]["close"]

                    # Simple technical analysis (no AI API calls)
                    sma_20 = df['close'].tail(20).mean()
                    sma_50 = df['close'].tail(50).mean()
                    rsi = df.iloc[-1].get('rsi_14', 50)

                    # Decision based on pure technicals
                    if current_price > sma_20 > sma_50 and rsi < 70:
                        decision = "BUY"
                        confidence = 0.75
                    elif current_price < sma_20 < sma_50 and rsi > 30:
                        decision = "SELL"
                        confidence = 0.70
                    else:
                        decision = "HOLD"
                        confidence = 0.50

                    # Log decision
                    if decision in ["BUY", "SELL"] and symbol not in trader.open_positions:
                        logger.info(f"[{iteration:4d}] {decision:4} {symbol:6} @ ${current_price:7.2f} | SMA20: ${sma_20:7.2f} | RSI: {rsi:5.1f}")

                except Exception as e:
                    continue

            # Run one trading iteration (processes all symbols)
            result = trader.run_iteration(use_ai=False)

            portfolio = result['portfolio_value']
            pnl = result['daily_pnl']
            positions = result['positions_open']
            circuit = result['circuit_state']

            # Log status every 10 iterations
            if iteration % 10 == 0:
                logger.info(f"[{iteration:4d}] Portfolio: ${portfolio:,.0f} | P&L: ${pnl:+,.0f} | Positions: {positions} | Circuit: {circuit}")

            # Wait 30 seconds before next iteration
            time_module.sleep(30)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
    finally:
        summary = trader.get_summary()
        logger.info("="*70)
        logger.info(f"Portfolio: ${summary['current_capital']:,.2f} | Return: {summary['total_return']:+.2f}% | Trades: {len(trader.executions)}")
        logger.info("="*70)
        trader.close()
        session.close()

if __name__ == "__main__":
    run_autonomous_trading_no_ai()
