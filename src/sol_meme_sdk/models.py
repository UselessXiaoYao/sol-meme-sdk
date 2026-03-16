"""
Data models for Sol Meme SDK
"""

from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class OrderType(str, Enum):
    """Order types"""
    MARKET = "market"
    LIMIT = "limit"


class OrderSide(str, Enum):
    """Order sides"""
    BUY = "buy"
    SELL = "sell"


class Network(str, Enum):
    """Solana networks"""
    MAINNET = "mainnet"
    DEVNET = "devnet"
    TESTNET = "testnet"


class TokenInfo(BaseModel):
    """Token information model"""
    address: str = Field(..., description="Token mint address")
    symbol: str = Field(..., description="Token symbol")
    name: str = Field(..., description="Token name")
    decimals: int = Field(..., description="Token decimals")
    supply: Optional[int] = Field(None, description="Total supply")
    price: Optional[float] = Field(None, description="Current price in SOL")
    market_cap: Optional[float] = Field(None, description="Market capitalization")
    liquidity: Optional[float] = Field(None, description="Liquidity amount")


class TradeOrder(BaseModel):
    """Trade order model"""
    token_address: str = Field(..., description="Token mint address")
    side: OrderSide = Field(..., description="Buy or sell")
    order_type: OrderType = Field(..., description="Market or limit")
    amount: float = Field(..., description="Amount to trade")
    price: Optional[float] = Field(None, description="Limit price (for limit orders)")
    slippage: float = Field(0.5, description="Slippage tolerance in percentage")


class TradeResult(BaseModel):
    """Trade execution result"""
    order_id: str = Field(..., description="Unique order identifier")
    token_address: str = Field(..., description="Token mint address")
    side: OrderSide = Field(..., description="Buy or sell")
    executed_amount: float = Field(..., description="Executed amount")
    executed_price: float = Field(..., description="Average execution price")
    total_cost: float = Field(..., description="Total cost/revenue")
    transaction_hash: str = Field(..., description="Transaction hash")
    timestamp: datetime = Field(default_factory=datetime.now, description="Execution time")
    status: str = Field("completed", description="Order status")


class WalletInfo(BaseModel):
    """Wallet information model"""
    address: str = Field(..., description="Wallet address")
    balance_sol: float = Field(..., description="SOL balance")
    tokens: Dict[str, float] = Field(default_factory=dict, description="Token balances")
    total_value: Optional[float] = Field(None, description="Total portfolio value in SOL")


class MarketData(BaseModel):
    """Market data model"""
    token_address: str = Field(..., description="Token mint address")
    price: float = Field(..., description="Current price")
    volume_24h: float = Field(..., description="24h trading volume")
    price_change_24h: float = Field(..., description="24h price change percentage")
    liquidity: float = Field(..., description="Current liquidity")
    timestamp: datetime = Field(default_factory=datetime.now, description="Data timestamp")


class TransactionConfig(BaseModel):
    """Transaction configuration"""
    max_retries: int = Field(3, description="Maximum retry attempts")
    retry_delay: float = Field(1.0, description="Retry delay in seconds")
    timeout: float = Field(30.0, description="Transaction timeout in seconds")
    skip_preflight: bool = Field(False, description="Skip preflight checks")
    commitment: str = Field("confirmed", description="Blockchain commitment level")