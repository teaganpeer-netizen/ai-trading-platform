#!/bin/bash
# Run trading + auto-export trades to CSV every 5 minutes

cd /Users/teaganpeer/dev/ai-trading-platform

# Start trading
nohup python run_trading.py > logs/trading.log 2>&1 &
TRADE_PID=$!
echo $TRADE_PID > trading.pid

echo "✅ Trading started (PID: $TRADE_PID)"
echo "✅ Exporting trades to CSV every 5 minutes..."
echo ""
echo "Open trades CSV in Excel or Google Sheets for live updates"
echo ""

# Auto-export every 5 minutes
while true; do
    python export_trades.py > /dev/null 2>&1
    sleep 300
done
