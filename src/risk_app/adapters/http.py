"""HTTP client for Risk Manager V6"""
import time
import requests
from typing import Optional, Dict, Any
import structlog
from ..core.settings import settings
from ..core.errors import APIError

logger = structlog.get_logger(__name__)

class HTTPClient:
    """HTTP client with session management and retry logic"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })
        self.access_token: Optional[str] = None
        self.token_expiry: Optional[float] = None
    
    def set_auth_token(self, token: str, expires_in: int = 3600) -> None:
        """Set the authentication token and calculate expiry"""
        self.access_token = token
        self.token_expiry = time.time() + expires_in
        self.session.headers['Authorization'] = f'Bearer {token}'
        logger.info("Auth token set", expires_in_minutes=expires_in//60)
    
    def is_token_valid(self) -> bool:
        """Check if the current token is still valid"""
        if not self.access_token or not self.token_expiry:
            return False
        
        # Add margin for refresh
        margin = settings.token_refresh_margin * 60
        return time.time() < (self.token_expiry - margin)
    
    def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make a POST request with retry logic"""
        url = f"{settings.api_base_url}{endpoint}"
        
        for attempt in range(settings.api_max_retries):
            try:
                logger.debug("Making POST request", url=url, attempt=attempt+1)
                response = self.session.post(
                    url,
                    json=data,
                    timeout=settings.api_timeout
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    logger.warning("Authentication failed", status_code=response.status_code)
                    raise APIError("Authentication failed", response.status_code, response.json())
                else:
                    logger.error("API request failed", 
                               status_code=response.status_code, 
                               response=response.text)
                    raise APIError(f"API request failed: {response.status_code}", 
                                 response.status_code, response.json())
                    
            except requests.exceptions.RequestException as e:
                logger.warning("Request failed, retrying", 
                             attempt=attempt+1, 
                             error=str(e))
                if attempt == settings.api_max_retries - 1:
                    raise APIError(f"Request failed after {settings.api_max_retries} attempts: {e}")
                time.sleep(2 ** attempt)  # Exponential backoff
    
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a GET request with retry logic"""
        url = f"{settings.api_base_url}{endpoint}"
        
        for attempt in range(settings.api_max_retries):
            try:
                logger.debug("Making GET request", url=url, attempt=attempt+1)
                response = self.session.get(
                    url,
                    params=params,
                    timeout=settings.api_timeout
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    logger.warning("Authentication failed", status_code=response.status_code)
                    raise APIError("Authentication failed", response.status_code, response.json())
                else:
                    logger.error("API request failed", 
                               status_code=response.status_code, 
                               response=response.text)
                    raise APIError(f"API request failed: {response.status_code}", 
                                 response.status_code, response.json())
                    
            except requests.exceptions.RequestException as e:
                logger.warning("Request failed, retrying", 
                             attempt=attempt+1, 
                             error=str(e))
                if attempt == settings.api_max_retries - 1:
                    raise APIError(f"Request failed after {settings.api_max_retries} attempts: {e}")
                time.sleep(2 ** attempt)  # Exponential backoff

