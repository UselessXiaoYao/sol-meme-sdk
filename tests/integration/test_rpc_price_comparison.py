#!/usr/bin/env python3
"""
RPC价格对比测试脚本
测试从RPC直接获取价格，并与Jupiter、Raydium API进行对比
"""

import asyncio
import logging
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sol_meme_sdk.rpc_price_provider import RPCPriceProvider, PriceComparisonTool
from sol_meme_sdk.wallet import Wallet
from sol_meme_sdk.trading_engine import TradingEngine
from sol_meme_sdk.unified_config import get_config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_single_comparison():
    """测试单次价格对比"""
    print("🔍 开始单次价格对比测试")
    
    try:
        # 初始化组件
        wallet = Wallet()
        trading_engine = TradingEngine(wallet)
        rpc_provider = RPCPriceProvider()
        
        # 连接RPC
        await rpc_provider.connect()
        
        # 创建对比工具
        comparison_tool = PriceComparisonTool(trading_engine, rpc_provider)
        
        # 测试代币 (USDC)
        test_token = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        
        print(f"\n📊 测试代币: USDC ({test_token[:8]}...)")
        
        # 执行对比
        comparison = await comparison_tool.compare_prices(test_token)
        
        # 打印结果
        print("\n📋 对比结果:")
        print("-" * 60)
        
        for source, data in comparison['sources'].items():
            if data['status'] == 'success':
                print(f"✅ {source.upper():<10}: {data['price']:.10f} SOL")
                print(f"   响应时间: {data['response_time']:.3f}s")
            else:
                print(f"❌ {source.upper():<10}: 失败")
                print(f"   错误: {data.get('error', 'Unknown')}")
        
        # 打印分析
        print("\n🔍 分析结果:")
        analysis = comparison['analysis']
        
        if analysis['successful_sources']:
            print(f"✅ 成功源: {', '.join(analysis['successful_sources'])}")
        
        if analysis['fastest_source']:
            print(f"🏃 最快源: {analysis['fastest_source']}")
        
        if analysis['price_differences']:
            print("📊 价格差异:")
            for pair, diff in analysis['price_differences'].items():
                print(f"   {pair}: {diff['percentage_difference']:.2f}%")
        
        if analysis['recommendations']:
            print("💡 推荐:")
            for rec in analysis['recommendations']:
                print(f"   • {rec}")
        
        print("-" * 60)
        
        # 检查RPC连接状态
        rpc_health = await rpc_provider.health_check()
        print(f"🔗 RPC连接状态: {'✅ 健康' if rpc_health else '❌ 异常'}")
        
        return True
        
    except Exception as e:
        logger.error(f"单次对比测试失败: {e}")
        return False
    finally:
        # 清理资源
        if 'rpc_provider' in locals():
            await rpc_provider.close()


async def test_multiple_tokens():
    """测试多个代币的价格对比"""
    print("\n🔍 开始多代币价格对比测试")
    
    # 测试代币列表
    test_tokens = [
        ("SOL", "So11111111111111111111111111111111111111112"),
        ("USDC", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"),
        ("USDT", "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"),
    ]
    
    try:
        # 初始化组件
        wallet = Wallet()
        trading_engine = TradingEngine(wallet)
        rpc_provider = RPCPriceProvider()
        
        # 连接RPC
        await rpc_provider.connect()
        
        # 创建对比工具
        comparison_tool = PriceComparisonTool(trading_engine, rpc_provider)
        
        results = {}
        
        for token_name, token_address in test_tokens:
            print(f"\n📊 测试代币: {token_name} ({token_address[:8]}...)")
            
            try:
                comparison = await comparison_tool.compare_prices(token_address)
                results[token_name] = comparison
                
                # 打印简要结果
                successful_sources = comparison['analysis']['successful_sources']
                print(f"   ✅ 成功源: {', '.join(successful_sources) if successful_sources else '无'}")
                
                for source in ['rpc', 'jupiter', 'raydium']:
                    if source in comparison['sources'] and comparison['sources'][source]['status'] == 'success':
                        price = comparison['sources'][source]['price']
                        time = comparison['sources'][source]['response_time']
                        print(f"   {source.upper():<8}: {price:.8f} SOL ({time:.3f}s)")
                
            except Exception as e:
                print(f"   ❌ 测试失败: {e}")
                results[token_name] = {'error': str(e)}
        
        # 统计成功率
        print("\n📈 总体统计:")
        total_tokens = len(test_tokens)
        
        for source in ['rpc', 'jupiter', 'raydium']:
            successful = sum(1 for token in test_tokens 
                           if results.get(token[0], {}).get('sources', {}).get(source, {}).get('status') == 'success')
            success_rate = (successful / total_tokens) * 100
            print(f"   {source.upper():<8}: {success_rate:.1f}% ({successful}/{total_tokens})")
        
        return True
        
    except Exception as e:
        logger.error(f"多代币测试失败: {e}")
        return False
    finally:
        # 清理资源
        if 'rpc_provider' in locals():
            await rpc_provider.close()


async def test_real_time_monitoring():
    """测试实时价格监控"""
    print("\n📈 开始实时价格监控测试")
    
    try:
        # 初始化组件
        wallet = Wallet()
        trading_engine = TradingEngine(wallet)
        rpc_provider = RPCPriceProvider()
        
        # 连接RPC
        await rpc_provider.connect()
        
        # 创建对比工具
        comparison_tool = PriceComparisonTool(trading_engine, rpc_provider)
        
        # 测试代币
        test_token = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC
        
        # 短时间监控（20秒，每2秒一次）
        print(f"🔍 监控代币: USDC ({test_token[:8]}...)")
        print("⏱️  时长: 20秒, 间隔: 2秒")
        
        await comparison_tool.monitor_price_real_time(
            test_token, 
            duration=20, 
            interval=2.0
        )
        
        return True
        
    except Exception as e:
        logger.error(f"实时监控测试失败: {e}")
        return False
    finally:
        # 清理资源
        if 'rpc_provider' in locals():
            await rpc_provider.close()


async def test_rpc_pool_info():
    """测试RPC池子信息获取"""
    print("\n🔍 测试RPC池子信息获取")
    
    try:
        rpc_provider = RPCPriceProvider()
        await rpc_provider.connect()
        
        # 测试已知池子
        known_pools = rpc_provider.KNOWN_POOLS.get("mainnet-beta", {})
        
        for pool_name, pool_address in known_pools.items():
            print(f"\n📊 测试池子: {pool_name}")
            print(f"   地址: {pool_address}")
            
            try:
                pool_info = await rpc_provider.get_pool_info(pool_address)
                
                print(f"   ✅ 池子信息获取成功")
                print(f"   基础代币: {pool_info.get('base_mint', 'N/A')[:16]}...")
                print(f"   报价代币: {pool_info.get('quote_mint', 'N/A')[:16]}...")
                print(f"   基础数量: {pool_info.get('base_amount', 0):,}")
                print(f"   报价数量: {pool_info.get('quote_amount', 0):,}")
                
                if 'price' in pool_info:
                    print(f"   价格: {pool_info['price']:.10f}")
                
            except Exception as e:
                print(f"   ❌ 池子信息获取失败: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"RPC池子信息测试失败: {e}")
        return False
    finally:
        # 清理资源
        if 'rpc_provider' in locals():
            await rpc_provider.close()


async def main():
    """主测试函数"""
    print("🚀 RPC价格对比测试套件")
    print("=" * 60)
    
    # 获取配置信息
    config = get_config()
    print(f"📋 网络配置: {config.solana_network}")
    print(f"🔗 RPC端点: {config.solana_rpc_endpoint}")
    print("=" * 60)
    
    # 运行测试
    tests = [
        ("单次价格对比", test_single_comparison),
        ("RPC池子信息", test_rpc_pool_info),
        ("多代币对比", test_multiple_tokens),
        ("实时监控", test_real_time_monitoring),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n🎯 运行测试: {test_name}")
        print("-" * 40)
        
        try:
            success = await test_func()
            results[test_name] = "✅ 通过" if success else "❌ 失败"
        except Exception as e:
            logger.error(f"测试 {test_name} 异常: {e}")
            results[test_name] = "❌ 异常"
    
    # 打印测试结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总:")
    print("-" * 60)
    
    for test_name, result in results.items():
        print(f"{test_name:<20}: {result}")
    
    print("=" * 60)
    
    # 检查是否有失败的测试
    failed_tests = [name for name, result in results.items() if "失败" in result or "异常" in result]
    
    if failed_tests:
        print(f"\n⚠️  失败的测试: {', '.join(failed_tests)}")
        return 1
    else:
        print("\n🎉 所有测试通过!")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)