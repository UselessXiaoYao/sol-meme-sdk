"""
Jupiter Aggregator client for Solana token swaps with MEV protection
"""

import asyncio
import aiohttp
import time
import logging
import base64
from typing import Dict, Any, Optional, List, Callable
from decimal import Decimal
from solders.transaction import VersionedTransaction
from solders.signature import Signature

from .exceptions import TradingError
from .unified_config import get_config, reload_config, get_private_rpc_url
from .priority_fee import PriorityFeeEstimator
from .wallet import Wallet

logger = logging.getLogger(__name__)


class JupiterClient:
    """Jupiter Aggregator API client with MEV protection support"""
    
    def __init__(self, network: str = None, api_key: str = None):
        """
        Initialize Jupiter client with MEV protection
        
        Args:
            network: Solana network (mainnet-beta, devnet, testnet). If None, uses config.
            api_key: Jupiter API key. If None, uses config.
        """
        # 强制重新加载配置以确保获取最新设置
        config = reload_config()
        self.network = network or config.solana_network
        self.api_key = api_key or config.jupiter_api_key
        self.base_url = "https://api.jup.ag"
        
        # Rate limiting
        self.rate_limiter = asyncio.Semaphore(5)  # Limit concurrent requests
        self.last_call = 0
        self.min_interval = 0.2  # Minimum 200ms between calls
        
        # 初始化优先级费用估算服务（仅用于非Jupiter交易）
        self.rpc_url = get_private_rpc_url()
        self.priority_fee_estimator = PriorityFeeEstimator(self.rpc_url)
        
        # Network-specific configuration
        self._setup_network_config()
        
        if not self.api_key:
            logger.warning("No API key provided. Jupiter API calls will fail. "
                         "Get a free API key at https://portal.jup.ag/")
        
        logger.info(f"JupiterClient initialized for {self.network}")
    
    # _get_rpc_url 方法已移除，使用全局配置函数 get_private_rpc_url() 和 get_public_rpc_url()
    
    def _setup_network_config(self):
        """Setup network-specific configuration based on official Swap API V2"""
        # Jupiter Swap API V2 endpoints based on official documentation
        self.base_url = "https://api.jup.ag"
        # Swap API V2 endpoints
        self.order_endpoint = "/swap/v2/order"      # Get order with assembled transaction
        self.build_endpoint = "/swap/v2/build"       # Get raw swap instructions
        self.execute_endpoint = "/swap/v2/execute"   # Execute signed transaction
        self.tokens_endpoint = "/tokens/v2"          # Token search and info
        self.price_endpoint = "/price/v3"            # Price API (v3 for current documentation)
        
        # Network-specific settings for Swap API V2
        self.network_configs = {
            "mainnet-beta": {
                "supported_tokens": True,
                "quote_timeout": 10,
                "max_attempts": 3,
                "api_version": "v2",
                "features": {
                    "managed_execution": True,      # Jupiter handles transaction landing
                    "rfq_routing": True,           # JupiterZ RFQ market makers
                    "gasless_support": True,        # Automatic gasless for eligible trades
                    "rtse_enabled": True,          # Real-time slippage estimation
                    "all_routers": True            # All routers compete (Metis, JupiterZ, Dflow, OKX)
                }
            },
            "devnet": {
                "supported_tokens": False,        # Limited token support on devnet
                "quote_timeout": 15,               # Longer timeout for devnet
                "max_attempts": 1,                 # Single attempt on devnet
                "fallback_dex": ["RAYDIUM", "METEORA"],
                "api_version": "v2",
                "features": {
                    "managed_execution": False,
                    "rfq_routing": False,
                    "gasless_support": False,
                    "rtse_enabled": False,
                    "all_routers": False
                }
            },
            "testnet": {
                "supported_tokens": False,
                "quote_timeout": 15,
                "max_attempts": 1,
                "fallback_dex": ["RAYDIUM"],
                "api_version": "v2",
                "features": {
                    "managed_execution": False,
                    "rfq_routing": False,
                    "gasless_support": False,
                    "rtse_enabled": False,
                    "all_routers": False
                }
            }
        }
        
        config = self.network_configs.get(self.network, self.network_configs["mainnet-beta"])
        self.supported_tokens = config["supported_tokens"]
        self.quote_timeout = config["quote_timeout"]
        self.max_attempts = config["max_attempts"]
        self.fallback_dex = config.get("fallback_dex", [])
        self.api_version = config["api_version"]
        self.features = config["features"]
        
        # Devnet专用配置
        if self.is_devnet():
            self.devnet_usdc_mint = "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU"
            self.devnet_supported_tokens = [self.devnet_usdc_mint]
            logger.warning(f"Jupiter API在devnet上功能受限，仅支持有限代币: {self.devnet_supported_tokens}")
    
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
    
    async def get_order(
        self, 
        input_mint: str, 
        output_mint: str, 
        amount: float,
        taker: str = None,
        slippage_bps: int = 50,
        fee_bps: int = None,
        restrict_intermediate_tokens: bool = True,
        prioritization_fee_lamports: str = "auto"
    ) -> Dict[str, Any]:
        """
        Get swap order from Jupiter Swap API V2
        
        Args:
            input_mint: Input token mint address
            output_mint: Output token mint address  
            amount: Amount to swap (in smallest units of input token)
            taker: Taker address (required for assembled transaction)
            slippage_bps: Slippage in basis points (1 = 0.01%)
            fee_bps: Integrator fee in basis points
            restrict_intermediate_tokens: Whether to restrict intermediate tokens
            prioritization_fee_lamports: Priority fee setting ("auto" or specific lamports)
            
        Returns:
            Order response with quote and assembled transaction
        """
        await self._rate_limited_call()
        
        # Devnet环境检查
        if self.is_devnet():
            # 检查是否支持devnet上的代币对
            supported_tokens = ["So11111111111111111111111111111111111111112", 
                              self.devnet_usdc_mint]
            if input_mint not in supported_tokens or output_mint not in supported_tokens:
                raise TradingError(
                    f"Jupiter API在devnet上不支持此代币对: {input_mint} → {output_mint}\\n"
                    f"支持的代币: {supported_tokens}\\n"
                    f"建议使用Raydium或Meteora DEX"
                )
        
        try:
            # Convert amount to smallest units
            if input_mint == "So11111111111111111111111111111111111111112":  # SOL
                amount_lamports = int(amount * 1e9)
            else:
                # For tokens, we need to know decimals - this is simplified
                amount_lamports = int(amount * 1e6)  # Assume 6 decimals
            
            # Base parameters for Swap API V2
            params = {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": str(amount_lamports),
                "slippageBps": slippage_bps,
                "restrictIntermediateTokens": str(restrict_intermediate_tokens).lower()
            }
            
            # Add optional parameters
            if taker:
                params["taker"] = taker
            
            if fee_bps:
                params["platformFeeBps"] = fee_bps
            
            # 添加优先级费用参数
            if prioritization_fee_lamports:
                params["prioritizationFeeLamports"] = prioritization_fee_lamports
            
            return await self._make_api_request(self.order_endpoint, params)
                    
        except Exception as e:
            # 提供更友好的错误信息
            if "Invalid outputMint" in str(e):
                raise TradingError(
                    f"Jupiter API在{self.network}上不支持此代币对: {input_mint} → {output_mint}\\n"
                    f"错误详情: {e}\\n"
                    f"建议在devnet上使用Raydium或Meteora DEX"
                )
            raise TradingError(f"Failed to get order from Jupiter: {e}")
    
    async def execute_order(
        self, 
        signed_transaction: str, 
        request_id: str
    ) -> Dict[str, Any]:
        """
        Execute a signed swap transaction
        
        Args:
            signed_transaction: Base64-encoded signed transaction
            request_id: Request ID from the order response
            
        Returns:
            Execution result with status and signature
        """
        await self._rate_limited_call()
        
        try:
            data = {
                "signedTransaction": signed_transaction,
                "requestId": request_id
            }
            
            headers = {
                "x-api-key": self.api_key,
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}{self.execute_endpoint}", 
                    json=data, 
                    headers=headers,
                    timeout=30
                ) as resp:
                    if resp.status == 429:
                        raise TradingError("Jupiter API rate limit exceeded")
                    elif resp.status != 200:
                        error_text = await resp.text()
                        raise TradingError(f"Jupiter API error {resp.status}: {error_text}")
                    
                    result = await resp.json()
                    
                    if "error" in result:
                        raise TradingError(f"Jupiter execution error: {result['error']}")
                    
                    return result
                    
        except aiohttp.ClientError as e:
            raise TradingError(f"Network error calling Jupiter API: {e}")
        except Exception as e:
            raise TradingError(f"Failed to execute Jupiter order: {e}")
    
    async def get_quote(
        self, 
        input_mint: str, 
        output_mint: str, 
        amount: float,
        slippage_bps: int = 50
    ) -> Dict[str, Any]:
        """
        Get price quote only (without transaction) - for price checking
        
        Args:
            input_mint: Input token mint address
            output_mint: Output token mint address  
            amount: Amount to swap
            slippage_bps: Slippage in basis points
            
        Returns:
            Quote response without transaction
        """
        # Use get_order without taker to get quote only
        return await self.get_order(
            input_mint=input_mint,
            output_mint=output_mint,
            amount=amount,
            slippage_bps=slippage_bps,
            taker=None  # No taker = quote only, no transaction
        )
    
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
                
                # 使用build_endpoint构建交易
                async with session.post(f"{self.base_url}{self.build_endpoint}", json=data, headers=headers) as resp:
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
        Search for tokens using Jupiter Tokens API V2
        
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
            
            return await self._make_api_request(f"{self.tokens_endpoint}/search", params)
                    
        except Exception as e:
            raise TradingError(f"Failed to search tokens: {e}")
    
    async def get_token_info(self, mint_address: str) -> Dict[str, Any]:
        """
        Get detailed token information
        
        Args:
            mint_address: Token mint address
            
        Returns:
            Token information dictionary
        """
        await self._rate_limited_call()
        
        try:
            return await self._make_api_request(f"{self.tokens_endpoint}/{mint_address}", {})
                    
        except Exception as e:
            raise TradingError(f"Failed to get token info: {e}")
    
    async def get_prices(self, tokens: List[str]) -> Dict[str, Any]:
        """
        Get USD prices for multiple tokens
        
        Args:
            tokens: List of token mint addresses
            
        Returns:
            Price information dictionary
        """
        await self._rate_limited_call()
        
        try:
            if len(tokens) > 50:
                raise TradingError("Maximum 50 tokens per price request")
            
            params = {
                "ids": ",".join(tokens)
            }
            
            return await self._make_api_request(self.price_endpoint, params)
                    
        except Exception as e:
            raise TradingError(f"Failed to get prices: {e}")
    
    async def get_tokens_list(self) -> Dict[str, Any]:
        """Get list of supported tokens from Jupiter"""
        # 使用Jupiter的tokens端点获取完整的代币列表
        await self._rate_limited_call()
        
        try:
            # 获取主流代币列表
            return await self._make_api_request(f"{self.tokens_endpoint}/list", {"onlyTopTokens": True})
        except Exception as e:
            # 如果失败，尝试搜索USDC作为fallback
            logger.warning(f"Failed to get full token list, trying USDC search: {e}")
            return await self.search_tokens("USDC")
    
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
        Get token price in USD using Jupiter Price API v3
        
        Args:
            token_mint: Token mint address
            
        Returns:
            Price in USD
        """
        try:
            # Use Price API v3 for direct USD price
            prices = await self.get_prices([token_mint])
            
            if token_mint in prices:
                price_data = prices[token_mint]
                if isinstance(price_data, dict) and 'usdPrice' in price_data:
                    return float(price_data['usdPrice'])
                elif isinstance(price_data, (int, float)):
                    return float(price_data)
                else:
                    raise TradingError(f"Unexpected price data format: {price_data}")
            
            # Fallback: check if it's USDC
            usdc_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
            if token_mint == usdc_mint:
                return 1.0
            
            # Fallback to swap-based pricing
            price_in_usdc = await self.get_price(token_mint, usdc_mint)
            return price_in_usdc
                
        except Exception as e:
            raise TradingError(f"Failed to get USD price: {e}")
    
    async def get_price(self, input_mint: str, output_mint: str) -> float:
        """
        Get price for token pair using Jupiter Swap API
        
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
    
    async def analyze_order_response(self, order_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze Jupiter Swap API V2 order response
        
        Args:
            order_response: Order response from get_order()
            
        Returns:
            Analysis with V2 API insights
        """
        analysis = {
            'features_used': [],
            'route_quality': 'unknown',
            'router': 'unknown',
            'execution_mode': 'unknown',
            'price_impact': 0.0,
            'recommendations': []
        }
        
        try:
            # Analyze router information
            if 'router' in order_response:
                analysis['router'] = order_response['router']
                
                # Router-specific insights
                if order_response['router'] == 'jupiterz':
                    analysis['features_used'].append('rfq_routing')
                    analysis['recommendations'].append('RFQ routing - potentially better pricing')
                elif order_response['router'] == 'iris':
                    analysis['features_used'].append('metis_routing')
                    analysis['recommendations'].append('Metis routing - on-chain aggregation')
                elif order_response['router'] in ['dflow', 'okx']:
                    analysis['features_used'].append('third_party_routing')
                    analysis['recommendations'].append('Third-party routing - additional liquidity')
            
            # Analyze execution mode
            if 'mode' in order_response:
                analysis['execution_mode'] = order_response['mode']
                
                if order_response['mode'] == 'ultra':
                    analysis['features_used'].append('managed_execution')
                    analysis['recommendations'].append('Ultra mode - Jupiter handles transaction landing')
                elif order_response['mode'] == 'manual':
                    analysis['recommendations'].append('Manual mode - custom parameters used')
            
            # Analyze route plan
            if 'routePlan' in order_response:
                routes = order_response['routePlan']
                analysis['route_count'] = len(routes)
                
                # Analyze route quality based on number of hops
                if len(routes) == 1:
                    analysis['route_quality'] = 'excellent'
                    analysis['recommendations'].append('Direct route - optimal execution')
                elif len(routes) <= 3:
                    analysis['route_quality'] = 'good'
                    analysis['recommendations'].append('Multi-hop route - acceptable execution')
                else:
                    analysis['route_quality'] = 'poor'
                    analysis['recommendations'].append('Complex route - consider alternative DEX')
            
            # Check for price impact data
            if 'priceImpactPct' in order_response:
                analysis['price_impact'] = float(order_response['priceImpactPct'])
                
                # Add recommendation based on price impact
                if analysis['price_impact'] < 0.5:
                    analysis['recommendations'].append('Low price impact - good for large trades')
                elif analysis['price_impact'] < 2.0:
                    analysis['recommendations'].append('Moderate price impact - acceptable')
                else:
                    analysis['recommendations'].append('High price impact - consider smaller trade size')
            
            # Check if transaction is provided (indicates taker was provided)
            if 'transaction' in order_response and order_response['transaction']:
                analysis['features_used'].append('assembled_transaction')
                analysis['recommendations'].append('Assembled transaction ready for signing')
            
            return analysis
            
        except Exception as e:
            logger.warning(f"Failed to analyze order response: {e}")
            return analysis
    
    def get_api_status(self) -> Dict[str, Any]:
        """
        Get status of Jupiter API V2 for current network
        
        Returns:
            API status dictionary
        """
        return {
            'network': self.network,
            'api_version': self.api_version,
            'features_enabled': self.features,
            'recommendation': 'Use mainnet-beta for full Swap API V2 features'
        }
    
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
    
    async def swap_tokens(
        self,
        input_mint: str,
        output_mint: str,
        amount: float,
        wallet: Wallet,
        slippage_bps: int = 50,
        priority_fee_micro_lamports: Optional[int] = None,
        jito_tip: Optional[int] = None
    ) -> Dict[str, Any]:
        """执行代币交换（支持优先费和小费）
        
        Args:
            input_mint: 输入代币mint地址
            output_mint: 输出代币mint地址
            amount: 交换数量
            wallet: 钱包对象
            slippage_bps: 滑点容忍度
            priority_fee_micro_lamports: 优先级费用（微lamports）
            jito_tip: Jito小费（lamports）
            
        Returns:
            交易结果
        """
        try:
            # 获取订单（包含组装的交易）
            order = await self.get_order(
                input_mint=input_mint,
                output_mint=output_mint,
                amount=amount,
                taker=str(wallet.pubkey),
                slippage_bps=slippage_bps
            )
            
            if 'transaction' not in order or not order['transaction']:
                raise TradingError("Jupiter API未返回组装交易")
            
            # 解码交易
            tx_bytes = base64.b64decode(order['transaction'])
            transaction = VersionedTransaction.from_bytes(tx_bytes)
            
            # 注意：Jupiter API已经自动处理优先级费用，无需手动添加Jito小费
            # 如果确实需要Jito小费，应在交易构建阶段包含
            
            # 使用钱包签名交易
            signed_tx = wallet.sign_transaction(transaction)
            
            # 执行交易
            result = await self.execute_order(
                signed_transaction=base64.b64encode(bytes(signed_tx)).decode('utf-8'),
                request_id=order.get('requestId', '')
            )
            
            # 检查交易状态
            if result.get('status') == 'success':
                tx_hash = result.get('signature')
                
                # 等待交易确认
                from solana.rpc.api import Client
                rpc_client = Client(self.rpc_url)
                
                # 简单的确认检查
                for i in range(10):
                    await asyncio.sleep(2)
                    try:
                        signature = Signature.from_string(tx_hash)
                        status = rpc_client.get_signature_statuses([signature])
                        if status.value and status.value[0]:
                            if status.value[0].confirmation_status in ['confirmed', 'finalized']:
                                break
                    except:
                        pass
                
                return {
                    'input_mint': input_mint,
                    'output_mint': output_mint,
                    'input_amount': amount,
                    'output_amount': order.get('outAmount', 0),
                    'price_impact': order.get('priceImpactPct', 0),
                    'slippage_bps': slippage_bps,
                    'priority_fee': priority_fee_micro_lamports,
                    'jito_tip': jito_tip,
                    'tx_hash': tx_hash,
                    'status': 'success'
                }
            else:
                raise TradingError(f"交易执行失败: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            raise TradingError(f"Jupiter交换失败: {e}")
    
    async def execute_trade_with_mev_protection(
        self,
        input_mint: str,
        output_mint: str,
        amount: float,
        wallet: Wallet,
        slippage_bps: int = 50,
        priority_level: str = "medium",
        jito_tip: Optional[int] = None,
        max_attempts: int = 3
    ) -> Dict[str, Any]:
        """执行交易并包含MEV防护功能
        
        Args:
            input_mint: 输入代币mint地址
            output_mint: 输出代币mint地址
            amount: 交换数量
            wallet: 钱包对象
            slippage_bps: 滑点容忍度
            priority_level: 优先级级别（low, medium, high, very_high）
            jito_tip: Jito小费金额
            max_attempts: 最大尝试次数
            
        Returns:
            交易结果
        """
        return await self.mev_protection.execute_with_mev_protection(
            self.swap_tokens,
            input_mint,
            output_mint,
            amount,
            wallet,
            slippage_bps=slippage_bps,
            priority_level=priority_level,
            jito_tip=jito_tip,
            max_attempts=max_attempts
        )
    
    async def buy_token(
        self,
        token_mint: str,
        sol_amount: float,
        wallet: Wallet,
        slippage_bps: int = 50,
        priority_fee_micro_lamports: Optional[int] = None,
        jito_tip: Optional[int] = None
    ) -> Dict[str, Any]:
        """购买代币（用SOL购买）
        
        Args:
            token_mint: 目标代币mint地址
            sol_amount: SOL数量
            wallet: 钱包对象
            slippage_bps: 滑点容忍度
            priority_fee_micro_lamports: 优先级费用（微lamports）
            jito_tip: Jito小费（lamports）
            
        Returns:
            购买结果
        """
        return await self.swap_tokens(
            input_mint="So11111111111111111111111111111111111111112",  # SOL
            output_mint=token_mint,
            amount=sol_amount,
            wallet=wallet,
            slippage_bps=slippage_bps,
            priority_fee_micro_lamports=priority_fee_micro_lamports,
            jito_tip=jito_tip
        )
    
    async def sell_token(
        self,
        token_mint: str,
        token_amount: float,
        wallet: Wallet,
        slippage_bps: int = 50,
        priority_fee_micro_lamports: Optional[int] = None,
        jito_tip: Optional[int] = None
    ) -> Dict[str, Any]:
        """出售代币（换成SOL）
        
        Args:
            token_mint: 出售代币mint地址
            token_amount: 代币数量
            wallet: 钱包对象
            slippage_bps: 滑点容忍度
            priority_fee_micro_lamports: 优先级费用（微lamports）
            jito_tip: Jito小费（lamports）
            
        Returns:
            出售结果
        """
        return await self.swap_tokens(
            input_mint=token_mint,
            output_mint="So11111111111111111111111111111111111111112",  # SOL
            amount=token_amount,
            wallet=wallet,
            slippage_bps=slippage_bps,
            priority_fee_micro_lamports=priority_fee_micro_lamports,
            jito_tip=jito_tip
        )
    
    def get_mev_config(self) -> Dict[str, Any]:
        """获取MEV配置信息"""
        return {
            'rpc_url': self.rpc_url,
            'default_tips': self.mev_protection.default_tips,
            'jito_tip_account': str(self.mev_protection.jito_tip_account),
            'supported_priority_levels': ['low', 'medium', 'high', 'very_high']
        }
    
    async def get_recommended_fees(
        self, 
        priority_level: str = "medium"
    ) -> Dict[str, Any]:
        """获取推荐的费用配置
        
        Args:
            priority_level: 优先级级别
            
        Returns:
            推荐费用配置
        """
        fee_estimate = await self.mev_protection.get_priority_fee_estimate()
        recommended_tip = self.mev_protection.get_recommended_tip(priority_level)
        
        return {
            'priority_level': priority_level,
            'priority_fee_micro_lamports': fee_estimate.get(priority_level, 5000),
            'jito_tip': recommended_tip,
            'fee_estimates': fee_estimate,
            'recommendation': f'使用{priority_level}优先级配置，确保交易快速确认'
        }