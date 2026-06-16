"""
Enhanced MCP tools for richer market context.
Adds news sentiment, economic calendar, options data, and more.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
import yfinance as yf

logger = logging.getLogger(__name__)


class NewsSentimentProvider:
    """Analyzes news sentiment for symbols."""

    @staticmethod
    def get_sentiment_keywords(symbol: str) -> dict:
        """Extract sentiment from symbol-related keywords."""
        try:
            # Try to get news headlines via yfinance
            ticker = yf.Ticker(symbol)
            info = ticker.info

            sentiment_score = 0.0
            keywords = {
                "bullish": ["surge", "soar", "rally", "beat", "upgrade", "buy", "strong", "record"],
                "bearish": ["plunge", "crash", "miss", "downgrade", "sell", "weak", "decline"],
            }

            # Simulate sentiment from available data
            # In production, would use actual news API (NewsAPI, Financial Times, etc.)
            if "fiftyTwoWeekChange" in info:
                change = info.get("fiftyTwoWeekChange", 0)
                if change > 0.3:
                    sentiment_score = 0.7  # Positive
                elif change < -0.3:
                    sentiment_score = 0.3  # Negative
                else:
                    sentiment_score = 0.5  # Neutral

            return {
                "sentiment_score": sentiment_score,  # 0-1, 0.5=neutral
                "sentiment_label": "bullish" if sentiment_score > 0.6 else "bearish" if sentiment_score < 0.4 else "neutral",
                "strength": "strong" if abs(sentiment_score - 0.5) > 0.2 else "mild",
                "data_source": "price_action_proxy",
            }
        except Exception as e:
            logger.warning(f"Failed to get sentiment for {symbol}: {e}")
            return {"sentiment_score": 0.5, "sentiment_label": "neutral"}


class EconomicCalendarProvider:
    """Provides upcoming economic events."""

    @staticmethod
    def get_upcoming_events() -> dict:
        """Get major economic events for the next 7 days."""
        # In production, integrate with FRED, Trading Economics API, or Investopedia
        # For now, provide static common events
        today = datetime.utcnow()

        events = {
            "fed_meetings": [],
            "earnings_announcements": [],
            "economic_reports": [],
            "impact_level": {},
        }

        # Common high-impact events
        common_events = {
            "CPI (Consumer Price Index)": {"impact": "high", "frequency": "monthly"},
            "Federal Reserve Decision": {"impact": "very_high", "frequency": "monthly"},
            "Non-Farm Payroll": {"impact": "very_high", "frequency": "monthly"},
            "GDP Report": {"impact": "high", "frequency": "quarterly"},
            "Unemployment Rate": {"impact": "high", "frequency": "monthly"},
            "Retail Sales": {"impact": "medium", "frequency": "monthly"},
        }

        return {
            "upcoming_events": list(common_events.keys())[:3],  # Top 3 events
            "major_events_next_week": True,
            "fed_decision_soon": False,
            "earnings_season": False,
            "events_info": common_events,
        }

    @staticmethod
    def get_event_impact() -> str:
        """Get current economic event impact summary."""
        events = EconomicCalendarProvider.get_upcoming_events()
        if events.get("upcoming_events"):
            return f"⚠️ Watch for: {', '.join(events['upcoming_events'][:2])}"
        return "Economic calendar clear (low event risk)"


class OptionsDataProvider:
    """Provides options market data and signals."""

    @staticmethod
    def get_iv_metrics(symbol: str) -> dict:
        """Get implied volatility metrics."""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="3mo")

            if hist.empty:
                return {}

            # Calculate simple volatility proxy (no actual IV without options data)
            returns = hist["Close"].pct_change()
            volatility = returns.std() * (252 ** 0.5)

            return {
                "iv_estimate": round(volatility, 4),
                "iv_percentile": "N/A",  # Would need options chain
                "iv_rank": "moderate",
                "put_call_ratio": "N/A",  # Would need options chain
                "skew": "neutral",
            }
        except Exception as e:
            logger.warning(f"Failed to get IV metrics for {symbol}: {e}")
            return {}

    @staticmethod
    def get_options_sentiment(symbol: str) -> dict:
        """Get options market sentiment."""
        # In production, analyze options flow (unusual activity, OTM puts/calls, etc.)
        return {
            "options_sentiment": "neutral",
            "unusual_activity": False,
            "put_call_flow": "balanced",
            "oTM_calls": "normal",
            "oTM_puts": "normal",
            "notes": "Options data requires paid API (InvestorsExchange, Unusual Whales, etc.)",
        }


class MarketBreadthProvider:
    """Provides broad market breadth indicators."""

    @staticmethod
    def get_market_breadth() -> dict:
        """Get market breadth (advances vs declines)."""
        try:
            # Get major indices
            indices = {
                "^GSPC": "S&P 500",
                "^RUT": "Russell 2000",
                "^DJI": "Dow",
            }

            breadth_data = {}
            for ticker, name in indices.items():
                data = yf.Ticker(ticker)
                hist = data.history(period="5d")

                if len(hist) > 1:
                    recent_change = hist["Close"].iloc[-1] - hist["Close"].iloc[0]
                    breadth_data[name] = "up" if recent_change > 0 else "down"

            # Consensus
            consensus = "bullish" if list(breadth_data.values()).count("up") >= 2 else "bearish"

            return {
                "indices": breadth_data,
                "consensus": consensus,
                "market_health": "good" if consensus == "bullish" else "weak",
                "advance_decline_ratio": "N/A",  # Would need tick data
            }
        except Exception as e:
            logger.warning(f"Failed to get market breadth: {e}")
            return {}


class EarningsCalendarProvider:
    """Provides earnings calendar data."""

    @staticmethod
    def get_upcoming_earnings(symbol: str) -> dict:
        """Check if symbol has upcoming earnings."""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            if "nextEarningsDate" in info:
                earnings_date = info.get("nextEarningsDate")
                return {
                    "next_earnings": earnings_date,
                    "days_until_earnings": None,  # Would calculate from date
                    "eps_estimate": info.get("epsEstimate"),
                    "revenue_estimate": info.get("revenueEstimate"),
                    "earnings_soon": True,
                }
            else:
                return {"next_earnings": None, "earnings_soon": False}
        except Exception as e:
            logger.warning(f"Failed to get earnings for {symbol}: {e}")
            return {"earnings_soon": False}


class ComprehensiveMarketContext:
    """Combines all MCP tools for comprehensive context."""

    def __init__(self):
        self.news = NewsSentimentProvider()
        self.calendar = EconomicCalendarProvider()
        self.options = OptionsDataProvider()
        self.breadth = MarketBreadthProvider()
        self.earnings = EarningsCalendarProvider()

    def build_comprehensive_context(self, symbol: str) -> str:
        """Build complete market context for AI decision."""
        context = f"\n🎯 COMPREHENSIVE MARKET CONTEXT FOR {symbol}:\n"

        # News sentiment
        sentiment = self.news.get_sentiment_keywords(symbol)
        context += f"\n📰 News Sentiment:\n"
        context += f"  Score: {sentiment['sentiment_score']:.0%} ({sentiment['sentiment_label']})\n"
        context += f"  Strength: {sentiment['strength']}\n"

        # Economic calendar
        context += f"\n📅 Economic Calendar:\n"
        context += f"  {self.calendar.get_event_impact()}\n"

        # Market breadth
        breadth = self.breadth.get_market_breadth()
        if breadth:
            context += f"\n📊 Market Breadth:\n"
            context += f"  Consensus: {breadth.get('consensus', 'unknown').upper()}\n"
            context += f"  Health: {breadth.get('market_health', 'unknown')}\n"

        # Options sentiment
        options = self.options.get_options_sentiment(symbol)
        context += f"\n📈 Options Market:\n"
        context += f"  Sentiment: {options['options_sentiment']}\n"
        context += f"  Unusual Activity: {'YES ⚠️' if options['unusual_activity'] else 'No'}\n"

        # Earnings
        earnings = self.earnings.get_upcoming_earnings(symbol)
        if earnings.get("earnings_soon"):
            context += f"\n💰 Earnings Alert:\n"
            context += f"  Upcoming earnings detected - higher volatility expected\n"

        context += f"\n═══════════════════════════════════════════\n"

        return context

    def get_market_overview(self) -> str:
        """Quick market health summary used by the CLI."""
        breadth = self.breadth.get_market_breadth()
        if not breadth:
            return None
        consensus = breadth.get("consensus", "unknown").upper()
        indices = breadth.get("indices", {})
        index_str = "  ".join(f"{name}: {'↑' if v == 'up' else '↓'}" for name, v in indices.items())
        event_note = self.calendar.get_event_impact()
        return f"Market {consensus} | {index_str}\n  {event_note}"

    def get_caution_flags(self, symbol: str) -> list[str]:
        """Get any caution flags that should influence trading."""
        flags = []

        # Check earnings
        earnings = self.earnings.get_upcoming_earnings(symbol)
        if earnings.get("earnings_soon"):
            flags.append("⚠️ Earnings coming soon - expect volatility")

        # Check economic calendar
        events = self.calendar.get_upcoming_events()
        if events.get("upcoming_events"):
            flags.append(f"⚠️ Economic event risk: {events['upcoming_events'][0]}")

        # Check sentiment
        sentiment = self.news.get_sentiment_keywords(symbol)
        if sentiment["sentiment_score"] < 0.3:
            flags.append("⚠️ Negative sentiment - proceed with caution")

        return flags
