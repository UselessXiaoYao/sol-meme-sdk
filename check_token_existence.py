#!/usr/bin/env python3
"""
检查GMGN币对的真实代币地址
"""

import asyncio
from sol_meme_sdk import RaydiumClient
from solana.rpc.commitment import Confirmed
from solders.pubkey import Pubkey


async def check_real_token():
    """检查真实代币地址"""
    
    print("🔍 检查GMGN币对真实代币")
    print("=" * 60)
    
    client = RaydiumClient()
    
    try:
        await client.connect()
        
        # 用户提供的地址
        pool_address = "EcSrKwco6iun9xDShsMJUFGTc9kiCjkZ6UJGJ8Gr2vQV"
        token_address = "8EUmqJyKSjgb4Mw25fDUGxxA7dWHGncXFJCD32ipT5m6"
        developer_address = "ELvJ96YimxmEM7aEJhvQ8PJKicW1vRbPQEJpnZwN4cMS"
        funding_address = "4mNpGfTfcqfkfHgZnrC1hHrbnyWJMVa3EmjN3WTCF6pN"
        
        print("📋 地址列表:")
        print(f"   币对地址: {pool_address}")
        print(f"   代币地址: {token_address}")
        print(f"   开发者地址: {developer_address}")
        print(f"   资金来源地址: {funding_address}")
        
        print("\n🔍 检查代币账户:")
        print("-" * 40)
        
        # 检查代币账户
        token_pubkey = Pubkey.from_string(token_address)
        token_account = await client.client.get_account_info(token_pubkey, commitment=Confirmed)
        
        if token_account.value:
            print(f"✅ 代币账户存在: {token_address}")
            print(f"   数据长度: {len(token_account.value.data)} bytes")
            print(f"   所有者: {token_account.value.owner}")
            
            # 解析代币数据
            if len(token_account.value.data) >= 82:
                data = token_account.value.data
                print(f"   代币数据: {data[:50].hex()}...")
        else:
            print(f"❌ 代币账户不存在: {token_address}")
        
        print("\n🔍 检查开发者账户:")
        print("-" * 40)
        
        developer_pubkey = Pubkey.from_string(developer_address)
        developer_account = await client.client.get_account_info(developer_pubkey, commitment=Confirmed)
        
        if developer_account.value:
            print(f"✅ 开发者账户存在: {developer_address}")
            print(f"   数据长度: {len(developer_account.value.data)} bytes")
            print(f"   所有者: {developer_account.value.owner}")
        else:
            print(f"❌ 开发者账户不存在: {developer_address}")
        
        print("\n🔍 检查资金来源账户:")
        print("-" * 40)
        
        funding_pubkey = Pubkey.from_string(funding_address)
        funding_account = await client.client.get_account_info(funding_pubkey, commitment=Confirmed)
        
        if funding_account.value:
            print(f"✅ 资金来源账户存在: {funding_address}")
            print(f"   数据长度: {len(funding_account.value.data)} bytes")
            print(f"   所有者: {funding_account.value.owner}")
        else:
            print(f"❌ 资金来源账户不存在: {funding_address}")
        
        print("\n🎯 重新分析池结构:")
        print("-" * 40)
        
        # 重新获取池信息
        pool_info = await client.get_pool_info(pool_address)
        
        print(f"池地址: {pool_info['pool_address']}")
        print(f"基础代币: {pool_info['base_mint']}")
        print(f"报价代币: {pool_info['quote_mint']}")
        print(f"LP代币: {pool_info['lp_mint']}")
        
        # 检查是否匹配
        if pool_info['base_mint'] == token_address:
            print("✅ 基础代币匹配提供的代币地址")
        elif pool_info['quote_mint'] == token_address:
            print("✅ 报价代币匹配提供的代币地址")
        else:
            print("❌ 池中的代币与提供的地址不匹配")
        
        if pool_info['lp_mint'] == developer_address:
            print("✅ LP代币匹配开发者地址")
        else:
            print("❌ LP代币与开发者地址不匹配")
        
        print("\n💡 分析结论:")
        print("-" * 40)
        
        # 基于新信息重新分析
        if pool_info['base_mint'] == "11111111111111111111111111111111":
            print("🔍 池结构分析:")
            print("   - 基础代币是系统ID，说明这是SOL交易对")
            print("   - 报价代币应该是真实代币地址")
            print("   - LP代币是开发者地址")
            
            # 检查报价代币是否是真实代币
            quote_mint_pubkey = Pubkey.from_string(pool_info['quote_mint'])
            quote_account = await client.client.get_account_info(quote_mint_pubkey, commitment=Confirmed)
            
            if quote_account.value:
                print(f"✅ 报价代币是真实代币: {pool_info['quote_mint']}")
            else:
                print(f"❌ 报价代币账户不存在")
        
        print("\n🎉 检查完成！")
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        
    finally:
        await client.close()


async def main():
    """主检查函数"""
    
    await check_real_token()


if __name__ == "__main__":
    asyncio.run(main())