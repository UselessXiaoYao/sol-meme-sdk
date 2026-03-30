#!/usr/bin/env python3
"""
分析Meteora API的实际数据结构
"""

import asyncio
import aiohttp
import json

async def analyze_meteora_api_structure():
    """分析Meteora API的实际数据结构"""
    
    meteora_api_base = "https://damm-v2.datapi.meteora.ag"
    
    print("🔍 分析Meteora API数据结构...")
    
    try:
        # 测试获取池列表
        async with aiohttp.ClientSession() as session:
            print("\n📊 获取池列表数据...")
            url = f"{meteora_api_base}/pools"
            params = {'page': 1, 'page_size': 10}  # 只获取前10个池
            
            async with session.get(url, params=params, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    print("✅ API响应成功")
                    print(f"总池数: {data.get('total', 'N/A')}")
                    print(f"总页数: {data.get('pages', 'N/A')}")
                    print(f"当前页: {data.get('current_page', 'N/A')}")
                    print(f"每页大小: {data.get('page_size', 'N/A')}")
                    
                    # 分析第一个池的数据结构
                    if data.get('data') and len(data['data']) > 0:
                        first_pool = data['data'][0]
                        print("\n📋 第一个池的字段结构:")
                        print(json.dumps(first_pool, indent=2, ensure_ascii=False)[:1000])  # 限制输出长度
                        
                        # 提取关键字段
                        print("\n🔑 关键字段:")
                        for key in ['address', 'id', 'name', 'token_a_mint', 'token_b_mint', 
                                   'token_x_mint', 'token_y_mint', 'liquidity', 'volume', 'fees', 'tvl']:
                            if key in first_pool:
                                print(f"  {key}: {first_pool[key]}")
                    
                    # 获取池详情
                    print("\n📄 获取单个池的详细信息...")
                    if data.get('data') and len(data['data']) > 0:
                        pool_address = data['data'][0].get('address')
                        if pool_address:
                            detail_url = f"{meteora_api_base}/pools/{pool_address}"
                            async with session.get(detail_url, timeout=15) as detail_response:
                                if detail_response.status == 200:
                                    pool_detail = await detail_response.json()
                                    print("✅ 池详情获取成功")
                                    print("📋 池详情字段结构:")
                                    print(json.dumps(pool_detail, indent=2, ensure_ascii=False)[:800])
                                else:
                                    print(f"❌ 池详情获取失败: {detail_response.status}")
                else:
                    print(f"❌ API请求失败: {response.status}")
                    print(f"响应内容: {await response.text()}")
                    
    except Exception as e:
        print(f"❌ 分析过程中出错: {e}")

async def test_pagination():
    """测试分页功能"""
    
    meteora_api_base = "https://damm-v2.datapi.meteora.ag"
    
    print("\n🔍 测试分页功能...")
    
    try:
        async with aiohttp.ClientSession() as session:
            # 测试不同页大小
            page_sizes = [10, 50, 100]
            
            for page_size in page_sizes:
                print(f"\n📄 测试页大小: {page_size}")
                url = f"{meteora_api_base}/pools"
                params = {'page': 1, 'page_size': page_size}
                
                async with session.get(url, params=params, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        actual_records = len(data.get('data', []))
                        print(f"  请求页大小: {page_size}, 实际返回: {actual_records} 条记录")
                        print(f"  总记录数: {data.get('total', 'N/A')}")
                    else:
                        print(f"  ❌ 请求失败: {response.status}")
                        
    except Exception as e:
        print(f"❌ 分页测试失败: {e}")

async def main():
    """主函数"""
    print("🚀 开始分析Meteora API数据结构...")
    
    await analyze_meteora_api_structure()
    await test_pagination()
    
    print("\n✅ 分析完成")

if __name__ == "__main__":
    asyncio.run(main())