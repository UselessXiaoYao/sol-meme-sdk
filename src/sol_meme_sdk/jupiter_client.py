"""
Jupiter Aggregator client for Solana token swaps
"""

import asyncio
import aiohttp
import time
import logging
from typing import Dict, Any, Optional
from decimal import Decimal

from .exceptions import TradingError
from .config import get_config

logger = logging.getLogger(__name__)


class JupiterClient:
    """Jupiter Aggregator API client"""
    
    def __init__(self, network: str = None, api_key: str = None):
        """
        Initialize Jupiter client
        
        Args:
            network: Solana network (mainnet-beta, devnet, testnet). If None, uses config.
            api_key: Jupiter API key. If None, uses config.
        """
        config = get_config()
        self.network = network or config.solana_network
        self.api_key = api_key or config.jupiter_api_key
        self.base_url = "https://api.jup.ag"
        
        # Rate limiting
        self.rate_limiter = asyncio.Semaphore(5)  # Limit concurrent requests
        self.last_call = 0
        self.min_interval = 0.2  # Minimum 200ms between calls
        
        # Network-specific configuration
        self._setup_network_config()
        
        if not self.api_key:
            logger.warning("No API key provided. Jupiter API calls will fail. "
                         "Get a free API key at https://portal.jup.ag/")
        
        logger.info(f"JupiterClient initialized for {self.network}")
    
    def _setup_network_config(self):
        """Setup network-specific configuration"""
        # Jupiter Ultra API endpoints based on official documentation
        self.base_url = "https://api.jup.ag"
        # Ultra API endpoints with /ultra/v1/ prefix
        self.quote_endpoint = "/ultra/v1/order"    # Ultra API: Get order endpoint
        self.swap_endpoint = "/ultra/v1/execute"    # Ultra API: Execute order endpoint
        self.tokens_endpoint = "/ultra/v1/search"   # Ultra API: Search tokens endpoint
        
        # Network-specific settings
        self.network_configs = {
            "mainnet-beta": {
                "supported_tokens": True,
            },
            "devnet": {
                "supported_tokens": False,  # Limited token support on devnet
            },
            "testnet": {
                "supported_tokens": False,
            }
        }
        
        config = self.network_configs.get(self.network, self.network_configs["mainnet-beta"])
        self.supported_tokens = config["supported_tokens"]
    
    async def _rate_limited_call(self):
        """Ensure API calls respect rate limits"""
        async with self.rate_limiter:
            now = time.time()
            if now - self.last_call < self.min_interval:
                await asyncio.sleep(self.min_interval - (now - self.last_call))
            self.last_call = time.time()
    
    async def _make_api_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make API request with authentication headers"""
        
        if not self.api_key:
            raise TradingError("Jupiter API key is required. Get a free key at https://portal.jup.ag/")
        
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                # Build URL with query parameters for Jupiter API
                url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
                
                # Jupiter API uses query string parameters, not JSON body
                logger.info(f"Making API request to: {url}")
                logger.info(f"Request parameters: {params}")
                
                async with session.get(url, params=params, headers=headers, timeout=10) as resp:
                    if resp.status == 401:
                        raise TradingError("Jupiter API key is invalid or expired")
                    elif resp.status == 429:
                        raise TradingError("Jupiter API rate limit exceeded")
                    elif resp.status != 200:
                        error_text = await resp.text()
                        raise TradingError(f"Jupiter API error {resp.status}: {error_text}")
                    
                    data = await resp.json()
                    
                    if "error" in data:
                        raise TradingError(f"Jupiter API error: {data['error']}")
                    
                    return data
                    
        except aiohttp.ClientConnectorError as e:
            raise TradingError(f"Jupiter API connection failed: {e}")
        except aiohttp.ClientError as e:
            raise TradingError(f"Jupiter API client error: {e}")
        except asyncio.TimeoutError:
            raise TradingError("Jupiter API request timeout")
        except Exception as e:
            raise TradingError(f"Jupiter API request failed: {e}")
    
    async def get_quote(
        self, 
        input_mint: str, 
        output_mint: str, 
        amount: float,
        slippage_bps: int = 50,  # 0.5% slippage
        taker: str = None,
        restrict_intermediate_tokens: bool = True
    ) -> Dict[str, Any]:
        """
        Get swap quote from Jupiter Ultra API
        
        Args:
            input_mint: Input token mint address
            output_mint: Output token mint address  
            amount: Amount to swap (in token units)
            slippage_bps: Slippage in basis points (1 = 0.01%)
            taker: Taker address (optional for gasless swaps)
            restrict_intermediate_tokens: Whether to restrict intermediate tokens
            
        Returns:
            Quote response dictionary
        """
        await self._rate_limited_call()
        
        try:
            # Convert amount to lamports for SOL, or token units for tokens
            if input_mint == "So11111111111111111111111111111111111111112":  # SOL
                amount_lamports = int(amount * 1e9)
            else:
                # For tokens, we need to know decimals - this is simplified
                amount_lamports = int(amount * 1e6)  # Assume 6 decimals
            
            params = {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": str(amount_lamports),  # Jupiter Ultra API expects string amounts
                "slippageBps": slippage_bps,
                "restrictIntermediateTokens": str(restrict_intermediate_tokens).lower()
            }
            
            # Add optional parameters
            if taker:
                params["taker"] = taker
            
            return await self._make_api_request(self.quote_endpoint, params)
                    
        except Exception as e:
            raise TradingError(f"Failed to get quote from Jupiter: {e}")
    
    async def get_swap_transaction(
        self, 
        quote_response: Dict[str, Any], 
        user_public_key: str,
        wrap_unwrap_sol: bool = True
    ) -> Dict[str, Any]:
        """
        Get swap transaction from Jupiter
        
        Args:
            quote_response: Response from get_quote()
            user_public_key: User's wallet public key
            wrap_unwrap_sol: Whether to wrap/unwrap SOL automatically
            
        Returns:
            Swap transaction data
        """
        await self._rate_limited_call()
        
        try:
            data = {
                "quoteResponse": quote_response,
                "userPublicKey": user_public_key,
                "wrapAndUnwrapSol": wrap_unwrap_sol,
                "dynamicComputeUnitLimit": True,
                "prioritizationFeeLamports": "auto"
            }
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    "x-api-key": self.api_key,
                    "Content-Type": "application/json"
                }
                
                async with session.post(f"{self.base_url}{self.swap_endpoint}", json=data, headers=headers) as resp:
                    if resp.status == 429:
                        raise TradingError("Jupiter API rate limit exceeded")
                    elif resp.status != 200:
                        error_text = await resp.text()
                        raise TradingError(f"Jupiter API error {resp.status}: {error_text}")
                    
                    swap_data = await resp.json()
                    
                    if "error" in swap_data:
                        raise TradingError(f"Jupiter swap error: {swap_data['error']}")
                    
                    return swap_data
                    
        except aiohttp.ClientError as e:
            raise TradingError(f"Network error calling Jupiter API: {e}")
        except Exception as e:
            raise TradingError(f"Failed to get swap transaction from Jupiter: {e}")
    
    async def search_tokens(self, query: str, limit: int = 20) -> Dict[str, Any]:
        """
        Search for tokens using Jupiter Ultra API
        
        Args:
            query: Search query (token symbol, name, or address)
            limit: Maximum number of results
            
        Returns:
            Search results dictionary
        """
        await self._rate_limited_call()
        
        try:
            params = {
                "query": query,
                "limit": limit
            }
            
            return await self._make_api_request(self.tokens_endpoint, params)
                    
        except Exception as e:
            raise TradingError(f"Failed to search tokens: {e}")
    
    async def get_tokens_list(self) -> Dict[str, Any]:
        """Get list of supported tokens from Jupiter"""
        return await self.search_tokens("SOL")  # Default search to get token list
    
    async def get_price(
        self, 
        input_mint: str, 
        output_mint: str = "So11111111111111111111111111111111111111112"  # SOL
    ) -> float:
        """
        Get price for token pair using Jupiter Ultra API
        
        Args:
            input_mint: Input token mint address
            output_mint: Output token mint address (default: SOL)
            
        Returns:
            Price in output token units
        """
        try:
            # Get quote for 1 unit of input token
            quote = await self.get_quote(input_mint, output_mint, 1.0)
            
            if "outAmount" not in quote:
                raise TradingError("Invalid quote response")
            
            # Convert output amount to price
            out_amount = int(quote["outAmount"])
            
            if output_mint == "So11111111111111111111111111111111111111112":
                # Convert lamports to SOL
                return out_amount / 1e9
            else:
                # For token-to-token, we'd need to know decimals
                # This is simplified - assume 6 decimals for output token
                return out_amount / 1e6
                
        except Exception as e:
            raise TradingError(f"Failed to get price: {e}")
    
    async def get_token_price_usd(self, token_mint: str) -> float:
        """
        Get token price in USD using USDC as reference
        
        Args:
            token_mint: Token mint address
            
        Returns:
            Price in USD
        """
        try:
            # Get price in USDC
            usdc_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
            
            if token_mint == usdc_mint:
                return 1.0  # USDC is 1:1 with USD
            
            # Get price in USDC
            price_in_usdc = await self.get_price(token_mint, usdc_mint)
            
            # For SOL, we need to handle the conversion properly
            if token_mint == "So11111111111111111111111111111111111111112":
                # SOL price in USDC is already correct
                return price_in_usdc
            
            return price_in_usdc
                
        except Exception as e:
            raise TradingError(f"Failed to get USD price: {e}")
    
    def is_network_supported(self) -> bool:
        """Check if current network is supported by Jupiter"""
        return self.network in ["mainnet-beta", "devnet", "testnet"]
    
    def is_devnet(self) -> bool:
        """Check if using devnet"""
        return self.network == "devnet"
    
    async def health_check(self) -> bool:
        """Check if Jupiter API is healthy"""
        try:
            headers = {
                "x-api-key": self.api_key,
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}{self.quote_endpoint}", params={
                    "inputMint": "So11111111111111111111111111111111111111112",
                    "outputMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
                    "amount": 1000000,  # 0.001 SOL
                    "slippageBps": 50
                }, headers=headers) as resp:
                    return resp.status == 200
        except:
            return False