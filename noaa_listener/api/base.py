"""Base API client with retry logic and error handling."""

import time
from typing import Optional, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from noaa_listener.logger import get_logger

logger = get_logger(__name__)


class BaseAPIClient:
    """Base API client with common functionality."""
    
    def __init__(
        self,
        base_url: str,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: int = 5,
        headers: Optional[Dict[str, str]] = None
    ):
        """Initialize API client.
        
        Args:
            base_url: Base URL for API
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries in seconds
            headers: Default headers to include in requests
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.default_headers = headers or {}
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry logic.
        
        Returns:
            Configured requests session
        """
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=1,
            raise_on_status=False
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers
        session.headers.update(self.default_headers)
        
        return session
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        retry_count: int = 0
    ) -> Optional[Dict[str, Any]]:
        """Make an API request with retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            params: Query parameters
            headers: Request headers
            json_data: JSON request body
            retry_count: Current retry attempt
            
        Returns:
            Response JSON or None on failure
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                headers=headers,
                json=json_data,
                timeout=self.timeout
            )
            
            # Handle rate limiting
            if response.status_code == 429:
                if retry_count < self.max_retries:
                    retry_after = int(response.headers.get('Retry-After', self.retry_delay))
                    wait_time = min(retry_after, self.retry_delay * (2 ** retry_count))
                    logger.warning(f"Rate limited. Waiting {wait_time}s before retry {retry_count + 1}/{self.max_retries}")
                    time.sleep(wait_time)
                    return self._make_request(method, endpoint, params, headers, json_data, retry_count + 1)
                else:
                    logger.error(f"Rate limit exceeded after {self.max_retries} retries")
                    return None
            
            # Handle other errors
            if response.status_code >= 400:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                if retry_count < self.max_retries and response.status_code >= 500:
                    wait_time = self.retry_delay * (2 ** retry_count)
                    logger.info(f"Retrying in {wait_time}s (attempt {retry_count + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                    return self._make_request(method, endpoint, params, headers, json_data, retry_count + 1)
                return None
            
            # Success
            return response.json()
            
        except requests.exceptions.Timeout:
            logger.error(f"Request timeout for {url}")
            if retry_count < self.max_retries:
                wait_time = self.retry_delay * (2 ** retry_count)
                logger.info(f"Retrying in {wait_time}s (attempt {retry_count + 1}/{self.max_retries})")
                time.sleep(wait_time)
                return self._make_request(method, endpoint, params, headers, json_data, retry_count + 1)
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            if retry_count < self.max_retries:
                wait_time = self.retry_delay * (2 ** retry_count)
                logger.info(f"Retrying in {wait_time}s (attempt {retry_count + 1}/{self.max_retries})")
                time.sleep(wait_time)
                return self._make_request(method, endpoint, params, headers, json_data, retry_count + 1)
            return None
        
        except Exception as e:
            logger.error(f"Unexpected error during API request: {e}")
            return None
    
    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Make a GET request.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            headers: Request headers
            
        Returns:
            Response JSON or None
        """
        return self._make_request("GET", endpoint, params=params, headers=headers)
    
    def post(
        self,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Make a POST request.
        
        Args:
            endpoint: API endpoint
            json_data: JSON request body
            params: Query parameters
            headers: Request headers
            
        Returns:
            Response JSON or None
        """
        return self._make_request("POST", endpoint, params=params, headers=headers, json_data=json_data)
    
    def close(self) -> None:
        """Close the session."""
        self.session.close()
