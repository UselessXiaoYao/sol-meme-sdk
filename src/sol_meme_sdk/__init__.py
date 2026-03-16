"""
Sol Meme SDK - Python SDK for trading meme coins on Solana blockchain
"""

from .client import SolMemeClient
from .wallet import Wallet
from .models import TokenInfo, TradeOrder, TradeResult, Network, TransactionConfig
from .exceptions import (
    SolMemeError,
    WalletError,
    TradingError,
    NetworkError,
    InsufficientFundsError,
)

__version__ = "0.1.0"
__all__ = [
    "SolMemeClient",
    "Wallet",
    "TokenInfo",
    "TradeOrder",
    "TradeResult",
    "Network",
    "TransactionConfig",
    "SolMemeError",
    "WalletError",
    "TradingError",
    "NetworkError",
    "InsufficientFundsError",
]