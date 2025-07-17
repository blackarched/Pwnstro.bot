#!/bin/bash

# --- Self-Correcting Directory Logic ---
# This block ensures the script always runs from its own location,
# fixing the "ModuleNotFoundError".
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"
echo "[+] Ensuring script is running from the correct directory: $SCRIPT_DIR"

# --- Virtual Environment Activation ---
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment 'venv' not found. Please run setup.sh first."
    exit 1
fi
source venv/bin/activate
echo "[+] Virtual environment activated."

# --- Pwnagotchi Process Start ---
echo "[+] Starting Pwnagotchi process in the background..."
# Using "sudo -E" preserves the environment, allowing it to find the venv python.
# We also redirect output to a log file for cleaner execution.
sudo -E venv/bin/pwnagotchi --log-file /tmp/pwnagotchi.log &
PWN_PID=$!

# Function to clean up the background process on exit
cleanup() {
    echo ""
    echo "[+] Shutting down Pwnagotchi process (PID: $PWN_PID)..."
    # Use pkill to be more robust if the PID is lost
    sudo pkill -f "venv/bin/pwnagotchi"
    echo "[+] Exiting."
}

# Trap Ctrl+C (SIGINT) and script exit (EXIT) to run the cleanup function
trap cleanup SIGINT EXIT

# --- Dashboard Server Start ---
echo "[+] Starting C&C dashboard server on http://0.0.0.0:8080"
echo "[+] Press Ctrl+C to shut down both processes."
# Start the uvicorn server in the foreground
uvicorn main:app --host 0.0.0.0 --port 8080 --log-level warning