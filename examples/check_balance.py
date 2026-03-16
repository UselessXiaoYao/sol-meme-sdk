#!/usr/bin/env python3
"""
Check wallet balance on devnet
"""

import asyncio
from sol_meme_sdk import SolMemeClient, Network


async def main():
    """Check wallet balance"""
    
    # 使用之前生成的钱包（从basic_usage.py的输出中获取私钥）
    private_key = "Vga8kazq8LEnqp1qo9jVawPyfYPA4jU8b85tt7ydW9PXireEt3jxPnnPNrCT9SzyAihLjjNjcJAoYtt3WFMfvan"
    
    # 初始化客户端
    client = SolMemeClient(
        network=Network.DEVNET,
        private_key=private_key
    )
    
    try:
        # 连接到网络
        print("Connecting to Solana devnet...")
        await client.connect()
        
        # 获取钱包信息
        wallet_info = await client.get_wallet_info()
        print(f"\nWallet Information:")
        print(f"Address: {wallet_info['address']}")
        print(f"SOL Balance: {wallet_info['balance_sol']:.6f} SOL")
        
        # 如果余额为0，提示获取测试SOL
        if wallet_info['balance_sol'] == 0:
            print("\n⚠️  Your wallet has 0 SOL. Please get test SOL from:")
            print("1. https://faucet.solana.com/")
            print("2. https://solfaucet.com/")
            print(f"\nWallet address: {wallet_info['address']}")
        else:
            print(f"✅  You have {wallet_info['balance_sol']:.6f} SOL for testing!")
        
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        # 清理
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())