"""
Bridge Server - Industrial Grade Implementation
================================================
A robust local server that acts as a bridge between a PyQt6 desktop application
and a browser-based API client. This server facilitates communication when
direct API access is restricted due to network limitations.

Author: Professional Development Team
Version: 1.0.0
License: MIT
"""

import asyncio
import json
import logging
import signal
import sys
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, Any, List, Tuple
from queue import Queue, Empty, Full
from threading import Thread, Event, Lock

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
import aiohttp

# ============================================================================
# Configuration & Constants
# ============================================================================

class Config:
    """Central configuration management for the bridge server."""

    # Server Configuration
    HOST = "127.0.0.1"  # Localhost only for security
    PORT = 5000
    DEBUG_MODE = False
    THREADED = True

    # Queue Configuration
    MAX_QUEUE_SIZE = 100
    REQUEST_TIMEOUT_SECONDS = 30
    CLEANUP_INTERVAL_SECONDS = 60

    # Logging Configuration
    LOG_LEVEL = logging.INFO
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE = "bridge_server.log"

    # Security Configuration
    MAX_REQUEST_SIZE = 1024 * 1024  # 1MB
    ALLOWED_ORIGINS = ["*"]  # For local development
    API_KEY_HEADER = "X-Bridge-Key"

    # Performance Configuration
    POLLING_INTERVAL_MS = 500
    MAX_CONCURRENT_REQUESTS = 5

# ============================================================================
# Data Models
# ============================================================================

class MessageType(Enum):
    """Enumeration of message types supported by the bridge."""
    TEXT = "text"
    IMAGE = "image"
    SYSTEM = "system"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    STREAM = "stream"
    STREAM_END = "stream_end"

class MessageStatus(Enum):
    """Status tracking for message lifecycle."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"

@dataclass
class BridgeMessage:
    """Represents a message passing through the bridge."""
    id: str
    type: MessageType
    payload: Any
    timestamp: float
    status: MessageStatus = MessageStatus.PENDING
    metadata: Dict[str, Any] = None
    response: Optional[Any] = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "type": self.type.value if isinstance(self.type, MessageType) else self.type,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "status": self.status.value if isinstance(self.status, MessageStatus) else self.status,
            "metadata": self.metadata,
            "response": self.response,
            "error": self.error
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BridgeMessage':
        """Create a BridgeMessage from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            type=MessageType(data.get("type", "text")),
            payload=data.get("payload"),
            timestamp=data.get("timestamp", time.time()),
            status=MessageStatus(data.get("status", "pending")),
            metadata=data.get("metadata", {}),
            response=data.get("response"),
            error=data.get("error")
        )

# ============================================================================
# Queue Management
# ============================================================================

class MessageQueueManager:
    """Manages message queues with proper synchronization and cleanup."""

    def __init__(self, max_size: int = Config.MAX_QUEUE_SIZE):
        self.request_queue: Queue = Queue(maxsize=max_size)
        self.response_queue: Queue = Queue(maxsize=max_size)
        self.stream_queue: Queue = Queue(maxsize=max_size)
        self._lock = Lock()
        self._active_requests: Dict[str, BridgeMessage] = {}
        self._streaming_responses: Dict[str, List[str]] = {}

        # Statistics
        self.stats = {
            "total_requests": 0,
            "total_responses": 0,
            "failed_requests": 0,
            "average_response_time": 0.0,
            "uptime_start": time.time()
        }

    def put_request(self, message: BridgeMessage) -> bool:
        """Add a request to the queue with overflow protection."""
        try:
            self.request_queue.put(message, timeout=1)
            with self._lock:
                self._active_requests[message.id] = message
                self.stats["total_requests"] += 1
            return True
        except Full:
            logging.error(f"Request queue is full. Dropping message: {message.id}")
            return False

    def put_response(self, message: BridgeMessage) -> bool:
        """Add a response to the queue."""
        try:
            self.response_queue.put(message, timeout=1)
            with self._lock:
                if message.id in self._active_requests:
                    self.stats["total_responses"] += 1
                    response_time = time.time() - self._active_requests[message.id].timestamp
                    # Update average response time
                    prev_avg = self.stats["average_response_time"]
                    prev_count = self.stats["total_responses"] - 1
                    self.stats["average_response_time"] = (prev_avg * prev_count + response_time) / self.stats["total_responses"]
            return True
        except Full:
            logging.error(f"Response queue is full. Dropping message: {message.id}")
            return False

    def get_request(self, timeout: float = 0.1) -> Optional[BridgeMessage]:
        """Get the next request with timeout."""
        try:
            message = self.request_queue.get(timeout=timeout)
            with self._lock:
                if message.id in self._active_requests:
                    message.status = MessageStatus.PROCESSING
            return message
        except Empty:
            return None

    def get_response(self, timeout: float = 0.1) -> Optional[BridgeMessage]:
        """Get the next response with timeout."""
        try:
            message = self.response_queue.get(timeout=timeout)
            with self._lock:
                if message.id in self._active_requests:
                    self._active_requests[message.id].status = MessageStatus.COMPLETED
                    del self._active_requests[message.id]
            return message
        except Empty:
            return None

    def add_stream_chunk(self, message_id: str, chunk: str) -> None:
        """Add a streaming response chunk."""
        with self._lock:
            if message_id not in self._streaming_responses:
                self._streaming_responses[message_id] = []
            self._streaming_responses[message_id].append(chunk)

    def get_stream_chunks(self, message_id: str) -> List[str]:
        """Get all streaming chunks for a message."""
        with self._lock:
            return self._streaming_responses.get(message_id, [])

    def clear_stream_chunks(self, message_id: str) -> None:
        """Clear streaming chunks for a message."""
        with self._lock:
            if message_id in self._streaming_responses:
                del self._streaming_responses[message_id]

    def cleanup_expired_requests(self, timeout_seconds: int = Config.REQUEST_TIMEOUT_SECONDS):
        """Remove expired requests to prevent memory leaks."""
        current_time = time.time()
        with self._lock:
            expired_ids = []
            for message_id, message in self._active_requests.items():
                if current_time - message.timestamp > timeout_seconds:
                    message.status = MessageStatus.TIMEOUT
                    expired_ids.append(message_id)
                    self.stats["failed_requests"] += 1

            for message_id in expired_ids:
                del self._active_requests[message_id]
                if message_id in self._streaming_responses:
                    del self._streaming_responses[message_id]

        if expired_ids:
            logging.warning(f"Cleaned up {len(expired_ids)} expired requests")

    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health and statistics information."""
        with self._lock:
            uptime = time.time() - self.stats["uptime_start"]
            return {
                "status": "healthy",
                "uptime_seconds": round(uptime, 2),
                "uptime_formatted": str(timedelta(seconds=int(uptime))),
                "queue_sizes": {
                    "requests": self.request_queue.qsize(),
                    "responses": self.response_queue.qsize(),
                    "streams": len(self._streaming_responses)
                },
                "statistics": self.stats,
                "active_requests": len(self._active_requests)
            }

# ============================================================================
# Security & Validation
# ============================================================================

class SecurityManager:
    """Handles security and validation for the bridge server."""

    @staticmethod
    def validate_payload_size(payload: Any) -> bool:
        """Validate that payload size is within limits."""
        try:
            payload_str = json.dumps(payload) if not isinstance(payload, str) else payload
            return len(payload_str) <= Config.MAX_REQUEST_SIZE
        except:
            return False

    @staticmethod
    def sanitize_input(data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize and validate input data."""
        allowed_keys = {"id", "type", "payload", "timestamp", "metadata"}
        sanitized = {}

        for key, value in data.items():
            if key in allowed_keys:
                if key == "payload" and not SecurityManager.validate_payload_size(value):
                    raise ValueError(f"Payload size exceeds limit for key: {key}")
                sanitized[key] = value

        return sanitized

    @staticmethod
    def generate_request_id() -> str:
        """Generate a unique request ID."""
        return str(uuid.uuid4())

# ============================================================================
# Background Tasks
# ============================================================================

class BackgroundTaskManager:
    """Manages background tasks and cleanup operations."""

    def __init__(self, queue_manager: MessageQueueManager):
        self.queue_manager = queue_manager
        self._stop_event = Event()
        self._thread: Optional[Thread] = None
        self._cleanup_thread: Optional[Thread] = None

    def start(self):
        """Start background task threads."""
        self._thread = Thread(target=self._run, daemon=True, name="BackgroundTaskManager")
        self._cleanup_thread = Thread(target=self._cleanup_loop, daemon=True, name="CleanupLoop")
        self._thread.start()
        self._cleanup_thread.start()
        logging.info("Background tasks started")

    def stop(self):
        """Stop background task threads."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)
        logging.info("Background tasks stopped")

    def _run(self):
        """Main background task loop."""
        while not self._stop_event.is_set():
            # Perform any periodic tasks here
            time.sleep(1)

    def _cleanup_loop(self):
        """Periodically clean up expired requests."""
        while not self._stop_event.is_set():
            self.queue_manager.cleanup_expired_requests()
            time.sleep(Config.CLEANUP_INTERVAL_SECONDS)

# ============================================================================
# Flask Application Factory
# ============================================================================

def create_app(queue_manager: MessageQueueManager) -> Flask:
    """Application factory pattern for Flask app creation."""

    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": Config.ALLOWED_ORIGINS}})

    # Configure logging
    logging.basicConfig(
        level=Config.LOG_LEVEL,
        format=Config.LOG_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(Config.LOG_FILE)
        ]
    )
    logger = logging.getLogger(__name__)

    # ========================================================================
    # Error Handlers
    # ========================================================================

    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        """Handle HTTP exceptions with proper JSON responses."""
        response = {
            "status": "error",
            "code": error.code,
            "message": error.description,
            "timestamp": time.time()
        }
        logger.error(f"HTTP Error {error.code}: {error.description}")
        return jsonify(response), error.code

    @app.errorhandler(Exception)
    def handle_general_exception(error):
        """Handle general exceptions."""
        response = {
            "status": "error",
            "code": 500,
            "message": "Internal server error",
            "timestamp": time.time()
        }
        logger.exception(f"Unhandled exception: {str(error)}")
        return jsonify(response), 500

    # ========================================================================
    # Request Handlers
    # ========================================================================

    @app.route("/", methods=["GET"])
    def index():
        """Root endpoint for health check."""
        return jsonify({
            "name": "Bridge Server",
            "version": "1.0.0",
            "status": "running",
            "timestamp": time.time()
        })

    @app.route("/health", methods=["GET"])
    def health():
        """Comprehensive health check endpoint."""
        health_data = queue_manager.get_health_status()
        return jsonify({
            "status": "healthy",
            "timestamp": time.time(),
            "data": health_data
        })

    @app.route("/api/v1/request", methods=["POST"])
    def submit_request():
        """
        Submit a new request to the bridge.
        Expected JSON format:
        {
            "payload": "Your message here",
            "type": "text",
            "metadata": {}
        }
        """
        try:
            # Parse and validate input
            data = request.get_json()
            if not data:
                return jsonify({"status": "error", "message": "No JSON data provided"}), 400

            # Validate payload
            if "payload" not in data:
                return jsonify({"status": "error", "message": "Missing 'payload' field"}), 400

            # Create message
            message = BridgeMessage(
                id=SecurityManager.generate_request_id(),
                type=MessageType(data.get("type", "text")),
                payload=data["payload"],
                timestamp=time.time(),
                metadata=data.get("metadata", {})
            )

            # Add to queue
            if not queue_manager.put_request(message):
                return jsonify({"status": "error", "message": "Queue is full"}), 503

            logger.info(f"Request queued: {message.id}")
            return jsonify({
                "status": "queued",
                "request_id": message.id,
                "timestamp": time.time()
            }), 202

        except ValueError as e:
            return jsonify({"status": "error", "message": str(e)}), 400
        except Exception as e:
            logger.exception(f"Error submitting request: {str(e)}")
            return jsonify({"status": "error", "message": "Internal server error"}), 500

    @app.route("/api/v1/request", methods=["GET"])
    def get_pending_request():
        """
        Get the next pending request for the browser client.
        Returns empty if no requests are pending.
        """
        message = queue_manager.get_request(timeout=0.1)

        if message is None:
            return jsonify({
                "status": "empty",
                "timestamp": time.time()
            })

        logger.info(f"Request dispatched to browser: {message.id}")
        return jsonify({
            "status": "pending",
            "request": message.to_dict()
        })

    @app.route("/api/v1/response", methods=["POST"])
    def submit_response():
        """
        Submit a response from the browser client.
        Expected JSON format:
        {
            "request_id": "uuid",
            "response": "Response text",
            "type": "text"
        }
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({"status": "error", "message": "No JSON data provided"}), 400

            # Validate required fields
            if "request_id" not in data or "response" not in data:
                return jsonify({"status": "error", "message": "Missing required fields"}), 400

            # Create response message
            message = BridgeMessage(
                id=data["request_id"],
                type=MessageType(data.get("type", "text")),
                payload=data["response"],
                timestamp=time.time(),
                status=MessageStatus.COMPLETED
            )

            # Add to response queue
            if not queue_manager.put_response(message):
                return jsonify({"status": "error", "message": "Response queue is full"}), 503

            logger.info(f"Response received: {message.id}")
            return jsonify({
                "status": "accepted",
                "request_id": message.id,
                "timestamp": time.time()
            }), 200

        except Exception as e:
            logger.exception(f"Error submitting response: {str(e)}")
            return jsonify({"status": "error", "message": "Internal server error"}), 500

    @app.route("/api/v1/response", methods=["GET"])
    def get_response():
        """
        Get the next available response for the PyQt6 application.
        """
        message = queue_manager.get_response(timeout=0.1)

        if message is None:
            return jsonify({
                "status": "empty",
                "timestamp": time.time()
            })

        return jsonify({
            "status": "completed",
            "response": message.to_dict()
        })

    @app.route("/api/v1/stream/<request_id>", methods=["POST"])
    def submit_stream_chunk(request_id: str):
        """
        Submit a streaming response chunk for progressive rendering.
        """
        try:
            data = request.get_json()
            if not data or "chunk" not in data:
                return jsonify({"status": "error", "message": "Missing 'chunk' field"}), 400

            # Add stream chunk
            queue_manager.add_stream_chunk(request_id, data["chunk"])

            return jsonify({"status": "accepted"}), 200

        except Exception as e:
            logger.exception(f"Error submitting stream chunk: {str(e)}")
            return jsonify({"status": "error", "message": "Internal server error"}), 500

    @app.route("/api/v1/stream/<request_id>", methods=["GET"])
    def get_stream_chunks(request_id: str):
        """
        Get all stream chunks for a specific request.
        """
        chunks = queue_manager.get_stream_chunks(request_id)

        return jsonify({
            "status": "success",
            "request_id": request_id,
            "chunks": chunks,
            "timestamp": time.time()
        })

    @app.route("/api/v1/stream/<request_id>", methods=["DELETE"])
    def clear_stream_chunks(request_id: str):
        """
        Clear stream chunks for a specific request.
        """
        queue_manager.clear_stream_chunks(request_id)

        return jsonify({
            "status": "cleared",
            "request_id": request_id
        })

    @app.route("/api/v1/stats", methods=["GET"])
    def get_statistics():
        """
        Get detailed statistics about the bridge server.
        """
        return jsonify({
            "status": "success",
            "statistics": queue_manager.get_health_status()
        })

    return app

# ============================================================================
# Server Runner
# ============================================================================

class BridgeServer:
    """Main server class that manages the application lifecycle."""

    def __init__(self, host: str = Config.HOST, port: int = Config.PORT):
        self.host = host
        self.port = port
        self.queue_manager = MessageQueueManager()
        self.app = create_app(self.queue_manager)
        self.background_tasks = BackgroundTaskManager(self.queue_manager)
        self._server_thread: Optional[Thread] = None
        self._is_running = False

    def start(self):
        """Start the server and background tasks."""
        if self._is_running:
            logging.warning("Server is already running")
            return

        # Start background tasks
        self.background_tasks.start()

        # Start server in a separate thread
        self._server_thread = Thread(
            target=self._run_server,
            daemon=True,
            name="BridgeServer"
        )
        self._server_thread.start()
        self._is_running = True

        logging.info(f"Bridge server started on http://{self.host}:{self.port}")
        logging.info("Press Ctrl+C to stop the server")

    def _run_server(self):
        """Run the Flask server."""
        try:
            self.app.run(
                host=self.host,
                port=self.port,
                debug=Config.DEBUG_MODE,
                threaded=Config.THREADED,
                use_reloader=False  # Disable reloader for production
            )
        except Exception as e:
            logging.error(f"Server error: {e}")
            self._is_running = False

    def stop(self):
        """Stop the server and clean up resources."""
        if not self._is_running:
            logging.warning("Server is not running")
            return

        logging.info("Shutting down bridge server...")
        self.background_tasks.stop()
        self._is_running = False

        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=5)

        logging.info("Bridge server stopped")

    def run(self):
        """Run the server in the main thread (blocking)."""
        self.start()

        # Handle graceful shutdown
        def signal_handler(signum, frame):
            logging.info("Received shutdown signal")
            self.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Keep the main thread alive
        try:
            while self._is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point for the bridge server."""
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Bridge Server for PyQt6-Browser Communication")
    parser.add_argument(
        "--host",
        default=Config.HOST,
        help=f"Host address (default: {Config.HOST})"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=Config.PORT,
        help=f"Port number (default: {Config.PORT})"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )

    args = parser.parse_args()

    # Update configuration
    if args.debug:
        Config.DEBUG_MODE = True
        Config.LOG_LEVEL = logging.DEBUG

    # Create and run server
    server = BridgeServer(host=args.host, port=args.port)

    try:
        server.run()
    except Exception as e:
        logging.exception(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
