#!/usr/bin/env python3
"""
调试交易详情获取功能
直接测试获取指定交易哈希的详细信息
"""

import asyncio
import logging
from solana.rpc.api import Client
from solders.signature import Signature

# 设置日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 关闭httpx的详细日志记录
logging.getLogger("httpx").setLevel(logging.WARNING)

async def debug_transaction_details():
    """调试交易详情获取功能"""
    
    # 你的交易哈希
    signature = "3zGvkroEAWxP4RZoYGZrZPMW7qvujFWhnTrhGWSuSiCBiyPuSrS8iqxebCz5L2w3tVZ4UcWGzg8x6VbXAX6dFMWT"
    
    print(f"🔍 开始调试交易详情获取: {signature}")
    print("=" * 60)
    
    # 尝试使用公共RPC获取交易详情
    print("🔧 尝试使用公共RPC获取交易详情...")
    rpc_url = "https://api.mainnet-beta.solana.com"
    rpc_client = Client(rpc_url)
    
    try:
        # 1. 首先检查交易状态
        print("📊 步骤1: 检查交易状态")
        sig_obj = Signature.from_string(signature)
        status = rpc_client.get_signature_statuses([sig_obj])
        
        if status.value and len(status.value) > 0:
            sig_status = status.value[0]
            if sig_status is not None:
                print(f"✅ 交易状态: {sig_status}")
                if hasattr(sig_status, 'confirmation_status'):
                    print(f"   确认状态: {sig_status.confirmation_status}")
                if hasattr(sig_status, 'err') and sig_status.err:
                    print(f"   交易错误: {sig_status.err}")
        else:
            print("❌ 无法获取交易状态")
            return
        
        print()
        
        # 2. 获取详细交易信息
        print("📊 步骤2: 获取详细交易信息")
        tx_details = rpc_client.get_transaction(
            sig_obj,
            max_supported_transaction_version=0,
            encoding="jsonParsed",
            commitment="confirmed"
        )
        
        if tx_details.value:
            print("✅ 成功获取交易详情")
            print(f"   交易详情类型: {type(tx_details.value)}")
            
            # 打印交易详情的所有属性
            if hasattr(tx_details.value, '__dict__'):
                print(f"   交易详情属性: {list(tx_details.value.__dict__.keys())}")
            
            # 打印交易详情
            print("\n📋 交易详情:")
            print(f"   {tx_details.value}")
            
            # 使用与 TradingEngine 相同的解析逻辑
            print("\n🔍 按照 TradingEngine 格式解析交易详情:")
            tx = tx_details.value
            
            try:
                # 注意：tx 是 EncodedConfirmedTransactionWithStatusMeta 对象
                # 我们需要访问 tx.transaction 来获取 EncodedTransactionWithStatusMeta
                
                # 交易槽位信息
                if hasattr(tx, 'slot'):
                    slot = tx.slot
                    print(f"   🔄 交易槽位: {slot}")
                
                # 区块时间
                if hasattr(tx, 'block_time'):
                    block_time = tx.block_time
                    if block_time:
                        from datetime import datetime
                        dt = datetime.fromtimestamp(block_time)
                        print(f"   ⏰ 区块时间: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # 获取交易数据
                if hasattr(tx, 'transaction'):
                    tx_data = tx.transaction
                    
                    # 获取交易哈希
                    if hasattr(tx_data, 'signatures'):
                        signatures = tx_data.signatures
                        if signatures:
                            print(f"   🔗 交易哈希: {signatures[0]}")
                    
                    # 解析交易元数据
                    if hasattr(tx_data, 'meta'):
                        meta = tx_data.meta
                        
                        # 解析交易内容
                        print("   📋 交易类型分析:")
                        
                        # 从日志中提取详细的Swap信息
                        if hasattr(meta, 'log_messages'):
                            log_messages = meta.log_messages
                            swap_details_found = False
                            for log in log_messages:
                                # 查找Swap相关的详细信息
                                if 'SwapEvent' in log:
                                    import re
                                    # 提取Swap事件详情
                                    swap_match = re.search(r'SwapEvent\s*\{\s*dex:\s*(\w+),\s*amount_in:\s*(\d+),\s*amount_out:\s*(\d+)\s*\}', log)
                                    if swap_match:
                                        dex_name = swap_match.group(1)
                                        amount_in = int(swap_match.group(2))
                                        amount_out = int(swap_match.group(3))
                                        print(f"     💱 Swap事件: {dex_name} DEX")
                                        print(f"       输入: {amount_in:,} tokens")
                                        print(f"       输出: {amount_out:,} tokens")
                                        swap_details_found = True
                                        break
                                
                            # 如果没找到SwapEvent，尝试从其他日志中提取信息
                            if not swap_details_found:
                                for log in log_messages:
                                    if 'amount_in:' in log and 'amount_out:' in log:
                                        import re
                                        # 尝试多种格式
                                        amount_in_match = re.search(r'amount_in:\s*(\d+)', log)
                                        amount_out_match = re.search(r'amount_out:\s*(\d+)', log)
                                        if amount_in_match and amount_out_match:
                                            amount_in = int(amount_in_match.group(1))
                                            amount_out = int(amount_out_match.group(1))
                                            print(f"     💱 Swap详情: {amount_in:,} -> {amount_out:,}")
                                            
                                        # 查找代币信息
                                        token_in_match = re.search(r'So11111111111111111111111111111111111111112', log)
                                        token_out_match = re.search(r'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', log)
                                        if token_in_match and token_out_match:
                                            print(f"       代币对: SOL -> USDC")
                                            print(f"       汇率: 1 SOL ≈ {amount_out/amount_in:.2f} USDC")
                                        break
                        
                        # 交易费用
                        
                        # 交易费用
                        fee = getattr(meta, 'fee', '未知')
                        print(f"   💰 交易费用: {fee} lamports (约 {fee/1000000000:.6f} SOL)")
                        
                        # 交易状态
                        err = getattr(meta, 'err', None)
                        if err:
                            print(f"   ⚠️  交易错误: {err}")
                        else:
                            print("   ✅ 交易执行成功")
                        
                        # 计算单位消耗
                        compute_units = getattr(meta, 'compute_units_consumed', None)
                        if compute_units:
                            print(f"   ⚡ 计算单位消耗: {compute_units:,}")
                        
                        # 余额变化 - 正确显示交易费用
                        pre_balances = getattr(meta, 'pre_balances', [])
                        post_balances = getattr(meta, 'post_balances', [])
                        
                        if pre_balances and post_balances and len(pre_balances) == len(post_balances):
                            print(f"   💳 余额变化分析 (显示前3个账户):")
                            for i, (pre, post) in enumerate(zip(pre_balances[:3], post_balances[:3])):
                                if pre != post:
                                    change = post - pre
                                    # 第一个账户的变化应该等于交易费用
                                    if i == 0:
                                        print(f"     账户 {i} (签名者): {pre} -> {post} (交易费用: {change:+d} lamports)")
                                    else:
                                        print(f"     账户 {i}: {pre} -> {post} (变化: {change:+d})")
                        
                        # 代币余额变化
                        pre_tokens = getattr(meta, 'pre_token_balances', [])
                        post_tokens = getattr(meta, 'post_token_balances', [])
                        
                        if pre_tokens and post_tokens:
                            print("   📦 代币余额变化:")
                            
                            # 创建代币映射
                            token_map = {}
                            for token in pre_tokens + post_tokens:
                                if hasattr(token, 'mint'):
                                    mint = str(token.mint)  # 将 Pubkey 转换为字符串
                                    if mint not in token_map:
                                        token_map[mint] = {'pre': 0, 'post': 0}
                            
                            # 收集余额
                            for token in pre_tokens:
                                if hasattr(token, 'mint') and hasattr(token, 'ui_token_amount'):
                                    mint = str(token.mint)  # 将 Pubkey 转换为字符串
                                    amount = token.ui_token_amount.ui_amount or 0
                                    token_map[mint]['pre'] = amount
                            
                            for token in post_tokens:
                                if hasattr(token, 'mint') and hasattr(token, 'ui_token_amount'):
                                    mint = str(token.mint)  # 将 Pubkey 转换为字符串
                                    amount = token.ui_token_amount.ui_amount or 0
                                    token_map[mint]['post'] = amount
                            
                            # 显示代币变化
                            for mint, balances in token_map.items():
                                change = balances['post'] - balances['pre']
                                if abs(change) > 0.0000001:  # 只显示有意义的变动
                                    token_name = "USDC" if mint == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v" else mint[:8] + "..."
                                    print(f"     {token_name}: {balances['pre']:.6f} -> {balances['post']:.6f} ({change:+.6f})")
                        
                        # 交易日志
                        log_messages = getattr(meta, 'log_messages', [])
                        if log_messages:
                            print(f"   📝 交易日志数量: {len(log_messages)}")
                            for i, log in enumerate(log_messages[:2]):  # 只显示前2条
                                print(f"     日志 {i+1}: {log[:80]}...")
                    
                    # 交易消息
                    if hasattr(tx_data, 'message'):
                        message = tx_data.message
                        
                        # 账户数量
                        if hasattr(message, 'account_keys'):
                            accounts = message.account_keys
                            print(f"   🔑 交易涉及账户数量: {len(accounts)}")
                        
                        # 指令数量
                        if hasattr(message, 'instructions'):
                            instructions = message.instructions
                            print(f"   📋 交易指令数量: {len(instructions)}")
                        
                        # 最近区块哈希
                        if hasattr(message, 'recent_blockhash'):
                            blockhash = message.recent_blockhash
                            print(f"   🔗 最近区块哈希: {blockhash[:16]}...")
                        
            except Exception as e:
                print(f"   ❌ 解析交易详情失败: {e}")
                # 提供更多调试信息
                print(f"   交易详情对象类型: {type(tx)}")
                if hasattr(tx, '__dict__'):
                    print(f"   交易详情属性: {list(tx.__dict__.keys())}")
                if hasattr(tx, 'transaction') and hasattr(tx.transaction, '__dict__'):
                    print(f"   交易数据属性: {list(tx.transaction.__dict__.keys())}")
                print("   🔍 交易已确认，但详情解析失败")
        else:
            print("❌ 无法获取交易详情")
            
    except Exception as e:
        print(f"❌ 调试过程中出现错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("🔍 调试完成")

if __name__ == "__main__":
    asyncio.run(debug_transaction_details())