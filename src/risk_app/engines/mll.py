"""MLL (Maximum Loss Limit) engine for Risk Manager V6"""
from typing import Dict, Any, Optional
from enum import Enum
import structlog
from ..core.errors import RiskManagerError

logger = structlog.get_logger(__name__)

class MLLStatus(Enum):
    """MLL status enumeration"""
    ALIVE = "ALIVE"
    BLOWN = "BLOWN"
    UNKNOWN = "UNKNOWN"

class MLLResult:
    """Result of MLL calculation"""
    
    def __init__(self, 
                 account_id: int,
                 plan_size: str,
                 starting_balance: float,
                 eod_high_anchor: float,
                 base_mll: float,
                 current_equity: float,
                 floor: Optional[float],
                 used: Optional[float],
                 remaining: Optional[float],
                 pct_used: Optional[float],
                 status: MLLStatus,
                 reason: str):
        self.account_id = account_id
        self.plan_size = plan_size
        self.starting_balance = starting_balance
        self.eod_high_anchor = eod_high_anchor
        self.base_mll = base_mll
        self.current_equity = current_equity
        self.floor = floor
        self.used = used
        self.remaining = remaining
        self.pct_used = pct_used
        self.status = status
        self.reason = reason
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/serialization"""
        return {
            "account_id": self.account_id,
            "plan_size": self.plan_size,
            "starting_balance": self.starting_balance,
            "eod_high_anchor": self.eod_high_anchor,
            "base_mll": self.base_mll,
            "current_equity": self.current_equity,
            "floor": self.floor,
            "used": self.used,
            "remaining": self.remaining,
            "pct_used": self.pct_used,
            "status": self.status.value,
            "reason": self.reason
        }

class MLLEngine:
    """Maximum Loss Limit calculation engine"""
    
    # MLL limits by account type (from Topstep documentation)
    MLL_LIMITS = {
        50000: 2000,   # $50K account: $2,000 MLL
        100000: 3000,  # $100K account: $3,000 MLL
        150000: 4500   # $150K account: $4,500 MLL
    }
    
    def __init__(self):
        self.logger = structlog.get_logger(__name__)
    
    def get_plan_size(self, starting_balance: float) -> str:
        """Get plan size based on starting balance"""
        if starting_balance <= 50000:
            return "50K"
        elif starting_balance <= 100000:
            return "100K"
        else:
            return "150K"
    
    def get_base_mll(self, starting_balance: float) -> float:
        """Get base MLL for starting balance"""
        # Determine account type based on starting balance
        if starting_balance <= 50000:
            return self.MLL_LIMITS[50000]
        elif starting_balance <= 100000:
            return self.MLL_LIMITS[100000]
        else:
            return self.MLL_LIMITS[150000]
    
    def calculate_mll(self, 
                     account_id: int,
                     starting_balance: float,
                     eod_high_anchor: float,
                     current_equity: float) -> MLLResult:
        """
        Calculate MLL for an account
        
        Args:
            account_id: Account ID
            starting_balance: Original account starting balance
            eod_high_anchor: Prior day's EOD high (including unrealized)
            current_equity: Current account equity (net liquidation)
            
        Returns:
            MLLResult with floor, used, remaining, pct_used, status, and reason
        """
        try:
            # Get plan size and base MLL
            plan_size = self.get_plan_size(starting_balance)
            base_mll = self.get_base_mll(starting_balance)
            
            # Check if we have a valid EOD high anchor
            if eod_high_anchor <= 0:
                return MLLResult(
                    account_id=account_id,
                    plan_size=plan_size,
                    starting_balance=starting_balance,
                    eod_high_anchor=eod_high_anchor,
                    base_mll=base_mll,
                    current_equity=current_equity,
                    floor=None,
                    used=None,
                    remaining=None,
                    pct_used=None,
                    status=MLLStatus.UNKNOWN,
                    reason="missing_anchor"
                )
            
            # Calculate raw floor
            raw_floor = eod_high_anchor - base_mll
            
            # Apply freeze at starting balance
            floor = min(starting_balance, raw_floor)
            
            # Calculate how much loss has been used
            used = eod_high_anchor - current_equity
            
            # Calculate remaining loss allowance
            remaining = base_mll - used
            
            # Calculate percentage used
            pct_used = (used / base_mll) * 100 if base_mll > 0 else 0
            
            # Determine status with small epsilon to avoid rounding issues
            epsilon = 0.01
            if current_equity <= (floor + epsilon):
                status = MLLStatus.BLOWN
                reason = "mll_blown"
            else:
                status = MLLStatus.ALIVE
                reason = "within_limits"
            
            result = MLLResult(
                account_id=account_id,
                plan_size=plan_size,
                starting_balance=starting_balance,
                eod_high_anchor=eod_high_anchor,
                base_mll=base_mll,
                current_equity=current_equity,
                floor=floor,
                used=used,
                remaining=remaining,
                pct_used=pct_used,
                status=status,
                reason=reason
            )
            
            self.logger.info("MLL calculation completed", 
                           account_id=account_id,
                           plan_size=plan_size,
                           starting_balance=starting_balance,
                           eod_high_anchor=eod_high_anchor,
                           base_mll=base_mll,
                           floor=floor,
                           used=used,
                           remaining=remaining,
                           pct_used=pct_used,
                           status=status.value,
                           reason=reason)
            
            return result
            
        except Exception as e:
            self.logger.error("MLL calculation failed", 
                             account_id=account_id,
                             error=str(e))
            raise RiskManagerError(f"MLL calculation failed: {e}")
    
    def is_blown(self, result: MLLResult) -> bool:
        """Check if account is blown (MLL violated)"""
        return result.status == MLLStatus.BLOWN
    
    def is_unknown(self, result: MLLResult) -> bool:
        """Check if account status is unknown (missing anchor)"""
        return result.status == MLLStatus.UNKNOWN
    
    def get_warning_level(self, result: MLLResult) -> Optional[str]:
        """Get warning level based on MLL usage"""
        if result.pct_used is None:
            return None
            
        if result.pct_used >= 95:
            return "CRITICAL"
        elif result.pct_used >= 90:
            return "HIGH"
        elif result.pct_used >= 80:
            return "MEDIUM"
        elif result.pct_used >= 70:
            return "LOW"
        else:
            return None

