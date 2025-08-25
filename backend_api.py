#!/usr/bin/env python3
"""
Safe minimal Flask backend API with CORS, rate limiting, and structured logging.
"""

import logging
import sys
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
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('backend_api.log')
    ]
)

logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Configure CORS
CORS(app, origins="*", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

# Configure rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

@app.before_request
def log_request_info():
    """Log incoming requests for debugging and monitoring."""
    logger.info(f"Request: {request.method} {request.url} from {request.remote_addr}")

@app.after_request
def log_response_info(response):
    """Log response information."""
    logger.info(f"Response: {response.status_code} for {request.method} {request.url}")
    return response

@app.route('/health', methods=['GET'])
@limiter.exempt
def health_check():
    """Health check endpoint."""
    logger.info("Health check requested")
    return jsonify({
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "backend-api"
    }), 200

@app.route('/', methods=['GET'])
@limiter.limit("10 per minute")
def root():
    """Root endpoint with basic API information."""
    return jsonify({
        "message": "Backend API is running",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "root": "/"
        }
    }), 200

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    logger.warning(f"404 error for {request.url}")
    return jsonify({
        "error": "Not found",
        "message": "The requested endpoint does not exist"
    }), 404

@app.errorhandler(429)
def rate_limit_exceeded(error):
    """Handle rate limit exceeded errors."""
    logger.warning(f"Rate limit exceeded for {request.remote_addr}")
    return jsonify({
        "error": "Rate limit exceeded",
        "message": "Too many requests. Please try again later."
    }), 429

@app.errorhandler(500)
def internal_error(error):
    """Handle internal server errors."""
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({
        "error": "Internal server error",
        "message": "An unexpected error occurred"
    }), 500

if __name__ == '__main__':
    logger.info("Starting Flask backend API server...")
    app.run(
        host='0.0.0.0',
        port=8080,
        debug=True,
        threaded=True
    )