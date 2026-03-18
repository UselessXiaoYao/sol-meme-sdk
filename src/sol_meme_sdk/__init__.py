"""
Sol Meme SDK - Python SDK for trading meme coins on Solana blockchain
"""

from .client import SolMemeClient
from .wallet import Wallet
from .models import TokenInfo, TradeOrder, TradeResult, Network, TransactionConfig, DEXProtocol
from .exceptions import (
    SolMemeError,
    WalletError,
    TradingError,
    NetworkError,
    InsufficientFundsError,
    InvalidTokenError,
)

__version__ = "0.2.0"
__all__ = [
    "SolMemeClient",
    "Wallet",
    "TokenInfo",
    "TradeOrder",
    "TradeResult",
    "Network",
    "TransactionConfig",
    "DEXProtocol",
    "SolMemeError",
    "WalletError",
    "TradingError",
    "NetworkError",
    "InsufficientFundsError",
    "InvalidTokenError",
]