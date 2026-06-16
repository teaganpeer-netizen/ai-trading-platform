"""
AI-powered trading decision engine using Groq.
"""

from datetime import datetime
from dataclasses import dataclass
import logging
import pandas as pd
from groq import Groq

logger = logging.getLogger(__name__)


@dataclass
class Decision:
    """AI trading decision."""
    symbol: str
    action: str  # "buy", "sell", "hold"
    confidence: float  # 0.0 to 1.0
    reasoning: str
    entry_price: float = None
    stop_loss: float = None
    take_profit: float = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class AIDecisionMaker:
    """Uses Groq to analyze market data and make trading decisions."""

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        self.client = Groq(api_key=api_key)
        self.model = model
        self.conversation_history = []

    def analyze_symbol(
        self,
        symbol: str,
        df: pd.DataFrame,
        current_price: float,
        portfolio_context: dict = None,
    ) -> Decision:
        """
        Analyze a symbol using AI and make a trading decision.

        Args:
            symbol: Stock symbol
            df: Historical price DataFrame with indicators
            current_price: Current price
            portfolio_context: Portfolio info (cash, positions, etc.)

        Returns:
            Decision object with buy/sell/hold recommendation
        """
        # Prepare market data summary
        market_summary = self._prepare_market_summary(symbol, df, current_price)

        # Build prompt
        prompt = self._build_prompt(symbol, market_summary, portfolio_context)

        # Get AI analysis
        response = self._call_groq(prompt)

        # Parse decision
        decision = self._parse_decision(symbol, response, current_price)

        return decision

    def _prepare_market_summary(self, symbol: str, df: pd.DataFrame, current_price: float) -> str:
        """Prepare market data summary for AI analysis."""
        if df.empty or len(df) < 2:
            return f"Insufficient data for {symbol}"

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        summary = f"""
Symbol: {symbol}
Current Price: ${current_price:.2f}

Recent Price Action:
- 52-week High: ${df['high'].max():.2f}
- 52-week Low: ${df['low'].min():.2f}
- Current: ${current_price:.2f}
- Price Change: {((current_price - df['close'].iloc[0]) / df['close'].iloc[0] * 100):.2f}%
- Volume: {latest['volume']:,.0f} shares

Technical Indicators (Latest):
- SMA20: ${latest.get('sma_20', 0):.2f}
- SMA50: ${latest.get('sma_50', 0):.2f}
- EMA12: ${latest.get('ema_12', 0):.2f}
- RSI14: {latest.get('rsi_14', 50):.1f}
- MACD: {latest.get('macd', 0):.4f}
- BBands Upper: ${latest.get('bb_upper', 0):.2f}
- BBands Lower: ${latest.get('bb_lower', 0):.2f}
- ATR14: ${latest.get('atr_14', 0):.2f}

Price Momentum:
- Daily Return: {latest.get('returns', 0) * 100:.2f}%
- 5-day trend: {'↑ UP' if latest['close'] > df.iloc[-6]['close'] else '↓ DOWN'}
- Price vs SMA20: {'Above' if current_price > latest.get('sma_20', current_price) else 'Below'} MA20
- Price vs SMA50: {'Above' if current_price > latest.get('sma_50', current_price) else 'Below'} MA50
"""
        return summary.strip()

    def _build_prompt(self, symbol: str, market_data: str, portfolio_context: dict = None) -> str:
        """Build AI prompt for decision making."""
        portfolio_info = ""
        if portfolio_context:
            portfolio_info = f"""
Portfolio Context:
- Available Cash: ${portfolio_context.get('cash', 0):,.0f}
- Current Positions: {portfolio_context.get('open_positions', 0)}
- Portfolio Value: ${portfolio_context.get('portfolio_value', 0):,.0f}
- Current Exposure: {portfolio_context.get('exposure_pct', 0):.1f}%
- Daily P&L: ${portfolio_context.get('daily_pnl', 0):,.0f}
"""

        prompt = f"""You are an expert quantitative trader with 20+ years of experience in algorithmic trading.

{market_data}

{portfolio_info}

Based on the above market data and technical indicators, provide a trading decision for {symbol}.

Your response MUST be in exactly this format (no other text):
ACTION: [BUY|SELL|HOLD]
CONFIDENCE: [0.0-1.0]
REASONING: [2-3 sentence explanation of your decision]
ENTRY_PRICE: [price or N/A]
STOP_LOSS: [price or N/A]
TAKE_PROFIT: [price or N/A]

Consider:
1. Current price relative to moving averages
2. RSI for overbought/oversold conditions
3. MACD for momentum changes
4. Bollinger Bands for volatility
5. Overall trend direction
6. Risk-reward ratio

Be precise. Confidence should reflect your conviction (0.1 = low, 0.9 = high)."""

        return prompt

    def _call_groq(self, prompt: str) -> str:
        """Call Groq API for analysis."""
        try:
            message = self.client.chat.completions.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,  # Lower temp for more consistent trading decisions
            )
            response = message.choices[0].message.content
            return response
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            raise

    def _parse_decision(self, symbol: str, response: str, current_price: float) -> Decision:
        """Parse AI response into Decision object."""
        lines = response.strip().split('\n')
        decision_dict = {}

        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()
                decision_dict[key] = value

        action = decision_dict.get('action', 'HOLD').upper()
        if action not in ['BUY', 'SELL', 'HOLD']:
            action = 'HOLD'

        try:
            confidence = float(decision_dict.get('confidence', '0.5'))
            confidence = max(0.0, min(1.0, confidence))
        except ValueError:
            confidence = 0.5

        reasoning = decision_dict.get('reasoning', 'Analysis inconclusive')

        # Parse prices
        entry = self._parse_price(decision_dict.get('entry_price', 'N/A'))
        stop = self._parse_price(decision_dict.get('stop_loss', 'N/A'))
        target = self._parse_price(decision_dict.get('take_profit', 'N/A'))

        return Decision(
            symbol=symbol,
            action=action,
            confidence=confidence,
            reasoning=reasoning,
            entry_price=entry,
            stop_loss=stop,
            take_profit=target,
        )

    def _parse_price(self, price_str: str) -> float | None:
        """Parse price from string."""
        try:
            if 'n/a' in price_str.lower():
                return None
            return float(price_str.replace('$', '').strip())
        except (ValueError, AttributeError):
            return None

    def get_conversation_history(self) -> list:
        """Get conversation history."""
        return self.conversation_history
