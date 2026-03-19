#!/usr/bin/env python3
"""
详细调试API响应结构，找出正确的进度字段
"""

import asyncio
import aiohttp
import json
from src.sol_meme_sdk.api_config import get_api_config


async def debug_api_response():
    """详细调试API响应"""
    api_config = get_api_config()
    pumpfun_api_url = api_config.get_pumpfun_api_url()
    
    print(f"🔧 使用API端点: {pumpfun_api_url}")
    
    async with aiohttp.ClientSession() as session:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Referer': 'https://pump.fun/'
        }
        
        async with session.get(pumpfun_api_url, headers=headers, timeout=15) as response:
            if response.status == 200:
                data = await response.json()
                print(f"✅ 获取到 {len(data)} 个代币")
                
                # 检查第一个代币的所有字段
                if data:
                    first_token = data[0]
                    print(f"\n📋 第一个代币的所有字段:")
                    print("=" * 60)
                    
                    # 按字段名排序显示
                    sorted_keys = sorted(first_token.keys())
                    for key in sorted_keys:
                        value = first_token[key]
                        print(f"{key:25}: {value}")
                    
                    print("=" * 60)
                    
                    # 特别检查可能包含进度信息的字段
                    print(f"\n🔍 检查可能包含进度信息的字段:")
                    
                    for key in sorted_keys:
                        value = first_token[key]
                        key_lower = key.lower()
                        
                        # 检查字段名中是否包含进度相关的关键词
                        if any(word in key_lower for word in ['progress', 'percent', 'ratio', 'complete', 'filled', 'reserve']):
                            print(f"🔍 {key:25}: {value}")
                            
                            # 如果是数字字段，尝试计算百分比
                            if isinstance(value, (int, float)):
                                if value <= 1.0:
                                    print(f"   → 可能进度: {value:.3f} ({value:.1%})")
                                elif value <= 100:
                                    print(f"   → 可能进度: {value/100:.3f} ({value/100:.1%})")
                    
                    # 检查数值字段，找出可能表示进度的模式
                    print(f"\n🔢 检查数值字段的模式:")
                    
                    # 查找所有数值字段
                    numeric_fields = {}
                    for key in sorted_keys:
                        value = first_token[key]
                        if isinstance(value, (int, float)):
                            numeric_fields[key] = value
                    
                    # 按值排序
                    sorted_numeric = sorted(numeric_fields.items(), key=lambda x: x[1])
                    
                    for key, value in sorted_numeric:
                        if value > 0:  # 忽略0值
                            print(f"{key:25}: {value:15} → {value/1e9:.6f} (除以1e9)")
                    
                    # 检查SOL相关的字段
                    print(f"\n💰 检查SOL相关字段:")
                    for key in sorted_keys:
                        if 'sol' in key.lower():
                            value = first_token[key]
                            print(f"{key:25}: {value}")
                            if isinstance(value, (int, float)) and value > 0:
                                print(f"   → SOL值: {value/1e9:.6f} SOL")
                
                # 检查是否有其他代币有不同的字段结构
                print(f"\n📊 检查所有代币的字段一致性:")
                all_keys = set()
                for token in data:
                    all_keys.update(token.keys())
                
                print(f"所有代币共有的字段数: {len(all_keys)}")
                print("共有字段:", sorted(all_keys))
                    
            else:
                print(f"❌ API请求失败: {response.status}")


async def main():
    """主函数"""
    await debug_api_response()


if __name__ == "__main__":
    print("🔍 详细调试API响应结构")
    print("=" * 60)
    asyncio.run(main())