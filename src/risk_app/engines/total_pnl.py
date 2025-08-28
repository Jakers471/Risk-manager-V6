"""
Total P&L Engine for Risk Manager V6

HIDDEN NOTES FOR AI REFERENCE:
- ALWAYS CROSS REFERENCE TO DOCS FOR PROPER API REFERENCING
- CHECK TOPSTEP PROGRAM RULES DOCUMENTATION FOR HELPFUL INFO
- Total P&L = Realized P&L + Unrealized P&L
- Combines results from RealizedPnLEngine and UnrealizedPnLEngine
- Provides portfolio-level P&L analysis
"""

import structlog
from typing import Dict, Any
from datetime import datetime, timezone
from dataclasses import dataclass
from .realized_pnl import RealizedPnLResult
from .unrealized_pnl import UnrealizedPnLResult

logger = structlog.get_logger(__name__)


@dataclass
class TotalPnLResult:
    """Result of total P&L calculation"""
    account_id: int
    account_name: str
    total_pnl: float
    realized_pnl: float
    unrealized_pnl: float
    total_fees: float
    completed_trades: int
    open_positions: int
    date: datetime
    status: str  # PROFIT, LOSS, BREAKEVEN
    
    def __post_init__(self):
        """Set status based on total P&L"""
        if self.total_pnl > 0.01:  # Small epsilon to avoid rounding issues
            self.status = "PROFIT"
        elif self.total_pnl < -0.01:
            self.status = "LOSS"
        else:
            self.status = "BREAKEVEN"


class TotalPnLEngine:
    """Dedicated engine for calculating total P&L from realized and unrealized components"""
    
    def __init__(self):
        self.logger = structlog.get_logger(__name__)
    
    def calculate_total_pnl(self,
                           realized_result: RealizedPnLResult,
                           unrealized_result: UnrealizedPnLResult) -> TotalPnLResult:
        """
        Calculate total P&L from realized and unrealized components
        
        Args:
            realized_result: Realized P&L result
            unrealized_result: Unrealized P&L result
            
        Returns:
            TotalPnLResult with total P&L data
        """
        try:
            total_pnl = realized_result.realized_pnl + unrealized_result.unrealized_pnl
            
            result = TotalPnLResult(
                account_id=realized_result.account_id,
                account_name=realized_result.account_name,
                total_pnl=total_pnl,
                realized_pnl=realized_result.realized_pnl,
                unrealized_pnl=unrealized_result.unrealized_pnl,
                total_fees=realized_result.total_fees,
                completed_trades=realized_result.completed_trades,
                open_positions=unrealized_result.open_positions,
                date=datetime.now(timezone.utc),
                status="BREAKEVEN"  # Will be set by __post_init__
            )
            
            self.logger.info("Total P&L calculated",
                           account_id=realized_result.account_id,
                           account_name=realized_result.account_name,
                           total_pnl=total_pnl,
                           realized_pnl=realized_result.realized_pnl,
                           unrealized_pnl=unrealized_result.unrealized_pnl)
            
            return result
            
        except Exception as e:
            self.logger.error("Failed to calculate total P&L",
                            account_id=realized_result.account_id,
                            error=str(e))
            raise
    
    def get_warning_level(self, result: TotalPnLResult) -> str:
        """
        Get warning level based on total P&L result
        
        Args:
            result: Total P&L result to evaluate
            
        Returns:
            Warning level: NORMAL, WARNING, CRITICAL
        """
        if result.total_pnl < -2000:  # $2000 total loss limit
            return "CRITICAL"
        elif result.total_pnl < -1000:
            return "WARNING"
        else:
            return "NORMAL"
    
    def format_display(self, result: TotalPnLResult) -> str:
        """
        Format total P&L result for display
        
        Args:
            result: Total P&L result to format
            
        Returns:
            Formatted string for display
        """
        return f"Total P&L: ${result.total_pnl:,.2f}"
