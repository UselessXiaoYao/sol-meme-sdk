"""
Main client class for Sol Meme SDK
"""

import asyncio
import logging
from typing import Optional, Dict, List, Any
from solana.rpc.api import Client
from solana.rpc.commitment import Confirmed

from .wallet import Wallet
from .trading import TradingEngine
from .models import Network, TokenInfo, TradeOrder, TradeResult, TransactionConfig
from .exceptions import SolMemeError, NetworkError

logger = logging.getLogger(__name__)


class SolMemeClient:
    """Main client for Solana meme coin trading SDK"""

    def __init__(
        self,
        network: Network = Network.MAINNET,
        rpc_url: Optional[str] = None,
        private_key: Optional[str] = None,
        config: Optional[TransactionConfig] = None
    ):
        """
        Initialize Sol Meme SDK client
        
        Args:
            network: Solana network to connect to
            rpc_url: Custom RPC URL (optional)
            private_key: Wallet private key (optional)
            config: Transaction configuration
        """
        self.network = network
        self.config = config or TransactionConfig()
        
        # Set RPC URL
        if rpc_url:
            self.rpc_url = rpc_url
        else:
            self.rpc_url = self._get_default_rpc_url(network)
        
        # Initialize Solana client
        self.solana_client = Client(self.rpc_url, commitment=Confirmed)
        
        # Initialize wallet
        self.wallet = Wallet(private_key=private_key)
        
        # Initialize trading engine
        self.trading = TradingEngine(self.solana_client, self.wallet, self.config)
        
        logger.info(f"SolMemeClient initialized for {network} at {self.rpc_url}")
        logger.info(f"Wallet address: {self.wallet.address}")

    def _get_default_rpc_url(self, network: Network) -> str:
        """Get default RPC URL for network"""
        urls = {
            Network.MAINNET: "https://api.mainnet-beta.solana.com",
            Network.DEVNET: "https://api.devnet.solana.com", 
            Network.TESTNET: "https://api.testnet.solana.com",
        }
        return urls.get(network, urls[Network.MAINNET])

    async def connect(self) -> bool:
        """
        Connect to Solana network
        
        Returns:
            True if connection successful
        """
        try:
            # Test connection
            version = self.solana_client.get_version()
            if version.value:
                logger.info(f"Connected to Solana {self.network}")
                logger.info(f"Solana version: {version.value}")
                return True
            
            raise NetworkError("Failed to get version from RPC")
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            raise NetworkError(f"Failed to connect to {self.network}: {e}")

    async def get_balance(self) -> float:
        """
        Get wallet SOL balance
        
        Returns:
            SOL balance
        """
        return self.wallet.get_balance(self.solana_client)

    async def get_wallet_info(self) -> Dict[str, Any]:
        """
        Get comprehensive wallet information
        
        Returns:
            Wallet information dictionary
        """
        wallet_info = self.wallet.get_wallet_info(self.solana_client)
        return wallet_info.dict()

    async def get_token_info(self, token_address: str) -> TokenInfo:
        """
        Get token information
        
        Args:
            token_address: Token mint address
            
        Returns:
            TokenInfo object
        """
        try:
            # This would fetch token metadata from on-chain data
            # For now, return placeholder
            return TokenInfo(
                address=token_address,
                symbol="UNKNOWN",
                name="Unknown Token",
                decimals=6,
                price=0.001
            )
        except Exception as e:
            raise SolMemeError(f"Failed to get token info: {e}")

    async def buy_token(
        self,
        token_address: str,
        amount_sol: float,
        slippage: float = 0.5
    ) -> TradeResult:
        """
        Buy meme token with SOL
        
        Args:
            token_address: Token mint address
            amount_sol: Amount of SOL to spend
            slippage: Slippage tolerance percentage
            
        Returns:
            TradeResult with execution details
        """
        return await self.trading.buy_token(token_address, amount_sol, slippage)

    async def sell_token(
        self,
        token_address: str,
        amount_tokens: float,
        slippage: float = 0.5
    ) -> TradeResult:
        """
        Sell meme token for SOL
        
        Args:
            token_address: Token mint address
            amount_tokens: Amount of tokens to sell
            slippage: Slippage tolerance percentage
            
        Returns:
            TradeResult with execution details
        """
        return await self.trading.sell_token(token_address, amount_tokens, slippage)

    async def get_trade_history(self, limit: int = 100) -> List[TradeResult]:
        """
        Get trade history
        
        Args:
            limit: Maximum number of trades to return
            
        Returns:
            List of TradeResult objects
        """
        return await self.trading.get_trade_history(limit)

    async def get_token_price(self, token_address: str) -> float:
        """
        Get current token price in SOL
        
        Args:
            token_address: Token mint address
            
        Returns:
            Price in SOL
        """
        return await self.trading._get_token_price(token_address)

    async def get_market_data(self, token_address: str) -> Dict[str, Any]:
        """
        Get market data for token
        
        Args:
            token_address: Token mint address
            
        Returns:
            Market data dictionary
        """
        try:
            # This would fetch from DEX APIs or on-chain data
            price = await self.get_token_price(token_address)
            
            return {
                "token_address": token_address,
                "price": price,
                "volume_24h": 0.0,  # Placeholder
                "price_change_24h": 0.0,  # Placeholder
                "liquidity": 0.0,  # Placeholder
            }
        except Exception as e:
            raise SolMemeError(f"Failed to get market data: {e}")

    async def scan_meme_tokens(self, filters: Optional[Dict] = None) -> List[TokenInfo]:
        """
        Scan for new meme tokens
        
        Args:
            filters: Filter criteria
            
        Returns:
            List of TokenInfo objects
        """
        try:
            # This would scan DEXs for new token listings
            # For now, return empty list
            return []
        except Exception as e:
            raise SolMemeError(f"Failed to scan meme tokens: {e}")

    async def monitor_price(self, token_address: str, callback, interval: float = 5.0):
        """
        Monitor token price and call callback on changes
        
        Args:
            token_address: Token to monitor
            callback: Function to call on price changes
            interval: Check interval in seconds
        """
        last_price = None
        
        while True:
            try:
                current_price = await self.get_token_price(token_address)
                
                if last_price is None or abs(current_price - last_price) / last_price > 0.01:
                    await callback(token_address, current_price, last_price)
                    last_price = current_price
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Price monitoring error: {e}")
                await asyncio.sleep(interval)

    def export_wallet(self, password: Optional[str] = None) -> str:
        """
        Export wallet to JSON
        
        Args:
            password: Optional encryption password
            
        Returns:
            JSON string with wallet data
        """
        return self.wallet.export_to_json(password)

    @classmethod
    def from_wallet_file(cls, file_path: str, password: Optional[str] = None, **kwargs) -> 'SolMemeClient':
        """
        Create client from wallet file
        
        Args:
            file_path: Path to wallet file
            password: Wallet file password
            **kwargs: Additional client arguments
            
        Returns:
            SolMemeClient instance
        """
        import json
        
        try:
            with open(file_path, 'r') as f:
                wallet_data = json.load(f)
            
            private_key = wallet_data.get('private_key')
            if not private_key:
                raise SolMemeError("No private key found in wallet file")
            
            return cls(private_key=private_key, **kwargs)
            
        except Exception as e:
            raise SolMemeError(f"Failed to load wallet from file: {e}")

    async def close(self):
        """Close client connections"""
        # Close any open connections
        logger.info("SolMemeClient closed")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        asyncio.run(self.close())