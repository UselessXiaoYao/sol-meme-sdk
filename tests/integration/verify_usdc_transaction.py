#!/usr/bin/env python3
"""
验证USDC交易是否到账
"""

import asyncio
from solana.rpc.api import Client
from solders.pubkey import Pubkey

def verify_usdc_transaction():
    """验证USDC交易是否到账"""
    print("🔍 验证USDC交易是否到账")
    print("=" * 50)
    
    # 交易信息
    tx_hash = "5egv86LMgCDjy6B4tHZ26EcQ78d8bdSeTwRxypeUHYDic25m2KmQmiTc27xd99nBJa7ZqkhqzWjV7gk3SuAEyxMQ"
    wallet_address = "Bw1cQdJx3R9L8VfauE45Fvnj5U3ELFjR9KPgtXhgmm6R"
    usdc_devnet = "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU"
    
    client = Client("https://api.devnet.solana.com")
    
    try:
        print(f"🔗 检查交易: {tx_hash[:20]}...")
        
        # 1. 检查交易详情
        print("\n🔍 1. 检查交易详情...")
        transaction = client.get_transaction(tx_hash)
        
        if transaction.value:
            print("✅ 交易存在")
            tx_info = transaction.value
            
            # 检查交易状态
            if hasattr(tx_info, 'meta') and tx_info.meta:
                print(f"   交易状态: {tx_info.meta.err}")
                print(f"   计算单元: {tx_info.meta.compute_units_consumed}")
                
                # 检查交易日志
                if hasattr(tx_info, 'transaction') and hasattr(tx_info.transaction, 'message'):
                    print(f"   指令数量: {len(tx_info.transaction.message.instructions)}")
        else:
            print("❌ 交易不存在或无法访问")
            
        # 2. 检查钱包的代币账户
        print("\n🔍 2. 检查钱包的代币账户...")
        wallet_pubkey = Pubkey.from_string(wallet_address)
        
        # 检查所有代币账户
        from solana.rpc.types import TokenAccountOpts
        token_accounts = client.get_token_accounts_by_owner(
            wallet_pubkey,
            TokenAccountOpts(mint=None)
        )
        
        if token_accounts.value:
            print(f"✅ 找到 {len(token_accounts.value)} 个代币账户")
            
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
            
        # 3. 检查特定USDC账户
        print("\n🔍 3. 检查特定USDC账户...")
        usdc_pubkey = Pubkey.from_string(usdc_devnet)
        
        # 检查是否有USDC代币账户
        usdc_accounts = client.get_token_accounts_by_owner(
            wallet_pubkey,
            TokenAccountOpts(mint=usdc_pubkey)
        )
        
        if usdc_accounts.value:
            print(f"✅ 找到USDC代币账户")
            for account in usdc_accounts.value:
                account_info = account.account.data.parsed['info']
                balance = account_info['tokenAmount']['uiAmount']
                print(f"   USDC余额: {balance}")
        else:
            print("ℹ️ 没有找到USDC代币账户")
            
        # 4. 检查交易签名
        print("\n🔍 4. 检查交易签名状态...")
        signatures = client.get_signatures_for_address(
            wallet_pubkey,
            limit=10
        )
        
        if signatures.value:
            print(f"✅ 找到 {len(signatures.value)} 笔最近交易")
            
            # 查找特定的交易
            found = False
            for sig in signatures.value:
                if tx_hash in sig.signature:
                    print(f"   🎯 找到目标交易")
                    print(f"      签名: {sig.signature[:20]}...")
                    print(f"      状态: {sig.confirmation_status}")
                    print(f"      区块: {sig.slot}")
                    found = True
                    break
                    
            if not found:
                print("   ⚠️ 目标交易不在最近10笔交易中")
                
        # 5. 检查区块确认状态
        print("\n🔍 5. 检查区块确认状态...")
        try:
            # 获取最新区块高度
            slot = client.get_slot()
            if slot.value:
                print(f"   当前区块高度: {slot.value}")
                
                # 检查交易所在的区块
                if signatures.value:
                    for sig in signatures.value:
                        if tx_hash in sig.signature:
                            print(f"   交易区块: {sig.slot}")
                            print(f"   确认数: {slot.value - sig.slot if slot.value > sig.slot else '待确认'}")
                            break
                            
        except Exception as e:
            print(f"   区块确认检查失败: {e}")
            
        print("\n" + "=" * 50)
        print("💡 总结:")
        print("   - 如果USDC余额为0，可能有以下原因:")
        print("     1. 交易尚未确认")
        print("     2. 交易失败")
        print("     3. 代币账户尚未创建")
        print("     4. 网络延迟或API限制")
        print("\n   🔄 建议等待几分钟后重新检查")
        
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_usdc_transaction()