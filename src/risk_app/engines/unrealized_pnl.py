"""
Unrealized P&L Engine for Risk Manager V6

HIDDEN NOTES FOR AI REFERENCE:
- ALWAYS CROSS REFERENCE TO DOCS FOR PROPER API REFERENCING
- CHECK TOPSTEP PROGRAM RULES DOCUMENTATION FOR HELPFUL INFO
- UP&L = Unrealized P&L: The potential profit or loss on your open positions, based on the current market price
- Positions API: POST /api/Position/searchOpen for open positions
- Position fields: id, accountId, contractId, creationTimestamp, type, size, averagePrice
- Need current market price vs average entry price for accurate UP&L calculation
"""

import structlog
from typing import List, Dict, Any
from datetime import datetime, timezone
from dataclasses import dataclass

logger = structlog.get_logger(__name__)


@dataclass
class UnrealizedPnLResult:
    """Result of unrealized P&L calculation"""
    account_id: int
    account_name: str
    unrealized_pnl: float
    open_positions: int
    total_size: int
    long_positions: int
    short_positions: int
    date: datetime
    status: str  # PROFIT, LOSS, BREAKEVEN
    
    def __post_init__(self):
        """Set status based on unrealized P&L"""
        if self.unrealized_pnl > 0.01:  # Small epsilon to avoid rounding issues
            self.status = "PROFIT"
        elif self.unrealized_pnl < -0.01:
            self.status = "LOSS"
        else:
            self.status = "BREAKEVEN"


class UnrealizedPnLEngine:
    """Dedicated engine for calculating unrealized P&L from open positions"""
    
    def __init__(self):
        self.logger = structlog.get_logger(__name__)
    
    def calculate_unrealized_pnl(self,
                                account_id: int,
                                account_name: str,
                                positions_data: List[Dict[str, Any]]) -> UnrealizedPnLResult:
        """
        Calculate unrealized P&L from open positions
        
        Args:
            account_id: Account ID
            account_name: Account name
            positions_data: List of position dictionaries from API
            
        Returns:
            UnrealizedPnLResult with unrealized P&L data
        """
        try:
            total_upnl = 0.0
            open_positions = 0
            total_size = 0
            long_positions = 0
            short_positions = 0
            
            for position in positions_data:
                # Calculate unrealized P&L for each open position
                # This would require current market price vs average entry price
                # For now, we'll use a simplified calculation
                # In a real implementation, you'd need market data
                
                size = position.get("size", 0)
                avg_price = position.get("averagePrice", 0.0)
                position_type = position.get("type")  # 0 = long, 1 = short
                
                total_size += abs(size)
                
                if position_type == 0:
                    long_positions += 1
                elif position_type == 1:
                    short_positions += 1
                
                # Simplified calculation - in reality you'd need current market price
                # For now, we'll estimate based on position size and average price
                # This is a placeholder - actual UP&L requires real-time market data
                
                open_positions += 1
            
            # For now, return 0 since we don't have real-time market data
            # In a real implementation, you'd calculate: (current_price - avg_price) * size
            total_upnl = 0.0
            
            result = UnrealizedPnLResult(
                account_id=account_id,
                account_name=account_name,
                unrealized_pnl=total_upnl,
                open_positions=open_positions,
                total_size=total_size,
                long_positions=long_positions,
                short_positions=short_positions,
                date=datetime.now(timezone.utc),
                status="BREAKEVEN"  # Will be set by __post_init__
            )
            
            self.logger.info("Unrealized P&L calculated",
                           account_id=account_id,
                           account_name=account_name,
                           unrealized_pnl=total_upnl,
                           open_positions=open_positions,
                           total_size=total_size)
            
            return result
            
        except Exception as e:
            self.logger.error("Failed to calculate unrealized P&L",
                            account_id=account_id,
                            error=str(e))
            raise
    
    def get_warning_level(self, result: UnrealizedPnLResult) -> str:
        """
        Get warning level based on unrealized P&L result
        
        Args:
            result: Unrealized P&L result to evaluate
            
        Returns:
            Warning level: NORMAL, WARNING, CRITICAL
        """
        if result.unrealized_pnl < -2000:  # $2000 position loss limit
            return "CRITICAL"
        elif result.unrealized_pnl < -1000:
            return "WARNING"
        else:
            return "NORMAL"
    
    def format_display(self, result: UnrealizedPnLResult) -> str:
        """
        Format unrealized P&L result for display
        
        Args:
            result: Unrealized P&L result to format
            
        Returns:
            Formatted string for display
        """
        return f"UP&L: ${result.unrealized_pnl:,.2f}"
