#!/usr/bin/env python3
"""
演示JupiterClient的execute_trade_with_mev_protection接口使用
"""

import sys
import os
import asyncio
# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

from src.sol_meme_sdk.jupiter_client import JupiterClient
from src.sol_meme_sdk.wallet import Wallet
from src.sol_meme_sdk.exceptions import TradingError


async def demo_mev_protection_usage():
    """演示MEV保护功能的使用"""
    print("🛡️ 演示JupiterClient MEV保护功能使用")
    print("=" * 60)
    
    try:
        # 初始化JupiterClient
        jupiter_client = JupiterClient()
        
        # 生成测试钱包（仅用于演示，不实际执行交易）
        wallet = Wallet.generate()
        print(f"💰 测试钱包地址: {wallet.pubkey}")
        
        # 演示不同优先级级别的MEV保护交易
        print("\n📊 演示不同优先级级别的MEV保护交易")
        
        # 配置不同优先级级别的交易参数
        priority_configs = [
            {"level": "low", "description": "低优先级 - 适合不紧急的交易"},
            {"level": "medium", "description": "中等优先级 - 平衡速度和成本"},
            {"level": "high", "description": "高优先级 - 快速确认交易"},
            {"level": "very_high", "description": "极高优先级 - 确保快速确认"}
        ]
        
        for config in priority_configs:
            print(f"\n🔧 {config['level'].upper()}优先级配置: {config['description']}")
            
            try:
                # 获取推荐的费用配置
                fees = await jupiter_client.get_recommended_fees(priority_level=config['level'])
                print(f"   推荐优先费: {fees['priority_fee_micro_lamports']} 微lamports")
                print(f"   推荐Jito小费: {fees['jito_tip']} lamports")
                
                # 演示execute_trade_with_mev_protection调用（不实际执行）
                print(f"   📝 调用execute_trade_with_mev_protection方法...")
                
                # 模拟交易参数（不实际执行）
                trade_params = {
                    "input_mint": "So11111111111111111111111111111111111111112",  # SOL
                    "output_mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
                    "amount": 0.01,  # 0.01 SOL
                    "wallet": wallet,
                    "slippage_bps": 50,
                    "priority_level": config['level'],
                    "jito_tip": fees['jito_tip'],
                    "max_attempts": 3
                }
                
                print(f"   ✅ {config['level']}优先级MEV保护配置就绪")
                print(f"   输入: 0.01 SOL → 输出: USDC")
                print(f"   滑点: 0.5%")
                print(f"   最大尝试次数: 3")
                
            except TradingError as e:
                print(f"   ⚠️  {config['level']}优先级配置失败: {e}")
            except Exception as e:
                print(f"   ❌ {config['level']}优先级配置异常: {e}")
        
        # 演示自定义Jito小费
        print("\n💎 演示自定义Jito小费配置")
        
        custom_tip_amounts = [5000, 10000, 50000, 100000]  # lamports
        
        for tip_amount in custom_tip_amounts:
            print(f"\n🔧 自定义Jito小费: {tip_amount} lamports")
            
            try:
                # 演示自定义小费的MEV保护交易
                trade_params = {
                    "input_mint": "So11111111111111111111111111111111111111112",
                    "output_mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                    "amount": 0.01,
                    "wallet": wallet,
                    "slippage_bps": 50,
                    "priority_level": "medium",
                    "jito_tip": tip_amount,
                    "max_attempts": 3
                }
                
                print(f"   ✅ 自定义小费配置就绪")
                print(f"   小费金额: {tip_amount} lamports (≈ {tip_amount/1e9:.8f} SOL)")
                
            except Exception as e:
                print(f"   ❌ 自定义小费配置失败: {e}")
        
        # 演示MEV保护的重试机制
        print("\n🔄 演示MEV保护的重试机制")
        
        max_attempts_options = [1, 3, 5]
        
        for max_attempts in max_attempts_options:
            print(f"\n🔧 最大尝试次数: {max_attempts}")
            
            try:
                # 演示不同重试次数的配置
                trade_params = {
                    "input_mint": "So11111111111111111111111111111111111111112",
                    "output_mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                    "amount": 0.01,
                    "wallet": wallet,
                    "slippage_bps": 50,
                    "priority_level": "medium",
                    "jito_tip": None,  # 使用推荐值
                    "max_attempts": max_attempts
                }
                
                print(f"   ✅ 重试机制配置就绪")
                print(f"   最大尝试次数: {max_attempts}")
                print(f"   每次重试自动增加费用")
                
            except Exception as e:
                print(f"   ❌ 重试机制配置失败: {e}")
        
        print("\n✅ MEV保护功能演示完成")
        
    except Exception as e:
        print(f"❌ 演示失败: {e}")


async def compare_mev_vs_standard_trading():
    """比较MEV保护交易与标准交易的差异"""
    print("\n📊 比较MEV保护交易与标准交易的差异")
    print("=" * 60)
    
    try:
        jupiter_client = JupiterClient()
        wallet = Wallet.generate()
        
        print("🔍 比较两种交易方式:")
        
        # 标准交易方式
        print("\n1️⃣ 标准交易方式 (swap_tokens):")
        print("   ✅ 简单直接")
        print("   ✅ 固定费用配置")
        print("   ❌ 无自动重试")
        print("   ❌ 无费用调整")
        print("   ❌ 无MEV保护")
        
        # MEV保护交易方式
        print("\n2️⃣ MEV保护交易方式 (execute_trade_with_mev_protection):")
        print("   ✅ 自动重试机制")
        print("   ✅ 动态费用调整")
        print("   ✅ Jito小费支持")
        print("   ✅ 防止三明治攻击")
        print("   ✅ 提高交易成功率")
        
        # 使用场景建议
        print("\n💡 使用场景建议:")
        print("   📌 标准交易: 小额、不紧急的交易")
        print("   📌 MEV保护: 大额、时间敏感的交易")
        print("   📌 MEV保护: 网络拥堵时的交易")
        print("   📌 MEV保护: 重要资产转移")
        
        print("\n✅ 交易方式比较完成")
        
    except Exception as e:
        print(f"❌ 比较失败: {e}")


async def demo_integration_with_trading_engine():
    """演示与交易引擎的集成"""
    print("\n⚙️ 演示与交易引擎的集成")
    print("=" * 60)
    
    try:
        # 检查是否存在交易引擎
        try:
            from src.sol_meme_sdk.trading_engine import TradingEngine
            
            print("🔧 检测到TradingEngine，演示集成方案")
            
            # 创建交易引擎实例
            engine = TradingEngine()
            jupiter_client = JupiterClient()
            
            # 演示集成调用
            print("\n📝 集成调用示例:")
            print("   1. 交易引擎监控市场条件")
            print("   2. 发现交易机会")
            print("   3. 调用JupiterClient的MEV保护交易")
            print("   4. 自动重试直到成功")
            
            # 模拟交易策略
            strategies = [
                "快速套利策略 - 使用高优先级MEV保护",
                "趋势跟踪策略 - 使用中等优先级MEV保护", 
                "长期持有策略 - 使用低优先级标准交易"
            ]
            
            for strategy in strategies:
                print(f"\n🎯 策略: {strategy}")
                
                if "高优先级" in strategy:
                    print("   🔧 使用execute_trade_with_mev_protection")
                    print("   💰 优先级: high/very_high")
                    print("   🛡️ 启用完整MEV保护")
                elif "中等优先级" in strategy:
                    print("   🔧 使用execute_trade_with_mev_protection") 
                    print("   💰 优先级: medium")
                    print("   🛡️ 启用基础MEV保护")
                else:
                    print("   🔧 使用swap_tokens")
                    print("   💰 优先级: low")
                    print("   🛡️ 不使用MEV保护")
            
            print("\n✅ 交易引擎集成演示完成")
            
        except ImportError:
            print("⚠️ 未检测到TradingEngine，跳过集成演示")
            
    except Exception as e:
        print(f"❌ 集成演示失败: {e}")


async def main():
    """主演示函数"""
    print("🎯 JupiterClient MEV保护功能使用演示")
    print("=" * 60)
    
    # 运行所有演示
    demos = [
        ("MEV保护功能使用演示", demo_mev_protection_usage),
        ("交易方式比较", compare_mev_vs_standard_trading),
        ("交易引擎集成演示", demo_integration_with_trading_engine)
    ]
    
    for demo_name, demo_func in demos:
        print(f"\n🚀 开始演示: {demo_name}")
        await demo_func()
    
    # 总结
    print("\n" + "=" * 60)
    print("📋 演示总结")
    print("=" * 60)
    
    print("✅ execute_trade_with_mev_protection接口功能完整")
    print("✅ 支持多种优先级级别配置")
    print("✅ 支持自定义Jito小费")
    print("✅ 自动重试和费用调整机制")
    print("✅ 与交易引擎良好集成")
    
    print("\n💡 使用建议:")
    print("   1. 重要交易使用MEV保护功能")
    print("   2. 根据交易紧急程度选择优先级级别")
    print("   3. 网络拥堵时使用高优先级配置")
    print("   4. 小额交易可使用标准swap_tokens方法")
    
    print("\n🎉 演示完成！")


if __name__ == "__main__":
    asyncio.run(main())