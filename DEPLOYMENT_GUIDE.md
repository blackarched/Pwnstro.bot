# 🚀 Pwnagotchi Dashboard - Live Deployment Guide

## Quick Start Options

### Option 1: Simple Development Server (Fastest)
```bash
# 1. Navigate to the dashboard directory
cd /home/aztr0n0t/Documents/pwngotchi_v3/New_pwnagotchi

# 2. Install Python dependencies
pip3 install -r requirements.txt

# 3. Run the backend server
python3 backend_api.py

# 4. Open browser and go to:
# http://localhost:8080
```

### Option 2: Production Installation (Recommended)
```bash
# 1. Navigate to dashboard directory
cd /home/aztr0n0t/Documents/pwngotchi_v3/New_pwnagotchi

# 2. Run automated installer
sudo ./install.sh --prod

# 3. Access via:
# http://YOUR_IP_ADDRESS (if nginx installed)
# or http://localhost:8080
```

### Option 3: Docker Deployment (Easiest)
```bash
# 1. Navigate to dashboard directory
cd /home/aztr0n0t/Documents/pwngotchi_v3/New_pwnagotchi

# 2. Deploy with Docker
./docker-deploy.sh --env=prod

# 3. Access via:
# http://localhost:8080
```

---

## 🔧 Detailed Setup Instructions

### Prerequisites Check
```bash
# Check Python version (need 3.8+)
python3 --version

# Check if pip is installed
pip3 --version

# For Docker option, check Docker
docker --version
docker-compose --version
```

### Method 1: Development Server (Quick Test)

**Step 1: Install Dependencies**
```bash
cd /home/aztr0n0t/Documents/pwngotchi_v3/New_pwnagotchi

# Install required Python packages
pip3 install flask flask-cors flask-limiter psutil

# Or install all from requirements
pip3 install -r requirements.txt
```

**Step 2: Run Backend**
```bash
# Start the API server
python3 backend_api.py
```

**Expected Output:**
```
2024-01-XX XX:XX:XX,XXX - root - INFO - Pwnagotchi API starting up
2024-01-XX XX:XX:XX,XXX - root - INFO - System initialized with PID XXXX
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:8080
 * Running on http://YOUR_IP:8080
```

**Step 3: Access Dashboard**
- Open browser: `http://localhost:8080`
- Or from another device: `http://YOUR_IP:8080`

---

### Method 2: Production Installation

**Step 1: Prepare System**
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install required system packages
sudo apt install -y python3 python3-pip python3-venv wireless-tools net-tools nginx
```

**Step 2: Run Installer**
```bash
cd /home/aztr0n0t/Documents/pwngotchi_v3/New_pwnagotchi

# Make installer executable
chmod +x install.sh

# Run production installation
sudo ./install.sh --prod
```

**Step 3: Verify Installation**
```bash
# Check service status
sudo systemctl status pwnagotchi-dashboard

# Check nginx status (if installed)
sudo systemctl status nginx

# View logs
sudo journalctl -u pwnagotchi-dashboard -f
```

**Step 4: Access Dashboard**
- Via Nginx: `http://YOUR_IP`
- Direct: `http://YOUR_IP:8080`

---

### Method 3: Docker Deployment

**Step 1: Install Docker**
```bash
# Install Docker (Ubuntu/Debian)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install -y docker-compose

# Add user to docker group
sudo usermod -aG docker $USER
# Logout and login again
```

**Step 2: Deploy**
```bash
cd /home/aztr0n0t/Documents/pwngotchi_v3/New_pwnagotchi

# Make deploy script executable
chmod +x docker-deploy.sh

# Deploy basic version
./docker-deploy.sh --env=prod

# Or deploy with nginx and monitoring
./docker-deploy.sh --env=prod --with-nginx --with-monitoring
```

**Step 3: Access**
- Basic: `http://localhost:8080`
- With Nginx: `http://localhost`
- Monitoring: `http://localhost:3000` (Grafana)

---

## 🎛️ Dashboard Features Once Running

### Live System Monitoring
- **CPU Usage**: Real-time processor utilization
- **Memory Usage**: RAM consumption tracking
- **Temperature**: System temperature monitoring
- **Network Interfaces**: WiFi/Ethernet status

### Network Operations
- **WiFi Scanning**: Click "SCAN NETWORKS" to discover nearby APs
- **Interface Monitoring**: Real-time status of network adapters
- **Handshake Tracking**: Monitor captured WPA handshakes

### System Control
- **Mode Toggle**: Switch between AUTO/MANUAL modes
- **System Reboot**: Restart the system (requires sudo permissions)
- **System Shutdown**: Power off the system

### Configuration
- **Unit Name**: Customize device identifier
- **Scan Interval**: Adjust scanning frequency (1-60 seconds)
- **Settings Persistence**: Configuration saved automatically

### Data Export
- **Export Data**: Download system metrics as JSON
- **Export Logs**: Save system logs as text file
- **Real-time Logs**: View live system activity

---

## 🔧 Troubleshooting

### Common Issues

**1. Permission Denied Errors**
```bash
# Fix file permissions
sudo chown -R $USER:$USER /home/aztr0n0t/Documents/pwngotchi_v3/New_pwnagotchi

# For system commands, add sudo permissions
echo "$USER ALL=(ALL) NOPASSWD: /sbin/reboot, /sbin/shutdown, /sbin/iwlist" | sudo tee /etc/sudoers.d/pwnagotchi
```

**2. Port Already in Use**
```bash
# Check what's using port 8080
sudo lsof -i :8080

# Kill process if needed
sudo kill -9 PID_NUMBER

# Or change port in backend_api.py
```

**3. Network Scanning Not Working**
```bash
# Install wireless tools
sudo apt install -y wireless-tools

# Check wireless interfaces
iwconfig

# Test manual scan
sudo iwlist scan
```

**4. Dashboard Not Loading**
```bash
# Check if backend is running
curl http://localhost:8080/api/status

# Check logs
tail -f /var/log/pwnagotchi/api.log

# Restart service (if installed)
sudo systemctl restart pwnagotchi-dashboard
```

---

## 📱 Accessing from Remote Devices

### Same Network Access
1. Find your system's IP address:
```bash
ip addr show | grep inet
```

2. Access from any device on the network:
- `http://YOUR_IP:8080` (direct)
- `http://YOUR_IP` (if nginx installed)

### External Access (Advanced)
1. **Port Forwarding**: Configure router to forward port 80/8080
2. **VPN**: Use OpenVPN or WireGuard for secure access
3. **Cloudflare Tunnel**: Use cloudflared for secure external access

---

## 🔒 Security Considerations

### Development Mode
- Only accessible from localhost by default
- No authentication required
- Suitable for testing and development

### Production Mode
- Includes rate limiting
- Input validation and sanitization
- Secure headers (CSP, XSS protection)
- Nginx reverse proxy with security features

### Network Security
```bash
# Enable firewall
sudo ufw enable
sudo ufw allow 22      # SSH
sudo ufw allow 80      # HTTP
sudo ufw allow 8080    # Dashboard (if needed)
```

---

## 📊 Monitoring and Maintenance

### Check System Health
```bash
# Manual health check
python3 health_monitor.py --check

# View system metrics
curl http://localhost:8080/api/status | jq

# Monitor logs
tail -f /var/log/pwnagotchi/api.log
```

### Service Management
```bash
# Start service
sudo systemctl start pwnagotchi-dashboard

# Stop service
sudo systemctl stop pwnagotchi-dashboard

# Restart service
sudo systemctl restart pwnagotchi-dashboard

# View status
sudo systemctl status pwnagotchi-dashboard
```

### Docker Management
```bash
# View running containers
docker-compose ps

# View logs
docker-compose logs -f

# Restart services
docker-compose restart

# Stop all services
docker-compose down
```

---

## 🎯 Next Steps After Running

1. **Customize Configuration**: Update unit name and scan intervals
2. **Set Up Monitoring**: Enable health monitoring with alerts
3. **Configure WiFi**: Ensure wireless interface is properly configured
4. **Test Network Scanning**: Verify WiFi scanning functionality
5. **Set Up Backup**: Configure data export and backup procedures

## 📞 Support

If you encounter issues:
1. Check the logs: `/var/log/pwnagotchi/api.log`
2. Verify all dependencies are installed
3. Ensure proper permissions are set
4. Test with curl: `curl http://localhost:8080/api/status`

The dashboard should provide real-time system monitoring and network scanning capabilities once properly deployed!
