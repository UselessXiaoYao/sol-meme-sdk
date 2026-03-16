"""
Exception classes for Sol Meme SDK
"""


class SolMemeError(Exception):
    """Base exception for all SDK errors"""
    pass


class WalletError(SolMemeError):
    """Wallet-related errors"""
    pass


class TradingError(SolMemeError):
    """Trading-related errors"""
    pass


class NetworkError(SolMemeError):
    """Network communication errors"""
    pass


class InsufficientFundsError(TradingError):
    """Insufficient funds for transaction"""
    pass


class InvalidTokenError(TradingError):
    """Invalid token address or token not found"""
    pass


class TransactionError(TradingError):
    """Transaction execution errors"""
    pass