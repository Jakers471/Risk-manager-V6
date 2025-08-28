"""HTTP client for Risk Manager V6."""

import time
import structlog
from typing import Optional, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..core.settings import settings
from ..core.errors import APIError

logger = structlog.get_logger(__name__)


class HTTPClient:
    """HTTP client with session management and retry logic."""
    
    def __init__(self):
        """Initialize the HTTP client."""
        self.session = requests.Session()
        self._access_token: Optional[str] = None
        self._token_expiry: Optional[int] = None
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=settings.api_max_retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set default headers
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "RiskManagerV6/1.0"
        })
    
    def set_access_token(self, token: str, expires_in: int):
        """Set the access token and expiry."""
        self._access_token = token
        self._token_expiry = time.time() + expires_in
        
        # Update authorization header
        self.session.headers.update({
            "Authorization": f"Bearer {token}"
        })
        
        logger.info("Auth token set", expires_in_minutes=expires_in // 60)
    
    def is_token_valid(self) -> bool:
        """Check if the current token is still valid."""
        if not self._access_token or not self._token_expiry:
            return False
        
        # Add margin to prevent edge cases
        margin = settings.auth_token_refresh_margin_minutes * 60
        return time.time() < (self._token_expiry - margin)
    
    def should_refresh_token(self) -> bool:
        """Check if token should be refreshed soon."""
        if not self._access_token or not self._token_expiry:
            return True
        
        margin = settings.auth_token_refresh_margin_minutes * 60
        return time.time() >= (self._token_expiry - margin)
    
    def post(self, endpoint: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Make a POST request."""
        url = f"{settings.api_base_url}{endpoint}"
        
        try:
            response = self.session.post(
                url,
                json=data,
                timeout=settings.api_timeout
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error("POST request failed", endpoint=endpoint, error=str(e))
            raise APIError(f"POST request failed: {e}")
    
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Make a GET request."""
        url = f"{settings.api_base_url}{endpoint}"
        
        try:
            response = self.session.get(
                url,
                params=params,
                timeout=settings.api_timeout
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error("GET request failed", endpoint=endpoint, error=str(e))
            raise APIError(f"GET request failed: {e}")

