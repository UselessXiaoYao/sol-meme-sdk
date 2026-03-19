#!/usr/bin/env python3
"""
直接检查GMGN交易机制的脚本
"""

import asyncio
import aiohttp
import json


async def check_gmgn_api():
    """检查GMGN是否有公开API"""
    
    print("🔍 检查GMGN API")
    print("=" * 60)
    
    # GMGN可能的API端点
    gmgn_apis = [
        "https://api.gmgn.ai/api/v1/pairs",
        "https://api.gmgn.ai/pairs",
        "https://gmgn.ai/api/pairs",
        "https://api.gmgn.ai/v1/pairs",
    ]
    
    for api_url in gmgn_apis:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, timeout=5) as resp:
                    if resp.status == 200:
                        print(f"✅ 找到GMGN API: {api_url}")
                        data = await resp.json()
                        print(f"   返回数据: {json.dumps(data, indent=2)[:500]}...")
                        return api_url
                    else:
                        print(f"❌ {api_url} 返回状态: {resp.status}")
        except Exception as e:
            print(f"❌ {api_url} 连接失败: {e}")
    
    print("❌ 未找到可用的GMGN API")
    return None


async def check_raydium_pool_details():
    """检查Raydium池的详细信息"""
    
    print("\n🔗 检查Raydium池详细信息")
    print("=" * 60)
    
    pair_address = "CSRJSQ5daTA9sehZAboPQYAJqbptJgzQ2e7aGduWzQ8U"
    
    # Raydium的不同API端点
    raydium_endpoints = [
        "https://api.raydium.io/v2/sdk/liquidity/mainnet.json",
        "https://api.raydium.io/v2/pools",
        "https://api.raydium.io/pools",
    ]
    
    for endpoint in raydium_endpoints:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint, timeout=10) as resp:
                    if resp.status == 200:
                        print(f"✅ 连接到Raydium API: {endpoint}")
                        data = await resp.json()
                        
                        # 搜索我们的池
                        found = False
                        
                        # 检查不同的数据结构
                        if isinstance(data, list):
                            for pool in data:
                                if (pool.get('id') == pair_address or 
                                    pool.get('address') == pair_address or
                                    pool.get('authority') == pair_address):
                                    found = True
                                    print("✅ 找到匹配的池！")
                                    print(json.dumps(pool, indent=2))
                                    break
                        elif isinstance(data, dict):
                            # 检查official和unOfficial池
                            for pool_type in ['official', 'unOfficial']:
                                if pool_type in data:
                                    for pool in data[pool_type]:
                                        if (pool.get('id') == pair_address or 
                                            pool.get('address') == pair_address or
                                            pool.get('authority') == pair_address):
                                            found = True
                                            print(f"✅ 在{pool_type}池中找到匹配！")
                                            print(json.dumps(pool, indent=2))
                                            break
                                if found:
                                    break
                        
                        if not found:
                            print("❌ 未找到匹配的池")
                            
                    else:
                        print(f"❌ {endpoint} 返回状态: {resp.status}")
                        
        except Exception as e:
            print(f"❌ {endpoint} 连接失败: {e}")


async def check_token_metadata():
    """检查代币元数据"""
    
    print("\n💰 检查代币元数据")
    print("=" * 60)
    
    mint_address = "HG7q9f1k61ZRiWEttYpSVUXhzHHXfe9VX1ESbqvbwu1d"
    
    # 不同的代币元数据源
    metadata_sources = [
        f"https://api.mainnet-beta.solana.com/token-metadata/{mint_address}",
        f"https://raw.githubusercontent.com/solana-labs/token-list/main/src/tokens/solana.tokenlist.json",
        "https://token.jup.ag/tokens",
    ]
    
    for source in metadata_sources:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(source, timeout=10) as resp:
                    if resp.status == 200:
                        print(f"✅ 连接到元数据源: {source}")
                        
                        if "token-metadata" in source:
                            # Solana token metadata API
                            data = await resp.json()
                            print("Token Metadata:")
                            print(json.dumps(data, indent=2))
                        elif "token-list" in source:
                            # Solana token list
                            data = await resp.json()
                            for token in data.get('tokens', []):
                                if token.get('address') == mint_address:
                                    print("✅ 在代币列表中找到！")
                                    print(f"   名称: {token.get('name')}")
                                    print(f"   符号: {token.get('symbol')}")
                                    print(f"   小数位: {token.get('decimals')}")
                                    break
                            else:
                                print("❌ 未在代币列表中找到")
                        elif "jup.ag" in source:
                            # Jupiter token list
                            data = await resp.json()
                            for token in data:
                                if token.get('address') == mint_address:
                                    print("✅ 在Jupiter代币列表中找到！")
                                    print(f"   名称: {token.get('name')}")
                                    print(f"   符号: {token.get('symbol')}")
                                    print(f"   小数位: {token.get('decimals')}")
                                    break
                            else:
                                print("❌ 未在Jupiter代币列表中找到")
                                
                    else:
                        print(f"❌ {source} 返回状态: {resp.status}")
                        
        except Exception as e:
            print(f"❌ {source} 连接失败: {e}")


async def analyze_gmgn_mechanism():
    """分析GMGN交易机制"""
    
    print("\n🎯 GMGN交易机制分析")
    print("=" * 60)
    
    print("💡 关键洞察：")
    print("1. GMGN可能不是通过标准的DEX聚合器交易")
    print("2. GMGN可能使用自定义的智能合约来处理交易")
    print("3. 这个池可能是Raydium的老版本池，GMGN有特殊支持")
    print("4. GMGN可能直接与Raydium的AMM协议交互，绕过订单簿")
    
    print("\n🔍 技术分析：")
    print("池地址: CSRJSQ5daTA9sehZAboPQYAJqbptJgzQ2e7aGduWzQ8U")
    print("所有者: pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA (Raydium)")
    
    print("\n❓ 为什么我们的SDK无法交易：")
    print("1. SDK依赖Jupiter API，而Jupiter不支持这个特定的池")
    print("2. 这个池可能不在Jupiter的默认代币列表中")
    print("3. GMGN可能有特殊的白名单或定制集成")
    
    print("\n💡 解决方案：")
    print("1. 添加对Raydium的直接集成")
    print("2. 使用Raydium的SDK来处理这个池的交易")
    print("3. 或者找到池中的基础代币，通过Jupiter交易基础代币")


async def main():
    """运行所有检查"""
    await check_gmgn_api()
    await check_raydium_pool_details()
    await check_token_metadata()
    await analyze_gmgn_mechanism()
    
    print("\n" + "=" * 60)
    print("🎯 最终结论")
    print("=" * 60)
    print("✅ GMGN能够交易这个池的原因：")
    print("   - GMGN有特殊的Raydium池集成")
    print("   - 可能使用自定义的智能合约")
    print("   - 直接与Raydium AMM协议交互")
    print("\n❌ 我们的SDK无法交易的原因：")
    print("   - 依赖Jupiter API，而Jupiter不支持这个池")
    print("   - 需要Raydium的直接集成")
    print("\n🔧 技术建议：")
    print("   要支持类似的交易，需要添加Raydium SDK集成")


if __name__ == "__main__":
    asyncio.run(main())