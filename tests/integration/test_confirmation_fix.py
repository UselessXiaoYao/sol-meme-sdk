#!/usr/bin/env python3
"""
测试交易确认逻辑修复 - 使用本地RPC节点
"""

import asyncio
import sys
import os
import logging

# 首先设置环境变量，确保在导入任何模块之前生效
local_env_file = os.path.join(os.path.dirname(__file__), ".env.local")
if os.path.exists(local_env_file):
    # 直接读取并设置环境变量
    with open(local_env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
    
    print(f"✅ 已设置本地环境变量: {local_env_file}")
    print(f"🔧 RPC节点: {os.getenv('SOLANA_RPC_ENDPOINT', '默认')}")
    print(f"🔧 网络类型: {os.getenv('SOLANA_NETWORK', 'mainnet-beta')}")
else:
    print("⚠️  未找到本地环境变量文件，使用默认配置")

# 设置日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

from src.sol_meme_sdk.trading_engine import TradingEngine
from src.sol_meme_sdk.wallet import Wallet
from src.sol_meme_sdk.models import TransactionConfig


async def test_multiple_transactions():
    """测试多个交易哈希的确认逻辑"""
    print("🔧 批量测试交易确认逻辑")
    print("=" * 50)
    
    # 加载钱包
    wallet_file = os.path.join(os.path.dirname(__file__), "new_wallet.json")
    
    if not os.path.exists(wallet_file):
        print("❌ 钱包文件不存在")
        print(f"   钱包文件路径: {wallet_file}")
        return
    
    try:
        wallet = Wallet.from_json_file(wallet_file)
        print(f"✅ 钱包加载成功 - 地址: {wallet.address}")
        
        # 创建交易配置
        tx_config = TransactionConfig(
            enable_devnet_testing=False  # 主网模式
        )
        
        # 初始化交易引擎
        trading_engine = TradingEngine(wallet, tx_config)
        print("✅ 交易引擎初始化完成")
        
        # 用户提供的交易哈希列表
        tx_hashes = [
            "AXGZn4Sq2mV3Cep3AgtiUYgaLK7WMFJPDzKRqbFg2sDGXanrzx2SQF9esLe2vxGVGM98hb7i86cjqmQFHhGziLZ",
            "5km7XfKnzEZziaEVVevss8B3yG1he9cFVtWbcFWo5y2oV7Qiim7pAqhwkpNaCtrbHeJfZr9CCi2gz25EUVEQ8pnM",
            "5X3maj4PvoEiN2zbEE5zi1YsRFbjvwH1eX3bYdBKr7XeG7mU8en1cvw2NYykGfoZQhH6kMDqjpZdnFCB4h2hiqUZ",
            "3QLrG9ja6yaduKp9JqpXtHrodGwkvcSwEhFCgrNwVieis1JaBUQB1ac53yDkrNnYCjRLqBynTUFFnEVVLKWoLhR6",
            "5KxLj4iLpSoPDZeGDsMpzAbSFYoV6WPPH1QmAXrZA5jhTkYrcFAJdZwhr3rmkbWC6cggfTqmrUzqakcyUivMTge1",
            "2ZTnhEZ6zqx2kJQbqdQB5aGyuJ7H43pnknQpEDeqVRBeLPgwTpinwFr2EMPNK1YcThbCLcGuT1XCzUU9iR4cpmqC",
            "3aWZdz74Bo3dL7VFUAQsFn3XLnz5trRDj3zF3MKLrrBPC9sBye3riPhD4chas6ChQJg3FyqeqMM5KtcNdu3Vj1R9"
        ]
        
        print(f"📋 测试 {len(tx_hashes)} 个交易哈希")
        print("-" * 50)
        
        results = []
        
        for i, tx_hash in enumerate(tx_hashes, 1):
            print(f"\n🔍 测试交易 {i}/{len(tx_hashes)}:")
            print(f"   哈希: {tx_hash}")
            print(f"   开始检查确认状态...")
            
            try:
                # 首先直接检查交易状态，获取更多信息
                try:
                    from solana.rpc.api import Client
                    rpc_client = trading_engine._get_rpc_client()
                    from solders.signature import Signature
                    signature = Signature.from_string(tx_hash)
                    
                    # 直接检查交易状态
                    status = rpc_client.get_signature_statuses([signature])
                    print(f"   直接检查状态: {status}")
                    
                    if status.value and len(status.value) > 0:
                        sig_status = status.value[0]
                        if sig_status is None:
                            print("   ⚠️  RPC返回状态为None")
                        else:
                            print(f"   ℹ️  交易状态详情: {sig_status}")
                            if hasattr(sig_status, 'confirmation_status'):
                                print(f"   📊 确认状态: {sig_status.confirmation_status}")
                            if hasattr(sig_status, 'err') and sig_status.err:
                                print(f"   ❌ 交易错误: {sig_status.err}")
                    
                except Exception as e:
                    print(f"   🔍 状态检查失败: {e}")
                
                # 然后使用等待确认逻辑
                confirmed = await trading_engine._wait_for_confirmation(tx_hash, timeout=15.0)
                
                results.append({
                    'hash': tx_hash,
                    'confirmed': confirmed,
                    'index': i
                })
                
                print(f"   确认状态: {'✅ 已确认' if confirmed else '❌ 未确认/超时'}")
                
                # 如果连续3个交易都失败，提前退出测试
                recent_failures = sum(1 for r in results[-3:] if not r['confirmed'])
                if recent_failures >= 3:
                    print(f"\n⚠️  连续{recent_failures}个交易失败，提前终止测试")
                    break
                    
            except Exception as e:
                print(f"   ❌ 测试交易 {i} 出现严重错误: {e}")
                import traceback
                traceback.print_exc()
                
                # 记录失败结果
                results.append({
                    'hash': tx_hash,
                    'confirmed': False,
                    'index': i,
                    'error': str(e)
                })
                
                # 如果出现严重错误，询问是否继续
                if i < len(tx_hashes):
                    print(f"\n⚠️  出现严重错误，是否继续测试剩余 {len(tx_hashes) - i} 个交易？")
                    print("   输入 'y' 继续，其他任意键退出: ", end="")
                    
                    # 在实际环境中，这里需要用户输入判断
                    # 为了自动化测试，我们选择继续但记录错误
                    print("自动继续...")
        
        # 汇总结果
        print(f"\n📊 测试结果汇总:")
        print("=" * 50)
        
        confirmed_count = sum(1 for r in results if r['confirmed'])
        failed_count = len(results) - confirmed_count
        
        print(f"✅ 已确认交易: {confirmed_count}/{len(results)}")
        print(f"❌ 未确认/超时交易: {failed_count}/{len(results)}")
        
        if confirmed_count > 0:
            print(f"\n📈 已确认交易详情:")
            for r in results:
                if r['confirmed']:
                    print(f"   {r['index']}. {r['hash']}")
        
        if failed_count > 0:
            print(f"\n📉 未确认交易详情:")
            for r in results:
                if not r['confirmed']:
                    print(f"   {r['index']}. {r['hash']}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """主函数"""
    print("🚀 开始批量交易确认测试")
    
    try:
        await test_multiple_transactions()
    except KeyboardInterrupt:
        print("\n⏹️  测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试出现异常: {e}")
    
    print("\n🎉 测试完成")


if __name__ == "__main__":
    asyncio.run(main())