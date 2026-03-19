#!/usr/bin/env python3
"""
探索Pump.Fun API的参数，看看如何获取更多代币数据
"""

import asyncio
import aiohttp
import json
from urllib.parse import urlencode


async def explore_api_parameters():
    """探索API参数"""
    
    # 尝试不同的参数组合
    parameters_list = [
        {},  # 默认
        {"limit": 100},  # 增加限制
        {"limit": 200},  # 更多数据
        {"offset": 50},  # 偏移量
        {"offset": 50, "limit": 100},  # 偏移+限制
        {"sort": "progress", "order": "desc"},  # 按进度排序
        {"sort": "market_cap", "order": "desc"},  # 按市值排序
        {"sort": "created_timestamp", "order": "desc"},  # 按创建时间排序
        {"sort": "created_timestamp", "order": "asc"},  # 按创建时间升序
        {"min_progress": 0.5},  # 最小进度过滤
        {"max_progress": 1.0},  # 最大进度过滤
    ]
    
    base_url = "https://frontend-api-v3.pump.fun/coins"
    
    for params in parameters_list:
        url = base_url
        if params:
            url = f"{base_url}?{urlencode(params)}"
        
        print(f"\n🔧 测试参数: {params}")
        print(f"   URL: {url}")
        
        async with aiohttp.ClientSession() as session:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
                'Referer': 'https://pump.fun/'
            }
            
            try:
                async with session.get(url, headers=headers, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"   ✅ 获取到 {len(data)} 个代币")
                        
                        # 检查是否有高进度代币
                        high_progress_tokens = []
                        for token in data:
                            real_sol = token.get('real_sol_reserves', 0)
                            virtual_sol = token.get('virtual_sol_reserves', 1)
                            complete = token.get('complete', False)
                            
                            if complete:
                                progress = 1.0
                            elif virtual_sol <= 0:
                                progress = 0.0
                            else:
                                progress = real_sol / virtual_sol
                                progress = max(0.0, min(progress, 1.0))
                            
                            if progress > 0.5:  # 进度超过50%
                                high_progress_tokens.append((token.get('symbol', 'UNK'), progress))
                        
                        if high_progress_tokens:
                            print(f"   🎯 高进度代币: {len(high_progress_tokens)}个")
                            for symbol, progress in sorted(high_progress_tokens, key=lambda x: x[1], reverse=True)[:5]:
                                print(f"      {symbol}: {progress:.1%}")
                        else:
                            print(f"   ⚠️ 没有高进度代币")
                            
                    else:
                        print(f"   ❌ 请求失败: {response.status}")
                        
            except Exception as e:
                print(f"   ❌ 请求异常: {e}")


async def check_pagination():
    """检查分页机制"""
    print(f"\n📄 检查分页机制")
    
    base_url = "https://frontend-api-v3.pump.fun/coins"
    
    # 测试不同页码
    for page in range(1, 6):
        params = {"page": page, "limit": 50}
        url = f"{base_url}?{urlencode(params)}"
        
        print(f"\n🔧 测试页码: {page}")
        
        async with aiohttp.ClientSession() as session:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
                'Referer': 'https://pump.fun/'
            }
            
            try:
                async with session.get(url, headers=headers, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"   ✅ 获取到 {len(data)} 个代币")
                        
                        # 检查是否有重复数据
                        if page > 1 and len(data) > 0:
                            # 简单检查：显示第一个代币
                            first_token = data[0]
                            print(f"   第一个代币: {first_token.get('symbol', 'UNK')}")
                            
                    else:
                        print(f"   ❌ 请求失败: {response.status}")
                        
            except Exception as e:
                print(f"   ❌ 请求异常: {e}")


async def main():
    """主函数"""
    print("🔍 探索Pump.Fun API参数")
    print("=" * 60)
    
    await explore_api_parameters()
    await check_pagination()
    
    print(f"\n📋 总结:")
    print("1. API可能只返回固定的50个最新代币")
    print("2. 参数如limit, offset可能被忽略")
    print("3. 需要寻找其他方法获取更多数据")


if __name__ == "__main__":
    asyncio.run(main())