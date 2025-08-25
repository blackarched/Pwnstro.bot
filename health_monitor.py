#!/usr/bin/env python3
"""
Pwnagotchi Health Monitor
Advanced monitoring and alerting system for production deployments

Features:
- System health checks
- Performance metrics
- Alerting mechanisms
- Log analysis
- Automatic recovery
"""

import json
import logging
import os
import psutil
import requests
import smtplib
import subprocess
import time
from datetime import datetime, timedelta
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from typing import Dict, List, Optional, Tuple

import schedule

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/pwnagotchi/health_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class HealthMonitor:
    """Comprehensive health monitoring system"""
    
    def __init__(self, config_path: str = '/etc/pwnagotchi/health_config.json'):
        self.config = self.load_config(config_path)
        self.alerts_sent = {}
        self.last_checks = {}
        self.metrics_history = []
        
    def load_config(self, config_path: str) -> Dict:
        """Load monitoring configuration"""
        default_config = {
            'api_url': 'http://localhost:8080/api',
            'checks': {
                'api_response': {'enabled': True, 'timeout': 10, 'threshold': 5.0},
                'cpu_usage': {'enabled': True, 'threshold': 90.0},
                'memory_usage': {'enabled': True, 'threshold': 85.0},
                'disk_usage': {'enabled': True, 'threshold': 90.0},
                'temperature': {'enabled': True, 'threshold': 80.0},
                'process_count': {'enabled': True, 'threshold': 500}
            },
            'alerts': {
                'email': {
                    'enabled': False,
                    'smtp_server': 'localhost',
                    'smtp_port': 587,
                    'username': '',
                    'password': '',
                    'from_email': 'pwnagotchi@localhost',
                    'to_emails': ['admin@localhost']
                },
                'webhook': {
                    'enabled': False,
                    'url': '',
                    'headers': {}
                },
                'cooldown': 300  # 5 minutes between duplicate alerts
            },
            'recovery': {
                'auto_restart': True,
                'max_restart_attempts': 3,
                'restart_cooldown': 600  # 10 minutes
            },
            'metrics': {
                'retention_hours': 72,
                'collection_interval': 60
            }
        }
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                    # Merge with defaults
                    return self.deep_merge(default_config, user_config)
            else:
                # Create default config file
                os.makedirs(os.path.dirname(config_path), exist_ok=True)
                with open(config_path, 'w') as f:
                    json.dump(default_config, f, indent=2)
                logger.info(f"Created default config at {config_path}")
                
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            
        return default_config
    
    def deep_merge(self, default: Dict, user: Dict) -> Dict:
        """Deep merge user config with defaults"""
        result = default.copy()
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self.deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    def check_api_health(self) -> Tuple[bool, Dict]:
        """Check API endpoint health"""
        try:
            start_time = time.time()
            response = requests.get(
                f"{self.config['api_url']}/status",
                timeout=self.config['checks']['api_response']['timeout']
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                threshold = self.config['checks']['api_response']['threshold']
                
                return response_time < threshold, {
                    'status_code': response.status_code,
                    'response_time': response_time,
                    'threshold': threshold,
                    'data': data
                }
            else:
                return False, {
                    'status_code': response.status_code,
                    'response_time': response_time,
                    'error': 'Non-200 status code'
                }
                
        except Exception as e:
            return False, {
                'error': str(e),
                'response_time': float('inf')
            }
    
    def check_system_resources(self) -> Tuple[bool, Dict]:
        """Check system resource usage"""
        try:
            # CPU usage
            cpu_usage = psutil.cpu_percent(interval=1)
            cpu_ok = cpu_usage < self.config['checks']['cpu_usage']['threshold']
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_ok = memory.percent < self.config['checks']['memory_usage']['threshold']
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_usage = (disk.used / disk.total) * 100
            disk_ok = disk_usage < self.config['checks']['disk_usage']['threshold']
            
            # Process count
            process_count = len(psutil.pids())
            process_ok = process_count < self.config['checks']['process_count']['threshold']
            
            # Temperature
            temperature = self.get_cpu_temperature()
            temp_ok = temperature < self.config['checks']['temperature']['threshold']
            
            all_ok = cpu_ok and memory_ok and disk_ok and process_ok and temp_ok
            
            return all_ok, {
                'cpu': {'usage': cpu_usage, 'ok': cpu_ok},
                'memory': {'usage': memory.percent, 'ok': memory_ok},
                'disk': {'usage': disk_usage, 'ok': disk_ok},
                'processes': {'count': process_count, 'ok': process_ok},
                'temperature': {'value': temperature, 'ok': temp_ok}
            }
            
        except Exception as e:
            return False, {'error': str(e)}
    
    def get_cpu_temperature(self) -> float:
        """Get CPU temperature"""
        try:
            # Try reading from thermal zone
            temp_files = [
                '/sys/class/thermal/thermal_zone0/temp',
                '/sys/class/thermal/thermal_zone1/temp'
            ]
            
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    with open(temp_file, 'r') as f:
                        temp_millicelsius = int(f.read().strip())
                        return temp_millicelsius / 1000.0
            
            # Try vcgencmd for Raspberry Pi
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
            
        except Exception:
            pass
        
        return 0.0
    
    def check_service_status(self) -> Tuple[bool, Dict]:
        """Check systemd service status"""
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', 'pwnagotchi-dashboard'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            is_active = result.stdout.strip() == 'active'
            
            # Get service info
            status_result = subprocess.run(
                ['systemctl', 'status', 'pwnagotchi-dashboard', '--no-pager'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            return is_active, {
                'active': is_active,
                'status_output': status_result.stdout,
                'return_code': result.returncode
            }
            
        except Exception as e:
            return False, {'error': str(e)}
    
    def check_log_errors(self) -> Tuple[bool, Dict]:
        """Check for critical errors in logs"""
        try:
            log_file = '/var/log/pwnagotchi/api.log'
            if not os.path.exists(log_file):
                return True, {'message': 'Log file not found'}
            
            # Check last 100 lines for errors
            result = subprocess.run(
                ['tail', '-n', '100', log_file],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            error_keywords = ['ERROR', 'CRITICAL', 'FATAL', 'Exception', 'Traceback']
            error_lines = []
            
            for line in result.stdout.split('\n'):
                if any(keyword in line for keyword in error_keywords):
                    error_lines.append(line.strip())
            
            # Only recent errors (last 5 minutes)
            recent_errors = []
            now = datetime.now()
            for line in error_lines[-10:]:  # Last 10 errors
                try:
                    # Extract timestamp from log line
                    timestamp_str = line.split(' - ')[0]
                    log_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
                    if now - log_time < timedelta(minutes=5):
                        recent_errors.append(line)
                except Exception:
                    # If timestamp parsing fails, include the error anyway
                    recent_errors.append(line)
            
            has_recent_errors = len(recent_errors) > 0
            
            return not has_recent_errors, {
                'recent_errors': recent_errors,
                'total_errors_checked': len(error_lines)
            }
            
        except Exception as e:
            return False, {'error': str(e)}
    
    def run_health_check(self) -> Dict:
        """Run comprehensive health check"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'healthy',
            'checks': {}
        }
        
        all_checks_ok = True
        
        # API health check
        if self.config['checks']['api_response']['enabled']:
            api_ok, api_data = self.check_api_health()
            results['checks']['api'] = {'status': 'ok' if api_ok else 'error', 'data': api_data}
            all_checks_ok = all_checks_ok and api_ok
        
        # System resources
        resource_checks = ['cpu_usage', 'memory_usage', 'disk_usage', 'temperature', 'process_count']
        if any(self.config['checks'][check]['enabled'] for check in resource_checks):
            resources_ok, resources_data = self.check_system_resources()
            results['checks']['resources'] = {'status': 'ok' if resources_ok else 'error', 'data': resources_data}
            all_checks_ok = all_checks_ok and resources_ok
        
        # Service status
        service_ok, service_data = self.check_service_status()
        results['checks']['service'] = {'status': 'ok' if service_ok else 'error', 'data': service_data}
        all_checks_ok = all_checks_ok and service_ok
        
        # Log errors
        logs_ok, logs_data = self.check_log_errors()
        results['checks']['logs'] = {'status': 'ok' if logs_ok else 'warning', 'data': logs_data}
        # Don't fail overall status for log warnings, but include in alerts
        
        results['overall_status'] = 'healthy' if all_checks_ok else 'unhealthy'
        
        return results
    
    def send_alert(self, alert_type: str, message: str, details: Dict = None):
        """Send alert via configured channels"""
        alert_key = f"{alert_type}_{hash(message)}"
        now = time.time()
        
        # Check cooldown
        if alert_key in self.alerts_sent:
            if now - self.alerts_sent[alert_key] < self.config['alerts']['cooldown']:
                return  # Skip duplicate alert
        
        self.alerts_sent[alert_key] = now
        
        # Email alert
        if self.config['alerts']['email']['enabled']:
            self.send_email_alert(alert_type, message, details)
        
        # Webhook alert
        if self.config['alerts']['webhook']['enabled']:
            self.send_webhook_alert(alert_type, message, details)
        
        logger.warning(f"Alert sent: {alert_type} - {message}")
    
    def send_email_alert(self, alert_type: str, message: str, details: Dict = None):
        """Send email alert"""
        try:
            email_config = self.config['alerts']['email']
            
            msg = MimeMultipart()
            msg['From'] = email_config['from_email']
            msg['To'] = ', '.join(email_config['to_emails'])
            msg['Subject'] = f"Pwnagotchi Alert: {alert_type}"
            
            body = f"""
Pwnagotchi Health Monitor Alert

Type: {alert_type}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Message: {message}

Details:
{json.dumps(details, indent=2) if details else 'No additional details'}

---
Pwnagotchi Health Monitor
            """
            
            msg.attach(MimeText(body, 'plain'))
            
            server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
            if email_config['username']:
                server.starttls()
                server.login(email_config['username'], email_config['password'])
            
            server.send_message(msg)
            server.quit()
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
    
    def send_webhook_alert(self, alert_type: str, message: str, details: Dict = None):
        """Send webhook alert"""
        try:
            webhook_config = self.config['alerts']['webhook']
            
            payload = {
                'alert_type': alert_type,
                'message': message,
                'timestamp': datetime.now().isoformat(),
                'details': details,
                'source': 'pwnagotchi-health-monitor'
            }
            
            headers = webhook_config.get('headers', {})
            headers['Content-Type'] = 'application/json'
            
            response = requests.post(
                webhook_config['url'],
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code >= 400:
                logger.error(f"Webhook alert failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
    
    def attempt_recovery(self, check_results: Dict):
        """Attempt automatic recovery"""
        if not self.config['recovery']['auto_restart']:
            return
        
        recovery_key = 'service_restart'
        now = time.time()
        
        # Check restart cooldown
        if recovery_key in self.last_checks:
            if now - self.last_checks[recovery_key] < self.config['recovery']['restart_cooldown']:
                return
        
        # Check if service is down
        service_check = check_results['checks'].get('service', {})
        if service_check.get('status') == 'error':
            try:
                logger.info("Attempting service restart...")
                result = subprocess.run(
                    ['sudo', 'systemctl', 'restart', 'pwnagotchi-dashboard'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    self.send_alert('RECOVERY', 'Service automatically restarted')
                    logger.info("Service restart successful")
                else:
                    self.send_alert('RECOVERY_FAILED', f'Service restart failed: {result.stderr}')
                    logger.error(f"Service restart failed: {result.stderr}")
                
                self.last_checks[recovery_key] = now
                
            except Exception as e:
                self.send_alert('RECOVERY_FAILED', f'Recovery attempt failed: {str(e)}')
                logger.error(f"Recovery attempt failed: {e}")
    
    def collect_metrics(self):
        """Collect metrics for trend analysis"""
        try:
            check_results = self.run_health_check()
            
            # Store metrics with timestamp
            metric_entry = {
                'timestamp': datetime.now().isoformat(),
                'results': check_results
            }
            
            self.metrics_history.append(metric_entry)
            
            # Cleanup old metrics
            retention_hours = self.config['metrics']['retention_hours']
            cutoff_time = datetime.now() - timedelta(hours=retention_hours)
            
            self.metrics_history = [
                entry for entry in self.metrics_history
                if datetime.fromisoformat(entry['timestamp']) > cutoff_time
            ]
            
            # Save to file
            metrics_file = '/var/log/pwnagotchi/metrics.json'
            with open(metrics_file, 'w') as f:
                json.dump(self.metrics_history, f, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
    
    def monitor_loop(self):
        """Main monitoring loop"""
        logger.info("Starting health monitor loop")
        
        # Schedule regular checks
        schedule.every().minute.do(self.collect_metrics)
        schedule.every(5).minutes.do(self.run_scheduled_check)
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(30)  # Check every 30 seconds
            except KeyboardInterrupt:
                logger.info("Health monitor stopped")
                break
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                time.sleep(60)  # Wait longer on error
    
    def run_scheduled_check(self):
        """Run scheduled health check"""
        try:
            results = self.run_health_check()
            
            # Check for issues and send alerts
            if results['overall_status'] != 'healthy':
                failed_checks = []
                for check_name, check_result in results['checks'].items():
                    if check_result['status'] == 'error':
                        failed_checks.append(check_name)
                
                message = f"Health check failed: {', '.join(failed_checks)}"
                self.send_alert('HEALTH_CHECK_FAILED', message, results)
                
                # Attempt recovery
                self.attempt_recovery(results)
            
            # Check for warnings
            warning_checks = []
            for check_name, check_result in results['checks'].items():
                if check_result['status'] == 'warning':
                    warning_checks.append(check_name)
            
            if warning_checks:
                message = f"Health check warnings: {', '.join(warning_checks)}"
                self.send_alert('HEALTH_CHECK_WARNING', message, results)
            
        except Exception as e:
            logger.error(f"Error in scheduled check: {e}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Pwnagotchi Health Monitor')
    parser.add_argument('--config', default='/etc/pwnagotchi/health_config.json',
                       help='Path to configuration file')
    parser.add_argument('--check', action='store_true',
                       help='Run single health check and exit')
    parser.add_argument('--daemon', action='store_true',
                       help='Run as daemon')
    
    args = parser.parse_args()
    
    monitor = HealthMonitor(args.config)
    
    if args.check:
        # Single check mode
        results = monitor.run_health_check()
        print(json.dumps(results, indent=2))
        exit(0 if results['overall_status'] == 'healthy' else 1)
    
    elif args.daemon:
        # Daemon mode
        monitor.monitor_loop()
    
    else:
        # Interactive mode
        results = monitor.run_health_check()
        print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
