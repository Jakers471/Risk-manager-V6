"""Settings loader for Risk Manager V6"""
import os
from pathlib import Path
from typing import Optional
import yaml
from dotenv import load_dotenv
import structlog

logger = structlog.get_logger(__name__)

class Settings:
    """Application settings loaded from environment and config files"""
    
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Load config files
        self.config = self._load_config()
        
        # API settings
        self.api_base_url = self.config["api"]["base_url"]
        self.api_auth_endpoint = self.config["api"]["auth_endpoint"]
        self.api_timeout = self.config["api"]["timeout"]
        self.api_max_retries = self.config["api"]["max_retries"]
        
        # Auth settings
        self.token_refresh_margin = self.config["auth"]["token_refresh_margin_minutes"]
        self.session_timeout = self.config["auth"]["session_timeout_minutes"]
        
        # Credentials from environment
        self.api_username = os.getenv("TOPSTEP_USERNAME")
        self.api_key = os.getenv("TOPSTEP_API_KEY")
        
        if not self.api_username or not self.api_key:
            logger.warning("Missing API credentials in environment variables")
    
    def _load_config(self) -> dict:
        """Load configuration from YAML files"""
        config_path = Path(__file__).parent.parent / "config" / "config.yaml"
        
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info("Configuration loaded successfully")
            return config
        except Exception as e:
            logger.error("Failed to load configuration", error=str(e))
            raise

# Global settings instance
settings = Settings()

