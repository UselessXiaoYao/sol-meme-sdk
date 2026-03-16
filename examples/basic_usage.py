#!/usr/bin/env python3
"""
Basic usage example for Sol Meme SDK
"""

import asyncio
import os
from sol_meme_sdk import SolMemeClient, Network, TransactionConfig


async def main():
    """Basic SDK usage example"""
    
    # Configuration
    config = TransactionConfig(
        max_retries=3,
        retry_delay=1.0,
        timeout=30.0
    )
    
    # Initialize client
    client = SolMemeClient(
        network=Network.DEVNET,  # Use devnet for testing
        private_key=None,  # Generate new wallet
        config=config
    )
    
    try:
        # Connect to network
        print("Connecting to Solana...")
        await client.connect()
        
        # Get wallet info
        print("\nWallet Information:")
        wallet_info = await client.get_wallet_info()
        print(f"Address: {wallet_info['address']}")
        print(f"SOL Balance: {wallet_info['balance_sol']:.6f} SOL")
        
        # Example token address (replace with actual token)
        token_address = "So11111111111111111111111111111111111111112"  # SOL placeholder
        
        # Get token info
        print(f"\nToken Information:")
        token_info = await client.get_token_info(token_address)
        print(f"Symbol: {token_info.symbol}")
        print(f"Name: {token_info.name}")
        print(f"Decimals: {token_info.decimals}")
        
        # Get token price
        price = await client.get_token_price(token_address)
        print(f"Current Price: {price:.8f} SOL")
        
        # Get market data
        market_data = await client.get_market_data(token_address)
        print(f"24h Volume: {market_data['volume_24h']:.2f}")
        print(f"24h Change: {market_data['price_change_24h']:.2f}%")
        
        # Export wallet (for backup)
        wallet_json = client.export_wallet()
        print(f"\nWallet backup (save this securely):")
        print(wallet_json)
        
        # Note: Actual trading would require funds and real token addresses
        print("\nNote: To execute real trades, you need:")
        print("1. Fund your wallet with SOL")
        print("2. Use actual token addresses from DEXs")
        print("3. Test on devnet first")
        
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        # Clean up
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())