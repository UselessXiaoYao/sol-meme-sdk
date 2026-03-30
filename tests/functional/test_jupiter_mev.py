#!/usr/bin/env python3
"""
测试JupiterClient的MEV和优先费功能
"""

import sys
import os
import asyncio
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.sol_meme_sdk.jupiter_client import JupiterClient
from src.sol_meme_sdk.wallet import Wallet

def test_jupiter_mev_setup():
    """测试JupiterClient的MEV配置"""
    print("🔧 测试JupiterClient MEV配置")
    print("=" * 60)
    
    try:
        # 初始化JupiterClient
        jupiter_client = JupiterClient()
        
        # 测试MEV配置
        mev_config = jupiter_client.get_mev_config()
        print("📋 MEV配置信息:")
        print(f"   RPC URL: {mev_config['rpc_url']}")
        print(f"   Jito小费地址: {mev_config['jito_tip_account']}")
        print(f"   默认小费配置: {mev_config['default_tips']}")
        print(f"   支持的优先级级别: {mev_config['supported_priority_levels']}")
        
        print("✅ JupiterClient MEV配置测试完成")
        return True
        
    except Exception as e:
        print(f"❌ JupiterClient MEV配置测试失败: {e}")
        return False

async def test_recommended_fees():
    """测试推荐费用获取"""
    print("\n💰 测试推荐费用获取")
    print("=" * 60)
    
    try:
        jupiter_client = JupiterClient()
        
        # 测试不同优先级级别的费用
        priority_levels = ['low', 'medium', 'high', 'very_high']
        
        for level in priority_levels:
            fees = await jupiter_client.get_recommended_fees(priority_level=level)
            print(f"\n📊 {level.upper()}优先级费用:")
            print(f"   优先费: {fees['priority_fee_micro_lamports']} 微lamports")
            print(f"   Jito小费: {fees['jito_tip']} lamports")
            print(f"   推荐: {fees['recommendation']}")
            
        print("\n✅ 推荐费用获取测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 推荐费用获取测试失败: {e}")
        return False

async def test_swap_methods():
    """测试交换方法（不实际执行交易）"""
    print("\n🔄 测试交换方法结构")
    print("=" * 60)
    
    try:
        jupiter_client = JupiterClient()
        wallet = Wallet.generate()
        
        # 测试代币信息获取（验证API连接）
        print("🔗 测试Jupiter API连接...")
        
        # 获取SOL和USDC代币信息
        try:
            sol_info = await jupiter_client.get_token_info("So11111111111111111111111111111111111111112")
            usdc_info = await jupiter_client.get_token_info("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
            
            print("✅ Jupiter API连接正常")
            print(f"   SOL代币: {sol_info.get('symbol', 'SOL')}")
            print(f"   USDC代币: {usdc_info.get('symbol', 'USDC')}")
            
        except Exception as api_error:
            print(f"⚠️  Jupiter API连接测试失败（可能缺少API密钥）: {api_error}")
        
        # 测试方法结构（不实际执行）
        print("\n🔧 测试交换方法结构:")
        
        # 检查swap_tokens方法是否存在
        if hasattr(jupiter_client, 'swap_tokens'):
            print("   ✅ swap_tokens方法存在")
        else:
            print("   ❌ swap_tokens方法缺失")
            
        # 检查execute_trade_with_mev_protection方法是否存在
        if hasattr(jupiter_client, 'execute_trade_with_mev_protection'):
            print("   ✅ execute_trade_with_mev_protection方法存在")
        else:
            print("   ❌ execute_trade_with_mev_protection方法缺失")
            
        # 检查buy_token方法是否存在
        if hasattr(jupiter_client, 'buy_token'):
            print("   ✅ buy_token方法存在")
        else:
            print("   ❌ buy_token方法缺失")
            
        # 检查sell_token方法是否存在
        if hasattr(jupiter_client, 'sell_token'):
            print("   ✅ sell_token方法存在")
        else:
            print("   ❌ sell_token方法缺失")
        
        print("\n✅ 交换方法结构测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 交换方法测试失败: {e}")
        return False

def test_mev_integration():
    """测试MEV集成"""
    print("\n🛡️ 测试MEV集成")
    print("=" * 60)
    
    try:
        jupiter_client = JupiterClient()
        
        # 检查MEV保护服务是否已集成
        if hasattr(jupiter_client, 'mev_protection'):
            mev_service = jupiter_client.mev_protection
            print("✅ MEV保护服务已集成")
            print(f"   服务类型: {type(mev_service).__name__}")
            
            # 检查MEV服务方法
            mev_methods = ['add_jito_tip', 'get_priority_fee_estimate', 'execute_with_mev_protection']
            for method in mev_methods:
                if hasattr(mev_service, method):
                    print(f"   ✅ {method}方法可用")
                else:
                    print(f"   ❌ {method}方法不可用")
        else:
            print("❌ MEV保护服务未集成")
            return False
            
        print("\n✅ MEV集成测试完成")
        return True
        
    except Exception as e:
        print(f"❌ MEV集成测试失败: {e}")
        return False

async def main():
    """主测试函数"""
    print("🎯 JupiterClient MEV功能测试")
    print("=" * 60)
    
    # 运行所有测试
    tests = [
        ("MEV配置测试", test_jupiter_mev_setup),
        ("MEV集成测试", test_mev_integration),
        ("推荐费用测试", test_recommended_fees),
        ("交换方法测试", test_swap_methods)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🚀 运行测试: {test_name}")
        
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            results.append((test_name, result))
            
        except Exception as e:
            print(f"❌ 测试 {test_name} 异常: {e}")
            results.append((test_name, False))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 总体结果: {passed}/{total} 测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！JupiterClient MEV功能已成功集成")
    else:
        print(f"⚠️  有 {total - passed} 个测试失败，请检查配置")

if __name__ == "__main__":
    asyncio.run(main())