"""
Portfolio Engine for Risk Manager V6

HIDDEN NOTES FOR AI REFERENCE:
- ALWAYS CROSS REFERENCE TO DOCS FOR PROPER API REFERENCING
- CHECK TOPSTEP PROGRAM RULES DOCUMENTATION FOR HELPFUL INFO
- Portfolio engine aggregates P&L data across all accounts
- Provides portfolio-level risk analysis and decision making
- Combines results from all individual account engines
"""

import structlog
from typing import List, Dict, Any
from datetime import datetime, timezone
from dataclasses import dataclass
from .realized_pnl import RealizedPnLResult
from .unrealized_pnl import UnrealizedPnLResult
from .total_pnl import TotalPnLResult

logger = structlog.get_logger(__name__)


@dataclass
class PortfolioResult:
    """Result of portfolio-level calculation"""
    total_equity: float
    total_balance: float
    total_realized_pnl: float
    total_unrealized_pnl: float
    total_pnl: float
    total_fees: float
    total_completed_trades: int
    total_open_positions: int
    account_count: int
    date: datetime
    status: str  # PROFIT, LOSS, BREAKEVEN
    
    def __post_init__(self):
        """Set status based on total portfolio P&L"""
        if self.total_pnl > 0.01:  # Small epsilon to avoid rounding issues
            self.status = "PROFIT"
        elif self.total_pnl < -0.01:
            self.status = "LOSS"
        else:
            self.status = "BREAKEVEN"


class PortfolioEngine:
    """Dedicated engine for portfolio-level calculations and analysis"""
    
    def __init__(self):
        self.logger = structlog.get_logger(__name__)
    
    def calculate_portfolio_summary(self,
                                  account_results: List[Dict[str, Any]]) -> PortfolioResult:
        """
        Calculate portfolio-level summary from individual account results
        
        Args:
            account_results: List of dictionaries containing account P&L results
            
        Returns:
            PortfolioResult with portfolio-level data
        """
        try:
            total_equity = 0.0
            total_balance = 0.0
            total_realized_pnl = 0.0
            total_unrealized_pnl = 0.0
            total_fees = 0.0
            total_completed_trades = 0
            total_open_positions = 0
            
            for account_data in account_results:
                # Sum up account balances and equity
                total_equity += account_data.get("equity", 0.0)
                total_balance += account_data.get("balance", 0.0)
                
                # Sum up P&L components
                realized_result = account_data.get("realized_result")
                if realized_result:
                    total_realized_pnl += realized_result.realized_pnl
                    total_fees += realized_result.total_fees
                    total_completed_trades += realized_result.completed_trades
                
                unrealized_result = account_data.get("unrealized_result")
                if unrealized_result:
                    total_unrealized_pnl += unrealized_result.unrealized_pnl
                    total_open_positions += unrealized_result.open_positions
            
            # Calculate total P&L
            total_pnl = total_realized_pnl + total_unrealized_pnl
            
            result = PortfolioResult(
                total_equity=total_equity,
                total_balance=total_balance,
                total_realized_pnl=total_realized_pnl,
                total_unrealized_pnl=total_unrealized_pnl,
                total_pnl=total_pnl,
                total_fees=total_fees,
                total_completed_trades=total_completed_trades,
                total_open_positions=total_open_positions,
                account_count=len(account_results),
                date=datetime.now(timezone.utc),
                status="BREAKEVEN"  # Will be set by __post_init__
            )
            
            self.logger.info("Portfolio summary calculated",
                           total_equity=total_equity,
                           total_balance=total_balance,
                           total_realized_pnl=total_realized_pnl,
                           total_unrealized_pnl=total_unrealized_pnl,
                           total_pnl=total_pnl,
                           account_count=len(account_results))
            
            return result
            
        except Exception as e:
            self.logger.error("Failed to calculate portfolio summary", error=str(e))
            raise
    
    def get_portfolio_warning_level(self, result: PortfolioResult) -> str:
        """
        Get warning level based on portfolio result
        
        Args:
            result: Portfolio result to evaluate
            
        Returns:
            Warning level: NORMAL, WARNING, CRITICAL
        """
        if result.total_pnl < -5000:  # $5000 portfolio loss limit
            return "CRITICAL"
        elif result.total_pnl < -2000:
            return "WARNING"
        else:
            return "NORMAL"
    
    def get_risk_assessment(self, result: PortfolioResult) -> Dict[str, Any]:
        """
        Get comprehensive risk assessment for the portfolio
        
        Args:
            result: Portfolio result to assess
            
        Returns:
            Dictionary with risk assessment data
        """
        try:
            assessment = {
                "overall_status": result.status,
                "warning_level": self.get_portfolio_warning_level(result),
                "risk_factors": []
            }
            
            # Check for risk factors
            if result.total_realized_pnl < -1000:
                assessment["risk_factors"].append("Significant realized losses")
            
            if result.total_unrealized_pnl < -2000:
                assessment["risk_factors"].append("Large unrealized losses")
            
            if result.total_pnl < -3000:
                assessment["risk_factors"].append("Total portfolio losses")
            
            if result.total_open_positions > 10:
                assessment["risk_factors"].append("High number of open positions")
            
            if not assessment["risk_factors"]:
                assessment["risk_factors"].append("Normal risk levels")
            
            self.logger.info("Portfolio risk assessment completed",
                           assessment=assessment)
            
            return assessment
            
        except Exception as e:
            self.logger.error("Failed to generate risk assessment", error=str(e))
            raise
    
    def format_portfolio_display(self, result: PortfolioResult) -> str:
        """
        Format portfolio result for display
        
        Args:
            result: Portfolio result to format
            
        Returns:
            Formatted string for display
        """
        return f"Portfolio P&L: ${result.total_pnl:,.2f}"
