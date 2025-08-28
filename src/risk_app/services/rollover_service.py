"""Rollover service for Risk Manager V6"""
import time
from datetime import datetime, timezone, timedelta
from typing import List
import structlog
from ..stores.anchors_store import AnchorsStore
from ..repos.accounts_repo import AccountsRepository
from ..core.errors import RiskManagerError

logger = structlog.get_logger(__name__)

class RolloverService:
    """Handles daily rollover at 17:00 CT"""
    
    def __init__(self, anchors_store: AnchorsStore, accounts_repo: AccountsRepository):
        self.anchors_store = anchors_store
        self.accounts_repo = accounts_repo
        self.last_rollover_check = 0.0
        self.rollover_check_interval = 60  # Check every minute
    
    def is_rollover_time(self) -> bool:
        """Check if it's time for rollover (17:00 CT)"""
        # Convert current time to CT
        utc_now = datetime.now(timezone.utc)
        ct_offset = timedelta(hours=5)  # CT is UTC-5
        ct_time = utc_now - ct_offset
        
        # Check if it's 17:00 (5:00 PM) CT
        return ct_time.hour == 17 and ct_time.minute == 0
    
    def should_check_rollover(self) -> bool:
        """Check if we should check for rollover (rate limiting)"""
        current_time = time.time()
        if current_time - self.last_rollover_check >= self.rollover_check_interval:
            self.last_rollover_check = current_time
            return True
        return False
    
    def perform_rollover_if_needed(self) -> List[int]:
        """Perform rollover for all accounts if it's rollover time"""
        if not self.should_check_rollover():
            return []
        
        if not self.is_rollover_time():
            return []
        
        logger.info("Starting daily rollover process")
        
        # Get all accounts that need rollover
        accounts = self.accounts_repo.get_active_accounts()
        rolled_over_accounts = []
        
        for account in accounts:
            if self.anchors_store.is_rollover_needed(account.id):
                try:
                    # Use equity for rollover (includes unrealized P&L)
                    current_equity = account.display_equity
                    self.anchors_store.perform_rollover(account.id, current_equity)
                    rolled_over_accounts.append(account.id)
                    logger.info("Rollover completed for account", 
                               account_id=account.id,
                               account_name=account.name,
                               equity=current_equity)
                except Exception as e:
                    logger.error("Failed to perform rollover for account", 
                               account_id=account.id,
                               error=str(e))
        
        if rolled_over_accounts:
            logger.info("Daily rollover completed", 
                       account_count=len(rolled_over_accounts),
                       account_ids=rolled_over_accounts)
        else:
            logger.info("No accounts needed rollover")
        
        return rolled_over_accounts
    
    def initialize_account_anchors(self, account_id: int, current_balance: float, starting_balance: float) -> None:
        """Initialize anchors for a new account"""
        try:
            # Set starting balance (only once)
            self.anchors_store.set_starting_balance(account_id, starting_balance)
            
            # Set initial EOD high anchor to current balance
            self.anchors_store.update_eod_high_anchor(account_id, current_balance)
            
            logger.info("Initialized anchors for account", 
                       account_id=account_id,
                       starting_balance=starting_balance,
                       initial_balance=current_balance)
        except Exception as e:
            logger.error("Failed to initialize anchors for account", 
                        account_id=account_id,
                        error=str(e))
            raise RiskManagerError(f"Failed to initialize anchors: {e}")
    
    def update_intraday_high(self, account_id: int, current_equity: float) -> None:
        """Update intraday high for an account"""
        try:
            self.anchors_store.update_intraday_high(account_id, current_equity)
        except Exception as e:
            logger.error("Failed to update intraday high", 
                        account_id=account_id,
                        error=str(e))
    
    def get_rollover_status(self) -> dict:
        """Get current rollover status"""
        accounts = self.accounts_repo.get_active_accounts()
        status = {
            "is_rollover_time": self.is_rollover_time(),
            "accounts_needing_rollover": [],
            "total_accounts": len(accounts)
        }
        
        for account in accounts:
            if self.anchors_store.is_rollover_needed(account.id):
                status["accounts_needing_rollover"].append({
                    "account_id": account.id,
                    "account_name": account.name,
                    "current_equity": account.display_equity,
                    "starting_balance": self.anchors_store.get_starting_balance(account.id),
                    "eod_high_anchor": self.anchors_store.get_eod_high_anchor(account.id),
                    "intraday_high_today": self.anchors_store.get_intraday_high_today(account.id),
                    "locked_out": self.anchors_store.is_locked_out(account.id)
                })
        
        return status

