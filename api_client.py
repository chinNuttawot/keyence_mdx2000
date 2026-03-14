"""
API Client for sending marking data to external API.

Sends laser marking data retrieved from Keyence MD-X2000 to a configured API endpoint.
"""

import logging
import json
from typing import Optional, Dict, Any
from datetime import datetime
from dataclasses import asdict

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import config
from keyence_client import MarkingData, KeyenceStatus


class APIClientError(Exception):
    """Exception for API communication errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class APIClient:
    """
    Client for sending marking data to external API.
    
    Attributes:
        endpoint: API endpoint URL
        api_key: Optional API key for authentication
        timeout: Request timeout in seconds
    """
    
    def __init__(
        self,
        endpoint: str = None,
        api_key: str = None,
        timeout: int = None
    ):
        """
        Initialize API client.
        
        Args:
            endpoint: API endpoint URL (default from config)
            api_key: API key for authentication (default from config)
            timeout: Request timeout in seconds (default from config)
        """
        self.endpoint = endpoint or config.API_ENDPOINT
        self.api_key = api_key or config.API_KEY
        self.timeout = timeout or config.API_TIMEOUT
        
        self.logger = logging.getLogger(__name__)
        
        # Setup session with retry logic
        self._session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Create requests session with retry logic."""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Disable SSL verification for internal servers with self-signed certificates
        session.verify = False
        
        return session
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers including authentication."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "KeyenceMDX2000-Client/1.0"
        }
        
        if self.api_key:
            # Support multiple authentication methods
            # Uncomment the one that matches your API
            headers["X-API-Key"] = self.api_key
            # headers["Authorization"] = f"Bearer {self.api_key}"
            # headers["Authorization"] = f"Basic {self.api_key}"
        
        # Device JWT token for protected endpoints (e.g., /api/injection/scan)
        if getattr(config, 'AUTH_TOKEN', '') and config.AUTH_TOKEN:
            headers["Authorization"] = f"Bearer {config.AUTH_TOKEN}"
        
        return headers
    
    def _prepare_payload(self, marking_data: MarkingData) -> Dict[str, Any]:
        """
        Prepare JSON payload for API request.
        
        Args:
            marking_data: MarkingData object from Keyence client
            
        Returns:
            Dictionary payload for JSON serialization
        """
        # Convert MarkingData to dict and add metadata
        payload = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "keyence_mdx2000",
            "data": {
                "status": marking_data.status.value,
                "marking_text": marking_data.marking_text,
                "job_number": marking_data.job_number,
                "block_number": marking_data.block_number,
                "error_code": marking_data.error_code
            }
        }
        
        return payload
    
    def send_marking_data(self, marking_data: MarkingData) -> Dict[str, Any]:
        """
        Send marking data to the API endpoint.
        
        Args:
            marking_data: MarkingData object containing marking information
            
        Returns:
            API response as dictionary
            
        Raises:
            APIClientError: If API request fails
        """
        if not self.endpoint:
            raise APIClientError("API endpoint not configured")
        
        payload = self._prepare_payload(marking_data)
        
        self.logger.info(f"Sending marking data to API: {self.endpoint}")
        self.logger.debug(f"Payload: {json.dumps(payload, indent=2)}")
        
        try:
            response = self._session.post(
                self.endpoint,
                json=payload,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            
            response.raise_for_status()
            
            result = response.json() if response.content else {}
            self.logger.info(f"API response: {response.status_code}")
            
            return result
            
        except requests.exceptions.Timeout:
            raise APIClientError("API request timeout", status_code=None)
        except requests.exceptions.ConnectionError as e:
            raise APIClientError(f"API connection error: {e}", status_code=None)
        except requests.exceptions.HTTPError as e:
            raise APIClientError(
                f"API HTTP error: {e}",
                status_code=e.response.status_code if e.response else None,
                response=e.response.text if e.response else None
            )
        except requests.exceptions.RequestException as e:
            raise APIClientError(f"API request failed: {e}")
        except json.JSONDecodeError:
            self.logger.warning("API response is not valid JSON")
            return {"status": "success", "raw_response": response.text}
    
    def send_raw_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send raw dictionary data to the API endpoint.
        
        Args:
            data: Dictionary data to send
            
        Returns:
            API response as dictionary
            
        Raises:
            APIClientError: If API request fails
        """
        if not self.endpoint:
            raise APIClientError("API endpoint not configured")
        
        # Add timestamp and source
        payload = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": "keyence_mdx2000",
            "data": data
        }
        
        self.logger.info(f"Sending raw data to API: {self.endpoint}")
        
        try:
            response = self._session.post(
                self.endpoint,
                json=payload,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            
            response.raise_for_status()
            
            return response.json() if response.content else {}
            
        except requests.exceptions.RequestException as e:
            raise APIClientError(f"API request failed: {e}")
    
    def get_current_production_order(self) -> Dict[str, Any]:
        """
        Get current production order from API.
        
        Returns:
            Dictionary containing production order data
            
        Raises:
            APIClientError: If API request fails
        """
        endpoint = config.PRODUCTION_ORDERS_API
        params = {"isDateTimeNow": "true"}
        
        self.logger.info(f"Requesting production order from: {endpoint}")
        self.logger.debug(f"Params: {params}")
        
        try:
            response = self._session.get(
                endpoint,
                params=params,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            
            response.raise_for_status()
            result = response.json()
            self.logger.info(f"Production order retrieved successfully")
            return result
            
        except requests.exceptions.RequestException as e:
            raise APIClientError(f"Failed to get production order: {e}")

    def send_injection_scan(self, scan_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send injection scan data to API.
        
        Args:
            scan_data: Dictionary containing combined marking and production data
            
        Returns:
            API response as dictionary
        """
        endpoint = config.INJECTION_SCAN_API
        
        self.logger.info(f"==> POST {endpoint}")
        self.logger.debug(f"==> Payload: {json.dumps(scan_data, indent=2)}")
        
        try:
            response = self._session.post(
                endpoint,
                json=scan_data,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            
            response.raise_for_status()
            result = response.json() if response.content else {}
            self.logger.info(f"Injection scan sent successfully: {response.status_code}")
            self.logger.debug(f"<== Response [{response.status_code}]: {json.dumps(result, indent=2)}")
            return result
            
        except requests.exceptions.RequestException as e:
            raise APIClientError(f"Failed to send injection scan: {e}")

    def health_check(self) -> bool:
        """
        Check if API endpoint is reachable.
        
        Returns:
            True if API is reachable, False otherwise
        """
        # specialized health check might be needed, but for now we check the legacy endpoint
        # or we could check the new ones. Let's check the production order endpoint as it's critical.
        if config.PRODUCTION_ORDERS_API:
             try:
                # Just a quick check, maybe without payload or a simple GET if supported, 
                # but usually HEAD is safer. However, POST-only APIs might fail HEAD.
                # Let's try 'options' or just assume true if we can connect.
                # For safety, let's keep the legacy check if configured, OR check the new one.
                response = self._session.head(config.PRODUCTION_ORDERS_API, timeout=5)
                # 405 Method Not Allowed is actually a success for connectivity check on a POST endpoint
                return response.status_code < 500
             except:
                 pass
        
        if not self.endpoint:
            return False
        
        try:
            response = self._session.head(
                self.endpoint,
                headers=self._get_headers(),
                timeout=5
            )
            return response.status_code < 500
        except requests.exceptions.RequestException:
            return False
    
    def close(self) -> None:
        """Close the API client session."""
        if self._session:
            self._session.close()
            self.logger.info("API client session closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False
