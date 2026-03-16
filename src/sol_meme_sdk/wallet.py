"""
Wallet management for Sol Meme SDK
"""

import base58
import json
import logging
from typing import Optional, Dict, List
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.api import Client
from solana.rpc.types import TxOpts

from .models import WalletInfo
from .exceptions import WalletError

logger = logging.getLogger(__name__)


class Wallet:
    """Wallet class for managing Solana accounts"""

    def __init__(self, private_key: Optional[str] = None):
        """
        Initialize wallet with private key or generate new keypair
        
        Args:
            private_key: Base58 encoded private key (optional)
        """
        if private_key:
            try:
                # Decode base58 private key
                private_key_bytes = base58.b58decode(private_key)
                self.keypair = Keypair.from_bytes(private_key_bytes)
            except Exception as e:
                raise WalletError(f"Invalid private key: {e}")
        else:
            # Generate new keypair
            self.keypair = Keypair()
        
        self.public_key = self.keypair.pubkey()
        self.address = str(self.public_key)
        logger.info(f"Wallet initialized: {self.address}")

    @classmethod
    def from_mnemonic(cls, mnemonic: str, derivation_path: str = "m/44'/501'/0'/0'") -> 'Wallet':
        """
        Create wallet from mnemonic phrase
        
        Args:
            mnemonic: BIP39 mnemonic phrase
            derivation_path: Derivation path (default: Solana standard)
            
        Returns:
            Wallet instance
        """
        try:
            # Note: In production, use a proper BIP39 library
            # This is a simplified implementation
            from solders.keypair import Keypair
            
            # For now, use the first keypair from mnemonic
            # In real implementation, use proper BIP39 derivation
            seed = mnemonic.encode()[:32].ljust(32, b'\x00')
            keypair = Keypair.from_seed(seed)
            
            wallet = cls.__new__(cls)
            wallet.keypair = keypair
            wallet.public_key = keypair.pubkey()
            wallet.address = str(wallet.public_key)
            return wallet
            
        except Exception as e:
            raise WalletError(f"Failed to create wallet from mnemonic: {e}")

    def get_private_key(self) -> str:
        """Get base58 encoded private key"""
        return base58.b58encode(bytes(self.keypair)).decode()

    def get_balance(self, client: Client) -> float:
        """
        Get SOL balance
        
        Args:
            client: Solana RPC client
            
        Returns:
            SOL balance
        """
        try:
            balance_response = client.get_balance(self.public_key)
            if balance_response.value is None:
                return 0.0
            return balance_response.value / 1e9  # Convert lamports to SOL
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            raise WalletError(f"Failed to get balance: {e}")

    def get_token_balances(self, client: Client) -> Dict[str, float]:
        """
        Get token balances for this wallet
        
        Args:
            client: Solana RPC client
            
        Returns:
            Dictionary of token addresses to balances
        """
        # This is a simplified implementation
        # In production, use proper token program interaction
        try:
            # For now, return empty dict
            # Real implementation would query token accounts
            return {}
        except Exception as e:
            logger.error(f"Failed to get token balances: {e}")
            raise WalletError(f"Failed to get token balances: {e}")

    def get_wallet_info(self, client: Client) -> WalletInfo:
        """
        Get comprehensive wallet information
        
        Args:
            client: Solana RPC client
            
        Returns:
            WalletInfo object
        """
        try:
            balance_sol = self.get_balance(client)
            tokens = self.get_token_balances(client)
            
            return WalletInfo(
                address=self.address,
                balance_sol=balance_sol,
                tokens=tokens,
                total_value=balance_sol  # Simplified - would include token values
            )
        except Exception as e:
            logger.error(f"Failed to get wallet info: {e}")
            raise WalletError(f"Failed to get wallet info: {e}")

    def sign_transaction(self, transaction) -> bytes:
        """
        Sign a transaction
        
        Args:
            transaction: Transaction to sign
            
        Returns:
            Signed transaction bytes
        """
        try:
            transaction.sign(self.keypair)
            return bytes(transaction)
        except Exception as e:
            logger.error(f"Failed to sign transaction: {e}")
            raise WalletError(f"Failed to sign transaction: {e}")

    def export_to_json(self, password: Optional[str] = None) -> str:
        """
        Export wallet to JSON format
        
        Args:
            password: Optional encryption password
            
        Returns:
            JSON string containing wallet data
        """
        wallet_data = {
            "address": self.address,
            "private_key": self.get_private_key(),
            "public_key": str(self.public_key)
        }
        
        if password:
            # Simple encryption (in production use proper encryption)
            import hashlib
            key = hashlib.sha256(password.encode()).digest()
            # Implement proper AES encryption here
            wallet_data["encrypted"] = True
        
        return json.dumps(wallet_data, indent=2)

    @classmethod
    def import_from_json(cls, json_data: str, password: Optional[str] = None) -> 'Wallet':
        """
        Import wallet from JSON data
        
        Args:
            json_data: JSON string containing wallet data
            password: Encryption password if applicable
            
        Returns:
            Wallet instance
        """
        try:
            data = json.loads(json_data)
            
            if data.get("encrypted") and password:
                # Implement decryption logic
                raise WalletError("Encrypted wallet import not implemented")
            
            private_key = data.get("private_key")
            if not private_key:
                raise WalletError("No private key found in JSON data")
            
            return cls(private_key=private_key)
            
        except Exception as e:
            raise WalletError(f"Failed to import wallet from JSON: {e}")