"""
Multi-DEX Trading Engine - High-level trading interface that aggregates multiple DEX clients
Supports Jupiter, Raydium, and other Solana DEXs for optimal trade execution
"""

import asyncio
import logging
import time
import base64
from typing import Optional, List, Dict, Any
from solana.rpc.api import Client
from solana.rpc.types import TxOpts
from solders.transaction import Transaction, VersionedTransaction

from .models import TradeOrder, TradeResult, OrderType, OrderSide, TransactionConfig
from .exceptions import TradingError, InsufficientFundsError, InvalidTokenError
from .jupiter_client import JupiterClient
from .raydium_client import RaydiumClient
from .priority_fee import PriorityFeeEstimator

logger = logging.getLogger(__name__)


class TradingEngine:
    """Multi-DEX trading engine for executing meme coin trades on Solana
    
    Features:
    - Aggregates multiple DEX clients (Jupiter, Raydium, etc.)
    - Auto-selects optimal trading route based on price and liquidity
    - Supports MEV protection and priority fees
    - Fallback mechanisms for reliability
    """

    def __init__(self, wallet, config: Optional[TransactionConfig] = None, 
                 jupiter_client: Optional[JupiterClient] = None, 
                 raydium_client: Optional[RaydiumClient] = None):
        """
        Initialize multi-DEX trading engine
        
        Args:
            wallet: Wallet instance for signing transactions
            config: Transaction configuration
            jupiter_client: Pre-configured Jupiter client (optional)
            raydium_client: Pre-configured Raydium client (optional)
        """
        self.wallet = wallet
        self.config = config or TransactionConfig()
        
        # Use provided clients or create new ones
        network = "devnet" if self.config.enable_devnet_testing else "mainnet-beta"
        
        # Devnet-specific configuration (先设置is_devnet属性)
        self.is_devnet = network == "devnet"
        
        self.jupiter_client = jupiter_client or JupiterClient(network)
        self.raydium_client = raydium_client or RaydiumClient(network)
        
        # Network-specific token addresses
        self.common_tokens = self._get_network_tokens(network)
        
        # 初始化优先级费用估算服务（仅用于非Jupiter交易）
        rpc_url = self._get_rpc_url()
        self.priority_fee_estimator = PriorityFeeEstimator(rpc_url)
        
        if self.is_devnet:
            logger.warning("Devnet环境启用 - 部分DEX功能可能受限")
            logger.info(f"Devnet USDC地址: {self.common_tokens['USDC']}")
            logger.info(f"Devnet SOL地址: {self.common_tokens['SOL']}")
        
        # DEX selection strategy from config
        self.dex_priority = self.config.dex_priority
        
        logger.info(f"Multi-DEX TradingEngine initialized for {network}")
    
    def _get_rpc_url(self) -> str:
        """Get RPC URL - 使用全局私有RPC配置（用于交易执行）"""
        from .unified_config import get_private_rpc_url
        return get_private_rpc_url()
    
    def _get_public_rpc_url(self) -> str:
        """Get public RPC URL - 用于查询和验证"""
        from .unified_config import get_public_rpc_url
        return get_public_rpc_url()
    
    def _get_network_tokens(self, network: str) -> Dict[str, str]:
        """Get token addresses for specific network"""
        if network == "devnet":
            # Devnet-specific token addresses
            return {
                "SOL": "So11111111111111111111111111111111111111112",
                "WSOL": "So11111111111111111111111111111111111111112",
                "USDC": "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU",
            }
        else:
            # Mainnet token addresses
            return {
                "SOL": "So11111111111111111111111111111111111111112",
                "WSOL": "So11111111111111111111111111111111111111112",
                "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            }

    async def buy_token(
        self,
        token_address: str,
        amount_sol: float,
        slippage: float = 0.5,
        token_info: Optional[Dict] = None,
        use_jito_tip: bool = False,
        priority_level: str = "medium"
    ) -> TradeResult:
        """
        Buy meme token with SOL
        
        Args:
            token_address: Token mint address
            amount_sol: Amount of SOL to spend
            slippage: Slippage tolerance percentage
            token_info: Optional token information
            use_jito_tip: Use Jito tip protection (Raydium path)
            priority_level: Priority level (low, medium, high, very_high)
            
        Returns:
            TradeResult with execution details
        """
        try:
            # Validate inputs
            if amount_sol <= 0:
                raise TradingError("Amount must be positive")
            
            # Get token information if not provided
            if not token_info:
                token_info = await self._get_token_info(token_address)
            
            # Calculate expected token amount
            expected_tokens = await self._calculate_buy_amount(
                token_address, amount_sol, slippage
            )
            
            # 根据是否使用Jito tip选择不同的执行路径
            if use_jito_tip:
                # 使用Raydium路径（支持Jito tip）
                logger.info(f"🛡️ 使用Raydium路径购买代币（包含Jito tip保护）")
                result = await self.raydium_client.execute_trade_with_mev_protection(
                    input_mint="So11111111111111111111111111111111111111112",  # SOL
                    output_mint=token_address,
                    amount=int(amount_sol * 10**9),  # 转换为lamports
                    wallet=self.wallet,
                    slippage_bps=int(slippage * 100),  # 转换为basis points
                    priority_level=priority_level,
                    jito_tip=None,  # 使用推荐值
                    max_attempts=3
                )
                
                # 转换为TradeResult格式
                return TradeResult(
                    success=True,
                    tx_hash=result.get('tx_hash', ''),
                    input_amount=amount_sol,
                    output_amount=expected_tokens,
                    fees=result.get('fees', 0),
                    execution_time=time.time()
                )
            else:
                # 使用Jupiter路径（托管执行，自动优先级费用）
                logger.info(f"🚀 使用Jupiter路径购买代币（托管执行）")
                return await self._execute_trade(
                    TradeOrder(
                        token_address=token_address,
                        side=OrderSide.BUY,
                        order_type=OrderType.MARKET,
                        amount=amount_sol,
                        slippage=slippage
                    ),
                    expected_tokens
                )
            
        except Exception as e:
            logger.error(f"Buy token failed: {e}")
            raise TradingError(f"Buy token failed: {e}")

    async def sell_token(
        self,
        token_address: str,
        amount_tokens: float,
        slippage: float = 0.5,
        token_info: Optional[Dict] = None,
        use_jito_tip: bool = False,
        priority_level: str = "medium"
    ) -> TradeResult:
        """
        Sell meme token for SOL
        
        Args:
            token_address: Token mint address
            amount_tokens: Amount of tokens to sell
            slippage: Slippage tolerance percentage
            token_info: Optional token information
            use_jito_tip: Use Jito tip protection (Raydium path)
            priority_level: Priority level (low, medium, high, very_high)
            
        Returns:
            TradeResult with execution details
        """
        try:
            # Validate inputs
            if amount_tokens <= 0:
                raise TradingError("Amount must be positive")
            
            # Get token information if not provided
            if not token_info:
                token_info = await self._get_token_info(token_address)
            
            # Calculate expected SOL amount
            expected_sol = await self._calculate_sell_amount(
                token_address, amount_tokens, slippage
            )
            
            # 根据是否使用Jito tip选择不同的执行路径
            if use_jito_tip:
                # 使用Raydium路径（支持Jito tip）
                logger.info(f"🛡️ 使用Raydium路径出售代币（包含Jito tip保护）")
                result = await self.raydium_client.execute_trade_with_mev_protection(
                    input_mint=token_address,
                    output_mint="So11111111111111111111111111111111111111112",  # SOL
                    amount=int(amount_tokens * 10**token_info.get('decimals', 6)),  # 转换为最小单位
                    wallet=self.wallet,
                    slippage_bps=int(slippage * 100),  # 转换为basis points
                    priority_level=priority_level,
                    jito_tip=None,  # 使用推荐值
                    max_attempts=3
                )
                
                # 转换为TradeResult格式
                return TradeResult(
                    success=True,
                    tx_hash=result.get('tx_hash', ''),
                    input_amount=amount_tokens,
                    output_amount=expected_sol,
                    fees=result.get('fees', 0),
                    execution_time=time.time()
                )
            else:
                # 使用Jupiter路径（托管执行，自动优先级费用）
                logger.info(f"🚀 使用Jupiter路径出售代币（托管执行）")
                return await self._execute_trade(
                    TradeOrder(
                        token_address=token_address,
                        side=OrderSide.SELL,
                        order_type=OrderType.MARKET,
                        amount=amount_tokens,
                        slippage=slippage
                    ),
                    expected_sol
                )
            
        except Exception as e:
            logger.error(f"Sell token failed: {e}")
            raise TradingError(f"Sell token failed: {e}")

    async def _get_token_info(self, token_address: str) -> Dict[str, Any]:
        """Get token information by directly querying token details"""
        try:
            # 首先尝试直接获取代币信息
            if self.jupiter_client:
                try:
                    token_info = await self.jupiter_client.get_token_info(token_address)
                    if token_info:
                        return {
                            "address": token_address,
                            "decimals": token_info.get("decimals", 6),
                            "symbol": token_info.get("symbol", "UNKNOWN"),
                            "name": token_info.get("name", "Unknown Token")
                        }
                except Exception as e:
                    logger.debug(f"Failed to get token info from Jupiter API: {e}")
            
            # 如果直接查询失败，尝试通过价格查询来验证代币是否存在
            try:
                price = await self._get_token_price(token_address)
                logger.info(f"Token {token_address} exists (price: {price} SOL)")
            except Exception as e:
                logger.warning(f"Token {token_address} price query failed: {e}")
                raise TradingError(f"Token {token_address} does not exist or is not tradeable")
            
            # 价格查询成功，说明代币存在，使用默认信息
            return {
                "address": token_address,
                "decimals": 6,
                "symbol": "UNKNOWN",
                "name": "Unknown Token"
            }
            
        except Exception as e:
            logger.warning(f"Failed to get token info: {e}")
            
            # Fallback for devnet/testing
            if self.config.enable_devnet_testing:
                return {
                    "address": token_address,
                    "decimals": 6,
                    "symbol": "UNKNOWN",
                    "name": "Unknown Token"
                }
            else:
                raise TradingError(f"Failed to get token information: {e}")

    async def _get_token_balance(self, token_address: str) -> float:
        """Get token balance for wallet"""
        try:
            # Create a synchronous RPC client for balance checking - 使用公共RPC（查询）
            from solana.rpc.api import Client
            rpc_url = self._get_public_rpc_url()
            rpc_client = Client(rpc_url)
            
            # Get token balances from wallet (synchronous call)
            token_balances = self.wallet.get_token_balances(rpc_client)
            
            # Return balance for specific token
            balance = token_balances.get(token_address, 0.0)
            logger.debug(f"Token balance for {token_address}: {balance}")
            return balance
            
        except Exception as e:
            raise TradingError(f"Failed to get token balance: {e}")
    
    async def get_balance(self, token_address: str) -> float:
        """Get token balance for wallet (public method)"""
        return await self._get_token_balance(token_address)
    
    async def _get_sol_balance(self) -> float:
        """Get SOL balance for wallet"""
        try:
            from solana.rpc.api import Client
            rpc_url = self._get_public_rpc_url()  # 使用公共RPC（查询）
            
            # 每次查询都创建新的RPC客户端，避免缓存
            rpc_client = Client(rpc_url)
            
            # Get SOL balance from wallet
            sol_balance = self.wallet.get_balance(rpc_client)
            logger.debug(f"SOL balance: {sol_balance}")
            
            return sol_balance
            
        except Exception as e:
            raise TradingError(f"Failed to get SOL balance: {e}")
    
    async def get_token_price(self, token_address: str) -> float:
        """Public method to get token price in SOL"""
        return await self._get_token_price(token_address)

    async def _calculate_buy_amount(
        self, token_address: str, amount_sol: float, slippage: float
    ) -> float:
        """Calculate expected token amount for buy order"""
        try:
            # 使用多源价格查询获取最佳价格
            price = await self._get_best_token_price(token_address)
            
            # 考虑交易费用和滑点
            fee_amount = amount_sol * 0.003  # 0.3% 交易费
            available_sol = amount_sol - fee_amount
            
            # 计算预期代币数量
            expected_tokens = available_sol / price
            
            # 应用滑点保护
            min_tokens = expected_tokens * (1 - slippage / 100)
            
            logger.info(f"Buy calculation: {amount_sol} SOL -> {min_tokens:.6f} tokens (price: {price:.6f} SOL/token)")
            return min_tokens
        except Exception as e:
            raise TradingError(f"Failed to calculate buy amount: {e}")

    async def _calculate_sell_amount(
        self, token_address: str, amount_tokens: float, slippage: float
    ) -> float:
        """Calculate expected SOL amount for sell order"""
        try:
            # 使用多源价格查询获取最佳价格
            price = await self._get_best_token_price(token_address)
            
            # 计算预期SOL数量
            expected_sol = amount_tokens * price
            
            # 考虑交易费用
            fee_amount = expected_sol * 0.003  # 0.3% 交易费
            
            # 应用滑点保护
            min_sol = (expected_sol - fee_amount) * (1 - slippage / 100)
            
            logger.info(f"Sell calculation: {amount_tokens} tokens -> {min_sol:.6f} SOL (price: {price:.6f} SOL/token)")
            return min_sol
        except Exception as e:
            raise TradingError(f"Failed to calculate sell amount: {e}")

    async def _get_token_price(self, token_address: str) -> float:
        """Get current token price in SOL using multiple DEX sources"""
        # 如果是SOL本身，价格为1 SOL
        if token_address == self.common_tokens["SOL"]:
            logger.debug(f"SOL price: 1.0 SOL (base token)")
            return 1.0
            
        try:
            # 使用多DEX价格获取策略
            price = await self._get_best_token_price(token_address)
            logger.debug(f"Got price for {token_address}: {price} SOL")
            return price
            
        except Exception as e:
            logger.warning(f"Failed to get price from DEX sources for {token_address}: {e}")
            
            # Fallback to placeholder price for devnet/testing
            if self.config.enable_devnet_testing:
                logger.info("Using placeholder price for devnet testing")
                return 0.001  # 0.001 SOL per token
            else:
                raise TradingError(f"Failed to get token price: {e}")

    async def _execute_trade(self, order: TradeOrder, expected_amount: float) -> TradeResult:
        """Execute trade on blockchain using Jupiter V2 API when possible"""
        try:
            # 构建交易
            transaction = await self._build_trade_transaction(order, expected_amount)
            
            # 如果是Jupiter交易，使用V2 API的execute_order方法
            if hasattr(transaction, 'data') and 'jupiter' in str(transaction).lower():
                # 尝试使用Jupiter V2的托管执行功能
                return await self._execute_jupiter_v2_trade(order, expected_amount)
            
            # 所有交易对象都通过钱包进行签名
            # 钱包会自动处理 VersionedTransaction 和传统 Transaction
            signed_tx = self.wallet.sign_transaction(transaction)
            
            # 发送交易
            tx_hash = await self._send_transaction_with_retry(signed_tx)
            
            # 等待确认
            confirmed = await self._wait_for_confirmation(tx_hash)
            
            if not confirmed:
                raise TradingError("Transaction not confirmed")
            
            # 等待1秒确保链上数据稳定（对于某些RPC节点可能有延迟）
            await asyncio.sleep(1.0)
            
            # 从链上获取实际的交易执行结果
            try:
                actual_result = await self._get_actual_trade_result(tx_hash, order, expected_amount)
                logger.info(f"✅ 交易执行完成 - 实际成交: {actual_result.executed_amount}, 价格: {actual_result.executed_price}")
                return actual_result
            except Exception as parse_error:
                logger.warning(f"无法从链上解析实际交易结果，使用预期值: {parse_error}")
                # 回退到使用预期值
                return TradeResult(
                    order_id=f"{tx_hash[:16]}",
                    token_address=order.token_address,
                    side=order.side,
                    executed_amount=expected_amount,
                    executed_price=await self._get_token_price(order.token_address),
                    total_cost=order.amount if order.side == OrderSide.BUY else expected_amount,
                    transaction_hash=tx_hash,
                    status="completed"
                )
            
        except Exception as e:
            logger.error(f"Trade execution failed: {e}")
            raise TradingError(f"Trade execution failed: {e}")
    
    async def _execute_jupiter_v2_trade(self, order: TradeOrder, expected_amount: float) -> TradeResult:
        """使用Jupiter V2 API执行交易，包括托管执行功能"""
        try:
            # 确定输入输出代币
            if order.side == OrderSide.BUY:
                input_mint = self.common_tokens["SOL"]
                output_mint = order.token_address
                amount = order.amount
            else:  # SELL
                input_mint = order.token_address
                output_mint = self.common_tokens["SOL"]
                amount = order.amount
            
            # 获取Jupiter V2订单（包含组装的交易）
            order_response = await self.jupiter_client.get_order(
                input_mint=input_mint,
                output_mint=output_mint,
                amount=amount,
                taker=self.wallet.address,
                slippage_bps=self.config.jupiter_slippage_bps
            )
            
            # 分析订单响应
            analysis = await self.jupiter_client.analyze_order_response(order_response)
            logger.info(f"Jupiter V2交易分析: {analysis}")
            
            # 检查是否包含组装的交易
            if "transaction" not in order_response or not order_response["transaction"]:
                raise TradingError("No assembled transaction from Jupiter V2")
            
            # 获取请求ID用于执行
            request_id = order_response.get("requestId")
            
            # 解码交易（Jupiter返回的已经是签好名的交易）
            transaction_bytes = base64.b64decode(order_response["transaction"])
            transaction = VersionedTransaction.from_bytes(transaction_bytes)
            
            # 直接使用原始交易数据（已经签名）
            signed_tx_base64 = order_response["transaction"]
            
            # 调试：检查当前交易的状态
            logger.info(f"当前交易签名数量: {len(transaction.signatures)}")
            
            # 尝试直接使用当前交易（应该已经是未签名的）
            try:
                # 自己签名交易
                signed_tx = self.wallet.sign_transaction(transaction)
                
                # 发送已签名的交易
                tx_hash = await self._send_transaction_with_retry(signed_tx)
                confirmed = await self._wait_for_confirmation(tx_hash)
                
                if not confirmed:
                    raise TradingError("Transaction not confirmed")

                # 从链上获取实际的交易执行结果
                try:
                    actual_result = await self._get_actual_trade_result(tx_hash, order, expected_amount)
                    logger.info(f"✅ Jupiter V2交易执行完成 - 实际成交: {actual_result.executed_amount}, 价格: {actual_result.executed_price}")
                    return actual_result
                except Exception as parse_error:
                    logger.warning(f"无法从链上解析Jupiter V2实际交易结果，使用预期值: {parse_error}")
                    # 回退到使用预期值
                    return TradeResult(
                        order_id=f"{tx_hash[:16]}",
                        token_address=order.token_address,
                        side=order.side,
                        executed_amount=expected_amount,
                        executed_price=await self._get_token_price(order.token_address),
                        total_cost=order.amount if order.side == OrderSide.BUY else expected_amount,
                        transaction_hash=tx_hash,
                        status="completed",
                        jupiter_v2_features=analysis.get('features_used', [])
                    )
            except Exception as e:
                logger.warning(f"直接签名失败: {e}")
                
                # 回退方案：重新请求不包含taker的交易
                logger.info("尝试重新获取不包含taker的交易")
                
                # 重新请求Jupiter，不提供taker参数
                fallback_order_response = await self.jupiter_client.get_order(
                    input_mint=input_mint,
                    output_mint=output_mint,
                    amount=amount,
                    # 不提供taker参数
                    slippage_bps=self.config.jupiter_slippage_bps
                )
                
                if "transaction" in fallback_order_response and fallback_order_response["transaction"]:
                    # 解码交易
                    transaction_bytes = base64.b64decode(fallback_order_response["transaction"])
                    transaction = VersionedTransaction.from_bytes(transaction_bytes)
                    
                    # 自己签名交易
                    signed_tx = self.wallet.sign_transaction(transaction)
                    
                # 发送已签名的交易
                tx_hash = await self._send_transaction_with_retry(signed_tx)
                confirmed = await self._wait_for_confirmation(tx_hash)
                
                if not confirmed:
                    raise TradingError("Transaction not confirmed")
                
                # 等待1秒确保链上数据稳定
                await asyncio.sleep(1.0)
                
                # 从链上获取实际的交易执行结果
                try:
                    actual_result = await self._get_actual_trade_result(tx_hash, order, expected_amount)
                    logger.info(f"✅ Jupiter V2回退方案交易执行完成 - 实际成交: {actual_result.executed_amount}, 价格: {actual_result.executed_price}")
                    return actual_result
                except Exception as parse_error:
                    logger.warning(f"无法从链上解析Jupiter V2实际交易结果，使用预期值: {parse_error}")
                    # 回退到使用预期值
                    return TradeResult(
                        order_id=f"{tx_hash[:16]}",
                        token_address=order.token_address,
                        side=order.side,
                        executed_amount=expected_amount,
                        executed_price=await self._get_token_price(order.token_address),
                        total_cost=order.amount if order.side == OrderSide.BUY else expected_amount,
                        transaction_hash=tx_hash,
                        status="completed",
                        jupiter_v2_features=analysis.get('features_used', [])
                    )
                else:
                    raise TradingError("Jupiter API未返回交易数据")
            
            # 最终回退到传统方式
            logger.warning("所有方式失败，尝试传统执行")
            tx_hash = await self._send_transaction_with_retry(signed_tx)
            confirmed = await self._wait_for_confirmation(tx_hash)
            
            if not confirmed:
                raise TradingError("Transaction not confirmed")
            
            return TradeResult(
                order_id=f"{tx_hash[:16]}",
                token_address=order.token_address,
                side=order.side,
                executed_amount=expected_amount,
                executed_price=await self._get_token_price(order.token_address),
                total_cost=order.amount if order.side == OrderSide.BUY else expected_amount,
                transaction_hash=tx_hash,
                status="completed",
                jupiter_v2_features=analysis.get('features_used', [])
            )
            
        except Exception as e:
            logger.error(f"Jupiter V2 trade execution failed: {e}")
            # 回退到传统执行方式
            return await self._execute_traditional_trade(order, expected_amount)
    
    async def _execute_traditional_trade(self, order: TradeOrder, expected_amount: float) -> TradeResult:
        """传统执行方式（不使用Jupiter V2托管执行）"""
        try:
            # 构建交易
            transaction = await self._build_trade_transaction(order, expected_amount)
            
            # 处理不同类型的交易
            if isinstance(transaction, VersionedTransaction):
                # VersionedTransaction已经签名，直接发送
                signed_tx = bytes(transaction)
            else:
                # 传统Transaction需要签名
                signed_tx = self.wallet.sign_transaction(transaction)
            
            # 发送交易
            tx_hash = await self._send_transaction_with_retry(signed_tx)
            
            # 等待确认
            confirmed = await self._wait_for_confirmation(tx_hash)
            
            if not confirmed:
                raise TradingError("Transaction not confirmed")
            
            # 等待1秒确保链上数据稳定（对于某些RPC节点可能有延迟）
            await asyncio.sleep(1.0)
            
            # 创建交易结果
            return TradeResult(
                order_id=f"{tx_hash[:16]}",
                token_address=order.token_address,
                side=order.side,
                executed_amount=expected_amount,
                executed_price=await self._get_token_price(order.token_address),
                total_cost=order.amount if order.side == OrderSide.BUY else expected_amount,
                transaction_hash=tx_hash,
                status="completed"
            )
            
        except Exception as e:
            logger.error(f"Traditional trade execution failed: {e}")
            raise TradingError(f"Traditional trade execution failed: {e}")

    async def _build_trade_transaction(
        self, order: TradeOrder, expected_amount: float
    ) -> VersionedTransaction:
        """Build trade transaction using optimal DEX selection"""
        try:
            # Determine input and output tokens
            if order.side == OrderSide.BUY:
                input_mint = self.common_tokens["SOL"]  # Buy token with SOL
                output_mint = order.token_address
                amount = order.amount  # SOL amount
            else:  # SELL
                input_mint = order.token_address  # Sell token for SOL
                output_mint = self.common_tokens["SOL"]
                amount = order.amount  # Token amount
            
            # Try different DEXs in priority order
            for dex_name in self.dex_priority:
                try:
                    if dex_name == "jupiter":
                        if not self.jupiter_client:
                            continue
                        transaction = await self._build_jupiter_transaction(
                            input_mint, output_mint, amount
                        )
                    elif dex_name == "raydium":
                        if not self.raydium_client:
                            continue
                        transaction = await self._build_raydium_transaction(
                            input_mint, output_mint, amount, order
                        )
                    else:
                        continue
                    
                    if transaction:
                        logger.info(f"Built transaction using {dex_name}")
                        return transaction
                        
                except Exception as e:
                    logger.warning(f"Failed to build transaction with {dex_name}: {e}")
                    continue
            
            # If all DEXs fail, try Jupiter as final fallback
            logger.warning("All DEXs failed, trying Jupiter as final fallback")
            if self.jupiter_client:
                transaction = await self._build_jupiter_transaction(
                    input_mint, output_mint, amount
                )
                
                if transaction:
                    return transaction
            
            # Ultimate fallback - 无法构建交易
            logger.error("All transaction building methods failed, cannot create transaction")
            raise TradingError("Failed to build transaction: All DEX providers failed")
            
        except Exception as e:
            logger.error(f"Failed to build transaction: {e}")
            raise TradingError(f"Failed to build transaction: {e}")
    
    async def _build_jupiter_transaction(
        self, input_mint: str, output_mint: str, amount: float
    ) -> Optional[VersionedTransaction]:
        """Build transaction using Jupiter Swap API V2"""
        try:
            # 使用Jupiter V2 API的get_order方法获取完整的交易
            # 这包括报价和已组装的交易
            order_response = await self.jupiter_client.get_order(
                input_mint=input_mint,
                output_mint=output_mint,
                amount=amount,
                taker=self.wallet.address,  # 提供taker以获取组装的交易
                slippage_bps=self.config.jupiter_slippage_bps,
                prioritization_fee_lamports="auto"  # 启用Jupiter自动优先级费用计算
            )
            
            # 分析订单响应
            analysis = await self.jupiter_client.analyze_order_response(order_response)
            logger.info(f"Jupiter V2路由分析: {analysis}")
            
            # 检查是否包含已组装的交易
            if "transaction" not in order_response or not order_response["transaction"]:
                raise TradingError("No assembled transaction returned from Jupiter V2 API")
            
            # 解码交易 - 使用VersionedTransaction
            transaction_bytes = base64.b64decode(order_response["transaction"])
            transaction = VersionedTransaction.from_bytes(transaction_bytes)
            
            # 调试：检查交易签名状态
            logger.debug(f"交易签名数量: {len(transaction.signatures)}")
            for i, sig in enumerate(transaction.signatures):
                logger.debug(f"签名 {i}: {sig}")
            
            # 记录路由信息
            if "routePlan" in order_response:
                logger.debug(f"Jupiter V2路由计划: {order_response['routePlan']}")
            
            # 记录使用的V2功能
            if analysis.get('features_used'):
                logger.info(f"Jupiter V2功能使用: {analysis['features_used']}")
            
            return transaction
            
        except Exception as e:
            logger.warning(f"Jupiter V2 transaction building failed: {e}")
            return None
    
    async def _build_raydium_transaction(
        self, input_mint: str, output_mint: str, amount: float, order: TradeOrder
    ) -> Optional[Transaction]:
        """Build transaction using Raydium direct pools"""
        try:
            # For Raydium, we need to handle SOL wrapping and specific pool selection
            if input_mint == self.common_tokens["SOL"]:
                # Use WSOL for Raydium trades
                input_mint = self.common_tokens["WSOL"]
            
            # Get swap quote from Raydium
            quote = await self.raydium_client.get_swap_quote(
                input_mint=input_mint,
                output_mint=output_mint,
                amount=amount,
                slippage_bps=self.config.raydium_slippage_bps
            )
            
            # Build transaction
            transaction = await self.raydium_client.build_swap_transaction(
                quote=quote,
                wallet_address=self.wallet.address,
                wrap_sol=True  # Auto-wrap SOL for Raydium
            )
            
            logger.debug(f"Raydium pool used: {quote.get('poolId', 'Unknown')}")
            return transaction
            
        except Exception as e:
            logger.warning(f"Raydium transaction building failed: {e}")
            return None

    async def _send_transaction_with_retry(self, signed_tx: bytes) -> str:
        """Send transaction with retry logic"""
        # Get RPC client from one of the DEX clients
        rpc_client = self._get_rpc_client()
        
        for attempt in range(self.config.max_retries):
            try:
                # Send transaction
                opts = TxOpts(
                    skip_preflight=self.config.skip_preflight,
                    preflight_commitment=self.config.commitment
                )
                
                # Client 是同步的，不需要 await
                result = rpc_client.send_raw_transaction(signed_tx, opts=opts)
                
                if result.value:
                    logger.info(f"✅ 交易发送成功: {result.value}")
                    return str(result.value)
                
                # 检查是否有错误信息
                if hasattr(result, 'error') and result.error:
                    error_msg = str(result.error)
                    logger.error(f"交易发送失败: {error_msg}")
                    
                    # 如果是模拟失败，立即停止
                    if 'simulation' in error_msg.lower() or 'failed' in error_msg.lower():
                        raise TradingError(f"交易模拟失败: {error_msg}")
                
                raise TradingError("Transaction failed to send")
                
            except Exception as e:
                logger.warning(f"Transaction attempt {attempt + 1} failed: {type(e).__name__} - {str(e)}")
                
                # 如果是模拟失败，立即停止重试
                if 'simulation' in str(e).lower() or 'failed' in str(e).lower():
                    raise
                
                if attempt == self.config.max_retries - 1:
                    raise
                
                await asyncio.sleep(self.config.retry_delay)
    
    def _get_rpc_client(self):
        """Get RPC client using the correct RPC URL"""
        from solana.rpc.api import Client
        
        # Get the correct RPC URL - 交易确认使用公共RPC（验证）
        rpc_url = self._get_public_rpc_url()
        
        # Create a new RPC client with the correct URL
        return Client(rpc_url)
    
    def _is_local_node(self) -> bool:
        """检测是否为本地节点"""
        rpc_url = self._get_rpc_url()
        return any(domain in rpc_url for domain in ['localhost', '127.0.0.1', '69.67.149.99'])

    async def _wait_for_confirmation(self, tx_hash: str, timeout: float = 60.0) -> bool:
        """Wait for transaction confirmation with fallback to public RPC for local nodes
        
        Args:
            tx_hash: 交易哈希字符串
            timeout: 超时时间（秒）
            
        Returns:
            bool: 交易是否确认成功
        """
        rpc_client = self._get_rpc_client()
        start_time = time.time()
        
        # Import required classes
        from solders.signature import Signature
        from solana.rpc.async_api import AsyncClient
        
        logger.info(f"开始等待交易确认: {tx_hash}")
        
        # Ratelimit防护参数
        check_count = 0
        consecutive_errors = 0
        max_consecutive_errors = 3
        
        # 第一次检查前先等待5秒，给交易更多时间确认
        await asyncio.sleep(5.0)
        
        while time.time() - start_time < timeout:
            check_count += 1
            
            try:
                # Convert string hash to Signature object
                signature = Signature.from_string(tx_hash)
                
                # 首先尝试使用get_signature_statuses（最可靠的方法）
                # 注意：同步客户端不需要await
                status = rpc_client.get_signature_statuses([signature])
                
                if status.value and len(status.value) > 0:
                    sig_status = status.value[0]
                    if sig_status is not None:
                        # 交易状态可用
                        if hasattr(sig_status, 'confirmation_status'):
                            if sig_status.confirmation_status in ['confirmed', 'finalized']:
                                logger.info(f"✅ 交易确认成功! (检查 #{check_count})")
                                logger.info(f"   确认状态: {sig_status.confirmation_status}")
                                
                                # 交易确认后，尝试获取详细交易信息
                                try:
                                    tx_details = rpc_client.get_transaction(
                                        signature,
                                        max_supported_transaction_version=0,
                                        encoding="jsonParsed",
                                        commitment="confirmed"
                                    )
                                    if tx_details.value:
                                        # 始终打印交易详情信息
                                        self._print_transaction_details(tx_details.value)
                                    else:
                                        logger.info("   🔍 交易已确认，但无法获取详细交易信息")
                                except Exception as tx_error:
                                    logger.debug(f"获取交易详情失败: {tx_error}")
                                    logger.info("   🔍 交易已确认，但详情解析失败")
                                
                                if hasattr(sig_status, 'err') and sig_status.err:
                                    logger.warning(f"   交易错误: {sig_status.err}")
                                    return False
                                return True
                            else:
                                logger.info(f"检查 #{check_count}: 交易状态: {sig_status.confirmation_status}")
                        else:
                            # 旧版本Solana SDK可能没有confirmation_status属性
                            logger.info(f"检查 #{check_count}: 交易状态可用，但无确认状态属性")
                            return True
                
                # 如果状态不明确，尝试get_transaction
                try:
                    confirmation = rpc_client.get_transaction(
                        signature, 
                        max_supported_transaction_version=0,
                        encoding="jsonParsed",
                        commitment="confirmed"
                    )
                    
                    if confirmation.value and confirmation.value.transaction:
                        # 交易存在，打印详细交易信息
                        tx_details = confirmation.value
                        
                        logger.info(f"✅ 交易确认成功! (检查 #{check_count})")
                        
                        # 解析并打印交易详情
                        self._print_transaction_details(tx_details)
                        
                        return True
                except Exception as tx_error:
                    # 处理TransactionHistoryNotAvailable错误
                    error_msg = str(tx_error).lower()
                    if 'transactionhistorynotavailable' in error_msg:
                        logger.info(f"检查 #{check_count}: RPC节点交易历史不可用")
                    else:
                        logger.debug(f"get_transaction检查失败: {tx_error}")
                
                # 如果交易不存在，继续等待
                logger.info(f"检查 #{check_count}: 交易尚未确认，继续等待...")
                
                # 重置错误计数器
                consecutive_errors = 0
                
                # 智能等待算法：检查次数越多，等待时间越长
                base_wait = 3.0
                if check_count > 10:
                    base_wait = 8.0
                elif check_count > 5:
                    base_wait = 5.0
                
                logger.info(f"等待 {base_wait:.1f} 秒后进行下一次检查...")
                await asyncio.sleep(base_wait)
                
            except Exception as e:
                consecutive_errors += 1
                error_type = type(e).__name__
                error_msg = str(e)
                
                # 区分可重试的异常和应该立即终止的异常
                # 可重试的异常：网络错误、Ratelimit、临时性错误
                # 应该立即终止的异常：代码逻辑错误、类型错误、参数错误等
                
                # 检查是否是代码逻辑错误（应该立即终止）
                if error_type in ['TypeError', 'AttributeError', 'ValueError', 'NameError', 'SyntaxError']:
                    logger.error(f"❌ 代码逻辑错误，立即终止检查: {error_type}: {error_msg}")
                    return False
                
                # 检查是否是Ratelimit错误（可重试）
                error_msg_lower = error_msg.lower()
                if '429' in error_msg_lower or 'ratelimit' in error_msg_lower or 'too many requests' in error_msg_lower:
                    logger.warning(f"🚫 Ratelimit检测到! 错误: {error_type}: {error_msg}")
                    
                    # Ratelimit错误需要更长的等待时间
                    ratelimit_wait = 15.0 + (consecutive_errors * 8.0)
                    logger.warning(f"🚫 Ratelimit防护: 等待 {ratelimit_wait:.1f} 秒...")
                    await asyncio.sleep(ratelimit_wait)
                
                # 检查是否是网络相关错误（可重试）
                elif any(keyword in error_msg_lower for keyword in ['connection', 'timeout', 'network', 'socket', 'http']):
                    logger.warning(f"🌐 网络错误，尝试重试: {error_type}: {error_msg}")
                    
                    # 网络错误，适当等待
                    network_wait = 5.0 + (consecutive_errors * 3.0)
                    logger.warning(f"网络错误防护: 等待 {network_wait:.1f} 秒...")
                    await asyncio.sleep(network_wait)
                
                # 其他未知错误（谨慎重试）
                else:
                    logger.warning(f"⚠️  未知错误，谨慎重试: {error_type}: {error_msg}")
                    
                    # 对于未知错误，等待时间更长，重试次数更少
                    unknown_wait = 10.0 + (consecutive_errors * 5.0)
                    logger.warning(f"未知错误防护: 等待 {unknown_wait:.1f} 秒...")
                    await asyncio.sleep(unknown_wait)
                
                # 如果连续错误太多，提前返回
                if consecutive_errors >= max_consecutive_errors:
                    logger.error(f"❌ 连续错误过多 ({consecutive_errors}次)，停止检查")
                    return False
        
        logger.error(f"❌ 交易确认超时 ({timeout}秒)")
        
        logger.warning(f"❌ 交易 {tx_hash} 在 {timeout} 秒内未确认")
        return False

    async def get_trade_history(self, limit: int = 100) -> List[TradeResult]:
        """Get trade history for wallet"""
        try:
            # This would query on-chain transactions
            # For now, return empty list
            return []
        except Exception as e:
            raise TradingError(f"Failed to get trade history: {e}")

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel pending order"""
        try:
            # This would cancel limit orders if supported
            # For market orders, this is not applicable
            logger.info(f"Order {order_id} cancellation requested")
            return True
        except Exception as e:
            raise TradingError(f"Failed to cancel order: {e}")

    async def _get_best_token_price(self, token_address: str) -> float:
        """Get best token price from multiple DEX sources"""
        price_sources = []
        
        # 1. Jupiter API (聚合器，包含多个DEX)
        try:
            jupiter_price = await self._get_jupiter_price(token_address)
            if jupiter_price > 0:
                price_sources.append(("jupiter", jupiter_price))
        except Exception as e:
            logger.warning(f"Failed to get Jupiter price: {e}")
        
        # 2. Raydium direct pool price
        try:
            raydium_price = await self._get_raydium_price(token_address)
            if raydium_price > 0:
                price_sources.append(("raydium", raydium_price))
        except Exception as e:
            logger.warning(f"Raydium price query failed: {e}")
        
        # 如果没有找到价格源，使用默认方法
        if not price_sources:
            logger.warning("No price sources available, using fallback method")
            return await self._get_jupiter_price(token_address)
        
        # 选择最佳价格（最低价用于买入，最高价用于卖出）
        # 这里返回平均价格作为基准
        prices = [price for _, price in price_sources if price > 0]
        if prices:
            avg_price = sum(prices) / len(prices)
            logger.info(f"Price sources for {token_address}: {price_sources}, using average: {avg_price:.6f}")
            return avg_price
        else:
            raise TradingError(f"No valid price found for token {token_address}")
    
    def _print_transaction_details(self, tx_details):
        """解析并打印交易详情（使用改进的解析逻辑）
        
        Args:
            tx_details: 交易详情对象 (EncodedConfirmedTransactionWithStatusMeta)
        """
        try:
            # 安全地访问交易详情属性
            logger.info("   📊 交易详情解析:")
            
            # 交易槽位信息
            if hasattr(tx_details, 'slot'):
                slot = tx_details.slot
                logger.info(f"   🔄 交易槽位: {slot}")
            
            # 区块时间
            if hasattr(tx_details, 'block_time'):
                block_time = tx_details.block_time
                if block_time:
                    from datetime import datetime
                    dt = datetime.fromtimestamp(block_time)
                    logger.info(f"   ⏰ 区块时间: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 获取交易数据
            if hasattr(tx_details, 'transaction'):
                tx_data = tx_details.transaction
                
                # 获取交易哈希
                if hasattr(tx_data, 'signatures'):
                    signatures = tx_data.signatures
                    if signatures:
                        logger.info(f"   🔗 交易哈希: {signatures[0]}")
                
                # 解析交易元数据
                if hasattr(tx_data, 'meta'):
                    meta = tx_data.meta
                    
                    # 解析交易内容
                    logger.info("   📋 交易类型分析:")
                    
                    # 从日志中提取详细的Swap信息
                    if hasattr(meta, 'log_messages'):
                        log_messages = meta.log_messages
                        swap_details_found = False
                        for log in log_messages:
                            # 查找Swap相关的详细信息
                            if 'SwapEvent' in log:
                                import re
                                # 提取Swap事件详情
                                swap_match = re.search(r'SwapEvent\s*\{\s*dex:\s*(\w+),\s*amount_in:\s*(\d+),\s*amount_out:\s*(\d+)\s*\}', log)
                                if swap_match:
                                    dex_name = swap_match.group(1)
                                    amount_in = int(swap_match.group(2))
                                    amount_out = int(swap_match.group(3))
                                    logger.info(f"     💱 Swap事件: {dex_name} DEX")
                                    logger.info(f"       输入: {amount_in:,} tokens")
                                    logger.info(f"       输出: {amount_out:,} tokens")
                                    swap_details_found = True
                                    break
                        
                        # 如果没找到SwapEvent，尝试从其他日志中提取信息
                        if not swap_details_found:
                            for log in log_messages:
                                if 'amount_in:' in log and 'amount_out:' in log:
                                    import re
                                    # 尝试多种格式
                                    amount_in_match = re.search(r'amount_in:\s*(\d+)', log)
                                    amount_out_match = re.search(r'amount_out:\s*(\d+)', log)
                                    if amount_in_match and amount_out_match:
                                        amount_in = int(amount_in_match.group(1))
                                        amount_out = int(amount_out_match.group(1))
                                        logger.info(f"     💱 Swap详情: {amount_in:,} -> {amount_out:,}")
                                        
                                    # 查找代币信息
                                    token_in_match = re.search(r'So11111111111111111111111111111111111111112', log)
                                    token_out_match = re.search(r'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', log)
                                    if token_in_match and token_out_match:
                                        logger.info(f"       代币对: SOL -> USDC")
                                        logger.info(f"       汇率: 1 SOL ≈ {amount_out/amount_in:.2f} USDC")
                                    break
                    
                    # 交易费用 - 正确显示
                    fee = getattr(meta, 'fee', '未知')
                    logger.info(f"   💰 交易费用: {fee} lamports (约 {fee/1000000000:.6f} SOL)")
                    
                    # 交易状态
                    err = getattr(meta, 'err', None)
                    if err:
                        logger.info(f"   ⚠️  交易错误: {err}")
                    else:
                        logger.info("   ✅ 交易执行成功")
                    
                    # 计算单位消耗
                    compute_units = getattr(meta, 'compute_units_consumed', None)
                    if compute_units:
                        logger.info(f"   ⚡ 计算单位消耗: {compute_units:,}")
                    
                    # 余额变化 - 正确显示交易费用
                    pre_balances = getattr(meta, 'pre_balances', [])
                    post_balances = getattr(meta, 'post_balances', [])
                    
                    if pre_balances and post_balances and len(pre_balances) == len(post_balances):
                        logger.info(f"   💳 余额变化分析 (显示前3个账户):")
                        for i, (pre, post) in enumerate(zip(pre_balances[:3], post_balances[:3])):
                            if pre != post:
                                change = post - pre
                                # 第一个账户的变化应该等于交易费用
                                if i == 0:
                                    logger.info(f"     账户 {i} (签名者): {pre} -> {post} (交易费用: {change:+d} lamports)")
                                else:
                                    logger.info(f"     账户 {i}: {pre} -> {post} (变化: {change:+d})")
                    
                    # 代币余额变化
                    pre_tokens = getattr(meta, 'pre_token_balances', [])
                    post_tokens = getattr(meta, 'post_token_balances', [])
                    
                    if pre_tokens and post_tokens:
                        logger.info("   📦 代币余额变化:")
                        
                        # 创建代币映射
                        token_map = {}
                        for token in pre_tokens + post_tokens:
                            if hasattr(token, 'mint'):
                                mint = str(token.mint)  # 将 Pubkey 转换为字符串
                                if mint not in token_map:
                                    token_map[mint] = {'pre': 0, 'post': 0}
                        
                        # 收集余额
                        for token in pre_tokens:
                            if hasattr(token, 'mint') and hasattr(token, 'ui_token_amount'):
                                mint = str(token.mint)  # 将 Pubkey 转换为字符串
                                amount = token.ui_token_amount.ui_amount or 0
                                token_map[mint]['pre'] = amount
                        
                        for token in post_tokens:
                            if hasattr(token, 'mint') and hasattr(token, 'ui_token_amount'):
                                mint = str(token.mint)  # 将 Pubkey 转换为字符串
                                amount = token.ui_token_amount.ui_amount or 0
                                token_map[mint]['post'] = amount
                        
                        # 显示代币变化
                        for mint, balances in token_map.items():
                            change = balances['post'] - balances['pre']
                            if abs(change) > 0.0000001:  # 只显示有意义的变动
                                token_name = "USDC" if mint == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v" else mint[:8] + "..."
                                logger.info(f"     {token_name}: {balances['pre']:.6f} -> {balances['post']:.6f} ({change:+.6f})")
                    
                    # 交易日志
                    log_messages = getattr(meta, 'log_messages', [])
                    if log_messages:
                        logger.info(f"   📝 交易日志数量: {len(log_messages)}")
                        for i, log in enumerate(log_messages[:2]):  # 只显示前2条
                            logger.info(f"     日志 {i+1}: {log[:80]}...")
                
                # 交易消息
                if hasattr(tx_data, 'message'):
                    message = tx_data.message
                    
                    # 账户数量
                    if hasattr(message, 'account_keys'):
                        accounts = message.account_keys
                        logger.info(f"   🔑 交易涉及账户数量: {len(accounts)}")
                    
                    # 指令数量
                    if hasattr(message, 'instructions'):
                        instructions = message.instructions
                        logger.info(f"   📋 交易指令数量: {len(instructions)}")
                    
                    # 最近区块哈希
                    if hasattr(message, 'recent_blockhash'):
                        blockhash = message.recent_blockhash
                        logger.info(f"   🔗 最近区块哈希: {blockhash[:16]}...")
            
        except Exception as e:
            logger.warning(f"解析交易详情失败: {e}")
            # 提供更多调试信息
            logger.debug(f"交易详情对象类型: {type(tx_details)}")
            if hasattr(tx_details, '__dict__'):
                logger.debug(f"交易详情属性: {list(tx_details.__dict__.keys())}")
            if hasattr(tx_details, 'transaction') and hasattr(tx_details.transaction, '__dict__'):
                logger.debug(f"交易数据属性: {list(tx_details.transaction.__dict__.keys())}")
            # 如果解析失败，至少打印基本信息
            logger.info("   🔍 交易已确认，但详情解析失败")
    
    async def _get_jupiter_price(self, token_address: str) -> float:
        """Get price from Jupiter aggregator"""
        try:
            price = await self.jupiter_client.get_price(
                input_mint=token_address,
                output_mint=self.common_tokens["SOL"]
            )
            logger.info(f"Jupiter price for {token_address}: {price:.10f} SOL")
            return price
        except Exception as e:
            logger.warning(f"Jupiter price query failed for {token_address}: {e}")
            raise
    
    async def _get_raydium_price(self, token_address: str) -> float:
        """Get price from Raydium direct pools using Raydium API v3"""
        # 如果是SOL本身，价格为1 SOL
        if token_address == self.common_tokens["SOL"]:
            logger.info("Raydium price for SOL: 1.0 SOL (base token)")
            return 1.0
            
        try:
            # 使用Raydium交易API获取价格
            # 通过获取SOL -> token的报价来计算价格
            
            # 获取报价（使用小额SOL作为输入）
            quote = await self.raydium_client.get_swap_quote(
                input_mint=self.common_tokens["SOL"],
                output_mint=token_address,
                amount=10000000,  # 0.01 SOL
                slippage_bps=100,  # 1% 滑点
                tx_version="V0"
            )
            
            if quote.get('success'):
                data = quote['data']
                input_amount = float(data['inputAmount']) / 1e9  # SOL数量
                output_amount = float(data['outputAmount'])  # 代币数量
                
                # 获取代币小数位数
                decimals = data.get('outputDecimals', 6)
                output_amount = output_amount / (10 ** decimals)
                
                # 计算价格：1 token = ? SOL
                price = input_amount / output_amount
                logger.info(f"Raydium price for {token_address}: {price:.10f} SOL")
                return price
            else:
                raise TradingError(f"Raydium API quote failed: {quote}")
                
        except Exception as e:
            logger.warning(f"Raydium price calculation failed: {e}")
            raise TradingError(f"Failed to get Raydium price: {e}")

    async def analyze_dex_prices(self, token_address: str) -> Dict[str, Any]:
        """分析不同DEX的价格差异
        
        Args:
            token_address: 代币地址
            
        Returns:
            包含各DEX价格和比较信息的字典
        """
        results = {}
        
        # 获取Jupiter价格
        try:
            jupiter_price = await self._get_jupiter_price(token_address)
            results['jupiter'] = {
                'price': jupiter_price,
                'status': 'success'
            }
        except Exception as e:
            results['jupiter'] = {
                'price': 0.0,
                'status': 'failed',
                'error': str(e)
            }
        
        # 获取Raydium价格
        try:
            raydium_price = await self._get_raydium_price(token_address)
            results['raydium'] = {
                'price': raydium_price,
                'status': 'success'
            }
        except Exception as e:
            results['raydium'] = {
                'price': 0.0,
                'status': 'failed',
                'error': str(e)
            }
        
        # 计算价格差异
        if results['jupiter']['status'] == 'success' and results['raydium']['status'] == 'success':
            price_diff = abs(jupiter_price - raydium_price)
            price_diff_pct = (price_diff / min(jupiter_price, raydium_price)) * 100
            results['comparison'] = {
                'price_difference': price_diff,
                'price_difference_percent': price_diff_pct,
                'best_dex': 'jupiter' if jupiter_price < raydium_price else 'raydium'
            }
        
        return results

    async def analyze_dex_liquidity(self, token_address: str) -> Dict[str, Any]:
        """分析不同DEX的流动性情况
        
        Args:
            token_address: 代币地址
            
        Returns:
            包含各DEX流动性信息的字典
        """
        results = {}
        
        # 分析Raydium流动性
        try:
            pools = await self.raydium_client.get_raydium_pools()
            if pools and pools.get('official'):
                pool_data = pools['official']
                pools_list = pool_data['data'] if isinstance(pool_data, dict) and 'data' in pool_data else pool_data
                
                # 查找包含目标代币的池
                token_pools = []
                for pool in pools_list:
                    mintA = pool.get('mintA', {}).get('address', '')
                    mintB = pool.get('mintB', {}).get('address', '')
                    
                    if token_address in [mintA, mintB]:
                        token_pools.append({
                            'id': pool.get('id', 'N/A'),
                            'tvl': float(pool.get('tvl', 0)),
                            'pair': f"{pool.get('mintA', {}).get('symbol', 'N/A')}/{pool.get('mintB', {}).get('symbol', 'N/A')}",
                            'type': pool.get('pooltype', ['N/A'])[0]
                        })
                
                results['raydium'] = {
                    'status': 'success',
                    'pool_count': len(token_pools),
                    'total_tvl': sum(pool['tvl'] for pool in token_pools),
                    'pools': sorted(token_pools, key=lambda x: x['tvl'], reverse=True)[:5]  # 前5个最大流动性的池
                }
            else:
                results['raydium'] = {
                    'status': 'failed',
                    'error': 'No pools found'
                }
        except Exception as e:
            results['raydium'] = {
                'status': 'failed',
                'error': str(e)
            }
        
        # 分析Jupiter流动性（通过Ultra Mode路由信息推断）
        try:
            # 获取Jupiter报价来分析可用路由
            quote = await self.jupiter_client.get_quote(
                input_mint=self.common_tokens["SOL"],
                output_mint=token_address,
                amount=10000000,  # 0.01 SOL
                slippage_bps=50,
                enable_ultra_features=True  # 启用Ultra Mode功能
            )
            
            # 使用Ultra Mode分析功能
            ultra_analysis = await self.jupiter_client.get_ultra_quote_analysis(quote)
            
            if 'routePlan' in quote:
                results['jupiter'] = {
                    'status': 'success',
                    'route_count': len(quote['routePlan']),
                    'available_routes': len(quote['routePlan']),
                    'ultra_features': ultra_analysis['ultra_features_used'],
                    'route_quality': ultra_analysis['route_quality'],
                    'mev_protection': ultra_analysis['mev_protection'],
                    'price_impact': ultra_analysis['price_impact'],
                    'recommendations': ultra_analysis['recommendations']
                }
            else:
                results['jupiter'] = {
                    'status': 'failed',
                    'error': 'No route plan available'
                }
        except Exception as e:
            results['jupiter'] = {
                'status': 'failed',
                'error': str(e)
            }
        
        return results

    async def get_optimal_dex(self, token_address: str, trade_type: str = "buy") -> Dict[str, Any]:
        """获取最优DEX推荐（基于价格和流动性）
        
        Args:
            token_address: 代币地址
            trade_type: 交易类型 ("buy" 或 "sell")
            
        Returns:
            包含推荐DEX和详细分析信息的字典
        """
        recommendation = {
            'token_address': token_address,
            'trade_type': trade_type,
            'recommended_dex': None,
            'reason': '',
            'details': {}
        }
        
        # 获取价格比较
        price_analysis = await self.analyze_dex_prices(token_address)
        
        # 获取流动性比较
        liquidity_analysis = await self.analyze_dex_liquidity(token_address)
        
        # 决策逻辑
        jupiter_ok = price_analysis.get('jupiter', {}).get('status') == 'success'
        raydium_ok = price_analysis.get('raydium', {}).get('status') == 'success'
        
        if jupiter_ok and raydium_ok:
            # 两个DEX都可用，基于价格和流动性选择
            jupiter_price = price_analysis['jupiter']['price']
            raydium_price = price_analysis['raydium']['price']
            
            # 对于买入，选择价格更低的DEX
            if trade_type == "buy":
                if jupiter_price <= raydium_price:
                    recommendation['recommended_dex'] = 'jupiter'
                    recommendation['reason'] = 'Jupiter提供更好的价格'
                else:
                    recommendation['recommended_dex'] = 'raydium'
                    recommendation['reason'] = 'Raydium提供更好的价格'
            else:  # 卖出，选择价格更高的DEX
                if jupiter_price >= raydium_price:
                    recommendation['recommended_dex'] = 'jupiter'
                    recommendation['reason'] = 'Jupiter提供更好的价格'
                else:
                    recommendation['recommended_dex'] = 'raydium'
                    recommendation['reason'] = 'Raydium提供更好的价格'
            
            # 考虑流动性因素
            raydium_tvl = liquidity_analysis.get('raydium', {}).get('total_tvl', 0)
            if raydium_tvl > 1000000:  # 如果Raydium流动性超过100万美元
                recommendation['reason'] += f" (Raydium流动性充足: ${raydium_tvl:,.0f})"
        
        elif jupiter_ok:
            recommendation['recommended_dex'] = 'jupiter'
            recommendation['reason'] = 'Raydium不可用，使用Jupiter'
        
        elif raydium_ok:
            recommendation['recommended_dex'] = 'raydium'
            recommendation['reason'] = 'Jupiter不可用，使用Raydium'
        
        else:
            recommendation['recommended_dex'] = None
            recommendation['reason'] = '两个DEX都不可用'
        
        recommendation['details'] = {
            'price_analysis': price_analysis,
            'liquidity_analysis': liquidity_analysis
        }
        
        return recommendation

    async def compare_dex_performance(self, token_address: str) -> Dict[str, Any]:
        """比较DEX性能（响应时间和成功率）
        
        Args:
            token_address: 代币地址
            
        Returns:
            包含各DEX性能指标的字典
        """
        performance = {}
        
        # 测试Jupiter性能
        jupiter_start = time.time()
        try:
            jupiter_quote = await self.jupiter_client.get_quote(
                input_mint=self.common_tokens["SOL"],
                output_mint=token_address,
                amount=10000000,
                slippage_bps=50
            )
            jupiter_time = time.time() - jupiter_start
            performance['jupiter'] = {
                'response_time': jupiter_time,
                'status': 'success',
                'route_count': len(jupiter_quote.get('routePlan', [])) if 'routePlan' in jupiter_quote else 0
            }
        except Exception as e:
            performance['jupiter'] = {
                'response_time': time.time() - jupiter_start,
                'status': 'failed',
                'error': str(e)
            }
        
        # 测试Raydium性能
        raydium_start = time.time()
        try:
            raydium_quote = await self.raydium_client.get_swap_quote(
                input_mint=self.common_tokens["SOL"],
                output_mint=token_address,
                amount=10000000,
                slippage_bps=50
            )
            raydium_time = time.time() - raydium_start
            performance['raydium'] = {
                'response_time': raydium_time,
                'status': 'success',
                'route_count': 1 if raydium_quote.get('success') else 0  # Raydium是直接交易，没有路由计划
            }
        except Exception as e:
            performance['raydium'] = {
                'response_time': time.time() - raydium_start,
                'status': 'failed',
                'error': str(e)
            }
        
        return performance

    async def _get_actual_trade_result(self, tx_hash: str, order: TradeOrder, expected_amount: float) -> TradeResult:
        """从链上获取实际的交易执行结果
        
        Args:
            tx_hash: 交易哈希
            order: 交易订单
            expected_amount: 预期成交数量
            
        Returns:
            TradeResult: 包含实际交易数据的交易结果
        """
        try:
            # 获取交易详情
            from solders.signature import Signature
            
            rpc_client = self._get_rpc_client()
            signature = Signature.from_string(tx_hash)
            
            # 获取交易详情
            tx_response = rpc_client.get_transaction(
                signature,
                max_supported_transaction_version=0,
                encoding="jsonParsed",
                commitment="confirmed"
            )
            
            if not tx_response.value:
                raise TradingError(f"无法获取交易详情: {tx_hash}")
            
            # 解析实际的交易结果
            actual_amount = self._parse_actual_trade_amount(tx_response.value, order, expected_amount)
            actual_price = self._parse_actual_trade_price(tx_response.value, order, actual_amount)
            
            # 计算总成本/收益
            if order.side == OrderSide.BUY:
                total_cost = order.amount  # 购买时总成本是输入的SOL数量
            else:
                total_cost = actual_amount  # 卖出时总收益是实际获得的SOL数量
            
            logger.info(f"🔍 链上解析结果 - 实际成交: {actual_amount}, 实际价格: {actual_price}")
            
            return TradeResult(
                order_id=f"{tx_hash[:16]}",
                token_address=order.token_address,
                side=order.side,
                executed_amount=actual_amount,
                executed_price=actual_price,
                total_cost=total_cost,
                transaction_hash=tx_hash,
                status="completed"
            )
            
        except Exception as e:
            logger.error(f"解析实际交易结果失败: {e}")
            raise TradingError(f"无法从链上解析交易结果: {e}")

    def _parse_actual_trade_amount(self, tx_details, order: TradeOrder, expected_amount: float) -> float:
        """从交易详情中解析实际成交的代币数量
        
        Args:
            tx_details: 交易详情
            order: 交易订单
            expected_amount: 预期成交数量（用于回退）
            
        Returns:
            float: 实际成交的代币数量
        """
        try:
            # 获取交易中的代币余额变化
            # 注意：meta属性在tx_details.transaction.meta中
            if hasattr(tx_details, 'transaction') and tx_details.transaction:
                transaction = tx_details.transaction
                if hasattr(transaction, 'meta') and transaction.meta:
                    meta = transaction.meta
                    pre_token_balances = getattr(meta, 'pre_token_balances', []) or []
                    post_token_balances = getattr(meta, 'post_token_balances', []) or []
                    
                    logger.debug(f"🔍 交易详情分析 - 前余额记录数: {len(pre_token_balances)}, 后余额记录数: {len(post_token_balances)}")
                    
                    # 查找目标代币的余额变化
                    for pre_balance in pre_token_balances:
                        pre_mint = getattr(pre_balance, 'mint', None)
                        if pre_mint and str(pre_mint) == order.token_address:
                            # 找到匹配的前余额，查找对应的后余额
                            for post_balance in post_token_balances:
                                post_mint = getattr(post_balance, 'mint', None)
                                if post_mint and str(post_mint) == order.token_address:
                                    # 计算代币数量变化
                                    pre_amount = getattr(getattr(pre_balance, 'ui_token_amount', None), 'amount', 0)
                                    post_amount = getattr(getattr(post_balance, 'ui_token_amount', None), 'amount', 0)
                                    
                                    if pre_amount is not None and post_amount is not None:
                                        # 将字符串转换为数字
                                        try:
                                            pre_amount_num = int(pre_amount)
                                            post_amount_num = int(post_amount)
                                        except (ValueError, TypeError):
                                            pre_amount_num = 0
                                            post_amount_num = 0
                                        
                                        if order.side == OrderSide.BUY:
                                            # 买入：代币增加
                                            amount_change = post_amount_num - pre_amount_num
                                        else:
                                            # 卖出：代币减少
                                            amount_change = pre_amount_num - post_amount_num
                                        
                                        logger.info(f"🔍 找到代币余额变化 - 前: {pre_amount_num}, 后: {post_amount_num}, 变化: {amount_change}")
                                        
                                        if amount_change > 0:
                                            # 转换为小数（考虑代币精度）
                                            decimals = getattr(getattr(post_balance, 'ui_token_amount', None), 'decimals', 6)
                                            actual_amount = amount_change / (10 ** decimals)
                                            logger.info(f"🔍 解析到实际成交数量: {actual_amount} (链上变化: {amount_change}, 精度: {decimals})")
                                            return actual_amount
            
            # 如果无法解析，返回预期值
            logger.warning(f"无法从交易详情中解析实际成交数量，使用预期值: {expected_amount}")
            return expected_amount
            
        except Exception as e:
            logger.warning(f"解析实际成交数量失败，使用预期值: {e}")
            return expected_amount

    def _parse_actual_trade_price(self, tx_details, order: TradeOrder, actual_amount: float) -> float:
        """从交易详情中解析实际执行价格
        
        Args:
            tx_details: 交易详情
            order: 交易订单
            actual_amount: 实际成交的代币数量
            
        Returns:
            float: 实际执行价格（SOL/代币）
        """
        try:
            # 计算实际的汇率
            if order.side == OrderSide.BUY:
                # 买入：price = SOL数量 / 代币数量
                # 成本是SOL数量，收益是代币数量
                if actual_amount > 0:
                    actual_price = order.amount / actual_amount
                else:
                    actual_price = 0.0
            else:
                # 卖出：price = SOL数量 / 代币数量  
                # 成本是代币数量，收益是SOL数量
                if order.amount > 0:
                    actual_price = actual_amount / order.amount
                else:
                    actual_price = 0.0
            
            if actual_price <= 0:
                logger.warning(f"计算的实际价格异常: {actual_price}，使用当前市场价格")
                # 回退到获取当前市场价格
                return self._get_token_price_sync(order.token_address)
            
            return actual_price
            
        except Exception as e:
            logger.warning(f"解析实际执行价格失败，使用当前价格: {e}")
            return self._get_token_price_sync(order.token_address)

    def _get_token_price_sync(self, token_address: str) -> float:
        """同步方式获取代币价格（用于异常处理）
        
        Args:
            token_address: 代币地址
            
        Returns:
            float: 代币价格
        """
        try:
            # 如果是SOL，直接返回1.0
            if token_address == self.common_tokens["SOL"]:
                return 1.0
            
            # 直接返回默认价格，避免异步调用问题
            return 0.001
        except:
            # 最终回退到默认价格
            return 0.001