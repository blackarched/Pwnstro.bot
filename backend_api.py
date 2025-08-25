#!/usr/bin/env python3
"""
Pwnagotchi Backend API
Production-ready Flask backend for the Pwnagotchi dashboard

Security Features:
- CORS protection
- Input validation
- Rate limiting
- Secure headers
- Error handling and logging
"""

import json
import logging
import os
import subprocess
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import psutil
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging safely
log_handlers = []
try:
    os.makedirs('/var/log/pwnagotchi', exist_ok=True)
    log_handlers.append(logging.FileHandler('/var/log/pwnagotchi/api.log'))
except Exception:
    # Fallback to console-only if log directory is not writable
    pass

log_handlers.append(logging.StreamHandler())

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=log_handlers
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Security configuration
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', os.urandom(24)),
    JSON_SORT_KEYS=False,
    JSONIFY_PRETTYPRINT_REGULAR=False
)

# CORS configuration
CORS(app, origins=['http://localhost:*', 'http://127.0.0.1:*'])

# Rate limiting (Flask-Limiter v3.x API: pass app as keyword or init_app)
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
    app=app
)

# Global system state
system_state = {
    'start_time': time.time(),
    'networks_seen': 0,
    'handshakes': 0,
    'peers_met': 0,
    'mode': 'AUTO',
    'config': {
        'name': 'pwnagotchi',
        'scan_interval': 5
    },
    'logs': [],
    'network_interfaces': []
}


class SystemMonitor:
    """System monitoring and control functionality"""
    
    @staticmethod
    def get_system_stats() -> Dict:
        """Get current system statistics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            # Get temperature (Linux-specific)
            temperature = SystemMonitor.get_cpu_temperature()
            
            # Calculate uptime
            uptime_seconds = int(time.time() - system_state['start_time'])
            
            return {
                'uptime': uptime_seconds,
                'cpu_usage': round(cpu_percent, 1),
                'memory_usage': round(memory.percent, 1),
                'temperature': temperature,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return {
                'uptime': 0,
                'cpu_usage': 0,
                'memory_usage': 0,
                'temperature': 0,
                'timestamp': datetime.now().isoformat()
            }
    
    @staticmethod
    def get_cpu_temperature() -> float:
        """Get CPU temperature from system sensors"""
        try:
            # Try different temperature sources
            temp_files = [
                '/sys/class/thermal/thermal_zone0/temp',
                '/sys/class/thermal/thermal_zone1/temp'
            ]
            
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    with open(temp_file, 'r') as f:
                        temp_millicelsius = int(f.read().strip())
                        return round(temp_millicelsius / 1000.0, 1)
            
            # Fallback: try vcgencmd for Raspberry Pi
            result = subprocess.run(
                ['vcgencmd', 'measure_temp'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                temp_str = result.stdout.strip()
                if 'temp=' in temp_str:
                    return float(temp_str.split('=')[1].replace("'C", ""))
            
        except Exception as e:
            logger.debug(f"Could not read temperature: {e}")
        
        return 0.0
    
    @staticmethod
    def get_network_interfaces() -> List[Dict]:
        """Get network interface information"""
        try:
            interfaces = []
            net_if_addrs = psutil.net_if_addrs()
            net_if_stats = psutil.net_if_stats()
            
            for interface_name, addresses in net_if_addrs.items():
                if interface_name.startswith(('lo', 'docker')):
                    continue
                
                stats = net_if_stats.get(interface_name)
                if not stats:
                    continue
                
                interface_info = {
                    'name': interface_name,
                    'active': stats.isup,
                    'type': SystemMonitor.get_interface_type(interface_name),
                    'status': 'UP' if stats.isup else 'DOWN',
                    'ip': None
                }
                
                # Get IP address
                for addr in addresses:
                    if addr.family == 2:  # AF_INET (IPv4)
                        interface_info['ip'] = addr.address
                        break
                
                interfaces.append(interface_info)
            
            return interfaces
            
        except Exception as e:
            logger.error(f"Error getting network interfaces: {e}")
            return []
    
    @staticmethod
    def get_interface_type(interface_name: str) -> str:
        """Determine interface type based on name"""
        if interface_name.startswith('wlan') or interface_name.startswith('wifi'):
            return 'WiFi'
        elif interface_name.startswith('eth') or interface_name.startswith('enp'):
            return 'Ethernet'
        elif interface_name.startswith('usb'):
            return 'USB'
        else:
            return 'Unknown'


class PwnagotchiCore:
    """Core Pwnagotchi functionality simulation"""
    
    @staticmethod
    def scan_networks() -> int:
        """Simulate network scanning"""
        try:
            # Use iwlist to scan for networks (requires root)
            result = subprocess.run(
                ['iwlist', 'scan'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # Count unique SSIDs
                ssids = set()
                for line in result.stdout.split('\n'):
                    if 'ESSID:' in line:
                        ssid = line.split('ESSID:')[1].strip().strip('"')
                        if ssid and ssid != '<hidden>':
                            ssids.add(ssid)
                
                networks_found = len(ssids)
                system_state['networks_seen'] += networks_found
                
                add_log_entry(f"Network scan completed: {networks_found} networks found")
                return networks_found
            
        except Exception as e:
            logger.error(f"Network scan failed: {e}")
            add_log_entry(f"Network scan failed: {str(e)}", level='error')
        
        return 0
    
    @staticmethod
    def toggle_mode() -> bool:
        """Toggle between AUTO and MANUAL mode"""
        try:
            current_mode = system_state['mode']
            new_mode = 'MANUAL' if current_mode == 'AUTO' else 'AUTO'
            system_state['mode'] = new_mode
            
            add_log_entry(f"Mode changed from {current_mode} to {new_mode}")
            return True
            
        except Exception as e:
            logger.error(f"Mode toggle failed: {e}")
            add_log_entry(f"Mode toggle failed: {str(e)}", level='error')
            return False


def add_log_entry(message: str, level: str = 'info') -> None:
    """Add entry to system log"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'level': level,
        'message': message
    }
    
    system_state['logs'].append(log_entry)
    
    # Keep only last 500 log entries
    if len(system_state['logs']) > 500:
        system_state['logs'] = system_state['logs'][-500:]
    
    # Log to file as well
    if level == 'error':
        logger.error(message)
    elif level == 'warning':
        logger.warning(message)
    else:
        logger.info(message)


def validate_config(config: Dict) -> Tuple[bool, str]:
    """Validate configuration parameters"""
    if not isinstance(config, dict):
        return False, "Configuration must be a dictionary"
    
    if 'name' in config:
        if not isinstance(config['name'], str) or len(config['name']) > 32:
            return False, "Name must be a string with max 32 characters"
    
    if 'scan_interval' in config:
        if not isinstance(config['scan_interval'], int) or not (1 <= config['scan_interval'] <= 60):
            return False, "Scan interval must be an integer between 1 and 60"
    
    return True, ""


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500


@app.before_request
def before_request():
    """Add security headers and logging"""
    # Log request
    logger.debug(f"{request.method} {request.path} from {request.remote_addr}")


@app.after_request
def after_request(response):
    """Add security headers"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    # Only enable HSTS when explicitly requested (not useful for localhost)
    if os.environ.get('ENABLE_HSTS', 'false').lower() == 'true':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response


@app.route('/')
def index():
    """Serve dashboard HTML"""
    return send_from_directory('.', 'pwnagotchi_dashboard.html')


@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory('.', filename)


@app.route('/api/status')
@limiter.limit("30 per minute")
def get_status():
    """Get current system status"""
    try:
        system_stats = SystemMonitor.get_system_stats()
        network_interfaces = SystemMonitor.get_network_interfaces()
        
        status_data = {
            **system_stats,
            'networks_seen': system_state['networks_seen'],
            'handshakes': system_state['handshakes'],
            'peers_met': system_state['peers_met'],
            'mode': system_state['mode'],
            'config': system_state['config'],
            'interfaces': network_interfaces,
            'logs': system_state['logs'][-10:],  # Last 10 log entries
            'status': 'ACTIVE'
        }
        
        return jsonify(status_data)
        
    except Exception as e:
        logger.error(f"Status endpoint error: {e}")
        return jsonify({'error': 'Failed to get status'}), 500


@app.route('/api/command', methods=['POST'])
@limiter.limit("10 per minute")
def execute_command():
    """Execute system commands"""
    try:
        data = request.get_json()
        if not data or 'command' not in data:
            return jsonify({'error': 'Missing command parameter'}), 400
        
        command = data['command']
        add_log_entry(f"Received command: {command}")
        
        if command == 'toggle_mode':
            success = PwnagotchiCore.toggle_mode()
            return jsonify({'success': success})
        
        elif command == 'scan_networks':
            networks_found = PwnagotchiCore.scan_networks()
            return jsonify({'success': True, 'networks_found': networks_found})
        
        elif command == 'update_config':
            config = data.get('config', {})
            valid, error_msg = validate_config(config)
            
            if not valid:
                return jsonify({'error': error_msg}), 400
            
            system_state['config'].update(config)
            add_log_entry(f"Configuration updated: {config}")
            return jsonify({'success': True})
        
        elif command == 'reboot':
            add_log_entry("System reboot requested", level='warning')
            # In production, you would execute: subprocess.run(['sudo', 'reboot'])
            return jsonify({'success': True, 'message': 'Reboot command received (simulated)'})
        
        elif command == 'shutdown':
            add_log_entry("System shutdown requested", level='warning')
            # In production, you would execute: subprocess.run(['sudo', 'shutdown', '-h', 'now'])
            return jsonify({'success': True, 'message': 'Shutdown command received (simulated)'})
        
        else:
            return jsonify({'error': f'Unknown command: {command}'}), 400
    
    except Exception as e:
        logger.error(f"Command execution error: {e}")
        return jsonify({'error': 'Command execution failed'}), 500


@app.route('/api/export/data')
@limiter.limit("5 per minute")
def export_data():
    """Export system data"""
    try:
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'system_state': system_state,
            'system_stats': SystemMonitor.get_system_stats(),
            'network_interfaces': SystemMonitor.get_network_interfaces()
        }
        
        response = jsonify(export_data)
        response.headers['Content-Disposition'] = f'attachment; filename=pwnagotchi_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        
        add_log_entry("Data export requested")
        return response
        
    except Exception as e:
        logger.error(f"Data export error: {e}")
        return jsonify({'error': 'Export failed'}), 500


if __name__ == '__main__':
    # Initialize system
    add_log_entry("Pwnagotchi API starting up")
    add_log_entry(f"System initialized with PID {os.getpid()}")
    
    # Create log directory if it doesn't exist (best-effort; ignore if not permitted)
    try:
        os.makedirs('/var/log/pwnagotchi', exist_ok=True)
    except Exception:
        pass
    
    # Start server
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 8080)),
        debug=os.environ.get('DEBUG', 'False').lower() == 'true',
        threaded=True
    )
