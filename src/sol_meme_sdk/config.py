#!/usr/bin/env python3
"""
Configuration management for Solana Meme SDK
"""

import os
from typing import Optional
from dotenv import load_dotenv


class Config:
    """Configuration manager for SDK settings"""
    
    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()
        
        # Jupiter API configuration
        self.jupiter_api_key: Optional[str] = os.getenv("JUPITER_API_KEY")
        
        # Solana network configuration
        self.solana_network: str = os.getenv("SOLANA_NETWORK", "mainnet-beta")
        self.solana_rpc_endpoint: Optional[str] = os.getenv("SOLANA_RPC_ENDPOINT")
        
        # Validate required configurations
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration settings"""
        if not self.jupiter_api_key:
            print("⚠️  Warning: JUPITER_API_KEY not found in environment variables")
            print("   Get a free API key at: https://portal.jup.ag/")
        
        # Set default RPC endpoints based on network
        if not self.solana_rpc_endpoint:
            if self.solana_network == "mainnet-beta":
                self.solana_rpc_endpoint = "https://api.mainnet-beta.solana.com"
            elif self.solana_network == "devnet":
                self.solana_rpc_endpoint = "https://api.devnet.solana.com"
            elif self.solana_network == "testnet":
                self.solana_rpc_endpoint = "https://api.testnet.solana.com"
    
    def get_jupiter_api_key(self) -> str:
        """Get Jupiter API key with validation"""
        if not self.jupiter_api_key:
            raise ValueError(
                "Jupiter API key is required. "
                "Set JUPITER_API_KEY in .env file or get a free key at https://portal.jup.ag/"
            )
        return self.jupiter_api_key
    
    def get_solana_config(self) -> dict:
        """Get Solana network configuration"""
        return {
            "network": self.solana_network,
            "rpc_endpoint": self.solana_rpc_endpoint
        }


# Global configuration instance
_config = Config()


def get_config() -> Config:
    """Get the global configuration instance"""
    return _config


def set_jupiter_api_key(api_key: str) -> None:
    """Set Jupiter API key programmatically"""
    _config.jupiter_api_key = api_key


def set_solana_network(network: str) -> None:
    """Set Solana network programmatically"""
    _config.solana_network = network
    _config._validate_config()  # Re-validate to update RPC endpoint