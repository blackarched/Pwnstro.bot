#!/usr/bin/env python3
"""
Minimal Flask Backend API
Safe, minimal Flask skeleton with CORS, rate limiting, and structured logging
"""

import logging
import os
from datetime import datetime

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        # Add file handler if possible, fallback gracefully if not
        logging.FileHandler('api.log') if os.access('.', os.W_OK) else logging.NullHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Basic security configuration
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', os.urandom(24)),
    JSON_SORT_KEYS=False,
    JSONIFY_PRETTYPRINT_REGULAR=False
)

# CORS configuration - allow localhost for development
CORS(app, origins=['http://localhost:*', 'http://127.0.0.1:*'])

# Rate limiting with memory storage
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
    app=app
)


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500


@app.before_request
def before_request():
    """Log incoming requests"""
    logger.info(f"Request: {request.method} {request.path} from {request.remote_addr}")


@app.after_request
def after_request(response):
    """Add security headers"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response


@app.route('/health')
@limiter.limit("30 per minute")
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'service': 'backend-api'
    }), 200


@app.route('/api/status')
@limiter.limit("30 per minute")
def get_status():
    """Basic status endpoint"""
    return jsonify({
        'status': 'running',
        'timestamp': datetime.now().isoformat(),
        'uptime': 'available',
        'version': '1.0.0'
    }), 200


@app.route('/')
def index():
    """Root endpoint"""
    return jsonify({
        'message': 'Backend API is running',
        'endpoints': {
            '/health': 'Health check',
            '/api/status': 'Service status'
        }
    }), 200


if __name__ == '__main__':
    logger.info("Starting minimal Flask backend API")
    logger.info(f"Process PID: {os.getpid()}")
    
    # Start the Flask development server
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 8080)),
        debug=os.environ.get('DEBUG', 'False').lower() == 'true',
        threaded=True
    )