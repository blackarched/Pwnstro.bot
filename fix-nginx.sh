#!/bin/bash
#
# Quick fix for nginx configuration error
# This script fixes the limit_req_zone directive placement issue
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    log_error "This script must be run as root (use sudo)"
    exit 1
fi

log_info "Fixing nginx configuration for Pwnagotchi Dashboard..."

# Backup existing configurations
log_info "Creating backups..."
cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true

# Remove the problematic site configuration
log_info "Removing problematic site configuration..."
rm -f /etc/nginx/sites-enabled/pwnagotchi-dashboard
rm -f /etc/nginx/sites-available/pwnagotchi-dashboard

# Create a simple, working nginx configuration
log_info "Creating corrected nginx configuration..."

# First, add rate limiting zones to main nginx.conf if not present
if ! grep -q "limit_req_zone.*pwnagotchi" /etc/nginx/nginx.conf; then
    log_info "Adding rate limiting zones to nginx.conf..."
    
    # Create temporary file with updated nginx.conf
    awk '
    /http {/ { 
        print
        print "    # Pwnagotchi rate limiting zones"
        print "    limit_req_zone $binary_remote_addr zone=pwnagotchi_api:10m rate=10r/m;"
        print "    limit_req_zone $binary_remote_addr zone=pwnagotchi_general:10m rate=60r/m;"
        print ""
        next
    }
    { print }
    ' /etc/nginx/nginx.conf > /tmp/nginx.conf.tmp
    
    mv /tmp/nginx.conf.tmp /etc/nginx/nginx.conf
fi

# Create simple site configuration without rate limiting zones
cat > /etc/nginx/sites-available/pwnagotchi-dashboard << 'EOF'
# Pwnagotchi Dashboard - Simplified Configuration

# Upstream backend
upstream pwnagotchi_backend {
    server 127.0.0.1:8080 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

# Main server block
server {
    listen 80;
    listen [::]:80;
    server_name _;
    
    # Security headers
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # Hide nginx version
    server_tokens off;
    
    # Request size limits
    client_max_body_size 10M;
    client_body_buffer_size 128k;
    
    # Timeouts
    client_body_timeout 12;
    client_header_timeout 12;
    keepalive_timeout 15;
    send_timeout 10;
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1000;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml;
    
    # Main application
    location / {
        limit_req zone=pwnagotchi_general burst=20 nodelay;
        
        proxy_pass http://pwnagotchi_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # API endpoints with stricter rate limiting
    location /api/ {
        limit_req zone=pwnagotchi_api burst=20 nodelay;
        
        proxy_pass http://pwnagotchi_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # No caching for API
        add_header Cache-Control "no-cache, no-store, must-revalidate";
        add_header Pragma "no-cache";
        add_header Expires "0";
    }
    
    # Health check endpoint (bypass rate limiting)
    location = /health {
        access_log off;
        proxy_pass http://pwnagotchi_backend/api/status;
        proxy_set_header Host $host;
    }
    
    # Static files with caching
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        proxy_pass http://pwnagotchi_backend;
        expires 1d;
        add_header Cache-Control "public";
    }
    
    # Block access to sensitive files
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
    
    # Logging
    access_log /var/log/nginx/pwnagotchi-access.log;
    error_log /var/log/nginx/pwnagotchi-error.log;
}
EOF

# Enable the site
log_info "Enabling site configuration..."
ln -sf /etc/nginx/sites-available/pwnagotchi-dashboard /etc/nginx/sites-enabled/

# Test nginx configuration
log_info "Testing nginx configuration..."
if nginx -t; then
    log_success "Nginx configuration test passed!"
    
    # Restart nginx
    log_info "Restarting nginx..."
    systemctl restart nginx
    
    # Check nginx status
    if systemctl is-active --quiet nginx; then
        log_success "Nginx restarted successfully!"
    else
        log_error "Nginx failed to start"
        systemctl status nginx
        exit 1
    fi
else
    log_error "Nginx configuration test failed"
    cat /etc/nginx/sites-available/pwnagotchi-dashboard
    exit 1
fi

# Start the pwnagotchi dashboard service
log_info "Starting Pwnagotchi Dashboard service..."
systemctl enable pwnagotchi-dashboard
systemctl start pwnagotchi-dashboard

# Wait a moment and check status
sleep 3

if systemctl is-active --quiet pwnagotchi-dashboard; then
    log_success "Pwnagotchi Dashboard service is running!"
else
    log_error "Pwnagotchi Dashboard service failed to start"
    systemctl status pwnagotchi-dashboard
fi

# Test the connection
log_info "Testing dashboard connection..."
sleep 5

if curl -f -s http://localhost/api/status > /dev/null; then
    log_success "Dashboard is accessible via nginx!"
    echo
    echo "✅ SETUP COMPLETE!"
    echo
    echo "Access your dashboard at:"
    echo "  http://localhost"
    echo "  http://$(hostname -I | awk '{print $1}')"
    echo
    echo "Direct API access:"
    echo "  http://localhost:8080"
    echo
elif curl -f -s http://localhost:8080/api/status > /dev/null; then
    log_success "Dashboard backend is running on port 8080!"
    echo
    echo "⚠️  Nginx proxy working, but check configuration"
    echo
    echo "Access your dashboard at:"
    echo "  http://localhost:8080 (direct)"
    echo
else
    log_error "Dashboard is not responding"
    echo
    echo "Troubleshooting steps:"
    echo "1. Check service status: sudo systemctl status pwnagotchi-dashboard"
    echo "2. Check logs: sudo journalctl -u pwnagotchi-dashboard -f"
    echo "3. Check if port is open: sudo lsof -i :8080"
    echo "4. Try direct python run: cd $(pwd) && python3 backend_api.py"
fi

log_info "Fix script completed!"
EOF
