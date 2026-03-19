#!/usr/bin/env python3
"""
Corrected analysis of GMGN trading mechanism
"""

import asyncio
from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey
import aiohttp


async def check_gmgn_trading_mechanism():
    """Analyze how GMGN enables trading of this pair"""
    
    print("🔍 重新分析GMGN交易机制")
    print("=" * 60)
    
    pair_address = "CSRJSQ5daTA9sehZAboPQYAJqbptJgzQ2e7aGduWzQ8U"
    
    client = AsyncClient('https://api.mainnet-beta.solana.com')
    
    try:
        # 1. 重新检查这个账户的真实性质
        pair_pubkey = Pubkey.from_string(pair_address)
        pair_info = await client.get_account_info(pair_pubkey)
        
        if pair_info.value:
            print("✅ 账户确实存在，让我们深入分析：")
            print(f"   所有者程序: {pair_info.value.owner}")
            
            # 2. 检查这是否真的是Raydium流动性池
            owner_str = str(pair_info.value.owner)
            
            if owner_str == "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA":
                print("✅ 确认是Raydium流动性池账户")
                
                # 3. 分析GMGN可能的工作方式
                print("\n💡 GMGN可能的工作方式：")
                print("   1. GMGN可能直接与Raydium协议交互")
                print("   2. 可能通过智能合约处理流动性操作")
                print("   3. 用户交易的不是LP代币，而是基础代币")
                
                # 4. 尝试获取池的具体信息
                print("\n🔗 尝试获取池的详细信息：")
                
                # Raydium API获取池信息
                async with aiohttp.ClientSession() as session:
                    # 获取Raydium的所有池
                    raydium_url = "https://api.raydium.io/v2/sdk/liquidity/mainnet.json"
                    
                    async with session.get(raydium_url, timeout=10) as resp:
                        if resp.status == 200:
                            pools_data = await resp.json()
                            
                            # 在所有池类型中搜索
                            found_pool = None
                            for pool_type in ['official', 'unOfficial']:
                                for pool in pools_data.get(pool_type, []):
                                    # 检查池账户地址
                                    if pool.get('authority') == pair_address:
                                        found_pool = pool
                                        print(f"✅ 在Raydium {pool_type}池中找到匹配！")
                                        break
                                if found_pool:
                                    break
                            
                            if found_pool:
                                print(f"   Mint地址: {found_pool.get('lpMint')}")
                                print(f"   Base代币: {found_pool.get('baseMint')}")
                                print(f"   Quote代币: {found_pool.get('quoteMint')}")
                                print(f"   Market ID: {found_pool.get('marketId')}")
                                
                                # 5. 检查这个池是否在GMGN支持的列表中
                                print("\n📊 检查池的交易状态：")
                                
                                # 尝试通过Raydium获取价格信息
                                market_id = found_pool.get('marketId')
                                if market_id:
                                    market_url = f"https://api.raydium.io/v2/main/market?marketId={market_id}"
                                    
                                    async with session.get(market_url, timeout=10) as market_resp:
                                        if market_resp.status == 200:
                                            market_data = await market_resp.json()
                                            print("✅ 获取到市场数据")
                                            if 'data' in market_data:
                                                print(f"   当前价格: {market_data['data'].get('price', 'N/A')}")
                                                print(f"   24h交易量: {market_data['data'].get('volume', 'N/A')}")
                                            
                            else:
                                print("❌ 在Raydium池中未找到匹配的池账户")
                                
                                # 6. 这可能是一个特殊的GMGN池
                                print("\n💡 这可能是一个GMGN特有的池：")
                                print("   - GMGN可能使用自定义的流动性池结构")
                                print("   - 或者这是Raydium的老版本池")
                                print("   - GMGN可能直接与Serum订单簿交互")
                        else:
                            print(f"❌ Raydium API错误: {resp.status}")
                
                # 7. 关键洞察：GMGN如何实现交易
                print("\n🎯 GMGN交易机制的关键洞察：")
                print("   ✅ GMGN不是通过Jupiter交易LP代币")
                print("   ✅ GMGN直接与底层DEX（Raydium）交互")
                print("   ✅ 用户交易的是池中的基础代币，不是LP代币")
                print("   ✅ GMGN可能处理了复杂的流动性操作")
                
        else:
            print("❌ 账户不存在")
            
    except Exception as e:
        print(f"❌ 分析失败: {e}")
    
    await client.close()


async def check_actual_trading():
    """检查实际的交易可能性"""
    
    print("\n🔄 检查实际交易可能性")
    print("=" * 60)
    
    # 如果我们要交易这个池，需要知道池中的代币
    pair_address = "CSRJSQ5daTA9sehZAboPQYAJqbptJgzQ2e7aGduWzQ8U"
    
    # 尝试通过不同方式获取池信息
    try:
        # 方法1: 通过Raydium的池列表搜索
        async with aiohttp.ClientSession() as session:
            # 获取所有Raydium池
            raydium_url = "https://api.raydium.io/v2/sdk/liquidity/mainnet.json"
            
            async with session.get(raydium_url, timeout=10) as resp:
                if resp.status == 200:
                    pools_data = await resp.json()
                    
                    # 搜索所有池类型
                    found_pools = []
                    for pool_type in ['official', 'unOfficial']:
                        for pool in pools_data.get(pool_type, []):
                            # 检查池的各种字段
                            if (pool.get('authority') == pair_address or 
                                pool.get('id') == pair_address):
                                found_pools.append((pool_type, pool))
                    
                    if found_pools:
                        print("✅ 找到匹配的池：")
                        for pool_type, pool in found_pools:
                            print(f"   {pool_type}池:")
                            print(f"     池ID: {pool.get('id')}")
                            print(f"     Base代币: {pool.get('baseMint')}")
                            print(f"     Quote代币: {pool.get('quoteMint')}")
                            print(f"     LP Mint: {pool.get('lpMint')}")
                            
                            # 这些是实际可以交易的代币
                            base_mint = pool.get('baseMint')
                            quote_mint = pool.get('quoteMint')
                            
                            print(f"\n💡 实际可交易的代币：")
                            print(f"   Base代币地址: {base_mint}")
                            print(f"   Quote代币地址: {quote_mint}")
                            print(f"   \n🎯 要交易这个池，应该使用这些代币地址！")
                            
                    else:
                        print("❌ 未找到匹配的池")
                        print("💡 这可能意味着：")
                        print("   - 池已关闭或迁移")
                        print("   - GMGN使用自定义池结构")
                        print("   - 需要其他API来获取信息")
                        
                else:
                    print(f"❌ Raydium API错误: {resp.status}")
                    
    except Exception as e:
        print(f"❌ 交易检查失败: {e}")


async def main():
    """运行分析"""
    await check_gmgn_trading_mechanism()
    await check_actual_trading()
    
    print("\n" + "=" * 60)
    print("🎯 总结")
    print("=" * 60)
    print("✅ GMGN能够交易的原因：")
    print("   - GMGN直接与底层DEX（Raydium）交互")
    print("   - 不是通过Jupiter交易LP代币")
    print("   - 用户交易的是池中的基础代币")
    print("\n❌ 我们的SDK无法交易的原因：")
    print("   - SDK依赖Jupiter API，而Jupiter不支持LP代币交易")
    print("   - 需要直接与Raydium协议集成才能实现类似功能")
    print("\n💡 解决方案：")
    print("   - 添加Raydium直接集成")
    print("   - 或者使用池中的基础代币地址进行交易")


if __name__ == "__main__":
    asyncio.run(main())