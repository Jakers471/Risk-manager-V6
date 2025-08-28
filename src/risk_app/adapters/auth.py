"""Authentication adapter for Risk Manager V6."""

import structlog
from typing import Optional, Dict, Any

from ..core.settings import settings
from ..core.errors import AuthenticationError
from .http import HTTPClient

logger = structlog.get_logger(__name__)


class AuthManager:
    """Manages authentication with the Topstep API."""
    
    def __init__(self):
        """Initialize the authentication manager."""
        self.http_client = HTTPClient()
        
        # Validate credentials
        if not settings.username or not settings.api_key:
            raise AuthenticationError("Missing API credentials in settings")
        
        self.username = settings.username
        self.api_key = settings.api_key
        self._access_token: Optional[str] = None
        self._token_expiry: Optional[int] = None
    
    def login(self) -> bool:
        """Authenticate with the Topstep API."""
        logger.info("Attempting authentication")
        
        try:
            # Prepare login payload
            payload = {
                "userName": self.username,  # API expects "userName" not "username"
                "apiKey": self.api_key
            }
            
            # Make login request
            response = self.http_client.post(
                endpoint=settings.api_auth_endpoint,
                data=payload
            )
            
            if response and response.get("success") and "token" in response:
                # Store token and expiry
                self._access_token = response["token"]
                self._token_expiry = 3600  # Default 1 hour expiry
                
                # Set token in HTTP client
                self.http_client.set_access_token(self._access_token, self._token_expiry)
                
                logger.info("Authentication successful", 
                           token_expires_in_minutes=self.token_expires_in_minutes)
                return True
            else:
                error_msg = response.get("errorMessage", "Unknown error") if response else "No response"
                logger.error("Authentication failed", error=error_msg, response=response)
                raise AuthenticationError(f"Authentication failed: {error_msg}")
                
        except Exception as e:
            logger.error("Authentication failed", error=str(e))
            raise AuthenticationError(f"Authentication failed: {e}")
    
    def is_authenticated(self) -> bool:
        """Check if currently authenticated."""
        return self._access_token is not None and self.http_client.is_token_valid()
    
    def refresh_if_needed(self) -> bool:
        """Refresh token if it's about to expire."""
        if not self.is_authenticated():
            return self.login()
        
        # Check if token needs refresh (within margin)
        if self.http_client.should_refresh_token():
            logger.info("Refreshing authentication token")
            return self.login()
        
        return True
    
    @property
    def token_expires_in_minutes(self) -> int:
        """Get minutes until token expires."""
        if not self._token_expiry:
            return 0
        return self._token_expiry // 60
    
    def get_token_info(self) -> Dict[str, Any]:
        """Get current token information."""
        return {
            "status": "authenticated" if self.is_authenticated() else "not_authenticated",
            "expires_in_minutes": self.token_expires_in_minutes,
            "needs_refresh": self.http_client.should_refresh_token() if self.is_authenticated() else True
        }

