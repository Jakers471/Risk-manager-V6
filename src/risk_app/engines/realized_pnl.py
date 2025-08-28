"""
Realized P&L Engine for Risk Manager V6

HIDDEN NOTES FOR AI REFERENCE:
- ALWAYS CROSS REFERENCE TO DOCS FOR PROPER API REFERENCING
- CHECK TOPSTEP PROGRAM RULES DOCUMENTATION FOR HELPFUL INFO
- RP&L = Realized Day P&L: The actual profit or loss from positions you've closed for the trading day
- Trades API provides: profitAndLoss, fees, side, size, voided
- Only count trades with non-null profitAndLoss (completed trades)
- null profitAndLoss indicates a half-turn trade (open position)
- Calculate net P&L after fees
"""

import structlog
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from dataclasses import dataclass

logger = structlog.get_logger(__name__)


@dataclass
class RealizedPnLResult:
    """Result of realized P&L calculation"""
    account_id: int
    account_name: str
    realized_pnl: float
    net_pnl: float  # After fees
    total_fees: float
    completed_trades: int
    open_trades: int
    total_trades: int
    date: datetime
    status: str  # PROFIT, LOSS, BREAKEVEN
    
    def __post_init__(self):
        """Set status based on realized P&L"""
        if self.realized_pnl > 0.01:  # Small epsilon to avoid rounding issues
            self.status = "PROFIT"
        elif self.realized_pnl < -0.01:
            self.status = "LOSS"
        else:
            self.status = "BREAKEVEN"


class RealizedPnLEngine:
    """Dedicated engine for calculating realized P&L from completed trades"""
    
    def __init__(self):
        self.logger = structlog.get_logger(__name__)
    
    def calculate_realized_pnl(self, 
                              account_id: int,
                              account_name: str,
                              trades_data: List[Dict[str, Any]],
                              date: Optional[datetime] = None) -> RealizedPnLResult:
        """
        Calculate realized P&L from completed trades (trades with non-null profitAndLoss)
        
        Args:
            account_id: Account ID
            account_name: Account name
            trades_data: List of trade dictionaries from API
            date: Date for calculation (defaults to today)
            
        Returns:
            RealizedPnLResult with realized P&L data
        """
        try:
            total_rpnl = 0.0
            total_fees = 0.0
            completed_trades = 0
            open_trades = 0
            
            for trade in trades_data:
                # Skip voided trades
                if trade.get("voided", False):
                    continue
                
                # Count fees
                fees = trade.get("fees", 0.0)
                total_fees += fees
                
                # Only count trades with non-null profitAndLoss (completed trades)
                # null profitAndLoss indicates a half-turn trade (open position)
                profit_loss = trade.get("profitAndLoss")
                if profit_loss is not None:
                    total_rpnl += profit_loss
                    completed_trades += 1
                else:
                    open_trades += 1
            
            # Calculate net P&L after fees
            net_pnl = total_rpnl - total_fees
            
            result = RealizedPnLResult(
                account_id=account_id,
                account_name=account_name,
                realized_pnl=total_rpnl,
                net_pnl=net_pnl,
                total_fees=total_fees,
                completed_trades=completed_trades,
                open_trades=open_trades,
                total_trades=len(trades_data),
                date=date or datetime.now(timezone.utc),
                status="BREAKEVEN"  # Will be set by __post_init__
            )
            
            self.logger.info("Realized P&L calculated",
                           account_id=account_id,
                           account_name=account_name,
                           realized_pnl=total_rpnl,
                           net_pnl=net_pnl,
                           completed_trades=completed_trades,
                           total_trades=len(trades_data))
            
            return result
            
        except Exception as e:
            self.logger.error("Failed to calculate realized P&L",
                            account_id=account_id,
                            error=str(e))
            raise
    
    def get_warning_level(self, result: RealizedPnLResult) -> str:
        """
        Get warning level based on realized P&L result
        
        Args:
            result: Realized P&L result to evaluate
            
        Returns:
            Warning level: NORMAL, WARNING, CRITICAL
        """
        if result.realized_pnl < -1000:  # $1000 daily loss limit
            return "CRITICAL"
        elif result.realized_pnl < -500:
            return "WARNING"
        else:
            return "NORMAL"
    
    def format_display(self, result: RealizedPnLResult) -> str:
        """
        Format realized P&L result for display
        
        Args:
            result: Realized P&L result to format
            
        Returns:
            Formatted string for display
        """
        return f"RP&L: ${result.realized_pnl:,.2f}"
