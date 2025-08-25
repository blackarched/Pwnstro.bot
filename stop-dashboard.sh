#!/bin/bash
# Pwnagotchi Dashboard Stop Script
set -e

echo "🛑 Stopping Pwnagotchi Dashboard..."

# Stop backend using PID file
if [ -f "/tmp/pwnagotchi-dashboard.pid" ]; then
    PID=$(cat /tmp/pwnagotchi-dashboard.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "🔪 Stopping backend process (PID: $PID)..."
        kill $PID
        sleep 2
        
        # Force kill if still running
        if ps -p $PID > /dev/null 2>&1; then
            echo "🔨 Force killing backend process..."
            kill -9 $PID
        fi
        
        echo "✅ Backend stopped successfully"
    else
        echo "⚠️  Backend process not running (PID: $PID)"
    fi
    
    rm -f /tmp/pwnagotchi-dashboard.pid
else
    echo "⚠️  PID file not found, trying to kill by name..."
    pkill -f 'backend_api.py' || echo "No backend_api.py processes found"
fi

# Verify port is free
if lsof -i :8080 > /dev/null 2>&1; then
    echo "⚠️  Port 8080 is still in use:"
    lsof -i :8080
else
    echo "✅ Port 8080 is now free"
fi

echo "🎯 Dashboard stopped successfully"
