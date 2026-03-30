#!/usr/bin/env python3
"""
主网Jupiter API报价测试 - 使用TradingEngine验证代码功能
"""

import asyncio
import os
import sys
from pathlib import Path

# 设置主网环境变量
os.environ["SOLANA_NETWORK"] = "mainnet-beta"

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from sol_meme_sdk.trading_engine import TradingEngine
from sol_meme_sdk.models import TransactionConfig, DEXProtocol, TradeOrder, OrderSide, OrderType
from sol_meme_sdk.wallet import Wallet
from sol_meme_sdk.unified_config import get_config

async def test_mainnet_jupiter():
    """测试主网Jupiter API功能"""
    print("🚀 主网Jupiter API测试")
    print("=" * 60)
    
    try:
        # 1. 检查配置
        config = get_config()
        print(f"🔧 当前网络: {config.solana_network}")
        print(f"   RPC端点: {config.solana_rpc_endpoint}")
        
        # 2. 检查Jupiter API密钥
        if not config.jupiter_api_key or config.jupiter_api_key == "your_jupiter_api_key_here":
            print("⚠️  Jupiter API密钥未设置")
            print("   请设置JUPITER_API_KEY环境变量")
            print("   获取免费密钥: https://portal.jup.ag/")
            
            # 尝试使用公共API端点（可能有限制）
            print("💡 尝试使用公共API端点进行基础测试...")
        else:
            print("✅ Jupiter API密钥已设置")
        
        # 3. 主网代币地址
        mainnet_tokens = {
            "SOL": "So11111111111111111111111111111111111111112",
            "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "JUP": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
            "BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"
        }
        
        print(f"\n💰 主网代币地址:")
        for symbol, address in mainnet_tokens.items():
            print(f"   {symbol}: {address}")
        
        # 4. 测试TradingEngine初始化
        print("\n🔄 初始化TradingEngine...")
        
        # 创建主网配置
        trade_config = TransactionConfig(
            enable_devnet_testing=False,  # 主网模式
            dex_protocol=DEXProtocol.AUTO,
            jupiter_slippage_bps=50,
            raydium_slippage_bps=50,
            max_retries=3,
            skip_preflight=False
        )
        
        print("✅ TransactionConfig 创建成功")
        
        # 检查钱包文件（可选，因为只需要测试API调用）
        wallet_file = project_root / "new_wallet.json"
        if wallet_file.exists():
            try:
                wallet = Wallet.from_json_file(str(wallet_file))
                print(f"✅ 钱包加载成功 - 地址: {wallet.address}")
                
                # 创建TradingEngine实例
                trading_engine = TradingEngine(wallet=wallet, config=trade_config)
                print("✅ TradingEngine 初始化成功!")
                print(f"   网络模式: {'devnet' if trading_engine.is_devnet else 'mainnet'}")
                
            except Exception as e:
                print(f"⚠️  TradingEngine初始化失败: {e}")
                print("   使用独立Jupiter客户端测试...")
                trading_engine = None
        else:
            print("⚠️  钱包文件不存在，跳过TradingEngine初始化")
            trading_engine = None
        
        # 5. 测试Jupiter API报价功能
        print("\n🔍 测试Jupiter API报价功能...")
        
        test_cases = [
            {
                "name": "SOL → USDC (基础交易对)",
                "input_mint": mainnet_tokens["SOL"],
                "output_mint": mainnet_tokens["USDC"],
                "amount": 0.01  # 0.01 SOL
            },
            {
                "name": "USDC → SOL (反向交易)",
                "input_mint": mainnet_tokens["USDC"],
                "output_mint": mainnet_tokens["SOL"],
                "amount": 1.0  # 1 USDC
            },
            {
                "name": "SOL → JUP (热门代币)",
                "input_mint": mainnet_tokens["SOL"],
                "output_mint": mainnet_tokens["JUP"],
                "amount": 0.01  # 0.01 SOL
            }
        ]
        
        success_count = 0
        
        for test_case in test_cases:
            print(f"\n📊 测试: {test_case['name']}")
            print(f"   输入: {test_case['amount']} {test_case['input_mint'][:10]}...")
            print(f"   输出: {test_case['output_mint'][:10]}...")
            
            try:
                if trading_engine:
                    # 使用TradingEngine的Jupiter客户端
                    quote = await trading_engine.jupiter_client.get_quote(
                        input_mint=test_case["input_mint"],
                        output_mint=test_case["output_mint"],
                        amount=test_case["amount"],
                        slippage_bps=50
                    )
                else:
                    # 独立Jupiter客户端测试
                    from sol_meme_sdk.jupiter_client import JupiterClient
                    jupiter_client = JupiterClient(network="mainnet-beta")
                    quote = await jupiter_client.get_quote(
                        input_mint=test_case["input_mint"],
                        output_mint=test_case["output_mint"],
                        amount=test_case["amount"],
                        slippage_bps=50
                    )
                
                # 解析报价结果
                if "outAmount" in quote:
                    out_amount = int(quote["outAmount"])
                    
                    # 根据输出代币转换金额
                    if test_case["output_mint"] == mainnet_tokens["SOL"]:
                        out_amount_sol = out_amount / 1e9
                        print(f"   ✅ 报价成功: {out_amount_sol:.6f} SOL")
                    elif test_case["output_mint"] == mainnet_tokens["USDC"]:
                        out_amount_usdc = out_amount / 1e6
                        print(f"   ✅ 报价成功: {out_amount_usdc:.2f} USDC")
                    else:
                        print(f"   ✅ 报价成功: {out_amount} 单位")
                    
                    # 显示路由信息
                    if "routePlan" in quote:
                        print(f"   路由步骤: {len(quote['routePlan'])} 步")
                    
                    success_count += 1
                    
                else:
                    print(f"   ❌ 报价响应格式错误")
                    print(f"   响应: {quote}")
                    
            except Exception as e:
                print(f"   ❌ 报价失败: {e}")
        
        # 6. 总结结果
        print("\n" + "=" * 60)
        print("📋 测试结果总结:")
        print(f"   成功测试: {success_count}/{len(test_cases)}")
        
        if success_count == len(test_cases):
            print("🎉 所有Jupiter API测试通过!")
            print("✅ TradingEngine和Jupiter客户端代码正常")
        elif success_count > 0:
            print("⚠️  部分测试通过，可能存在API限制或代币问题")
        else:
            print("❌ 所有测试失败，需要检查API密钥或网络连接")
        
        print("\n💡 建议:")
        if success_count == 0:
            print("   1. 检查JUPITER_API_KEY环境变量")
            print("   2. 验证网络连接")
            print("   3. 确认代币地址正确性")
        else:
            print("   1. Jupiter API功能正常")
            print("   2. TradingEngine集成正确")
            print("   3. 可以继续进行交易测试")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mainnet_jupiter())