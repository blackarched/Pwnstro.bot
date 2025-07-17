#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo " Pwnstro.bot C&C Dashboard Setup "
echo "======================================"

# 1. Install System Dependencies
echo "[+] Installing system dependencies (python3-venv, python3-dev)..."
sudo apt-get update
sudo apt-get install -y python3-venv python3-dev git

# 2. Create Python Virtual Environment
echo "[+] Creating Python virtual environment in './venv'..."
python3 -m venv venv

# 3. Activate Virtual Environment and Install Python Packages
echo "[+] Activating venv and installing all required Python packages..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate

# 4. Create the Run Script
echo "[+] Creating the 'run.sh' script..."
cat << 'EOF' > run.sh
#!/bin/bash

# Activate the virtual environment
source venv/bin/activate

# Find the pwnagotchi executable inside the venv
PWNAGOTCHI_EXEC=$(find "$(pwd)/venv" -name pwnagotchi)

if [ -z "$PWNAGOTCHI_EXEC" ]; then
    echo "Error: Could not find the pwnagotchi executable in the venv."
    exit 1
fi

echo "Starting Pwnagotchi process in the background..."
# Start pwnagotchi as a background process
sudo "$PWNAGOTCHI_EXEC" &
# Get the Process ID (PID) of the background pwnagotchi
PWN_PID=$!

# Function to clean up the background process on exit
cleanup() {
    echo "Shutting down Pwnagotchi process (PID: $PWN_PID)..."
    sudo kill $PWN_PID
    echo "Exiting."
}

# Trap Ctrl+C (SIGINT) and script exit (EXIT) to run the cleanup function
trap cleanup SIGINT EXIT

echo "Starting C&C dashboard server..."
# Start the uvicorn server in the foreground
uvicorn main:app --host 0.0.0.0 --port 8080

EOF

# 5. Make the Run Script Executable
chmod +x run.sh

echo ""
echo "======================================"
echo "✅ Setup complete!"
echo "To start the application, run: ./run.sh"
echo "======================================"
