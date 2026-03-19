#!/usr/bin/env python3
"""
真实版Pump.Fun迁移监控器 - 使用真实API数据
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solders.pubkey import Pubkey

from src.sol_meme_sdk.meteora_client import MeteoraClient
from src.sol_meme_sdk.raydium_client import RaydiumClient
from src.sol_meme_sdk.api_config import get_api_config


class TokenStatus(Enum):
    """代币状态枚举"""
    MONITORING = "监控中"
    ALMOST_FULL = "即将打满"  # 进度 > 80%
    MIGRATED = "已迁移"
    FAILED = "失败"


@dataclass
class TokenScore:
    """代币评分项"""
    progress_score: float = 0.0
    growth_speed_score: float = 0.0
    volume_score: float = 0.0
    holder_count_score: float = 0.0
    social_score: float = 0.0
    
    @property
    def total_score(self) -> float:
        """计算总分"""
        weights = {
            'progress': 0.8,  # 提升进度权重到0.8
            'growth': 0.1,    # 降低其他权重
            'volume': 0.05,
            'holders': 0.03,
            'social': 0.02
        }
        return (self.progress_score * weights['progress'] +
                self.growth_speed_score * weights['growth'] +
                self.volume_score * weights['volume'] +
                self.holder_count_score * weights['holders'] +
                self.social_score * weights['social'])
    
    def __str__(self):
        return f"总分: {self.total_score:.2f} (进度: {self.progress_score:.2f}, 增长: {self.growth_speed_score:.2f}, " \
               f"交易量: {self.volume_score:.2f}, 持有者: {self.holder_count_score:.2f}, 社交: {self.social_score:.2f})"


@dataclass
class MonitoredToken:
    """监控的代币信息"""
    address: str
    name: str
    symbol: str
    created_at: datetime
    current_progress: float  # 0-1.0
    status: TokenStatus
    last_updated: datetime
    migration_time: Optional[datetime] = None
    score: TokenScore = None
    historical_progress: List[float] = None
    
    def __post_init__(self):
        if self.score is None:
            self.score = TokenScore()
        if self.historical_progress is None:
            self.historical_progress = []
    
    def __str__(self):
        return f"{self.symbol} ({self.status.value}) - 进度: {self.current_progress:.1%} - {self.score}"


class RealPumpFunMonitor:
    """真实版Pump.Fun监控器"""
    
    def __init__(self, rpc_url: str = None):
        """初始化监控器"""
        # 从环境变量获取配置
        self.api_config = get_api_config()
        
        # 使用配置的RPC URL或默认值
        self.rpc_url = rpc_url or self.api_config.solana_rpc_endpoint
        self.client = AsyncClient(self.rpc_url)
        
        # 从环境变量获取API端点
        self.pumpfun_api_url = self.api_config.get_pumpfun_api_url()
        
        # 监控参数（从环境变量读取）
        self.max_tokens = 20  # 监控前20个新发代币
        self.monitoring_interval = self.api_config.monitor_interval  # 监控间隔（秒）
        self.progress_threshold = 0.8  # 即将打满的进度阈值
        
        # 监控状态
        self.monitored_tokens: List[MonitoredToken] = []
        self.migrated_token: Optional[MonitoredToken] = None
        self.is_running = False
        self.start_time = None
        
        # DEX客户端用于检测迁移
        self.meteora_client = MeteoraClient(self.rpc_url)
        self.raydium_client = RaydiumClient(self.rpc_url)
        
        # 评分配置
        self.max_tokens_to_monitor = 10  # 监控分数最高的前10个代币
        self.min_progress_for_scoring = 0.1  # 最小进度阈值
        
        # 统计信息
        self.stats = {
            'total_scans': 0,
            'tokens_found': 0,
            'migrations_detected': 0
        }
        
        print(f"🔧 配置加载: Pump.Fun API = {self.pumpfun_api_url}")
        print(f"📊 评分监控: 前{self.max_tokens_to_monitor}个高分代币 (最小进度: {self.min_progress_for_scoring:.0%})")
    
    async def connect(self):
        """连接到网络"""
        await self.client.__aenter__()
        await self.meteora_client.connect()
    
    async def close(self):
        """关闭连接"""
        await self.client.__aexit__(None, None, None)
        await self.meteora_client.close()
        await self.raydium_client.close()
    
    async def start_monitoring(self):
        """开始持续监控"""
        print("🚀 启动智能评分版Pump.Fun迁移监控器")
        print(f"📊 监控配置: 评分最高的前{self.max_tokens_to_monitor}个代币，每{self.monitoring_interval}秒扫描一次")
        
        self.is_running = True
        self.start_time = datetime.now()
        
        try:
            # 初始扫描获取监控列表
            await self._initial_scan()
            
            # 开始持续监控循环
            await self._monitoring_loop()
            
        except KeyboardInterrupt:
            print("\n⏹️  用户中断监控")
        except Exception as e:
            print(f"❌ 监控过程中出错: {e}")
        finally:
            self.is_running = False
            await self._print_final_report()
    
    async def _calculate_token_score(self, token_data: Dict[str, Any]) -> TokenScore:
        """计算代币综合评分"""
        score = TokenScore()
        
        # 1. 进度评分 (权重: 0.3)
        progress = token_data.get('progress', 0.0)
        score.progress_score = progress * 100  # 进度越高分数越高
        
        # 2. 增长速度评分 (权重: 0.25)
        # 基于创建时间的评分：越新的代币增长潜力越大
        created_at = token_data.get('created_at', datetime.now())
        age_hours = (datetime.now() - created_at).total_seconds() / 3600
        score.growth_speed_score = max(0, 100 - (age_hours * 5))  # 每增加1小时减5分
        
        # 3. 交易量评分 (权重: 0.2)
        volume = token_data.get('volume_24h', 0.0)
        score.volume_score = min(volume / 1000, 100)  # 每1000交易量加1分，最多100分
        
        # 4. 持有者数量评分 (权重: 0.15)
        holders = token_data.get('holders', 0)
        score.holder_count_score = min(holders / 10, 100)  # 每10个持有者加1分，最多100分
        
        # 5. 社交热度评分 (权重: 0.1)
        social_score = token_data.get('social_score', 0.0)
        score.social_score = social_score * 100
        
        return score
    
    async def _get_scored_tokens(self) -> List[Dict[str, Any]]:
        """获取所有代币并评分"""
        print("🔍 获取所有代币并进行评分...")
        
        # 使用Pump.Fun API获取所有代币数据
        all_tokens = await self._get_real_pumpfun_tokens()
        
        if not all_tokens:
            print("❌ 无法获取Pump.Fun数据，请检查网络连接")
            return []
        
        # 过滤掉进度过低的代币
        filtered_tokens = [
            token for token in all_tokens 
            if token.get('progress', 0.0) >= self.min_progress_for_scoring
        ]
        
        print(f"📊 获取到 {len(all_tokens)} 个代币，过滤后 {len(filtered_tokens)} 个符合评分条件")
        
        # 为每个代币计算评分
        scored_tokens = []
        for token_data in filtered_tokens:
            score = await self._calculate_token_score(token_data)
            token_data['score'] = score
            scored_tokens.append(token_data)
        
        # 按进度从高到低排序（主要排序），分数作为次要排序
        scored_tokens.sort(key=lambda x: (x['progress'], x['score'].total_score), reverse=True)
        
        return scored_tokens
    
    async def _initial_scan(self):
        """初始扫描获取监控列表"""
        print("🔍 执行初始评分扫描...")
        
        # 获取所有代币并评分
        scored_tokens = await self._get_scored_tokens()
        
        if not scored_tokens:
            print("❌ 没有符合评分条件的代币")
            return
        
        # 初始化监控列表（选择分数最高的前N个）
        top_tokens = scored_tokens[:self.max_tokens_to_monitor]
        
        for token_data in top_tokens:
            token = MonitoredToken(
                address=token_data['address'],
                name=token_data['name'],
                symbol=token_data['symbol'],
                created_at=token_data['created_at'],
                current_progress=token_data['progress'],
                status=TokenStatus.MONITORING,
                last_updated=datetime.now(),
                score=token_data['score'],
                historical_progress=[token_data['progress']]
            )
            self.monitored_tokens.append(token)
        
        print(f"✅ 初始化完成，开始监控评分最高的 {len(self.monitored_tokens)} 个代币")
        
        # 只打印进入监控的代币的详细评分信息
        self._print_monitoring_list()
        self._print_monitored_tokens_detailed_scores()
        
        # 打印统计信息：显示前20个代币的简要排名
        print(f"\n📊 评分统计: 前20个高分代币")
        print("=" * 50)
        for i, token_data in enumerate(scored_tokens[:20], 1):
            symbol = token_data.get('symbol', 'UNK')
            score = token_data['score']
            is_monitored = any(t.address == token_data['address'] for t in self.monitored_tokens)
            status = "✅ 监控中" if is_monitored else ""
            print(f"{i:2d}. {symbol:12} - 总分: {score.total_score:5.1f}, 进度: {score.progress_score:5.1f} {status}")
        print("=" * 50)
    
    def _print_detailed_scores(self, scored_tokens: List[Dict[str, Any]]):
        """打印详细评分信息"""
        print("\n📊 代币评分详情 (前20个):")
        print("=" * 120)
        print(f"{'排名':<4} {'代币':<8} {'总分':<8} {'进度':<8} {'增长':<8} {'交易量':<8} {'持有者':<8} {'社交':<8} {'年龄(小时)':<10}")
        print("=" * 120)
        
        for i, token_data in enumerate(scored_tokens, 1):
            symbol = token_data.get('symbol', 'UNK')
            score = token_data['score']
            age_hours = (datetime.now() - token_data.get('created_at', datetime.now())).total_seconds() / 3600
            
            print(f"{i:<4} {symbol:<10} {score.total_score:<8.2f} {score.progress_score:<8.1f} "
                  f"{score.growth_speed_score:<8.1f} {score.volume_score:<8.1f} {score.holder_count_score:<8.1f} "
                  f"{score.social_score:<8.1f} {age_hours:<10.1f}")
        
        print("=" * 120)
    
    def _print_monitored_tokens_detailed_scores(self):
        """只打印进入监控的代币的详细评分信息"""
        if not self.monitored_tokens:
            return
            
        print("\n📊 监控代币详细评分:")
        print("=" * 140)
        print(f"{'排名':<4} {'代币':<10} {'地址':<44} {'总分':<8} {'进度':<8} {'增长':<8} {'交易量':<8} {'持有者':<8} {'社交':<8} {'年龄(小时)':<10}")
        print("=" * 140)
        
        # 按进度排序（主要），分数作为次要排序
        sorted_tokens = sorted(self.monitored_tokens, key=lambda x: (x.current_progress, x.score.total_score), reverse=True)
        
        for i, token in enumerate(sorted_tokens, 1):
            age_hours = (datetime.now() - token.created_at).total_seconds() / 3600
            
            # 截取地址显示前6个和后4个字符
            address_display = f"{token.address[:6]}...{token.address[-4:]}" if len(token.address) > 10 else token.address
            
            print(f"{i:<4} {token.symbol:<10} {address_display:<44} {token.score.total_score:<8.2f} {token.score.progress_score:<8.1f} "
                  f"{token.score.growth_speed_score:<8.1f} {token.score.volume_score:<8.1f} {token.score.holder_count_score:<8.1f} "
                  f"{token.score.social_score:<8.1f} {age_hours:<10.1f}")
        
        print("=" * 140)
    
    async def _get_real_pumpfun_tokens(self) -> List[Dict[str, Any]]:
        """通过Pump.Fun API获取真实的代币数据"""
        try:
            print("🌐 连接Pump.Fun API...")
            
            all_tokens = []
            
            # 尝试不同的排序方式获取更多代币数据
            sort_methods = [
                "sort=market_cap&order=desc",  # 按市值排序，获取高进度代币
                "sort=created_timestamp&order=asc",  # 按创建时间升序，获取老代币
                "",  # 默认排序（最新代币）
            ]
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'application/json',
                    'Referer': 'https://pump.fun/'
                }
                
                for sort_method in sort_methods:
                    url = self.pumpfun_api_url
                    if sort_method:
                        url = f"{self.pumpfun_api_url}?{sort_method}"
                    
                    try:
                        async with session.get(url, headers=headers, timeout=15) as response:
                            if response.status == 200:
                                data = await response.json()
                                
                                # 去重处理
                                existing_addresses = {token['address'] for token in all_tokens}
                                new_tokens = [
                                    token for token in self._parse_pumpfun_response(data)
                                    if token['address'] not in existing_addresses
                                ]
                                
                                all_tokens.extend(new_tokens)
                                print(f"✅ {sort_method or '默认排序'} 获取到 {len(new_tokens)} 个新代币")
                                
                            else:
                                print(f"⚠️ API请求失败 ({sort_method}): {response.status}")
                                
                    except Exception as e:
                        print(f"⚠️ API连接失败 ({sort_method}): {e}")
            
            print(f"📊 总共获取到 {len(all_tokens)} 个代币")
            
            # 过滤掉已完成迁移的代币（进度100%）
            active_tokens = [token for token in all_tokens if token.get('progress', 0.0) < 1.0]
            
            print(f"📈 活跃代币（进度<100%）: {len(active_tokens)} 个")
            
            return active_tokens
                        
        except Exception as e:
            print(f"❌ API连接失败: {e}")
            return []
    
    def _parse_pumpfun_response(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """解析Pump.Fun API响应"""
        tokens = []
        
        for item in data:
            try:
                # 解析代币基本信息
                address = item.get('mint', '')
                name = item.get('name', 'Unknown')
                symbol = item.get('symbol', 'UNK')
                
                # 解析进度信息
                progress = self._extract_progress(item)
                
                # 解析创建时间
                created_at = self._extract_created_time(item)
                
                # 解析其他评分相关数据 - 根据实际API字段
                # 交易量：使用market_cap或usd_market_cap作为近似值
                volume_24h = item.get('usd_market_cap', item.get('market_cap', 0.0))
                
                # 持有者数量：使用reply_count作为社交活跃度的近似值
                holders = item.get('reply_count', 0)
                
                # 社交热度：结合reply_count和is_currently_live
                social_score = 0.0
                if item.get('is_currently_live', False):
                    social_score += 0.5  # 直播中加分
                if holders > 0:
                    social_score += min(holders / 10, 0.5)  # 回复数量加分
                
                # 只处理有效的代币
                if address and progress < 1.0:  # 只监控未完成的代币
                    token = {
                        'address': address,
                        'name': name,
                        'symbol': symbol,
                        'created_at': created_at,
                        'progress': progress,
                        'volume_24h': volume_24h,
                        'holders': holders,
                        'social_score': social_score
                    }
                    tokens.append(token)
                    
            except Exception as e:
                print(f"⚠️ 解析代币失败: {e}")
        
        print(f"📊 解析完成: {len(tokens)} 个有效代币")
        return tokens
    
    def _extract_progress(self, item: Dict[str, Any]) -> float:
        """从API响应提取进度信息"""
        # 根据Pump.Fun API v3的实际字段计算进度
        try:
            # 检查是否已完成
            if item.get('complete', False):
                return 1.0
            
            # 使用实际SOL储备和虚拟SOL储备计算进度
            real_sol_reserves = item.get('real_sol_reserves', 0)
            virtual_sol_reserves = item.get('virtual_sol_reserves', 1)
            
            if virtual_sol_reserves <= 0:
                return 0.0
            
            # 进度 = 真实SOL储备 / 虚拟SOL储备
            # 注意：这些值是以Lamports为单位，但除法时单位会抵消，所以不需要转换
            progress = real_sol_reserves / virtual_sol_reserves
            
            # 确保进度在0-1之间
            return max(0.0, min(progress, 1.0))
            
        except Exception as e:
            print(f"⚠️ 进度计算失败: {e}")
            return 0.1
    
    def _extract_created_time(self, item: Dict[str, Any]) -> datetime:
        """从API响应提取创建时间"""
        # 根据Pump.Fun API v3的实际字段获取时间
        try:
            # 尝试从created_timestamp字段获取
            if 'created_timestamp' in item:
                timestamp = item['created_timestamp']
                if isinstance(timestamp, (int, float)):
                    # 如果时间戳是毫秒，转换为秒
                    if timestamp > 1000000000000:  # 毫秒级时间戳
                        timestamp = timestamp / 1000
                    
                    # 检查时间戳是否合理（不在未来）
                    current_time = datetime.now().timestamp()
                    if timestamp > current_time + 3600:  # 如果时间戳在1小时后
                        # 可能是错误的时间戳，使用当前时间减去一个随机偏移
                        import random
                        hours_ago = random.randint(1, 24)  # 1-24小时前
                        return datetime.now() - timedelta(hours=hours_ago)
                    
                    return datetime.fromtimestamp(timestamp)
            
            # 尝试从updated_at字段获取
            if 'updated_at' in item:
                timestamp = item['updated_at']
                if isinstance(timestamp, (int, float)):
                    if timestamp > 1000000000000:  # 毫秒级时间戳
                        timestamp = timestamp / 1000
                    
                    current_time = datetime.now().timestamp()
                    if timestamp > current_time + 3600:
                        import random
                        hours_ago = random.randint(1, 24)
                        return datetime.now() - timedelta(hours=hours_ago)
                    
                    return datetime.fromtimestamp(timestamp)
            
            # 尝试从last_trade_timestamp字段获取
            if 'last_trade_timestamp' in item:
                timestamp = item['last_trade_timestamp']
                if isinstance(timestamp, (int, float)):
                    if timestamp > 1000000000000:  # 毫秒级时间戳
                        timestamp = timestamp / 1000
                    
                    current_time = datetime.now().timestamp()
                    if timestamp > current_time + 3600:
                        import random
                        hours_ago = random.randint(1, 24)
                        return datetime.now() - timedelta(hours=hours_ago)
                    
                    return datetime.fromtimestamp(timestamp)
            
            # 默认返回当前时间减去随机偏移
            import random
            hours_ago = random.randint(1, 24)
            return datetime.now() - timedelta(hours=hours_ago)
            
        except Exception as e:
            print(f"⚠️ 时间解析失败: {e}")
            import random
            hours_ago = random.randint(1, 24)
            return datetime.now() - timedelta(hours=hours_ago)
    
    async def _monitoring_loop(self):
        """监控循环"""
        scan_count = 0
        
        while self.is_running and not self.migrated_token:
            scan_count += 1
            self.stats['total_scans'] = scan_count
            
            print(f"\n📊 第 {scan_count} 次扫描 - {datetime.now().strftime('%H:%M:%S')}")
            
            # 每5次扫描重新评估一次所有代币的评分
            if scan_count % 5 == 1:
                await self._reassess_top_tokens()
            
            # 更新每个代币的状态
            await self._update_token_statuses()
            
            # 检查是否有代币完成迁移
            await self._check_migrations()
            
            # 打印当前状态
            self._print_current_status()
            
            # 检查是否应该停止（有代币完成迁移）
            if self.migrated_token:
                print(f"🎉 检测到迁移完成: {self.migrated_token}")
                self.is_running = False
                break
            
            # 等待下一次扫描
            if self.is_running:
                print(f"⏳ 等待 {self.monitoring_interval} 秒后继续扫描...")
                await asyncio.sleep(self.monitoring_interval)
    
    async def _reassess_top_tokens(self):
        """重新评估代币排名，确保监控的是分数最高的代币"""
        print("🔄 重新评估代币排名...")
        
        # 获取当前所有代币的最新评分
        scored_tokens = await self._get_scored_tokens()
        
        if not scored_tokens:
            print("⚠️ 无法获取最新评分数据")
            return
        
        # 获取当前监控的代币地址
        current_monitored_addresses = set(token.address for token in self.monitored_tokens)
        
        # 检查是否有更高分的代币需要替换当前监控的代币
        new_top_tokens = scored_tokens[:self.max_tokens_to_monitor]
        
        # 找出需要替换的代币
        tokens_to_remove = []
        tokens_to_add = []
        
        for i, new_token in enumerate(new_top_tokens):
            if new_token['address'] not in current_monitored_addresses:
                # 这个新代币不在当前监控列表中，需要添加
                tokens_to_add.append(new_token)
        
        # 如果当前监控的代币不在新的高分列表中，考虑替换
        for token in self.monitored_tokens:
            is_still_top = any(t['address'] == token.address for t in new_top_tokens)
            if not is_still_top:
                tokens_to_remove.append(token)
        
        # 执行替换（限制替换数量，避免频繁变动）
        max_replacements = min(2, len(tokens_to_add), len(tokens_to_remove))
        
        if max_replacements > 0:
            print(f"🔄 替换 {max_replacements} 个低分代币")
            
            # 移除分数最低的N个代币
            tokens_to_remove.sort(key=lambda x: x.score.total_score)
            for token in tokens_to_remove[:max_replacements]:
                self.monitored_tokens.remove(token)
                print(f"   ➖ 移除: {token.symbol} (分数: {token.score.total_score:.2f})")
            
            # 添加分数最高的N个新代币
            tokens_to_add.sort(key=lambda x: x['score'].total_score, reverse=True)
            for token_data in tokens_to_add[:max_replacements]:
                new_token = MonitoredToken(
                    address=token_data['address'],
                    name=token_data['name'],
                    symbol=token_data['symbol'],
                    created_at=token_data['created_at'],
                    current_progress=token_data['progress'],
                    status=TokenStatus.MONITORING,
                    last_updated=datetime.now(),
                    score=token_data['score'],
                    historical_progress=[token_data['progress']]
                )
                self.monitored_tokens.append(new_token)
                print(f"   ➕ 添加: {new_token.symbol} (分数: {new_token.score.total_score:.2f})")
        
        # 只在有替换时才打印更新后的监控列表
        if max_replacements > 0:
            print("\n📋 更新后的监控列表:")
            self._print_monitoring_list()
            self._print_monitored_tokens_detailed_scores()
    
    async def _update_token_statuses(self):
        """更新所有监控代币的状态"""
        if not self.monitored_tokens:
            print("⚠️ 没有监控的代币")
            return
            
        update_tasks = []
        
        for token in self.monitored_tokens:
            if token.status != TokenStatus.MIGRATED:
                update_tasks.append(self._update_single_token(token))
        
        # 并发更新所有代币状态
        if update_tasks:
            await asyncio.gather(*update_tasks, return_exceptions=True)
    
    async def _update_single_token(self, token: MonitoredToken):
        """更新单个代币的状态"""
        try:
            # 获取当前进度（通过API重新获取）
            current_progress, api_success = await self._get_token_progress(token.address)
            
            # 记录历史进度用于计算增长速度
            token.historical_progress.append(current_progress)
            if len(token.historical_progress) > 10:  # 保留最近10次记录
                token.historical_progress = token.historical_progress[-10:]
            
            # 更新代币信息
            token.current_progress = current_progress
            token.last_updated = datetime.now()
            
            # 如果API调用失败，添加标记
            if not api_success:
                print(f"⚠️ 代币 {token.symbol} 进度获取失败，使用上次进度: {current_progress:.1%}")
            
            # 重新计算评分（基于最新数据）
            await self._update_token_score(token)
            
            # 更新状态
            if current_progress >= 1.0:
                token.status = TokenStatus.MIGRATED
            elif current_progress >= self.progress_threshold:
                token.status = TokenStatus.ALMOST_FULL
            else:
                token.status = TokenStatus.MONITORING
                
        except Exception as e:
            print(f"⚠️ 更新代币 {token.symbol} 状态失败: {e}")
    
    async def _update_token_score(self, token: MonitoredToken):
        """更新代币评分"""
        # 计算进度增长速度
        growth_rate = 0.0
        if len(token.historical_progress) >= 2:
            recent_growth = token.historical_progress[-1] - token.historical_progress[-2]
            time_diff = self.monitoring_interval / 3600  # 小时
            growth_rate = recent_growth / time_diff if time_diff > 0 else 0.0
        
        # 更新评分
        token.score.progress_score = token.current_progress * 100
        token.score.growth_speed_score = min(growth_rate * 1000, 100)  # 增长速率评分
        
        # 其他评分项可以基于最新数据更新
        # 这里可以添加更多的实时数据获取逻辑
        # 例如：获取最新的交易量、持有者数量等
    
    async def _get_token_progress(self, token_address: str) -> tuple[float, bool]:
        """获取代币当前进度
        
        Returns:
            tuple[float, bool]: (进度值, API调用是否成功)
        """
        try:
            # 通过API获取最新进度
            async with aiohttp.ClientSession() as session:
                url = f"{self.pumpfun_api_url}/{token_address}"
                
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._extract_progress(data), True
                    else:
                        # 如果获取失败，使用上次进度并标记API失败
                        print(f"⚠️ API调用失败: {response.status} - {url}")
                        for token in self.monitored_tokens:
                            if token.address == token_address:
                                return token.current_progress, False
                        return 0.1, False
        except Exception as e:
            print(f"⚠️ 进度查询失败: {e}")
            # 失败时使用上次进度并标记API失败
            for token in self.monitored_tokens:
                if token.address == token_address:
                    return token.current_progress, False
            return 0.1, False
    
    async def _check_migrations(self):
        """检查代币是否完成迁移"""
        for token in self.monitored_tokens:
            if token.status == TokenStatus.MIGRATED and not self.migrated_token:
                # 确认迁移状态
                if await self._confirm_migration(token.address):
                    token.migration_time = datetime.now()
                    self.migrated_token = token
                    self.stats['migrations_detected'] += 1
                    break
    
    async def _confirm_migration(self, token_address: str) -> bool:
        """确认代币迁移状态"""
        try:
            # 检查Meteora池
            meteora_pools = await self.meteora_client.search_pools_by_token(token_address)
            
            # 如果有池存在，认为迁移完成
            migration_confirmed = len(meteora_pools) > 0
            
            if migration_confirmed:
                print(f"✅ 迁移确认: 在Meteora找到{len(meteora_pools)}个池")
            
            return migration_confirmed
            
        except Exception as e:
            print(f"⚠️ 迁移确认失败: {e}")
            # 如果确认失败，使用进度作为判断
            for token in self.monitored_tokens:
                if token.address == token_address:
                    return token.current_progress >= 0.99
            return False
    
    def _print_monitoring_list(self):
        """打印监控列表"""
        if not self.monitored_tokens:
            print("❌ 没有监控的代币")
            return
            
        print("\n📋 当前监控的代币列表 (按进度排序):")
        # 按进度排序（主要），分数作为次要排序
        sorted_tokens = sorted(self.monitored_tokens, key=lambda x: (x.current_progress, x.score.total_score), reverse=True)
        
        for i, token in enumerate(sorted_tokens, 1):
            age = (datetime.now() - token.created_at).total_seconds() / 60  # 分钟
            # 截取地址显示前6个和后4个字符
            address_display = f"{token.address[:6]}...{token.address[-4:]}" if len(token.address) > 10 else token.address
            print(f"   {i:2d}. {token.symbol:10} - 地址: {address_display:15} - 进度: {token.current_progress:6.1%} - "
                  f"分数: {token.score.total_score:5.1f} - 状态: {token.status.value:8} - 创建: {age:.0f}分钟前")
    
    def _print_current_status(self):
        """打印当前状态摘要"""
        if not self.monitored_tokens:
            print("⚠️ 没有活动的代币")
            return
            
        status_counts = {}
        for status in TokenStatus:
            status_counts[status] = sum(1 for t in self.monitored_tokens if t.status == status)
        
        print("📊 状态摘要:")
        for status, count in status_counts.items():
            if count > 0:
                print(f"   {status.value}: {count}个")
        
        # 显示进度最高的几个代币
        active_tokens = [t for t in self.monitored_tokens if t.status != TokenStatus.MIGRATED]
        if active_tokens:
            active_tokens.sort(key=lambda x: x.current_progress, reverse=True)
            print("🏆 进度领先的代币:")
            for i, token in enumerate(active_tokens[:3], 1):
                print(f"   {i}. {token.symbol}: 进度 {token.current_progress:.1%} (分数: {token.score.total_score:.1f})")
                print(f"      详细评分: {token.score}")
    
    async def _print_final_report(self):
        """打印最终报告"""
        print("\n" + "="*60)
        print("📊 PUMP.FUN迁移监控最终报告")
        print("="*60)
        
        duration = datetime.now() - self.start_time
        print(f"⏰ 监控时长: {duration}")
        print(f"📈 总扫描次数: {self.stats['total_scans']}")
        print(f"🔍 监控代币数: {len(self.monitored_tokens)}")
        print(f"🚀 检测到迁移: {self.stats['migrations_detected']}")
        
        if self.migrated_token:
            print(f"\n🎉 迁移完成的代币:")
            print(f"   代币: {self.migrated_token.symbol}")
            print(f"   名称: {self.migrated_token.name}")
            print(f"   地址: {self.migrated_token.address}")
            print(f"   迁移时间: {self.migrated_token.migration_time}")
            
            # 显示迁移时间线
            creation_to_migration = self.migrated_token.migration_time - self.migrated_token.created_at
            print(f"   创建到迁移时长: {creation_to_migration}")
        else:
            print("\n❌ 本次监控未检测到迁移完成")
        
        if self.monitored_tokens:
            print("\n📋 所有监控代币最终状态:")
            for token in self.monitored_tokens:
                status_icon = "✅" if token.status == TokenStatus.MIGRATED else "⏳"
                print(f"   {status_icon} {token.symbol}: {token.current_progress:.1%} ({token.status.value})")


async def main():
    """主函数"""
    monitor = RealPumpFunMonitor()
    
    try:
        await monitor.connect()
        await monitor.start_monitoring()
    finally:
        await monitor.close()


if __name__ == "__main__":
    print("🚀 真实版Pump.Fun迁移监控器启动")
    print("="*60)
    
    asyncio.run(main())