#!/usr/bin/env python3
"""Risk Manager V6 - Main Entry Point"""

import sys
import os
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from risk_app.core.logging_setup import setup_logging
from risk_app.core.settings import settings
from risk_app.adapters.auth import AuthManager
from risk_app.adapters.accounts import AccountsAdapter
from risk_app.repos.accounts_repo import AccountsRepository
from risk_app.stores.anchors_store import AnchorsStore
from risk_app.services.rollover_service import RolloverService
from risk_app.engines.mll import MLLEngine
import structlog

def main():
    """Main entry point for Risk Manager V6"""
    try:
        # Setup logging
        setup_logging()
        logger = structlog.get_logger(__name__)
        
        logger.info("Risk Manager V6 starting up")
        
        # Step 1: Authentication
        print("🔐 Step 1: Authentication")
        auth_manager = AuthManager()
        
        if auth_manager.login():
            token_info = auth_manager.get_token_info()
            logger.info("Authentication successful", 
                       status=token_info["status"],
                       expires_in_minutes=token_info["expires_in_minutes"])
            
            print(f"✅ Authenticated (token expires in {token_info['expires_in_minutes']} min)")
            
            # Step 2: Fetch Account Data
            print("\n📊 Step 2: Fetching Account Data")
            accounts_adapter = AccountsAdapter(auth_manager.http_client)
            
            try:
                accounts_data = accounts_adapter.search_accounts(only_active=True)
                print(f"✅ Fetched {len(accounts_data)} active accounts")
                
                # Step 3: Persist Data
                print("\n💾 Step 3: Persisting Data")
                accounts_repo = AccountsRepository()
                accounts_repo.store_accounts(accounts_data)
                
                # Display account information
                active_accounts = accounts_repo.get_active_accounts()
                print(f"✅ Stored {len(active_accounts)} accounts in repository")
                
                for account in active_accounts:
                    print(f"   📈 Account: {account.name} (ID: {account.id})")
                    print(f"      Balance: ${account.balance:,.2f}")
                    print(f"      Equity: ${account.display_equity:,.2f}")
                    print(f"      Unrealized P&L: ${account.unrealized_pnl:,.2f}")
                    print(f"      Can Trade: {account.can_trade}")
                    print(f"      Simulated: {account.simulated}")
                    if account.status:
                        print(f"      Status: {account.status}")
                    print()
                
                # Step 4: Anchors & Rollover
                print("⚓ Step 4: Anchors & Rollover")
                anchors_store = AnchorsStore()
                rollover_service = RolloverService(anchors_store, accounts_repo)
                
                # Initialize anchors for each account with proper starting balances
                # Based on account names, determine starting balances
                for account in active_accounts:
                    if "S1AUG15" in account.name:
                        starting_balance = 50000  # 50K account
                    elif "PRACTICEAUG26" in account.name:
                        starting_balance = 150000  # 150K account
                    else:
                        # Default based on current balance
                        starting_balance = account.balance
                    
                    rollover_service.initialize_account_anchors(account.id, account.balance, starting_balance)
                    print(f"   ⚓ Initialized anchors for {account.name} (Starting: ${starting_balance:,.2f})")
                
                # Check rollover status
                rollover_status = rollover_service.get_rollover_status()
                print(f"   📅 Rollover status: {rollover_status['total_accounts']} accounts monitored")
                print(f"   🕐 Is rollover time: {rollover_status['is_rollover_time']}")
                
                # Step 5: MLL Engine (Corrected Logic)
                print("\n🧮 Step 5: MLL Engine (Corrected)")
                mll_engine = MLLEngine()
                
                for account in active_accounts:
                    starting_balance = anchors_store.get_starting_balance(account.id)
                    eod_high_anchor = anchors_store.get_eod_high_anchor(account.id)
                    current_equity = account.display_equity
                    
                    mll_result = mll_engine.calculate_mll(
                        account_id=account.id,
                        starting_balance=starting_balance,
                        eod_high_anchor=eod_high_anchor,
                        current_equity=current_equity
                    )
                    
                    print(f"   📊 MLL for {account.name}:")
                    print(f"      Plan Size: {mll_result.plan_size}")
                    print(f"      Starting Balance: ${mll_result.starting_balance:,.2f}")
                    print(f"      EOD High Anchor: ${mll_result.eod_high_anchor:,.2f}")
                    print(f"      Current Equity: ${mll_result.current_equity:,.2f}")
                    
                    if mll_result.floor is not None:
                        print(f"      Floor: ${mll_result.floor:,.2f}")
                        print(f"      Used: ${mll_result.used:,.2f}")
                        print(f"      Remaining: ${mll_result.remaining:,.2f}")
                        print(f"      % Used: {mll_result.pct_used:.1f}%")
                    else:
                        print(f"      Floor: N/A (Missing Anchor)")
                        print(f"      Used: N/A")
                        print(f"      Remaining: N/A")
                        print(f"      % Used: N/A")
                    
                    print(f"      Status: {mll_result.status.value}")
                    print(f"      Reason: {mll_result.reason}")
                    
                    # Check for warnings
                    warning_level = mll_engine.get_warning_level(mll_result)
                    if warning_level:
                        print(f"      ⚠️  Warning Level: {warning_level}")
                    print()
                
                # Step 6: Basic Compute (Portfolio-level)
                print("🧮 Step 6: Portfolio Compute")
                total_equity = sum(account.display_equity for account in active_accounts)
                total_balance = sum(account.balance for account in active_accounts)
                total_unrealized = sum(account.unrealized_pnl for account in active_accounts)
                
                print(f"✅ Total Portfolio Equity: ${total_equity:,.2f}")
                print(f"✅ Total Portfolio Balance: ${total_balance:,.2f}")
                print(f"✅ Total Unrealized P&L: ${total_unrealized:,.2f}")
                
                # Step 7: Basic Decision
                print("\n🎯 Step 7: Basic Decision")
                if total_unrealized < -1000:
                    print("⚠️  WARNING: Total unrealized loss exceeds $1,000")
                elif total_unrealized > 1000:
                    print("✅ GOOD: Total unrealized profit exceeds $1,000")
                else:
                    print("📊 NORMAL: Total unrealized P&L within normal range")
                
                print("\n🎉 Walking Skeleton Complete!")
                print("✅ Auth → Fetch → Persist → Anchors → MLL → Compute → Decide")
                
            except Exception as e:
                logger.error("Failed to fetch accounts", error=str(e))
                print(f"❌ Failed to fetch accounts: {e}")
                sys.exit(1)
                
        else:
            logger.error("Authentication failed")
            print("❌ Authentication failed")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Startup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

