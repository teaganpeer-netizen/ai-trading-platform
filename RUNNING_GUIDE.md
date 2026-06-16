# 🚀 Running Your AI Trading Platform

## Current Status (June 16, 2026)

✅ **Dashboard**: Running on http://localhost:5000  
✅ **Autonomous Trading**: Running (1 trade/minute)  
✅ **Phase 2 Features**: Tax tracking, Quant analysis, ML predictions active

---

## 📊 Quick Access

### Start Everything
```bash
cd /Users/teaganpeer/dev/ai-trading-platform
./manage_trading.sh start
```

### Check Status
```bash
./manage_trading.sh status
```

### View Live Logs
```bash
./manage_trading.sh logs
# or
tail -f logs/autonomous_trading.log
```

### Stop Everything
```bash
./manage_trading.sh stop
```

---

## 🌐 Dashboard Access

**Local Machine:**
```
http://localhost:5000
```

**What You See:**
- Portfolio value in real-time
- Open positions with P&L
- Trade history
- Circuit breaker status
- Daily profit/loss

**Auto-refresh:** Every 5 seconds

---

## 🔄 Running After Today

### Option 1: Terminal Session (Manual)
```bash
cd /Users/teaganpeer/dev/ai-trading-platform

# Terminal 1: Start dashboard
python dashboard/app.py

# Terminal 2: Start autonomous trading
python run_autonomous.py

# Browser: Open http://localhost:5000
```

### Option 2: Background Process (Recommended)
```bash
./manage_trading.sh start

# Runs in background - keeps going even if you close terminal
```

### Option 3: LaunchAgent (Runs on Startup)

Create `~/Library/LaunchAgents/com.teaganpeer.trading.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.teaganpeer.trading</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/teaganpeer/dev/ai-trading-platform/manage_trading.sh</string>
        <string>start</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/teaganpeer/dev/ai-trading-platform/logs/launchagent.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/teaganpeer/dev/ai-trading-platform/logs/launchagent_error.log</string>
</dict>
</plist>
```

Then:
```bash
launchctl load ~/Library/LaunchAgents/com.teaganpeer.trading.plist
# Runs automatically on startup!
```

---

## 📈 Trading Metrics (Updated Every Minute)

**In Dashboard:**
- Portfolio value
- Daily P&L
- Open positions count
- Circuit breaker state
- Recent trades

**In Logs (autonomous_trading.log):**
```
[   1] P&L: $     +0 | Positions: 1 | Circuit: open | Portfolio: $100,000
[   2] P&L: $     +0 | Positions: 1 | Circuit: open | Portfolio: $100,000
[   3] P&L: $   -150 | Positions: 2 | Circuit: open | Portfolio: $99,850
```

---

## 🎛️ Manual Controls

### CLI Menu (Anytime)
```bash
python cli.py
```

Then access:
- Option 1: Paper Trading (manual mode)
- Option 3: Analyze Single Symbol
- Option 7: Tax Tracker
- Option 8: Quant Analysis
- Option 4: Market Scanner

### Recording a Tax Trade
```
python cli.py
→ Option 7 (Tax Tracker)
→ Option 1 (Record a Trade)
→ Enter: symbol, dates, prices, quantity
→ Gets classified as ST/LT automatically
→ Tax liability calculated
```

### Viewing Market Regime
```
python cli.py
→ Option 8 (Quant Analysis)
→ Option 3 (Regime Detection)
→ Enter: SPY (or any symbol)
→ See: Bull/Bear/Sideways state, confidence, volatility
```

---

## 🛑 Troubleshooting

**Dashboard won't open?**
```bash
# Check if it's running
./manage_trading.sh status

# Check for errors
tail logs/dashboard.log

# Restart it
./manage_trading.sh restart
```

**Autonomous trading stopped?**
```bash
# Check logs
./manage_trading.sh logs

# Restart
./manage_trading.sh restart
```

**Port 5000 already in use?**
```bash
# Find what's using it
lsof -i :5000

# Kill it
kill -9 <PID>

# Restart dashboard
./manage_trading.sh start
```

---

## 📊 What's Happening Right Now

### Autonomous Trading
- Makes 1 decision per minute (60+ per hour)
- Analyzes all symbols in watchlist
- Uses AI (Groq LLM) to decide BUY/SELL/HOLD
- Applies risk management (2% position sizing, circuit breaker)
- Logs every trade with P&L

### Tax Tracking
- Every closed trade automatically records:
  - Entry/exit dates
  - Cost basis and proceeds
  - Gain/loss
  - ST or LT classification
  - Tax liability estimate

### Quant Analysis (When You Ask)
- Market regime detection (Bull/Bear/Sideways)
- Correlation analysis (detect over-concentrated positions)
- Cointegration detection (find mean-reverting pairs)
- Portfolio risk metrics (Sharpe, Sortino, VaR)

### ML Predictions (When You Ask)
- Random Forest trains on historical data
- Predicts next-day price movements
- Shows confidence and key features

---

## 💼 Next Steps

### This Week
- [ ] Monitor dashboard daily
- [ ] Check logs for unusual activity
- [ ] Verify tax tracking accuracy
- [ ] Test CLI options (3, 7, 8)

### This Month
- [ ] Accumulate 30+ days trading data
- [ ] Review P&L trends
- [ ] Backtest against historical data
- [ ] Fine-tune risk parameters

### 3-6 Months
- [ ] Run continuous paper trading
- [ ] Achieve 15%+ returns
- [ ] Train ML models thoroughly
- [ ] Zero circuit breaker trips
- [ ] Prepare for live trading

### 6+ Months (When Ready for Live)
- Add Alpaca credentials to `.env`
- Change `ALPACA_PAPER_MODE=true` → `false`
- Start with $5k-$10k
- Monitor closely first week
- Scale gradually

---

## 📁 File Locations

```
~/dev/ai-trading-platform/
├── manage_trading.sh          ← Use this to control everything
├── run_autonomous.py          ← Autonomous trading runner
├── cli.py                     ← Interactive menu
├── dashboard/
│   └── app.py                 ← Web dashboard (port 5000)
├── logs/
│   ├── autonomous_trading.log ← Trading activity
│   ├── dashboard.log          ← Dashboard errors
│   └── ...
├── ai_engine/
│   ├── tax_tracker.py         ← Tax tracking module
│   ├── quant_analyzer.py      ← Quant analysis module
│   ├── ml_engine.py           ← ML predictions module
│   └── ...
└── RUNNING_GUIDE.md           ← This file
```

---

## 🚀 One-Line Commands

```bash
# Start everything
cd ~/dev/ai-trading-platform && ./manage_trading.sh start

# Open dashboard
open http://localhost:5000

# View live logs
tail -f ~/dev/ai-trading-platform/logs/autonomous_trading.log

# Check status
~/dev/ai-trading-platform/manage_trading.sh status

# Stop everything
~/dev/ai-trading-platform/manage_trading.sh stop

# Restart everything
~/dev/ai-trading-platform/manage_trading.sh restart
```

---

## 📞 Support Commands

```bash
# Run interactive CLI
python cli.py

# Check current status
./manage_trading.sh status

# View last 50 trades
./manage_trading.sh logs

# Restart services
./manage_trading.sh restart

# Check Python dependencies
pip list | grep -E "pandas|numpy|groq|alpaca"
```

---

## ✅ Success Metrics

**Daily:**
- Dashboard accessible at http://localhost:5000
- Autonomous trading making decisions
- Logs show trades every 1-5 minutes
- No circuit breaker trips

**Weekly:**
- Portfolio trending (up or stable)
- Tax tracker recording all trades
- No unusual errors in logs
- Dashboard responsive

**Monthly:**
- P&L accumulating
- Tax liability being tracked
- Model retraining improving predictions
- Risk metrics staying healthy

---

**Last Updated:** June 16, 2026  
**Version:** Phase 2 (Tax + Quant + ML)  
**Status:** ✅ Running Autonomously  
**Dashboard:** http://localhost:5000
