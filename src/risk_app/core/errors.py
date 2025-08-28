"""Custom exceptions for Risk Manager V6"""

class RiskManagerError(Exception):
    """Base exception for Risk Manager V6"""
    pass

class AuthenticationError(RiskManagerError):
    """Raised when authentication fails"""
    pass

class APIError(RiskManagerError):
    """Raised when API calls fail"""
    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data

class ConfigurationError(RiskManagerError):
    """Raised when configuration is invalid or missing"""
    pass

class SessionError(RiskManagerError):
    """Raised when session management fails"""
    pass

