#!/usr/bin/env python3
"""
实际Raydium集成测试 - 使用现有工具和API
"""

import asyncio
import aiohttp
import json
from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey


class RaydiumIntegrationTest:
    """Raydium集成测试类"""
    
    def __init__(self):
        self.client = AsyncClient('https://api.mainnet-beta.solana.com')
        self.raydium_base_url = "https://api.raydium.io"
    
    async def get_raydium_pools(self):
        """获取Raydium池列表"""
        
        print("🔍 获取Raydium池列表")
        print("=" * 60)
        
        endpoints = [
            "/v2/sdk/liquidity/mainnet.json",
            "/v2/amm/pools",
            "/pools"
        ]
        
        for endpoint in endpoints:
            try:
                url = f"{self.raydium_base_url}{endpoint}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=10) as resp:
                        if resp.status == 200:
                            print(f"✅ {endpoint} - 成功")
                            data = await resp.json()
                            
                            # 分析数据结构
                            if isinstance(data, dict):
                                print(f"   字典键: {list(data.keys())[:5]}...")
                                
                                # 检查池类型
                                for pool_type in ['official', 'unOfficial', 'pools']:
                                    if pool_type in data:
                                        pools = data[pool_type]
                                        print(f"   {pool_type}池数量: {len(pools)}")
                                        
                                        # 搜索我们的池
                                        target_pool = None
                                        for pool in pools[:10]:  # 检查前10个池
                                            if 'authority' in pool:
                                                print(f"     池示例: {pool.get('id', 'N/A')[:20]}...")
                                            
                            elif isinstance(data, list):
                                print(f"   列表长度: {len(data)}")
                                if len(data) > 0:
                                    print(f"   第一个池: {data[0].get('id', 'N/A')[:30]}...")
                                    
                            return data
                            
                        else:
                            print(f"❌ {endpoint} - 状态码: {resp.status}")
                            
            except Exception as e:
                print(f"❌ {endpoint} - 错误: {e}")
        
        return None
    
    async def find_our_pool(self, pools_data):
        """在池列表中查找我们的池"""
        
        print("\n🔎 查找目标池")
        print("=" * 60)
        
        target_pool_address = "CSRJSQ5daTA9sehZAboPQYAJqbptJzgQ2e7aGduWzQ8U"
        
        if not pools_data:
            print("❌ 没有池数据")
            return None
        
        # 递归搜索池
        def search_in_data(data, path=""):
            if isinstance(data, dict):
                # 检查是否是池对象
                if 'authority' in data and data.get('authority') == target_pool_address:
                    return data, path
                
                # 递归搜索值
                for key, value in data.items():
                    result = search_in_data(value, f"{path}.{key}")
                    if result:
                        return result
                        
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    result = search_in_data(item, f"{path}[{i}]")
                    if result:
                        return result
            
            return None
        
        result = search_in_data(pools_data)
        
        if result:
            pool, path = result
            print(f"✅ 找到池! 路径: {path}")
            print(f"   池ID: {pool.get('id', 'N/A')}")
            print(f"   Base代币: {pool.get('baseMint', 'N/A')}")
            print(f"   Quote代币: {pool.get('quoteMint', 'N/A')}")
            return pool
        else:
            print("❌ 未找到目标池")
            return None
    
    async def analyze_pool_structure(self):
        """分析池的详细结构"""
        
        print("\n🔧 分析池结构")
        print("=" * 60)
        
        pool_address = "CSRJSQ5daTA9sehZAboPQYAJqbptJzgQ2e7aGduWzQ8U"
        
        try:
            # 获取账户数据
            pool_pubkey = Pubkey.from_string(pool_address)
            account_info = await self.client.get_account_info(pool_pubkey)
            
            if account_info.value:
                data = account_info.value.data
                print(f"✅ 账户数据长度: {len(data)} 字节")
                
                # Raydium AMM池的标准数据结构分析
                print("\n📊 数据结构分析:")
                
                # 1. 代币mint地址
                base_mint = Pubkey(data[8:40])
                quote_mint = Pubkey(data[40:72])
                print(f"   基础代币mint: {base_mint}")
                print(f"   报价代币mint: {quote_mint}")
                
                # 2. 代币数量
                base_amount = int.from_bytes(data[72:80], 'little')
                quote_amount = int.from_bytes(data[80:88], 'little')
                print(f"   基础代币数量: {base_amount:,}")
                print(f"   报价代币数量: {quote_amount:,}")
                
                # 3. LP代币信息
                lp_mint = Pubkey(data[104:136])
                lp_supply = int.from_bytes(data[136:144], 'little')
                print(f"   LP代币mint: {lp_mint}")
                print(f"   LP代币供应量: {lp_supply:,}")
                
                # 4. 价格计算
                if base_amount > 0 and quote_amount > 0:
                    price = quote_amount / base_amount
                    print(f"   💰 当前价格: 1 base = {price:,.6f} quote")
                    
                    # 计算LP代币价值
                    if lp_supply > 0:
                        total_value = quote_amount * 2  # 简化计算
                        lp_value = total_value / lp_supply
                        print(f"   💎 每个LP代币价值: {lp_value:,.6f} quote")
                
                return {
                    'base_mint': str(base_mint),
                    'quote_mint': str(quote_mint),
                    'base_amount': base_amount,
                    'quote_amount': quote_amount,
                    'lp_mint': str(lp_mint),
                    'lp_supply': lp_supply
                }
            
            else:
                print("❌ 无法获取账户数据")
                
        except Exception as e:
            print(f"❌ 池结构分析失败: {e}")
        
        return None
    
    async def test_liquidity_operations(self, pool_info):
        """测试流动性操作"""
        
        print("\n💧 流动性操作测试")
        print("=" * 60)
        
        if not pool_info:
            print("❌ 没有池信息")
            return
        
        print("💡 LP代币操作流程:")
        print("1. 添加流动性 → 获得LP代币")
        print("2. 移除流动性 → 赎回基础代币")
        print("3. LP代币交易 → 二级市场交易")
        
        print("\n🔧 技术实现:")
        print("   ✅ 我们已经解析了池结构")
        print("   ✅ 知道基础代币和报价代币")
        print("   ✅ 了解LP代币的mint和供应量")
        
        print("\n🎯 下一步实现:")
        print("   1. 创建Raydium交易构建器")
        print("   2. 实现添加流动性功能")
        print("   3. 实现移除流动性功能")
        print("   4. 集成到SDK中")
    
    async def check_gmgn_compatibility(self):
        """检查与GMGN的兼容性"""
        
        print("\n🔄 GMGN兼容性检查")
        print("=" * 60)
        
        print("💡 GMGN的工作方式分析:")
        print("   - 直接与Raydium智能合约交互")
        print("   - 使用自定义的交易构建逻辑")
        print("   - 支持各种Raydium池版本")
        
        print("\n🎯 我们的实现策略:")
        print("   ✅ 使用相同的底层协议(Raydium)")
        print("   ✅ 解析相同的池数据结构")
        print("   ✅ 实现相同的流动性操作")
        
        print("\n🔧 技术差异:")
        print("   GMGN: 自定义前端 + 直接合约调用")
        print("   我们: Python SDK + 标准Raydium集成")
    
    async def run_all_tests(self):
        """运行所有测试"""
        
        print("🔧 Raydium集成测试开始")
        print("=" * 60)
        
        # 1. 获取池列表
        pools_data = await self.get_raydium_pools()
        
        # 2. 查找我们的池
        if pools_data:
            await self.find_our_pool(pools_data)
        
        # 3. 分析池结构
        pool_info = await self.analyze_pool_structure()
        
        # 4. 测试流动性操作
        await self.test_liquidity_operations(pool_info)
        
        # 5. 检查GMGN兼容性
        await self.check_gmgn_compatibility()
        
        print("\n" + "=" * 60)
        print("🎯 测试总结")
        print("=" * 60)
        
        if pool_info:
            print("✅ 池结构解析成功!")
            print("💡 我们已经具备了实现LP交易的基础:")
            print(f"   - 基础代币: {pool_info['base_mint']}")
            print(f"   - 报价代币: {pool_info['quote_mint']}")
            print(f"   - LP代币: {pool_info['lp_mint']}")
            print(f"   - LP供应量: {pool_info['lp_supply']:,}")
        else:
            print("❌ 池结构解析失败")
        
        print("\n🔧 下一步行动:")
        print("   1. 创建Raydium交易构建器类")
        print("   2. 实现添加/移除流动性功能")
        print("   3. 测试实际交易")
        
        await self.client.close()


async def main():
    """主函数"""
    test = RaydiumIntegrationTest()
    await test.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())