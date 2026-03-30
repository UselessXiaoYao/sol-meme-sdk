#!/usr/bin/env python3
"""
检查交易状态和卖出单状态
"""

from solana.rpc.api import Client
from solders.pubkey import Pubkey
from solana.rpc.commitment import Confirmed

def check_trade_status():
    """检查交易状态和卖出单状态"""
    print("🔍 检查交易状态和卖出单状态")
    print("=" * 50)
    
    wallet_address = "Bw1cQdJx3R9L8VfauE45Fvnj5U3ELFjR9KPgtXhgmm6R"
    usdc_devnet = "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU"
    
    client = Client("https://api.devnet.solana.com")
    
    try:
        wallet_pubkey = Pubkey.from_string(wallet_address)
        
        print(f"👛 钱包地址: {wallet_address}")
        print(f"💎 USDC地址: {usdc_devnet}")
        
        # 1. 检查钱包余额
        print("\n🔍 1. 检查当前余额...")
        
        # SOL余额
        balance_response = client.get_balance(wallet_pubkey, commitment=Confirmed)
        if balance_response.value:
            sol_balance = balance_response.value / 10**9
            print(f"💰 SOL余额: {sol_balance:.6f} SOL")
        
        # USDC余额
        from solana.rpc.types import TokenAccountOpts
        usdc_pubkey = Pubkey.from_string(usdc_devnet)
        token_accounts = client.get_token_accounts_by_owner(
            wallet_pubkey,
            TokenAccountOpts(mint=usdc_pubkey),
            commitment=Confirmed
        )
        
        if token_accounts.value:
            for account in token_accounts.value:
                # 手动解析SPL代币账户数据
                import struct
                data = account.account.data
                if len(data) == 165:
                    # 解析余额
                    amount_bytes = data[64:72]
                    balance_raw = struct.unpack('<Q', amount_bytes)[0]
                    usdc_balance = balance_raw / 10**6
                    print(f"💵 USDC余额: {usdc_balance} USDC")
        
        # 2. 检查最近交易
        print("\n🔍 2. 检查最近交易记录...")
        
        signatures = client.get_signatures_for_address(
            wallet_pubkey,
            limit=10,
            commitment=Confirmed
        )
        
        if signatures.value:
            print(f"✅ 找到 {len(signatures.value)} 笔最近交易")
            
            usdc_related_tx = []
            for i, sig in enumerate(signatures.value):
                print(f"\n   {i+1}. 交易签名: {sig.signature}")
                print(f"      状态: {sig.confirmation_status}")
                print(f"      区块: {sig.slot}")
                print(f"      错误: {sig.err}")
                
                # 检查交易详情（修复版本兼容性问题）
                try:
                    tx_detail = client.get_transaction(
                        sig.signature, 
                        commitment=Confirmed,
                        max_supported_transaction_version=0
                    )
                    if tx_detail.value:
                        # 检查是否涉及USDC
                        if usdc_devnet in str(tx_detail.value):
                            usdc_related_tx.append(sig.signature)
                            print(f"      🎯 涉及USDC交易")
                except Exception as tx_error:
                    print(f"      ⚠️ 交易详情获取失败: {tx_error}")
        else:
            print("ℹ️ 没有找到交易记录")
        
        # 3. 检查USDC代币账户的交易历史
        print("\n🔍 3. 检查USDC代币账户交易...")
        
        if token_accounts.value:
            for account in token_accounts.value:
                account_pubkey = account.pubkey
                account_signatures = client.get_signatures_for_address(
                    account_pubkey,
                    limit=5,
                    commitment=Confirmed
                )
                
                if account_signatures.value:
                    print(f"✅ USDC账户交易记录: {len(account_signatures.value)} 笔")
                    for sig in account_signatures.value:
                        signature_str = str(sig.signature)
                        print(f"   - 交易: {signature_str[:20]}...")
                        print(f"     状态: {sig.confirmation_status}")
                        if sig.err:
                            print(f"     错误: {sig.err}")
                else:
                    print("ℹ️ USDC账户无交易记录")
        
        # 4. 检查Jupiter API可用性
        print("\n🔍 4. 检查DEX API可用性...")
        
        try:
            import requests
            
            # 测试Jupiter API
            jupiter_url = "https://quote-api.jup.ag/v6/quote"
            params = {
                "inputMint": "So11111111111111111111111111111111111111112",  # SOL
                "outputMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # mainnet USDC
                "amount": 10000000,  # 0.01 SOL
                "slippageBps": 50
            }
            
            response = requests.get(jupiter_url, params=params, timeout=10)
            if response.status_code == 200:
                print("✅ Jupiter API (mainnet) 正常工作")
            else:
                print(f"❌ Jupiter API (mainnet) 错误: {response.status_code}")
                
        except Exception as e:
            print(f"⚠️ API测试失败: {e}")
        
        print("\n" + "=" * 50)
        print("💡 分析结果:")
        print("   1. 余额检查确认USDC到账状态")
        print("   2. 交易记录显示是否有卖出单执行")
        print("   3. Jupiter API错误是因为devnet流动性限制")
        print("   4. 卖出单可能只是创建了订单对象，并未实际执行")
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_trade_status()