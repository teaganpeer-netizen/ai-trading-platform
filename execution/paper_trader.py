"""
Paper trading engine that orchestrates all components.
Simulates real trading with risk management, AI decisions, and Alpaca execution.
"""

from datetime import datetime, timedelta, time as dt_time
from dataclasses import dataclass
from zoneinfo import ZoneInfo
import logging
from data import get_session, BarRepository, BarProcessor, Trade, TradeRepository
from data.collectors.yfinance_collector import YFinanceCollector
from risk import RiskManager, CircuitBreaker, CircuitState
from ai_engine import AIDecisionMaker
from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class TradeExecution:
    """Record of a trade execution."""
    symbol: str
    side: str  # "buy" or "sell"
    quantity: float
    price: float
    timestamp: datetime
    ai_confidence: float = 0.0
    ai_reasoning: str = ""
    status: str = "executed"  # executed, pending, cancelled
    order_id: str = None


class PaperTrader:
    """
    Paper trading engine that executes trades based on AI decisions with risk management.

    Workflow:
    1. Load market data
    2. For each symbol: call AI decision maker
    3. Check risk limits (position size, exposure, circuit breaker)
    4. Execute trade if approved
    5. Track P&L and performance
    """

    def __init__(
        self,
        initial_capital: float = 100_000,
        watchlist: list[str] = None,
    ):
        self.initial_capital = initial_capital
        self.watchlist = watchlist or settings.watchlist
        self.session = get_session()
        self.bar_repo = BarRepository(self.session)
        self.trade_repo = TradeRepository(self.session)

        # Initialize components
        self.risk_manager = RiskManager(
            portfolio_value=initial_capital,
            risk_per_trade_pct=settings.max_risk_per_trade_pct,
            max_daily_loss_pct=settings.daily_loss_limit_pct,
            max_portfolio_exposure_pct=settings.max_portfolio_exposure_pct,
        )

        self.circuit_breaker = CircuitBreaker(
            initial_portfolio_value=initial_capital,
            halt_drawdown_pct=0.15,
            halt_daily_loss_pct=settings.daily_loss_limit_pct,
        )

        self.ai_maker = None
        try:
            self.ai_maker = AIDecisionMaker(api_key=settings.groq_api_key)
            logger.info("✓ AI Decision Maker initialized")
        except Exception as e:
            logger.warning(f"AI Decision Maker unavailable: {e}")

        self.open_positions = {}  # symbol -> (quantity, entry_price, entry_time, ai_confidence)
        self.executions: list[TradeExecution] = []
        self.daily_pnl = 0.0
        self.peak_capital = initial_capital
        self.current_capital = initial_capital

        self._restore_open_positions()
        logger.info(f"✓ Paper Trader initialized (capital: ${initial_capital:,.0f})")

    def _restore_open_positions(self) -> None:
        """Reload open positions from DB so restarts don't cause duplicate buys."""
        open_trades = self.trade_repo.get_open_trades()
        capital_deployed = 0.0
        for trade in open_trades:
            symbol = trade.symbol
            # If multiple DB rows exist for the same symbol (legacy duplicates), keep the latest
            if symbol not in self.open_positions or trade.entry_time > self.open_positions[symbol][2]:
                self.open_positions[symbol] = (
                    trade.quantity,
                    trade.entry_price,
                    trade.entry_time,
                    trade.risk_metric or 0.0,
                    trade.id,
                )
                capital_deployed += trade.quantity * trade.entry_price
        if self.open_positions:
            self.current_capital = max(0.0, self.initial_capital - capital_deployed)
            logger.info(
                f"✓ Restored {len(self.open_positions)} open position(s) from DB "
                f"({', '.join(self.open_positions.keys())})"
            )

    @staticmethod
    def is_market_open() -> bool:
        """Return True only during NYSE regular hours Mon–Fri 9:30–16:00 ET."""
        et = ZoneInfo("America/New_York")
        now = datetime.now(et)
        if now.weekday() >= 5:  # Saturday=5, Sunday=6
            return False
        market_open = dt_time(9, 30)
        market_close = dt_time(16, 0)
        return market_open <= now.time() < market_close

    def run_iteration(self, use_ai: bool = True) -> dict:
        """
        Run one iteration: check all symbols, get signals, execute trades.

        Args:
            use_ai: Whether to use AI for decision making

        Returns:
            Summary of iteration (trades executed, P&L, etc.)
        """
        iteration_start = datetime.utcnow()
        trades_executed = 0

        market_open = self.is_market_open()

        for symbol in self.watchlist:
            try:
                # Always check exits (stop losses run 24/7 to protect positions)
                # Only open new positions during market hours
                self._process_symbol(symbol, use_ai=use_ai, allow_entry=market_open)
                trades_executed += 1
            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")

        # Update portfolio metrics
        portfolio_value = self._calculate_portfolio_value()
        self.risk_manager.update_portfolio_value(portfolio_value)

        # Update circuit breaker
        self.circuit_breaker.update(
            current_portfolio_value=portfolio_value,
            daily_loss_pct=abs(self.daily_pnl) / self.initial_capital if self.daily_pnl < 0 else 0,
        )

        return {
            "timestamp": iteration_start,
            "symbols_processed": len(self.watchlist),
            "positions_open": len(self.open_positions),
            "portfolio_value": portfolio_value,
            "daily_pnl": self.daily_pnl,
            "circuit_state": self.circuit_breaker.state.value,
            "ai_enabled": use_ai and self.ai_maker is not None,
            "market_open": market_open,
        }

    def _process_symbol(self, symbol: str, use_ai: bool = True, allow_entry: bool = True) -> None:
        """Process a single symbol: get signal, execute if valid."""
        # Get latest bars
        bars = self.bar_repo.get_bars(symbol, limit=200)
        if not bars or len(bars) < 50:
            logger.debug(f"Insufficient data for {symbol}")
            return

        df = BarProcessor.to_dataframe(bars)
        df = df.sort_index()
        df = BarProcessor.enrich_bars(df)

        # Use live price if available; fall back to last DB bar
        live = YFinanceCollector.get_live_price(symbol)
        current_price = live if live else df.iloc[-1]["close"]

        # Check if we should close existing position (exits run regardless of market hours)
        if symbol in self.open_positions:
            self._check_close_position(symbol, current_price, df)
            return

        # Don't open new positions outside market hours
        if not allow_entry:
            logger.debug(f"{symbol}: Market closed — skipping entry")
            return

        # Portfolio context needed for both risk checks and AI prompt — always compute it
        portfolio_context = {
            "cash": self.current_capital - sum(
                qty * price for qty, price, _, _, _ in self.open_positions.values()
            ),
            "open_positions": len(self.open_positions),
            "portfolio_value": self._calculate_portfolio_value(),
            "exposure_pct": self.risk_manager.get_exposure(
                {s: p for s, (q, p, _, _, _) in self.open_positions.items()}
            ),
            "daily_pnl": self.daily_pnl,
        }

        # Try to get BUY decision (AI preferred, fallback to technical)
        decision = None

        if use_ai and self.ai_maker:
            try:
                decision = self.ai_maker.analyze_symbol(symbol, df, current_price, portfolio_context)
            except Exception as e:
                logger.debug(f"AI failed for {symbol}: {e}, using technical analysis")
                decision = None

        # Fallback to technical analysis if AI unavailable or failed
        if not decision or decision.action != "BUY":
            decision = self._get_technical_decision(symbol, df, current_price)
            if not decision:
                return

        # Check risk limits
        can_trade, reason = self.risk_manager.can_trade(
            num_open_positions=len(self.open_positions),
            current_exposure_pct=portfolio_context["exposure_pct"],
        )

        if not can_trade:
            logger.info(f"{symbol}: Cannot trade - {reason}")
            return

        can_trade_cb, reason_cb = self.circuit_breaker.can_open_position()
        if not can_trade_cb:
            logger.warning(f"{symbol}: Circuit breaker - {reason_cb}")
            return

        # Execute trade
        self._execute_buy(symbol, current_price, decision)

    def _get_technical_decision(self, symbol: str, df, current_price):
        """Get a trading decision using technical analysis only."""
        from ai_engine import Decision

        try:
            sma_20 = df.iloc[-1].get('sma_20', 0)
            sma_50 = df.iloc[-1].get('sma_50', 0)
            rsi = df.iloc[-1].get('rsi_14', 50)
            atr = df.iloc[-1].get('atr_14', current_price * 0.02)

            # Technical buy signal
            if current_price > sma_20 > sma_50 and rsi < 70:
                stop_loss = current_price - (2 * atr if atr > 0 else current_price * 0.02)
                take_profit = current_price + (3 * atr if atr > 0 else current_price * 0.03)

                return Decision(
                    symbol=symbol,
                    action="BUY",
                    confidence=0.70,
                    entry_price=current_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    reasoning=f"Technical: SMA20(${sma_20:.2f}) > SMA50(${sma_50:.2f}), RSI={rsi:.1f}"
                )

            return None
        except Exception as e:
            logger.debug(f"Technical analysis failed for {symbol}: {e}")
            return None

    def _execute_buy(self, symbol: str, current_price: float, decision) -> None:
        """Execute a buy order."""
        # Position sizing
        stop_loss = decision.stop_loss or (current_price * 0.95)
        position_size = self.risk_manager.calculate_position_size(current_price, stop_loss)

        if position_size <= 0:
            logger.warning(f"{symbol}: Invalid position size")
            return

        # Check we have enough cash
        cost = position_size * current_price
        available_cash = self.current_capital - sum(
            qty * price for qty, price, _, _, _ in self.open_positions.values()
        )

        if cost > available_cash:
            logger.warning(f"{symbol}: Insufficient cash (need ${cost:,.0f}, have ${available_cash:,.0f})")
            return

        # Execute
        self.current_capital -= cost
        trade = Trade(
            symbol=symbol,
            entry_time=datetime.utcnow(),
            entry_price=current_price,
            quantity=position_size,
            trade_type="long",
            status="open",
            strategy="AI",
            signal_reason=decision.reasoning,
            risk_metric=decision.confidence,
        )
        self.trade_repo.create_trade(trade)
        self.open_positions[symbol] = (position_size, current_price, datetime.utcnow(), decision.confidence, trade.id)

        execution = TradeExecution(
            symbol=symbol,
            side="buy",
            quantity=position_size,
            price=current_price,
            timestamp=datetime.utcnow(),
            ai_confidence=decision.confidence,
            ai_reasoning=decision.reasoning,
        )
        self.executions.append(execution)

        logger.info(
            f"BUY {symbol}: {position_size:.2f} @ ${current_price:.2f} "
            f"(confidence {decision.confidence:.0%}, risk ${position_size * (current_price - (decision.stop_loss or current_price * 0.95)):,.2f})"
        )

    def _check_close_position(self, symbol: str, current_price: float, df) -> None:
        """Check if we should close an open position."""
        qty, entry_price, entry_time, ai_conf, trade_id = self.open_positions[symbol]

        # Calculate P&L
        pnl = (current_price - entry_price) * qty
        pnl_pct = (current_price - entry_price) / entry_price

        # Simple exit: close if 2% profit or 1% loss
        should_close = pnl_pct >= 0.02 or pnl_pct <= -0.01

        if not should_close:
            return

        # Close position
        self.current_capital += qty * current_price
        del self.open_positions[symbol]
        self.daily_pnl += pnl

        # Update database
        self.trade_repo.update_trade(
            trade_id=trade_id,
            exit_price=current_price,
            exit_time=datetime.utcnow(),
            pnl=pnl,
            pnl_pct=pnl_pct,
            status="closed",
            is_win=pnl > 0,
        )

        execution = TradeExecution(
            symbol=symbol,
            side="sell",
            quantity=qty,
            price=current_price,
            timestamp=datetime.utcnow(),
            status="executed",
        )
        self.executions.append(execution)

        logger.info(
            f"SELL {symbol}: {qty:.2f} @ ${current_price:.2f} "
            f"PnL: ${pnl:+,.2f} ({pnl_pct:+.2f}%)"
        )

    def _calculate_portfolio_value(self) -> float:
        """Calculate current portfolio value using live prices."""
        current_value = self.current_capital
        for symbol, (qty, entry_price, _, _, _) in self.open_positions.items():
            live = YFinanceCollector.get_live_price(symbol)
            if live:
                current_value += qty * live
            else:
                bars = self.bar_repo.get_bars(symbol, limit=1)
                current_value += qty * (bars[0].close if bars else entry_price)
        return current_value

    def get_summary(self) -> dict:
        """Get performance summary."""
        portfolio_value = self._calculate_portfolio_value()
        total_return = (portfolio_value - self.initial_capital) / self.initial_capital

        return {
            "initial_capital": self.initial_capital,
            "current_capital": portfolio_value,
            "total_return": total_return * 100,
            "daily_pnl": self.daily_pnl,
            "open_positions": len(self.open_positions),
            "executions": len(self.executions),
            "circuit_state": self.circuit_breaker.state.value,
        }

    def close(self):
        """Close all resources."""
        self.session.close()
