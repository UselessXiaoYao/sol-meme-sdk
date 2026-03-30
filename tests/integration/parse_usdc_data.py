#!/usr/bin/env python3
"""
解析USDC账户原始数据
"""

from solana.rpc.api import Client
from solders.pubkey import Pubkey
from solana.rpc.types import TokenAccountOpts
import struct

def parse_spl_token_account(data: bytes):
    """
    手动解析SPL代币账户的165字节数据
    
    SPL代币账户结构（165字节）：
    - 0-32字节: mint地址（代币合约地址）
    - 32-64字节: owner地址（代币所有者）
    - 64-72字节: amount（8字节，小端序）
    - 72-73字节: delegate_option（1字节）
    - 73-105字节: delegate（如果有）
    - 105-113字节: state（8字节）
    - 113-121字节: is_native_option（8字节）
    - 121-129字节: is_native（8字节）
    - 129-161字节: delegated_amount（32字节）
    - 161-165字节: close_authority_option（4字节）
    """
    
    if len(data) != 165:
        raise ValueError(f"Expected 165 bytes, got {len(data)} bytes")
    
    # 解析各个字段
    mint = Pubkey(data[:32])
    owner = Pubkey(data[32:64])
    
    # 解析余额（8字节小端序）
    amount_bytes = data[64:72]
    amount = struct.unpack('<Q', amount_bytes)[0]  # 小端序无符号64位整数
    
    # 解析delegate选项
    delegate_option = data[72]
    if delegate_option == 1:
        delegate = Pubkey(data[73:105])
    else:
        delegate = None
    
    # 解析状态（已初始化/冻结等）
    state = data[105]
    
    # 解析是否为原生代币
    is_native_option = data[113]
    if is_native_option == 1:
        is_native = True
        native_amount = struct.unpack('<Q', data[121:129])[0]
    else:
        is_native = False
        native_amount = 0
    
    # 解析delegated_amount
    delegated_amount_bytes = data[129:161]
    delegated_amount = struct.unpack('<Q', delegated_amount_bytes[:8])[0]
    
    # 解析close_authority
    close_authority_option = data[161]
    if close_authority_option == 1:
        close_authority = Pubkey(data[162:165] + b'\x00' * 29)  # 补齐32字节
    else:
        close_authority = None
    
    return {
        'mint': str(mint),
        'owner': str(owner),
        'amount': amount,
        'amount_ui': amount / 10**6,  # USDC有6位小数
        'delegate': str(delegate) if delegate else None,
        'state': state,
        'is_native': is_native,
        'native_amount': native_amount,
        'delegated_amount': delegated_amount,
        'close_authority': str(close_authority) if close_authority else None
    }

def check_and_parse_usdc():
    """检查并解析USDC余额"""
    print("🔍 检查并解析USDC余额")
    print("=" * 50)
    
    wallet_address = "Bw1cQdJx3R9L8VfauE45Fvnj5U3ELFjR9KPgtXhgmm6R"
    usdc_devnet = "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU"
    
    client = Client("https://api.devnet.solana.com")
    
    try:
        wallet_pubkey = Pubkey.from_string(wallet_address)
        usdc_pubkey = Pubkey.from_string(usdc_devnet)
        
        print(f"👛 钱包地址: {wallet_address}")
        print(f"💎 USDC地址: {usdc_devnet}")
        
        # 1. 检查SOL余额
        print("\n🔍 1. 检查SOL余额...")
        balance_response = client.get_balance(wallet_pubkey)
        if balance_response.value:
            sol_balance = balance_response.value / 10**9
            print(f"💰 SOL余额: {sol_balance:.6f} SOL")
        
        # 2. 检查USDC账户
        print("\n🔍 2. 检查USDC代币账户...")
        usdc_accounts = client.get_token_accounts_by_owner(
            wallet_pubkey,
            TokenAccountOpts(mint=usdc_pubkey)
        )
        
        if usdc_accounts.value:
            print(f"✅ 找到 {len(usdc_accounts.value)} 个USDC账户")
            
            for i, account in enumerate(usdc_accounts.value):
                print(f"\n   账户 {i+1}:")
                print(f"    账户地址: {account.pubkey}")
                print(f"    数据长度: {len(account.account.data)} 字节")
                
                # 检查数据类型
                if isinstance(account.account.data, bytes):
                    print("    ⚠️ 数据格式: 原始字节 (需要手动解析)")
                    
                    try:
                        # 手动解析SPL代币账户数据
                        parsed_data = parse_spl_token_account(account.account.data)
                        
                        print(f"    ✅ 解析成功!")
                        print(f"    代币: {parsed_data['mint']}")
                        print(f"    所有者: {parsed_data['owner']}")
                        print(f"    原始余额: {parsed_data['amount']}")
                        print(f"    💰 USDC余额: {parsed_data['amount_ui']} USDC")
                        print(f"    状态: {parsed_data['state']}")
                        
                        if parsed_data['amount_ui'] > 0:
                            print(f"    🎉 USDC已到账: {parsed_data['amount_ui']} USDC")
                        else:
                            print("    ℹ️ USDC余额为0")
                            
                    except Exception as e:
                        print(f"    ❌ 解析失败: {e}")
                        print(f"    原始数据: {account.account.data.hex()}")
                        
                elif hasattr(account.account.data, 'parsed'):
                    print("    ✅ 数据格式: 已解析JSON")
                    account_info = account.account.data.parsed['info']
                    balance = account_info['tokenAmount']['uiAmount']
                    print(f"    💰 USDC余额: {balance} USDC")
                    
                else:
                    print(f"    ⚠️ 未知数据格式: {type(account.account.data)}")
        else:
            print("❌ 没有找到USDC代币账户")
        
        print("\n" + "=" * 50)
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_and_parse_usdc()