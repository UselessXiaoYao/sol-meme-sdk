#!/usr/bin/env python3
"""
Raydium Devnet 交易示例
演示如何在Raydium Devnet上进行代币交易
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.sol_meme_sdk.raydium_client import RaydiumClient
from src.sol_meme_sdk.wallet import Wallet
from src.sol_meme_sdk.unified_config import get_config


class DevnetRaydiumTrader:
    """Devnet Raydium交易器"""
    
    def __init__(self):
        # 设置Devnet RPC端点
        self.devnet_rpc = "https://api.devnet.solana.com"
        
        # 初始化Raydium客户端（使用devnet）
        self.raydium_client = RaydiumClient(rpc_url=self.devnet_rpc, network="devnet")
        
        # Devnet上的代币地址
        self.sol_mint = "So11111111111111111111111111111111111111112"  # SOL mint地址
        self.usdc_devnet = "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU"  # Devnet USDC
        
    async def setup_wallet(self) -> Wallet:
        """设置测试钱包"""
        try:
            # 从环境变量或文件加载钱包
            wallet_file = project_root / "new_wallet.json"
            
            if wallet_file.exists():
                # 从文件加载钱包
                wallet = Wallet.from_json_file(str(wallet_file))
                print(f"✅ 从文件加载钱包: {wallet.address}")
            else:
                # 创建新钱包
                print("🆕 创建新的测试钱包...")
                wallet = Wallet()  # 使用默认构造函数创建新钱包
                
                # 保存钱包到文件
                wallet.save_to_json_file(str(wallet_file))
                print(f"✅ 新钱包已创建并保存: {wallet.address}")
            
            return wallet
            
        except Exception as e:
            print(f"❌ 钱包设置失败: {e}")
            raise
    
    async def check_wallet_balance(self, wallet: Wallet) -> float:
        """检查钱包余额"""
        try:
            # 创建同步客户端来获取余额
            from solana.rpc.api import Client
            sync_client = Client(self.raydium_client.rpc_url)
            balance = wallet.get_balance(sync_client)
            print(f"💰 钱包余额: {balance:.6f} SOL")
            return balance
        except Exception as e:
            print(f"❌ 检查余额失败: {e}")
            return 0
    
    async def airdrop_devnet_sol(self, wallet: Wallet, amount: float = 1.0) -> bool:
        """在Devnet上获取测试SOL"""
        try:
            print(f"🚀 正在请求Devnet空投: {amount} SOL...")
            
            # 转换为lamports (1 SOL = 1,000,000,000 lamports)
            lamports = int(amount * 1_000_000_000)
            
            # 发送空投请求
            airdrop_result = await self.raydium_client.client.request_airdrop(
                wallet.public_key, lamports
            )
            
            if airdrop_result.value:
                print(f"✅ 空投成功! 交易签名: {airdrop_result.value}")
                
                # 等待确认
                await asyncio.sleep(5)  # 给网络一些时间处理
                
                # 确认空投
                confirmed = await self.raydium_client.wait_for_confirmation(
                    str(airdrop_result.value)
                )
                
                if confirmed:
                    print("✅ 空投已确认!")
                    return True
                else:
                    print("⚠️ 空投确认超时")
                    return False
            else:
                print("❌ 空投请求失败")
                return False
                
        except Exception as e:
            print(f"❌ 空投失败: {e}")
            return False
    
    async def test_swap_quote(self, input_mint: str, output_mint: str, amount: int):
        """测试交易报价功能"""
        try:
            print(f"📊 测试交易报价...")
            print(f"  输入: {input_mint}")
            print(f"  输出: {output_mint}")
            print(f"  金额: {amount} lamports")
            
            quote = await self.raydium_client.get_swap_quote(
                input_mint=input_mint,
                output_mint=output_mint,
                amount=amount,
                slippage_bps=100,  # 1% 滑点
                tx_version="V0"
            )
            
            print(f"✅ 报价获取成功!")
            print(f"  输出金额: {quote['data'].get('outputAmount', 0)}")
            print(f"  价格影响: {quote['data'].get('priceImpactPct', 0):.4f}%")
            
            if 'routePlan' in quote['data']:
                print(f"  路由路径: {len(quote['data']['routePlan'])} 个池")
            
            return quote
            
        except Exception as e:
            print(f"❌ 报价测试失败: {e}")
            return None
    
    async def execute_test_swap(self, wallet: Wallet, amount: int = 1000000) -> bool:
        """执行测试交易（SOL -> Devnet USDC）"""
        try:
            print(f"🔄 执行测试交易...")
            
            # 检查余额
            balance = await self.check_wallet_balance(wallet)
            if balance < 0.01:  # 确保有足够的SOL
                print("⚠️ 余额不足，先进行空投...")
                if not await self.airdrop_devnet_sol(wallet, 1.0):
                    return False
            
            # 获取报价
            quote = await self.test_swap_quote(
                input_mint=self.sol_mint,
                output_mint=self.usdc_devnet,
                amount=amount
            )
            
            if not quote:
                return False
            
            print(f"🚀 执行交易...")
            
            # 执行交易
            swap_result = await self.raydium_client.swap_tokens(
                input_mint=self.sol_mint,
                output_mint=self.usdc_devnet,
                amount=amount,
                wallet=wallet,
                slippage_bps=100,  # 1% 滑点
                tx_version="V0",
                priority_fee_micro_lamports=10000  # 小额优先级费用
            )
            
            print(f"✅ 交易执行结果:")
            print(f"  交易签名: {swap_result.get('transaction_signature')}")
            print(f"  确认状态: {swap_result.get('confirmed')}")
            print(f"  输入金额: {swap_result.get('input_amount')}")
            print(f"  输出金额: {swap_result.get('output_amount')}")
            print(f"  状态: {swap_result.get('status')}")
            
            return swap_result.get('status') == 'success'
            
        except Exception as e:
            print(f"❌ 交易执行失败: {e}")
            return False
    
    async def run_complete_demo(self):
        """运行完整的演示流程"""
        try:
            print("🎯 Raydium Devnet 交易演示开始")
            print("=" * 50)
            
            # 连接客户端
            print("🔗 连接到Raydium客户端...")
            await self.raydium_client.connect()
            
            # 设置钱包
            print("👛 设置钱包...")
            wallet = await self.setup_wallet()
            
            # 检查余额
            print("💰 检查钱包余额...")
            balance = await self.check_wallet_balance(wallet)
            
            # 如果需要，获取空投
            if balance < 0.1:
                print("💸 余额不足，请求空投...")
                await self.airdrop_devnet_sol(wallet, 2.0)
            
            # 再次检查余额
            balance = await self.check_wallet_balance(wallet)
            
            # 测试报价功能
            print("📊 测试交易报价...")
            await self.test_swap_quote(
                input_mint=self.sol_mint,
                output_mint=self.usdc_devnet,
                amount=1000000  # 0.001 SOL
            )
            
            # 执行测试交易
            print("🔄 执行测试交易...")
            if balance > 0.01:  # 确保有足够的SOL
                success = await self.execute_test_swap(wallet, 1000000)  # 0.001 SOL
                
                if success:
                    print("🎉 演示成功完成!")
                else:
                    print("⚠️ 演示部分完成，交易可能因网络问题失败")
            else:
                print("⚠️ 余额不足，跳过实际交易")
            
            # 关闭连接
            print("🔌 关闭连接...")
            await self.raydium_client.close()
            
            print("✅ 演示结束")
            
        except Exception as e:
            print(f"❌ 演示失败: {e}")
            # 确保连接关闭
            try:
                await self.raydium_client.close()
            except:
                pass


async def main():
    """主函数"""
    trader = DevnetRaydiumTrader()
    await trader.run_complete_demo()


if __name__ == "__main__":
    # 运行演示
    asyncio.run(main())