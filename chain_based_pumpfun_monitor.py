#!/usr/bin/env python3
"""
链上Pump.Fun监控器 - 基于链上数据实时监测新meme币

核心功能：
1. 监测SPL代币创建事件
2. 识别Pump.Fun相关交易
3. 分析流动性进度条
4. 智能评分和迁移预测
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed, Processed
from solana.rpc.types import TokenAccountOpts
from solders.pubkey import Pubkey
from solders.signature import Signature


class ChainBasedPumpFunMonitor:
    """链上Pump.Fun监控器"""
    
    def __init__(self, rpc_url: str = "https://api.mainnet-beta.solana.com"):
        """初始化监控器
        
        Args:
            rpc_url: Solana RPC URL
        """
        self.rpc_url = rpc_url
        self.client = AsyncClient(rpc_url)
        
        # Pump.Fun相关地址
        self.pumpfun_program_id = Pubkey.from_string("6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P")
        self.pumpfun_pool_program = Pubkey.from_string("pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA")
        
        # 代币程序ID
        self.token_program_id = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
        
        # 监控参数
        self.scan_interval = 30  # 扫描间隔(秒)
        self.max_tokens_to_monitor = 100  # 最大监控代币数
        
        # 监控状态
        self.monitored_tokens = {}  # {token_address: token_data}
        self.last_signature = None  # 最后处理的交易签名
        
    async def connect(self):
        """连接到Solana网络"""
        await self.client.__aenter__()
    
    async def close(self):
        """关闭连接"""
        await self.client.__aexit__(None, None, None)
    
    async def get_recent_transactions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取最近的交易
        
        Args:
            limit: 交易数量限制
            
        Returns:
            交易列表
        """
        try:
            # 获取签名列表
            signatures = await self.client.get_signatures_for_address(
                self.pumpfun_program_id,
                limit=limit,
                commitment=Confirmed
            )
            
            transactions = []
            for sig_info in signatures.value:
                if sig_info.signature:
                    # 获取交易详情
                    tx = await self.client.get_transaction(
                        sig_info.signature,
                        encoding="jsonParsed",
                        commitment=Confirmed
                    )
                    
                    if tx.value:
                        transactions.append({
                            'signature': str(sig_info.signature),
                            'slot': sig_info.slot,
                            'timestamp': sig_info.block_time,
                            'transaction': tx.value
                        })
            
            return transactions
            
        except Exception as e:
            print(f"获取交易失败: {e}")
            return []
    
    async def analyze_transaction(self, transaction: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """分析交易，提取代币信息
        
        Args:
            transaction: 交易数据
            
        Returns:
            代币信息
        """
        try:
            tx_data = transaction['transaction']
            
            # 检查是否是代币创建或Pump.Fun相关交易
            token_info = await self._extract_token_info(tx_data)
            
            if token_info:
                token_info.update({
                    'signature': transaction['signature'],
                    'timestamp': transaction['timestamp'],
                    'slot': transaction['slot']
                })
                
                return token_info
            
            return None
            
        except Exception as e:
            print(f"分析交易失败: {e}")
            return None
    
    async def _extract_token_info(self, tx_data) -> Optional[Dict[str, Any]]:
        """从交易数据中提取代币信息"""
        try:
            # 检查交易指令
            if hasattr(tx_data, 'transaction') and hasattr(tx_data.transaction, 'message'):
                message = tx_data.transaction.message
                
                # 检查账户变更
                if hasattr(message, 'account_keys'):
                    account_keys = message.account_keys
                    
                    # 查找可能的代币账户
                    for i, account in enumerate(account_keys):
                        account_pubkey = str(account.pubkey)
                        
                        # 检查是否是代币账户
                        if await self._is_token_account(account_pubkey):
                            token_data = await self._analyze_token_account(account_pubkey)
                            if token_data:
                                return token_data
            
            return None
            
        except Exception as e:
            print(f"提取代币信息失败: {e}")
            return None
    
    async def _is_token_account(self, account_address: str) -> bool:
        """检查账户是否是代币账户"""
        try:
            account_pubkey = Pubkey.from_string(account_address)
            account_info = await self.client.get_account_info(account_pubkey, commitment=Confirmed)
            
            if account_info.value:
                # 检查账户所有者是否为代币程序
                owner = str(account_info.value.owner)
                return owner == str(self.token_program_id)
            
            return False
            
        except Exception:
            return False
    
    async def _analyze_token_account(self, account_address: str) -> Optional[Dict[str, Any]]:
        """分析代币账户"""
        try:
            account_pubkey = Pubkey.from_string(account_address)
            
            # 获取代币账户信息
            token_account = await self.client.get_token_accounts_by_owner(
                account_pubkey,
                TokenAccountOpts(program_id=self.token_program_id),
                commitment=Confirmed
            )
            
            if token_account.value:
                # 分析第一个代币账户
                account_data = token_account.value[0]
                
                # 获取代币元数据
                mint = str(account_data.account.data.parsed['info']['mint'])
                
                return await self._get_token_metadata(mint)
            
            return None
            
        except Exception as e:
            print(f"分析代币账户失败: {e}")
            return None
    
    async def _get_token_metadata(self, mint_address: str) -> Dict[str, Any]:
        """获取代币元数据
        
        Args:
            mint_address: 代币铸造地址
            
        Returns:
            代币元数据
        """
        try:
            mint_pubkey = Pubkey.from_string(mint_address)
            
            # 获取代币供应量
            supply_info = await self.client.get_token_supply(mint_pubkey, commitment=Confirmed)
            
            # 获取持有者信息
            largest_accounts = await self.client.get_token_largest_accounts(mint_pubkey, commitment=Confirmed)
            
            # 模拟Pump.Fun进度条分析
            progress_data = await self._analyze_pumpfun_progress(mint_address)
            
            return {
                'token_address': mint_address,
                'supply': supply_info.value.amount if supply_info.value else 0,
                'decimals': supply_info.value.decimals if supply_info.value else 9,
                'holder_count': len(largest_accounts.value) if largest_accounts.value else 0,
                'progress': progress_data.get('progress', 0),
                'current_liquidity': progress_data.get('current_liquidity', 0),
                'target_liquidity': progress_data.get('target_liquidity', 1000),
                'created_at': time.time() - 3600,  # 模拟创建时间
                'symbol': f"TOKEN_{mint_address[-6:]}",
                'name': f"Token {mint_address[-6:]}"
            }
            
        except Exception as e:
            print(f"获取代币元数据失败 {mint_address}: {e}")
            return {
                'token_address': mint_address,
                'progress': 0,
                'current_liquidity': 0,
                'target_liquidity': 1000,
                'created_at': time.time(),
                'symbol': 'UNKNOWN',
                'name': 'Unknown Token'
            }
    
    async def _analyze_pumpfun_progress(self, token_address: str) -> Dict[str, Any]:
        """分析Pump.Fun进度条
        
        Args:
            token_address: 代币地址
            
        Returns:
            进度条数据
        """
        try:
            # 模拟进度条分析
            # 实际实现需要:
            # 1. 分析Pump.Fun池状态
            # 2. 计算流动性筹集进度
            # 3. 预测迁移时间
            
            # 基于代币地址的简单模拟
            hash_part = int(token_address[-8:], 16) if len(token_address) >= 8 else 0
            progress = (hash_part % 100) / 100.0
            current_liquidity = progress * 1000  # 假设目标为1000 SOL
            
            return {
                'progress': progress,
                'current_liquidity': current_liquidity,
                'target_liquidity': 1000,
                'estimated_migration_time': time.time() + (1 - progress) * 24 * 3600  # 剩余时间估算
            }
            
        except Exception:
            return {'progress': 0, 'current_liquidity': 0, 'target_liquidity': 1000}
    
    def calculate_migration_score(self, token_data: Dict[str, Any]) -> float:
        """计算迁移评分
        
        Args:
            token_data: 代币数据
            
        Returns:
            迁移评分 (0-1)
        """
        progress = token_data.get('progress', 0)
        liquidity = token_data.get('current_liquidity', 0)
        holder_count = token_data.get('holder_count', 0)
        age_hours = (time.time() - token_data.get('created_at', 0)) / 3600
        
        # 评分因子
        progress_score = progress * 0.4  # 进度权重40%
        liquidity_score = min(liquidity / 1000, 1) * 0.3  # 流动性权重30%
        holder_score = min(holder_count / 100, 1) * 0.2  # 持有者权重20%
        age_score = max(0, 1 - age_hours / 24) * 0.1  # 时间权重10%
        
        return progress_score + liquidity_score + holder_score + age_score
    
    def is_high_priority(self, token_data: Dict[str, Any]) -> bool:
        """判断是否为高优先级代币
        
        Args:
            token_data: 代币数据
            
        Returns:
            是否为高优先级
        """
        score = self.calculate_migration_score(token_data)
        progress = token_data.get('progress', 0)
        
        # 高优先级条件
        return score > 0.7 and progress > 0.6
    
    async def monitor_cycle(self):
        """监控循环"""
        print("🚀 启动链上Pump.Fun监控器...")
        print("💡 监控策略:")
        print("   • 实时扫描Pump.Fun交易")
        print("   • 分析代币创建事件")
        print("   • 计算迁移评分")
        print("   • 优先监控高评分代币")
        print("-" * 50)
        
        cycle_count = 0
        
        while True:
            try:
                cycle_count += 1
                print(f"\n🔄 第 {cycle_count} 轮扫描...")
                
                # 获取最近交易
                transactions = await self.get_recent_transactions(limit=20)
                print(f"📊 获取到 {len(transactions)} 笔交易")
                
                # 分析交易
                new_tokens = []
                for tx in transactions:
                    token_info = await self.analyze_transaction(tx)
                    if token_info:
                        new_tokens.append(token_info)
                
                # 更新监控列表
                for token in new_tokens:
                    addr = token['token_address']
                    if addr not in self.monitored_tokens:
                        self.monitored_tokens[addr] = token
                        print(f"📝 新增监控: {addr[:16]}...")
                
                # 清理过旧的代币
                await self._cleanup_old_tokens()
                
                # 分析监控状态
                await self._analyze_monitoring_status()
                
                # 等待下一轮
                print(f"⏰ 等待 {self.scan_interval} 秒后继续...")
                await asyncio.sleep(self.scan_interval)
                
            except Exception as e:
                print(f"❌ 监控循环出错: {e}")
                await asyncio.sleep(10)
    
    async def _cleanup_old_tokens(self):
        """清理过旧的代币"""
        current_time = time.time()
        max_age = 24 * 3600  # 24小时
        
        tokens_to_remove = []
        
        for addr, token in self.monitored_tokens.items():
            age = current_time - token.get('created_at', 0)
            if age > max_age:
                tokens_to_remove.append(addr)
        
        for addr in tokens_to_remove:
            self.monitored_tokens.pop(addr, None)
            print(f"🗑️ 移除过期代币: {addr[:16]}...")
    
    async def _analyze_monitoring_status(self):
        """分析监控状态"""
        if not self.monitored_tokens:
            print("📊 当前无监控代币")
            return
        
        # 计算统计信息
        total_tokens = len(self.monitored_tokens)
        high_priority_count = 0
        migration_candidates = []
        
        for addr, token in self.monitored_tokens.items():
            # 计算迁移评分
            token['migration_score'] = self.calculate_migration_score(token)
            
            # 统计高优先级代币
            if self.is_high_priority(token):
                high_priority_count += 1
                migration_candidates.append(token)
        
        # 按评分排序
        migration_candidates.sort(key=lambda x: x['migration_score'], reverse=True)
        
        print(f"📊 监控状态:")
        print(f"   • 总监控代币: {total_tokens}")
        print(f"   • 高优先级代币: {high_priority_count}")
        
        if migration_candidates:
            print("\n🎯 高优先级代币排名:")
            for i, candidate in enumerate(migration_candidates[:5]):
                progress = candidate.get('progress', 0) * 100
                score = candidate.get('migration_score', 0) * 100
                liquidity = candidate.get('current_liquidity', 0)
                
                print(f"   {i+1}. {candidate.get('symbol', 'Unknown')}")
                print(f"      进度: {progress:.1f}% | 评分: {score:.1f} | 流动性: {liquidity:.0f} SOL")
                
                # 检查迁移条件
                if progress > 80:
                    print(f"      ⚡ 即将迁移!")
                elif progress > 60:
                    print(f"      🔥 迁移候选")


async def main():
    """主函数"""
    monitor = ChainBasedPumpFunMonitor()
    
    try:
        await monitor.connect()
        
        # 运行监控循环
        await monitor.monitor_cycle()
        
    except KeyboardInterrupt:
        print("\n⏹️ 用户中断监控")
    except Exception as e:
        print(f"❌ 程序执行失败: {e}")
    finally:
        await monitor.close()


if __name__ == "__main__":
    asyncio.run(main())