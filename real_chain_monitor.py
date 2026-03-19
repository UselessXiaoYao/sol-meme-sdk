#!/usr/bin/env python3
"""
真实链上监控器 - 集成真实Solana RPC进行Pump.Fun代币监控
"""

import asyncio
import time
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solana.rpc.types import TokenAccountOpts
from solders.pubkey import Pubkey
from solders.account import Account

from src.sol_meme_sdk.config import get_config
from src.sol_meme_sdk.multi_dex_client import MultiDexClient


class RealChainMonitor:
    """真实链上监控器类"""
    
    def __init__(self, rpc_url: Optional[str] = None):
        """初始化监控器
        
        Args:
            rpc_url: Solana RPC URL
        """
        self.rpc_url = rpc_url or get_config().solana_rpc_endpoint
        self.client = AsyncClient(self.rpc_url)
        self.dex_client = MultiDexClient(rpc_url)
        
        # 监控配置
        self.monitor_interval = 30  # 秒
        self.max_concurrent_requests = 10
        
        # 状态跟踪
        self.monitored_tokens: Dict[str, Dict[str, Any]] = {}
        self.last_scan_time = 0
        
        # Pump.Fun程序地址（已知的Pump.Fun相关地址）
        self.pumpfun_program_ids = [
            "6EF8rrecthR5DkZ8HtH7vPjJpZk5QnWJ8YV7jKqL9mNp",  # Pump.Fun主程序
            "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA",  # Pump AMM
        ]
    
    async def connect(self):
        """连接到Solana网络"""
        await self.client.__aenter__()
        await self.dex_client.connect()
        print(f"✅ 已连接到Solana网络: {self.rpc_url}")
    
    async def close(self):
        """关闭连接"""
        await self.dex_client.close()
        await self.client.__aexit__(None, None, None)
        print("✅ 已断开Solana网络连接")
    
    async def get_recent_transactions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取最近的交易记录
        
        Args:
            limit: 交易数量限制
            
        Returns:
            交易记录列表
        """
        try:
            # 获取最近的签名
            signatures = await self.client.get_recent_signatures_for_address(
                Pubkey.from_string(self.pumpfun_program_ids[0]), 
                limit=limit
            )
            
            transactions = []
            for sig_info in signatures.value:
                # 获取交易详情
                tx = await self.client.get_transaction(
                    sig_info.signature,
                    encoding="jsonParsed",
                    commitment=Confirmed
                )
                
                if tx.value:
                    transactions.append({
                        'signature': str(sig_info.signature),
                        'slot': tx.value.slot,
                        'timestamp': tx.value.block_time,
                        'transaction': tx.value.transaction
                    })
            
            return transactions
            
        except Exception as e:
            print(f"❌ 获取交易记录失败: {e}")
            return []
    
    async def detect_new_tokens_from_transactions(self, transactions: List[Dict[str, Any]]) -> List[str]:
        """从交易中检测新创建的代币
        
        Args:
            transactions: 交易记录列表
            
        Returns:
            新代币地址列表
        """
        new_tokens = []
        
        for tx_data in transactions:
            try:
                # 分析交易中的账户变更
                tx = tx_data['transaction']
                
                # 检查是否包含代币创建相关的指令
                for instruction in tx.message.instructions:
                    # 检查是否包含initialize_mint指令（代币创建）
                    if hasattr(instruction, 'program_id'):
                        program_id = str(instruction.program_id)
                        
                        # 如果是代币程序
                        if program_id == "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA":
                            # 检查是否包含mint账户
                            accounts = instruction.accounts
                            if len(accounts) >= 1:
                                mint_account = str(accounts[0])
                                
                                # 验证这是否是一个有效的SPL代币
                                if await self.validate_spl_token(mint_account):
                                    if mint_account not in self.monitored_tokens:
                                        new_tokens.append(mint_account)
                                        print(f"🎯 检测到新代币: {mint_account[:8]}...{mint_account[-8:]}")
            
            except Exception as e:
                print(f"❌ 分析交易失败: {e}")
        
        return new_tokens
    
    async def validate_spl_token(self, token_address: str) -> bool:
        """验证是否为有效的SPL代币
        
        Args:
            token_address: 代币地址
            
        Returns:
            是否为有效SPL代币
        """
        try:
            # 获取代币mint账户信息
            mint_account = await self.client.get_account_info(
                Pubkey.from_string(token_address),
                commitment=Confirmed
            )
            
            if not mint_account.value:
                return False
            
            # 检查账户所有者是否为代币程序
            owner = str(mint_account.value.owner)
            if owner != "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA":
                return False
            
            # 检查账户数据长度（SPL代币mint账户有固定结构）
            if len(mint_account.value.data) < 82:  # Mint账户最小长度
                return False
            
            return True
            
        except Exception:
            return False
    
    async def get_token_holders(self, token_address: str) -> List[Dict[str, Any]]:
        """获取代币持有者信息
        
        Args:
            token_address: 代币地址
            
        Returns:
            持有者信息列表
        """
        try:
            # 获取代币账户列表
            token_accounts = await self.client.get_token_accounts_by_owner(
                Pubkey.from_string(token_address),
                TokenAccountOpts(
                    mint=Pubkey.from_string(token_address),
                    program_id=Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
                ),
                commitment=Confirmed
            )
            
            holders = []
            for account in token_accounts.value:
                account_info = account.account
                holders.append({
                    'address': str(account.pubkey),
                    'amount': account_info.data.parsed['info']['tokenAmount']['amount'],
                    'decimals': account_info.data.parsed['info']['tokenAmount']['decimals']
                })
            
            return holders
            
        except Exception as e:
            print(f"❌ 获取持有者信息失败: {e}")
            return []
    
    async def estimate_liquidity_progress(self, token_address: str) -> Dict[str, Any]:
        """估算流动性进度
        
        Args:
            token_address: 代币地址
            
        Returns:
            进度估算结果
        """
        try:
            # 获取持有者信息
            holders = await self.get_token_holders(token_address)
            
            if not holders:
                return {'progress': 0.0, 'holders_count': 0, 'total_supply': 0}
            
            # 估算总供应量（基于持有者分布）
            total_supply = sum(int(h['amount']) for h in holders)
            
            # 分析持有者分布
            holders_count = len(holders)
            
            # 基于持有者数量和分布估算进度
            # 经验公式：持有者越多，进度越高
            if holders_count < 10:
                progress = 0.1
            elif holders_count < 50:
                progress = 0.3
            elif holders_count < 100:
                progress = 0.5
            elif holders_count < 200:
                progress = 0.7
            else:
                progress = 0.85
            
            # 考虑大额持有者的影响
            large_holders = [h for h in holders if int(h['amount']) > total_supply * 0.01]
            if len(large_holders) > 3:
                progress = min(progress + 0.1, 0.95)
            
            return {
                'progress': progress,
                'holders_count': holders_count,
                'total_supply': total_supply,
                'large_holders_count': len(large_holders)
            }
            
        except Exception as e:
            print(f"❌ 估算流动性进度失败: {e}")
            return {'progress': 0.0, 'holders_count': 0, 'total_supply': 0}
    
    async def check_token_on_dex(self, token_address: str) -> Dict[str, Any]:
        """检查代币是否在DEX上有流动性池
        
        Args:
            token_address: 代币地址
            
        Returns:
            DEX状态信息
        """
        try:
            # 这里需要实现实际的DEX池检测逻辑
            # 暂时使用模拟数据
            
            # 模拟检测Raydium池
            raydium_pools = await self.search_raydium_pools(token_address)
            
            # 模拟检测Meteora池
            meteora_pools = await self.search_meteora_pools(token_address)
            
            dex_status = {
                'on_raydium': len(raydium_pools) > 0,
                'on_meteora': len(meteora_pools) > 0,
                'raydium_pools': raydium_pools,
                'meteora_pools': meteora_pools,
                'total_liquidity': 0
            }
            
            # 计算总流动性
            if dex_status['on_raydium']:
                dex_status['total_liquidity'] += sum(pool.get('liquidity', 0) for pool in raydium_pools)
            if dex_status['on_meteora']:
                dex_status['total_liquidity'] += sum(pool.get('liquidity', 0) for pool in meteora_pools)
            
            return dex_status
            
        except Exception as e:
            print(f"❌ 检查DEX状态失败: {e}")
            return {'on_raydium': False, 'on_meteora': False, 'total_liquidity': 0}
    
    async def search_raydium_pools(self, token_address: str) -> List[Dict[str, Any]]:
        """搜索Raydium池（模拟实现）
        
        Args:
            token_address: 代币地址
            
        Returns:
            池信息列表
        """
        # 这里需要集成真实的Raydium API
        # 暂时返回空列表
        return []
    
    async def search_meteora_pools(self, token_address: str) -> List[Dict[str, Any]]:
        """搜索Meteora池（模拟实现）
        
        Args:
            token_address: 代币地址
            
        Returns:
            池信息列表
        """
        # 这里需要集成真实的Meteora API
        # 暂时返回空列表
        return []
    
    async def score_token(self, token_address: str) -> Dict[str, Any]:
        """对代币进行评分
        
        Args:
            token_address: 代币地址
            
        Returns:
            评分结果
        """
        try:
            # 获取流动性进度
            progress_data = await self.estimate_liquidity_progress(token_address)
            
            # 检查DEX状态
            dex_status = await self.check_token_on_dex(token_address)
            
            # 计算各项评分
            progress_score = progress_data['progress'] * 100
            holders_score = min(progress_data['holders_count'] / 10, 10)  # 最大10分
            dex_score = 10 if dex_status['total_liquidity'] > 1000 else 0
            
            # 综合评分
            total_score = (progress_score * 0.4 + 
                         holders_score * 0.3 + 
                         dex_score * 0.3)
            
            # 判断状态
            if dex_status['total_liquidity'] >= 1000:
                status = "已迁移"
                priority = "低"
            elif progress_data['progress'] >= 0.8:
                status = "即将打满"
                priority = "高"
            else:
                status = "监控中"
                priority = "中"
            
            return {
                'token_address': token_address,
                'progress': progress_data['progress'],
                'holders_count': progress_data['holders_count'],
                'total_supply': progress_data['total_supply'],
                'on_dex': dex_status['on_raydium'] or dex_status['on_meteora'],
                'total_liquidity': dex_status['total_liquidity'],
                'progress_score': progress_score,
                'holders_score': holders_score,
                'dex_score': dex_score,
                'total_score': total_score,
                'status': status,
                'priority': priority,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ 代币评分失败: {e}")
            return {
                'token_address': token_address,
                'progress': 0.0,
                'holders_count': 0,
                'total_score': 0,
                'status': '错误',
                'priority': '低'
            }
    
    async def scan_new_tokens(self) -> List[Dict[str, Any]]:
        """扫描新代币
        
        Returns:
            新代币评分结果列表
        """
        print(f"🔍 开始扫描新代币...")
        
        try:
            # 获取最近的交易
            transactions = await self.get_recent_transactions(limit=50)
            
            # 检测新代币
            new_tokens = await self.detect_new_tokens_from_transactions(transactions)
            
            # 对新代币进行评分
            scored_tokens = []
            for token_address in new_tokens:
                score_result = await self.score_token(token_address)
                scored_tokens.append(score_result)
                
                # 更新监控列表
                self.monitored_tokens[token_address] = score_result
            
            print(f"✅ 扫描完成，发现 {len(new_tokens)} 个新代币")
            return scored_tokens
            
        except Exception as e:
            print(f"❌ 扫描失败: {e}")
            return []
    
    async def monitor_priority_tokens(self) -> List[Dict[str, Any]]:
        """监控高优先级代币
        
        Returns:
            高优先级代币列表
        """
        priority_tokens = []
        
        for token_address, token_data in self.monitored_tokens.items():
            if token_data.get('priority') == '高':
                # 重新评分以获取最新状态
                updated_score = await self.score_token(token_address)
                priority_tokens.append(updated_score)
                
                # 更新数据
                self.monitored_tokens[token_address] = updated_score
        
        return priority_tokens
    
    async def run_monitoring_cycle(self):
        """运行一个监控周期"""
        print(f"\n🔄 开始监控周期 ({datetime.now().strftime('%H:%M:%S')})")
        
        # 扫描新代币
        new_tokens = await self.scan_new_tokens()
        
        # 监控高优先级代币
        priority_tokens = await self.monitor_priority_tokens()
        
        # 输出结果
        if new_tokens:
            print(f"\n🎯 新发现代币 ({len(new_tokens)} 个):")
            for token in new_tokens:
                print(f"   {token['token_address'][:8]}...{token['token_address'][-8:]} - "
                      f"进度: {token['progress']:.1%} - 评分: {token['total_score']:.1f} - "
                      f"状态: {token['status']}")
        
        if priority_tokens:
            print(f"\n🚨 高优先级代币 ({len(priority_tokens)} 个):")
            for token in priority_tokens:
                print(f"   {token['token_address'][:8]}...{token['token_address'][-8:]} - "
                      f"进度: {token['progress']:.1%} - 评分: {token['total_score']:.1f} - "
                      f"流动性: {token['total_liquidity']} SOL")
        
        print(f"✅ 监控周期完成，{len(self.monitored_tokens)} 个代币在监控中")
    
    async def start_continuous_monitoring(self, duration_minutes: int = 60):
        """开始持续监控
        
        Args:
            duration_minutes: 监控持续时间（分钟）
        """
        print(f"🚀 开始持续监控，持续时间: {duration_minutes} 分钟")
        print(f"📡 使用RPC: {self.rpc_url}")
        
        start_time = time.time()
        cycle_count = 0
        
        try:
            while time.time() - start_time < duration_minutes * 60:
                cycle_count += 1
                print(f"\n{'='*60}")
                print(f"📊 监控周期 #{cycle_count}")
                print(f"⏰ 已运行: {(time.time() - start_time) / 60:.1f} 分钟")
                
                await self.run_monitoring_cycle()
                
                # 等待下一个周期
                print(f"⏳ 等待 {self.monitor_interval} 秒后继续...")
                await asyncio.sleep(self.monitor_interval)
                
        except KeyboardInterrupt:
            print("\n⏹️  监控被用户中断")
        except Exception as e:
            print(f"\n❌ 监控出错: {e}")
        finally:
            print(f"\n📊 监控统计:")
            print(f"   总周期数: {cycle_count}")
            print(f"   监控代币数: {len(self.monitored_tokens)}")
            print(f"   总运行时间: {(time.time() - start_time) / 60:.1f} 分钟")


async def main():
    """主函数"""
    monitor = RealChainMonitor()
    
    try:
        await monitor.connect()
        
        # 测试网络连接
        print("🔗 测试网络连接...")
        version = await monitor.client.get_version()
        print(f"✅ Solana节点版本: {version.value}")
        
        # 开始持续监控（10分钟测试）
        await monitor.start_continuous_monitoring(duration_minutes=10)
        
    except Exception as e:
        print(f"❌ 监控启动失败: {e}")
    finally:
        await monitor.close()


if __name__ == "__main__":
    asyncio.run(main())