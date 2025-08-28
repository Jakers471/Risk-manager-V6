#!/usr/bin/env python3
"""
Risk Manager V6 - Walking Skeleton
End-to-end path: Auth → Fetch → Persist → Anchors → MLL → RP&L → Compute → Decide

HIDDEN NOTES FOR AI REFERENCE:
- ALWAYS CROSS REFERENCE TO DOCS FOR PROPER API REFERENCING
- CHECK TOPSTEP PROGRAM RULES DOCUMENTATION FOR HELPFUL INFO
- RP&L = Realized Day P&L: The actual profit or loss from positions you've closed for the trading day
- UP&L = Unrealized P&L: The potential profit or loss on your open positions, based on the current market price
- Use configuration-based account management (accounts.yaml) for starting balances
- NO MOCK DATA - ALWAYS CONNECT TO REAL API
"""

import structlog
from src.risk_app.core.logging_setup import setup_logging
from src.risk_app.core.settings import settings
from src.risk_app.adapters.auth import AuthManager
from src.risk_app.adapters.accounts import AccountsAdapter
from src.risk_app.adapters.trades import TradesAdapter
from src.risk_app.adapters.positions import PositionsAdapter
from src.risk_app.repos.accounts_repo import AccountsRepository
from src.risk_app.stores.anchors_store import AnchorsStore
from src.risk_app.services.rollover_service import RolloverService
from src.risk_app.engines.mll import MLLEngine
from src.risk_app.engines.realized_pnl import RealizedPnLEngine
from src.risk_app.engines.unrealized_pnl import UnrealizedPnLEngine
from src.risk_app.engines.total_pnl import TotalPnLEngine
from src.risk_app.engines.portfolio import PortfolioEngine

# Setup logging
setup_logging()
logger = structlog.get_logger(__name__)

def main():
    """Main walking skeleton execution."""
    logger.info("Risk Manager V6 starting up")
    
    print("🚀 Risk Manager V6 - Walking Skeleton")
    print("=" * 50)
    
    # Step 1: Authentication
    print("\n🔐 Step 1: Authentication")
    auth_manager = AuthManager()
    auth_result = auth_manager.login()
    
    if not auth_result:
        print("❌ Authentication failed")
        return
    
    print(f"✅ Authenticated (token expires in {auth_manager.token_expires_in_minutes} min)")
    
    # Step 2: Fetch Account Data
    print("\n📊 Step 2: Fetching Account Data")
    accounts_adapter = AccountsAdapter(auth_manager.http_client)
    accounts_data = accounts_adapter.search_accounts(only_active=True)
    
    if not accounts_data:
        print("❌ No accounts found")
        return
    
    print(f"✅ Fetched {len(accounts_data)} active accounts")
    
    # Step 3: Persist Data
    print("\n💾 Step 3: Persisting Data")
    accounts_repo = AccountsRepository()
    accounts_repo.store_accounts(accounts_data)
    
    accounts = accounts_repo.get_all_accounts()
    print(f"✅ Stored {len(accounts)} accounts in repository")
    
    for account in accounts:
        print(f"   📈 Account: {account.name} (ID: {account.id})")
        print(f"      Balance: ${account.balance:,.2f}")
        print(f"      Equity: ${account.display_equity:,.2f}")
        print(f"      Unrealized P&L: ${account.unrealized_pnl:,.2f}")
        print(f"      Can Trade: {account.can_trade}")
        print(f"      Simulated: {account.simulated}")
        print()
    
    # Step 4: Anchors & Rollover
    print("⚓ Step 4: Anchors & Rollover")
    anchors_store = AnchorsStore()
    rollover_service = RolloverService(anchors_store, accounts_repo)
    
    for account in accounts:
        # Get starting balance from configuration
        starting_balance = settings.get_account_starting_balance(account.name)
        account_type = settings.get_account_type(starting_balance)
        
        # Initialize anchors if needed
        anchors = anchors_store.get_anchors(account.id)
        if anchors.starting_balance == 0.0:  # New account
            rollover_service.initialize_account_anchors(account.id, account.balance, starting_balance)
            print(f"   ⚓ Initialized anchors for {account.name} (Starting: ${starting_balance:,.2f})")
        else:
            print(f"   ⚓ Using existing anchors for {account.name} ({account_type})")
    
    # Check rollover status
    rollover_status = rollover_service.perform_rollover_if_needed()
    print(f"   📅 Rollover status: {len(accounts)} accounts monitored")
    print(f"   🕐 Is rollover time: {rollover_service.is_rollover_time()}")
    
    # Step 5: MLL Engine
    print("\n🧮 Step 5: MLL Engine (Corrected)")
    mll_engine = MLLEngine()
    
    for account in accounts:
        # Get starting balance from configuration
        starting_balance = settings.get_account_starting_balance(account.name)
        account_type = settings.get_account_type(starting_balance)
        
        # Get anchors
        anchors = anchors_store.get_anchors(account.id)
        
        # Calculate MLL
        mll_result = mll_engine.calculate_mll(
            account_id=account.id,
            starting_balance=starting_balance,
            eod_high_anchor=anchors.eod_high_anchor,
            current_equity=account.display_equity
        )
        
        # Display results
        print(f"   📊 MLL for {account.name}:")
        print(f"      Plan Size: {account_type}")
        print(f"      Starting Balance: ${starting_balance:,.2f}")
        print(f"      EOD High Anchor: ${anchors.eod_high_anchor:,.2f}")
        print(f"      Current Equity: ${account.display_equity:,.2f}")
        print(f"      Floor: ${mll_result.floor:,.2f}")
        print(f"      Used: ${mll_result.used:,.2f}")
        print(f"      Remaining: ${mll_result.remaining:,.2f}")
        print(f"      % Used: {mll_result.pct_used:.1f}%")
        print(f"      Status: {mll_result.status}")
        print(f"      Reason: {mll_result.reason}")
        
        # Warning level
        warning_level = mll_engine.get_warning_level(mll_result)
        if warning_level != "NORMAL":
            print(f"      ⚠️  Warning Level: {warning_level}")
        print()
    
    # Step 6: Modularized P&L Engines
    print("💰 Step 6: Modularized P&L Engines")
    trades_adapter = TradesAdapter(auth_manager.http_client)
    positions_adapter = PositionsAdapter(auth_manager.http_client)
    
    # Initialize all P&L engines
    realized_pnl_engine = RealizedPnLEngine()
    unrealized_pnl_engine = UnrealizedPnLEngine()
    total_pnl_engine = TotalPnLEngine()
    
    # Store account results for portfolio calculation
    account_results = []
    
    for account in accounts:
        try:
            # Test with wider window first to see if we can get any trades
            logger.info(f"Testing wide window for {account.name}")
            wide_trades = trades_adapter.get_trades_wide_window(account.id, hours_back=48)
            
            # Get trade data for RP&L calculation (regular session window)
            trades_data = trades_adapter.get_daily_trades(account.id)
            
            # Get position data for UP&L calculation
            positions_data = positions_adapter.get_open_positions(account.id)
            
            # Calculate realized P&L
            realized_result = realized_pnl_engine.calculate_realized_pnl(
                account_id=account.id,
                account_name=account.name,
                trades_data=trades_data
            )
            
            # Calculate unrealized P&L
            unrealized_result = unrealized_pnl_engine.calculate_unrealized_pnl(
                account_id=account.id,
                account_name=account.name,
                positions_data=positions_data
            )
            
            # Calculate total P&L
            total_result = total_pnl_engine.calculate_total_pnl(
                realized_result=realized_result,
                unrealized_result=unrealized_result
            )
            
            # Display results
            print(f"   💰 P&L for {account.name}:")
            print(f"      Realized Day P&L: ${realized_result.realized_pnl:,.2f}")
            print(f"      Net RP&L (after fees): ${realized_result.net_pnl:,.2f}")
            print(f"      Unrealized P&L: ${unrealized_result.unrealized_pnl:,.2f}")
            print(f"      Total P&L: ${total_result.total_pnl:,.2f}")
            print(f"      Total Fees: ${realized_result.total_fees:,.2f}")
            print(f"      Completed Trades: {realized_result.completed_trades}")
            print(f"      Open Trades: {realized_result.open_trades}")
            print(f"      Open Positions: {unrealized_result.open_positions}")
            print(f"      Total Trades: {realized_result.total_trades}")
            
            # Status indicators
            print(f"      📈 RP&L Status: {realized_result.status}")
            print(f"      📊 UP&L Status: {unrealized_result.status}")
            print(f"      🎯 Total Status: {total_result.status}")
            
            # Warning levels
            rpnl_warning = realized_pnl_engine.get_warning_level(realized_result)
            upnl_warning = unrealized_pnl_engine.get_warning_level(unrealized_result)
            if rpnl_warning != "NORMAL":
                print(f"      ⚠️  RP&L Warning: {rpnl_warning}")
            if upnl_warning != "NORMAL":
                print(f"      ⚠️  UP&L Warning: {upnl_warning}")
            print()
            
            # Store results for portfolio calculation
            account_results.append({
                "equity": account.display_equity,
                "balance": account.balance,
                "realized_result": realized_result,
                "unrealized_result": unrealized_result,
                "total_result": total_result
            })
            
        except Exception as e:
            logger.error("Failed to calculate P&L", account_id=account.id, error=str(e))
            print(f"   ❌ Failed to calculate P&L for {account.name}: {e}")
            print()
    
    # Step 7: Portfolio Engine
    print("🧮 Step 7: Portfolio Engine")
    portfolio_engine = PortfolioEngine()
    portfolio_result = None
    
    try:
        # Calculate portfolio summary
        portfolio_result = portfolio_engine.calculate_portfolio_summary(account_results)
        
        # Get risk assessment
        risk_assessment = portfolio_engine.get_risk_assessment(portfolio_result)
        
        print(f"✅ Total Portfolio Equity: ${portfolio_result.total_equity:,.2f}")
        print(f"✅ Total Portfolio Balance: ${portfolio_result.total_balance:,.2f}")
        print(f"✅ Total Realized P&L: ${portfolio_result.total_realized_pnl:,.2f}")
        print(f"✅ Total Unrealized P&L: ${portfolio_result.total_unrealized_pnl:,.2f}")
        print(f"✅ Total Portfolio P&L: ${portfolio_result.total_pnl:,.2f}")
        print(f"✅ Total Fees: ${portfolio_result.total_fees:,.2f}")
        print(f"✅ Total Completed Trades: {portfolio_result.total_completed_trades}")
        print(f"✅ Total Open Positions: {portfolio_result.total_open_positions}")
        print(f"✅ Account Count: {portfolio_result.account_count}")
        
        # Portfolio status and warnings
        print(f"📊 Portfolio Status: {portfolio_result.status}")
        portfolio_warning = portfolio_engine.get_portfolio_warning_level(portfolio_result)
        if portfolio_warning != "NORMAL":
            print(f"⚠️  Portfolio Warning: {portfolio_warning}")
        
        # Risk assessment
        print(f"🎯 Risk Level: {risk_assessment['warning_level']}")
        print(f"🔍 Risk Factors: {', '.join(risk_assessment['risk_factors'])}")
        
    except Exception as e:
        logger.error("Failed to calculate portfolio summary", error=str(e))
        print(f"❌ Failed to calculate portfolio summary: {e}")
    
    # Step 8: Basic Decision
    print("\n🎯 Step 8: Basic Decision")
    if portfolio_result is None:
        print("❌ Cannot make decisions - portfolio calculation failed")
    else:
        if portfolio_result.total_unrealized_pnl < -1000:
            print("📊 WARNING: Significant unrealized losses detected")
        elif portfolio_result.total_unrealized_pnl > 1000:
            print("📊 POSITIVE: Significant unrealized gains detected")
        else:
            print("📊 NORMAL: Total unrealized P&L within normal range")
        
        if portfolio_result.total_realized_pnl < -500:
            print("📊 WARNING: Significant realized losses today")
        elif portfolio_result.total_realized_pnl > 500:
            print("📊 POSITIVE: Significant realized profits today")
        else:
            print("📊 NORMAL: Total realized P&L within normal range")
    
    print("\n🎉 Walking Skeleton Complete!")
    print("✅ Auth → Fetch → Persist → Anchors → MLL → RP&L → Compute → Decide")

if __name__ == "__main__":
    main()



