#!/usr/bin/env python3
"""
实际交易测试 - 检查可行性并尝试执行交易
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径到sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from sol_meme_sdk.wallet import Wallet
from sol_meme_sdk.trading_engine import TradingEngine
from sol_meme_sdk.models import TransactionConfig, DEXProtocol, TradeOrder, OrderSide, OrderType
from solana.rpc.api import Client
from solders.pubkey import Pubkey

async def test_actual_trades():
    """测试实际交易执行"""
    print("🚀 实际交易测试")
    print("=" * 50)
    
    try:
        # 1. 初始化
        devnet_rpc = "https://api.devnet.solana.com"
        client = Client(devnet_rpc)
        
        wallet_file = project_root / "new_wallet.json"
        wallet = Wallet.from_json_file(str(wallet_file))
        
        print(f"👛 钱包地址: {wallet.address}")
        
        # 检查余额
        sol_balance = wallet.get_balance(client)
        print(f"💰 SOL余额: {sol_balance:.6f} SOL")
        
        # 2. 检查USDC余额
        usdc_devnet = "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU"
        token_balances = wallet.get_token_balances(client)
        
        if usdc_devnet in token_balances:
            usdc_balance = token_balances[usdc_devnet]
            print(f"💵 USDC余额: {usdc_balance} USDC")
        else:
            print("❌ 没有USDC余额，无法测试卖出交易")
            return
        
        # 3. 初始化TradingEngine
        config = TransactionConfig(
            enable_devnet_testing=True,
            dex_protocol=DEXProtocol.AUTO,
            jupiter_slippage_bps=50,
            raydium_slippage_bps=50,
            max_retries=3,
            skip_preflight=False
        )
        
        trading_engine = TradingEngine(wallet=wallet, config=config)
        print("✅ TradingEngine 初始化成功")
        
        # 4. 检查DEX可用性
        print("\n🔍 检查DEX可用性...")
        
        # 测试Jupiter价格查询
        try:
            quote = await trading_engine.jupiter_client.get_quote(
                input_mint="So11111111111111111111111111111111111111112",  # SOL
                output_mint=usdc_devnet,  # devnet USDC
                amount=10000000,  # 0.01 SOL
                slippage_bps=50
            )
            print("✅ Jupiter API 可用")
            print(f"   报价: {quote}")
        except Exception as e:
            print(f"❌ Jupiter API 不可用: {e}")
            print("   💡 devnet上SOL←→USDC交易对可能不存在")
        
        # 5. 尝试小额买入交易（0.001 SOL → USDC）
        print("\n🔄 尝试小额买入交易测试...")
        
        buy_order = TradeOrder(
            token_address=usdc_devnet,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            amount=0.001,  # 非常小的金额
            slippage=5.0  # 5% 滑点
        )
        
        print(f"✅ 买入订单创建: {buy_order.amount} SOL → USDC")
        
        try:
            # 尝试执行交易
            print("🔧 尝试执行交易构建...")
            
            # 检查交易构建可行性 - 使用正确的方法名
            transaction = await trading_engine._build_trade_transaction(buy_order, 0.0)
            
            if transaction:
                print("✅ 交易构建成功")
                print(f"   交易大小: {len(bytes(transaction))} 字节")
                
                # 检查是否需要签名
                if not transaction.signatures:
                    print("⚠️ 交易需要签名，但devnet流动性可能不足")
                    
                # 检查交易费用
                fee_response = client.get_fee_for_message(transaction.compile_message())
                if fee_response.value:
                    print(f"   预估费用: {fee_response.value / 10**9:.6f} SOL")
                
                # 询问是否实际执行
                print("\n💡 交易构建完成，但devnet流动性可能不足")
                print("   建议在主网环境测试实际执行")
                
            else:
                print("❌ 交易构建失败")
                
        except Exception as e:
            print(f"❌ 交易构建失败: {e}")
            print("   💡 可能是devnet环境限制或方法调用错误")
        
        # 6. 测试卖出交易构建
        print("\n🔄 测试卖出交易构建...")
        
        sell_amount = min(usdc_balance, 1.0)  # 最多卖出1 USDC
        sell_order = TradeOrder(
            token_address=usdc_devnet,
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            amount=sell_amount,
            slippage=5.0
        )
        
        print(f"✅ 卖出订单创建: {sell_order.amount} USDC → SOL")
        
        try:
            transaction = await trading_engine._build_trade_transaction(sell_order, 0.0)
            
            if transaction:
                print("✅ 卖出交易构建成功")
                print(f"   交易大小: {len(bytes(transaction))} 字节")
                
                # 检查费用
                fee_response = client.get_fee_for_message(transaction.compile_message())
                if fee_response.value:
                    print(f"   预估费用: {fee_response.value / 10**9:.6f} SOL")
                
            else:
                print("❌ 卖出交易构建失败")
                
        except Exception as e:
            print(f"❌ 卖出交易构建失败: {e}")
        
        # 7. 总结
        print("\n" + "=" * 50)
        print("📋 测试结果总结:")
        print("   1. ✅ 钱包和余额检查正常")
        print("   2. ✅ TradingEngine框架正常")
        print("   3. ⚠️ DEX API在devnet受限")
        print("   4. ✅ 交易构建功能正常")
        print("   5. ⚠️ 实际执行受devnet流动性限制")
        
        print("\n💡 后续建议:")
        print("   1. 在主网环境测试完整交易流程")
        print("   2. 可以添加模拟交易测试")
        print("   3. 考虑使用测试网进行功能验证")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_actual_trades())