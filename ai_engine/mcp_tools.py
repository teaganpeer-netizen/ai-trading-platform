"""
MCP Tools integration for enhanced market analysis.
Provides real-time market context to the AI decision maker.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
import yfinance as yf

logger = logging.getLogger(__name__)


class MarketContextProvider:
    """Provides real-time market context for AI decision making."""

    def get_market_overview(self) -> dict:
        """Get current market conditions and sentiment."""
        try:
            # Get major indices
            indices = {
                "^GSPC": "S&P 500",
                "^IXIC": "NASDAQ",
                "^DJI": "Dow Jones",
                "^VIX": "VIX (Volatility)",
            }

            overview = {}
            for ticker, name in indices.items():
                data = yf.Ticker(ticker)
                hist = data.history(period="1d")
                if not hist.empty:
                    current = hist.iloc[-1]["Close"]
                    prev = hist.iloc[0]["Close"] if len(hist) > 1 else current
                    change_pct = ((current - prev) / prev * 100) if prev != 0 else 0
                    overview[name] = {
                        "price": round(current, 2),
                        "change_pct": round(change_pct, 2),
                        "direction": "up" if change_pct > 0 else "down" if change_pct < 0 else "flat",
                    }

            return overview
        except Exception as e:
            logger.warning(f"Failed to get market overview: {e}")
            return {}

    def get_sector_performance(self) -> dict:
        """Get sector performance."""
        sector_etfs = {
            "XLK": "Technology",
            "XLF": "Financials",
            "XLE": "Energy",
            "XLV": "Healthcare",
            "XLI": "Industrials",
            "XLY": "Consumer Discretionary",
            "XLP": "Consumer Staples",
            "XLRE": "Real Estate",
            "XLU": "Utilities",
        }

        performance = {}
        for ticker, sector in sector_etfs.items():
            try:
                data = yf.Ticker(ticker)
                hist = data.history(period="5d")
                if len(hist) > 1:
                    current = hist.iloc[-1]["Close"]
                    prev = hist.iloc[0]["Close"]
                    change_pct = ((current - prev) / prev * 100) if prev != 0 else 0
                    performance[sector] = {
                        "ticker": ticker,
                        "change_5d_pct": round(change_pct, 2),
                        "strength": "strong" if change_pct > 2 else "weak" if change_pct < -2 else "neutral",
                    }
            except Exception as e:
                logger.debug(f"Failed to get {sector} performance: {e}")

        return performance

    def get_correlation_analysis(self, symbols: list[str]) -> dict:
        """Analyze correlations between symbols."""
        try:
            import pandas as pd

            # Download data
            data = yf.download(" ".join(symbols), period="3mo", progress=False)
            if data.empty:
                return {}

            # Get closing prices
            closes = data["Close"] if isinstance(data.columns, pd.MultiIndex) else data[["Close"]]

            # Calculate correlation
            if isinstance(closes, pd.DataFrame):
                corr_matrix = closes.corr()
            else:
                return {}

            # Format output
            correlations = {}
            for i, sym1 in enumerate(symbols):
                correlations[sym1] = {}
                for j, sym2 in enumerate(symbols):
                    if i != j and sym1 in corr_matrix.index and sym2 in corr_matrix.columns:
                        corr_value = corr_matrix.loc[sym1, sym2]
                        correlations[sym1][sym2] = round(float(corr_value), 3)

            return correlations
        except Exception as e:
            logger.warning(f"Failed to analyze correlations: {e}")
            return {}

    def get_volatility_context(self, symbol: str) -> dict:
        """Get volatility information for a symbol."""
        try:
            data = yf.Ticker(symbol)
            hist = data.history(period="3mo")

            if hist.empty:
                return {}

            # Calculate volatility metrics
            returns = hist["Close"].pct_change()
            volatility = returns.std() * (252 ** 0.5)  # Annualized
            recent_vol = returns.tail(20).std() * (252 ** 0.5)

            # Get historical volatility range
            high_vol = returns.rolling(20).std().max() * (252 ** 0.5)
            low_vol = returns.rolling(20).std().min() * (252 ** 0.5)

            return {
                "current_volatility": round(volatility, 4),
                "recent_volatility": round(recent_vol, 4),
                "high_volatility": round(high_vol, 4),
                "low_volatility": round(low_vol, 4),
                "vol_percentile": round(
                    (recent_vol - low_vol) / (high_vol - low_vol) * 100 if high_vol > low_vol else 50, 1
                ),
            }
        except Exception as e:
            logger.warning(f"Failed to get volatility for {symbol}: {e}")
            return {}

    def get_trend_strength(self, symbol: str) -> dict:
        """Analyze trend strength."""
        try:
            data = yf.Ticker(symbol)
            hist = data.history(period="6mo")

            if len(hist) < 50:
                return {}

            closes = hist["Close"]

            # Calculate trend metrics
            sma_20 = closes.rolling(20).mean().iloc[-1]
            sma_50 = closes.rolling(50).mean().iloc[-1]
            sma_200 = closes.rolling(200).mean().iloc[-1] if len(hist) >= 200 else None

            current_price = closes.iloc[-1]

            # Determine trend
            trend = "uptrend" if current_price > sma_50 > sma_200 else "downtrend" if current_price < sma_50 < sma_200 else "sideways"

            # Calculate trend strength (how far from averages)
            strength_50 = abs((current_price - sma_50) / sma_50 * 100)
            strength_200 = abs((current_price - sma_200) / sma_200 * 100) if sma_200 else 0

            return {
                "current_price": round(current_price, 2),
                "sma_20": round(sma_20, 2),
                "sma_50": round(sma_50, 2),
                "sma_200": round(sma_200, 2) if sma_200 else None,
                "trend": trend,
                "strength_vs_50": round(strength_50, 2),
                "strength_vs_200": round(strength_200, 2),
            }
        except Exception as e:
            logger.warning(f"Failed to analyze trend for {symbol}: {e}")
            return {}

    def build_ai_context(self, symbol: str, symbols_list: Optional[list] = None) -> str:
        """Build comprehensive market context for AI."""
        context = f"\n📊 MARKET CONTEXT FOR {symbol}:\n"

        # Market overview
        overview = self.get_market_overview()
        if overview:
            context += "\nMarket Status:\n"
            for market, data in overview.items():
                direction = "📈" if data["direction"] == "up" else "📉" if data["direction"] == "down" else "➡️"
                context += f"  {direction} {market}: {data['change_pct']:+.2f}%\n"

        # Volatility
        vol = self.get_volatility_context(symbol)
        if vol:
            context += f"\nVolatility:\n"
            context += f"  Current: {vol['current_volatility']:.2%} (annualized)\n"
            context += f"  Recent (20d): {vol['recent_volatility']:.2%}\n"
            context += f"  Percentile: {vol['vol_percentile']:.0f}% (0=low, 100=high)\n"

        # Trend
        trend = self.get_trend_strength(symbol)
        if trend:
            context += f"\nTrend Analysis:\n"
            context += f"  Trend: {trend['trend'].upper()}\n"
            context += f"  Price: ${trend['current_price']}\n"
            context += f"  Distance from SMA50: {trend['strength_vs_50']:.2f}%\n"

        # Sector performance
        sector_perf = self.get_sector_performance()
        if sector_perf:
            context += "\nSector Momentum:\n"
            for sector, data in list(sector_perf.items())[:5]:
                context += f"  {sector}: {data['change_5d_pct']:+.2f}% ({data['strength']})\n"

        return context
