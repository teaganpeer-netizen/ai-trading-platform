"""
Market Scanner MCP - Finds high-probability trading candidates.
Discovers opportunities without relying on pre-set watchlist.
"""

import io
import logging
from typing import Optional
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Cached S&P 500 list so we don't hit Wikipedia on every scan
_SP500_CACHE: list[str] | None = None


def _fetch_sp500_tickers() -> list[str]:
    """Pull the current S&P 500 ticker list from Wikipedia. Cached after first call."""
    global _SP500_CACHE
    if _SP500_CACHE:
        return _SP500_CACHE
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; trading-scanner/1.0)"}
        resp = requests.get(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()
        table = pd.read_html(io.StringIO(resp.text), header=0)[0]
        tickers = table["Symbol"].str.replace(".", "-", regex=False).tolist()
        # Add major sector ETFs for breadth
        tickers += ["SPY", "QQQ", "IWM", "DIA", "XLK", "XLF", "XLE", "XLV", "XLI"]
        _SP500_CACHE = sorted(set(tickers))
        logger.info(f"Loaded {len(_SP500_CACHE)} symbols from S&P 500 + ETFs")
        return _SP500_CACHE
    except Exception as e:
        logger.warning(f"Could not fetch S&P 500 list ({e}), falling back to core universe")
        return _CORE_UNIVERSE


# Fallback if Wikipedia is unreachable
_CORE_UNIVERSE = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AMD", "INTC",
    "NFLX", "ADBE", "ASML", "AVGO", "JPM", "BAC", "GS", "MS", "C", "WFC",
    "JNJ", "UNH", "PFE", "ABBV", "TMO", "LLY", "WMT", "MCD", "KO", "PEP",
    "NKE", "XOM", "CVX", "COP", "SLB", "EOG", "SPY", "QQQ", "IWM", "DIA",
]


class MarketScanner:
    """Scans the full S&P 500 for trading opportunities."""

    def __init__(self, universe: Optional[list] = None):
        self.universe = universe or _fetch_sp500_tickers()
        logger.info(f"Scanner initialized with {len(self.universe)} symbols")

    def _batch_download(self, period: str) -> pd.DataFrame:
        """
        Download OHLCV data for the full universe in one yfinance call.
        Returns a DataFrame with MultiIndex columns (field, symbol).
        Falls back to empty DataFrame on failure.
        """
        try:
            data = yf.download(
                self.universe,
                period=period,
                auto_adjust=True,
                progress=False,
                threads=True,
            )
            return data
        except Exception as e:
            logger.warning(f"Batch download failed: {e}")
            return pd.DataFrame()

    def find_high_gainers(self, period: str = "5d", top_n: int = 10) -> dict:
        """Find top gainers across the full universe using a single batch download."""
        data = self._batch_download(period)
        if data.empty:
            return {}

        gainers = {}
        close = data["Close"] if "Close" in data.columns else data.xs("Close", axis=1, level=0)
        volume = data["Volume"] if "Volume" in data.columns else data.xs("Volume", axis=1, level=0)

        for symbol in close.columns:
            try:
                prices = close[symbol].dropna()
                if len(prices) < 2:
                    continue
                current = prices.iloc[-1]
                previous = prices.iloc[0]
                change_pct = ((current - previous) / previous * 100) if previous != 0 else 0
                if change_pct > 0:
                    vol = int(volume[symbol].iloc[-1]) if symbol in volume.columns else 0
                    gainers[symbol] = {
                        "change_pct": round(change_pct, 2),
                        "current_price": round(current, 2),
                        "volume": vol,
                        "momentum": "strong" if change_pct > 5 else "moderate" if change_pct > 2 else "mild",
                    }
            except Exception:
                continue

        sorted_gainers = dict(sorted(gainers.items(), key=lambda x: x[1]["change_pct"], reverse=True))
        return dict(list(sorted_gainers.items())[:top_n])

    def find_volume_spikes(self, threshold_multiplier: float = 2.0, top_n: int = 10) -> dict:
        """Find stocks with unusual volume vs 20-day average using a batch download."""
        data = self._batch_download("30d")
        if data.empty:
            return {}

        volume_spikes = {}
        close = data["Close"] if "Close" in data.columns else data.xs("Close", axis=1, level=0)
        volume = data["Volume"] if "Volume" in data.columns else data.xs("Volume", axis=1, level=0)

        for symbol in volume.columns:
            try:
                vol_series = volume[symbol].dropna()
                if len(vol_series) < 10:
                    continue
                current_volume = vol_series.iloc[-1]
                avg_volume = vol_series.iloc[-20:].mean()
                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0

                if volume_ratio > threshold_multiplier:
                    prices = close[symbol].dropna()
                    current_price = prices.iloc[-1]
                    prev_close = prices.iloc[-2] if len(prices) > 1 else current_price
                    price_change = ((current_price - prev_close) / prev_close * 100) if prev_close != 0 else 0
                    volume_spikes[symbol] = {
                        "volume_ratio": round(volume_ratio, 2),
                        "current_volume": int(current_volume),
                        "avg_volume": int(avg_volume),
                        "price_change": round(price_change, 2),
                        "signal_strength": "very_strong" if volume_ratio > 4 else "strong" if volume_ratio > 2.5 else "moderate",
                    }
            except Exception:
                continue

        sorted_spikes = dict(sorted(volume_spikes.items(), key=lambda x: x[1]["volume_ratio"], reverse=True))
        return dict(list(sorted_spikes.items())[:top_n])

    def find_breakout_candidates(self, period_days: int = 252, top_n: int = 10) -> dict:
        """Find stocks breaking out of 52-week resistance using a batch download."""
        data = self._batch_download("1y")
        if data.empty:
            return {}

        breakouts = {}
        close = data["Close"] if "Close" in data.columns else data.xs("Close", axis=1, level=0)
        high = data["High"] if "High" in data.columns else data.xs("High", axis=1, level=0)
        volume = data["Volume"] if "Volume" in data.columns else data.xs("Volume", axis=1, level=0)

        for symbol in close.columns:
            try:
                prices = close[symbol].dropna()
                highs = high[symbol].dropna()
                if len(prices) < 50:
                    continue
                high_52w = highs.max()
                current_price = prices.iloc[-1]
                recent_high = highs.iloc[-3:].max()

                if current_price >= high_52w * 0.99 and current_price >= recent_high * 0.99:
                    vol = volume[symbol].dropna()
                    volume_trend = vol.iloc[-5:].mean() / vol.iloc[-20:].mean() if len(vol) >= 20 else 1.0
                    breakouts[symbol] = {
                        "current_price": round(current_price, 2),
                        "resistance_level": round(high_52w, 2),
                        "breakout_strength": "strong" if volume_trend > 1.5 else "weak",
                        "volume_confirmation": round(volume_trend, 2),
                    }
            except Exception:
                continue

        return dict(list(breakouts.items())[:top_n])

    def find_momentum_stocks(self, lookback_days: int = 5, top_n: int = 10) -> dict:
        """Find stocks with consistent upward momentum using a batch download."""
        data = self._batch_download("20d")
        if data.empty:
            return {}

        momentum_stocks = {}
        close = data["Close"] if "Close" in data.columns else data.xs("Close", axis=1, level=0)

        for symbol in close.columns:
            try:
                prices = close[symbol].dropna()
                if len(prices) < lookback_days:
                    continue
                start_price = prices.iloc[-lookback_days]
                current_price = prices.iloc[-1]
                momentum_pct = ((current_price - start_price) / start_price * 100) if start_price != 0 else 0

                closes = prices.iloc[-lookback_days:].values
                is_uptrend = all(closes[i] <= closes[i + 1] for i in range(len(closes) - 1))

                if momentum_pct > 0 and is_uptrend:
                    momentum_stocks[symbol] = {
                        "momentum_pct": round(momentum_pct, 2),
                        "current_price": round(current_price, 2),
                        "trend_consistency": "consistent",
                        "strength": "very_strong" if momentum_pct > 10 else "strong" if momentum_pct > 5 else "moderate",
                    }
            except Exception:
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
