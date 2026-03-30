#!/usr/bin/env python3
"""
分析GMGN币对地址 EcSrKwco6iun9xDShsMJUFGTc9kiCjkZ6UJGJ8Gr2vQV
"""

import asyncio
import json
from sol_meme_sdk import RaydiumClient


async def analyze_gmgn_pair():
    """分析GMGN币对"""
    
    print("🔍 分析GMGN币对地址")
    print("=" * 60)
    
    # 初始化Raydium客户端
    client = RaydiumClient()
    
    try:
        await client.connect()
        
        # 用户提供的币对地址
        pool_address = "EcSrKwco6iun9xDShsMJUFGTc9kiCjkZ6UJGJ8Gr2vQV"
        
        print(f"📊 分析池地址: {pool_address}")
        print("-" * 40)
        
        # 获取池信息
        pool_info = await client.get_pool_info(pool_address)
        
        print("🔍 池结构分析:")
        print(f"   池地址: {pool_info['pool_address']}")
        print(f"   基础代币: {pool_info['base_mint']}")
        print(f"   报价代币: {pool_info['quote_mint']}")
        print(f"   LP代币: {pool_info['lp_mint']}")
        print(f"   基础代币数量: {pool_info['base_amount']:,}")
        print(f"   报价代币数量: {pool_info['quote_amount']:,}")
        print(f"   LP供应量: {pool_info['lp_supply']:,}")
        
        if 'price' in pool_info:
            print(f"   当前价格: 1 base = {pool_info['price']:.10f} quote")
        
        # 计算LP价格
        lp_price = await client.get_lp_token_price(pool_address)
        print(f"   💰 LP代币价格: {lp_price:.10f} quote")
        
        # 池所有权分析
        print(f"   所有者程序: {pool_info['owner_program']}")
        
        print("\n📈 流动性分析:")
        print("-" * 40)
        
        # 计算总流动性价值
        total_liquidity = pool_info.get('quote_amount', 0) * 2  # 简化计算
        print(f"   总流动性价值: {total_liquidity:,} quote")
        
        # 计算池深度
        if pool_info.get('base_amount', 0) > 0:
            pool_depth = pool_info['quote_amount'] / pool_info['base_amount']
            print(f"   池深度: {pool_depth:.4f}")
        
        # 估算APY
        apy = await client.get_pool_apy(pool_address)
        print(f"   估算APY: {apy:.2f}%")
        
        # 获取交易量
        volume = await client.get_pool_volume_24h(pool_address)
        print(f"   24小时交易量: {volume['total_volume_usd']:,.2f} USD")
        
        print("\n🔍 技术分析:")
        print("-" * 40)
        
        # 分析池状态
        if pool_info['base_amount'] == 0 or pool_info['quote_amount'] == 0:
            print("   ⚠️ 池流动性不足或为空池")
        else:
            print("   ✅ 池有流动性")
        
        # 检查池类型
        if "Raydium" in pool_info['owner_program']:
            print("   ✅ Raydium官方池")
        else:
            print(f"   ℹ️ 池类型: {pool_info['owner_program']}")
        
        print("\n🎯 GMGN交易支持分析:")
        print("-" * 40)
        
        # 检查池是否适合GMGN交易
        liquidity_threshold = 1000000  # 最小流动性阈值
        
        if pool_info['base_amount'] > liquidity_threshold and pool_info['quote_amount'] > liquidity_threshold:
            print("   ✅ 流动性充足，适合GMGN交易")
        else:
            print("   ⚠️ 流动性可能不足")
        
        # 检查价格稳定性
        if 'price' in pool_info and pool_info['price'] > 0:
            price_stability = abs(pool_info['base_amount'] / pool_info['quote_amount'] - pool_info['price']) / pool_info['price']
            if price_stability < 0.1:  # 10%价格波动
                print("   ✅ 价格相对稳定")
            else:
                print(f"   ⚠️ 价格波动较大: {price_stability:.2f}")
        
        print("\n💡 交易建议:")
        print("-" * 40)
        
        # 提供交易建议
        if pool_info['base_amount'] > 0 and pool_info['quote_amount'] > 0:
            print("   ✅ 池状态正常，可以交易")
            print("   💰 建议交易量: 小额测试开始")
            print("   📊 监控价格波动和流动性变化")
        else:
            print("   ⚠️ 池可能存在问题，谨慎交易")
        
        print("\n🔗 与之前池的对比:")
        print("-" * 40)
        
        # 对比之前的池
        old_pool = "CSRJSQ5daTA9sehZAboPQYAJqbptJgzQ2e7aGduWzQ8U"
        old_pool_info = await client.get_pool_info(old_pool)
        
        print(f"   新池流动性: {pool_info['base_amount']:,} base")
        print(f"   旧池流动性: {old_pool_info['base_amount']:,} base")
        
        liquidity_ratio = pool_info['base_amount'] / old_pool_info['base_amount'] if old_pool_info['base_amount'] > 0 else float('inf')
        print(f"   流动性比例: {liquidity_ratio:.2f}")
        
        print("\n🎉 分析完成！")
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        
    finally:
        await client.close()


async def check_token_existence():
    """检查代币是否存在"""
    
    print("\n🔍 检查代币存在性")
    print("=" * 60)
    
    client = RaydiumClient()
    
    try:
        await client.connect()
        
        pool_address = "EcSrKwco6iun9xDShsMJUFGTc9kiCjkZ6UJGJ8Gr2vQV"
        pool_info = await client.get_pool_info(pool_address)
        
        print("🔎 代币验证:")
        
        # 检查基础代币
        base_mint = pool_info['base_mint']
        print(f"   基础代币: {base_mint}")
        
        # 检查报价代币
        quote_mint = pool_info['quote_mint']
        print(f"   报价代币: {quote_mint}")
        
        # 检查LP代币
        lp_mint = pool_info['lp_mint']
        print(f"   LP代币: {lp_mint}")
        
        # 尝试获取代币信息
        from solana.rpc.commitment import Confirmed
        from solders.pubkey import Pubkey
        
        print("\n📋 代币账户检查:")
        
        for mint_name, mint_address in [("基础代币", base_mint), ("报价代币", quote_mint), ("LP代币", lp_mint)]:
            try:
                mint_pubkey = Pubkey.from_string(mint_address)
                account_info = await client.client.get_account_info(mint_pubkey, commitment=Confirmed)
                
                if account_info.value:
                    print(f"   ✅ {mint_name}账户存在")
                    print(f"      数据长度: {len(account_info.value.data)} bytes")
                    print(f"      所有者: {account_info.value.owner}")
                else:
                    print(f"   ❌ {mint_name}账户不存在")
                    
            except Exception as e:
                print(f"   ⚠️ {mint_name}检查失败: {e}")
        
        print("\n🎯 代币状态总结:")
        
        if pool_info['base_amount'] > 0 and pool_info['quote_amount'] > 0:
            print("   ✅ 代币对存在且可交易")
        else:
            print("   ⚠️ 代币对可能存在问题")
        
    except Exception as e:
        print(f"❌ 代币检查失败: {e}")
        
    finally:
        await client.close()


async def main():
    """主分析函数"""
    
    print("🔬 GMGN币对深度分析")
    print("=" * 60)
    
    # 分析池信息
    await analyze_gmgn_pair()
    
    # 检查代币存在性
    await check_token_existence()
    
    print("\n" + "=" * 60)
    print("🎉 分析完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())