"""
Main backtesting engine.
"""

from datetime import datetime
import logging
import pandas as pd
from data import get_session, BarRepository, BarProcessor, Trade
from backtesting.strategy import Strategy, Signal
from backtesting.portfolio import Portfolio

logger = logging.getLogger(__name__)


class Backtester:
    """Runs a strategy against historical data."""

    def __init__(
        self,
        strategy: Strategy,
        initial_cash: float = 100_000,
        max_position_size_pct: float = 0.10,
    ):
        self.strategy = strategy
        self.portfolio = Portfolio(initial_cash)
        self.max_position_size_pct = max_position_size_pct
        self.bar_index = 0

    def run(
        self,
        symbols: list[str],
        start_date: datetime = None,
        end_date: datetime = None,
    ) -> dict:
        """
        Run backtest on a set of symbols.

        Args:
            symbols: List of stock symbols
            start_date: Start date (inclusive). If None, use earliest data.
            end_date: End date (inclusive). If None, use latest data.

        Returns:
            Results dict with stats and trades.
        """
        session = get_session()
        bar_repo = BarRepository(session)

        # Load bars for all symbols
        all_bars = {}
        for symbol in symbols:
            bars = bar_repo.get_bars(symbol, limit=10000)  # Get up to 10k bars
            if not bars:
                logger.warning(f"No bars found for {symbol}")
                continue

            # Convert to DataFrame
            df = BarProcessor.to_dataframe(bars)

            # Filter by date range
            if start_date:
                df = df[df.index >= start_date]
            if end_date:
                df = df[df.index <= end_date]

            if df.empty:
                logger.warning(f"No bars for {symbol} in date range")
                continue

            # Sort by timestamp (ascending)
            df = df.sort_index()
            all_bars[symbol] = df

        if not all_bars:
            logger.error("No data available for backtest")
            return {}

        # Initialize strategy
        self.strategy.initialize({
            "initial_cash": self.portfolio.initial_cash,
            "symbols": symbols,
        })

        # Get date range from data
        min_date = min(df.index[0] for df in all_bars.values())
        max_date = max(df.index[-1] for df in all_bars.values())
        logger.info(f"Backtesting from {min_date.date()} to {max_date.date()}")

        # Align all DataFrames to same dates (forward fill missing dates)
        all_dates = pd.DatetimeIndex([])
        for df in all_bars.values():
            all_dates = all_dates.union(df.index)
        all_dates = sorted(all_dates)

        # Walk through each bar date
        for bar_idx, current_date in enumerate(all_dates):
            self.bar_index = bar_idx

            # Get current prices
            current_prices = {}
            for symbol, df in all_bars.items():
                if current_date in df.index:
                    current_prices[symbol] = df.loc[current_date, "close"]
                elif len(df[df.index <= current_date]) > 0:
                    # Use last known price
                    last_idx = len(df[df.index <= current_date]) - 1
                    current_prices[symbol] = df.iloc[last_idx]["close"]

            if not current_prices:
                continue

            # Update portfolio metrics
            portfolio_value = self.portfolio.get_total_value(current_prices)
            self.portfolio.update_max_drawdown(portfolio_value)

            # Call strategy for each symbol
            for symbol in symbols:
                if symbol not in all_bars:
                    continue

                df = all_bars[symbol]
                # Get data up to current date
                df_hist = df[df.index <= current_date]
                if df_hist.empty:
                    continue

                # Call strategy
                signal = self.strategy.on_bar(symbol, df_hist)

                if signal is None:
                    continue

                try:
                    if signal.action == "buy":
                        self._execute_buy(symbol, signal, current_prices[symbol], current_date, bar_idx)
                    elif signal.action == "sell":
                        self._execute_sell(symbol, signal, current_prices[symbol], current_date, bar_idx)
                    elif signal.action == "close":
                        if self.portfolio.get_position(symbol):
                            self._execute_sell(symbol, signal, current_prices[symbol], current_date, bar_idx)
                except Exception as e:
                    logger.error(f"Error executing {signal.action} for {symbol}: {e}")

        # Close any remaining open positions at final prices
        final_prices = {}
        for symbol, df in all_bars.items():
            final_prices[symbol] = df.iloc[-1]["close"]

        for symbol in list(self.portfolio.positions.keys()):
            if symbol in final_prices:
                self._execute_sell(
                    symbol,
                    Signal(symbol, "close", 1.0, "Backtest end"),
                    final_prices[symbol],
                    all_dates[-1],
                    len(all_dates) - 1,
                )

        session.close()
        return self._generate_results()

    def _execute_buy(self, symbol: str, signal, price: float, timestamp: datetime, bar_idx: int) -> None:
        """Execute a buy order."""
        if self.portfolio.get_position(symbol):
            logger.debug(f"Already have position in {symbol}, skipping buy")
            return

        # Position size: max_position_size_pct of portfolio
        portfolio_value = self.portfolio.get_total_value({symbol: price})
        max_investment = portfolio_value * self.max_position_size_pct
        quantity = max_investment / price

        if quantity > 0 and self.portfolio.cash >= max_investment:
            self.portfolio.open_position(symbol, quantity, price, timestamp, bar_idx)
            logger.debug(f"BUY {symbol} x{quantity:.2f} @ ${price:.2f} ({signal.reason})")

    def _execute_sell(self, symbol: str, signal, price: float, timestamp: datetime, bar_idx: int) -> None:
        """Execute a sell order."""
        position = self.portfolio.get_position(symbol)
        if not position:
            logger.debug(f"No position in {symbol}, skipping sell")
            return

        trade = self.portfolio.close_position(symbol, price, timestamp)
        logger.debug(f"SELL {symbol} x{position.quantity:.2f} @ ${price:.2f} PnL: ${trade['pnl']:.2f}")
        self.strategy.on_trade_closed(self.portfolio.trade_count, trade["pnl"], trade["pnl_pct"])

    def _generate_results(self) -> dict:
        """Generate final results."""
        stats = self.portfolio.get_stats()
        return {
            "strategy": self.strategy.name,
            "stats": stats,
            "trades": self.portfolio.closed_trades,
        }
