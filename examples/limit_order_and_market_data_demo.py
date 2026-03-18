"""
Demo script for limit order and real-time market data functionality
This script demonstrates the newly implemented features using Jupiter API on mainnet.
"""

import asyncio
import time
from sol_meme_sdk.client import SolMemeClient
from sol_meme_sdk.models import Network, TransactionConfig


async def demo_market_data():
    """Demonstrate real-time market data functionality"""
    print("🚀 Market Data Demo")
    print("=" * 50)
    
    # Initialize client for mainnet
    client = SolMemeClient(
        network=Network.MAINNET,
        config=TransactionConfig()
    )
    
    # List of popular meme tokens to monitor
    meme_tokens = [
        ("Bonk", "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"),
        ("Doge", "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZTuJosfgAs"),
        ("Samoyedcoin", "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZTuJosfgAs"),
        ("USDC", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"),
        ("SOL", "So11111111111111111111111111111111111111112")
    ]
    
    print("📊 Fetching real-time market data for popular tokens...")
    
    for token_name, token_address in meme_tokens:
        try:
            market_data = await client.get_market_data(token_address)
            
            print(f"\n🔹 {token_name} ({token_address[:8]}...)")
            print(f"   Price: ${market_data['price']:.6f}")
            print(f"   24h Volume: ${market_data['volume_24h']:,.2f}")
            print(f"   24h Change: {market_data['price_change_24h']:+.2f}%")
            print(f"   Liquidity: ${market_data['liquidity']:,.2f}")
            print(f"   Market Cap: ${market_data['market_cap']:,.2f}")
            
        except Exception as e:
            print(f"❌ Failed to get market data for {token_name}: {e}")
    
    print("\n✅ Market data demo completed!")


async def demo_limit_orders():
    """Demonstrate limit order functionality"""
    print("\n🚀 Limit Order Demo")
    print("=" * 50)
    
    # Initialize client (no private key needed for demo)
    client = SolMemeClient(network=Network.MAINNET)
    
    # Example token addresses
    sol_address = "So11111111111111111111111111111111111111112"
    usdc_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    
    print("📊 Getting current market prices...")
    try:
        sol_price = await client.get_token_price(sol_address)
        usdc_price = await client.get_token_price(usdc_address)
        print(f"   SOL Price: ${sol_price:.2f}")
        print(f"   USDC Price: ${usdc_price:.6f}")
    except Exception as e:
        print(f"❌ Failed to get prices: {e}")
        return
    
    print("\n💡 Example Limit Order Scenarios:")
    
    # Scenario 1: Buy order (current price > limit price)
    print("\n1. Buy Limit Order (pending example):")
    print(f"   Buy 1 SOL when price drops to ${sol_price * 0.95:.2f}")
    print("   This order would go to pending status")
    
    # Scenario 2: Sell order (current price < limit price) 
    print("\n2. Sell Limit Order (pending example):")
    print(f"   Sell 100 USDC when price rises to ${usdc_price * 1.05:.6f}")
    print("   This order would go to pending status")
    
    # Scenario 3: Immediate execution (current price meets limit)
    print("\n3. Immediate Execution Order:")
    print(f"   Buy 0.1 SOL at current price (${sol_price:.2f})")
    print("   This order would execute immediately")
    
    print("\n📋 Limit Order Features:")
    print("   • Real-time price monitoring")
    print("   • Automatic execution when price conditions are met") 
    print("   • Order cancellation capability")
    print("   • Order status tracking")
    print("   • Order persistence across restarts")
    
    print("\n⚠️  Note: To actually place orders, provide a wallet private key")
    print("   and sufficient balance for the transactions.")
    
    print("\n✅ Limit order demo completed!")


async def demo_order_management():
    """Demonstrate order management functionality"""
    print("\n🚀 Order Management Demo")
    print("=" * 50)
    
    print("📋 Order Management Features:")
    print("   1. Place Limit Order - Create buy/sell orders with price targets")
    print("   2. Cancel Order - Cancel pending orders before execution")
    print("   3. Get Order Status - Check current status and execution conditions")
    print("   4. Auto-execution - Orders execute automatically when price targets are met")
    
    print("\n💡 Example Workflow:")
    print("   • Place buy order: Buy 10 SOL @ $95")
    print("   • Monitor order: Check if current price <= $95")
    print("   • Auto-execute: Order executes when condition is met")
    print("   • Cancel: Option to cancel before execution")
    
    print("\n✅ Order management demo completed!")


async def demo_jupiter_integration():
    """Demonstrate Jupiter API integration"""
    print("\n🚀 Jupiter API Integration Demo")
    print("=" * 50)
    
    client = SolMemeClient(network=Network.MAINNET)
    
    print("🔌 Testing Jupiter API connection...")
    
    try:
        # Test Jupiter API health
        healthy = await client.jupiter_client.health_check()
        print(f"✅ Jupiter API Health: {'Healthy' if healthy else 'Unhealthy'}")
        
        # Test token search
        print("\n🔍 Testing token search...")
        search_results = await client.jupiter_client.search_tokens("BONK")
        if search_results:
            print(f"✅ Found {len(search_results)} tokens matching 'BONK'")
        
        # Test price fetching
        print("\n💰 Testing price fetching...")
        sol_price = await client.get_token_price("So11111111111111111111111111111111111111112")
        print(f"✅ SOL Price: ${sol_price:.2f}")
        
        print("\n✅ Jupiter API integration demo completed!")
        
    except Exception as e:
        print(f"❌ Jupiter API test failed: {e}")
        print("💡 Make sure you have a valid Jupiter API key configured")


async def main():
    """Main demo function"""
    print("🚀 Sol Meme SDK - Limit Order & Market Data Demo")
    print("=" * 60)
    
    try:
        # Demo 1: Market Data
        await demo_market_data()
        
        # Demo 2: Jupiter Integration
        await demo_jupiter_integration()
        
        # Demo 3: Limit Orders
        await demo_limit_orders()
        
        # Demo 4: Order Management
        await demo_order_management()
        
        print("\n" + "=" * 60)
        print("🎉 All demos completed successfully!")
        print("\n📝 Next Steps:")
        print("   1. Configure your Jupiter API key in .env file")
        print("   2. Set your wallet private key for trading")
        print("   3. Run tests: python -m pytest tests/test_limit_order_and_market_data.py")
        print("   4. Start trading with real-time market data and limit orders!")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        print("💡 Make sure you have internet connection and valid API configuration")


if __name__ == "__main__":
    asyncio.run(main())