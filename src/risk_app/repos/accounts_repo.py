"""Accounts repository for Risk Manager V6"""
from typing import List, Dict, Any, Optional
import time
import structlog
from ..domain.models import Account
from ..core.errors import RiskManagerError

logger = structlog.get_logger(__name__)

class AccountsRepository:
    """In-memory repository for account data"""
    
    def __init__(self):
        self._accounts: Dict[int, Account] = {}
        self._last_update: Optional[float] = None
    
    def store_accounts(self, accounts_data: List[Dict[str, Any]]) -> None:
        """Store accounts from API response"""
        try:
            logger.info("Storing accounts", count=len(accounts_data))
            
            # Clear existing accounts
            self._accounts.clear()
            
            # Convert and store new accounts
            for account_data in accounts_data:
                try:
                    account = Account(**account_data)
                    self._accounts[account.id] = account
                    logger.debug("Stored account", account_id=account.id, name=account.name)
                except Exception as e:
                    logger.warning("Failed to parse account data", 
                                 account_data=account_data, error=str(e))
            
            self._last_update = time.time()
            logger.info("Accounts stored successfully", total_accounts=len(self._accounts))
            
        except Exception as e:
            logger.error("Failed to store accounts", error=str(e))
            raise RiskManagerError(f"Failed to store accounts: {e}")
    
    def get_all_accounts(self) -> List[Account]:
        """Get all stored accounts"""
        return list(self._accounts.values())
    
    def get_active_accounts(self) -> List[Account]:
        """Get only active accounts"""
        return [account for account in self._accounts.values() if account.is_active]
    
    def get_account(self, account_id: int) -> Optional[Account]:
        """Get a specific account by ID"""
        return self._accounts.get(account_id)
    
    def get_account_count(self) -> int:
        """Get the number of stored accounts"""
        return len(self._accounts)
    
    def is_fresh(self, max_age_seconds: int = 300) -> bool:
        """Check if the data is fresh (updated within max_age_seconds)"""
        if self._last_update is None:
            return False
        
        return (time.time() - self._last_update) < max_age_seconds
    
    def clear(self) -> None:
        """Clear all stored accounts"""
        self._accounts.clear()
        self._last_update = None
        logger.info("Accounts repository cleared")
