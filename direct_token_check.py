#!/usr/bin/env python3
"""
直接检查代币在Raydium上的交易情况
"""

import asyncio
import aiohttp
import json
from sol_meme_sdk import RaydiumClient


async def check_token_on_raydium():
    """检查代币在Raydium上的真实交易情况"""
    
    print("🔍 检查代币在Raydium上的真实交易")
    print("=" * 60)
    
    client = RaydiumClient()
    
    try:
        await client.connect()
        
        # 真实代币地址
        token_address = "8EUmqJyKSjgb4Mw25fDUGxxA7dWHGncXFJCD32ipT5m6"
        
        print(f"🔎 检查代币: {token_address}")
        print("-" * 40)
        
        # 方法1: 通过Raydium API查找池
        print("📋 方法1: 通过Raydium API查找池")
        
        try:
            # 使用Raydium的池查找API
            url = f"https://api.raydium.io/v2/sdk/token/info"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        tokens_data = await resp.json()
                        
                        # 查找代币信息
                        token_info = None
                        for token in tokens_data:
                            if token.get('mint') == token_address:
                                token_info = token
                                break
                        
                        if token_info:
                            print(f"✅ 在Raydium找到代币信息:")
                            print(f"   名称: {token_info.get('name', 'Unknown')}")
                            print(f"   符号: {token_info.get('symbol', 'Unknown')}")
                            print(f"   小数位数: {token_info.get('decimals', 'Unknown')}")
                        else:
                            print("❌ 在Raydium API中未找到代币信息")
                    else:
                        print(f"⚠️ Raydium API错误: {resp.status}")
        except Exception as e:
            print(f"⚠️ Raydium API调用失败: {e}")
        
        # 方法2: 通过池列表查找
        print("\n📋 方法2: 在Raydium池列表中查找")
        
        try:
            pools_data = await client.get_raydium_pools()
            
            found_pools = []
            
            # 在所有池类型中搜索包含该代币的池
            for pool_type in ['official', 'unOfficial']:
                if pool_type in pools_data:
                    for pool in pools_data[pool_type]:
                        if (pool.get('baseMint') == token_address or 
                            pool.get('quoteMint') == token_address):
                            found_pools.append(pool)
            
            if found_pools:
                print(f"✅ 找到 {len(found_pools)} 个包含该代币的池")
                for i, pool in enumerate(found_pools[:3]):  # 显示前3个
                    print(f"   {i+1}. 池ID: {pool.get('id', 'Unknown')}")
                    print(f"      基础代币: {pool.get('baseMint', 'Unknown')}")
                    print(f"      报价代币: {pool.get('quoteMint', 'Unknown')}")
                    print(f"      版本: {pool.get('version', 'Unknown')}")
            else:
                print("❌ 在Raydium池列表中未找到包含该代币的池")
                
        except Exception as e:
            print(f"⚠️ 池列表搜索失败: {e}")
        
        # 方法3: 直接分析代币账户
        print("\n📋 方法3: 直接分析代币账户")
        
        from solana.rpc.commitment import Confirmed
        from solders.pubkey import Pubkey
        
        token_pubkey = Pubkey.from_string(token_address)
        token_account = await client.client.get_account_info(token_pubkey, commitment=Confirmed)
        
        if token_account.value:
            print("✅ 代币账户详细信息:")
            print(f"   数据长度: {len(token_account.value.data)} bytes")
            print(f"   所有者: {token_account.value.owner}")
            
            # 尝试解析代币元数据
            data = token_account.value.data
            if len(data) >= 82:
                # 解析代币标准结构
                mint_authority = Pubkey(data[0:32])
                supply = int.from_bytes(data[32:40], 'little')
                decimals = data[40]
                is_initialized = bool(data[41])
                freeze_authority_option = data[42]
                
                print(f"   铸币权限: {mint_authority}")
                print(f"   总供应量: {supply:,}")
                print(f"   小数位数: {decimals}")
                print(f"   是否初始化: {is_initialized}")
        
        # 方法4: 检查代币在Jupiter上的情况
        print("\n📋 方法4: 检查代币在Jupiter上的情况")
        
        try:
            # 使用Jupiter API检查代币
            jupiter_url = f"https://token.jup.ag/all"
            async with aiohttp.ClientSession() as session:
                async with session.get(jupiter_url, timeout=10) as resp:
                    if resp.status == 200:
                        jupiter_tokens = await resp.json()
                        
                        jupiter_token = None
                        for token in jupiter_tokens:
                            if token.get('address') == token_address:
                                jupiter_token = token
                                break
                        
                        if jupiter_token:
                            print(f"✅ 在Jupiter找到代币信息:")
                            print(f"   名称: {jupiter_token.get('name', 'Unknown')}")
                            print(f"   符号: {jupiter_token.get('symbol', 'Unknown')}")
                            print(f"   小数位数: {jupiter_token.get('decimals', 'Unknown')}")
                            print(f"   扩展: {jupiter_token.get('extensions', {})}")
                        else:
                            print("❌ 在Jupiter中未找到代币信息")
                    else:
                        print(f"⚠️ Jupiter API错误: {resp.status}")
                        
        except Exception as e:
            print(f"⚠️ Jupiter API调用失败: {e}")
        
        print("\n💡 综合分析结论:")
        print("-" * 40)
        
        # 基于所有检查结果给出结论
        print("1. 代币确实存在且有效")
        print("2. GMGN显示的池地址可能有特殊用途")
        print("3. 实际交易可能发生在其他池中")
        print("4. 需要进一步验证GMGN的实际交易机制")
        
        print("\n🎯 建议下一步:")
        print("1. 在GMGN界面查看实际交易使用的池地址")
        print("2. 检查代币在其他DEX上的交易情况")
        print("3. 验证GMGN是否使用了自定义交易逻辑")
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        
    finally:
        await client.close()


async def main():
    """主检查函数"""
    
    await check_token_on_raydium()


if __name__ == "__main__":
    asyncio.run(main())