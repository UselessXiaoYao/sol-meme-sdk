"""
Trading functionality for Sol Meme SDK
"""

import asyncio
import logging
import time
from typing import Optional, List, Dict, Any
from decimal import Decimal
from solders.pubkey import Pubkey
from solana.rpc.api import Client
from solana.rpc.types import TxOpts
from solana.transaction import Transaction

from .models import TradeOrder, TradeResult, OrderType, OrderSide, TransactionConfig
from .exceptions import TradingError, InsufficientFundsError, InvalidTokenError

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
        
        # Common token addresses (example addresses)
        self.common_tokens = {
            "SOL": "So11111111111111111111111111111111111111112",
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
        """Get token information from on-chain data"""
        try:
            # This would query token metadata and market data
            # For now, return basic info
            return {
                "address": token_address,
                "decimals": 6,  # Default, should be fetched from chain
                "symbol": "UNKNOWN",
                "name": "Unknown Token"
            }
        except Exception as e:
            raise InvalidTokenError(f"Failed to get token info: {e}")

    async def _get_token_balance(self, token_address: str) -> float:
        """Get token balance for wallet"""
        try:
            # This would query token accounts
            # For now, return 0 (placeholder)
            return 0.0
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
        """Get current token price in SOL"""
        try:
            # This would query price from DEX or price oracle
            # For now, return placeholder price
            return 0.001  # 0.001 SOL per token
        except Exception as e:
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
        """Build trade transaction"""
        # This would build the actual transaction for token swap
        # For now, return placeholder transaction
        transaction = Transaction()
        
        # Add instructions for token swap based on order type
        # This would interact with Raydium, Jupiter, or other DEXs
        
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