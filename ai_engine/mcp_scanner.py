"""
Market Scanner MCP - Finds high-probability trading candidates.
Discovers opportunities without relying on pre-set watchlist.
"""

import logging
from typing import Optional
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class MarketScanner:
    """Scans market for trading opportunities."""

    # Popular liquid stocks to scan
    LIQUID_UNIVERSE = [
        # Mega cap (high volume)
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
        # Large cap tech
        "AMD", "INTC", "NFLX", "ADBE", "ASML", "AVGO",
        # Financial
        "JPM", "BAC", "GS", "MS", "C", "WFC",
        # Healthcare
        "JNJ", "UNH", "PFE", "ABBV", "TMO", "LLY",
        # Consumer
        "WMT", "MCD", "KO", "PEP", "NKE", "MCD",
        # Energy
        "XOM", "CVX", "COP", "SLB", "EOG",
        # Indices
        "SPY", "QQQ", "IWM", "DIA",
    ]

    def __init__(self, universe: Optional[list] = None):
        self.universe = universe or self.LIQUID_UNIVERSE
        logger.info(f"Scanner initialized with {len(self.universe)} symbols")

    def find_high_gainers(self, period: str = "1d", top_n: int = 10) -> dict:
        """Find top gainers in the market."""
        gainers = {}

        for symbol in self.universe:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period=period)

                if len(hist) < 2:
                    continue

                current = hist.iloc[-1]["Close"]
                previous = hist.iloc[0]["Close"]
                change_pct = ((current - previous) / previous * 100) if previous != 0 else 0

                if change_pct > 0:  # Only gainers
                    volume = hist.iloc[-1].get("Volume", 0)
                    gainers[symbol] = {
                        "change_pct": round(change_pct, 2),
                        "current_price": round(current, 2),
                        "volume": int(volume),
                        "momentum": "strong" if change_pct > 5 else "moderate" if change_pct > 2 else "mild",
                    }
            except Exception as e:
                logger.debug(f"Failed to scan {symbol}: {e}")
                continue

        # Sort by % change descending
        sorted_gainers = dict(sorted(gainers.items(), key=lambda x: x[1]["change_pct"], reverse=True))
        return dict(list(sorted_gainers.items())[:top_n])

    def find_volume_spikes(self, threshold_multiplier: float = 2.0, top_n: int = 10) -> dict:
        """Find stocks with unusual volume spikes."""
        volume_spikes = {}

        for symbol in self.universe:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="30d")

                if len(hist) < 10:
                    continue

                current_volume = hist.iloc[-1]["Volume"]
                avg_volume = hist["Volume"].iloc[-20:].mean()
                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0

                if volume_ratio > threshold_multiplier:
                    current_price = hist.iloc[-1]["Close"]
                    prev_close = hist.iloc[-2]["Close"]
                    price_change = ((current_price - prev_close) / prev_close * 100) if prev_close != 0 else 0

                    volume_spikes[symbol] = {
                        "volume_ratio": round(volume_ratio, 2),
                        "current_volume": int(current_volume),
                        "avg_volume": int(avg_volume),
                        "price_change": round(price_change, 2),
                        "signal_strength": "very_strong" if volume_ratio > 4 else "strong" if volume_ratio > 2.5 else "moderate",
                    }
            except Exception as e:
                logger.debug(f"Failed to scan volume for {symbol}: {e}")
                continue

        sorted_spikes = dict(sorted(volume_spikes.items(), key=lambda x: x[1]["volume_ratio"], reverse=True))
        return dict(list(sorted_spikes.items())[:top_n])

    def find_breakout_candidates(self, period_days: int = 252, top_n: int = 10) -> dict:
        """Find stocks breaking out of resistance."""
        breakouts = {}

        for symbol in self.universe:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period=f"{period_days}d")

                if len(hist) < 50:
                    continue

                # Simple breakout: price > 52-week high in last 3 days
                high_52w = hist["High"].iloc[-252:].max() if len(hist) >= 252 else hist["High"].max()
                current_price = hist.iloc[-1]["Close"]
                recent_high = hist["High"].iloc[-3:].max()

                if current_price >= high_52w and current_price == recent_high:
                    volume_trend = hist["Volume"].iloc[-5:].mean() / hist["Volume"].iloc[-20:].mean()

                    breakouts[symbol] = {
                        "current_price": round(current_price, 2),
                        "resistance_level": round(high_52w, 2),
                        "breakout_strength": "strong" if volume_trend > 1.5 else "weak",
                        "volume_confirmation": round(volume_trend, 2),
                    }
            except Exception as e:
                logger.debug(f"Failed to find breakout for {symbol}: {e}")
                continue

        return dict(list(breakouts.items())[:top_n])

    def find_momentum_stocks(self, lookback_days: int = 5, top_n: int = 10) -> dict:
        """Find stocks with positive momentum."""
        momentum_stocks = {}

        for symbol in self.universe:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="20d")

                if len(hist) < lookback_days:
                    continue

                # Calculate momentum: % change over lookback period
                start_price = hist.iloc[-lookback_days]["Close"]
                current_price = hist.iloc[-1]["Close"]
                momentum_pct = ((current_price - start_price) / start_price * 100) if start_price != 0 else 0

                # Also check trend consistency
                closes = hist["Close"].iloc[-lookback_days:].values
                is_uptrend = all(closes[i] <= closes[i+1] for i in range(len(closes)-1))

                if momentum_pct > 0 and is_uptrend:
                    momentum_stocks[symbol] = {
                        "momentum_pct": round(momentum_pct, 2),
                        "current_price": round(current_price, 2),
                        "trend_consistency": "consistent" if is_uptrend else "inconsistent",
                        "strength": "very_strong" if momentum_pct > 10 else "strong" if momentum_pct > 5 else "moderate",
                    }
            except Exception as e:
                logger.debug(f"Failed to find momentum for {symbol}: {e}")
                continue

        sorted_momentum = dict(sorted(momentum_stocks.items(), key=lambda x: x[1]["momentum_pct"], reverse=True))
        return dict(list(sorted_momentum.items())[:top_n])

    def run_full_scan(self, top_n: int = 5) -> dict:
        """Run all scans and return comprehensive opportunity list."""
        logger.info("Running full market scan...")

        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "scan_type": "comprehensive",
            "gainers": self.find_high_gainers(top_n=top_n),
            "volume_spikes": self.find_volume_spikes(top_n=top_n),
            "breakouts": self.find_breakout_candidates(top_n=top_n),
            "momentum": self.find_momentum_stocks(top_n=top_n),
        }

        # Build opportunity list (deduplicated, scored)
        opportunities = self._score_opportunities(results, top_n)
        results["top_opportunities"] = opportunities

        return results

    def _score_opportunities(self, scan_results: dict, top_n: int = 5) -> list:
        """Score opportunities across all scans."""
        opportunity_scores = {}

        # Score gainers
        for symbol, data in scan_results.get("gainers", {}).items():
            opportunity_scores[symbol] = opportunity_scores.get(symbol, 0) + 2

        # Score volume spikes
        for symbol, data in scan_results.get("volume_spikes", {}).items():
            opportunity_scores[symbol] = opportunity_scores.get(symbol, 0) + 3

        # Score breakouts
        for symbol, data in scan_results.get("breakouts", {}).items():
            opportunity_scores[symbol] = opportunity_scores.get(symbol, 0) + 4

        # Score momentum
        for symbol, data in scan_results.get("momentum", {}).items():
            opportunity_scores[symbol] = opportunity_scores.get(symbol, 0) + 2

        # Sort and return top opportunities
        sorted_opps = sorted(opportunity_scores.items(), key=lambda x: x[1], reverse=True)
        return [{"symbol": sym, "score": score} for sym, score in sorted_opps[:top_n]]

    def get_scan_summary(self, results: dict) -> str:
        """Generate text summary of scan results."""
        summary = "\n🔍 MARKET SCAN RESULTS\n"
        summary += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

        summary += f"\n🏆 Top Opportunities (Multi-Scan Confirmed):\n"
        for opp in results.get("top_opportunities", [])[:5]:
            summary += f"  • {opp['symbol']} (Score: {opp['score']})\n"

        summary += f"\n📈 Top Gainers:\n"
        for symbol, data in list(results.get("gainers", {}).items())[:3]:
            summary += f"  • {symbol}: +{data['change_pct']:.1f}% ({data['momentum']} momentum)\n"

        summary += f"\n📊 Volume Spikes:\n"
        for symbol, data in list(results.get("volume_spikes", {}).items())[:3]:
            summary += f"  • {symbol}: {data['volume_ratio']:.1f}x volume ({data['signal_strength']})\n"

        summary += f"\n⬆️  Breakouts:\n"
        for symbol, data in list(results.get("breakouts", {}).items())[:3]:
            summary += f"  • {symbol}: ${data['current_price']} (above ${data['resistance_level']})\n"

        summary += f"\n💨 Momentum Stocks:\n"
        for symbol, data in list(results.get("momentum", {}).items())[:3]:
            summary += f"  • {symbol}: +{data['momentum_pct']:.1f}% momentum ({data['strength']})\n"

        return summary
