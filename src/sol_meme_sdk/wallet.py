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
            # 使用BIP39标准助记词生成
            from solders.keypair import Keypair
            import mnemonic as bip39_mnemonic
            import hashlib
            import hmac
            
            # 验证助记词有效性
            if not bip39_mnemonic.Mnemonic("english").check(mnemonic):
                raise WalletError("Invalid mnemonic phrase")
            
            # BIP39种子生成
            seed = bip39_mnemonic.Mnemonic.to_seed(mnemonic, passphrase="")
            
            # BIP44路径派生（m/44'/501'/0'/0' 用于Solana）
            # 使用HMAC-SHA512进行分层确定性派生
            def derive_path(seed, path):
                master = hmac.new(b"ed25519 seed", seed, hashlib.sha512).digest()
                
                for index in path:
                    if index >= 0x80000000:
                        data = master[32:] + index.to_bytes(4, 'big')
                    else:
                        data = master[32:] + (index + 0x80000000).to_bytes(4, 'big')
                    
                    il = hmac.new(master[:32], data, hashlib.sha512).digest()
                    master = il[:32] + il[32:]
                
                return master[:32]
            
            # Solana BIP44路径：m/44'/501'/0'/0'
            path = [44 + 0x80000000, 501 + 0x80000000, 0 + 0x80000000, 0, 0]
            derived_seed = derive_path(seed, path)
            
            keypair = Keypair.from_seed(derived_seed)
            
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
        try:
            from solana.rpc.commitment import Confirmed
            from solders.pubkey import Pubkey
            
            # Query token accounts for this wallet
            token_accounts = client.get_token_accounts_by_owner(
                self.public_key,
                commitment=Confirmed
            )
            
            balances = {}
            
            if token_accounts.value:
                for account in token_accounts.value:
                    account_info = account.account.data.parsed['info']
                    
                    # Get token mint address and balance
                    mint = account_info['mint']
                    balance = account_info['tokenAmount']['uiAmount']
                    
                    if balance and balance > 0:
                        balances[mint] = balance
            
            logger.debug(f"Found {len(balances)} token balances for wallet {self.address}")
            return balances
            
        except Exception as e:
            logger.error(f"Failed to get token balances: {e}")
            # Return empty dict on error
            return {}

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
            # 使用AES加密钱包数据
            import hashlib
            from cryptography.fernet import Fernet
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            import base64
            
            # 生成密钥
            salt = b'sol_meme_sdk_salt'
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
            
            # 加密数据
            fernet = Fernet(key)
            encrypted_data = fernet.encrypt(json.dumps(wallet_data).encode())
            
            wallet_data = {
                "encrypted": True,
                "salt": base64.b64encode(salt).decode(),
                "data": base64.b64encode(encrypted_data).decode()
            }
        
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
                # 解密钱包数据
                import base64
                from cryptography.fernet import Fernet
                from cryptography.hazmat.primitives import hashes
                from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
                
                salt = base64.b64decode(data["salt"])
                encrypted_data = base64.b64decode(data["data"])
                
                # 生成密钥
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
                key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
                
                # 解密数据
                fernet = Fernet(key)
                decrypted_data = fernet.decrypt(encrypted_data)
                data = json.loads(decrypted_data.decode())
            elif data.get("encrypted") and not password:
                raise WalletError("Encrypted wallet requires password for decryption")
            
            private_key = data.get("private_key")
            if not private_key:
                raise WalletError("No private key found in JSON data")
            
            return cls(private_key=private_key)
            
        except Exception as e:
            raise WalletError(f"Failed to import wallet from JSON: {e}")