# Pwnagotchi Enhanced Dashboard

Production-ready web dashboard for Pwnagotchi Linux systems with real backend integration.

## 🚀 Features

- **Real-time System Monitoring**: Live CPU, memory, and temperature stats
- **Network Interface Management**: Monitor WiFi and Ethernet interfaces
- **System Control**: Reboot, shutdown, and mode switching capabilities
- **Configuration Management**: Persistent settings with validation
- **Security Hardened**: Rate limiting, input validation, and XSS protection
- **Responsive Design**: Works on desktop and mobile devices
- **Export Functionality**: Download logs and system data

## 📋 Requirements

- Python 3.8+
- Linux system with network interfaces
- Root privileges for system commands
- Modern web browser

## 🛠️ Installation

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Create log directory:**
   ```bash
   sudo mkdir -p /var/log/pwnagotchi
   sudo chmod 755 /var/log/pwnagotchi
   ```

3. **Set up permissions for system commands:**
   ```bash
   # Add to sudoers for reboot/shutdown (optional)
   echo "$(whoami) ALL=(ALL) NOPASSWD: /sbin/reboot, /sbin/shutdown" | sudo tee -a /etc/sudoers
   ```

## 🚀 Usage

1. **Start the backend server:**
   ```bash
   python3 backend_api.py
   ```

2. **Access the dashboard:**
   Open http://localhost:8080 in your web browser

3. **Environment variables (optional):**
   ```bash
   export PORT=8080              # Server port
   export SECRET_KEY=your_key    # Flask secret key
   export DEBUG=false            # Debug mode
   ```

## 🔧 Configuration

The dashboard supports real-time configuration updates:

- **Unit Name**: Custom identifier for your device
- **Scan Interval**: Network scanning frequency (1-60 seconds)
- **Auto-reconnect**: Automatic connection recovery

## 🔒 Security Features

- **Rate Limiting**: Prevents API abuse
- **Input Validation**: Sanitizes all user inputs
- **CORS Protection**: Restricts cross-origin requests
- **Security Headers**: XSS and clickjacking protection
- **Error Handling**: Comprehensive logging and error recovery

## 🐛 Troubleshooting

**Connection Issues:**
- Ensure backend server is running on correct port
- Check firewall settings for port 8080
- Verify network connectivity

**Permission Errors:**
- Run with appropriate privileges for system monitoring
- Check log directory permissions: `/var/log/pwnagotchi/`

**Network Scanning:**
- Requires root privileges for iwlist command
- Install wireless-tools: `sudo apt-get install wireless-tools`

## 📁 File Structure

```
New_pwnagotchi/
├── pwnagotchi_dashboard.html    # Frontend dashboard
├── pwnagotchi_enhanced.js       # JavaScript functionality
├── backend_api.py               # Python backend server
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## 🔄 API Endpoints

- `GET /api/status` - System status and statistics
- `POST /api/command` - Execute system commands
- `GET /api/export/data` - Export system data

## 🎯 Production Deployment

For production deployment:

1. **Use a proper WSGI server:**
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:8080 backend_api:app
   ```

2. **Set up reverse proxy (nginx):**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://127.0.0.1:8080;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

3. **Configure systemd service:**
   ```ini
   [Unit]
   Description=Pwnagotchi Dashboard
   After=network.target
   
   [Service]
   Type=simple
   User=pwnagotchi
   WorkingDirectory=/opt/pwnagotchi
   ExecStart=/usr/bin/python3 backend_api.py
   Restart=always
   
   [Install]
   WantedBy=multi-user.target
   ```

## 📈 Monitoring

The dashboard provides comprehensive monitoring:

- **System Resources**: CPU, RAM, temperature
- **Network Activity**: Interface status, scanning results
- **Application Logs**: Real-time log streaming
- **Performance Metrics**: Response times and error rates

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Implement changes with tests
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This software is for educational and authorized testing purposes only. Users are responsible for complying with applicable laws and regulations.
