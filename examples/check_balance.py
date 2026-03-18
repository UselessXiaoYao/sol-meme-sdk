#!/usr/bin/env python3
"""
Check wallet balance on devnet
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from sol_meme_sdk import SolMemeClient, Network


def load_private_key_from_wallet():
    """从钱包文件动态加载私钥"""
    
    # 可能的钱包文件路径
    wallet_files = [
        "new_wallet.json",
        "../new_wallet.json",
        "wallet.json",
        "../wallet.json"
    ]
    
    for wallet_file in wallet_files:
        if Path(wallet_file).exists():
            try:
                with open(wallet_file, 'r') as f:
                    keypair_data = json.load(f)
                
                # 将私钥数组转换为base58字符串
                from solders.keypair import Keypair
                keypair = Keypair.from_bytes(bytes(keypair_data))
                private_key = str(keypair)
                
                print(f"✅ Loaded private key from: {wallet_file}")
                print(f"Wallet address: {keypair.pubkey()}")
                return private_key
                
            except Exception as e:
                print(f"❌ Error loading wallet from {wallet_file}: {e}")
                continue
    
    # 如果没有找到钱包文件，提示用户
    print("❌ No wallet file found. Please create a wallet first.")
    print("You can create a new wallet by running:")
    print("python3 create_new_wallet.py")
    print("\nOr manually specify a wallet file path.")
    return None


async def main():
    """Check wallet balance"""
    
    # 动态加载私钥
    private_key = load_private_key_from_wallet()
    if not private_key:
        return
    
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
            print("3. https://faucet.quicknode.com/solana/devnet")
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