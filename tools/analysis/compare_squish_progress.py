#!/usr/bin/env python3
"""
比较SQUISH代币在Pump.Fun和GMGN上的进度差异
"""

import asyncio
import aiohttp
import json
from src.sol_meme_sdk.api_config import get_api_config


async def compare_squish_progress():
    """比较SQUISH代币的进度"""
    api_config = get_api_config()
    pumpfun_api_url = api_config.get_pumpfun_api_url()
    
    print("🔍 比较SQUISH代币进度")
    print("=" * 60)
    
    # 首先获取所有代币，找到SQUISH
    async with aiohttp.ClientSession() as session:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Referer': 'https://pump.fun/'
        }
        
        # 尝试不同的排序方式
        sort_methods = [
            "",  # 默认
            "sort=market_cap&order=desc",
            "sort=created_timestamp&order=asc",
        ]
        
        squish_token = None
        
        for sort_method in sort_methods:
            url = pumpfun_api_url
            if sort_method:
                url = f"{pumpfun_api_url}?{sort_method}"
            
            print(f"\n🌐 尝试 {sort_method or '默认排序'}")
            
            async with session.get(url, headers=headers, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # 查找SQUISH代币
                    for token in data:
                        symbol = token.get('symbol', '').upper()
                        if symbol == 'SQUISH':
                            squish_token = token
                            print(f"✅ 找到SQUISH代币")
                            break
                    
                    if squish_token:
                        break
        
        if squish_token:
            print(f"\n📊 Pump.Fun API数据:")
            print(f"   地址: {squish_token.get('mint', 'N/A')}")
            print(f"   名称: {squish_token.get('name', 'Unknown')}")
            print(f"   符号: {squish_token.get('symbol', 'UNK')}")
            
            # 计算Pump.Fun进度
            complete = squish_token.get('complete', False)
            real_sol = squish_token.get('real_sol_reserves', 0)
            virtual_sol = squish_token.get('virtual_sol_reserves', 1)
            
            if complete:
                pumpfun_progress = 1.0
            elif virtual_sol <= 0:
                pumpfun_progress = 0.0
            else:
                pumpfun_progress = real_sol / virtual_sol
                pumpfun_progress = max(0.0, min(pumpfun_progress, 1.0))
            
            print(f"   Pump.Fun进度: {pumpfun_progress:.3f} ({pumpfun_progress:.1%})")
            print(f"   real_sol_reserves: {real_sol}")
            print(f"   virtual_sol_reserves: {virtual_sol}")
            print(f"   complete: {complete}")
            
            # 显示所有字段用于调试
            print(f"\n📋 所有字段:")
            for key, value in sorted(squish_token.items()):
                print(f"   {key}: {value}")
            
            # 检查是否有其他进度相关字段
            print(f"\n🔍 检查进度相关字段:")
            for key, value in squish_token.items():
                key_lower = key.lower()
                if any(word in key_lower for word in ['progress', 'percent', 'ratio', 'filled', 'reserve']):
                    print(f"   {key}: {value}")
        else:
            print("❌ 未找到SQUISH代币")
            
            # 显示前10个代币的进度供参考
            print(f"\n📊 前10个代币的进度:")
            
            # 重新获取一次数据
            url = pumpfun_api_url
            async with session.get(url, headers=headers, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for i, token in enumerate(data[:10], 1):
                        symbol = token.get('symbol', 'UNK')
                        
                        # 计算进度
                        complete = token.get('complete', False)
                        real_sol = token.get('real_sol_reserves', 0)
                        virtual_sol = token.get('virtual_sol_reserves', 1)
                        
                        if complete:
                            progress = 1.0
                        elif virtual_sol <= 0:
                            progress = 0.0
                        else:
                            progress = real_sol / virtual_sol
                            progress = max(0.0, min(progress, 1.0))
                        
                        print(f"   {i}. {symbol}: {progress:.1%}")
    
    # 尝试GMGN API获取进度
    print(f"\n🌐 尝试GMGN API查询")
    
    # 注意：这里需要实际的GMGN API端点
    # 暂时先模拟GMGN的20.9%进度
    gmgn_progress = 0.209
    print(f"   GMGN进度: {gmgn_progress:.1%}")
    
    if squish_token:
        print(f"\n📊 进度对比:")
        print(f"   Pump.Fun: {pumpfun_progress:.1%}")
        print(f"   GMGN:     {gmgn_progress:.1%}")
        print(f"   差异:     {abs(pumpfun_progress - gmgn_progress):.1%}")
        
        if abs(pumpfun_progress - gmgn_progress) > 0.1:  # 差异超过10%
            print(f"\n⚠️ 进度差异较大，可能原因:")
            print("   1. API数据延迟或缓存")
            print("   2. 不同的计算方式")
            print("   3. 数据源不同步")


async def test_real_pumpfun_monitor():
    """测试监控器中的进度计算"""
    print(f"\n🔧 测试监控器中的进度计算")
    
    from real_pumpfun_monitor import RealPumpFunMonitor
    
    monitor = RealPumpFunMonitor()
    
    # 模拟一个代币数据
    test_item = {
        'mint': 'test_address',
        'complete': False,
        'real_sol_reserves': 7734843201,
        'virtual_sol_reserves': 37734843201,
        'symbol': 'SQUISH'
    }
    
    progress = monitor._extract_progress(test_item)
    print(f"   测试进度: {progress:.3f} ({progress:.1%})")
    print(f"   计算方式: real_sol_reserves / virtual_sol_reserves")
    print(f"   具体值: {test_item['real_sol_reserves']} / {test_item['virtual_sol_reserves']}")


async def main():
    """主函数"""
    await compare_squish_progress()
    await test_real_pumpfun_monitor()
    
    print(f"\n📋 总结:")
    print("1. Pump.Fun API使用 real_sol_reserves / virtual_sol_reserves 计算进度")
    print("2. 如果进度差异较大，需要检查数据源和计算逻辑")
    print("3. 可能需要在监控器中添加GMGN API集成")


if __name__ == "__main__":
    asyncio.run(main())