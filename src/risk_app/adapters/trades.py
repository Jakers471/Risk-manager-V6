"""
Trades adapter for Risk Manager V6

HIDDEN NOTES FOR AI REFERENCE:
- ALWAYS CROSS REFERENCE TO DOCS FOR PROPER API REFERENCING
- CHECK TOPSTEP PROGRAM RULES DOCUMENTATION FOR HELPFUL INFO
- API endpoint: POST https://api.topstepx.com/api/Trade/search
- RP&L = Realized Day P&L: The actual profit or loss from positions you've closed for the trading day
- Use startTimestamp and endTimestamp to filter for current trading day
- profitAndLoss field contains the realized P&L for each trade
- null profitAndLoss indicates a half-turn trade (position still open)
- Timestamp format: "2025-01-20T15:47:39.882Z" (exact format required)
- Trading session: 08:30-17:00 Central Time (CT)
- Convert CT to UTC for API calls (CT = UTC-5 during CDT, UTC-6 during CST)
"""

import structlog
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import pytz
from .http import HTTPClient
from ..core.errors import APIError

logger = structlog.get_logger(__name__)


class TradesAdapter:
    """Handles trade-related API calls for RP&L calculations"""
    
    def __init__(self, http_client: HTTPClient):
        self.http_client = http_client
    
    def get_daily_trades(self, account_id: int, date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Get trades for a specific trading day
        
        Args:
            account_id: Account ID to fetch trades for
            date: Date to fetch trades for (defaults to today)
            
        Returns:
            List of trades with realized P&L data
        """
        try:
            # Use provided date or default to today
            if date is None:
                date = datetime.now(timezone.utc)
            
            # Create Central Time timezone
            central_tz = pytz.timezone('America/Chicago')
            
            # Create date in Central Time for trading session
            # Trading session: 08:30-17:00 CT
            ct_date = date.astimezone(central_tz).date()
            
            # Create start and end times in Central Time
            ct_start = central_tz.localize(datetime.combine(ct_date, datetime.min.time().replace(hour=8, minute=30)))
            ct_end = central_tz.localize(datetime.combine(ct_date, datetime.min.time().replace(hour=17, minute=0)))
            
            # Convert to UTC for API call
            utc_start = ct_start.astimezone(timezone.utc)
            utc_end = ct_end.astimezone(timezone.utc)
            
            # Format timestamps in the exact format expected by the API
            # Format: "2025-01-20T15:47:39.882Z"
            start_timestamp = utc_start.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
            end_timestamp = utc_end.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
            
            logger.info("Fetching daily trades", 
                       account_id=account_id,
                       date=ct_date,
                       session_ct="08:30-17:00",
                       session_utc=f"{utc_start.strftime('%H:%M')}-{utc_end.strftime('%H:%M')}Z",
                       start_timestamp=start_timestamp,
                       end_timestamp=end_timestamp)
            
            # Prepare request data
            request_data = {
                "accountId": account_id,
                "startTimestamp": start_timestamp,
                "endTimestamp": end_timestamp
            }
            
            # Make API call
            response = self.http_client.post("/api/Trade/search", request_data)
            
            # Validate response
            if not response.get("success"):
                error_msg = response.get("errorMessage", "Unknown error")
                logger.error("Trade search failed", error=error_msg)
                raise APIError(f"Trade search failed: {error_msg}")
            
            # Extract trades
            trades = response.get("trades", [])
            
            # Log diagnostic information
            if trades:
                first_trade = trades[0]
                last_trade = trades[-1]
                logger.info("Trade search successful", 
                           account_id=account_id,
                           trade_count=len(trades),
                           first_trade_time=first_trade.get("timestamp"),
                           last_trade_time=last_trade.get("timestamp"))
            else:
                logger.info("Trade search successful - no trades found", 
                           account_id=account_id,
                           trade_count=len(trades))
            
            return trades
            
        except Exception as e:
            logger.error("Failed to fetch daily trades", 
                        account_id=account_id,
                        error=str(e))
            raise APIError(f"Failed to fetch daily trades: {e}")
    
    def get_trades_wide_window(self, account_id: int, hours_back: int = 24) -> List[Dict[str, Any]]:
        """
        Get trades for a wider time window (for debugging)
        
        Args:
            account_id: Account ID to fetch trades for
            hours_back: Number of hours to look back
            
        Returns:
            List of trades with realized P&L data
        """
        try:
            # Create Central Time timezone
            central_tz = pytz.timezone('America/Chicago')
            
            # Get current time in UTC
            now_utc = datetime.now(timezone.utc)
            
            # Calculate start time (hours_back ago)
            start_utc = now_utc - timedelta(hours=hours_back)
            
            # Format timestamps
            start_timestamp = start_utc.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
            end_timestamp = now_utc.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
            
            logger.info("Fetching trades with wide window", 
                       account_id=account_id,
                       hours_back=hours_back,
                       start_timestamp=start_timestamp,
                       end_timestamp=end_timestamp)
            
            # Prepare request data
            request_data = {
                "accountId": account_id,
                "startTimestamp": start_timestamp,
                "endTimestamp": end_timestamp
            }
            
            # Make API call
            response = self.http_client.post("/api/Trade/search", request_data)
            
            # Validate response
            if not response.get("success"):
                error_msg = response.get("errorMessage", "Unknown error")
                logger.error("Trade search failed", error=error_msg)
                raise APIError(f"Trade search failed: {error_msg}")
            
            # Extract trades
            trades = response.get("trades", [])
            
            # Log diagnostic information
            if trades:
                first_trade = trades[0]
                last_trade = trades[-1]
                logger.info("Wide window trade search successful", 
                           account_id=account_id,
                           trade_count=len(trades),
                           first_trade_time=first_trade.get("timestamp"),
                           last_trade_time=last_trade.get("timestamp"))
            else:
                logger.info("Wide window trade search - no trades found", 
                           account_id=account_id,
                           trade_count=len(trades))
            
            return trades
            
        except Exception as e:
            logger.error("Failed to fetch trades with wide window", 
                        account_id=account_id,
                        error=str(e))
            raise APIError(f"Failed to fetch trades with wide window: {e}")
    
    def calculate_daily_rpnl(self, account_id: int, date: Optional[datetime] = None) -> float:
        """
        Calculate realized P&L for a trading day
        
        Args:
            account_id: Account ID to calculate RP&L for
            date: Date to calculate RP&L for (defaults to today)
            
        Returns:
            Total realized P&L for the day
        """
        try:
            trades = self.get_daily_trades(account_id, date)
            
            # Sum up realized P&L from completed trades
            total_rpnl = 0.0
            completed_trades = 0
            
            for trade in trades:
                # Only count trades with non-null profitAndLoss (completed trades)
                if trade.get("profitAndLoss") is not None:
                    profit_loss = trade["profitAndLoss"]
                    total_rpnl += profit_loss
                    completed_trades += 1
                    
                    logger.debug("Trade P&L", 
                               trade_id=trade.get("id"),
                               profit_loss=profit_loss,
                               side=trade.get("side"),
                               contract=trade.get("contractId"))
            
            logger.info("Daily RP&L calculated", 
                       account_id=account_id,
                       date=date.date() if date else "today",
                       total_rpnl=total_rpnl,
                       completed_trades=completed_trades,
                       total_trades=len(trades))
            
            return total_rpnl
            
        except Exception as e:
            logger.error("Failed to calculate daily RP&L", 
                        account_id=account_id,
                        error=str(e))
            raise APIError(f"Failed to calculate daily RP&L: {e}")
    
    def get_trade_summary(self, account_id: int, date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get comprehensive trade summary for a day
        
        Args:
            account_id: Account ID to get summary for
            date: Date to get summary for (defaults to today)
            
        Returns:
            Dictionary with trade summary data
        """
        try:
            trades = self.get_daily_trades(account_id, date)
            
            total_rpnl = 0.0
            total_fees = 0.0
            completed_trades = 0
            open_trades = 0
            buy_trades = 0
            sell_trades = 0
            
            for trade in trades:
                # Count fees
                fees = trade.get("fees", 0.0)
                total_fees += fees
                
                # Count by side (0 = buy, 1 = sell)
                side = trade.get("side")
                if side == 0:
                    buy_trades += 1
                elif side == 1:
                    sell_trades += 1
                
                # Count completed vs open trades
                if trade.get("profitAndLoss") is not None:
                    total_rpnl += trade["profitAndLoss"]
                    completed_trades += 1
                else:
                    open_trades += 1
            
            summary = {
                "account_id": account_id,
                "date": date.date() if date else datetime.now(timezone.utc).date(),
                "total_rpnl": total_rpnl,
                "total_fees": total_fees,
                "net_rpnl": total_rpnl - total_fees,
                "completed_trades": completed_trades,
                "open_trades": open_trades,
                "buy_trades": buy_trades,
                "sell_trades": sell_trades,
                "total_trades": len(trades)
            }
            
            logger.info("Trade summary generated", 
                       account_id=account_id,
                       summary=summary)
            
            return summary
            
        except Exception as e:
            logger.error("Failed to generate trade summary", 
                        account_id=account_id,
                        error=str(e))
            raise APIError(f"Failed to generate trade summary: {e}")

