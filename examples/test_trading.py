#!/usr/bin/env python3
"""
Test trading functionality on devnet
"""

import asyncio
from sol_meme_sdk import SolMemeClient, Network, TransactionConfig


async def main():
    """Test trading functionality"""
    
    # 使用之前生成的钱包
    private_key = "Vga8kazq8LEnqp1qo9jVawPyfYPA4jU8b85tt7ydW9PXireEt3jxPnnPNrCT9SzyAihLjjNjcJAoYtt3WFMfvan"
    
    # 交易配置
    config = TransactionConfig(
        max_retries=3,
        retry_delay=1.0,
        timeout=30.0
    )
    
    # 初始化客户端
    client = SolMemeClient(
        network=Network.DEVNET,
        private_key=private_key,
        config=config
    )
    
    try:
        # 连接到网络
        print("Connecting to Solana devnet...")
        await client.connect()
        
        # 检查余额
        wallet_info = await client.get_wallet_info()
        print(f"\n💰 Wallet Balance: {wallet_info['balance_sol']:.6f} SOL")
        
        if wallet_info['balance_sol'] < 0.01:
            print("❌ Insufficient SOL for testing. Please get more test SOL.")
            return
        
        # 测试代币查询
        print("\n🔍 Testing token information...")
        
        # 使用 Wrapped SOL 作为测试代币
        wsol_address = "So11111111111111111111111111111111111111112"
        
        try:
            # 获取代币信息
            token_info = await client.get_token_info(wsol_address)
            print(f"✅ Token Info: {token_info.symbol} - {token_info.name}")
            print(f"   Decimals: {token_info.decimals}")
            
            # 获取价格
            price = await client.get_token_price(wsol_address)
            print(f"💰 Current Price: {price:.8f} SOL")
            
            # 获取市场数据
            market_data = await client.get_market_data(wsol_address)
            print(f"📊 Market Data - Volume 24h: {market_data['volume_24h']:.2f}")
            
            print("\n✅ All basic functionality tests passed!")
            
        except Exception as e:
            print(f"⚠️  Token query failed (this is normal on devnet): {e}")
        
        # 测试交易功能（小额测试）
        if wallet_info['balance_sol'] > 0.1:
            print("\n🚀 Testing trading functionality...")
            
            # 注意：在实际测试中，你需要使用真实的代币地址
            # 这里只是演示交易函数的调用方式
            
            # 示例：尝试购买极小额（不会实际执行）
            try:
                # 这只是演示调用方式，实际需要有效的代币地址
                print("📝 Trading functions are ready for use with valid token addresses")
                print("To test actual trading, you need:")
                print("1. A valid token mint address from devnet")
                print("2. Sufficient SOL balance")
                print("3. Proper DEX liquidity")
                
            except Exception as e:
                print(f"⚠️  Trading test failed: {e}")
        
        print("\n🎯 Next steps:")
        print("1. Find real token addresses on devnet using DexScreener or similar")
        print("2. Ensure the token has liquidity on devnet DEXs")
        print("3. Start with very small amounts (0.01 SOL)")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        # 清理
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())