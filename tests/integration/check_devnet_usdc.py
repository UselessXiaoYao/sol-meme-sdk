#!/usr/bin/env python3
"""
检查devnet USDC地址有效性
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径到sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from solana.rpc.api import Client
from sol_meme_sdk.wallet import Wallet

async def check_devnet_usdc():
    """检查devnet USDC地址"""
    print("🔍 检查devnet USDC地址有效性")
    print("=" * 40)
    
    # devnet USDC地址
    usdc_devnet = "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU"
    
    try:
        # 连接devnet
        devnet_rpc = "https://api.devnet.solana.com"
        client = Client(devnet_rpc)
        
        # 检查网络连接
        version = client.get_version()
        if not version.value:
            print("❌ 网络连接失败")
            return
        
        print(f"✅ 网络连接正常")
        print(f"🔍 检查USDC地址: {usdc_devnet}")
        
        # 加载钱包
        wallet_file = project_root.parent / "new_wallet.json"
        if wallet_file.exists():
            wallet = Wallet.from_json_file(str(wallet_file))
            print(f"✅ 钱包加载成功: {wallet.address}")
            
            # 检查USDC余额
            try:
                token_balances = wallet.get_token_balances(client)
                if usdc_devnet in token_balances:
                    balance = token_balances[usdc_devnet]
                    print(f"💰 USDC余额: {balance}")
                else:
                    print("ℹ️ 钱包中没有USDC余额")
                    
                # 检查代币信息
                print("\n🔍 检查代币信息...")
                account_info = client.get_account_info(usdc_devnet)
                if account_info.value:
                    print(f"✅ 代币账户存在")
                    print(f"   - 账户数据长度: {len(account_info.value.data)}")
                else:
                    print("❌ 代币账户不存在或无法访问")
                    
            except Exception as e:
                print(f"⚠️ 代币查询失败: {e}")
        else:
            print("❌ 钱包文件不存在")
            
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_devnet_usdc())