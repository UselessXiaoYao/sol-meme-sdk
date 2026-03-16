#!/usr/bin/env python3
"""
Validate wallet address and create new wallet if needed
"""

import asyncio
from sol_meme_sdk import SolMemeClient, Network, Wallet
import base58


async def validate_address(address: str):
    """Validate if a Solana address is valid"""
    try:
        # 尝试解码 base58 地址
        decoded = base58.b58decode(address)
        print(f"✅ Address {address} is valid")
        print(f"   Length: {len(decoded)} bytes")
        return True
    except Exception as e:
        print(f"❌ Address {address} is invalid: {e}")
        return False


async def main():
    """Validate and create wallets"""
    
    # 验证现有地址
    existing_address = "GFuF8b2o4ef9x7YWjKWNyaSq5V5cJFHMXU9YQwQX1nWe"
    print("🔍 Validating existing wallet address...")
    is_valid = await validate_address(existing_address)
    
    if not is_valid:
        print("\n🔄 Creating a new wallet...")
        
        # 创建新钱包
        wallet = Wallet()
        new_address = wallet.address
        
        print(f"✅ New wallet created:")
        print(f"   Address: {new_address}")
        print(f"   Private Key: {wallet.private_key}")
        
        # 验证新地址
        await validate_address(new_address)
        
        # 测试连接到 devnet
        client = SolMemeClient(
            network=Network.DEVNET,
            private_key=wallet.private_key
        )
        
        await client.connect()
        wallet_info = await client.get_wallet_info()
        print(f"\n📊 Balance check on devnet:")
        print(f"   SOL Balance: {wallet_info['balance_sol']:.6f} SOL")
        
        await client.close()
        
        return new_address
    
    return existing_address


if __name__ == "__main__":
    address = asyncio.run(main())
    print(f"\n🎯 Use this address for faucet: {address}")