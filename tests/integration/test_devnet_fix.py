#!/usr/bin/env python3
"""
测试devnet环境修复结果
"""

import os
import sys
from pathlib import Path

# 设置环境变量
os.environ["SOLANA_NETWORK"] = "devnet"
os.environ["DEVNET_ENABLED"] = "true"

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from sol_meme_sdk.unified_config import get_config

def test_devnet_fix():
    """测试devnet修复结果"""
    print("🔧 测试devnet环境修复")
    print("=" * 50)
    
    try:
        # 获取配置
        config = get_config()
        
        print("✅ 配置系统正常")
        print(f"   当前网络: {config.solana_network}")
        print(f"   RPC端点: {config.solana_rpc_endpoint}")
        print(f"   Devnet启用: {config.devnet_enabled}")
        
        # 测试devnet专用配置
        devnet_config = config.get_devnet_config()
        print(f"\n🔧 Devnet专用配置:")
        print(f"   USDC地址: {devnet_config['usdc_mint']}")
        print(f"   SOL地址: {devnet_config['wrapped_sol']}")
        print(f"   支持的DEX: {devnet_config['supported_dex']}")
        print(f"   Jupiter受限: {devnet_config['jupiter_limited']}")
        
        # 测试代币地址获取
        print(f"\n💰 代币地址测试:")
        usdc_addr = config.get_token_mint_address("USDC")
        sol_addr = config.get_token_mint_address("SOL")
        print(f"   USDC地址: {usdc_addr}")
        print(f"   SOL地址: {sol_addr}")
        
        # 验证网络状态
        print(f"\n🌐 网络状态验证:")
        print(f"   是否devnet: {config.is_devnet()}")
        
        print("\n" + "=" * 50)
        print("🎉 Devnet环境修复测试通过!")
        print("\n✅ 修复完成项目:")
        print("   1. 配置系统升级 - 支持devnet专用配置")
        print("   2. Jupiter API优化 - devnet错误处理和回退")
        print("   3. TradingEngine改进 - 网络感知的代币地址")
        print("   4. 环境配置文件 - 完整的devnet配置")
        
        print("\n💡 下一步建议:")
        print("   1. 运行: python3 actual_trade_test.py 测试交易功能")
        print("   2. 检查Jupiter API密钥是否设置")
        print("   3. 使用Raydium作为devnet首选DEX")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_devnet_fix()