#!/usr/bin/env python3
"""
Pump.Fun自动扫描器 - 基于链上数据监测新meme币

核心功能：
1. 监测新创建的meme币地址
2. 分析进度条（流动性筹集进度）
3. 基于发布时间和流动性评分
4. 优先监控即将迁移的代币
5. 在迁移后第一时间执行买入
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solana.rpc.types import TokenAccountOpts
from solders.pubkey import Pubkey
from solders.rpc.responses import GetProgramAccountsResp


class PumpFunAutoScanner:
    """Pump.Fun自动扫描器"""
    
    def __init__(self, rpc_url: str = "https://api.mainnet-beta.solana.com"):
        """初始化扫描器
        
        Args:
            rpc_url: Solana RPC URL
        """
        self.rpc_url = rpc_url
        self.client = AsyncClient(self.rpc_url)
        
        # Pump.Fun相关地址
        self.pumpfun_program_id = Pubkey.from_string("6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P")
        self.pumpfun_pool_program = Pubkey.from_string("pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA")
        
        # 监控参数
        self.max_age_hours = 24  # 只监控24小时内创建的代币
        self.min_liquidity_threshold = 1000  # 迁移的最低流动性(SOL)
        self.progress_threshold = 0.8  # 即将打满的进度阈值(80%)
        
        # 监控列表
        self.monitored_tokens = {}  # {token_address: token_data}
        self.migration_candidates = []  # 即将迁移的代币
        
        # 评分权重
        self.scoring_weights = {
            'progress_score': 0.4,      # 进度条权重
            'liquidity_growth': 0.3,     # 流动性增长权重
            'time_since_creation': 0.2,  # 创建时间权重
            'trading_activity': 0.1      # 交易活跃度权重
        }
    
    async def connect(self):
        """连接到Solana网络"""
        await self.client.__aenter__()
    
    async def close(self):
        """关闭连接"""
        await self.client.__aexit__(None, None, None)
    
    async def scan_new_tokens(self) -> List[Dict[str, Any]]:
        """扫描新创建的meme币
        
        Returns:
            新发现的代币列表
        """
        try:
            print("🔍 开始扫描Pump.Fun上的新meme币...")
            
            # 方法1: 通过Pump.Fun程序账户扫描
            new_tokens = await self._scan_pumpfun_program_accounts()
            
            # 方法2: 通过Token创建事件扫描
            recent_tokens = await self._scan_recent_token_creations()
            
            # 合并结果
            all_tokens = new_tokens + recent_tokens
            
            # 去重和筛选
            unique_tokens = self._deduplicate_tokens(all_tokens)
            
            print(f"📊 发现 {len(unique_tokens)} 个新代币")
            return unique_tokens
            
        except Exception as e:
            print(f"❌ 扫描失败: {e}")
            return []
    
    async def _scan_pumpfun_program_accounts(self) -> List[Dict[str, Any]]:
        """通过Pump.Fun程序账户扫描新代币"""
        try:
            # 获取Pump.Fun程序的所有账户
            accounts = await self.client.get_program_accounts(
                self.pumpfun_program_id,
                commitment=Confirmed
            )
            
            tokens = []
            for account in accounts.value:
                token_data = await self._analyze_pumpfun_account(account)
                if token_data:
                    tokens.append(token_data)
            
            return tokens
            
        except Exception as e:
            print(f"Pump.Fun账户扫描失败: {e}")
            return []
    
    async def _scan_recent_token_creations(self) -> List[Dict[str, Any]]:
        """通过最近创建的代币账户扫描"""
        try:
            # 获取最近24小时内创建的代币
            recent_tokens = []
            
            # 这里需要更复杂的链上事件监听
            # 暂时返回模拟数据
            return self._get_mock_recent_tokens()
            
        except Exception as e:
            print(f"最近代币扫描失败: {e}")
            return []
    
    async def _analyze_pumpfun_account(self, account) -> Optional[Dict[str, Any]]:
        """分析Pump.Fun账户数据"""
        try:
            account_data = account.account.data
            
            # 解析账户数据（这里需要实际的Pump.Fun数据结构）
            # 暂时返回模拟分析
            return self._analyze_mock_pumpfun_account(account)
            
        except Exception:
            return None
    
    def _get_mock_recent_tokens(self) -> List[Dict[str, Any]]:
        """获取模拟的最近代币数据"""
        # 模拟新创建的meme币
        return [
            {
                "token_address": "MockToken1" + "A" * 32,
                "name": "DogeClone",
                "symbol": "DOGECLONE",
                "created_at": time.time() - 3600,  # 1小时前
                "initial_liquidity": 50,
                "current_liquidity": 150,
                "target_liquidity": 1000,
                "progress": 0.15,
                "holder_count": 25,
                "transaction_count": 80
            },
            {
                "token_address": "MockToken2" + "B" * 32,
                "name": "CatMeme",
                "symbol": "CATMEME",
                "created_at": time.time() - 7200,  # 2小时前
                "initial_liquidity": 100,
                "current_liquidity": 450,
                "target_liquidity": 1000,
                "progress": 0.45,
                "holder_count": 45,
                "transaction_count": 120
            },
            {
                "token_address": "MockToken3" + "C" * 32,
                "name": "FrogCoin",
                "symbol": "FROG",
                "created_at": time.time() - 10800,  # 3小时前
                "initial_liquidity": 200,
                "current_liquidity": 780,
                "target_liquidity": 1000,
                "progress": 0.78,
                "holder_count": 68,
                "transaction_count": 200
            }
        ]
    
    def _analyze_mock_pumpfun_account(self, account) -> Dict[str, Any]:
        """模拟Pump.Fun账户分析"""
        return {
            "token_address": "MockPumpFun" + "D" * 32,
            "name": "PumpFunMock",
            "symbol": "PUMPMOCK",
            "created_at": time.time() - 5400,  # 1.5小时前
            "initial_liquidity": 80,
            "current_liquidity": 320,
            "target_liquidity": 1000,
            "progress": 0.32,
            "holder_count": 35,
            "transaction_count": 95
        }
    
    def _deduplicate_tokens(self, tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去重代币列表"""
        seen = set()
        unique_tokens = []
        
        for token in tokens:
            addr = token.get("token_address", "")
            if addr and addr not in seen:
                seen.add(addr)
                unique_tokens.append(token)
        
        return unique_tokens
    
    def calculate_progress_score(self, token_data: Dict[str, Any]) -> float:
        """计算进度条评分
        
        Args:
            token_data: 代币数据
            
        Returns:
            进度评分 (0-1)
        """
        progress = token_data.get("progress", 0)
        
        # 进度条评分逻辑
        if progress < 0.3:
            return 0.3  # 早期阶段，评分较低
        elif progress < 0.7:
            return 0.6  # 中期阶段，中等评分
        elif progress < 0.9:
            return 0.8  # 即将打满，高评分
        else:
            return 0.9  # 接近完成，最高评分
    
    def calculate_liquidity_growth_score(self, token_data: Dict[str, Any]) -> float:
        """计算流动性增长评分
        
        Args:
            token_data: 代币数据
            
        Returns:
            流动性增长评分 (0-1)
        """
        initial = token_data.get("initial_liquidity", 1)
        current = token_data.get("current_liquidity", 0)
        
        if initial <= 0:
            return 0.0
        
        growth_rate = (current - initial) / initial
        
        # 增长评分逻辑
        if growth_rate < 1:
            return 0.3  # 增长缓慢
        elif growth_rate < 3:
            return 0.6  # 中等增长
        elif growth_rate < 5:
            return 0.8  # 快速增长
        else:
            return 0.9  # 爆发式增长
    
    def calculate_time_score(self, token_data: Dict[str, Any]) -> float:
        """计算时间评分（越新的代币评分越高）
        
        Args:
            token_data: 代币数据
            
        Returns:
            时间评分 (0-1)
        """
        created_at = token_data.get("created_at", 0)
        current_time = time.time()
        
        if created_at <= 0:
            return 0.0
        
        age_hours = (current_time - created_at) / 3600
        
        # 时间评分逻辑（越新评分越高）
        if age_hours < 2:
            return 0.9  # 非常新
        elif age_hours < 6:
            return 0.7  # 较新
        elif age_hours < 12:
            return 0.5  # 中等
        elif age_hours < 24:
            return 0.3  # 较老
        else:
            return 0.1  # 太老
    
    def calculate_trading_activity_score(self, token_data: Dict[str, Any]) -> float:
        """计算交易活跃度评分
        
        Args:
            token_data: 代币数据
            
        Returns:
            交易活跃度评分 (0-1)
        """
        tx_count = token_data.get("transaction_count", 0)
        holder_count = token_data.get("holder_count", 1)
        
        # 交易密度 = 交易数 / 持有者数
        if holder_count <= 0:
            return 0.0
        
        tx_density = tx_count / holder_count
        
        # 交易密度评分
        if tx_density < 1:
            return 0.3  # 低活跃度
        elif tx_density < 3:
            return 0.6  # 中等活跃度
        elif tx_density < 5:
            return 0.8  # 高活跃度
        else:
            return 0.9  # 极高活跃度
    
    def calculate_overall_score(self, token_data: Dict[str, Any]) -> float:
        """计算综合评分
        
        Args:
            token_data: 代币数据
            
        Returns:
            综合评分 (0-1)
        """
        scores = {
            'progress_score': self.calculate_progress_score(token_data),
            'liquidity_growth': self.calculate_liquidity_growth_score(token_data),
            'time_since_creation': self.calculate_time_score(token_data),
            'trading_activity': self.calculate_trading_activity_score(token_data)
        }
        
        # 加权平均
        total_score = 0
        total_weight = 0
        
        for factor, weight in self.scoring_weights.items():
            total_score += scores[factor] * weight
            total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0
    
    def is_migration_candidate(self, token_data: Dict[str, Any]) -> bool:
        """判断是否为迁移候选
        
        Args:
            token_data: 代币数据
            
        Returns:
            是否为迁移候选
        """
        progress = token_data.get("progress", 0)
        current_liquidity = token_data.get("current_liquidity", 0)
        
        # 迁移候选条件
        return (progress >= self.progress_threshold and 
                current_liquidity < self.min_liquidity_threshold)
    
    async def monitor_migration_events(self, token_address: str) -> bool:
        """监控迁移事件
        
        Args:
            token_address: 代币地址
            
        Returns:
            是否已迁移
        """
        try:
            # 检查是否在主流DEX出现
            dex_pools = await self._check_dex_listings(token_address)
            
            # 检查流动性是否达到迁移阈值
            total_liquidity = sum(pool.get("liquidity", 0) for pool in dex_pools)
            
            return len(dex_pools) > 0 and total_liquidity >= self.min_liquidity_threshold
            
        except Exception as e:
            print(f"迁移监控失败 {token_address}: {e}")
            return False
    
    async def _check_dex_listings(self, token_address: str) -> List[Dict[str, Any]]:
        """检查DEX上市情况"""
        # 模拟DEX检查
        return self._get_mock_dex_pools(token_address)
    
    def _get_mock_dex_pools(self, token_address: str) -> List[Dict[str, Any]]:
        """获取模拟的DEX池数据"""
        # 基于代币特征的模拟数据
        if "MockToken3" in token_address:  # 进度78%的代币
            return [{"dex": "Raydium", "liquidity": 1200}]
        return []
    
    async def auto_scanner_cycle(self):
        """自动扫描循环"""
        print("🚀 启动Pump.Fun自动扫描器...")
        
        while True:
            try:
                # 扫描新代币
                new_tokens = await self.scan_new_tokens()
                
                # 更新监控列表
                for token in new_tokens:
                    addr = token["token_address"]
                    if addr not in self.monitored_tokens:
                        self.monitored_tokens[addr] = token
                        print(f"📝 新增监控: {addr[:16]}...")
                
                # 计算评分和筛选迁移候选
                migration_candidates = []
                for addr, token in self.monitored_tokens.items():
                    # 计算综合评分
                    token["overall_score"] = self.calculate_overall_score(token)
                    
                    # 判断是否为迁移候选
                    if self.is_migration_candidate(token):
                        migration_candidates.append(token)
                
                # 按评分排序
                migration_candidates.sort(key=lambda x: x["overall_score"], reverse=True)
                self.migration_candidates = migration_candidates
                
                # 输出监控状态
                self._print_monitoring_status()
                
                # 检查迁移事件
                await self._check_migration_events()
                
                # 等待下一轮扫描
                print(f"⏰ 等待30秒后继续扫描...\n")
                await asyncio.sleep(30)
                
            except Exception as e:
                print(f"❌ 扫描循环出错: {e}")
                await asyncio.sleep(10)
    
    def _print_monitoring_status(self):
        """打印监控状态"""
        print(f"\n📊 监控状态:")
        print(f"   监控代币数量: {len(self.monitored_tokens)}")
        print(f"   迁移候选数量: {len(self.migration_candidates)}")
        
        if self.migration_candidates:
            print("\n🎯 迁移候选排名:")
            for i, candidate in enumerate(self.migration_candidates[:5]):  # 显示前5名
                progress = candidate.get("progress", 0) * 100
                score = candidate.get("overall_score", 0) * 100
                print(f"   {i+1}. {candidate.get('symbol', 'Unknown')} - 进度: {progress:.1f}% - 评分: {score:.1f}")
    
    async def _check_migration_events(self):
        """检查迁移事件"""
        migrated_tokens = []
        
        for candidate in self.migration_candidates:
            addr = candidate["token_address"]
            
            if await self.monitor_migration_events(addr):
                print(f"🎉 检测到迁移事件: {addr[:16]}...")
                migrated_tokens.append(candidate)
                
                # 执行买入逻辑
                await self.execute_buy_strategy(candidate)
        
        # 从监控列表中移除已迁移的代币
        for token in migrated_tokens:
            self.monitored_tokens.pop(token["token_address"], None)
    
    async def execute_buy_strategy(self, token_data: Dict[str, Any]):
        """执行买入策略
        
        Args:
            token_data: 代币数据
        """
        try:
            print(f"💰 执行买入策略: {token_data.get('symbol', 'Unknown')}")
            
            # 这里应该实现实际的买入逻辑
            # 1. 检查钱包余额
            # 2. 计算买入金额
            # 3. 执行交易
            # 4. 确认交易结果
            
            # 模拟买入逻辑
            buy_amount = 0.1  # 买入0.1 SOL
            token_address = token_data["token_address"]
            
            print(f"   📈 计划买入: {buy_amount} SOL 的 {token_data.get('symbol', 'Unknown')}")
            print(f"   🔗 代币地址: {token_address}")
            
            # 实际实现时需要调用交易接口
            # await self.trading_client.buy_token(token_address, buy_amount)
            
        except Exception as e:
            print(f"❌ 买入策略执行失败: {e}")


async def main():
    """主函数"""
    scanner = PumpFunAutoScanner()
    
    try:
        await scanner.connect()
        
        # 运行自动扫描循环
        await scanner.auto_scanner_cycle()
        
    except KeyboardInterrupt:
        print("\n⏹️ 用户中断扫描")
    except Exception as e:
        print(f"❌ 程序执行失败: {e}")
    finally:
        await scanner.close()


if __name__ == "__main__":
    asyncio.run(main())