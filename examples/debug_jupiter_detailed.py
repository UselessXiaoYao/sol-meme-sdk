#!/usr/bin/env python3
"""
Detailed debug of Jupiter API endpoints and parameters
"""

import asyncio
import sys
import os
import logging

# Add the SDK to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

import aiohttp
from sol_meme_sdk.config import get_config


async def debug_api_endpoints_detailed():
    """Detailed debug of Jupiter API endpoints"""
    
    config = get_config()
    api_key = config.jupiter_api_key
    
    print("🔍 Detailed Debug of Jupiter API")
    print("=" * 60)
    
    # Test different endpoint patterns based on Jupiter API documentation
    endpoints_to_test = [
        # Ultra Swap API (recommended) - /ultra/v1/
        ("https://api.jup.ag/ultra/v1/order", "GET", {
            "inputMint": "So11111111111111111111111111111111111111112", 
            "outputMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", 
            "amount": "100000000", 
            "slippageBps": 50,
            "taker": "BQ72nSv9f3PRyRKCBnHLVrerrv37CYTHm5h3s9VSGQDV",
            "restrictIntermediateTokens": "true"
        }),
        
        # Ultra API search endpoint
        ("https://api.jup.ag/ultra/v1/search", "GET", {"query": "USDC"}),
        
        # Metis Swap API (legacy but still functional) - /swap/v1/
        ("https://api.jup.ag/swap/v1/quote", "GET", {
            "inputMint": "So11111111111111111111111111111111111111112",
            "outputMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "amount": 100000000,
            "slippageBps": 50,
            "swapMode": "ExactIn",
            "restrictIntermediateTokens": "true",
            "instructionVersion": "V2"
        }),
        
        ("https://api.jup.ag/swap/v1/program-id-to-label", "GET", {}),
        
        # Tokens API - /tokens/v2/
        ("https://api.jup.ag/tokens/v2/search", "GET", {"query": "JUP"}),
        
        ("https://api.jup.ag/tokens/v2/recent", "GET", {}),
        
        # Price API - /price/v3/
        ("https://api.jup.ag/price/v3/price", "GET", {
            "ids": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
            "vsToken": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        }),
        
        # Additional working endpoints from testing
        ("https://api.jup.ag/tokens/v2/search", "GET", {"query": "So11111111111111111111111111111111111111112"}),
        
        ("https://api.jup.ag/tokens/v2/search", "GET", {"query": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"}),
        
        # Test with real Ultra API parameters
        ("https://api.jup.ag/ultra/v1/order", "GET", {
            "inputMint": "So11111111111111111111111111111111111111112", 
            "outputMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", 
            "amount": "100000000", 
            "slippageBps": 50
        }),
        
        # Test with minimal parameters
        ("https://api.jup.ag/ultra/v1/order", "GET", {
            "inputMint": "So11111111111111111111111111111111111111112", 
            "outputMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", 
            "amount": "100000000"
        })
    ]
    
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    for url, method, params in endpoints_to_test:
        print(f"\n🔄 Testing: {method} {url}")
        print(f"   Parameters: {params}")
        
        try:
            async with aiohttp.ClientSession() as session:
                if method == "GET":
                    async with session.get(url, params=params, headers=headers, timeout=10) as resp:
                        print(f"   Status: {resp.status}")
                        if resp.status == 200:
                            data = await resp.json()
                            if isinstance(data, dict):
                                print(f"   ✅ Success! Response keys: {list(data.keys())}")
                            elif isinstance(data, list):
                                print(f"   ✅ Success! Array response with {len(data)} items")
                                if len(data) > 0:
                                    print(f"   First item keys: {list(data[0].keys())}")
                            else:
                                print(f"   ✅ Success! Response type: {type(data)}")
                        else:
                            error_text = await resp.text()
                            print(f"   ❌ Error: {error_text}")
                elif method == "POST":
                    async with session.post(url, json=params, headers=headers, timeout=10) as resp:
                        print(f"   Status: {resp.status}")
                        if resp.status == 200:
                            data = await resp.json()
                            if isinstance(data, dict):
                                print(f"   ✅ Success! Response keys: {list(data.keys())}")
                            elif isinstance(data, list):
                                print(f"   ✅ Success! Array response with {len(data)} items")
                            else:
                                print(f"   ✅ Success! Response type: {type(data)}")
                        else:
                            error_text = await resp.text()
                            print(f"   ❌ Error: {error_text}")
                        
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    
    # Test the current Jupiter client implementation
    print("\n" + "=" * 60)
    print("🔧 Testing Current Jupiter Client Implementation")
    print("=" * 60)
    
    from src.sol_meme_sdk.jupiter_client import JupiterClient
    
    try:
        client = JupiterClient(network="mainnet-beta")
        print(f"✅ Client initialized")
        print(f"   Base URL: {client.base_url}")
        print(f"   Quote Endpoint: {client.quote_endpoint}")
        print(f"   Swap Endpoint: {client.swap_endpoint}")
        print(f"   Tokens Endpoint: {client.tokens_endpoint}")
        
        # Test getting a quote
        print("\n💰 Testing quote functionality...")
        quote = await client.get_quote(
            input_mint="So11111111111111111111111111111111111111112",
            output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            amount=1.0
        )
        print(f"✅ Quote successful!")
        
    except Exception as e:
        print(f"❌ Client test failed: {e}")


async def main():
    """Run the debug"""
    await debug_api_endpoints_detailed()


if __name__ == "__main__":
    asyncio.run(main())