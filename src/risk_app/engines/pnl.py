"""
P&L Engine for Risk Manager V6

HIDDEN NOTES FOR AI REFERENCE:
- ALWAYS CROSS REFERENCE TO DOCS FOR PROPER API REFERENCING
- CHECK TOPSTEP PROGRAM RULES DOCUMENTATION FOR HELPFUL INFO
- RP&L = Realized Day P&L: The actual profit or loss from positions you've closed for the trading day
- UP&L = Unrealized P&L: The potential profit or loss on your open positions, based on the current market price
- Account API provides: balance, canTrade, isVisible, simulated
- Trades API provides: profitAndLoss, fees, side, size, voided (null profitAndLoss = open position)
- Positions API: POST /api/Position/searchOpen for open positions
- Need to calculate realized P&L from completed trades (non-null profitAndLoss)
- Need to calculate unrealized P&L from open positions (current market value vs entry price)
"""

import structlog
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum

logger = structlog.get_logger(__name__)


class PnLType(Enum):
    """Types of P&L calculations"""
    REALIZED = "realized"
    UNREALIZED = "unrealized"
    TOTAL = "total"


@dataclass
class PnLResult:
    """Result of P&L calculation"""
    account_id: int
    account_name: str
    pnl_type: PnLType
    amount: float
    currency: str = "USD"
    date: Optional[datetime] = None
    trade_count: int = 0
    completed_trades: int = 0
    open_trades: int = 0
    total_fees: float = 0.0
    net_amount: float = 0.0  # After fees
    status: str = "UNKNOWN"  # PROFIT, LOSS, BREAKEVEN
    
    def __post_init__(self):
        """Set status based on amount"""
        if self.amount > 0.01:  # Small epsilon to avoid rounding issues
            self.status = "PROFIT"
        elif self.amount < -0.01:
            self.status = "LOSS"
        else:
            self.status = "BREAKEVEN"
        
        # Calculate net amount (after fees)
        self.net_amount = self.amount - self.total_fees


class PnLEngine:
    """Comprehensive P&L calculation engine"""
    
    def __init__(self):
        self.logger = structlog.get_logger(__name__)
    
    def calculate_realized_pnl(self, 
                              account_id: int,
                              account_name: str,
                              trades_data: List[Dict[str, Any]],
                              date: Optional[datetime] = None) -> PnLResult:
        """
        Calculate realized P&L from completed trades (trades with non-null profitAndLoss)
        
        Args:
            account_id: Account ID
            account_name: Account name
            trades_data: List of trade dictionaries from API
            date: Date for calculation (defaults to today)
            
        Returns:
            PnLResult with realized P&L data
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
            
            result = PnLResult(
                account_id=account_id,
                account_name=account_name,
                pnl_type=PnLType.REALIZED,
                amount=total_rpnl,
                date=date or datetime.now(timezone.utc),
                trade_count=len(trades_data),
                completed_trades=completed_trades,
                open_trades=open_trades,
                total_fees=total_fees
            )
            
            self.logger.info("Realized P&L calculated",
                           account_id=account_id,
                           account_name=account_name,
                           realized_pnl=total_rpnl,
                           net_pnl=result.net_amount,
                           completed_trades=completed_trades,
                           total_trades=len(trades_data))
            
            return result
            
        except Exception as e:
            self.logger.error("Failed to calculate realized P&L",
                            account_id=account_id,
                            error=str(e))
            raise
    
    def calculate_unrealized_pnl(self,
                                account_id: int,
                                account_name: str,
                                positions_data: List[Dict[str, Any]]) -> PnLResult:
        """
        Calculate unrealized P&L from open positions
        
        Args:
            account_id: Account ID
            account_name: Account name
            positions_data: List of position dictionaries from API
            
        Returns:
            PnLResult with unrealized P&L data
        """
        try:
            total_upnl = 0.0
            open_positions = 0
            
            for position in positions_data:
                # Calculate unrealized P&L for each open position
                # This would require current market price vs average entry price
                # For now, we'll use a simplified calculation
                # In a real implementation, you'd need market data
                
                size = position.get("size", 0)
                avg_price = position.get("averagePrice", 0.0)
                
                # Simplified calculation - in reality you'd need current market price
                # For now, we'll estimate based on position size and average price
                # This is a placeholder - actual UP&L requires real-time market data
                
                open_positions += 1
            
            # For now, return 0 since we don't have real-time market data
            # In a real implementation, you'd calculate: (current_price - avg_price) * size
            total_upnl = 0.0
            
            result = PnLResult(
                account_id=account_id,
                account_name=account_name,
                pnl_type=PnLType.UNREALIZED,
                amount=total_upnl,
                date=datetime.now(timezone.utc),
                open_trades=open_positions
            )
            
            self.logger.info("Unrealized P&L calculated",
                           account_id=account_id,
                           account_name=account_name,
                           unrealized_pnl=total_upnl,
                           open_positions=open_positions)
            
            return result
            
        except Exception as e:
            self.logger.error("Failed to calculate unrealized P&L",
                            account_id=account_id,
                            error=str(e))
            raise
    
    def calculate_total_pnl(self,
                           realized_result: PnLResult,
                           unrealized_result: PnLResult) -> PnLResult:
        """
        Calculate total P&L from realized and unrealized components
        
        Args:
            realized_result: Realized P&L result
            unrealized_result: Unrealized P&L result
            
        Returns:
            PnLResult with total P&L data
        """
        try:
            total_amount = realized_result.amount + unrealized_result.amount
            total_fees = realized_result.total_fees
            
            result = PnLResult(
                account_id=realized_result.account_id,
                account_name=realized_result.account_name,
                pnl_type=PnLType.TOTAL,
                amount=total_amount,
                date=datetime.now(timezone.utc),
                trade_count=realized_result.trade_count,
                completed_trades=realized_result.completed_trades,
                open_trades=realized_result.open_trades,
                total_fees=total_fees
            )
            
            self.logger.info("Total P&L calculated",
                           account_id=realized_result.account_id,
                           account_name=realized_result.account_name,
                           total_pnl=total_amount,
                           realized_pnl=realized_result.amount,
                           unrealized_pnl=unrealized_result.amount)
            
            return result
            
        except Exception as e:
            self.logger.error("Failed to calculate total P&L",
                            account_id=realized_result.account_id,
                            error=str(e))
            raise
    
    def get_pnl_summary(self,
                       account_id: int,
                       account_name: str,
                       trades_data: List[Dict[str, Any]],
                       positions_data: List[Dict[str, Any]],
                       date: Optional[datetime] = None) -> Dict[str, PnLResult]:
        """
        Get comprehensive P&L summary for an account
        
        Args:
            account_id: Account ID
            account_name: Account name
            trades_data: List of trade dictionaries from API
            positions_data: List of position dictionaries from API
            date: Date for calculation (defaults to today)
            
        Returns:
            Dictionary with realized, unrealized, and total P&L results
        """
        try:
            # Calculate realized P&L from completed trades
            realized_result = self.calculate_realized_pnl(
                account_id, account_name, trades_data, date
            )
            
            # Calculate unrealized P&L from open positions
            unrealized_result = self.calculate_unrealized_pnl(
                account_id, account_name, positions_data
            )
            
            # Calculate total P&L
            total_result = self.calculate_total_pnl(realized_result, unrealized_result)
            
            summary = {
                "realized": realized_result,
                "unrealized": unrealized_result,
                "total": total_result
            }
            
            self.logger.info("P&L summary generated",
                           account_id=account_id,
                           account_name=account_name,
                           summary=summary)
            
            return summary
            
        except Exception as e:
            self.logger.error("Failed to generate P&L summary",
                            account_id=account_id,
                            error=str(e))
            raise
    
    def format_pnl_display(self, pnl_result: PnLResult) -> str:
        """
        Format P&L result for display
        
        Args:
            pnl_result: P&L result to format
            
        Returns:
            Formatted string for display
        """
        if pnl_result.pnl_type == PnLType.REALIZED:
            prefix = "RP&L"
        elif pnl_result.pnl_type == PnLType.UNREALIZED:
            prefix = "UP&L"
        else:
            prefix = "Total P&L"
        
        return f"{prefix}: ${pnl_result.amount:,.2f}"
    
    def get_warning_level(self, pnl_result: PnLResult) -> str:
        """
        Get warning level based on P&L result
        
        Args:
            pnl_result: P&L result to evaluate
            
        Returns:
            Warning level: NORMAL, WARNING, CRITICAL
        """
        if pnl_result.pnl_type == PnLType.REALIZED:
            # For realized P&L, check against daily limits
            if pnl_result.amount < -1000:  # $1000 daily loss limit
                return "CRITICAL"
            elif pnl_result.amount < -500:
                return "WARNING"
            else:
                return "NORMAL"
        elif pnl_result.pnl_type == PnLType.UNREALIZED:
            # For unrealized P&L, check against position limits
            if pnl_result.amount < -2000:  # $2000 position loss limit
                return "CRITICAL"
            elif pnl_result.amount < -1000:
                return "WARNING"
            else:
                return "NORMAL"
        else:
            # For total P&L, use combined logic
            if pnl_result.amount < -2000:
                return "CRITICAL"
            elif pnl_result.amount < -1000:
                return "WARNING"
            else:
                return "NORMAL"

