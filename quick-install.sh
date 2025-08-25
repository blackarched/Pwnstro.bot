#!/bin/bash
# Pwnagotchi Dashboard Quick Install Script
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🎯 Pwnagotchi Dashboard Quick Install"
echo "======================================="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.8+ first."
    exit 1
fi

echo "✅ Python found: $(python3 --version)"

# Create virtual environment
echo "📦 Creating virtual environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate venv and install dependencies
echo "📦 Installing dependencies..."
source .venv/bin/activate

# Ensure pip is up to date
pip install --upgrade pip > /dev/null 2>&1

# Install required packages
pip install Flask==2.3.3 flask-cors==4.0.0 flask-limiter==3.5.0 psutil==5.9.8 Werkzeug==2.3.7 > /dev/null 2>&1

echo "✅ Dependencies installed successfully"

# Create log directory
echo "📁 Setting up log directory..."
mkdir -p /tmp/pwnagotchi-logs
echo "✅ Log directory ready"

# Test backend
echo "🔧 Testing backend..."
timeout 5 .venv/bin/python -c "
import sys
sys.path.append('.')
from backend_api import app
print('Backend imports successful')
" || {
    echo "❌ Backend test failed"
    exit 1
}

echo "✅ Backend test passed"

# Check if port 8080 is free
if lsof -i :8080 > /dev/null 2>&1; then
    echo "⚠️  Port 8080 is already in use. Trying to stop existing process..."
    pkill -f 'backend_api.py' || true
    sleep 2
fi

echo ""
echo "🚀 Installation complete!"
echo ""
echo "To start the dashboard:"
echo "  1. Run: ./start-dashboard.sh"
echo "  2. Open: http://localhost:8080"
echo ""
echo "To start manually:"
echo "  source .venv/bin/activate"
echo "  python3 backend_api.py"
echo ""
