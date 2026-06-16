"""
Quantitative analysis engine for advanced trading insights.
Correlation detection, cointegration testing, regime identification.
"""

import logging
import numpy as np
import pandas as pd
from typing import Optional
from scipy import stats
from scipy.stats import pearsonr
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CorrelationAnalyzer:
    """Detects correlations between trading positions."""

    @staticmethod
    def calculate_correlation_matrix(price_series: dict[str, list[float]]) -> pd.DataFrame:
        """Calculate correlation matrix for multiple symbols."""
        df = pd.DataFrame(price_series)
        return df.corr()

    @staticmethod
    def find_highly_correlated_pairs(
        price_series: dict[str, list[float]], threshold: float = 0.7
    ) -> list[tuple]:
        """Find pairs of symbols with high correlation."""
        corr_matrix = CorrelationAnalyzer.calculate_correlation_matrix(price_series)

        pairs = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                symbol1 = corr_matrix.columns[i]
                symbol2 = corr_matrix.columns[j]
                corr_value = corr_matrix.iloc[i, j]

                if abs(corr_value) > threshold:
                    pairs.append({
                        "symbol1": symbol1,
                        "symbol2": symbol2,
                        "correlation": round(corr_value, 3),
                        "type": "positive" if corr_value > 0 else "negative",
                        "strength": "very_high" if abs(corr_value) > 0.85 else "high",
                    })

        return sorted(pairs, key=lambda x: abs(x["correlation"]), reverse=True)

    @staticmethod
    def get_portfolio_correlation_risk(positions: dict[str, float]) -> dict:
        """Assess portfolio diversification risk based on correlation."""
        if len(positions) < 2:
            return {"risk": "low", "reason": "insufficient positions"}

        # Simple correlation averaging (production would use actual data)
        avg_correlation = 0.5  # Placeholder
        concentration = max(positions.values()) / sum(positions.values())

        risk_score = (avg_correlation * 0.6) + (concentration * 0.4)

        return {
            "correlation_average": avg_correlation,
            "concentration_ratio": round(concentration, 3),
            "risk_score": round(risk_score, 3),
            "risk_level": "high" if risk_score > 0.7 else "medium" if risk_score > 0.4 else "low",
            "recommendation": "reduce position overlap" if risk_score > 0.7 else "monitor",
        }


class CointegrationAnalyzer:
    """Detects cointegrated (mean-reverting) pairs for pair trading."""

    @staticmethod
    def engle_granger_test(price_series1: list[float], price_series2: list[float]) -> dict:
        """Engle-Granger cointegration test (simplified)."""
        if len(price_series1) < 20 or len(price_series2) < 20:
            return {"cointegrated": False, "pvalue": 1.0}

        # Calculate log prices
        log_p1 = np.log(price_series1)
        log_p2 = np.log(price_series2)

        # Simple regression to find hedge ratio
        slope, intercept, r_value, p_value, std_err = stats.linregress(log_p1, log_p2)

        # Check spread stationarity (simplified)
        spread = log_p2 - (slope * log_p1 + intercept)
        spread_mean = np.mean(spread)
        spread_std = np.std(spread)

        # Z-score of current spread
        current_zscore = (spread[-1] - spread_mean) / spread_std if spread_std > 0 else 0

        return {
            "cointegrated": p_value < 0.05,
            "p_value": round(p_value, 4),
            "r_squared": round(r_value ** 2, 4),
            "hedge_ratio": round(slope, 4),
            "current_zscore": round(current_zscore, 2),
            "mean_revert_opportunity": abs(current_zscore) > 2,  # > 2 SD = trading signal
            "mean_revert_strength": "strong" if abs(current_zscore) > 2.5 else "weak",
        }

    @staticmethod
    def find_cointegrated_pairs(
        price_data: dict[str, list[float]], symbols: list[str] = None
    ) -> list[dict]:
        """Find cointegrated pairs in portfolio."""
        symbols = symbols or list(price_data.keys())
        cointegrated_pairs = []

        for i, sym1 in enumerate(symbols):
            for sym2 in symbols[i + 1 :]:
                if sym1 in price_data and sym2 in price_data:
                    result = CointegrationAnalyzer.engle_granger_test(
                        price_data[sym1], price_data[sym2]
                    )

                    if result["cointegrated"]:
                        cointegrated_pairs.append({
                            "symbol1": sym1,
                            "symbol2": sym2,
                            "p_value": result["p_value"],
                            "hedge_ratio": result["hedge_ratio"],
                            "current_spread_zscore": result["current_zscore"],
                            "trading_signal": "BUY_SPREAD" if result["current_zscore"] < -2 else "SELL_SPREAD" if result["current_zscore"] > 2 else "HOLD",
                        })

        return sorted(cointegrated_pairs, key=lambda x: x["p_value"])


class RegimeDetector:
    """Identifies market regimes (bull, bear, sideways, volatile)."""

    REGIMES = {
        "bull": "Uptrend - prices rising, momentum positive",
        "bear": "Downtrend - prices falling, momentum negative",
        "sideways": "Range-bound - no clear direction",
        "volatile": "High volatility - elevated risk",
    }

    @staticmethod
    def detect_regime(close_prices: list[float], lookback: int = 60) -> dict:
        """Detect current market regime."""
        if len(close_prices) < lookback:
            return {"regime": "unknown", "confidence": 0.0}

        recent = close_prices[-lookback:]

        # Trend detection
        returns = np.diff(recent) / recent[:-1]
        avg_return = np.mean(returns)
        volatility = np.std(returns) * np.sqrt(252)  # Annualized

        # SMA analysis
        sma_short = np.mean(recent[-20:])
        sma_long = np.mean(recent)
        trend_strength = (sma_short - sma_long) / sma_long

        # Regime classification
        if volatility > 0.3:
            regime = "volatile"
            confidence = min(volatility / 0.5, 1.0)
        elif trend_strength > 0.02:
            regime = "bull"
            confidence = min(trend_strength / 0.05, 1.0)
        elif trend_strength < -0.02:
            regime = "bear"
            confidence = min(abs(trend_strength) / 0.05, 1.0)
        else:
            regime = "sideways"
            confidence = 0.6

        return {
            "regime": regime,
            "description": RegimeDetector.REGIMES.get(regime, ""),
            "confidence": round(confidence, 3),
            "trend_strength": round(trend_strength, 4),
            "volatility_annual": round(volatility, 4),
            "avg_daily_return": round(avg_return, 4),
        }

    @staticmethod
    def detect_regime_change(close_prices: list[float]) -> dict:
        """Detect if regime is changing."""
        if len(close_prices) < 120:
            return {"regime_change": False, "strength": 0.0}

        # Split into two periods
        mid_point = len(close_prices) // 2
        period1 = close_prices[: mid_point + 1]
        period2 = close_prices[mid_point:]

        regime1 = RegimeDetector.detect_regime(period1)
        regime2 = RegimeDetector.detect_regime(period2)

        # Check if regime changed significantly
        regime_changed = regime1["regime"] != regime2["regime"]
        strength = abs(regime2["trend_strength"] - regime1["trend_strength"])

        return {
            "regime_change": regime_changed,
            "previous_regime": regime1["regime"],
            "current_regime": regime2["regime"],
            "change_strength": round(strength, 4),
            "alert": regime_changed and strength > 0.03,
        }


class PortfolioMetrics:
    """Calculates portfolio-level risk metrics."""

    @staticmethod
    def calculate_sharpe_ratio(
        returns: list[float], risk_free_rate: float = 0.04
    ) -> float:
        """Calculate Sharpe ratio (annualized)."""
        if len(returns) == 0:
            return 0.0

        excess_returns = np.array(returns) - (risk_free_rate / 252)
        return (np.mean(excess_returns) / np.std(excess_returns)) * np.sqrt(252)

    @staticmethod
    def calculate_max_drawdown(prices: list[float]) -> float:
        """Calculate maximum drawdown."""
        if len(prices) == 0:
            return 0.0

        cummax = np.maximum.accumulate(prices)
        drawdown = (prices - cummax) / cummax
        return float(np.min(drawdown))

    @staticmethod
    def calculate_sortino_ratio(
        returns: list[float], risk_free_rate: float = 0.04
    ) -> float:
        """Calculate Sortino ratio (only penalizes downside volatility)."""
        if len(returns) == 0:
            return 0.0

        excess_returns = np.array(returns) - (risk_free_rate / 252)
        downside_returns = excess_returns[excess_returns < 0]
        downside_std = np.std(downside_returns) if len(downside_returns) > 0 else 0.0

        if downside_std == 0:
            return 0.0

        return (np.mean(excess_returns) / downside_std) * np.sqrt(252)

    @staticmethod
    def calculate_value_at_risk(returns: list[float], confidence: float = 0.95) -> float:
        """Calculate Value at Risk (VaR) at given confidence level."""
        if len(returns) == 0:
            return 0.0

        return float(np.percentile(returns, (1 - confidence) * 100))

    @staticmethod
    def calculate_expected_shortfall(returns: list[float], confidence: float = 0.95) -> float:
        """Calculate Expected Shortfall (CVaR) - average loss beyond VaR."""
        if len(returns) == 0:
            return 0.0

        var = PortfolioMetrics.calculate_value_at_risk(returns, confidence)
        losses = [r for r in returns if r <= var]

        return float(np.mean(losses)) if losses else var

    @staticmethod
    def get_portfolio_summary(
        portfolio_values: list[float], trade_returns: list[float]
    ) -> dict:
        """Generate comprehensive portfolio metrics."""
        if len(portfolio_values) < 2:
            return {"status": "insufficient_data"}

        total_return_pct = ((portfolio_values[-1] - portfolio_values[0]) / portfolio_values[0]) * 100
        max_dd = PortfolioMetrics.calculate_max_drawdown(portfolio_values)

        return {
            "total_return_pct": round(total_return_pct, 2),
            "max_drawdown_pct": round(max_dd * 100, 2),
            "sharpe_ratio": round(PortfolioMetrics.calculate_sharpe_ratio(trade_returns), 2),
            "sortino_ratio": round(PortfolioMetrics.calculate_sortino_ratio(trade_returns), 2),
            "var_95": round(PortfolioMetrics.calculate_value_at_risk(trade_returns) * 100, 2),
            "expected_shortfall": round(PortfolioMetrics.calculate_expected_shortfall(trade_returns) * 100, 2),
            "avg_return": round(np.mean(trade_returns) * 100, 2),
            "volatility": round(np.std(trade_returns) * np.sqrt(252) * 100, 2),
        }


class QuantAnalysisEngine:
    """Main engine combining all quant analysis tools."""

    def __init__(self):
        self.correlation = CorrelationAnalyzer()
        self.cointegration = CointegrationAnalyzer()
        self.regime = RegimeDetector()
        self.metrics = PortfolioMetrics()

    def analyze_symbol(
        self, symbol: str, price_data: dict[str, list[float]], current_price: float
    ) -> dict:
        """Comprehensive quant analysis for a symbol."""
        analysis = {
            "symbol": symbol,
            "timestamp": datetime.utcnow().isoformat(),
            "regime": None,
            "correlations": [],
            "cointegrations": [],
            "metrics": {},
        }

        # Regime analysis
        if symbol in price_data:
            prices = price_data[symbol]
            regime = self.regime.detect_regime(prices)
            regime_change = self.regime.detect_regime_change(prices)

            analysis["regime"] = regime
            if regime_change["regime_change"]:
                analysis["regime_alert"] = regime_change

        # Correlation analysis
        correlations = self.correlation.find_highly_correlated_pairs(price_data, threshold=0.6)
        analysis["correlations"] = [c for c in correlations if symbol in [c["symbol1"], c["symbol2"]]]

        # Cointegration analysis
        cointegrations = self.cointegration.find_cointegrated_pairs(
            price_data, [symbol] + [s for s in price_data.keys() if s != symbol][:10]
        )
        analysis["cointegrations"] = [c for c in cointegrations if symbol in [c["symbol1"], c["symbol2"]]]

        return analysis

    def get_analysis_report(self, analysis: dict) -> str:
        """Generate text report of quant analysis."""
        report = f"\n{'='*60}\n"
        report += f"QUANTITATIVE ANALYSIS - {analysis['symbol']}\n"
        report += f"{'='*60}\n\n"

        if analysis.get("regime"):
            regime = analysis["regime"]
            report += f"MARKET REGIME:\n"
            report += f"  State: {regime['regime'].upper()}\n"
            report += f"  Confidence: {regime['confidence']:.0%}\n"
            report += f"  Volatility (annualized): {regime['volatility_annual']:.1%}\n"
            report += f"  Trend Strength: {regime['trend_strength']:.4f}\n\n"

        if analysis.get("regime_alert"):
            alert = analysis["regime_alert"]
            report += f"⚠️  REGIME CHANGE DETECTED:\n"
            report += f"  {alert['previous_regime'].upper()} → {alert['current_regime'].upper()}\n"
            report += f"  Strength: {alert['change_strength']:.4f}\n\n"

        if analysis.get("correlations"):
            report += f"CORRELATIONS:\n"
            for corr in analysis["correlations"][:3]:
                report += f"  {corr['symbol1']}-{corr['symbol2']}: {corr['correlation']:+.3f} ({corr['strength']})\n"
            report += "\n"

        if analysis.get("cointegrations"):
            report += f"COINTEGRATION (Mean-Revert Pairs):\n"
            for coin in analysis["cointegrations"][:3]:
                report += f"  {coin['symbol1']}-{coin['symbol2']}: {coin['trading_signal']}\n"
                report += f"    Spread Z-Score: {coin['current_spread_zscore']:.2f}\n"
            report += "\n"

        report += f"{'='*60}\n"
        return report
