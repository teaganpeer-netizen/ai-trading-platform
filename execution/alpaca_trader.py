"""
Live trading integration with Alpaca Markets API.
"""

from datetime import datetime
import logging
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, OrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from data import get_session, TradeRepository
from risk import CircuitBreaker

logger = logging.getLogger(__name__)


class AlpacaTrader:
    """Live trading via Alpaca Markets API."""

    def __init__(self, api_key: str, secret_key: str, base_url: str):
        """
        Initialize Alpaca trader.

        Args:
            api_key: Alpaca API key
            secret_key: Alpaca secret key
            base_url: Alpaca API URL (paper or live)
        """
        self.client = TradingClient(
            api_key=api_key,
            secret_key=secret_key,
            base_url=base_url,
        )
        self.session = get_session()
        self.trade_repo = TradeRepository(self.session)
        self.is_paper = "paper" in base_url.lower()

        try:
            account = self.client.get_account()
            logger.info(f"✓ Connected to Alpaca ({account.trading_type})")
            logger.info(f"  Portfolio Value: ${account.portfolio_value:,.2f}")
            logger.info(f"  Buying Power: ${account.buying_power:,.2f}")
        except Exception as e:
            logger.error(f"Failed to connect to Alpaca: {e}")
            raise

    def get_account(self) -> dict:
        """Get current account info."""
        try:
            account = self.client.get_account()
            return {
                "portfolio_value": float(account.portfolio_value),
                "cash": float(account.cash),
                "buying_power": float(account.buying_power),
                "trading_type": account.trading_type,
                "account_number": account.account_number,
            }
        except Exception as e:
            logger.error(f"Failed to get account: {e}")
            return {}

    def get_positions(self) -> dict[str, dict]:
        """Get all open positions."""
        try:
            positions = self.client.get_all_positions()
            result = {}
            for pos in positions:
                result[pos.symbol] = {
                    "quantity": float(pos.qty),
                    "entry_price": float(pos.avg_fill_price),
                    "current_price": float(pos.current_price),
                    "market_value": float(pos.market_value),
                    "pnl": float(pos.unrealized_pl),
                    "pnl_pct": float(pos.unrealized_plpc),
                    "side": pos.side.value,
                }
            return result
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return {}

    def buy(
        self,
        symbol: str,
        quantity: float,
        ai_reasoning: str = None,
    ) -> dict | None:
        """
        Place a buy order.

        Args:
            symbol: Stock symbol
            quantity: Number of shares
            ai_reasoning: AI decision reasoning

        Returns:
            Order details or None on failure
        """
        try:
            order_request = MarketOrderRequest(
                symbol=symbol,
                qty=quantity,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY,
            )
            order = self.client.submit_order(order_request)

            logger.info(
                f"BUY {symbol}: {quantity} shares (Order ID: {order.id})"
            )

            # Log to database
            from data import Trade
            trade = Trade(
                symbol=symbol,
                entry_time=datetime.utcnow(),
                entry_price=None,  # Will update when filled
                quantity=quantity,
                trade_type="long",
                status="pending",
                strategy="AI",
                signal_reason=ai_reasoning,
            )
            self.trade_repo.create_trade(trade)

            return {
                "order_id": order.id,
                "symbol": symbol,
                "quantity": quantity,
                "side": "buy",
                "status": order.status.value,
                "submitted_at": order.submitted_at.isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to place buy order for {symbol}: {e}")
            return None

    def sell(
        self,
        symbol: str,
        quantity: float = None,
    ) -> dict | None:
        """
        Place a sell order.

        Args:
            symbol: Stock symbol
            quantity: Number of shares (if None, sell all)

        Returns:
            Order details or None on failure
        """
        try:
            # Get position to determine quantity
            if quantity is None:
                positions = self.client.get_all_positions()
                position = next((p for p in positions if p.symbol == symbol), None)
                if not position:
                    logger.warning(f"No position for {symbol}")
                    return None
                quantity = float(position.qty)

            order_request = MarketOrderRequest(
                symbol=symbol,
                qty=quantity,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.DAY,
            )
            order = self.client.submit_order(order_request)

            logger.info(
                f"SELL {symbol}: {quantity} shares (Order ID: {order.id})"
            )

            return {
                "order_id": order.id,
                "symbol": symbol,
                "quantity": quantity,
                "side": "sell",
                "status": order.status.value,
                "submitted_at": order.submitted_at.isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to place sell order for {symbol}: {e}")
            return None

    def get_orders(self, status: str = None) -> list[dict]:
        """Get recent orders."""
        try:
            orders = self.client.get_orders(status=status)
            return [
                {
                    "id": order.id,
                    "symbol": order.symbol,
                    "quantity": float(order.qty),
                    "side": order.side.value,
                    "status": order.status.value,
                    "submitted_at": order.submitted_at.isoformat(),
                    "filled_qty": float(order.filled_qty),
                    "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
                }
                for order in orders
            ]
        except Exception as e:
            logger.error(f"Failed to get orders: {e}")
            return []

    def close(self):
        """Close database session."""
        self.session.close()
