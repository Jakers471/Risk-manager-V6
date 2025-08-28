"""
Accounts adapter for Risk Manager V6

HIDDEN NOTES FOR AI REFERENCE:
- ALWAYS CROSS REFERENCE TO DOCS FOR PROPER API REFERENCING
- CHECK TOPSTEP PROGRAM RULES DOCUMENTATION FOR HELPFUL INFO
- API endpoint: POST https://api.topstepx.com/api/Account/search
- Use "onlyActiveAccounts" parameter to filter active accounts
- Response contains "accounts" array with account details
- Account fields: id, name, status, balance, equity, margin, freeMargin
- Use "canTrade" field to determine if account is tradeable
"""
from typing import List, Dict, Any, Optional
import structlog
from .http import HTTPClient
from ..core.errors import APIError

logger = structlog.get_logger(__name__)

class AccountsAdapter:
    """Handles account-related API calls"""
    
    def __init__(self, http_client: HTTPClient):
        self.http_client = http_client
    
    def search_accounts(self, only_active: bool = True) -> List[Dict[str, Any]]:
        """Search for accounts based on criteria"""
        try:
            logger.info("Searching for accounts", only_active=only_active)
            
            # Prepare request data
            request_data = {
                "onlyActiveAccounts": only_active
            }
            
            # Make API call
            response = self.http_client.post("/api/Account/search", request_data)
            
            # Validate response
            if not response.get("success"):
                error_msg = response.get("errorMessage", "Unknown error")
                logger.error("Account search failed", error=error_msg)
                raise APIError(f"Account search failed: {error_msg}")
            
            # Extract accounts
            accounts = response.get("accounts", [])
            logger.info("Account search successful", account_count=len(accounts))
            
            return accounts
            
        except Exception as e:
            logger.error("Account search failed", error=str(e))
            raise APIError(f"Account search failed: {e}")
    
    def get_account_details(self, account_id: int) -> Optional[Dict[str, Any]]:
        """Get details for a specific account"""
        try:
            logger.info("Fetching account details", account_id=account_id)
            
            # Search for the specific account
            accounts = self.search_accounts(only_active=False)
            
            # Find the account by ID
            for account in accounts:
                if account.get("id") == account_id:
                    logger.info("Account details retrieved", account_id=account_id)
                    return account
            
            logger.warning("Account not found", account_id=account_id)
            return None
            
        except Exception as e:
            logger.error("Failed to get account details", account_id=account_id, error=str(e))
            raise APIError(f"Failed to get account details: {e}")

