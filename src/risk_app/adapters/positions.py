"""
Positions adapter for Risk Manager V6

HIDDEN NOTES FOR AI REFERENCE:
- ALWAYS CROSS REFERENCE TO DOCS FOR PROPER API REFERENCING
- CHECK TOPSTEP PROGRAM RULES DOCUMENTATION FOR HELPFUL INFO
- API endpoint: POST https://api.topstepx.com/api/Position/searchOpen
- Use "accountId" parameter to search for open positions
- Response contains "positions" array with open position details
- Position fields: id, accountId, contractId, creationTimestamp, type, size, averagePrice
- UP&L = Unrealized P&L: The potential profit or loss on your open positions, based on the current market price
"""

import structlog
from typing import List, Dict, Any
from .http import HTTPClient
from ..core.errors import APIError

logger = structlog.get_logger(__name__)


class PositionsAdapter:
    """Handles position-related API calls for UP&L calculations"""
    
    def __init__(self, http_client: HTTPClient):
        self.http_client = http_client
    
    def get_open_positions(self, account_id: int) -> List[Dict[str, Any]]:
        """
        Get open positions for an account
        
        Args:
            account_id: Account ID to fetch open positions for
            
        Returns:
            List of open positions with position details
        """
        try:
            logger.info("Fetching open positions", account_id=account_id)
            
            # Prepare request data
            request_data = {
                "accountId": account_id
            }
            
            # Make API call
            response = self.http_client.post("/api/Position/searchOpen", request_data)
            
            # Validate response
            if not response.get("success"):
                error_msg = response.get("errorMessage", "Unknown error")
                logger.error("Position search failed", error=error_msg)
                raise APIError(f"Position search failed: {error_msg}")
            
            # Extract positions
            positions = response.get("positions", [])
            logger.info("Position search successful", 
                       account_id=account_id,
                       position_count=len(positions))
            
            return positions
            
        except Exception as e:
            logger.error("Failed to fetch open positions", 
                        account_id=account_id,
                        error=str(e))
            raise APIError(f"Failed to fetch open positions: {e}")
    
    def get_position_summary(self, account_id: int) -> Dict[str, Any]:
        """
        Get summary of open positions for an account
        
        Args:
            account_id: Account ID to get summary for
            
        Returns:
            Dictionary with position summary data
        """
        try:
            positions = self.get_open_positions(account_id)
            
            total_positions = len(positions)
            total_size = 0
            long_positions = 0
            short_positions = 0
            
            for position in positions:
                size = position.get("size", 0)
                position_type = position.get("type")  # 0 = long, 1 = short
                
                total_size += abs(size)
                
                if position_type == 0:
                    long_positions += 1
                elif position_type == 1:
                    short_positions += 1
            
            summary = {
                "account_id": account_id,
                "total_positions": total_positions,
                "total_size": total_size,
                "long_positions": long_positions,
                "short_positions": short_positions,
                "positions": positions
            }
            
            logger.info("Position summary generated", 
                       account_id=account_id,
                       summary=summary)
            
            return summary
            
        except Exception as e:
            logger.error("Failed to generate position summary", 
                        account_id=account_id,
                        error=str(e))
            raise APIError(f"Failed to generate position summary: {e}")

