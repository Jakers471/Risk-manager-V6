"""Authentication module for Risk Manager V6"""
import time
from typing import Optional, Dict, Any
import structlog
from .http import HTTPClient
from ..core.settings import settings
from ..core.errors import AuthenticationError, ConfigurationError

logger = structlog.get_logger(__name__)

class AuthManager:
    """Manages authentication and session tokens"""
    
    def __init__(self):
        self.http_client = HTTPClient()
        self.access_token: Optional[str] = None
        self.token_expiry: Optional[float] = None
        
        # Validate credentials are available
        if not settings.api_username or not settings.api_key:
            raise ConfigurationError("Missing API credentials. Set TOPSTEP_USERNAME and TOPSTEP_API_KEY environment variables.")
    
    def login(self) -> bool:
        """Authenticate with the API using username and API key"""
        try:
            logger.info("Attempting authentication")
            
            # Prepare login request
            login_data = {
                "userName": settings.api_username,
                "apiKey": settings.api_key
            }
            
            # Make login request
            response = self.http_client.post(settings.api_auth_endpoint, login_data)
            
            # Validate response
            if not response.get("success"):
                error_msg = response.get("errorMessage", "Unknown error")
                logger.error("Authentication failed", error=error_msg)
                raise AuthenticationError(f"Login failed: {error_msg}")
            
            # Extract token
            token = response.get("token")
            if not token:
                logger.error("No token received in response")
                raise AuthenticationError("No authentication token received")
            
            # Store token
            self.access_token = token
            self.token_expiry = time.time() + (settings.session_timeout * 60)
            self.http_client.set_auth_token(token, settings.session_timeout * 60)
            
            # Calculate expiry time for logging
            expiry_minutes = int((self.token_expiry - time.time()) / 60)
            logger.info("Authentication successful", 
                       token_expires_in_minutes=expiry_minutes)
            
            return True
            
        except Exception as e:
            logger.error("Authentication failed", error=str(e))
            raise AuthenticationError(f"Authentication failed: {e}")
    
    def is_authenticated(self) -> bool:
        """Check if we have a valid authentication token"""
        if not self.access_token or not self.token_expiry:
            return False
        
        # Check if token is still valid with margin
        margin = settings.token_refresh_margin * 60
        is_valid = time.time() < (self.token_expiry - margin)
        
        if not is_valid:
            logger.info("Token expired or will expire soon", 
                       expires_in_minutes=int((self.token_expiry - time.time()) / 60))
        
        return is_valid
    
    def refresh_if_needed(self) -> bool:
        """Refresh authentication if token is expired or about to expire"""
        if self.is_authenticated():
            return True
        
        logger.info("Token needs refresh, re-authenticating")
        return self.login()
    
    def get_token_info(self) -> Dict[str, Any]:
        """Get information about the current token"""
        if not self.access_token:
            return {"status": "not_authenticated"}
        
        expires_in_minutes = int((self.token_expiry - time.time()) / 60) if self.token_expiry else 0
        
        return {
            "status": "authenticated" if self.is_authenticated() else "expired",
            "expires_in_minutes": expires_in_minutes,
            "token_length": len(self.access_token) if self.access_token else 0
        }

