"""
Bridge Client - PyQt6 Integration
=================================
A professional client that integrates with the Bridge Server
for seamless API communication through browser proxy.
"""

import json
import logging
import time
from typing import Optional, Dict, Any, Callable
import requests
from requests.exceptions import RequestException, Timeout

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BridgeClient:
    """Professional client for communicating with the Bridge Server."""

    def __init__(self, base_url: str = "http://127.0.0.1:5000"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.timeout = 5  # seconds
        self.max_retries = 3
        self.retry_delay = 1  # seconds

    def check_health(self) -> Dict[str, Any]:
        """
        Check the health of the bridge server.

        Returns:
            Dictionary containing health status
        """
        try:
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except RequestException as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "error", "message": str(e)}

    def submit_request(self, payload: str, request_type: str = "text",
                      metadata: Optional[Dict] = None) -> Optional[str]:
        """
        Submit a request to the bridge server.

        Args:
            payload: The message content
            request_type: Type of request (text, image, etc.)
            metadata: Additional metadata

        Returns:
            Request ID if successful, None otherwise
        """
        data = {
            "payload": payload,
            "type": request_type,
            "metadata": metadata or {}
        }

        for attempt in range(self.max_retries):
            try:
                response = self.session.post(
                    f"{self.base_url}/api/v1/request",
                    json=data,
                    timeout=self.timeout
                )
                response.raise_for_status()

                result = response.json()
                if result.get("status") == "queued":
                    return result.get("request_id")
                else:
                    logger.error(f"Unexpected response: {result}")
                    return None

            except RequestException as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"All attempts failed for request submission")
                    return None

        return None

    def get_response(self, timeout_seconds: int = 30) -> Optional[Dict[str, Any]]:
        """
        Get the next available response from the bridge server.

        Args:
            timeout_seconds: Maximum time to wait for response

        Returns:
            Response data if available, None otherwise
        """
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            try:
                response = self.session.get(
                    f"{self.base_url}/api/v1/response",
                    timeout=self.timeout
                )
                response.raise_for_status()

                result = response.json()
                if result.get("status") == "completed":
                    return result.get("response")
                elif result.get("status") == "empty":
                    time.sleep(0.5)  # Poll every 500ms
                    continue
                else:
                    logger.warning(f"Unexpected status: {result.get('status')}")
                    time.sleep(0.5)

            except RequestException as e:
                logger.error(f"Error getting response: {e}")
                time.sleep(0.5)

        logger.warning(f"Timeout waiting for response after {timeout_seconds} seconds")
        return None

    def submit_response(self, request_id: str, response_data: str,
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
            response = self.session.post(
                f"{self.base_url}/api/v1/response",
                json=data,
                timeout=self.timeout
            )
            response.raise_for_status()

            result = response.json()
            return result.get("status") == "accepted"

        except RequestException as e:
            logger.error(f"Error submitting response: {e}")
            return False

    def get_stream_chunks(self, request_id: str) -> list:
        """
        Get streaming chunks for a request.

        Args:
            request_id: The request ID

        Returns:
            List of stream chunks
        """
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/stream/{request_id}",
                timeout=self.timeout
            )
            response.raise_for_status()

            result = response.json()
            return result.get("chunks", [])

        except RequestException as e:
            logger.error(f"Error getting stream chunks: {e}")
            return []

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get server statistics.

        Returns:
            Dictionary containing server statistics
        """
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/stats",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()

        except RequestException as e:
            logger.error(f"Error getting statistics: {e}")
            return {}

# Usage example
if __name__ == "__main__":
    client = BridgeClient()

    # Check server health
    health = client.check_health()
    print(f"Server health: {health}")

    # Submit a test request
    request_id = client.submit_request("Hello, bridge server!")
    if request_id:
        print(f"Request submitted with ID: {request_id}")

        # Wait for response
        response = client.get_response(timeout_seconds=10)
        if response:
            print(f"Response received: {response}")
