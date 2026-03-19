#!/usr/bin/env python3
"""
调试进度计算问题
检查H4MGU4ahpsxA86bM24W1P6oiwmFas4d2y78nRPu4pump这个代币的实际API响应
"""

import asyncio
import aiohttp
import json
from datetime import datetime
from src.sol_meme_sdk.api_config import get_api_config


async def debug_progress_calculation():
    """调试进度计算"""
    api_config = get_api_config()
    pumpfun_api_url = api_config.get_pumpfun_api_url()
    
    print(f"🔧 使用API端点: {pumpfun_api_url}")
    
    # 首先获取所有代币
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
                
                # 查找特定代币
                target_token = None
                for token in data:
                    if token.get('mint') == 'H4MGU4ahpsxA86bM24W1P6oiwmFas4d2y78nRPu4pump':
                        target_token = token
                        break
                
                if target_token:
                    print(f"\n🎯 找到目标代币: {target_token.get('name', 'Unknown')} ({target_token.get('symbol', 'UNK')})")
                    print("📊 原始数据:")
                    print(json.dumps(target_token, indent=2, ensure_ascii=False))
                    
                    # 计算进度
                    real_sol_reserves = target_token.get('real_sol_reserves', 0)
                    virtual_sol_reserves = target_token.get('virtual_sol_reserves', 1)
                    complete = target_token.get('complete', False)
                    
                    print(f"\n📈 进度计算参数:")
                    print(f"   real_sol_reserves: {real_sol_reserves}")
                    print(f"   virtual_sol_reserves: {virtual_sol_reserves}")
                    print(f"   complete: {complete}")
                    
                    if complete:
                        progress = 1.0
                    elif virtual_sol_reserves <= 0:
                        progress = 0.0
                    else:
                        progress = real_sol_reserves / virtual_sol_reserves
                        progress = max(0.0, min(progress, 1.0))
                    
                    print(f"   🔢 计算进度: {progress:.3f} ({progress:.1%})")
                    
                    # 检查是否有其他可能的进度字段
                    print(f"\n🔍 检查其他可能的进度字段:")
                    for key, value in target_token.items():
                        if 'progress' in key.lower() or 'percent' in key.lower() or 'ratio' in key.lower():
                            print(f"   {key}: {value}")
                else:
                    print("❌ 未找到目标代币")
                    
                    # 检查前10个代币的数据结构
                    print(f"\n📋 检查前10个代币的数据结构:")
                    for i, token in enumerate(data[:10], 1):
                        print(f"\n{i}. {token.get('symbol', 'UNK')}:")
                        print(f"   mint: {token.get('mint', 'N/A')}")
                        print(f"   real_sol_reserves: {token.get('real_sol_reserves', 0)}")
                        print(f"   virtual_sol_reserves: {token.get('virtual_sol_reserves', 1)}")
                        
                        # 计算进度
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
                        
                        print(f"   🔢 进度: {progress:.3f} ({progress:.1%})")
                        
            else:
                print(f"❌ API请求失败: {response.status}")


async def main():
    """主函数"""
    await debug_progress_calculation()


if __name__ == "__main__":
    print("🔍 调试进度计算问题")
    print("=" * 60)
    asyncio.run(main())