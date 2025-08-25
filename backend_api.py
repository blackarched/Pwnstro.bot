#!/usr/bin/env python3
"""
Minimal Backend API

Safe Flask skeleton with:
- CORS enabled
- Flask-Limiter rate limiting
- Structured JSON logging
- /health endpoint

No subprocess calls; suitable for local development.
"""

import json
import logging
import os
from datetime import datetime

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


class JsonLogFormatter(logging.Formatter):
    """Structured JSON log formatter for consistent logs."""

    def format(self, record: logging.LogRecord) -> str:
        log_payload = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Add request context fields when available
        try:
            if request:
                log_payload.update(
                    {
                        "method": request.method,
                        "path": request.path,
                        "remote_addr": request.remote_addr,
                    }
                )
        except RuntimeError:
            # Outside request context
            pass
        return json.dumps(log_payload, ensure_ascii=False)


def create_app() -> Flask:
    app = Flask(__name__)

    # App config
    app.config.update(
        JSON_SORT_KEYS=False,
        JSONIFY_PRETTYPRINT_REGULAR=False,
        PROPAGATE_EXCEPTIONS=True,
    )

    # CORS: allow all origins for local development
    CORS(app, resources={r"*": {"origins": "*"}})

    # Rate limiting (Flask-Limiter v3)
    Limiter(
        key_func=get_remote_address,
        default_limits=["120 per minute"],
        storage_uri="memory://",
        app=app,
    )

    # Logging
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    app.logger.handlers = [handler]
    app.logger.setLevel(logging.INFO)
    logging.getLogger("werkzeug").handlers = [handler]
    logging.getLogger("werkzeug").setLevel(logging.INFO)

    @app.before_request
    def _log_request() -> None:
        app.logger.info("request")

    @app.after_request
    def _set_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"}), 200

    @app.route("/", methods=["GET"])
    def root():
        return jsonify({"message": "backend online"}), 200

    return app


app = create_app()


if __name__ == "__main__":
    app.logger.info("Starting backend on 0.0.0.0:8080")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=True, threaded=True)
