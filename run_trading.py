"""
Autonomous trading runner - HYBRID MODE
Uses AI (Groq LLM) when available, falls back to technical analysis when rate-limited.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from execution import PaperTrader
from data import get_session, BarRepository, BarProcessor
from ai_engine import AIDecisionMaker
from config.settings import settings
from datetime import datetime, time
import time as time_module
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/autonomous_trading_hybrid.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class HybridTrader:
    """Trades with AI when available, falls back to technicals when rate-limited."""

    def __init__(self):
        self.trader = PaperTrader(initial_capital=100_000)
        self.session = get_session()
        self.bar_repo = BarRepository(self.session)
        self.ai_maker = None
        self.ai_available = False
        self.iteration = 0
        self.last_ai_error_time = None

        self._init_ai()

    def _init_ai(self):
        """Try to initialize AI."""
        try:
            self.ai_maker = AIDecisionMaker(api_key=settings.groq_api_key)
            self.ai_available = True
            logger.info("✓ AI Decision Maker initialized")
        except Exception as e:
            logger.warning(f"AI unavailable (will use technicals): {e}")
            self.ai_available = False

    def _get_ai_decision(self, symbol, df, current_price):
        """Get AI decision if available."""
        try:
            decision = self.ai_maker.analyze_symbol(symbol, df, current_price)
            if decision and decision.action in ["BUY", "SELL"]:
                return decision.action, decision.confidence
        except Exception as e:
            if "rate_limit" in str(e).lower():
                self.ai_available = False
                self.last_ai_error_time = datetime.now()
                logger.warning("⚠️  AI rate limited - switching to technical analysis")
            return None, None
        return None, None

    def _get_technical_decision(self, df):
        """Get decision based on technical analysis."""
        if len(df) < 50:
            return "HOLD", 0.5

        current_price = df.iloc[-1]["close"]
        sma_20 = df['close'].tail(20).mean()
        sma_50 = df['close'].tail(50).mean()
        rsi = df.iloc[-1].get('rsi_14', 50)

        if current_price > sma_20 > sma_50 and rsi < 70:
            return "BUY", 0.70
        elif current_price < sma_20 < sma_50 and rsi > 30:
            return "SELL", 0.65
        else:
            return "HOLD", 0.50

    def _check_ai_recovery(self):
        """Check if AI is available again after rate limit."""
        if not self.ai_available and self.last_ai_error_time:
            elapsed = (datetime.now() - self.last_ai_error_time).total_seconds()
            if elapsed > 120:  # Check every 2 minutes
                try:
                    test_decision = self.ai_maker.analyze_symbol("SPY", None, 100)
                    self.ai_available = True
                    logger.info("✓ AI recovered - resuming AI-powered trading")
                except:
                    pass

    def run(self):
        """Run autonomous trading."""
        logger.info("="*70)
        logger.info("🤖 HYBRID TRADING (AI + Technical Analysis Fallback)")
        logger.info("="*70)

        try:
            while True:
                self.iteration += 1

                # Check if AI recovered from rate limit
                self._check_ai_recovery()

                # Run one trading iteration
                result = self.trader.run_iteration(use_ai=self.ai_available)

                portfolio = result['portfolio_value']
                pnl = result['daily_pnl']
                positions = result['positions_open']
                circuit = result['circuit_state']

                # Log status every 5 iterations
                if self.iteration % 5 == 0:
                    mode = "🤖 AI" if self.ai_available else "📊 TECH"
                    mkt = "OPEN" if result.get("market_open") else "CLOSED"
                    logger.info(f"[{self.iteration:4d}] {mode} | Market: {mkt} | Portfolio: ${portfolio:,.0f} | P&L: ${pnl:+,.0f} | Pos: {positions} | {circuit}")

                # Wait before next iteration
                time_module.sleep(30)

        except KeyboardInterrupt:
            logger.info("Stopped by user")
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
        finally:
            summary = self.trader.get_summary()
            logger.info("="*70)
            logger.info(f"Final: ${summary['current_capital']:,.2f} | Return: {summary['total_return']:+.2f}% | Trades: {len(self.trader.executions)}")
            logger.info("="*70)
            self.trader.close()
            self.session.close()

if __name__ == "__main__":
    trader = HybridTrader()
    trader.run()
