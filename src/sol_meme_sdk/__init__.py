"""
Sol Meme SDK - Python SDK for trading meme coins on Solana blockchain
"""

from .client import SolMemeClient
from .wallet import Wallet
from .models import TokenInfo, TradeOrder, TradeResult, Network, TransactionConfig, DEXProtocol
from .raydium_client import RaydiumClient
from .meteora_client import MeteoraClient
from .multi_dex_client import MultiDexClient
from .exceptions import (
    SolMemeError,
    WalletError,
    TradingError,
    NetworkError,
    InsufficientFundsError,
    InvalidTokenError,
)

__version__ = "0.3.0"
__all__ = [
    "SolMemeClient",
    "Wallet",
    "TokenInfo",
    "TradeOrder",
    "TradeResult",
    "Network",
    "TransactionConfig",
    "DEXProtocol",
    "RaydiumClient",
    "MeteoraClient",
    "MultiDexClient",
    "SolMemeError",
    "WalletError",
    "TradingError",
    "NetworkError",
    "InsufficientFundsError",
    "InvalidTokenError",
]