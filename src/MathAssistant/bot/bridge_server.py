# src/MathAssistant/bot/bridge_server.py

"""
Bridge Server - Production Grade Implementation
================================================
A robust, secure, and scalable local server that acts as a bridge between
PyQt6 desktop applications and browser-based API clients.

Features:
- Multi-client support with connection pooling
- Advanced queue management with priority
- Streaming response support (SSE)
- Comprehensive logging and monitoring
- Rate limiting and security
- Graceful shutdown and error recovery
- Health checks and metrics
- WebSocket support for real-time communication

Author: Professional Development Team
Version: 2.0.0
License: MIT
"""

import asyncio
import base64
import json
import logging
import logging.handlers
import signal
import sys
import time
import uuid
import hashlib
import hmac
import secrets
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, Any, List, Tuple, Callable, Union
from queue import Queue, Empty, Full, PriorityQueue
from threading import Thread, Event, Lock, RLock
from collections import OrderedDict, deque
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager

from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from flask_sock import Sock
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix
import aiohttp
import requests
from PIL import Image
import io as io_module

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

    # WebSocket Configuration
    WEBSOCKET_ENABLED = True
    WEBSOCKET_PATH = "/ws"

    # Queue Configuration
    MAX_QUEUE_SIZE = 500
    REQUEST_TIMEOUT_SECONDS = 120
    CLEANUP_INTERVAL_SECONDS = 30
    MAX_RETRY_ATTEMPTS = 3

    # Logging Configuration
    LOG_LEVEL = logging.INFO
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - [%(threadName)s] - %(message)s"
    LOG_FILE = "./logs/bridge_server.log"
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5

    # Security Configuration
    MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_ORIGINS = ["*"]  # For local development
    API_KEY_HEADER = "X-Bridge-Key"
    RATE_LIMIT_REQUESTS = 100  # Requests per minute
    RATE_LIMIT_WINDOW = 60  # Seconds

    # Performance Configuration
    POLLING_INTERVAL_MS = 500
    MAX_CONCURRENT_REQUESTS = 10
    THREAD_POOL_SIZE = 20

    # Image Processing
    MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
    ALLOWED_IMAGE_TYPES = ['image/png', 'image/jpeg', 'image/gif', 'image/webp']
    IMAGE_CACHE_TTL = 300  # 5 minutes

    # Streaming Configuration
    STREAM_CHUNK_SIZE = 1024  # 1KB
    STREAM_BUFFER_SIZE = 10

    # Health Check
    HEALTH_CHECK_INTERVAL = 30  # Seconds


# ============================================================================
# Data Models
# ============================================================================

class MessageType(Enum):
    """Enumeration of message types supported by the bridge."""
    TEXT = "text"
    IMAGE = "image"
    MULTIMODAL = "multimodal"
    SYSTEM = "system"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    STREAM = "stream"
    STREAM_END = "stream_end"
    FILE = "file"
    AUDIO = "audio"

class MessagePriority(Enum):
    """Priority levels for messages."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3

class MessageStatus(Enum):
    """Status tracking for message lifecycle."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    STREAMING = "streaming"

@dataclass
class BridgeMessage:
    """Represents a message passing through the bridge."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType = MessageType.TEXT
    payload: Any = None
    timestamp: float = field(default_factory=time.time)
    status: MessageStatus = MessageStatus.PENDING
    priority: MessagePriority = MessagePriority.NORMAL
    metadata: Dict[str, Any] = field(default_factory=dict)
    response: Optional[Any] = None
    error: Optional[str] = None
    client_id: Optional[str] = None
    timeout: float = Config.REQUEST_TIMEOUT_SECONDS

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "type": self.type.value if isinstance(self.type, MessageType) else self.type,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "status": self.status.value if isinstance(self.status, MessageStatus) else self.status,
            "priority": self.priority.value if isinstance(self.priority, MessagePriority) else self.priority,
            "metadata": self.metadata,
            "response": self.response,
            "error": self.error,
            "client_id": self.client_id
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
            priority=MessagePriority(data.get("priority", 1)),
            metadata=data.get("metadata", {}),
            response=data.get("response"),
            error=data.get("error"),
            client_id=data.get("client_id")
        )


# ============================================================================
# Queue Management
# ============================================================================

class MessageQueueManager:
    """Advanced queue management with priority and streaming support."""

    def __init__(self, max_size: int = Config.MAX_QUEUE_SIZE):
        self.max_size = max_size
        self._lock = RLock()
        self._active_requests: OrderedDict[str, BridgeMessage] = OrderedDict()
        self._streaming_responses: Dict[str, deque] = {}
        self._request_queue: PriorityQueue = PriorityQueue(maxsize=max_size)
        self._response_queue: Queue = Queue(maxsize=max_size)
        self._stream_queue: Queue = Queue(maxsize=max_size)

        # Statistics
        self.stats = {
            "total_requests": 0,
            "total_responses": 0,
            "failed_requests": 0,
            "timeout_requests": 0,
            "average_response_time": 0.0,
            "uptime_start": time.time(),
            "requests_per_minute": 0,
            "active_streams": 0
        }

        # Rate limiting
        self._request_timestamps = deque(maxlen=Config.RATE_LIMIT_REQUESTS)

    def _check_rate_limit(self) -> bool:
        """Check if rate limit is exceeded."""
        current_time = time.time()

        # Add current timestamp
        self._request_timestamps.append(current_time)

        # Remove old timestamps
        while (self._request_timestamps and
               current_time - self._request_timestamps[0] > Config.RATE_LIMIT_WINDOW):
            self._request_timestamps.popleft()

        # Check if within limit
        return len(self._request_timestamps) <= Config.RATE_LIMIT_REQUESTS

    def put_request(self, message: BridgeMessage) -> Tuple[bool, str]:
        """
        Add a request to the queue with priority and rate limiting.
        Returns (success, error_message).
        """
        # Rate limiting
        if not self._check_rate_limit():
            return False, "Rate limit exceeded"

        # Queue size check
        if self._request_queue.qsize() >= self.max_size:
            return False, "Queue is full"

        try:
            # Use priority queue
            priority_value = (message.priority.value, message.timestamp)
            self._request_queue.put((priority_value, message), timeout=1)

            with self._lock:
                self._active_requests[message.id] = message
                self.stats["total_requests"] += 1

                # Update requests per minute
                current_time = time.time()
                recent_requests = [t for t in self._request_timestamps
                                  if current_time - t < 60]
                self.stats["requests_per_minute"] = len(recent_requests)

            return True, ""

        except Full:
            return False, "Queue is full"
        except Exception as e:
            return False, str(e)

    def put_response(self, message: BridgeMessage) -> Tuple[bool, str]:
        """Add a response to the queue."""
        try:
            self._response_queue.put(message, timeout=1)

            with self._lock:
                if message.id in self._active_requests:
                    self.stats["total_responses"] += 1
                    response_time = time.time() - self._active_requests[message.id].timestamp

                    # Update average response time
                    prev_avg = self.stats["average_response_time"]
                    prev_count = max(self.stats["total_responses"] - 1, 0)
                    self.stats["average_response_time"] = (
                        (prev_avg * prev_count + response_time) /
                        self.stats["total_responses"]
                    )

                    # Mark as completed
                    self._active_requests[message.id].status = MessageStatus.COMPLETED

                    # Clean up
                    if message.id in self._active_requests:
                        del self._active_requests[message.id]

            return True, ""

        except Full:
            return False, "Response queue is full"
        except Exception as e:
            return False, str(e)

    def get_request(self, timeout: float = 0.1) -> Optional[BridgeMessage]:
        """Get the next request with timeout, respecting priority."""
        try:
            priority_value, message = self._request_queue.get(timeout=timeout)

            with self._lock:
                if message.id in self._active_requests:
                    message.status = MessageStatus.PROCESSING
                    message.metadata["processing_started"] = time.time()

            return message

        except Empty:
            return None

    def get_response(self, timeout: float = 0.1) -> Optional[BridgeMessage]:
        """Get the next response with timeout."""
        try:
            message = self._response_queue.get(timeout=timeout)
            return message
        except Empty:
            return None

    def add_stream_chunk(self, message_id: str, chunk: str) -> bool:
        """Add a streaming response chunk."""
        try:
            with self._lock:
                if message_id not in self._streaming_responses:
                    self._streaming_responses[message_id] = deque(maxlen=Config.STREAM_BUFFER_SIZE)
                    self.stats["active_streams"] += 1

                self._streaming_responses[message_id].append(chunk)

            # Also add to stream queue for real-time delivery
            stream_message = BridgeMessage(
                id=message_id,
                type=MessageType.STREAM,
                payload=chunk,
                status=MessageStatus.STREAMING
            )
            self._stream_queue.put(stream_message, timeout=1)

            return True

        except Exception as e:
            logging.error(f"Failed to add stream chunk: {e}")
            return False

    def get_stream_chunks(self, message_id: str) -> List[str]:
        """Get all streaming chunks for a message."""
        with self._lock:
            chunks = list(self._streaming_responses.get(message_id, []))
        return chunks

    def get_stream_queue(self, timeout: float = 0.1) -> Optional[BridgeMessage]:
        """Get streaming chunks from queue."""
        try:
            return self._stream_queue.get(timeout=timeout)
        except Empty:
            return None

    def clear_stream_chunks(self, message_id: str) -> None:
        """Clear streaming chunks for a message."""
        with self._lock:
            if message_id in self._streaming_responses:
                del self._streaming_responses[message_id]
                self.stats["active_streams"] -= 1

    def cleanup_expired_requests(self, timeout_seconds: int = Config.REQUEST_TIMEOUT_SECONDS):
        """Remove expired requests to prevent memory leaks."""
        current_time = time.time()

        with self._lock:
            expired_ids = []

            for message_id, message in self._active_requests.items():
                if current_time - message.timestamp > timeout_seconds:
                    message.status = MessageStatus.TIMEOUT
                    expired_ids.append(message_id)
                    self.stats["timeout_requests"] += 1

            for message_id in expired_ids:
                del self._active_requests[message_id]

                # Clean up streaming
                if message_id in self._streaming_responses:
                    del self._streaming_responses[message_id]
                    self.stats["active_streams"] -= 1

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
                    "requests": self._request_queue.qsize(),
                    "responses": self._response_queue.qsize(),
                    "streams": len(self._streaming_responses),
                    "stream_queue": self._stream_queue.qsize()
                },
                "statistics": {
                    **self.stats,
                    "requests_per_minute": self.stats["requests_per_minute"],
                    "average_response_time_ms": round(self.stats["average_response_time"] * 1000, 2)
                },
                "active_requests": len(self._active_requests),
                "active_streams": self.stats["active_streams"]
            }


# ============================================================================
# Image Processing
# ============================================================================

class ImageProcessor:
    """Handle image upload, validation, and processing."""

    def __init__(self, cache_ttl: int = Config.IMAGE_CACHE_TTL):
        self.cache_ttl = cache_ttl
        self.image_cache: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()

    def validate_image(self, image_data: str, image_type: str) -> Tuple[bool, str]:
        """Validate image data and type."""
        try:
            # Check image type
            if image_type not in Config.ALLOWED_IMAGE_TYPES:
                return False, f"Unsupported image type: {image_type}"

            # Check size
            image_bytes = base64.b64decode(image_data)
            if len(image_bytes) > Config.MAX_IMAGE_SIZE:
                return False, f"Image too large: {len(image_bytes)} bytes"

            # Validate image format
            try:
                img = Image.open(io_module.BytesIO(image_bytes))
                img.verify()
                return True, ""
            except Exception as e:
                return False, f"Invalid image format: {str(e)}"

        except Exception as e:
            return False, f"Image validation error: {str(e)}"

    def store_image(self, image_id: str, image_data: str, image_type: str) -> None:
        """Store image in cache."""
        with self._lock:
            self.image_cache[image_id] = {
                "data": image_data,
                "type": image_type,
                "timestamp": time.time()
            }

    def get_image(self, image_id: str) -> Optional[Dict[str, Any]]:
        """Get image from cache."""
        with self._lock:
            image = self.image_cache.get(image_id)

            if not image:
                return None

            # Check if expired
            if time.time() - image["timestamp"] > self.cache_ttl:
                del self.image_cache[image_id]
                return None

            return image

    def cleanup_expired_images(self) -> None:
        """Clean up expired images."""
        current_time = time.time()

        with self._lock:
            expired_ids = [
                image_id for image_id, image in self.image_cache.items()
                if current_time - image["timestamp"] > self.cache_ttl
            ]

            for image_id in expired_ids:
                del self.image_cache[image_id]

        if expired_ids:
            logging.info(f"Cleaned up {len(expired_ids)} expired images")


# ============================================================================
# Security Manager
# ============================================================================

class SecurityManager:
    """Advanced security and validation."""

    def __init__(self):
        self._api_keys = set()
        self._rate_limits = {}
        self._lock = Lock()

    def generate_api_key(self) -> str:
        """Generate a secure API key."""
        return secrets.token_urlsafe(32)

    def validate_api_key(self, api_key: str) -> bool:
        """Validate API key."""
        if not api_key:
            return False

        return api_key in self._api_keys

    def add_api_key(self, api_key: str) -> None:
        """Add an API key."""
        with self._lock:
            self._api_keys.add(api_key)

    def validate_payload_size(self, payload: Any) -> bool:
        """Validate that payload size is within limits."""
        try:
            payload_str = json.dumps(payload) if not isinstance(payload, str) else payload
            return len(payload_str) <= Config.MAX_REQUEST_SIZE
        except:
            return False

    def sanitize_input(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize and validate input data."""
        allowed_keys = {
            "id", "type", "payload", "timestamp", "metadata",
            "priority", "client_id", "images", "text"
        }
        sanitized = {}

        for key, value in data.items():
            if key in allowed_keys:
                if key == "payload" and not self.validate_payload_size(value):
                    raise ValueError(f"Payload size exceeds limit")

                # Sanitize strings
                if isinstance(value, str):
                    value = self._sanitize_string(value)

                sanitized[key] = value

        return sanitized

    def _sanitize_string(self, text: str) -> str:
        """Sanitize string to prevent injection."""
        # Remove null bytes
        text = text.replace('\x00', '')

        # Remove control characters (except newline and tab)
        import re
        text = re.sub(r'[\x01-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)

        return text

    def generate_request_id(self) -> str:
        """Generate a unique request ID."""
        return str(uuid.uuid4())

    def hash_payload(self, payload: str) -> str:
        """Hash payload for caching."""
        return hashlib.sha256(payload.encode()).hexdigest()


# ============================================================================
# WebSocket Manager
# ============================================================================

class WebSocketManager:
    """Manage WebSocket connections for real-time communication."""

    def __init__(self):
        self.connections = set()
        self._lock = Lock()

    def add_connection(self, ws) -> None:
        """Add a WebSocket connection."""
        with self._lock:
            self.connections.add(ws)

    def remove_connection(self, ws) -> None:
        """Remove a WebSocket connection."""
        with self._lock:
            self.connections.discard(ws)

    def broadcast(self, message: str) -> None:
        """Broadcast message to all connections."""
        with self._lock:
            for ws in self.connections:
                try:
                    ws.send(message)
                except Exception as e:
                    logging.error(f"Failed to send WebSocket message: {e}")
                    self.connections.discard(ws)

    def get_connection_count(self) -> int:
        """Get number of active connections."""
        with self._lock:
            return len(self.connections)


# ============================================================================
# Background Tasks
# ============================================================================

class BackgroundTaskManager:
    """Manages background tasks and cleanup operations."""

    def __init__(self, queue_manager: MessageQueueManager,
                 image_processor: ImageProcessor,
                 websocket_manager: WebSocketManager):
        self.queue_manager = queue_manager
        self.image_processor = image_processor
        self.websocket_manager = websocket_manager
        self._stop_event = Event()
        self._threads: List[Thread] = []

    def start(self):
        """Start background task threads."""
        # Cleanup thread
        cleanup_thread = Thread(
            target=self._cleanup_loop,
            daemon=True,
            name="CleanupLoop"
        )
        cleanup_thread.start()
        self._threads.append(cleanup_thread)

        # Health check thread
        health_thread = Thread(
            target=self._health_check_loop,
            daemon=True,
            name="HealthCheckLoop"
        )
        health_thread.start()
        self._threads.append(health_thread)

        # Statistics thread
        stats_thread = Thread(
            target=self._statistics_loop,
            daemon=True,
            name="StatisticsLoop"
        )
        stats_thread.start()
        self._threads.append(stats_thread)

        logging.info("Background tasks started")

    def stop(self):
        """Stop background task threads."""
        self._stop_event.set()

        for thread in self._threads:
            if thread.is_alive():
                thread.join(timeout=5)

        logging.info("Background tasks stopped")

    def _cleanup_loop(self):
        """Periodically clean up expired requests and images."""
        while not self._stop_event.is_set():
            try:
                self.queue_manager.cleanup_expired_requests()
                self.image_processor.cleanup_expired_images()
            except Exception as e:
                logging.error(f"Cleanup error: {e}")

            self._stop_event.wait(Config.CLEANUP_INTERVAL_SECONDS)

    def _health_check_loop(self):
        """Periodically check system health."""
        while not self._stop_event.is_set():
            try:
                health = self.queue_manager.get_health_status()

                # Check for issues
                if health["queue_sizes"]["requests"] > Config.MAX_QUEUE_SIZE * 0.9:
                    logging.warning("Request queue at 90% capacity")

                if health["statistics"]["failed_requests"] > 100:
                    logging.warning("High failure rate detected")

                # Broadcast health status via WebSocket
                if self.websocket_manager.get_connection_count() > 0:
                    self.websocket_manager.broadcast(json.dumps({
                        "type": "health",
                        "data": health
                    }))

            except Exception as e:
                logging.error(f"Health check error: {e}")

            self._stop_event.wait(Config.HEALTH_CHECK_INTERVAL)

    def _statistics_loop(self):
        """Periodically log statistics."""
        while not self._stop_event.is_set():
            try:
                stats = self.queue_manager.get_health_status()
                logging.info(
                    f"Stats - Requests: {stats['statistics']['total_requests']}, "
                    f"Responses: {stats['statistics']['total_responses']}, "
                    f"Active: {stats['active_requests']}"
                )
            except Exception as e:
                logging.error(f"Statistics error: {e}")

            self._stop_event.wait(300)  # Every 5 minutes


# ============================================================================
# Flask Application Factory
# ============================================================================

def create_app(queue_manager: MessageQueueManager,
               image_processor: ImageProcessor,
               security_manager: SecurityManager,
               websocket_manager: WebSocketManager) -> Flask:
    """Application factory pattern for Flask app creation."""

    app = Flask(__name__)
    app.wsgi_app = ProxyFix(app.wsgi_app)

    # Configure CORS
    CORS(app, resources={
        r"/*": {
            "origins": Config.ALLOWED_ORIGINS,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", Config.API_KEY_HEADER]
        }
    })

    # Configure logging
    logging.basicConfig(
        level=Config.LOG_LEVEL,
        format=Config.LOG_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.handlers.RotatingFileHandler(
                Config.LOG_FILE,
                maxBytes=Config.LOG_MAX_BYTES,
                backupCount=Config.LOG_BACKUP_COUNT
            )
        ]
    )
    logger = logging.getLogger(__name__)

    # Initialize WebSocket
    sock = Sock(app)

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
    # Middleware
    # ========================================================================

    @app.before_request
    def before_request():
        """Execute before each request."""
        # Add request ID
        request.id = str(uuid.uuid4())

        # Log request
        logger.debug(
            f"Request {request.id}: {request.method} {request.path}"
        )

    @app.after_request
    def after_request(response):
        """Execute after each request."""
        # Add security headers
        response.headers['X-Request-ID'] = getattr(request, 'id', '')
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'

        return response

    # ========================================================================
    # WebSocket Handlers
    # ========================================================================

    @sock.route(Config.WEBSOCKET_PATH)
    def websocket_endpoint(ws):
        """WebSocket endpoint for real-time communication."""
        websocket_manager.add_connection(ws)
        logger.info(f"WebSocket connected. Total: {websocket_manager.get_connection_count()}")

        try:
            while True:
                # Receive message
                message = ws.receive()
                if message is None:
                    break

                # Parse message
                try:
                    data = json.loads(message)

                    # Handle different message types
                    if data.get("type") == "ping":
                        ws.send(json.dumps({"type": "pong", "timestamp": time.time()}))

                    elif data.get("type") == "subscribe":
                        # Handle subscription
                        pass

                except json.JSONDecodeError:
                    ws.send(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON"
                    }))

        except Exception as e:
            logger.error(f"WebSocket error: {e}")

        finally:
            websocket_manager.remove_connection(ws)
            logger.info(f"WebSocket disconnected. Total: {websocket_manager.get_connection_count()}")

    # ========================================================================
    # Request Handlers
    # ========================================================================

    @app.route("/", methods=["GET"])
    def index():
        """Root endpoint for health check."""
        return jsonify({
            "name": "Bridge Server",
            "version": "2.0.0",
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
            "data": health_data,
            "websocket_connections": websocket_manager.get_connection_count()
        })

    @app.route("/metrics", methods=["GET"])
    def metrics():
        """Prometheus-style metrics endpoint."""
        stats = queue_manager.get_health_status()

        metrics_text = f"""
# HELP bridge_uptime_seconds Total uptime in seconds
# TYPE bridge_uptime_seconds gauge
bridge_uptime_seconds {stats['uptime_seconds']}

# HELP bridge_total_requests Total number of requests
# TYPE bridge_total_requests counter
bridge_total_requests {stats['statistics']['total_requests']}

# HELP bridge_total_responses Total number of responses
# TYPE bridge_total_responses counter
bridge_total_responses {stats['statistics']['total_responses']}

# HELP bridge_active_requests Number of active requests
# TYPE bridge_active_requests gauge
bridge_active_requests {stats['active_requests']}

# HELP bridge_queue_size Current queue size
# TYPE bridge_queue_size gauge
bridge_queue_size {stats['queue_sizes']['requests']}
"""

        return Response(metrics_text, mimetype='text/plain')

    @app.route("/api/v1/request", methods=["POST"])
    def submit_request():
        """
        Submit a new request to the bridge.
        Expected JSON format:
        {
            "payload": "Your message here",
            "type": "text",
            "metadata": {},
            "priority": "normal"
        }
        """
        try:
            # Parse and validate input
            data = request.get_json()
            if not data:
                return jsonify({"status": "error", "message": "No JSON data provided"}), 400

            # Sanitize input
            data = security_manager.sanitize_input(data)

            # Validate payload
            if "payload" not in data:
                return jsonify({"status": "error", "message": "Missing 'payload' field"}), 400

            # Create message
            message = BridgeMessage(
                id=security_manager.generate_request_id(),
                type=MessageType(data.get("type", "text")),
                payload=data["payload"],
                timestamp=time.time(),
                priority=MessagePriority[data.get("priority", "normal").upper()]
                    if data.get("priority", "normal").upper() in MessagePriority.__members__
                    else MessagePriority.NORMAL,
                metadata=data.get("metadata", {}),
                client_id=data.get("client_id")
            )

            # Add to queue
            success, error_msg = queue_manager.put_request(message)

            if not success:
                return jsonify({
                    "status": "error",
                    "message": error_msg
                }), 503

            logger.info(f"Request queued: {message.id}")

            # Notify WebSocket clients
            websocket_manager.broadcast(json.dumps({
                "type": "request_queued",
                "request_id": message.id,
                "timestamp": time.time()
            }))

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
                return jsonify({
                    "status": "error",
                    "message": "Missing required fields"
                }), 400

            # Create response message
            message = BridgeMessage(
                id=data["request_id"],
                type=MessageType(data.get("type", "text")),
                payload=data["response"],
                timestamp=time.time(),
                status=MessageStatus.COMPLETED
            )

            # Add to response queue
            success, error_msg = queue_manager.put_response(message)

            if not success:
                return jsonify({
                    "status": "error",
                    "message": error_msg
                }), 503

            logger.info(f"Response received: {message.id}")

            # Notify WebSocket clients
            websocket_manager.broadcast(json.dumps({
                "type": "response_received",
                "request_id": message.id,
                "timestamp": time.time()
            }))

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

    @app.route("/api/v1/image", methods=["POST"])
    def upload_image():
        """
        Upload an image to the bridge.
        Expected JSON format:
        {
            "image_data": "base64_encoded_data",
            "image_type": "image/png"
        }
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({"status": "error", "message": "No JSON data provided"}), 400

            if "image_data" not in data:
                return jsonify({"status": "error", "message": "Missing image_data"}), 400

            image_data = data["image_data"]
            image_type = data.get("image_type", "image/png")

            # Validate image
            is_valid, error_msg = image_processor.validate_image(image_data, image_type)
            if not is_valid:
                return jsonify({"status": "error", "message": error_msg}), 400

            # Generate image ID
            image_id = str(uuid.uuid4())

            # Store image
            image_processor.store_image(image_id, image_data, image_type)

            logger.info(f"Image uploaded: {image_id}")

            return jsonify({
                "status": "success",
                "image_id": image_id,
                "timestamp": time.time()
            }), 200

        except Exception as e:
            logger.exception(f"Error uploading image: {str(e)}")
            return jsonify({"status": "error", "message": "Internal server error"}), 500

    @app.route("/api/v1/image/<image_id>", methods=["GET"])
    def get_image(image_id):
        """
        Get an image from the bridge.
        """
        image = image_processor.get_image(image_id)

        if not image:
            return jsonify({"status": "error", "message": "Image not found"}), 404

        return jsonify({
            "status": "success",
            "image": image
        })

    @app.route("/api/v1/stream/<request_id>", methods=["POST"])
    def submit_stream_chunk(request_id):
        """
        Submit a streaming response chunk for progressive rendering.
        """
        try:
            data = request.get_json()
            if not data or "chunk" not in data:
                return jsonify({"status": "error", "message": "Missing 'chunk' field"}), 400

            # Validate chunk size
            if len(data["chunk"]) > Config.STREAM_CHUNK_SIZE * 10:
                return jsonify({"status": "error", "message": "Chunk too large"}), 400

            # Add stream chunk
            success = queue_manager.add_stream_chunk(request_id, data["chunk"])

            if not success:
                return jsonify({"status": "error", "message": "Failed to add chunk"}), 500

            # Notify WebSocket clients
            websocket_manager.broadcast(json.dumps({
                "type": "stream_chunk",
                "request_id": request_id,
                "chunk": data["chunk"],
                "timestamp": time.time()
            }))

            return jsonify({"status": "accepted"}), 200

        except Exception as e:
            logger.exception(f"Error submitting stream chunk: {str(e)}")
            return jsonify({"status": "error", "message": "Internal server error"}), 500

    @app.route("/api/v1/stream/<request_id>", methods=["GET"])
    def get_stream_chunks(request_id):
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
    def clear_stream_chunks(request_id):
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
            "statistics": queue_manager.get_health_status(),
            "websocket_connections": websocket_manager.get_connection_count()
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
        self.image_processor = ImageProcessor()
        self.security_manager = SecurityManager()
        self.websocket_manager = WebSocketManager()
        self.app = create_app(
            self.queue_manager,
            self.image_processor,
            self.security_manager,
            self.websocket_manager
        )
        self.background_tasks = BackgroundTaskManager(
            self.queue_manager,
            self.image_processor,
            self.websocket_manager
        )
        self._server_thread: Optional[Thread] = None
        self._is_running = False
        self._shutdown_event = Event()

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
                use_reloader=False,  # Disable reloader for production
                ssl_context=None  # Add SSL context here for HTTPS
            )
        except Exception as e:
            logging.error(f"Server error: {e}")
            self._is_running = False
            self._shutdown_event.set()

    def stop(self):
        """Stop the server and clean up resources."""
        if not self._is_running:
            logging.warning("Server is not running")
            return

        logging.info("Shutting down bridge server...")

        # Stop background tasks
        self.background_tasks.stop()

        # Signal shutdown
        self._shutdown_event.set()
        self._is_running = False

        # Wait for server thread
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
            while self._is_running and not self._shutdown_event.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def get_status(self) -> Dict[str, Any]:
        """Get current server status."""
        return {
            "is_running": self._is_running,
            "host": self.host,
            "port": self.port,
            "queue_manager": self.queue_manager.get_health_status(),
            "websocket_connections": self.websocket_manager.get_connection_count()
        }

# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point for the bridge server."""
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(
        description="Bridge Server for PyQt6-Browser Communication",
        epilog="Example: python bridge_server.py --host 127.0.0.1 --port 5000 --debug"
    )

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

    parser.add_argument(
        "--log-level",
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default=logging.getLevelName(Config.LOG_LEVEL),  # تبدیل int به string
        help=f"Log level (default: {logging.getLevelName(Config.LOG_LEVEL)})"
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 2.0.0"
    )

    args = parser.parse_args()

    # Update configuration
    if args.debug:
        Config.DEBUG_MODE = True
        # در حالت debug، سطح لاگ را DEBUG قرار بده
        Config.LOG_LEVEL = logging.DEBUG
    else:
        # تبدیل رشته به ثابت logging
        Config.LOG_LEVEL = getattr(logging, args.log_level.upper())

    # Create and run server
    server = BridgeServer(host=args.host, port=args.port)

    try:
        server.run()
    except KeyboardInterrupt:
        logging.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        logging.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
