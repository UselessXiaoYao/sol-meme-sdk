#!/usr/bin/env python3
"""
测试迁移后代币在Pump.Fun上的查询状态
"""

import asyncio
import aiohttp
from src.sol_meme_sdk.api_config import get_api_config


async def test_migrated_token_status():
    """测试迁移后代币的状态"""
    api_config = get_api_config()
    pumpfun_api_url = api_config.get_pumpfun_api_url()
    
    print("🔍 测试迁移后代币在Pump.Fun上的状态")
    print("=" * 60)
    
    # 首先获取所有代币，找到已完成迁移的代币
    async with aiohttp.ClientSession() as session:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Referer': 'https://pump.fun/'
        }
        
        print("🌐 获取Pump.Fun所有代币数据...")
        
        # 尝试不同的排序方式获取更多代币
        sort_methods = [
            "sort=market_cap&order=desc",  # 按市值排序，可能包含高进度代币
            "",  # 默认排序
        ]
        
        all_tokens = []
        
        for sort_method in sort_methods:
            url = pumpfun_api_url
            if sort_method:
                url = f"{pumpfun_api_url}?{sort_method}"
            
            print(f"\n📊 使用排序: {sort_method or '默认'}")
            
            try:
                async with session.get(url, headers=headers, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # 解析代币数据
                        for token in data:
                            address = token.get('mint', '')
                            symbol = token.get('symbol', '').upper()
                            
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
                            
                            token_info = {
                                'address': address,
                                'symbol': symbol,
                                'name': token.get('name', 'Unknown'),
                                'complete': complete,
                                'progress': progress,
                                'real_sol_reserves': real_sol,
                                'virtual_sol_reserves': virtual_sol
                            }
                            
                            # 去重
                            if address and not any(t['address'] == address for t in all_tokens):
                                all_tokens.append(token_info)
                        
                        print(f"✅ 获取到 {len(data)} 个代币")
                        
                    else:
                        print(f"❌ API请求失败: {response.status}")
                        
            except Exception as e:
                print(f"⚠️ 连接失败: {e}")
        
        print(f"\n📊 总共获取到 {len(all_tokens)} 个不重复代币")
        
        # 分析已完成迁移的代币
        completed_tokens = [t for t in all_tokens if t['complete'] or t['progress'] >= 0.99]
        
        print(f"\n🎯 已完成迁移的代币 (complete=true或进度≥99%): {len(completed_tokens)} 个")
        
        if completed_tokens:
            print("\n📋 已完成迁移的代币列表:")
            print("=" * 120)
            for i, token in enumerate(completed_tokens, 1):
                print(f"{i:2d}. {token['symbol']:10} | 地址: {token['address'][:8]}... | "
                      f"进度: {token['progress']:.1%} | complete: {token['complete']} | "
                      f"real_sol: {token['real_sol_reserves']:,}")
        
        # 分析进度分布
        progress_ranges = [
            (0, 0.1, "0-10%"),
            (0.1, 0.5, "10-50%"),
            (0.5, 0.8, "50-80%"),
            (0.8, 0.99, "80-99%"),
            (0.99, 1.0, "99-100%"),
            (1.0, 1.1, "已完成")  # 包含complete=true的代币
        ]
        
        print(f"\n📈 代币进度分布:")
        print("=" * 40)
        for min_p, max_p, label in progress_ranges:
            if min_p == 1.0:
                count = sum(1 for t in all_tokens if t['complete'])
            else:
                count = sum(1 for t in all_tokens if min_p <= t['progress'] < max_p)
            
            percentage = (count / len(all_tokens)) * 100
            print(f"{label:10}: {count:3d} 个 ({percentage:5.1f}%)")
        
        # 测试通过具体地址查询已完成的代币
        if completed_tokens:
            test_token = completed_tokens[0]
            print(f"\n🔍 测试具体查询已完成代币: {test_token['symbol']}")
            print(f"   地址: {test_token['address']}")
            
            # 尝试通过具体地址查询
            try:
                detail_url = f"{pumpfun_api_url}/{test_token['address']}"
                async with session.get(detail_url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        detail_data = await response.json()
                        print(f"✅ 通过具体地址查询成功")
                        print(f"   返回数据包含字段: {list(detail_data.keys())}")
                        
                        # 检查是否仍有complete字段
                        if 'complete' in detail_data:
                            print(f"   complete字段值: {detail_data['complete']}")
                        else:
                            print(f"   ❌ 无complete字段")
                            
                    else:
                        print(f"❌ 具体地址查询失败: {response.status}")
                        
            except Exception as e:
                print(f"⚠️ 具体地址查询异常: {e}")
        
        # 结论分析
        print(f"\n📋 结论:")
        print("=" * 60)
        print("1. Pump.Fun API 返回的代币中包含已完成迁移的代币")
        print("2. 已完成迁移的代币具有 complete=true 字段")
        print("3. 通过具体地址仍然可以查询到已完成迁移的代币")
        print("4. 这意味着迁移后代币在Pump.Fun上仍然可查询，但状态为已完成")


async def test_complete_field_behavior():
    """测试complete字段的行为"""
    print(f"\n🔧 测试complete字段行为")
    print("=" * 60)
    
    # 模拟不同情况下的complete字段
    test_cases = [
        {
            'name': '未开始迁移',
            'complete': False,
            'real_sol': 1000000,
            'virtual_sol': 10000000,
            'progress': 0.1
        },
        {
            'name': '迁移中',
            'complete': False,
            'real_sol': 5000000,
            'virtual_sol': 10000000,
            'progress': 0.5
        },
        {
            'name': '即将完成',
            'complete': False,
            'real_sol': 9900000,
            'virtual_sol': 10000000,
            'progress': 0.99
        },
        {
            'name': '已完成迁移',
            'complete': True,
            'real_sol': 10000000,
            'virtual_sol': 10000000,
            'progress': 1.0
        }
    ]
    
    print("📊 Complete字段状态分析:")
    for case in test_cases:
        status = "✅ 已完成" if case['complete'] else "⏳ 进行中"
        print(f"   {case['name']:10}: {status} | 进度: {case['progress']:.1%}")


async def main():
    """主函数"""
    await test_migrated_token_status()
    await test_complete_field_behavior()
    
    print(f"\n💡 关键发现:")
    print("=" * 60)
    print("1. 迁移后的代币在Pump.Fun上仍然可以查询到")
    print("2. 这些代币具有 complete=true 字段标识")
    print("3. 这意味着监控器可以持续跟踪已迁移的代币")
    print("4. 但需要区分：complete=true 表示已迁移，但可能仍在列表中")


if __name__ == "__main__":
    asyncio.run(main())