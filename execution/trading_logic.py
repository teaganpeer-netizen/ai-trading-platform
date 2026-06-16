"""
Advanced trading logic with improved entry/exit strategies.
"""

import pandas as pd
import logging

logger = logging.getLogger(__name__)


class EnhancedTradingLogic:
    """Advanced trading signals and exit strategies."""

    @staticmethod
    def should_enter_position(df: pd.DataFrame, confidence: float = 0.7) -> bool:
        """Determine if conditions are right to enter."""
        if df.empty or len(df) < 50:
            return False

        latest = df.iloc[-1]

        # Entry conditions (AI confidence is primary factor)
        if confidence < 0.6:
            return False  # Low confidence, skip entry

        # Additional checks
        rsi = latest.get("rsi_14")
        if rsi and rsi > 85:
            logger.info("Entry blocked: RSI too high (overbought)")
            return False  # Too overbought

        return True

    @staticmethod
    def calculate_dynamic_stops(df: pd.DataFrame, entry_price: float) -> tuple[float, float]:
        """Calculate entry-specific stop loss and take profit."""
        if df.empty:
            return entry_price * 0.98, entry_price * 1.05

        latest = df.iloc[-1]
        atr = latest.get("atr_14", (entry_price * 0.02))

        # Use recent volatility to set stops
        if atr <= 0:
            atr = entry_price * 0.02

        # Stop loss: 2x ATR below entry
        stop_loss = entry_price - (atr * 2)

        # Take profit: 3x ATR above entry
        take_profit = entry_price + (atr * 3)

        return round(stop_loss, 2), round(take_profit, 2)

    @staticmethod
    def should_exit_on_signal(df: pd.DataFrame, entry_price: float) -> tuple[bool, str]:
        """Check if technical signal indicates exit."""
        if df.empty or len(df) < 2:
            return False, ""

        latest = df.iloc[-1]
        previous = df.iloc[-2]

        # Exit signal 1: MACD bearish crossover
        if "macd" in latest and "macd_signal" in latest:
            if previous["macd"] > previous["macd_signal"] and latest["macd"] < latest["macd_signal"]:
                return True, "MACD bearish crossover"

        # Exit signal 2: RSI overbought reversal (above 80 then drops)
        if "rsi_14" in latest:
            if previous.get("rsi_14", 50) > 75 and latest["rsi_14"] < 70:
                return True, "RSI overbought reversal"

        # Exit signal 3: Break below SMA50
        if "sma_50" in latest and latest["sma_50"] > 0:
            if latest["close"] < latest["sma_50"] < latest["open"]:
                return True, "Price broke below SMA50"

        return False, ""

    @staticmethod
    def should_exit_on_trailing_stop(current_price: float, entry_price: float, peak_price: float, atr: float = None) -> bool:
        """Trailing stop logic - exit if pullback exceeds threshold."""
        if atr is None:
            atr = entry_price * 0.02

        # Trail stop at 1.5x ATR below peak
        trailing_stop = peak_price - (atr * 1.5)

        if current_price < trailing_stop:
            logger.info(f"Trailing stop triggered: peak=${peak_price:.2f}, current=${current_price:.2f}, stop=${trailing_stop:.2f}")
            return True

        return False

    @staticmethod
    def calculate_position_confidence(df: pd.DataFrame) -> float:
        """Calculate confidence score based on confluence of signals."""
        if df.empty or len(df) < 50:
            return 0.0

        latest = df.iloc[-1]
        confidence_score = 0.0

        # SMA alignment (0-20 points)
        if "sma_20" in latest and "sma_50" in latest:
            if latest["close"] > latest["sma_20"] > latest["sma_50"]:
                confidence_score += 20

        # MACD bullish (0-20 points)
        if "macd" in latest and "macd_signal" in latest:
            if latest["macd"] > latest["macd_signal"] and latest["macd"] > 0:
                confidence_score += 20

        # RSI in good zone (0-15 points)
        if "rsi_14" in latest:
            rsi = latest["rsi_14"]
            if 45 < rsi < 75:
                confidence_score += 15

        # Volume confirmation (0-15 points)
        if "volume" in latest and len(df) > 20:
            avg_volume = df["volume"].tail(20).mean()
            if latest["volume"] > avg_volume * 1.1:
                confidence_score += 15

        # Price above all MAs (0-10 points)
        if all(key in latest for key in ["close", "sma_20", "sma_50"]):
            if latest["close"] > latest["sma_20"] > latest["sma_50"]:
                confidence_score += 10

        # Normalize to 0-1
        return min(confidence_score / 100, 1.0)

    @staticmethod
    def check_portfolio_health(open_positions: dict, current_prices: dict, daily_pnl: float, max_daily_loss: float) -> tuple[bool, str]:
        """Check overall portfolio health for additional risk management."""
        if not open_positions:
            return True, "No positions"

        # Check individual position losses
        max_position_loss = 0
        losing_position = None

        for symbol, (qty, entry_price) in open_positions.items():
            current_price = current_prices.get(symbol, entry_price)
            position_loss = (entry_price - current_price) * qty
            if position_loss > max_position_loss:
                max_position_loss = position_loss
                losing_position = symbol

        # If worst position is down 5%+, consider cutting it
        if losing_position and max_position_loss > 0:
            loss_pct = max_position_loss / (open_positions[losing_position][0] * open_positions[losing_position][1])
            if loss_pct > 0.05:
                return False, f"Position {losing_position} down {loss_pct:.1%}, consider exit"

        # Check daily loss vs limit
        if daily_pnl < 0 and abs(daily_pnl) > max_daily_loss * 0.8:
            return False, f"Daily loss approaching limit (${abs(daily_pnl):.0f})"

        return True, "Healthy"

    @staticmethod
    def rate_entry_quality(entry_price: float, sma_20: float, sma_50: float, rsi: float) -> dict:
        """Rate the quality of a potential entry."""
        quality_score = 0
        notes = []

        # Price location relative to MAs
        if sma_20 > 0 and sma_50 > 0:
            if entry_price > sma_20:
                quality_score += 2
                notes.append("Above SMA20")
            if entry_price > sma_50:
                quality_score += 2
                notes.append("Above SMA50")

        # RSI level
        if 40 < rsi < 70:
            quality_score += 2
            notes.append(f"RSI {rsi:.0f} (good zone)")
        elif rsi > 75:
            quality_score -= 1
            notes.append(f"RSI {rsi:.0f} (overbought)")

        # How far from SMA20
        if sma_20 > 0:
            distance_pct = (entry_price - sma_20) / sma_20
            if 0 < distance_pct < 0.05:
                quality_score += 2
                notes.append("Close to SMA20 (pullback)")
            elif distance_pct > 0.10:
                quality_score -= 1
                notes.append("Far from SMA20 (chasing)")

        return {
            "quality_score": quality_score,  # 0-10 scale
            "rating": "Excellent" if quality_score >= 7 else "Good" if quality_score >= 4 else "Fair" if quality_score >= 1 else "Poor",
            "notes": notes,
        }
