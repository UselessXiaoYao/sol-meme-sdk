#!/usr/bin/env python3
"""
Create a new wallet for testing
"""

import asyncio
from sol_meme_sdk import SolMemeClient, Network, Wallet


async def main():
    """Create and test a new wallet"""
    
    print("🆕 Creating a new wallet...")
    
    # 创建新钱包
    wallet = Wallet()
    
    print("✅ Wallet created successfully!")
    print(f"\n📋 Wallet Details:")
    print(f"   Address: {wallet.address}")
    print(f"   Private Key: {wallet.get_private_key()}")
    print(f"   Public Key: {wallet.public_key}")
    
    # 测试连接到 devnet
    print(f"\n🔗 Testing connection to devnet...")
    
    client = SolMemeClient(
        network=Network.DEVNET,
        private_key=wallet.get_private_key()
    )
    
    try:
        await client.connect()
        wallet_info = await client.get_wallet_info()
        
        print(f"✅ Connection successful!")
        print(f"   SOL Balance: {wallet_info['balance_sol']:.6f} SOL")
        
        if wallet_info['balance_sol'] == 0:
            print(f"\n🚰 Use this address to get test SOL:")
            print(f"   {wallet.address}")
            print(f"\n🌐 Try these faucets:")
            print(f"   1. https://faucet.solana.com/")
            print(f"   2. https://faucet.quicknode.com/solana/devnet")
            print(f"   3. https://solfaucet.com/")
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
    
    finally:
        await client.close()
    
    # 保存钱包信息到文件（可选）
    with open('new_wallet_backup.txt', 'w') as f:
        f.write(f"Address: {wallet.address}\n")
        f.write(f"Private Key: {wallet.get_private_key()}\n")
        f.write(f"Public Key: {wallet.public_key}\n")
    
    print(f"\n💾 Wallet backup saved to: new_wallet_backup.txt")
    print("⚠️  Keep this file secure and never share the private key!")


if __name__ == "__main__":
    asyncio.run(main())