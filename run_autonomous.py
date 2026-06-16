"""
Autonomous trading runner - runs for the rest of the NYSE day.
Executes one trade per minute with AI decision making.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from execution import PaperTrader
from datetime import datetime, time
import time as time_module
import logging

logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/autonomous_trading.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def is_market_hours():
    """Check if we're in NYSE trading hours (9:30 AM - 4:00 PM EST)."""
    now = datetime.now()
    market_open = time(9, 30)
    market_close = time(16, 0)
    return market_open <= now.time() <= market_close

def run_autonomous_trading():
    """Run autonomous trading session."""
    logger.info("="*70)
    logger.info("🚀 AUTONOMOUS TRADING SESSION STARTED")
    logger.info("="*70)
    
    trader = PaperTrader(initial_capital=100_000)
    iteration = 0
    
    try:
        while True:
            iteration += 1
            
            # Check market hours
            if not is_market_hours():
                logger.info(f"[{iteration}] Market closed, pausing trades")
                time_module.sleep(60)
                continue
            
            # Run trading iteration
            result = trader.run_iteration(use_ai=True)
            
            portfolio = result['portfolio_value']
            pnl = result['daily_pnl']
            positions = result['positions_open']
            circuit = result['circuit_state']
            
            # Log status
            status = f"[{iteration:4d}] P&L: ${pnl:+8,.0f} | Positions: {positions} | Circuit: {circuit} | Portfolio: ${portfolio:,.0f}"
            logger.info(status)
            
            # Wait 60 seconds before next iteration (1 trade per minute)
            time_module.sleep(60)
            
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
    finally:
        summary = trader.get_summary()
        logger.info("="*70)
        logger.info("📊 SESSION SUMMARY")
        logger.info(f"  Iterations: {iteration}")
        logger.info(f"  Portfolio: ${summary['current_capital']:,.2f}")
        logger.info(f"  Return: {summary['total_return']:+.2f}%")
        logger.info(f"  Daily P&L: ${summary['daily_pnl']:+,.2f}")
        logger.info("="*70)
        trader.close()

if __name__ == "__main__":
    run_autonomous_trading()
