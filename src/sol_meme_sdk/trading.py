"""
Trading functionality for Sol Meme SDK
"""

import asyncio
import logging
import time
import base64
from typing import Optional, List, Dict, Any
from solana.rpc.api import Client
from solana.rpc.types import TxOpts
from solana.transaction import Transaction

from .models import TradeOrder, TradeResult, OrderType, OrderSide, TransactionConfig
from .exceptions import TradingError, InsufficientFundsError, InvalidTokenError
from .jupiter_client import JupiterClient

logger = logging.getLogger(__name__)


class TradingEngine:
    """Trading engine for executing meme coin trades on Solana"""

    def __init__(self, client: Client, wallet, config: Optional[TransactionConfig] = None):
        """
        Initialize trading engine
        
        Args:
            client: Solana RPC client
            wallet: Wallet instance for signing transactions
            config: Transaction configuration
        """
        self.client = client
        self.wallet = wallet
        self.config = config or TransactionConfig()
        
        # Initialize Jupiter client
        network = "devnet" if self.config.enable_devnet_testing else "mainnet-beta"
        self.jupiter_client = JupiterClient(network)
        
        # Common token addresses for mainnet
        self.common_tokens = {
            "SOL": "So111111111111111111111111111111111111111111111111111111111111112",
            "WSOL": "So11111111111111111111111111111111111111112",
            "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        }

    async def buy_token(
        self,
        token_address: str,
        amount_sol: float,
        slippage: float = 0.5,
        token_info: Optional[Dict] = None
    ) -> TradeResult:
        """
        Buy meme token with SOL
        
        Args:
            token_address: Token mint address
            amount_sol: Amount of SOL to spend
            slippage: Slippage tolerance percentage
            token_info: Optional token information
            
        Returns:
            TradeResult with execution details
        """
        try:
            # Validate inputs
            if amount_sol <= 0:
                raise TradingError("Amount must be positive")
            
            # Check wallet balance
            balance = self.wallet.get_balance(self.client)
            if balance < amount_sol:
                raise InsufficientFundsError(
                    f"Insufficient SOL balance: {balance} < {amount_sol}"
                )
            
            # Get token information if not provided
            if not token_info:
                token_info = await self._get_token_info(token_address)
            
            # Calculate expected token amount
            expected_tokens = await self._calculate_buy_amount(
                token_address, amount_sol, slippage
            )
            
            # Execute trade
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
        token_info: Optional[Dict] = None
    ) -> TradeResult:
        """
        Sell meme token for SOL
        
        Args:
            token_address: Token mint address
            amount_tokens: Amount of tokens to sell
            slippage: Slippage tolerance percentage
            token_info: Optional token information
            
        Returns:
            TradeResult with execution details
        """
        try:
            # Validate inputs
            if amount_tokens <= 0:
                raise TradingError("Amount must be positive")
            
            # Check token balance
            token_balance = await self._get_token_balance(token_address)
            if token_balance < amount_tokens:
                raise InsufficientFundsError(
                    f"Insufficient token balance: {token_balance} < {amount_tokens}"
                )
            
            # Get token information if not provided
            if not token_info:
                token_info = await self._get_token_info(token_address)
            
            # Calculate expected SOL amount
            expected_sol = await self._calculate_sell_amount(
                token_address, amount_tokens, slippage
            )
            
            # Execute trade
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
        """Get token information using Jupiter tokens list"""
        try:
            # Try to get token info from Jupiter
            tokens_list = await self.jupiter_client.get_tokens_list()
            
            if isinstance(tokens_list, dict) and "tokens" in tokens_list:
                for token in tokens_list["tokens"]:
                    if token["address"] == token_address:
                        return {
                            "address": token_address,
                            "decimals": token.get("decimals", 6),
                            "symbol": token.get("symbol", "UNKNOWN"),
                            "name": token.get("name", "Unknown Token")
                        }
            
            # Fallback for devnet or unsupported tokens
            logger.warning(f"Token {token_address} not found in Jupiter list, using fallback")
            return {
                "address": token_address,
                "decimals": 6,
                "symbol": "UNKNOWN",
                "name": "Unknown Token"
            }
            
        except Exception as e:
            logger.warning(f"Failed to get token info from Jupiter: {e}")
            
            # Fallback for devnet/testing
            if self.config.enable_devnet_testing:
                return {
                    "address": token_address,
                    "decimals": 6,
                    "symbol": "UNKNOWN",
                    "name": "Unknown Token"
                }
            else:
                raise InvalidTokenError(f"Failed to get token info: {e}")

    async def _get_token_balance(self, token_address: str) -> float:
        """Get token balance for wallet"""
        try:
            # Get token balances from wallet
            token_balances = self.wallet.get_token_balances(self.client)
            
            # Return balance for specific token
            balance = token_balances.get(token_address, 0.0)
            logger.debug(f"Token balance for {token_address}: {balance}")
            return balance
            
        except Exception as e:
            raise TradingError(f"Failed to get token balance: {e}")

    async def _calculate_buy_amount(
        self, token_address: str, amount_sol: float, slippage: float
    ) -> float:
        """Calculate expected token amount for buy order"""
        try:
            # This would query DEX or AMM to get price and calculate amount
            # For now, use placeholder calculation
            price = await self._get_token_price(token_address)
            expected_tokens = amount_sol / price
            min_tokens = expected_tokens * (1 - slippage / 100)
            return min_tokens
        except Exception as e:
            raise TradingError(f"Failed to calculate buy amount: {e}")

    async def _calculate_sell_amount(
        self, token_address: str, amount_tokens: float, slippage: float
    ) -> float:
        """Calculate expected SOL amount for sell order"""
        try:
            # This would query DEX or AMM to get price and calculate amount
            # For now, use placeholder calculation
            price = await self._get_token_price(token_address)
            expected_sol = amount_tokens * price
            min_sol = expected_sol * (1 - slippage / 100)
            return min_sol
        except Exception as e:
            raise TradingError(f"Failed to calculate sell amount: {e}")

    async def _get_token_price(self, token_address: str) -> float:
        """Get current token price in SOL using Jupiter"""
        try:
            # Use Jupiter to get price
            price = await self.jupiter_client.get_price(
                input_mint=token_address,
                output_mint=self.common_tokens["SOL"]
            )
            logger.debug(f"Got price for {token_address}: {price} SOL")
            return price
            
        except Exception as e:
            logger.warning(f"Failed to get price from Jupiter for {token_address}: {e}")
            
            # Fallback to placeholder price for devnet/testing
            if self.config.enable_devnet_testing:
                logger.info("Using placeholder price for devnet testing")
                return 0.001  # 0.001 SOL per token
            else:
                raise TradingError(f"Failed to get token price: {e}")

    async def _execute_trade(self, order: TradeOrder, expected_amount: float) -> TradeResult:
        """Execute trade on blockchain"""
        try:
            # Build transaction
            transaction = await self._build_trade_transaction(order, expected_amount)
            
            # Sign transaction
            signed_tx = self.wallet.sign_transaction(transaction)
            
            # Send transaction with retry logic
            tx_hash = await self._send_transaction_with_retry(signed_tx)
            
            # Wait for confirmation
            confirmed = await self._wait_for_confirmation(tx_hash)
            
            if not confirmed:
                raise TradingError("Transaction not confirmed")
            
            # Create trade result
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

    async def _build_trade_transaction(
        self, order: TradeOrder, expected_amount: float
    ) -> Transaction:
        """Build trade transaction using Jupiter aggregator"""
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
            
            # Get quote from Jupiter
            quote = await self.jupiter_client.get_quote(
                input_mint=input_mint,
                output_mint=output_mint,
                amount=amount,
                slippage_bps=self.config.jupiter_slippage_bps
            )
            
            # Get swap transaction from Jupiter
            swap_data = await self.jupiter_client.get_swap_transaction(
                quote_response=quote,
                user_public_key=self.wallet.address
            )
            
            if "swapTransaction" not in swap_data:
                raise TradingError("No swap transaction returned from Jupiter")
            
            # Decode and return the transaction
            transaction_bytes = base64.b64decode(swap_data["swapTransaction"])
            transaction = Transaction.deserialize(transaction_bytes)
            
            logger.info(f"Built transaction using Jupiter: {quote.get('routePlan', [])}")
            return transaction
            
        except Exception as e:
            logger.error(f"Failed to build transaction with Jupiter: {e}")
            
            # Fallback to basic transaction if Jupiter fails
            logger.warning("Falling back to basic transaction")
            transaction = Transaction()
            return transaction

    async def _send_transaction_with_retry(self, signed_tx: bytes) -> str:
        """Send transaction with retry logic"""
        for attempt in range(self.config.max_retries):
            try:
                # Send transaction
                opts = TxOpts(
                    skip_preflight=self.config.skip_preflight,
                    preflight_commitment=self.config.commitment
                )
                
                result = self.client.send_raw_transaction(signed_tx, opts=opts)
                
                if result.value:
                    return str(result.value)
                
                raise TradingError("Transaction failed to send")
                
            except Exception as e:
                if attempt == self.config.max_retries - 1:
                    raise
                
                logger.warning(f"Transaction attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(self.config.retry_delay)

    async def _wait_for_confirmation(self, tx_hash: str, timeout: float = 30.0) -> bool:
        """Wait for transaction confirmation"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Check transaction status
                confirmation = self.client.get_confirmed_transaction(tx_hash)
                if confirmation.value and confirmation.value.transaction:
                    return True
                
                await asyncio.sleep(1.0)
                
            except Exception as e:
                logger.warning(f"Error checking confirmation: {e}")
                await asyncio.sleep(1.0)
        
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