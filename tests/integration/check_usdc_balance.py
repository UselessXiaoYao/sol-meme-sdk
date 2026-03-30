#!/usr/bin/env python3
"""
检查钱包USDC余额
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径到sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from solana.rpc.api import Client
from solders.pubkey import Pubkey
from solana.rpc.commitment import Confirmed

async def check_usdc_balance():
    """检查钱包USDC余额"""
    print("🔍 检查钱包USDC余额")
    print("=" * 40)
    
    # devnet USDC地址
    usdc_devnet = "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU"
    wallet_address = "Bw1cQdJx3R9L8VfauE45Fvnj5U3ELFjR9KPgtXhgmm6R"
    
    try:
        # 连接devnet
        devnet_rpc = "https://api.devnet.solana.com"
        client = Client(devnet_rpc)
        
        print(f"🔗 连接devnet: {devnet_rpc}")
        print(f"👛 钱包地址: {wallet_address}")
        print(f"💎 USDC地址: {usdc_devnet}")
        
        # 检查网络连接
        version = client.get_version()
        if not version.value:
            print("❌ 网络连接失败")
            return
        
        print(f"✅ 网络连接正常")
        
        # 将地址转换为Pubkey
        wallet_pubkey = Pubkey.from_string(wallet_address)
        usdc_pubkey = Pubkey.from_string(usdc_devnet)
        
        print("\n🔍 1. 检查USDC代币账户信息...")
        
        # 检查USDC账户存在性
        account_info = client.get_account_info(usdc_pubkey, commitment=Confirmed)
        if account_info.value:
            print(f"✅ USDC代币账户存在")
            print(f"   - 账户数据长度: {len(account_info.value.data)}")
            print(f"   - 所有者: {account_info.value.owner}")
        else:
            print("❌ USDC代币账户不存在")
            return
        
        print("\n🔍 2. 检查钱包的代币账户...")
        
        # 查询钱包的所有代币账户
        token_accounts = client.get_token_accounts_by_owner(
            wallet_pubkey
        )
        
        if token_accounts.value:
            print(f"✅ 查询到 {len(token_accounts.value)} 个代币账户")
            
            # 检查每个代币账户
            for i, account in enumerate(token_accounts.value):
                try:
                    account_info = account.account.data.parsed['info']
                    mint = account_info['mint']
                    balance = account_info['tokenAmount']['uiAmount']
                    
                    print(f"   {i+1}. 代币: {mint[:20]}...")
                    print(f"      余额: {balance}")
                    
                    if mint == usdc_devnet:
                        print(f"   🎯 找到USDC余额: {balance} USDC")
                        
                except Exception as e:
                    print(f"   {i+1}. 账户解析失败: {e}")
        else:
            print("ℹ️ 钱包中没有代币账户")
        
        print("\n🔍 3. 直接查询特定代币余额...")
        
        # 尝试直接查询USDC余额
        try:
            # 获取代币账户
            token_accounts_response = client.get_token_accounts_by_owner(
                wallet_pubkey,
                mint=usdc_pubkey
            )
            
            if token_accounts_response.value:
                print(f"✅ 找到USDC代币账户")
                for account in token_accounts_response.value:
                    account_info = account.account.data.parsed['info']
                    balance = account_info['tokenAmount']['uiAmount']
                    print(f"   USDC余额: {balance}")
            else:
                print("ℹ️ 没有找到USDC代币账户")
                
        except Exception as e:
            print(f"⚠️ 直接查询失败: {e}")
        
        print("\n🔍 4. 检查交易历史...")
        
        # 检查最近的交易历史
        try:
            signatures = client.get_signatures_for_address(
                wallet_pubkey,
                limit=5,
                commitment=Confirmed
            )
            
            if signatures.value:
                print(f"✅ 找到 {len(signatures.value)} 笔最近交易")
                for i, sig in enumerate(signatures.value[:3]):
                    print(f"   {i+1}. 交易: {sig.signature[:20]}...")
                    print(f"      状态: {sig.confirmation_status}")
                    print(f"      区块: {sig.slot}")
            else:
                print("ℹ️ 没有找到交易历史")
                
        except Exception as e:
            print(f"⚠️ 交易历史查询失败: {e}")
        
        print("\n" + "=" * 40)
        print("💡 总结:")
        print("   - USDC代币账户存在")
        print("   - 需要检查钱包是否确实收到了USDC")
        print("   - 可能需要等待区块确认")
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_usdc_balance())