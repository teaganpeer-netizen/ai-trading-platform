#!/bin/bash
#
# AI Trading Platform - Management Script
# Controls autonomous trading and dashboard
#

cd /Users/teaganpeer/dev/ai-trading-platform

case "$1" in

  start)
    echo "🚀 Starting AI Trading Platform..."

    # Start dashboard
    nohup python dashboard/app.py > logs/dashboard.log 2>&1 &
    DASH_PID=$!
    echo $DASH_PID > dashboard.pid
    echo "  ✓ Dashboard started (PID: $DASH_PID)"

    # Start autonomous trading
    nohup python run_autonomous.py > logs/autonomous_trading_output.log 2>&1 &
    TRADE_PID=$!
    echo $TRADE_PID > autonomous_trading.pid
    echo "  ✓ Autonomous trading started (PID: $TRADE_PID)"

    echo ""
    echo "📊 Dashboard: http://localhost:5000"
    echo "📋 Logs: tail -f logs/autonomous_trading.log"
    echo ""
    ;;

  stop)
    echo "🛑 Stopping AI Trading Platform..."

    if [ -f dashboard.pid ]; then
      kill $(cat dashboard.pid) 2>/dev/null
      echo "  ✓ Dashboard stopped"
      rm dashboard.pid
    fi

    if [ -f autonomous_trading.pid ]; then
      kill $(cat autonomous_trading.pid) 2>/dev/null
      echo "  ✓ Autonomous trading stopped"
      rm autonomous_trading.pid
    fi

    echo "✅ All services stopped"
    echo ""
    ;;

  status)
    echo "📊 AI Trading Platform Status"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    if pgrep -f "dashboard/app.py" > /dev/null; then
      echo "✓ Dashboard: RUNNING (http://localhost:5000)"
    else
      echo "✗ Dashboard: STOPPED"
    fi

    if pgrep -f "run_autonomous.py" > /dev/null; then
      echo "✓ Autonomous Trading: RUNNING"
    else
      echo "✗ Autonomous Trading: STOPPED"
    fi

    echo ""
    echo "Recent Activity:"
    tail -5 logs/autonomous_trading.log 2>/dev/null || echo "  No activity yet"
    echo ""
    ;;

  logs)
    echo "📋 Autonomous Trading Logs"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    tail -50 logs/autonomous_trading.log
    echo ""
    ;;

  restart)
    echo "🔄 Restarting AI Trading Platform..."
    $0 stop
    sleep 2
    $0 start
    ;;

  *)
    echo "AI Trading Platform - Management Script"
    echo ""
    echo "Usage: $0 {start|stop|status|logs|restart}"
    echo ""
    echo "Commands:"
    echo "  start      - Start dashboard & autonomous trading"
    echo "  stop       - Stop all services"
    echo "  status     - Show current status"
    echo "  logs       - View trading logs"
    echo "  restart    - Restart all services"
    echo ""
    echo "Examples:"
    echo "  ./manage_trading.sh start      # Start everything"
    echo "  ./manage_trading.sh status     # Check status"
    echo "  ./manage_trading.sh logs       # View logs"
    echo ""
    ;;
esac
