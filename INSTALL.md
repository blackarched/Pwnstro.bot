# Pwnagotchi Dashboard Installation Guide

## Quick Start (Local Development)

### 1. Install Dependencies
```bash
cd /home/aztr0n0t/Desktop/pwngotchi_v3/New_pwnagotchi

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install required packages
pip install --upgrade pip
pip install Flask==2.3.3 flask-cors==4.0.0 flask-limiter==3.5.0 psutil==5.9.8 Werkzeug==2.3.7
```

### 2. Run the Backend
```bash
# Start the backend API
python3 backend_api.py
```

### 3. Access the Dashboard
Open your browser and go to:
- **http://localhost:8080**

That's it! The dashboard should now be working.

---

## Production Installation (Recommended)

### Option 1: Systemd Service

1. **Install system-wide**:
```bash
cd /home/aztr0n0t/Desktop/pwngotchi_v3/New_pwnagotchi

# Create installation directory
sudo mkdir -p /opt/pwnagotchi-dashboard
sudo cp -r . /opt/pwnagotchi-dashboard/

# Create virtual environment
cd /opt/pwnagotchi-dashboard
sudo python3 -m venv venv
sudo ./venv/bin/pip install Flask==2.3.3 flask-cors==4.0.0 flask-limiter==3.5.0 psutil==5.9.8 Werkzeug==2.3.7

# Create log directory
sudo mkdir -p /var/log/pwnagotchi
sudo chown $USER:$USER /var/log/pwnagotchi
```

2. **Create systemd service**:
```bash
sudo tee /etc/systemd/system/pwnagotchi-dashboard.service > /dev/null << 'EOF'
[Unit]
Description=Pwnagotchi Dashboard API
After=network.target

[Service]
Type=simple
User=pwnagotchi
Group=pwnagotchi
WorkingDirectory=/opt/pwnagotchi-dashboard
ExecStart=/opt/pwnagotchi-dashboard/venv/bin/python backend_api.py
Restart=always
RestartSec=10
Environment=PORT=8080
Environment=FLASK_ENV=production

# Security settings
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/pwnagotchi

[Install]
WantedBy=multi-user.target
EOF
```

3. **Start the service**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable pwnagotchi-dashboard
sudo systemctl start pwnagotchi-dashboard
sudo systemctl status pwnagotchi-dashboard
```

### Option 2: Docker (Easiest)

1. **Build and run**:
```bash
cd /home/aztr0n0t/Desktop/pwngotchi_v3/New_pwnagotchi

# Build the container
docker build -t pwnagotchi-dashboard .

# Run the container
docker run -d \
  --name pwnagotchi-dashboard \
  -p 8080:8080 \
  --restart unless-stopped \
  pwnagotchi-dashboard
```

2. **Or use docker-compose**:
```bash
docker-compose up -d
```

### Option 3: With Nginx Reverse Proxy

1. **Install Nginx**:
```bash
sudo apt update
sudo apt install nginx
```

2. **Configure Nginx**:
```bash
sudo cp nginx-pwnagotchi.conf /etc/nginx/sites-available/pwnagotchi-dashboard
sudo ln -s /etc/nginx/sites-available/pwnagotchi-dashboard /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

3. **Access via Nginx**:
- **http://your-server-ip** (port 80)
- **http://your-server-ip:8080** (direct backend)

---

## Troubleshooting

### Backend Not Starting
```bash
# Check if dependencies are installed
.venv/bin/pip list | grep -E 'Flask|psutil'

# Check logs
tail -f /var/log/pwnagotchi/api.log

# Test manually
curl http://localhost:8080/api/status
```

### Port Already in Use
```bash
# Find what's using port 8080
sudo lsof -i :8080

# Kill the process if needed
sudo kill -9 <PID>
```

### Permission Issues
```bash
# Fix log directory permissions
sudo mkdir -p /var/log/pwnagotchi
sudo chown $USER:$USER /var/log/pwnagotchi
```

### Dashboard Won't Connect
1. Verify backend is running: `curl http://localhost:8080/api/status`
2. Check browser console for errors (F12)
3. Try disabling browser security extensions
4. Clear browser cache and cookies

---

## Daily Usage

### Start Dashboard (Development)
```bash
cd /home/aztr0n0t/Desktop/pwngotchi_v3/New_pwnagotchi
source .venv/bin/activate
python3 backend_api.py
# Open http://localhost:8080 in browser
```

### Start Dashboard (Production)
```bash
sudo systemctl start pwnagotchi-dashboard
# Dashboard available at http://your-ip:8080
```

### Stop Dashboard
```bash
# Development: Ctrl+C in terminal
# Production: sudo systemctl stop pwnagotchi-dashboard
# Docker: docker stop pwnagotchi-dashboard
```

---

## Security Notes

- Dashboard runs without authentication by default
- For production, consider adding authentication
- Use HTTPS in production environments
- Firewall port 8080 if not using Nginx proxy
- Regular security updates recommended

---

## Features Available

✅ Real-time system monitoring  
✅ Network interface status  
✅ WiFi scanning controls  
✅ System configuration  
✅ Live activity logs  
✅ Data export functionality  
✅ Responsive cyberpunk UI  

The dashboard provides full control over your Pwnagotchi system with a modern, secure web interface.
