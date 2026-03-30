#!/usr/bin/env python3
"""
调试钱包代币余额查询
"""

from solana.rpc.api import Client
from solders.pubkey import Pubkey
from solana.rpc.types import TokenAccountOpts
from solana.rpc.commitment import Confirmed
import struct

def debug_token_balances():
    """调试钱包代币余额查询"""
    print("🔍 调试钱包代币余额查询")
    print("=" * 50)
    
    wallet_address = "Bw1cQdJx3R9L8VfauE45Fvnj5U3ELFjR9KPgtXhgmm6R"
    usdc_devnet = "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU"
    
    client = Client("https://api.devnet.solana.com")
    
    try:
        wallet_pubkey = Pubkey.from_string(wallet_address)
        usdc_pubkey = Pubkey.from_string(usdc_devnet)
        
        print(f"👛 钱包地址: {wallet_address}")
        print(f"💎 USDC地址: {usdc_devnet}")
        
        # 1. 使用不同的TokenAccountOpts参数测试
        print("\n🔍 1. 测试TokenAccountOpts参数...")
        
        # 方法1: 空参数
        print("   🔍 方法1: TokenAccountOpts()")
        token_accounts_1 = client.get_token_accounts_by_owner(
            wallet_pubkey,
            TokenAccountOpts(),
            commitment=Confirmed
        )
        print(f"     账户数量: {len(token_accounts_1.value) if token_accounts_1.value else 0}")
        
        # 方法2: 指定mint
        print("   🔍 方法2: TokenAccountOpts(mint=usdc_pubkey)")
        token_accounts_2 = client.get_token_accounts_by_owner(
            wallet_pubkey,
            TokenAccountOpts(mint=usdc_pubkey),
            commitment=Confirmed
        )
        print(f"     账户数量: {len(token_accounts_2.value) if token_accounts_2.value else 0}")
        
        # 方法3: 指定SPL程序ID
        print("   🔍 方法3: TokenAccountOpts(program_id=SPL_TOKEN_PROGRAM_ID)")
        spl_program_id = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
        token_accounts_3 = client.get_token_accounts_by_owner(
            wallet_pubkey,
            TokenAccountOpts(program_id=spl_program_id),
            commitment=Confirmed
        )
        print(f"     账户数量: {len(token_accounts_3.value) if token_accounts_3.value else 0}")
        
        # 2. 检查具体账户数据
        print("\n🔍 2. 检查具体账户数据...")
        
        # 使用方法2的结果（指定mint）
        if token_accounts_2.value:
            print("✅ 找到USDC代币账户")
            
            for i, account in enumerate(token_accounts_2.value):
                print(f"\n   账户 {i+1}:")
                print(f"    账户地址: {account.pubkey}")
                print(f"    数据长度: {len(account.account.data)} 字节")
                
                # 检查数据类型
                if isinstance(account.account.data, bytes):
                    print("    ⚠️ 数据格式: 原始字节 (需要手动解析)")
                    
                    try:
                        # 手动解析SPL代币账户数据
                        data = account.account.data
                        if len(data) == 165:
                            # 解析mint地址（前32字节）
                            mint_pubkey = Pubkey(data[:32])
                            mint = str(mint_pubkey)
                            
                            # 解析余额（64-72字节，8字节小端序）
                            amount_bytes = data[64:72]
                            balance_raw = struct.unpack('<Q', amount_bytes)[0]
                            
                            # 转换为UI金额（假设6位小数，USDC标准）
                            balance = balance_raw / 10**6
                            
                            print(f"    ✅ 解析成功!")
                            print(f"    代币: {mint}")
                            print(f"    原始余额: {balance_raw}")
                            print(f"    💰 USDC余额: {balance} USDC")
                            
                            if balance > 0:
                                print(f"    🎉 USDC已到账: {balance} USDC")
                            else:
                                print("    ℹ️ USDC余额为0")
                                
                        else:
                            print(f"    ❌ 非标准数据长度: {len(data)} 字节")
                            
                    except Exception as e:
                        print(f"    ❌ 解析失败: {e}")
                        
                elif hasattr(account.account.data, 'parsed'):
                    print("    ✅ 数据格式: 已解析JSON")
                    account_info = account.account.data.parsed['info']
                    balance = account_info['tokenAmount']['uiAmount']
                    print(f"    💰 USDC余额: {balance} USDC")
                    
                else:
                    print(f"    ⚠️ 未知数据格式: {type(account.account.data)}")
        else:
            print("❌ 没有找到USDC代币账户")
            print("\n📝 可能原因:")
            print("   - USDC确实没有到账")
            print("   - API调用参数不正确")
            print("   - 网络问题")
        
        # 3. 检查所有代币账户
        print("\n🔍 3. 检查所有代币账户...")
        
        if token_accounts_1.value:
            print(f"✅ 找到 {len(token_accounts_1.value)} 个代币账户")
            
            for i, account in enumerate(token_accounts_1.value):
                print(f"\n   账户 {i+1}:")
                print(f"    账户地址: {account.pubkey}")
                print(f"    数据长度: {len(account.account.data)} 字节")
                
                # 检查数据类型
                if isinstance(account.account.data, bytes):
                    print("    ⚠️ 数据格式: 原始字节")
                    
                    try:
                        data = account.account.data
                        if len(data) == 165:
                            # 解析mint地址
                            mint_pubkey = Pubkey(data[:32])
                            mint = str(mint_pubkey)
                            
                            # 解析余额
                            amount_bytes = data[64:72]
                            balance_raw = struct.unpack('<Q', amount_bytes)[0]
                            balance = balance_raw / 10**6
                            
                            print(f"    代币: {mint}")
                            print(f"    余额: {balance}")
                            
                            if mint == usdc_devnet:
                                print(f"    🎯 这是USDC账户!")
                                
                        else:
                            print(f"    非标准数据: {len(data)} 字节")
                            
                    except Exception as e:
                        print(f"    解析失败: {e}")
                        
                elif hasattr(account.account.data, 'parsed'):
                    print("    ✅ 数据格式: 已解析JSON")
                    account_info = account.account.data.parsed['info']
                    mint = account_info['mint']
                    balance = account_info['tokenAmount']['uiAmount']
                    print(f"    代币: {mint}")
                    print(f"    余额: {balance}")
                    
                else:
                    print(f"    ⚠️ 未知数据格式: {type(account.account.data)}")
        else:
            print("ℹ️ 钱包中没有代币账户")
        
        print("\n" + "=" * 50)
        
    except Exception as e:
        print(f"❌ 调试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_token_balances()