"""Anchors store for Risk Manager V6"""
import json
import time
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime, timezone
import structlog
from ..core.errors import RiskManagerError

logger = structlog.get_logger(__name__)

class AccountAnchors:
    """Account anchor data for MLL calculations"""
    
    def __init__(self, account_id: int):
        self.account_id = account_id
        self.starting_balance: float = 0.0  # Original account starting balance
        self.eod_high_anchor: float = 0.0   # Prior day's EOD high (including unrealized)
        self.intraday_high_today: Optional[float] = None  # Today's intraday high (resets daily)
        self.last_rollover_date: Optional[str] = None  # Last rollover date (YYYY-MM-DD)
        self.locked_out: bool = False  # Whether account is locked out
    
    def set_starting_balance(self, balance: float) -> None:
        """Set the starting balance (only once)"""
        if self.starting_balance == 0.0:  # Only set if not already set
            self.starting_balance = balance
            logger.info("Set starting balance", 
                       account_id=self.account_id, 
                       starting_balance=balance)
    
    def update_eod_high_anchor(self, balance: float) -> None:
        """Update EOD high anchor if current balance is higher"""
        if balance > self.eod_high_anchor:
            old_anchor = self.eod_high_anchor
            self.eod_high_anchor = balance
            logger.info("Updated EOD high anchor", 
                       account_id=self.account_id, 
                       old_anchor=old_anchor,
                       new_anchor=balance)
    
    def update_intraday_high(self, equity: float) -> None:
        """Update today's intraday high with current equity"""
        if self.intraday_high_today is None or equity > self.intraday_high_today:
            old_high = self.intraday_high_today
            self.intraday_high_today = equity
            if old_high is not None:
                logger.debug("Updated intraday high", 
                           account_id=self.account_id,
                           old_high=old_high,
                           new_high=equity)
    
    def reset_intraday_high(self) -> None:
        """Reset intraday high for new trading day"""
        self.intraday_high_today = None
        logger.debug("Reset intraday high", account_id=self.account_id)
    
    def set_locked_out(self, locked: bool) -> None:
        """Set lockout status"""
        self.locked_out = locked
        logger.info("Set lockout status", 
                   account_id=self.account_id, 
                   locked_out=locked)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "account_id": self.account_id,
            "starting_balance": self.starting_balance,
            "eod_high_anchor": self.eod_high_anchor,
            "intraday_high_today": self.intraday_high_today,
            "last_rollover_date": self.last_rollover_date,
            "locked_out": self.locked_out
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AccountAnchors':
        """Create from dictionary"""
        anchors = cls(data["account_id"])
        anchors.starting_balance = data.get("starting_balance", 0.0)
        anchors.eod_high_anchor = data.get("eod_high_anchor", 0.0)
        anchors.intraday_high_today = data.get("intraday_high_today")
        anchors.last_rollover_date = data.get("last_rollover_date")
        anchors.locked_out = data.get("locked_out", False)
        return anchors

class AnchorsStore:
    """Persistent storage for account anchors"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.anchors_file = self.data_dir / "anchors.json"
        self._anchors: Dict[int, AccountAnchors] = {}
        self._load_anchors()
    
    def _load_anchors(self) -> None:
        """Load anchors from disk"""
        try:
            if self.anchors_file.exists():
                with open(self.anchors_file, 'r') as f:
                    data = json.load(f)
                    self._anchors = {
                        int(account_id): AccountAnchors.from_dict(anchor_data)
                        for account_id, anchor_data in data.items()
                    }
                logger.info("Loaded anchors from disk", account_count=len(self._anchors))
            else:
                logger.info("No anchors file found, starting fresh")
        except Exception as e:
            logger.error("Failed to load anchors", error=str(e))
            # Continue with empty anchors rather than failing
    
    def _save_anchors(self) -> None:
        """Save anchors to disk"""
        try:
            data = {
                str(account_id): anchors.to_dict()
                for account_id, anchors in self._anchors.items()
            }
            with open(self.anchors_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.debug("Saved anchors to disk", account_count=len(self._anchors))
        except Exception as e:
            logger.error("Failed to save anchors", error=str(e))
            raise RiskManagerError(f"Failed to save anchors: {e}")
    
    def get_anchors(self, account_id: int) -> AccountAnchors:
        """Get anchors for an account, create if doesn't exist"""
        if account_id not in self._anchors:
            self._anchors[account_id] = AccountAnchors(account_id)
            logger.info("Created new anchors", account_id=account_id)
        return self._anchors[account_id]
    
    def set_starting_balance(self, account_id: int, balance: float) -> None:
        """Set starting balance for an account"""
        anchors = self.get_anchors(account_id)
        anchors.set_starting_balance(balance)
        self._save_anchors()
    
    def update_eod_high_anchor(self, account_id: int, balance: float) -> None:
        """Update EOD high anchor for an account"""
        anchors = self.get_anchors(account_id)
        anchors.update_eod_high_anchor(balance)
        self._save_anchors()
    
    def update_intraday_high(self, account_id: int, equity: float) -> None:
        """Update intraday high for an account"""
        anchors = self.get_anchors(account_id)
        anchors.update_intraday_high(equity)
        self._save_anchors()
    
    def get_starting_balance(self, account_id: int) -> float:
        """Get starting balance for an account"""
        anchors = self.get_anchors(account_id)
        return anchors.starting_balance
    
    def get_eod_high_anchor(self, account_id: int) -> float:
        """Get EOD high anchor for an account"""
        anchors = self.get_anchors(account_id)
        return anchors.eod_high_anchor
    
    def get_intraday_high_today(self, account_id: int) -> Optional[float]:
        """Get today's intraday high for an account"""
        anchors = self.get_anchors(account_id)
        return anchors.intraday_high_today
    
    def is_locked_out(self, account_id: int) -> bool:
        """Check if account is locked out"""
        anchors = self.get_anchors(account_id)
        return anchors.locked_out
    
    def set_locked_out(self, account_id: int, locked: bool) -> None:
        """Set lockout status for an account"""
        anchors = self.get_anchors(account_id)
        anchors.set_locked_out(locked)
        self._save_anchors()
    
    def is_rollover_needed(self, account_id: int) -> bool:
        """Check if rollover is needed for an account"""
        anchors = self.get_anchors(account_id)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return anchors.last_rollover_date != today
    
    def perform_rollover(self, account_id: int, current_equity: float) -> None:
        """Perform rollover for an account at 17:00 CT"""
        anchors = self.get_anchors(account_id)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        # Update EOD high anchor with today's intraday high (or current equity if no intraday high)
        intraday_high = anchors.intraday_high_today or current_equity
        anchors.update_eod_high_anchor(intraday_high)
        
        # Reset intraday high for new day
        anchors.reset_intraday_high()
        
        # Clear lockout
        anchors.set_locked_out(False)
        
        # Update rollover date
        anchors.last_rollover_date = today
        
        # Save to disk
        self._save_anchors()
        
        logger.info("Performed rollover", 
                   account_id=account_id,
                   eod_high_anchor=anchors.eod_high_anchor,
                   intraday_high_used=intraday_high,
                   rollover_date=today)
    
    def get_all_account_ids(self) -> list[int]:
        """Get all account IDs that have anchors"""
        return list(self._anchors.keys())

