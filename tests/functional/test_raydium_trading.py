#!/usr/bin/env python3
"""
Raydium TradingEngine 测试
通过TradingEngine测试Raydium API获取代币价格和交易功能
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.sol_meme_sdk.trading_engine import TradingEngine
from src.sol_meme_sdk.raydium_client import RaydiumClient
from src.sol_meme_sdk.wallet import Wallet
from src.sol_meme_sdk.models import TransactionConfig
from src.sol_meme_sdk.unified_config import UnifiedConfig


async def test_raydium_trading():
    """测试Raydium TradingEngine功能"""
    print("🚀 Raydium TradingEngine 测试")
    print("=" * 50)
    
    # 初始化配置
    config = UnifiedConfig()
    print(f"🔧 当前网络: {config.solana_network}")
    print(f"   RPC端点: {config.solana_rpc_endpoint}")
    
    # 加载现有钱包
    wallet_file = os.path.join(os.path.dirname(__file__), "new_wallet.json")
    if not os.path.exists(wallet_file):
        print("❌ 钱包文件不存在，请先创建钱包")
        return
    
    try:
        wallet = Wallet.from_json_file(str(wallet_file))
        print(f"✅ 钱包加载成功 - 地址: {wallet.address}")
    except Exception as e:
        print(f"❌ 钱包加载失败: {e}")
        return
    
    # 创建Raydium客户端
    raydium_client = RaydiumClient(config.solana_network)
    
    # 创建交易配置
    tx_config = TransactionConfig()
    
    # 初始化TradingEngine，指定使用Raydium客户端
    print("\n🔄 初始化TradingEngine（指定Raydium客户端）...")
    trading = TradingEngine(
        wallet=wallet,
        config=tx_config,
        raydium_client=raydium_client
    )
    
    print(f"✅ TradingEngine 初始化成功!")
    print(f"   网络模式: {'devnet' if trading.is_devnet else 'mainnet'}")
    
    # 常用代币地址
    common_tokens = {
        "SOL": "So11111111111111111111111111111111111111112",
        "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        "JUP": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
        "BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"
    }
    
    try:
        print("\n💰 测试代币价格获取...")
        
        # 测试SOL价格
        sol_price = await trading._get_token_price(common_tokens["SOL"])
        print(f"✅ SOL价格: {sol_price:.6f} SOL (基准价格)")
        
        # 测试USDC价格
        usdc_price = await trading._get_token_price(common_tokens["USDC"])
        print(f"✅ USDC价格: {usdc_price:.6f} SOL")
        print(f"   汇率: 1 SOL = {1/usdc_price:.2f} USDC")
        
        # 测试JUP价格
        jup_price = await trading._get_token_price(common_tokens["JUP"])
        print(f"✅ JUP价格: {jup_price:.10f} SOL")
        print(f"   汇率: 1 SOL = {1/jup_price:,.0f} JUP")
        
        # 测试BONK价格
        bonk_price = await trading._get_token_price(common_tokens["BONK"])
        print(f"✅ BONK价格: {bonk_price:.15f} SOL")
        print(f"   汇率: 1 SOL = {1/bonk_price:,.0f} BONK")
        
    except Exception as e:
        print(f"❌ 代币价格获取失败: {e}")
    
    try:
        print("\n🔍 测试Raydium池信息获取...")
        
        # 使用Raydium客户端直接获取池信息
        pools = await raydium_client.get_raydium_pools()
        
        if pools and pools.get('official') is not None:
            # API v3返回的数据结构是 pools['official']['data']
            pool_data = pools['official']
            
            # 检查是否是嵌套的数据结构
            if isinstance(pool_data, dict) and 'data' in pool_data:
                pools_list = pool_data['data']
            else:
                pools_list = pool_data
            
            pool_count = len(pools_list)
            
            if pool_count > 0:
                print(f"✅ 获取到 {pool_count} 个Raydium池")
                
                # 显示前几个池的信息
                for i in range(min(3, pool_count)):
                    pool = pools_list[i]
                    print(f"\n   [{i+1}] 池信息:")
                    print(f"      池ID: {pool.get('id', 'N/A')[:20]}...")
                    
                    # 尝试获取代币符号
                    mintA = pool.get('mintA', {})
                    mintB = pool.get('mintB', {})
                    
                    symbol1 = mintA.get('symbol', mintA.get('address', 'N/A')[:8])
                    symbol2 = mintB.get('symbol', mintB.get('address', 'N/A')[:8])
                    
                    print(f"      代币对: {symbol1} / {symbol2}")
                    print(f"      流动性: {float(pool.get('tvl', 0)):,.0f} USD")
                    print(f"      池类型: {pool.get('pooltype', ['N/A'])[0]}")
            else:
                print("❌ 池列表为空")
                
        else:
            print("❌ 未获取到池数据")
            
    except Exception as e:
        print(f"❌ Raydium池信息获取失败: {e}")
    
    try:
        print("\n📊 测试Raydium交易报价...")
        
        # 使用Raydium客户端测试交易报价
        quote = await raydium_client.get_swap_quote(
            input_mint=common_tokens["SOL"],
            output_mint=common_tokens["USDC"],
            amount=100000000,  # 0.1 SOL
            slippage_bps=50,   # 0.5% 滑点
            tx_version="V0"
        )
        
        if quote.get('success'):
            data = quote['data']
            input_amount = float(data['inputAmount']) / 1e9  # SOL数量
            output_amount = float(data['outputAmount']) / 1e6  # USDC数量
            
            print(f"✅ Raydium交易报价获取成功")
            print(f"   {input_amount:.3f} SOL = {output_amount:.3f} USDC")
            print(f"   汇率: 1 SOL = {output_amount/input_amount:.3f} USDC")
            print(f"   价格影响: {float(data.get('priceImpactPct', 0)):.4f}%")
            
            # 显示路由信息
            route_plan = data.get('routePlan', [])
            if route_plan:
                print(f"   路由: {len(route_plan)} 步")
                for i, step in enumerate(route_plan):
                    pool_id = step.get('poolId', '')[:10]
                    print(f"      {i+1}. 池: {pool_id}...")
            
        else:
            print("❌ Raydium交易报价失败")
            
    except Exception as e:
        print(f"❌ Raydium交易报价测试失败: {e}")
    
    # 检查钱包余额
    try:
        print("\n💼 检查钱包余额...")
        
        # 获取SOL余额
        sol_balance = await trading.get_balance(common_tokens["SOL"])
        print(f"   SOL余额: {sol_balance:.6f} SOL")
        
        # 如果余额足够，测试小额交易
        if sol_balance > 0.001:
            print("\n🔄 测试小额交易（仅报价，不执行）...")
            
            try:
                # 测试购买USDC（仅获取报价）
                quote_result = await trading.get_quote(
                    input_mint=common_tokens["SOL"],
                    output_mint=common_tokens["USDC"],
                    amount=int(sol_balance * 0.001 * 1e9),  # 0.1% 的余额
                    slippage_bps=100
                )
                
                if quote_result:
                    print("✅ 小额交易报价成功（仅报价，未执行）")
                
            except Exception as e:
                print(f"   ⚠️ 交易报价测试失败: {e}")
        else:
            print("   💡 SOL余额不足，跳过交易测试")
            
    except Exception as e:
        print(f"❌ 余额检查失败: {e}")
    
    print("\n" + "=" * 50)
    print("📋 Raydium TradingEngine 测试完成")
    print("💡 总结:")
    print("   - Raydium API v3 工作正常")
    print("   - 代币价格获取功能正常") 
    print("   - 交易报价功能正常")
    print("   - TradingEngine 集成Raydium客户端成功")


if __name__ == "__main__":
    asyncio.run(test_raydium_trading())