# 🚀 AI Trading Platform - Startup Guide

**You have a production-ready AI trading platform. Here's how to use it.**

---

## Quick Start (60 seconds)

```bash
# 1. Launch the interactive CLI
python cli.py

# 2. Select an option:
#    1 = Run Paper Trading (AI-powered simulation)
#    2 = Backtest strategies
#    3 = Analyze a symbol
#    4 = View risk settings
#    5 = Launch web dashboard
#    6 = Exit
```

That's it. Everything else is automatic.

---

## What You Have

### 🎯 Core Components
- **Data Layer** — Auto-collects market data (YFinance)
- **AI Engine** — Groq LLM analyzes markets + makes decisions
- **Risk Manager** — Protects capital with position sizing
- **Trading Logic** — Smart entry/exit signals
- **Execution** — Paper trading (ready for Alpaca live)
- **Dashboard** — Web UI for monitoring

### 🔄 Integration Flow
```
Market Data
    ↓
Technical Indicators (SMA, RSI, MACD, ATR, etc.)
    ↓
MCP Market Context (sector performance, volatility, trends)
    ↓
AI Decision Maker (Groq LLM)
    ↓
Enhanced Trading Logic (entry/exit quality checks)
    ↓
Risk Manager (position sizing, circuit breaker)
    ↓
Execution (Paper or Live)
    ↓
Dashboard Monitoring
```

---

## 📋 Running Each Feature

### Option 1: Paper Trading

Interactive simulation with real AI decisions:

```bash
python cli.py
→ Select "1" (Run Paper Trading)
→ Enter iterations (e.g., 10)
→ AI makes buy/sell decisions
→ See positions, P&L, circuit breaker status
```

**What happens:**
- AI analyzes each symbol in watchlist
- Makes BUY/SELL/HOLD decisions with confidence scores
- Risk manager sizes positions (2% risk rule)
- Trades execute if conditions met
- Position P&L tracked in real-time
- Circuit breaker halts trading if losses exceed limits

### Option 2: Backtesting

Test strategies on historical data:

```bash
python cli.py
→ Select "2" (Run Backtester)
→ Choose strategy (SMA / RSI / MACD)
→ Enter symbols (e.g., SPY,AAPL)
→ Watch results
```

**Built-in strategies:**
- **SMA Crossover** — Buy when 20MA crosses above 50MA
- **RSI** — Buy at oversold (<30), sell at overbought (>70)
- **MACD** — Buy when MACD crosses above signal line

### Option 3: Analyze Symbol

Get AI decision + market context for one symbol:

```bash
python cli.py
→ Select "3" (Analyze Single Symbol)
→ Enter symbol (e.g., AAPL)
→ Get:
   - AI decision (BUY/SELL/HOLD + confidence)
   - Technical levels (entry, stop, target)
   - Market context (sector trends, volatility)
   - Entry quality rating
```

### Option 4: View Risk Manager

Check position sizing logic:

```bash
python cli.py
→ Select "4" (View Risk Manager)
→ See:
   - Risk per trade: 2% of portfolio
   - Daily loss limit: 3% of portfolio
   - Max exposure: 80% deployed
   - Example position sizing calculation
```

### Option 5: Web Dashboard

Real-time monitoring interface:

```bash
# Terminal 1: Run paper trading
python cli.py → Select "1"

# Terminal 2: Start dashboard
bash scripts/run_dashboard.sh

# Browser: Open http://localhost:5000
```

**Dashboard shows:**
- Portfolio value + daily P&L
- Open positions with live P&L
- Recent trade history
- Performance metrics (win rate, profit factor)
- Circuit breaker status
- Auto-refreshes every 5 seconds

---

## 🔧 Configuration

Edit `.env` to customize:

```ini
# Risk settings
MAX_RISK_PER_TRADE_PCT=0.02          # 2% per trade
DAILY_LOSS_LIMIT_PCT=0.03            # 3% daily limit
MAX_PORTFOLIO_EXPOSURE_PCT=0.80       # Max 80% deployed

# Watchlist
WATCHLIST=["AAPL","MSFT","SPY",...]  # Symbols to trade

# For live trading (Alpaca)
ALPACA_API_KEY=your_key              # Get from app.alpaca.markets
ALPACA_SECRET_KEY=your_secret         # Keep these safe
```

---

## 🎯 AI Decision Making

The AI (Groq LLM) considers:

1. **Technical Analysis**
   - Moving average alignment (SMA20, SMA50)
   - Momentum (RSI, MACD)
   - Volatility (Bollinger Bands, ATR)
   - Price action patterns

2. **Market Context (MCP)**
   - Market status (S&P 500, NASDAQ, VIX)
   - Sector performance (Tech, Finance, Energy, etc.)
   - Stock volatility percentile
   - Trend strength vs moving averages

3. **Risk Assessment**
   - Entry quality (confluence of signals)
   - Position size (2% Kelly Criterion)
   - Stop loss / take profit placement
   - Portfolio exposure limits

4. **Output**
   - Decision: BUY / SELL / HOLD
   - Confidence: 0-100%
   - Entry price
   - Stop loss price
   - Take profit target
   - Full reasoning

---

## 📊 Performance Metrics

The system tracks:

- **Total Return** — Starting vs. ending capital
- **Win Rate** — % of profitable trades
- **Profit Factor** — Gross wins / Gross losses (>1.0 is good)
- **Max Drawdown** — Largest peak-to-trough loss
- **Avg Win / Loss** — Average winning vs. losing trade size
- **Circuit Breaker** — Open/Caution/Halt status

---

## 🛡️ Risk Management

Protects capital automatically:

1. **Position Sizing** — 2% risk per trade
   - Entry price = $100, Stop = $95
   - Position size = 400 shares (risks exactly $2,000)

2. **Trading Limits**
   - Max 5 open positions at once
   - Max 80% of portfolio deployed
   - Max 3% daily loss allowed

3. **Circuit Breaker**
   - Halts trading if 15% drawdown
   - Halts trading if 5% daily loss
   - Halts trading after 5 consecutive losses
   - Auto-recovery after 1 hour grace period

4. **Exit Strategies**
   - Profit targets (3x ATR above entry)
   - Stop losses (2x ATR below entry)
   - MACD bearish crossover signals exit
   - RSI overbought reversal exits
   - Trailing stops for winners

---

## 🔴 Important Notes

⚠️ **Paper Trading Only**
- Currently runs on historical data simulation
- Not connected to live markets
- Use for testing strategies before going live

⚠️ **For Live Trading**
- Update `.env` to use live Alpaca credentials
- Test thoroughly with small positions first
- Monitor dashboard during market hours
- Circuit breaker will protect you

⚠️ **API Keys**
- Keep `.env` file secure (it's in .gitignore)
- Never commit credentials to git
- Use environment variables in production

---

## 📈 Example Session

```bash
$ python cli.py

╭─────────────────────────────────────────────╮
│ 🤖 AI TRADING PLATFORM                      │
│ Production-Grade Algorithmic Trading System │
╰─────────────────────────────────────────────╯

MAIN MENU
1. ▶ Run Paper Trading
2. 📊 Run Backtester
3. 📈 Analyze Single Symbol
4. 🔧 View Risk Manager
5. 📊 Dashboard
6. ❌ Exit

Select option (1-6): 3
SYMBOL ANALYSIS
Enter symbol (e.g., AAPL): SPY

Analyzing SPY...

═══════════════════════════════════
SPY ANALYSIS
═══════════════════════════════════

Price: $754.83
Action: BUY
Confidence: 80%
Entry Quality: Excellent

Reasoning:
The current price is above SMA20 and SMA50, indicating strong uptrend.
RSI at 52.6 is in a good zone. MACD shows positive momentum.

Levels:
  Entry: $754.83
  Stop: $745.00
  Target: $765.21

Technical Indicators:
  SMA20: $745.86
  SMA50: $724.78
  RSI14: 52.6
  MACD: 4.5393

📊 MARKET CONTEXT:
Market Status:
  S&P 500: +0.15%
  NASDAQ: +0.32%
  VIX: -2.1% (lower volatility = good)

Volatility: 15.4% (moderate)
Sector Strength: Tech +8.7%, Finance +3.4%, Energy -5.1%
```

---

## 🐛 Troubleshooting

**Problem:** CLI won't start
```bash
→ pip install -r requirements.txt
→ python cli.py
```

**Problem:** No data for symbol
```bash
→ Symbol needs to be backfilled first
→ Run: python scripts/backfill_data.py SYMBOL
```

**Problem:** AI not making decisions
```bash
→ Check GROQ_API_KEY in .env
→ Check internet connection
→ Verify Groq API is accessible
```

**Problem:** Dashboard not loading
```bash
→ bash scripts/run_dashboard.sh
→ Open http://localhost:5000 in browser
→ Check port 5000 isn't in use
```

---

## 📚 Commands Cheatsheet

```bash
# Run the CLI (main entry point)
python cli.py

# Or run specific features directly:
python scripts/run_paper_trading.py
python scripts/run_backtest.py --strategy sma --symbols SPY AAPL
python scripts/test_ai_decisions.py
python scripts/test_full_system.py
bash scripts/run_dashboard.sh

# Backfill data
python scripts/backfill_data.py AAPL MSFT GOOGL

# Test everything
python scripts/test_full_system.py
```

---

## 🎓 Architecture

```
config/           Configuration & environment
data/             Market data collection & storage
backtesting/      Strategy simulation framework
risk/             Position sizing & circuit breaker
ai_engine/        Groq LLM & market context (MCP)
execution/        Paper & live trading execution
dashboard/        Web monitoring interface
scripts/          CLI tools & runners
cli.py            Interactive menu system (you are here)
```

---

## ✅ You're Ready

Everything is tested, configured, and working. 

**Start with:** `python cli.py`

**Then:** Try each option to get familiar with the system.

**Finally:** Run paper trading to see AI in action.

Happy trading! 🚀
