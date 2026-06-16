#!/bin/bash
# Start the web dashboard

echo "Starting AI Trading Dashboard..."
echo "Dashboard will be available at http://localhost:5000"
echo ""

cd "$(dirname "$0")/.."
python dashboard/app.py
