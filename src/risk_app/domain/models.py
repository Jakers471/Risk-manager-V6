"""Domain models for Risk Manager V6"""
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

class Account(BaseModel):
    """Account model"""
    id: int = Field(..., description="Account ID")
    name: str = Field(..., description="Account name")
    balance: float = Field(..., description="Account balance")
    can_trade: bool = Field(..., alias="canTrade", description="Whether account can trade")
    is_visible: bool = Field(..., alias="isVisible", description="Whether account is visible")
    simulated: bool = Field(..., description="Whether this is a simulated account")
    
    # Optional fields that may not be present in all responses
    status: Optional[str] = Field(None, description="Account status (Active, Inactive, etc.)")
    equity: Optional[float] = Field(None, description="Account equity (balance + unrealized P&L)")
    margin: Optional[float] = Field(None, description="Used margin")
    free_margin: Optional[float] = Field(None, alias="freeMargin", description="Free margin")
    
    @property
    def is_active(self) -> bool:
        """Check if account is active"""
        if self.status:
            return self.status.lower() == "active"
        return self.can_trade  # Fallback to can_trade if status not available
    
    @property
    def unrealized_pnl(self) -> float:
        """Calculate unrealized P&L"""
        if self.equity is not None:
            return self.equity - self.balance
        return 0.0  # Default to 0 if equity not available
    
    @property
    def display_equity(self) -> float:
        """Get equity value, fallback to balance if not available"""
        return self.equity if self.equity is not None else self.balance

class RiskSnapshot(BaseModel):
    """Risk snapshot for an account"""
    account_id: int
    timestamp: datetime
    balance: float
    equity: float
    unrealized_pnl: float
    margin_used: float
    free_margin: float
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class AuthToken(BaseModel):
    """Authentication token model"""
    token: str
    expires_at: datetime
    is_valid: bool = True
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

