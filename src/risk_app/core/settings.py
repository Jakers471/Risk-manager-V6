"""Application settings and configuration."""

import os
from pathlib import Path
from typing import Dict, Any
import yaml
from dotenv import load_dotenv

from .errors import ConfigurationError

# Load environment variables
load_dotenv()


class Settings:
    """Application settings loaded from environment and config files."""
    
    def __init__(self):
        self.config_dir = Path(__file__).parent.parent / "config"
        self._load_config()
        self._load_accounts()
        self._validate_credentials()
    
    def _load_config(self):
        """Load main configuration from config.yaml."""
        config_file = self.config_dir / "config.yaml"
        if not config_file.exists():
            raise ConfigurationError(f"Configuration file not found: {config_file}")
        
        with open(config_file, 'r') as f:
            self.config = yaml.safe_load(f)
    
    def _load_accounts(self):
        """Load account starting balances from accounts.yaml."""
        accounts_file = self.config_dir / "accounts.yaml"
        if not accounts_file.exists():
            raise ConfigurationError(f"Accounts configuration file not found: {accounts_file}")
        
        with open(accounts_file, 'r') as f:
            accounts_config = yaml.safe_load(f)
            self.account_starting_balances = accounts_config.get('accounts', {})
            self.account_types = accounts_config.get('account_types', {})
    
    def _validate_credentials(self):
        """Validate required environment variables."""
        self.username = os.getenv('TOPSTEP_USERNAME')
        self.api_key = os.getenv('TOPSTEP_API_KEY')
        
        if not self.username or not self.api_key:
            raise ConfigurationError(
                "Missing required environment variables. Please set:\n"
                "TOPSTEP_USERNAME=your_username\n"
                "TOPSTEP_API_KEY=your_api_key"
            )
    
    def get_account_starting_balance(self, account_name: str) -> int:
        """Get starting balance for an account by name."""
        return self.account_starting_balances.get(account_name, 50000)  # Default to 50K
    
    def get_account_type(self, starting_balance: int) -> str:
        """Get account type string from starting balance."""
        return self.account_types.get(starting_balance, "UNKNOWN")
    
    @property
    def api_base_url(self) -> str:
        return self.config['api']['base_url']
    
    @property
    def api_auth_endpoint(self) -> str:
        return self.config['api']['auth_endpoint']
    
    @property
    def api_timeout(self) -> int:
        return self.config['api']['timeout']
    
    @property
    def api_max_retries(self) -> int:
        return self.config['api']['max_retries']
    
    @property
    def auth_token_refresh_margin_minutes(self) -> int:
        return self.config['auth']['token_refresh_margin_minutes']
    
    @property
    def auth_session_timeout_minutes(self) -> int:
        return self.config['auth']['session_timeout_minutes']
    
    @property
    def logging_level(self) -> str:
        return self.config['logging']['level']
    
    @property
    def logging_format(self) -> str:
        return self.config['logging']['format']


# Global settings instance
settings = Settings()

