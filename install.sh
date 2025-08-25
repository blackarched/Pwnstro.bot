#!/bin/bash
#
# Pwnagotchi Dashboard Installation Script
# Production-ready deployment automation
#
# Usage: sudo ./install.sh [--dev|--prod]
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/opt/pwnagotchi-dashboard"
SERVICE_USER="pwnagotchi"
SERVICE_NAME="pwnagotchi-dashboard"
LOG_DIR="/var/log/pwnagotchi"
CONFIG_DIR="/etc/pwnagotchi"
NGINX_AVAILABLE="/etc/nginx/sites-available"
NGINX_ENABLED="/etc/nginx/sites-enabled"

# Default mode
MODE="prod"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dev)
            MODE="dev"
            shift
            ;;
        --prod)
            MODE="prod"
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--dev|--prod]"
            echo "  --dev   Development installation"
            echo "  --prod  Production installation (default)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

# Detect OS and package manager
detect_os() {
    if [[ -f /etc/debian_version ]]; then
        OS="debian"
        PKG_MANAGER="apt"
    elif [[ -f /etc/redhat-release ]]; then
        OS="redhat"
        PKG_MANAGER="yum"
    elif [[ -f /etc/arch-release ]]; then
        OS="arch"
        PKG_MANAGER="pacman"
    else
        log_error "Unsupported operating system"
        exit 1
    fi
    log_info "Detected OS: $OS"
}

# Install system dependencies
install_dependencies() {
    log_info "Installing system dependencies..."
    
    case $PKG_MANAGER in
        apt)
            apt update
            apt install -y python3 python3-pip python3-venv python3-dev \
                          nginx supervisor wireless-tools net-tools \
                          build-essential curl wget git
            ;;
        yum)
            yum update -y
            yum install -y python3 python3-pip python3-devel \
                          nginx supervisor wireless-tools net-tools \
                          gcc gcc-c++ make curl wget git
            ;;
        pacman)
            pacman -Sy --noconfirm python python-pip python-virtualenv \
                                   nginx supervisor wireless_tools net-tools \
                                   base-devel curl wget git
            ;;
    esac
    
    log_success "System dependencies installed"
}

# Create system user
create_user() {
    if ! id "$SERVICE_USER" &>/dev/null; then
        log_info "Creating service user: $SERVICE_USER"
        useradd -r -s /bin/false -d "$INSTALL_DIR" "$SERVICE_USER"
        log_success "User $SERVICE_USER created"
    else
        log_info "User $SERVICE_USER already exists"
    fi
}

# Create directories
create_directories() {
    log_info "Creating directories..."
    
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "$CONFIG_DIR"
    
    # Set permissions
    chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
    chown -R "$SERVICE_USER:$SERVICE_USER" "$LOG_DIR"
    chmod 755 "$LOG_DIR"
    
    log_success "Directories created and configured"
}

# Install Python application
install_application() {
    log_info "Installing Pwnagotchi Dashboard..."
    
    # Copy application files
    cp -r ./* "$INSTALL_DIR/"
    
    # Create virtual environment
    cd "$INSTALL_DIR"
    python3 -m venv venv
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip setuptools wheel
    
    # Install dependencies
    if [[ "$MODE" == "dev" ]]; then
        pip install -r requirements.txt pytest pytest-flask pytest-cov black flake8 mypy
    else
        pip install -r requirements.txt gunicorn
    fi
    
    # Set permissions
    chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
    chmod +x "$INSTALL_DIR/backend_api.py"
    
    log_success "Application installed"
}

# Configure systemd service
configure_systemd() {
    log_info "Configuring systemd service..."
    
    cat > "/etc/systemd/system/${SERVICE_NAME}.service" << EOF
[Unit]
Description=Pwnagotchi Dashboard
After=network.target
Wants=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/venv/bin
ExecStart=$INSTALL_DIR/venv/bin/python backend_api.py
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=10
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$LOG_DIR $CONFIG_DIR
NoNewPrivileges=true

# Security settings
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_BIND_SERVICE
SecureBits=keep-caps

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=pwnagotchi-dashboard

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"
    
    log_success "Systemd service configured"
}

# Configure nginx
configure_nginx() {
    if [[ "$MODE" == "prod" ]]; then
        log_info "Configuring nginx reverse proxy..."
        
        cat > "$NGINX_AVAILABLE/pwnagotchi-dashboard" << EOF
server {
    listen 80;
    server_name _;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
    
    # Rate limiting
    limit_req_zone \$binary_remote_addr zone=api:10m rate=10r/m;
    
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # Static file caching
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        proxy_pass http://127.0.0.1:8080;
    }
    
    # Logging
    access_log /var/log/nginx/pwnagotchi-access.log;
    error_log /var/log/nginx/pwnagotchi-error.log;
}
EOF
        
        # Enable site
        ln -sf "$NGINX_AVAILABLE/pwnagotchi-dashboard" "$NGINX_ENABLED/"
        
        # Test nginx configuration
        if nginx -t; then
            systemctl enable nginx
            systemctl restart nginx
            log_success "Nginx configured and restarted"
        else
            log_error "Nginx configuration test failed"
            exit 1
        fi
    else
        log_info "Skipping nginx configuration in development mode"
    fi
}

# Configure firewall
configure_firewall() {
    log_info "Configuring firewall..."
    
    # Check if ufw is available
    if command -v ufw &> /dev/null; then
        ufw allow 22/tcp    # SSH
        ufw allow 80/tcp    # HTTP
        ufw allow 443/tcp   # HTTPS
        
        if [[ "$MODE" == "dev" ]]; then
            ufw allow 8080/tcp  # Development server
        fi
        
        # Enable firewall if not already enabled
        echo "y" | ufw enable 2>/dev/null || true
        log_success "UFW firewall configured"
    elif command -v firewall-cmd &> /dev/null; then
        # firewalld (CentOS/RHEL)
        firewall-cmd --permanent --add-service=ssh
        firewall-cmd --permanent --add-service=http
        firewall-cmd --permanent --add-service=https
        
        if [[ "$MODE" == "dev" ]]; then
            firewall-cmd --permanent --add-port=8080/tcp
        fi
        
        firewall-cmd --reload
        log_success "Firewalld configured"
    else
        log_warn "No supported firewall found, skipping firewall configuration"
    fi
}

# Configure sudo permissions
configure_sudo() {
    log_info "Configuring sudo permissions for system commands..."
    
    cat > "/etc/sudoers.d/$SERVICE_USER" << EOF
# Allow pwnagotchi user to execute system commands
$SERVICE_USER ALL=(ALL) NOPASSWD: /sbin/reboot
$SERVICE_USER ALL=(ALL) NOPASSWD: /sbin/shutdown
$SERVICE_USER ALL=(ALL) NOPASSWD: /sbin/iwlist
$SERVICE_USER ALL=(ALL) NOPASSWD: /bin/systemctl restart $SERVICE_NAME
EOF
    
    chmod 440 "/etc/sudoers.d/$SERVICE_USER"
    log_success "Sudo permissions configured"
}

# Create configuration file
create_config() {
    log_info "Creating configuration file..."
    
    cat > "$CONFIG_DIR/config.json" << EOF
{
    "server": {
        "host": "127.0.0.1",
        "port": 8080,
        "debug": $([ "$MODE" == "dev" ] && echo "true" || echo "false")
    },
    "security": {
        "secret_key": "$(openssl rand -hex 32)",
        "rate_limit": {
            "per_day": 200,
            "per_hour": 50,
            "per_minute": 10
        }
    },
    "logging": {
        "level": "$([ "$MODE" == "dev" ] && echo "DEBUG" || echo "INFO")",
        "file": "$LOG_DIR/api.log",
        "max_size": "10MB",
        "backup_count": 5
    },
    "pwnagotchi": {
        "name": "pwnagotchi",
        "scan_interval": 5,
        "auto_mode": true
    }
}
EOF
    
    chown "$SERVICE_USER:$SERVICE_USER" "$CONFIG_DIR/config.json"
    chmod 640 "$CONFIG_DIR/config.json"
    
    log_success "Configuration file created"
}

# Start services
start_services() {
    log_info "Starting services..."
    
    systemctl start "$SERVICE_NAME"
    systemctl status "$SERVICE_NAME" --no-pager -l
    
    if [[ "$MODE" == "prod" ]]; then
        systemctl start nginx
        systemctl status nginx --no-pager -l
    fi
    
    log_success "Services started"
}

# Health check
health_check() {
    log_info "Performing health check..."
    
    sleep 5  # Wait for service to fully start
    
    if [[ "$MODE" == "prod" ]]; then
        URL="http://localhost/api/status"
    else
        URL="http://localhost:8080/api/status"
    fi
    
    if curl -f -s "$URL" > /dev/null; then
        log_success "Health check passed - Dashboard is running"
    else
        log_error "Health check failed - Dashboard is not responding"
        systemctl status "$SERVICE_NAME" --no-pager -l
        exit 1
    fi
}

# Create uninstall script
create_uninstall() {
    log_info "Creating uninstall script..."
    
    cat > "$INSTALL_DIR/uninstall.sh" << 'EOF'
#!/bin/bash
# Pwnagotchi Dashboard Uninstall Script

set -euo pipefail

SERVICE_NAME="pwnagotchi-dashboard"
SERVICE_USER="pwnagotchi"
INSTALL_DIR="/opt/pwnagotchi-dashboard"
LOG_DIR="/var/log/pwnagotchi"
CONFIG_DIR="/etc/pwnagotchi"

echo "Stopping and disabling services..."
systemctl stop "$SERVICE_NAME" 2>/dev/null || true
systemctl disable "$SERVICE_NAME" 2>/dev/null || true

echo "Removing systemd service..."
rm -f "/etc/systemd/system/${SERVICE_NAME}.service"
systemctl daemon-reload

echo "Removing nginx configuration..."
rm -f "/etc/nginx/sites-enabled/pwnagotchi-dashboard"
rm -f "/etc/nginx/sites-available/pwnagotchi-dashboard"
systemctl reload nginx 2>/dev/null || true

echo "Removing sudo permissions..."
rm -f "/etc/sudoers.d/$SERVICE_USER"

echo "Removing directories..."
rm -rf "$INSTALL_DIR"
rm -rf "$LOG_DIR"
rm -rf "$CONFIG_DIR"

echo "Removing user..."
userdel "$SERVICE_USER" 2>/dev/null || true

echo "Uninstallation completed successfully!"
EOF
    
    chmod +x "$INSTALL_DIR/uninstall.sh"
    chown "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR/uninstall.sh"
    
    log_success "Uninstall script created at $INSTALL_DIR/uninstall.sh"
}

# Print installation summary
print_summary() {
    echo
    log_success "=== INSTALLATION COMPLETED SUCCESSFULLY ==="
    echo
    echo "Dashboard Information:"
    echo "  Installation Directory: $INSTALL_DIR"
    echo "  Configuration: $CONFIG_DIR/config.json"
    echo "  Logs: $LOG_DIR/"
    echo "  Service: $SERVICE_NAME"
    echo
    
    if [[ "$MODE" == "prod" ]]; then
        echo "Access URLs:"
        echo "  Dashboard: http://$(hostname -I | awk '{print $1}')"
        echo "  API Status: http://$(hostname -I | awk '{print $1}')/api/status"
    else
        echo "Access URLs:"
        echo "  Dashboard: http://localhost:8080"
        echo "  API Status: http://localhost:8080/api/status"
    fi
    
    echo
    echo "Service Management:"
    echo "  Start:   sudo systemctl start $SERVICE_NAME"
    echo "  Stop:    sudo systemctl stop $SERVICE_NAME"
    echo "  Restart: sudo systemctl restart $SERVICE_NAME"
    echo "  Status:  sudo systemctl status $SERVICE_NAME"
    echo "  Logs:    sudo journalctl -u $SERVICE_NAME -f"
    echo
    echo "Uninstall:"
    echo "  Run: sudo $INSTALL_DIR/uninstall.sh"
    echo
    log_success "Installation completed in $MODE mode!"
}

# Main installation function
main() {
    echo "======================================"
    echo "Pwnagotchi Dashboard Installer"
    echo "Mode: $MODE"
    echo "======================================"
    echo
    
    check_root
    detect_os
    install_dependencies
    create_user
    create_directories
    install_application
    configure_systemd
    configure_nginx
    configure_firewall
    configure_sudo
    create_config
    start_services
    health_check
    create_uninstall
    print_summary
}

# Run main function
main "$@"
