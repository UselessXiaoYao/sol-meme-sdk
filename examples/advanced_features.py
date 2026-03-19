"""
Advanced features demonstration for Sol Meme SDK
"""

import asyncio
import logging
from datetime import datetime

from sol_meme_sdk import SolMemeClient
from sol_meme_sdk.models import Network
from sol_meme_sdk.strategies import StrategyType
from sol_meme_sdk.monitor import AlertType

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demo_advanced_features():
    """Demonstrate advanced SDK features"""
    
    print("=== Sol Meme SDK Advanced Features Demo ===\n")
    
    # Initialize client
    client = SolMemeClient(network=Network.DEVNET)
    
    try:
        # Connect to network
        print("1. Connecting to Solana network...")
        connected = await client.connect()
        if not connected:
            print("❌ Failed to connect to network")
            return
        print("✅ Connected successfully\n")
        
        # Get wallet info
        print("2. Getting wallet information...")
        wallet_info = await client.get_wallet_info()
        print(f"   Wallet address: {wallet_info['address']}")
        print(f"   SOL balance: {wallet_info['balance_sol']:.6f} SOL\n")
        
        # Demo portfolio management
        print("3. Portfolio Management Features")
        portfolio_value = await client.get_portfolio_value()
        print(f"   Total portfolio value: {portfolio_value:.6f} SOL")
        
        detailed_portfolio = await client.get_detailed_portfolio()
        print(f"   SOL balance: {detailed_portfolio.get('sol_balance', 0):.6f} SOL")
        print(f"   Number of tokens: {len(detailed_portfolio.get('tokens', {}))}\n")
        
        # Demo price monitoring
        print("4. Price Monitoring Features")
        
        # Token addresses for demonstration
        sol_mint = "So11111111111111111111111111111111111111112"
        usdc_mint = "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU"  # Devnet USDC
        
        # Add tokens to monitor
        client.monitor_token(sol_mint, interval=10.0)
        client.monitor_token(usdc_mint, interval=10.0)
        
        # Add price alerts
        client.add_price_alert(sol_mint, AlertType.PRICE_ABOVE, 0.1)
        client.add_price_alert(usdc_mint, AlertType.PRICE_BELOW, 0.9)
        
        # Add price callback
        async def price_change_callback(token_address, current_price, previous_price, change_percent):
            print(f"   📊 Price change: {token_address[:8]}... {change_percent:+.2f}% ({previous_price:.6f} -> {current_price:.6f} SOL)")
        
        client.add_price_callback(price_change_callback)
        
        print("   ✅ Price monitoring configured\n")
        
        # Demo trading strategies
        print("5. Trading Strategies")
        
        # Add market maker strategy
        client.add_strategy(
            "market_maker_1",
            StrategyType.MARKET_MAKER,
            max_position_size=0.01,
            max_daily_trades=5,
            cooldown_period=60.0
        )
        
        # Add trend following strategy
        client.add_strategy(
            "trend_follower_1",
            StrategyType.TREND_FOLLOWING,
            max_position_size=0.02,
            stop_loss=0.05,
            take_profit=0.1
        )
        
        print("   ✅ Trading strategies configured\n")
        
        # Demo price history and statistics
        print("6. Market Analysis Features")
        
        # Get current price
        try:
            sol_price = await client.get_token_price(sol_mint)
            print(f"   SOL current price: {sol_price:.6f} SOL (self-reference)")
        except Exception as e:
            print(f"   ⚠️  Failed to get SOL price: {e}")
        
        # Get price statistics (after some monitoring)
        print("   Starting brief monitoring to collect data...")
        
        # Start monitoring for a short period
        await client.start_monitoring()
        
        # Let it run for a few seconds to collect data
        await asyncio.sleep(15)
        
        # Get price stats
        sol_stats = client.get_price_stats(sol_mint)
        if sol_stats:
            print(f"   SOL price statistics:")
            print(f"     Current: {sol_stats.get('current', 0):.6f}")
            print(f"     Min: {sol_stats.get('min', 0):.6f}")
            print(f"     Max: {sol_stats.get('max', 0):.6f}")
            print(f"     Average: {sol_stats.get('average', 0):.6f}")
            print(f"     Volatility: {sol_stats.get('volatility', 0):.2f}%")
        
        print("\n")
        
        # Demo portfolio performance tracking
        print("7. Portfolio Performance Tracking")
        
        performance = client.get_portfolio_performance(period_hours=1)
        if performance:
            print(f"   1-hour performance:")
            print(f"     Start value: {performance.get('start_value', 0):.6f} SOL")
            print(f"     End value: {performance.get('end_value', 0):.6f} SOL")
            print(f"     Return: {performance.get('return_percent', 0):.2f}%")
        
        print("\n")
        
        # Demo advanced trading features
        print("8. Advanced Trading Features")
        
        print("   📋 Advanced Features:")
        print("     • ✅ Limit orders with price triggers")
        print("     • ✅ Order cancellation and status tracking")
        print("     • ✅ Multi-token portfolio management")
        print("     • ✅ Real-time price alerts and notifications")
        print("     • ✅ Automated trading strategies (Market Maker, Momentum)")
        print("     • ✅ Advanced risk management and stop-loss")
        print("     • ✅ Multi-DEX aggregation (Raydium, Meteora, Jupiter)")
        print("     • ✅ BIP39 wallet encryption and secure key management")
        
        print("\n")
        
        # Stop monitoring
        await client.stop_monitoring()
        await client.stop_strategies()
        
        print("✅ Demo completed successfully!")
        print("\n=== Key Features Demonstrated ===")
        print("• Portfolio value tracking")
        print("• Real-time price monitoring")
        print("• Price alerts and callbacks")
        print("• Trading strategy integration")
        print("• Market data analysis")
        print("• Performance tracking")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        logger.error(f"Demo error: {e}")
    
    finally:
        # Cleanup
        await client.close()


async def demo_strategy_execution():
    """Demonstrate strategy execution"""
    
    print("\n=== Strategy Execution Demo ===\n")
    
    client = SolMemeClient(network=Network.DEVNET)
    
    try:
        await client.connect()
        
        # Add a simple strategy
        client.add_strategy(
            "demo_strategy",
            StrategyType.TREND_FOLLOWING,
            max_position_size=0.001,  # Small position for demo
            max_daily_trades=2,
            cooldown_period=10.0
        )
        
        print("Starting strategy execution (will run for 30 seconds)...")
        
        # Start strategies
        strategy_task = asyncio.create_task(client.start_strategies(interval=5.0))
        
        # Let it run for 30 seconds
        await asyncio.sleep(30)
        
        # Stop strategies
        await client.stop_strategies()
        strategy_task.cancel()
        
        print("Strategy demo completed")
        
    except Exception as e:
        print(f"Strategy demo failed: {e}")
    
    finally:
        await client.close()


if __name__ == "__main__":
    print("Sol Meme SDK - Advanced Features Demonstration")
    print("=" * 50)
    
    # Run main demo
    asyncio.run(demo_advanced_features())
    
    # Uncomment to run strategy demo
    # asyncio.run(demo_strategy_execution())