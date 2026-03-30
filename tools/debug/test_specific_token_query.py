#!/usr/bin/env python3
"""
测试直接查询指定Pump.Fun代币
"""

import asyncio
import aiohttp
import json
from src.sol_meme_sdk.api_config import get_api_config


async def test_specific_token_query(mint_address: str):
    """测试直接查询指定代币"""
    config = get_api_config()
    base_url = config.pumpfun_api_base
    
    print(f"🔍 测试查询代币: {mint_address}")
    print(f"🌐 API基础地址: {base_url}")
    
    # 尝试不同的端点
    endpoints_to_test = [
        f"/coins/{mint_address}",
        f"/tokens/{mint_address}", 
        f"/token/{mint_address}",
        f"/coin/{mint_address}",
        f"/coins?mint={mint_address}",
        f"/coins?address={mint_address}",
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Referer': 'https://pump.fun/'
    }
    
    async with aiohttp.ClientSession() as session:
        for endpoint in endpoints_to_test:
            url = f"{base_url}{endpoint}"
            print(f"\n🔄 测试端点: {url}")
            
            try:
                async with session.get(url, headers=headers, timeout=10) as response:
                    print(f"   📊 状态码: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        print(f"   ✅ 成功获取数据")
                        print(f"   📋 数据格式: {type(data)}")
                        
                        if isinstance(data, dict):
                            # 如果是字典，可能是单个代币数据
                            print(f"   🔑 数据键: {list(data.keys())}")
                            if 'mint' in data or 'address' in data:
                                print(f"   🎯 找到代币数据!")
                                return data
                        elif isinstance(data, list):
                            # 如果是列表，可能有多个结果
                            print(f"   📊 列表长度: {len(data)}")
                            if len(data) > 0:
                                print(f"   🔍 第一个结果: {data[0].keys() if isinstance(data[0], dict) else '非字典'}")
                        
                        # 保存响应数据用于分析
                        with open(f"api_response_{endpoint.replace('/', '_')}.json", 'w') as f:
                            json.dump(data, f, indent=2)
                        
                    elif response.status == 404:
                        print(f"   ❌ 端点不存在")
                    elif response.status == 400:
                        print(f"   ❌ 请求参数错误")
                    else:
                        print(f"   ⚠️ 其他错误: {response.status}")
                        
            except Exception as e:
                print(f"   ❌ 请求失败: {e}")
    
    # 如果所有端点都失败，尝试从列表筛选
    print(f"\n🔄 尝试从代币列表中筛选...")
    return await get_token_from_list(mint_address)


async def get_token_from_list(mint_address: str):
    """从代币列表中筛选指定代币"""
    config = get_api_config()
    url = config.get_pumpfun_api_url()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Referer': 'https://pump.fun/'
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ 获取到 {len(data)} 个代币")
                    
                    # 查找指定代币
                    for token in data:
                        if token.get('mint') == mint_address:
                            print(f"🎯 找到目标代币!")
                            return token
                    
                    print(f"❌ 未找到代币 {mint_address}")
                    
                else:
                    print(f"❌ API请求失败: {response.status}")
                    
        except Exception as e:
            print(f"❌ 请求失败: {e}")
    
    return None


async def main():
    """主函数"""
    # 测试代币地址
    mint_address = "CaQ1Q9i2YWsjPyWaGTJJjxPPmAnfCAxfvnDJ3T6hpump"
    
    print("🚀 Pump.Fun特定代币查询测试")
    print("=" * 60)
    
    result = await test_specific_token_query(mint_address)
    
    print(f"\n📊 最终结果:")
    print("=" * 60)
    
    if result:
        print("✅ 成功获取代币信息:")
        print(f"   地址: {result.get('mint', result.get('address', 'N/A'))}")
        print(f"   符号: {result.get('symbol', 'N/A')}")
        print(f"   名称: {result.get('name', 'N/A')}")
        print(f"   进度: {result.get('progress', 'N/A')}")
        print(f"   市值: {result.get('market_cap', 'N/A')}")
        
        # 保存结果
        with open("specific_token_result.json", 'w') as f:
            json.dump(result, f, indent=2)
        print(f"💾 结果已保存到 specific_token_result.json")
    else:
        print("❌ 未能获取代币信息")


if __name__ == "__main__":
    asyncio.run(main())