# src/MathAssistant/bot/bridge_client.py

"""
Bridge Client - Production Grade Implementation
================================================
A robust, secure, and feature-rich client for communicating with the Bridge Server.
Supports text, multimodal, streaming, and advanced error handling.

Features:
- Async and sync communication modes
- Automatic retry with exponential backoff
- Connection pooling and reuse
- Streaming response support
- Image upload and processing
- Comprehensive error handling
- Health monitoring
- Rate limiting awareness
- Thread-safe operations

Author: Professional Development Team
Version: 2.0.0
License: MIT
"""

import asyncio
import base64
import json
import logging
import random
import time
import uuid
import hashlib
import threading
from typing import Optional, Dict, Any, List, Callable, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from functools import wraps

import requests
import aiohttp
from requests.exceptions import RequestException, Timeout, ConnectionError
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ============================================================================
# Configuration & Constants
# ============================================================================

class ClientConfig:
    """Configuration for Bridge Client."""

    # Connection Settings
    DEFAULT_BASE_URL = "http://127.0.0.1:5000"
    CONNECT_TIMEOUT = 5  # seconds
    READ_TIMEOUT = 30  # seconds
    WRITE_TIMEOUT = 10  # seconds
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds
    MAX_RETRY_DELAY = 30  # seconds

    # Pool Settings
    POOL_CONNECTIONS = 10
    POOL_MAXSIZE = 20
    POOL_BLOCK = False

    # Polling Settings
    POLL_INTERVAL = 0.5  # seconds
    MAX_POLL_TIME = 120  # seconds

    # Streaming Settings
    STREAM_CHUNK_SIZE = 1024  # bytes
    STREAM_BUFFER_SIZE = 100

    # Image Settings
    MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
    SUPPORTED_IMAGE_TYPES = ['image/png', 'image/jpeg', 'image/gif', 'image/webp']

    # Logging
    LOG_LEVEL = logging.INFO
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


# ============================================================================
# Data Models
# ============================================================================

class RequestType(Enum):
    """Types of requests."""
    TEXT = "text"
    IMAGE = "image"
    MULTIMODAL = "multimodal"
    FILE = "file"
    AUDIO = "audio"
    SYSTEM = "system"

class ResponseStatus(Enum):
    """Status of responses."""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    STREAMING = "streaming"

@dataclass
class BridgeResponse:
    """Represents a response from the bridge."""
    request_id: str
    payload: Any
    status: ResponseStatus
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "payload": self.payload,
            "status": self.status.value,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "error": self.error
        }

@dataclass
class StreamChunk:
    """Represents a streaming chunk."""
    request_id: str
    chunk: str
    sequence: int
    timestamp: float = field(default_factory=time.time)
    is_final: bool = False

# ============================================================================
# Retry Handler
# ============================================================================

class RetryHandler:
    """Advanced retry handling with exponential backoff."""

    def __init__(self, max_retries: int = ClientConfig.MAX_RETRIES,
                 base_delay: float = ClientConfig.RETRY_DELAY,
                 max_delay: float = ClientConfig.MAX_RETRY_DELAY):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff."""
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        # Add jitter to prevent thundering herd
        jitter = random.uniform(0, 0.1 * delay)
        return delay + jitter

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if retry should be attempted."""
        if attempt >= self.max_retries:
            return False

        # Retry on connection errors and timeouts
        if isinstance(exception, (ConnectionError, Timeout)):
            return True

        # Retry on 5xx errors
        if isinstance(exception, RequestException):
            response = getattr(exception, 'response', None)
            if response and 500 <= response.status_code < 600:
                return True

        return False


# ============================================================================
# Connection Pool
# ============================================================================

class ConnectionPool:
    """Manage connection pooling for HTTP requests."""

    def __init__(self, pool_connections: int = ClientConfig.POOL_CONNECTIONS,
                 pool_maxsize: int = ClientConfig.POOL_MAXSIZE,
                 pool_block: bool = ClientConfig.POOL_BLOCK):
        self.pool_connections = pool_connections
        self.pool_maxsize = pool_maxsize
        self.pool_block = pool_block
        self._session = None
        self._lock = threading.Lock()

    def get_session(self) -> requests.Session:
        """Get or create a session with connection pooling."""
        with self._lock:
            if self._session is None:
                self._session = self._create_session()
            return self._session

    def _create_session(self) -> requests.Session:
        """Create a session with retry and pooling."""
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=ClientConfig.MAX_RETRIES,
            backoff_factor=ClientConfig.RETRY_DELAY,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE"]
        )

        # Configure adapter with pooling
        adapter = HTTPAdapter(
            pool_connections=self.pool_connections,
            pool_maxsize=self.pool_maxsize,
            pool_block=self.pool_block,
            max_retries=retry_strategy
        )

        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def close(self):
        """Close the session and release resources."""
        with self._lock:
            if self._session:
                self._session.close()
                self._session = None


# ============================================================================
# Main Bridge Client
# ============================================================================

class BridgeClient:
    """
    Professional client for communicating with the Bridge Server.
    Supports sync, async, streaming, and multimodal operations.
    """

    def __init__(self, base_url: str = ClientConfig.DEFAULT_BASE_URL,
                 api_key: Optional[str] = None,
                 connect_timeout: int = ClientConfig.CONNECT_TIMEOUT,
                 read_timeout: int = ClientConfig.READ_TIMEOUT):
        """
        Initialize the Bridge Client.

        Args:
            base_url: Base URL of the bridge server
            api_key: Optional API key for authentication
            connect_timeout: Connection timeout in seconds
            read_timeout: Read timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout

        # Initialize components
        self.connection_pool = ConnectionPool()
        self.retry_handler = RetryHandler()
        self._lock = threading.RLock()

        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_retries": 0,
            "average_response_time": 0.0,
            "last_request_time": None
        }

        # Streaming state
        self._streaming_requests: Dict[str, List[StreamChunk]] = {}

        # Configure logging
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.logger.setLevel(ClientConfig.LOG_LEVEL)

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for requests."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        if self.api_key:
            headers["X-Bridge-Key"] = self.api_key

        return headers

    def _make_request(self, method: str, endpoint: str,
                     data: Optional[Dict] = None,
                     params: Optional[Dict] = None,
                     stream: bool = False) -> requests.Response:
        """
        Make HTTP request with retry and error handling.
        """
        url = f"{self.base_url}{endpoint}"
        session = self.connection_pool.get_session()

        for attempt in range(self.retry_handler.max_retries):
            try:
                start_time = time.time()

                response = session.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    headers=self._get_headers(),
                    timeout=(self.connect_timeout, self.read_timeout),
                    stream=stream
                )

                # Update statistics
                response_time = time.time() - start_time
                self._update_stats(response_time, success=True)

                return response

            except (ConnectionError, Timeout) as e:
                self._update_stats(success=False)

                if self.retry_handler.should_retry(e, attempt):
                    delay = self.retry_handler.calculate_delay(attempt)
                    self.logger.warning(f"Request failed (attempt {attempt + 1}), "
                                      f"retrying in {delay:.2f}s: {str(e)}")
                    time.sleep(delay)
                else:
                    raise

            except RequestException as e:
                self._update_stats(success=False)
                raise

        raise RequestException(f"All retry attempts failed for {url}")

    def _update_stats(self, response_time: float = None, success: bool = True):
        """Update client statistics."""
        with self._lock:
            if success:
                self.stats["successful_requests"] += 1
            else:
                self.stats["failed_requests"] += 1

            self.stats["total_requests"] += 1
            self.stats["last_request_time"] = time.time()

            if response_time:
                prev_avg = self.stats["average_response_time"]
                prev_count = max(self.stats["total_requests"] - 1, 0)
                self.stats["average_response_time"] = (
                    (prev_avg * prev_count + response_time) /
                    self.stats["total_requests"]
                )

    # ========================================================================
    # Health and Status
    # ========================================================================

    def check_health(self) -> Dict[str, Any]:
        """
        Check the health of the bridge server.

        Returns:
            Dictionary containing health status
        """
        try:
            response = self._make_request("GET", "/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {"status": "error", "message": str(e)}

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get server statistics.

        Returns:
            Dictionary containing server statistics
        """
        try:
            response = self._make_request("GET", "/api/v1/stats")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {}

    def get_metrics(self) -> str:
        """
        Get metrics in Prometheus format.

        Returns:
            Metrics text
        """
        try:
            response = self._make_request("GET", "/metrics")
            response.raise_for_status()
            return response.text
        except Exception as e:
            self.logger.error(f"Failed to get metrics: {e}")
            return ""

    # ========================================================================
    # Request Submission
    # ========================================================================

    def submit_request(self, payload: str,
                      request_type: str = "text",
                      metadata: Optional[Dict] = None,
                      priority: str = "normal") -> Optional[str]:
        """
        Submit a request to the bridge server.

        Args:
            payload: The message content
            request_type: Type of request (text, image, etc.)
            metadata: Additional metadata
            priority: Priority level (low, normal, high, urgent)

        Returns:
            Request ID if successful, None otherwise
        """
        data = {
            "payload": payload,
            "type": request_type,
            "metadata": metadata or {},
            "priority": priority
        }

        try:
            response = self._make_request("POST", "/api/v1/request", data=data)

            if response.status_code == 202:
                result = response.json()
                return result.get("request_id")
            else:
                self.logger.error(f"Unexpected status code: {response.status_code}")
                return None

        except Exception as e:
            self.logger.error(f"Failed to submit request: {e}")
            return None

    def submit_multimodal_request(self, text: str,
                                 images: List[str],
                                 metadata: Optional[Dict] = None) -> Optional[str]:
        """
        Submit a multimodal request with text and images.

        Args:
            text: Text content
            images: List of image IDs (already uploaded)
            metadata: Additional metadata

        Returns:
            Request ID if successful
        """
        data = {
            "payload": text,
            "type": "multimodal",
            "images": images,
            "text": text,
            "metadata": metadata or {}
        }

        try:
            response = self._make_request("POST", "/api/v1/request", data=data)

            if response.status_code == 202:
                result = response.json()
                return result.get("request_id")

            return None

        except Exception as e:
            self.logger.error(f"Failed to submit multimodal request: {e}")
            return None

    # ========================================================================
    # Response Handling
    # ========================================================================

    def get_response(self, timeout_seconds: int = ClientConfig.MAX_POLL_TIME) -> Optional[BridgeResponse]:
        """
        Get the next available response from the bridge server.

        Args:
            timeout_seconds: Maximum time to wait for response

        Returns:
            BridgeResponse object if available, None otherwise
        """
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            try:
                response = self._make_request("GET", "/api/v1/response")

                if response.status_code == 200:
                    result = response.json()

                    if result.get("status") == "completed":
                        response_data = result.get("response", {})
                        return BridgeResponse(
                            request_id=response_data.get("id"),
                            payload=response_data.get("payload"),
                            status=ResponseStatus.SUCCESS,
                            metadata=response_data.get("metadata", {})
                        )
                    elif result.get("status") == "empty":
                        time.sleep(ClientConfig.POLL_INTERVAL)
                        continue

            except Exception as e:
                self.logger.error(f"Error getting response: {e}")
                time.sleep(ClientConfig.POLL_INTERVAL)

        self.logger.warning(f"Timeout waiting for response after {timeout_seconds} seconds")
        return None

    def submit_response(self, request_id: str,
                       response_data: str,
                       response_type: str = "text") -> bool:
        """
        Submit a response to the bridge server (from browser client).

        Args:
            request_id: The ID of the original request
            response_data: The response content
            response_type: Type of response

        Returns:
            True if successful, False otherwise
        """
        data = {
            "request_id": request_id,
            "response": response_data,
            "type": response_type
        }

        try:
            response = self._make_request("POST", "/api/v1/response", data=data)

            if response.status_code == 200:
                result = response.json()
                return result.get("status") == "accepted"

            return False

        except Exception as e:
            self.logger.error(f"Failed to submit response: {e}")
            return False

    # ========================================================================
    # Image Handling
    # ========================================================================

    def upload_image(self, image_path: str) -> Optional[str]:
        """
        Upload an image from file path.

        Args:
            image_path: Path to image file

        Returns:
            Image ID if successful, None otherwise
        """
        try:
            # Read and encode image
            with open(image_path, 'rb') as f:
                image_data = f.read()

            # Validate image size
            if len(image_data) > ClientConfig.MAX_IMAGE_SIZE:
                self.logger.error(f"Image too large: {len(image_data)} bytes")
                return None

            # Determine image type
            import mimetypes
            image_type = mimetypes.guess_type(image_path)[0]
            if image_type not in ClientConfig.SUPPORTED_IMAGE_TYPES:
                self.logger.error(f"Unsupported image type: {image_type}")
                return None

            # Encode to base64
            encoded_data = base64.b64encode(image_data).decode('utf-8')

            return self.upload_image_base64(encoded_data, image_type)

        except Exception as e:
            self.logger.error(f"Failed to upload image: {e}")
            return None

    def upload_image_base64(self, image_data: str,
                           image_type: str = "image/png") -> Optional[str]:
        """
        Upload an image from base64 encoded data.

        Args:
            image_data: Base64 encoded image data
            image_type: MIME type of image

        Returns:
            Image ID if successful, None otherwise
        """
        data = {
            "image_data": image_data,
            "image_type": image_type
        }

        try:
            response = self._make_request("POST", "/api/v1/image", data=data)

            if response.status_code == 200:
                result = response.json()
                return result.get("image_id")

            return None

        except Exception as e:
            self.logger.error(f"Failed to upload image: {e}")
            return None

    def get_image(self, image_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an image from the bridge server.

        Args:
            image_id: The image ID

        Returns:
            Dictionary containing image data
        """
        try:
            response = self._make_request("GET", f"/api/v1/image/{image_id}")

            if response.status_code == 200:
                result = response.json()
                return result.get("image")

            return None

        except Exception as e:
            self.logger.error(f"Failed to get image: {e}")
            return None

    # ========================================================================
    # Streaming Support
    # ========================================================================

    def start_streaming(self, request_id: str) -> None:
        """Initialize streaming for a request."""
        with self._lock:
            self._streaming_requests[request_id] = []

    def submit_stream_chunk(self, request_id: str, chunk: str,
                           sequence: int = None) -> bool:
        """
        Submit a streaming chunk.

        Args:
            request_id: The request ID
            chunk: The chunk content
            sequence: Sequence number (optional)

        Returns:
            True if successful
        """
        data = {
            "chunk": chunk
        }

        try:
            response = self._make_request(
                "POST",
                f"/api/v1/stream/{request_id}",
                data=data
            )

            if response.status_code == 200:
                # Store chunk locally
                with self._lock:
                    if request_id in self._streaming_requests:
                        self._streaming_requests[request_id].append(
                            StreamChunk(
                                request_id=request_id,
                                chunk=chunk,
                                sequence=sequence or len(self._streaming_requests[request_id])
                            )
                        )
                return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to submit stream chunk: {e}")
            return False

    def get_stream_chunks(self, request_id: str) -> List[str]:
        """
        Get all stream chunks for a request.

        Args:
            request_id: The request ID

        Returns:
            List of stream chunks
        """
        try:
            response = self._make_request(
                "GET",
                f"/api/v1/stream/{request_id}"
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("chunks", [])

            return []

        except Exception as e:
            self.logger.error(f"Failed to get stream chunks: {e}")
            return []

    def clear_stream_chunks(self, request_id: str) -> bool:
        """
        Clear stream chunks for a request.

        Args:
            request_id: The request ID

        Returns:
            True if successful
        """
        try:
            response = self._make_request(
                "DELETE",
                f"/api/v1/stream/{request_id}"
            )

            if response.status_code == 200:
                with self._lock:
                    if request_id in self._streaming_requests:
                        del self._streaming_requests[request_id]
                return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to clear stream chunks: {e}")
            return False

    # ========================================================================
    # Async Support
    # ========================================================================

    async def async_submit_request(self, payload: str,
                                  request_type: str = "text",
                                  metadata: Optional[Dict] = None) -> Optional[str]:
        """Async version of submit_request."""
        async with aiohttp.ClientSession() as session:
            data = {
                "payload": payload,
                "type": request_type,
                "metadata": metadata or {}
            }

            try:
                async with session.post(
                    f"{self.base_url}/api/v1/request",
                    json=data,
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=self.read_timeout)
                ) as response:
                    if response.status == 202:
                        result = await response.json()
                        return result.get("request_id")

                    return None

            except Exception as e:
                self.logger.error(f"Async request failed: {e}")
                return None

    async def async_get_response(self,
                                timeout_seconds: int = ClientConfig.MAX_POLL_TIME
                                ) -> Optional[BridgeResponse]:
        """Async version of get_response."""
        start_time = time.time()

        async with aiohttp.ClientSession() as session:
            while time.time() - start_time < timeout_seconds:
                try:
                    async with session.get(
                        f"{self.base_url}/api/v1/response",
                        headers=self._get_headers(),
                        timeout=aiohttp.ClientTimeout(total=self.read_timeout)
                    ) as response:
                        if response.status == 200:
                            result = await response.json()

                            if result.get("status") == "completed":
                                response_data = result.get("response", {})
                                return BridgeResponse(
                                    request_id=response_data.get("id"),
                                    payload=response_data.get("payload"),
                                    status=ResponseStatus.SUCCESS
                                )
                            elif result.get("status") == "empty":
                                await asyncio.sleep(ClientConfig.POLL_INTERVAL)
                                continue

                except Exception as e:
                    self.logger.error(f"Async get response failed: {e}")
                    await asyncio.sleep(ClientConfig.POLL_INTERVAL)

        return None

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def wait_for_response(self, request_id: str,
                         timeout_seconds: int = ClientConfig.MAX_POLL_TIME,
                         progress_callback: Optional[Callable[[str], None]] = None
                         ) -> Optional[BridgeResponse]:
        """
        Wait for a specific response with progress tracking.

        Args:
            request_id: The request ID to wait for
            timeout_seconds: Maximum time to wait
            progress_callback: Callback for progress updates

        Returns:
            BridgeResponse if received, None on timeout
        """
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            response = self.get_response(timeout_seconds=1)

            if response and response.request_id == request_id:
                return response

            if progress_callback:
                elapsed = time.time() - start_time
                progress_callback(f"Waiting... {elapsed:.1f}s elapsed")

            time.sleep(ClientConfig.POLL_INTERVAL)

        return None

    def close(self):
        """Close the client and release resources."""
        self.connection_pool.close()
        with self._lock:
            self._streaming_requests.clear()
        self.logger.info("Bridge client closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def __del__(self):
        """Destructor."""
        try:
            self.close()
        except:
            pass


# ============================================================================
# Helper Functions
# ============================================================================

def create_client(base_url: str = ClientConfig.DEFAULT_BASE_URL,
                 api_key: Optional[str] = None) -> BridgeClient:
    """Factory function to create a BridgeClient."""
    return BridgeClient(base_url=base_url, api_key=api_key)


def test_connection(base_url: str = ClientConfig.DEFAULT_BASE_URL) -> bool:
    """Test connection to bridge server."""
    client = BridgeClient(base_url=base_url)
    health = client.check_health()
    client.close()
    return health.get("status") == "healthy"


# ============================================================================
# Usage Example
# ============================================================================

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=ClientConfig.LOG_LEVEL,
        format=ClientConfig.LOG_FORMAT
    )

    # Create client
    client = BridgeClient()

    # Check health
    health = client.check_health()
    print(f"Server health: {health}")

    # Submit a test request
    request_id = client.submit_request(
        "Hello, bridge server!",
        priority="high"
    )

    if request_id:
        print(f"Request submitted with ID: {request_id}")

        # Wait for response
        response = client.wait_for_response(request_id, timeout_seconds=10)

        if response:
            print(f"Response received: {response.payload}")
        else:
            print("Timeout waiting for response")

    # Test image upload
    # image_id = client.upload_image("test_image.png")
    # if image_id:
    #     print(f"Image uploaded with ID: {image_id}")

    # Close client
    client.close()
