#!/usr/bin/env python3
"""
主网买卖代币测试代码
测试TradingEngine在主网上的买卖功能，使用USDC作为测试代币
"""

import asyncio
import sys
import os
import time
import logging
from decimal import Decimal

# 设置日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 关闭httpx的详细日志记录
logging.getLogger("httpx").setLevel(logging.WARNING)

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

from src.sol_meme_sdk.trading_engine import TradingEngine
from src.sol_meme_sdk.wallet import Wallet
from src.sol_meme_sdk.models import TransactionConfig, OrderSide


# 主网代币地址
MAINNET_TOKENS = {
    "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
    "SOL": "So11111111111111111111111111111111111111112",
    "RAY": "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",
    "BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    "WIF": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm"
}


async def test_price_check(trading_engine: TradingEngine, token_address: str, token_name: str):
    """测试价格查询功能"""
    print(f"\n🔍 查询 {token_name} 价格")
    print("-" * 30)
    
    try:
        price = await trading_engine.get_token_price(token_address)
        print(f"✅ {token_name} 价格: {price:.8f} SOL")
        
        # 换算成美元（假设1 SOL = 100美元）
        usd_price = price * 100
        print(f"   ≈ ${usd_price:.6f} USD")
        
        return price
    except Exception as e:
        print(f"❌ {token_name} 价格查询失败: {e}")
        raise  # 重新抛出异常，让调用方处理


async def test_buy_token(trading_engine: TradingEngine, token_address: str, token_name: str, amount_sol: float = 0.001):
    """测试买入代币功能"""
    print(f"\n🛒 测试买入 {token_name}")
    print("-" * 30)
    
    try:
        print(f"💸 准备花费 {amount_sol:.6f} SOL 买入 {token_name}")
        print("⏳ 正在执行买入交易...")
        
        start_time = time.time()
        
        # 执行买入
        result = await trading_engine.buy_token(
            token_address=token_address,
            amount_sol=amount_sol,
            slippage=1.0  # 1% 滑点容忍度
        )
        
        execution_time = time.time() - start_time
        
        print(f"✅ 买入成功！")
        print(f"   📦 获得代币数量: {result.executed_amount:.6f} {token_name}")
        print(f"   💰 平均执行价格: {result.executed_price:.8f} SOL")
        print(f"   🔗 交易哈希: {result.transaction_hash}")
        print(f"   ⏱️ 执行时间: {execution_time:.2f}秒")
        
        return result
        
    except Exception as e:
        print(f"❌ 买入 {token_name} 失败: {e}")
        raise  # 重新抛出异常，让调用方处理


async def test_sell_token(trading_engine: TradingEngine, token_address: str, token_name: str, amount_tokens: float = 0.1):
    """测试卖出代币功能"""
    print(f"\n💰 测试卖出 {token_name}")
    print("-" * 30)
    
    try:
        print(f"💸 准备卖出 {amount_tokens:.6f} {token_name}")
        print("⏳ 正在执行卖出交易...")
        
        start_time = time.time()
        
        # 执行卖出
        result = await trading_engine.sell_token(
            token_address=token_address,
            amount_tokens=amount_tokens,
            slippage=1.0  # 1% 滑点容忍度
        )
        
        execution_time = time.time() - start_time
        
        print(f"✅ 卖出成功！")
        print(f"   💰 获得SOL数量: {result.executed_amount:.6f} SOL")
        print(f"   📊 平均执行价格: {result.executed_price:.8f} SOL")
        print(f"   🔗 交易哈希: {result.transaction_hash}")
        print(f"   ⏱️ 执行时间: {execution_time:.2f}秒")
        
        return result
        
    except Exception as e:
        print(f"❌ 卖出 {token_name} 失败: {e}")
        raise  # 重新抛出异常，让调用方处理


async def test_wallet_balance(trading_engine: TradingEngine, token_address: str, token_name: str):
    """测试钱包余额查询"""
    print(f"\n👛 查询钱包余额")
    print("-" * 30)
    
    try:
        # 查询SOL余额
        sol_balance = await trading_engine._get_sol_balance()
        print(f"✅ SOL余额: {sol_balance:.6f} SOL")
        
        # 查询代币余额
        token_balance = await trading_engine._get_token_balance(token_address)
        print(f"✅ {token_name}余额: {token_balance:.6f} {token_name}")
        
        return {"sol": sol_balance, "token": token_balance}
        
    except Exception as e:
        print(f"❌ 余额查询失败: {e}")
        raise  # 重新抛出异常，让调用方处理


async def test_dex_selection(trading_engine: TradingEngine, token_address: str, token_name: str):
    """测试DEX选择功能"""
    print(f"\n🎯 测试DEX选择策略")
    print("-" * 30)
    
    try:
        # 获取最优DEX推荐
        recommendation = await trading_engine.get_optimal_dex(token_address, "buy")
        
        print(f"✅ 推荐DEX: {recommendation.get('recommended_dex', '未知')}")
        print(f"   📊 价格分析: {recommendation.get('price_analysis', {})}")
        print(f"   💧 流动性分析: {recommendation.get('liquidity_analysis', {})}")
        
        return recommendation
        
    except Exception as e:
        print(f"❌ DEX选择测试失败: {e}")
        raise  # 重新抛出异常，让调用方处理


async def comprehensive_trading_test(token_address: str, token_name: str, wallet_file: str):
    """综合交易测试 - 遇到错误立即停止"""
    print(f"🚀 开始 {token_name} 综合交易测试")
    print("=" * 50)
    
    test_results = {}
    
    try:
        # 1. 加载钱包
        wallet = Wallet.from_json_file(wallet_file)
        print(f"✅ 钱包加载成功 - 地址: {wallet.address}")
        test_results["wallet_loaded"] = True
        
        # 2. 创建交易配置（主网模式）
        tx_config = TransactionConfig(
            enable_devnet_testing=False,  # 主网模式
            dex_priority=["jupiter", "raydium"],  # DEX优先级
            jupiter_slippage_bps=100,  # 1%滑点
            raydium_slippage_bps=100
        )
        
        # 3. 初始化TradingEngine
        trading_engine = TradingEngine(wallet, tx_config)
        print(f"✅ 交易引擎初始化完成")
        print(f"   📡 网络: 主网")
        print(f"   🎯 DEX优先级: {tx_config.dex_priority}")
        
        # 打印RPC节点信息
        rpc_url = trading_engine._get_rpc_url()
        is_local_node = trading_engine._is_local_node()
        print(f"   🔗 RPC节点: {rpc_url}")
        print(f"   🏠 本地节点: {'是' if is_local_node else '否'}")
        
        test_results["engine_initialized"] = True
        
        # 4. 查询余额（前置条件检查）
        balance = await test_wallet_balance(trading_engine, token_address, token_name)
        test_results["balance"] = balance
        
        # 检查SOL余额是否足够
        if balance["sol"] < 0.01:
            print(f"❌ SOL余额不足: {balance['sol']:.6f} SOL < 0.01 SOL")
            print("⚠️  请确保钱包有足够的SOL余额再进行测试")
            test_results["error"] = "Insufficient SOL balance"
            return test_results
        
        print(f"✅ SOL余额充足: {balance['sol']:.6f} SOL")
        
        # 5. 查询价格
        price = await test_price_check(trading_engine, token_address, token_name)
        test_results["price"] = price
        
        # 6. DEX选择测试
        dex_selection = await test_dex_selection(trading_engine, token_address, token_name)
        test_results["dex_selection"] = dex_selection
        
        # 7. 买入测试（小额）
        buy_amount = min(0.001, balance["sol"] * 0.1)  # 最多使用10%的SOL
        print(f"💸 使用 {buy_amount:.6f} SOL 进行买入测试")
        
        buy_result = await test_buy_token(trading_engine, token_address, token_name, buy_amount)
        test_results["buy"] = buy_result
        
        # 等待交易确认
        print("⏳ 等待5秒确保交易确认...")
        await asyncio.sleep(5)
        
        # 8. 卖出测试（如果有余额）
        current_balance = await test_wallet_balance(trading_engine, token_address, token_name)
        test_results["current_balance"] = current_balance
        
        if current_balance["token"] > 0:
            # sell_amount = min(0.2, current_balance["token"] * 0.5)  # 最多卖出50%的代币
            sell_amount = current_balance["token"]  # 卖出全部代币进行测试
            print(f"💸 卖出 {sell_amount:.6f} {token_name} 进行卖出测试")
            
            sell_result = await test_sell_token(trading_engine, token_address, token_name, sell_amount)
            test_results["sell"] = sell_result
            
            # 等待交易确认
            print("⏳ 等待5秒确保交易确认...")
            await asyncio.sleep(5)
        else:
            print("⚠️  代币余额为0，跳过卖出测试")
        
        # 9. 最终余额查询
        final_balance = await test_wallet_balance(trading_engine, token_address, token_name)
        test_results["final_balance"] = final_balance
        
        print(f"\n🎉 {token_name} 综合测试完成！")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ {token_name} 测试失败: {e}")
        print("⚠️  测试已终止，不会继续执行后续步骤")
        test_results["error"] = str(e)
        test_results["failed"] = True
        
    return test_results


async def main():
    """主函数 - 改进的错误处理"""
    print("🔧 Sol Meme SDK 主网交易测试")
    print("=" * 50)
    
    # 钱包文件路径
    wallet_file = os.path.join(os.path.dirname(__file__), "../../new_wallet.json")
    
    if not os.path.exists(wallet_file):
        print("❌ 钱包文件不存在，请先创建钱包")
        print(f"   钱包文件路径: {wallet_file}")
        print("💡 请先运行钱包创建脚本生成钱包文件")
        return
    
    # 测试代币配置
    test_tokens = [
        (MAINNET_TOKENS["USDC"], "USDC"),
        # 可以添加更多测试代币
        # (MAINNET_TOKENS["RAY"], "RAY"),
        # (MAINNET_TOKENS["BONK"], "BONK"),
    ]
    
    all_results = {}
    
    for token_address, token_name in test_tokens:
        print(f"\n📋 测试代币: {token_name}")
        print(f"   🔗 地址: {token_address}")
        
        try:
            result = await comprehensive_trading_test(token_address, token_name, wallet_file)
            all_results[token_name] = result
            
            # 检查是否失败
            if result.get("failed"):
                print(f"\n⚠️  {token_name} 测试遇到错误，跳过后续测试")
                break
            
            # 测试间隔
            print("⏳ 等待3秒后进行下一个测试...")
            await asyncio.sleep(3)
            
        except Exception as e:
            print(f"❌ {token_name} 测试出现异常: {e}")
            all_results[token_name] = {"error": str(e), "failed": True}
            break  # 遇到异常立即停止
    
    # 测试总结
    print(f"\n📊 测试总结")
    print("=" * 50)
    
    success_count = 0
    failure_count = 0
    
    for token_name, result in all_results.items():
        print(f"\n{token_name}:")
        
        if result.get("failed"):
            failure_count += 1
            print(f"   ❌ 测试失败")
            if "error" in result:
                print(f"      错误信息: {result['error']}")
        elif "error" in result:
            failure_count += 1
            print(f"   ❌ 测试失败: {result['error']}")
        else:
            success_count += 1
            print("   ✅ 测试完成")
            
            # 显示交易详情
            if "buy" in result and result["buy"]:
                print(f"      🛒 买入交易: {result['buy'].transaction_hash}")
            if "sell" in result and result["sell"]:
                print(f"      💰 卖出交易: {result['sell'].transaction_hash}")
    
    print(f"\n📈 总体结果:")
    print(f"   成功: {success_count} 个测试")
    print(f"   失败: {failure_count} 个测试")
    
    if failure_count > 0:
        print("\n💡 提示:")
        print("   - 确保钱包有足够的SOL余额")
        print("   - 检查网络连接和RPC端点")
        print("   - 确认代币地址是否正确")
        print("   - 查看详细错误信息进行排查")


if __name__ == "__main__":
    # 运行测试
    asyncio.run(main())