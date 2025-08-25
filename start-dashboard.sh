#!/bin/bash
# Pwnagotchi Dashboard Startup Script
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🎯 Starting Pwnagotchi Dashboard..."

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Run ./quick-install.sh first."
    exit 1
fi

# Check if dependencies are installed
if ! .venv/bin/pip show Flask > /dev/null 2>&1; then
    echo "❌ Dependencies not installed. Run ./quick-install.sh first."
    exit 1
fi

# Stop any existing backend
echo "🛑 Stopping any existing backend..."
pkill -f 'backend_api.py' > /dev/null 2>&1 || true
sleep 1

# Check if port is free
if lsof -i :8080 > /dev/null 2>&1; then
    echo "❌ Port 8080 is still in use. Please free the port and try again."
    lsof -i :8080
    exit 1
fi

# Start backend
echo "🚀 Starting backend..."
source .venv/bin/activate

# Run in background and capture PID
nohup python3 backend_api.py > /tmp/pwnagotchi-dashboard.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > /tmp/pwnagotchi-dashboard.pid

# Wait for backend to start
echo "⏳ Waiting for backend to initialize..."
sleep 3

# Test if backend is responding
if curl -sf http://localhost:8080/api/status > /dev/null; then
    echo "✅ Backend started successfully (PID: $BACKEND_PID)"
    echo ""
    echo "🎉 Dashboard is now running!"
    echo ""
    echo "📱 Access the dashboard:"
    echo "   🌐 Local:    http://localhost:8080"
    echo "   🌐 Network:  http://$(hostname -I | awk '{print $1}'):8080"
    echo ""
    echo "📋 Management commands:"
    echo "   Stop:    ./stop-dashboard.sh"
    echo "   Logs:    tail -f /tmp/pwnagotchi-dashboard.log"
    echo "   Status:  curl http://localhost:8080/api/status"
    echo ""
    echo "🔍 Process info:"
    echo "   PID file: /tmp/pwnagotchi-dashboard.pid"
    echo "   Log file: /tmp/pwnagotchi-dashboard.log"
    echo ""
else
    echo "❌ Backend failed to start properly"
    echo "📋 Check logs: tail -f /tmp/pwnagotchi-dashboard.log"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi
