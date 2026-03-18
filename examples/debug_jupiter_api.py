#!/usr/bin/env python3
"""
Debug Jupiter API endpoints
"""

import asyncio
import sys
import os

# Add the SDK to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import aiohttp
from sol_meme_sdk.config import get_config


async def debug_api_endpoints():
    """Debug Jupiter API endpoints"""
    
    config = get_config()
    api_key = config.jupiter_api_key
    
    print("🔍 Debugging Jupiter API Endpoints")
    print("=" * 60)
    
    # Test different endpoint combinations
    endpoints = [
        "https://api.jup.ag/quote/v6",
        "https://api.jup.ag/swap/v6", 
        "https://api.jup.ag/tokens/v6",
        "https://api.jup.ag/quote",
        "https://api.jup.ag/swap",
        "https://api.jup.ag/tokens",
    ]
    
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    for endpoint in endpoints:
        print(f"\n🔄 Testing: {endpoint}")
        
        try:
            async with aiohttp.ClientSession() as session:
                # Test simple GET request
                async with session.get(endpoint, headers=headers, timeout=10) as resp:
                    print(f"   Status: {resp.status}")
                    if resp.status == 200:
                        print("   ✅ Endpoint is accessible")
                    elif resp.status == 404:
                        print("   ❌ Endpoint not found")
                    else:
                        error_text = await resp.text()
                        print(f"   Error: {error_text}")
                        
        except Exception as e:
            print(f"   ❌ Connection failed: {e}")
    
    # Test quote endpoint with parameters
    print(f"\n📊 Testing quote endpoint with parameters")
    quote_url = "https://api.jup.ag/quote/v6"
    params = {
        "inputMint": "So11111111111111111111111111111111111111112",  # SOL
        "outputMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
        "amount": 1000000000,  # 1 SOL in lamports
        "slippageBps": 50
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(quote_url, params=params, headers=headers, timeout=10) as resp:
                print(f"   Status: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    print("   ✅ Quote successful!")
                    print(f"   Input: {data.get('inputAmount', 'N/A')}")
                    print(f"   Output: {data.get('outputAmount', 'N/A')}")
                else:
                    error_text = await resp.text()
                    print(f"   Error: {error_text}")
                    
    except Exception as e:
        print(f"   ❌ Quote request failed: {e}")


async def main():
    """Run the debug"""
    await debug_api_endpoints()


if __name__ == "__main__":
    asyncio.run(main())