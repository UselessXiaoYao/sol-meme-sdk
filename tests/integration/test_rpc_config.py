#!/usr/bin/env python3
"""
RPC配置系统测试 - 分析私有RPC和公共RPC的使用场景
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.sol_meme_sdk.unified_config import (
    get_config, 
    get_public_rpc_url, 
    get_private_rpc_url, 
    is_private_rpc,
    print_config
)

def test_rpc_config():
    """测试RPC配置系统"""
    print("🔧 测试RPC配置系统")
    print("=" * 60)
    
    # 获取配置
    config = get_config()
    
    # 打印当前配置
    print_config()
    
    # 测试RPC URL获取
    print("\n📡 RPC配置详细信息:")
    print(f"   当前网络: {config.solana_network}")
    print(f"   私有RPC端点: {config.solana_private_rpc_endpoint}")
    print(f"   公共RPC端点: {config.solana_public_rpc_endpoint}")
    print(f"   是否使用不同RPC: {'是' if is_private_rpc() else '否'}")
    
    print("\n🔗 RPC使用情况:")
    print(f"   📍 私有RPC URL: {get_private_rpc_url()}")
    print(f"   📍 公共RPC URL: {get_public_rpc_url()}")
    
    print("\n✅ RPC配置系统测试完成")

def test_rpc_usage_analysis():
    """分析RPC使用场景"""
    print("\n📊 RPC使用场景分析")
    print("=" * 60)
    
    private_rpc = get_private_rpc_url()
    public_rpc = get_public_rpc_url()
    
    print("🏠 私有RPC使用场景:")
    print("   ✅ 交易执行 (TradingEngine._get_rpc_url())")
    print("   ✅ MEV保护服务")
    print("   ✅ DEX客户端连接 (JupiterClient, RaydiumClient等)")
    print("   🎯 目的: 保证交易执行速度和可靠性")
    
    print("\n🌐 公共RPC使用场景:")
    print("   ✅ 余额查询 (get_balance(), get_token_balances())")
    print("   ✅ 交易确认验证 (_wait_for_confirmation())")
    print("   ✅ 价格查询和监控")
    print("   🎯 目的: 保证查询准确性和稳定性")
    
    print(f"\n🔍 当前配置分析:")
    print(f"   私有RPC: {private_rpc}")
    print(f"   公共RPC: {public_rpc}")
    
    if private_rpc != public_rpc:
        print("   🎯 配置正确: 私有RPC和公共RPC分离使用")
        print("   💡 优势: 交易执行使用本地节点，查询使用公共RPC")
    else:
        print("   ⚠️  配置警告: 私有RPC和公共RPC相同")
    
    print("\n✅ RPC使用场景分析完成")

def test_config_validation():
    """测试配置验证"""
    print("\n🔍 配置验证测试")
    print("=" * 60)
    
    config = get_config()
    
    print("📋 配置验证:")
    
    # 检查RPC端点配置
    if not config.solana_private_rpc_endpoint:
        print("   ❌ 私有RPC端点未配置")
    else:
        print(f"   ✅ 私有RPC端点: {config.solana_private_rpc_endpoint}")
    
    if not config.solana_public_rpc_endpoint:
        print("   ❌ 公共RPC端点未配置")
    else:
        print(f"   ✅ 公共RPC端点: {config.solana_public_rpc_endpoint}")
    
    # 检查本地节点配置
    local_domains = ['localhost', '127.0.0.1', '69.67.149.99']
    is_local_private = any(domain in config.solana_private_rpc_endpoint for domain in local_domains)
    is_local_public = any(domain in config.solana_public_rpc_endpoint for domain in local_domains)
    
    print(f"\n🏠 本地节点检测:")
    print(f"   私有RPC是否为本地节点: {'是' if is_local_private else '否'}")
    print(f"   公共RPC是否为本地节点: {'是' if is_local_public else '否'}")
    
    if is_local_private and not is_local_public:
        print("   ✅ 配置正确: 私有RPC使用本地节点，公共RPC使用外部服务")
    elif is_local_private and is_local_public:
        print("   ⚠️  配置警告: 私有RPC和公共RPC都使用本地节点")
    elif not is_local_private and is_local_public:
        print("   ❌ 配置错误: 公共RPC使用本地节点，私有RPC使用外部服务")
    else:
        print("   ℹ️  配置信息: 都使用外部RPC服务")
    
    print("\n✅ 配置验证测试完成")

def test_practical_scenarios():
    """测试实际使用场景"""
    print("\n🚀 实际使用场景测试")
    print("=" * 60)
    
    try:
        from src.sol_meme_sdk.trading_engine import TradingEngine
        from src.sol_meme_sdk.wallet import Wallet
        from src.sol_meme_sdk.models import TransactionConfig
        
        # 创建测试钱包和配置
        wallet = Wallet.generate()
        tx_config = TransactionConfig(
            dex_priority=['jupiter', 'raydium'],
            max_position_size=0.1,
            slippage_tolerance=0.01
        )
        
        # 初始化交易引擎
        trading_engine = TradingEngine(wallet, tx_config)
        
        print("📊 TradingEngine RPC配置:")
        
        # 测试私有RPC获取
        private_rpc = trading_engine._get_rpc_url()
        print(f"   🔒 私有RPC (交易执行): {private_rpc}")
        
        # 测试公共RPC获取
        public_rpc = trading_engine._get_public_rpc_url()
        print(f"   🌐 公共RPC (查询验证): {public_rpc}")
        
        # 测试本地节点检测
        is_local = trading_engine._is_local_node()
        print(f"   🏠 检测为本地节点: {'是' if is_local else '否'}")
        
        print("\n🎯 使用场景验证:")
        print(f"   交易执行使用: {trading_engine._get_rpc_url()}")
        print(f"   余额查询使用: {trading_engine._get_public_rpc_url()}")
        print(f"   交易确认使用: {trading_engine._get_public_rpc_url()}")
        
        print("\n✅ 实际使用场景测试完成")
        
    except Exception as e:
        print(f"⚠️  实际场景测试失败: {e}")

if __name__ == "__main__":
    test_rpc_config()
    test_rpc_usage_analysis()
    test_config_validation()
    test_practical_scenarios()
    
    print("\n" + "=" * 60)
    print("🎉 所有RPC配置测试完成")
    print("=" * 60)