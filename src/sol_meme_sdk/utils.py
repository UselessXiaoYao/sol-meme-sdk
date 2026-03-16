"""
Utility functions for Sol Meme SDK
"""

import base58
import hashlib
import logging
import time
from typing import Optional, Union
from decimal import Decimal

from solders.pubkey import Pubkey

from .exceptions import SolMemeError

logger = logging.getLogger(__name__)


def validate_solana_address(address: str) -> bool:
    """
    Validate Solana address format
    
    Args:
        address: Address to validate
        
    Returns:
        True if valid Solana address
    """
    try:
        # Check if it's a valid base58 encoded public key
        Pubkey.from_string(address)
        return True
    except Exception:
        return False


def sol_to_lamports(amount: Union[float, Decimal]) -> int:
    """
    Convert SOL amount to lamports
    
    Args:
        amount: SOL amount
        
    Returns:
        Amount in lamports
    """
    if isinstance(amount, Decimal):
        amount = float(amount)
    return int(amount * 1e9)


def lamports_to_sol(lamports: int) -> float:
    """
    Convert lamports to SOL
    
    Args:
        lamports: Amount in lamports
        
    Returns:
        Amount in SOL
    """
    return lamports / 1e9


def calculate_slippage_amount(amount: float, slippage_percent: float) -> tuple:
    """
    Calculate minimum and maximum amounts based on slippage
    
    Args:
        amount: Base amount
        slippage_percent: Slippage percentage
        
    Returns:
        Tuple of (min_amount, max_amount)
    """
    slippage_factor = slippage_percent / 100
    min_amount = amount * (1 - slippage_factor)
    max_amount = amount * (1 + slippage_factor)
    return min_amount, max_amount


def generate_order_id() -> str:
    """
    Generate unique order ID
    
    Returns:
        Unique order ID string
    """
    timestamp = int(time.time() * 1000)
    random_bytes = hashlib.sha256(str(timestamp).encode()).digest()[:8]
    return f"order_{timestamp}_{base58.b58encode(random_bytes).decode()[:8]}"


def format_token_amount(amount: float, decimals: int) -> str:
    """
    Format token amount with proper decimal places
    
    Args:
        amount: Raw amount
        decimals: Token decimals
        
    Returns:
        Formatted amount string
    """
    divisor = 10 ** decimals
    formatted = amount / divisor
    return f"{formatted:.{decimals}f}"


def parse_token_amount(amount_str: str, decimals: int) -> float:
    """
    Parse token amount string to raw amount
    
    Args:
        amount_str: Formatted amount string
        decimals: Token decimals
        
    Returns:
        Raw amount
    """
    try:
        amount = float(amount_str)
        return amount * (10 ** decimals)
    except ValueError as e:
        raise SolMemeError(f"Invalid amount format: {amount_str}")


def safe_divide(numerator: float, denominator: float) -> float:
    """
    Safe division with zero check
    
    Args:
        numerator: Numerator
        denominator: Denominator
        
    Returns:
        Division result or 0 if denominator is 0
    """
    if denominator == 0:
        return 0.0
    return numerator / denominator


def retry_on_exception(
    max_retries: int = 3,
    delay: float = 1.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator for retrying functions on exception
    
    Args:
        max_retries: Maximum retry attempts
        delay: Delay between retries in seconds
        exceptions: Exceptions to catch
    """
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries - 1:
                        raise
                    logger.warning(f"Attempt {attempt + 1} failed: {e}")
                    await asyncio.sleep(delay)
        
        def sync_wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries - 1:
                        raise
                    logger.warning(f"Attempt {attempt + 1} failed: {e}")
                    time.sleep(delay)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def setup_logging(level: int = logging.INFO, log_file: Optional[str] = None):
    """
    Setup logging configuration
    
    Args:
        level: Logging level
        log_file: Optional log file path
    """
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=level,
        format=log_format,
        handlers=handlers
    )


def is_token_address(address: str) -> bool:
    """
    Check if address might be a token mint address
    
    Args:
        address: Address to check
        
    Returns:
        True if likely a token address
    """
    # Basic validation - token addresses are valid Solana addresses
    return validate_solana_address(address)


def estimate_transaction_fee(size: int) -> float:
    """
    Estimate transaction fee in SOL
    
    Args:
        size: Transaction size in bytes
        
    Returns:
        Estimated fee in SOL
    """
    # Base fee is 5000 lamports + 1000 lamports per signature
    # This is a simplified estimation
    base_fee = 5000
    signature_fee = 1000  # Per signature
    
    # Estimate 2 signatures (user + possibly program)
    total_lamports = base_fee + (2 * signature_fee)
    return lamports_to_sol(total_lamports)


def human_readable_amount(amount: float, decimals: int = 9) -> str:
    """
    Convert amount to human readable format
    
    Args:
        amount: Raw amount
        decimals: Number of decimal places
        
    Returns:
        Human readable string
    """
    if amount >= 1_000_000:
        return f"{amount/1_000_000:.2f}M"
    elif amount >= 1_000:
        return f"{amount/1_000:.2f}K"
    else:
        return f"{amount:.{min(decimals, 6)}f}"


# Import asyncio for async wrapper
import asyncio