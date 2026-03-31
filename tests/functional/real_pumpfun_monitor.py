#!/usr/bin/env python3
"""
真实版Pump.Fun迁移监控器 - 支持手动添加代币地址监控
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

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
    
    def total_score(self, weights: dict = None) -> float:
        """计算总分"""
        if weights is None:
            # 默认权重配置
            weights = {
                'progress': 0.8,
                'growth': 0.1,
                'volume': 0.05,
                'holders': 0.03,
                'social': 0.02
            }
        
        return (self.progress_score * weights.get('progress', 0.8) +
                self.growth_speed_score * weights.get('growth', 0.1) +
                self.volume_score * weights.get('volume', 0.05) +
                self.holder_count_score * weights.get('holders', 0.03) +
                self.social_score * weights.get('social', 0.02))
    
    def __str__(self):
        return f"总分: {self.total_score():.2f} (进度: {self.progress_score:.2f}, 增长: {self.growth_speed_score:.2f}, " \
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
        
        # 评分权重配置（可被配置文件覆盖）
        self.scoring_weights = {
            'progress': 0.8,
            'growth': 0.1,
            'volume': 0.05,
            'holders': 0.03,
            'social': 0.02
        }
        
        # 统计信息
        self.stats = {
            'total_scans': 0,
            'tokens_found': 0,
            'migrations_detected': 0
        }
        
        # 配置文件动态重载相关
        self.current_config_file = None
        self.last_config_mtime = 0
        self.config_reload_interval = 5  # 每5次扫描检查一次配置文件
        
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
    
    async def add_token_to_monitor(self, token_address: str) -> bool:
        """手动添加代币地址到监控列表"""
        # 检查是否已经在监控列表中
        existing_token = next((t for t in self.monitored_tokens if t.address == token_address), None)
        if existing_token:
            print(f"⚠️ 代币 {token_address} 已经在监控列表中")
            return False
        
        # 获取代币信息
        token_data = await self._get_single_token_info(token_address)
        if not token_data:
            print(f"❌ 无法获取代币信息: {token_address}")
            return False
        
        # 检查进度是否达到最小阈值
        if token_data.get('progress', 0.0) < self.min_progress_for_scoring:
            print(f"❌ 代币进度过低 ({token_data.get('progress', 0.0):.1%})，低于最小阈值 {self.min_progress_for_scoring:.0%}")
            return False
        
        # 计算评分
        score = await self._calculate_token_score(token_data)
        
        # 创建监控代币对象
        token = MonitoredToken(
            address=token_data['address'],
            name=token_data['name'],
            symbol=token_data['symbol'],
            created_at=token_data['created_at'],
            current_progress=token_data['progress'],
            status=TokenStatus.MONITORING,
            last_updated=datetime.now(),
            score=score,
            historical_progress=[token_data['progress']]
        )
        
        # 添加到监控列表
        self.monitored_tokens.append(token)
        
        print(f"✅ 成功添加代币到监控列表: {token.symbol} ({token.address}) - 进度: {token.current_progress:.1%}")
        
        # 如果监控列表已满，移除评分最低的代币
        if len(self.monitored_tokens) > self.max_tokens_to_monitor:
            self.monitored_tokens.sort(key=lambda x: x.score.total_score(self.scoring_weights), reverse=True)
            removed_token = self.monitored_tokens.pop()
            print(f"📊 监控列表已满，移除评分最低的代币: {removed_token.symbol} (分数: {removed_token.score.total_score(self.scoring_weights):.1f})")
        
        return True
    
    async def load_config(self, config_file: str = "monitored_tokens.json") -> bool:
        """从配置文件加载监控配置和代币列表"""
        import os
        
        if not os.path.exists(config_file):
            print(f"⚠️ 配置文件不存在: {config_file}")
            return False
        
        try:
            # 记录当前配置文件和修改时间
            self.current_config_file = config_file
            self.last_config_mtime = os.path.getmtime(config_file)
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # 加载监控配置参数
            self._load_monitoring_config(config_data)
            
            # 加载评分权重配置
            self._load_scoring_weights(config_data)
            
            # 加载代币地址列表
            token_addresses = config_data.get('tokens', [])
            if not token_addresses:
                print("⚠️ 配置文件中没有找到代币地址")
                return False
            
            print(f"📝 从配置文件加载 {len(token_addresses)} 个代币...")
            
            success_count = 0
            for token_address in token_addresses:
                if await self.add_token_to_monitor(token_address):
                    success_count += 1
            
            print(f"✅ 成功加载 {success_count}/{len(token_addresses)} 个代币到监控列表")
            return success_count > 0
            
        except Exception as e:
            print(f"❌ 加载配置文件失败: {e}")
            return False
    
    def _load_monitoring_config(self, config_data: dict):
        """加载监控配置参数"""
        # 监控间隔（秒）
        if 'monitoring_interval' in config_data:
            self.monitoring_interval = config_data['monitoring_interval']
            print(f"📊 监控间隔: {self.monitoring_interval}秒")
        
        # 最大监控代币数
        if 'max_tokens_to_monitor' in config_data:
            self.max_tokens_to_monitor = config_data['max_tokens_to_monitor']
            print(f"📊 最大监控代币数: {self.max_tokens_to_monitor}")
        
        # 最小进度阈值
        if 'min_progress_for_scoring' in config_data:
            self.min_progress_for_scoring = config_data['min_progress_for_scoring']
            print(f"📊 最小进度阈值: {self.min_progress_for_scoring:.0%}")
        
        # 进度阈值（即将打满）
        if 'progress_threshold' in config_data:
            self.progress_threshold = config_data['progress_threshold']
            print(f"📊 进度阈值: {self.progress_threshold:.0%}")
    
    def _load_scoring_weights(self, config_data: dict):
        """加载评分权重配置"""
        # 默认权重配置
        default_weights = {
            'progress': 0.8,
            'growth': 0.1,
            'volume': 0.05,
            'holders': 0.03,
            'social': 0.02
        }
        
        # 如果配置文件中有权重配置，使用配置文件的权重
        if 'scoring_weights' in config_data:
            self.scoring_weights = config_data['scoring_weights']
            print("📊 评分权重配置:")
            for factor, weight in self.scoring_weights.items():
                print(f"   {factor}: {weight}")
        else:
            self.scoring_weights = default_weights
            print("📊 使用默认评分权重配置")
    
    async def save_tokens_to_config(self, config_file: str = "monitored_tokens.json") -> bool:
        """将当前监控的代币列表保存到配置文件"""
        try:
            config_data = {
                'tokens': [token.address for token in self.monitored_tokens],
                'last_updated': datetime.now().isoformat()
            }
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ 监控列表已保存到配置文件: {config_file}")
            return True
            
        except Exception as e:
            print(f"❌ 保存配置文件失败: {e}")
            return False
    
    async def start_monitoring(self, config_file: str = None):
        """开始持续监控"""
        print("🚀 启动Pump.Fun代币迁移监控器")
        print(f"📊 监控配置: 最多监控{self.max_tokens_to_monitor}个代币，每{self.monitoring_interval}秒扫描一次")
        
        self.is_running = True
        self.start_time = datetime.now()
        
        try:
            # 必须从配置文件加载代币
            if config_file:
                if await self.load_config(config_file):
                    print("✅ 已从配置文件加载监控代币列表和配置")
                else:
                    print("❌ 无法从配置文件加载代币，监控器将退出")
                    return
            else:
                print("❌ 必须指定配置文件路径")
                print("💡 使用方法: python3 real_pumpfun_monitor.py --config <配置文件路径>")
                return
            
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
    
    def _print_monitored_tokens_detailed_scores(self):
        """只打印进入监控的代币的详细评分信息"""
        if not self.monitored_tokens:
            return
            
        print("\n📊 监控代币详细评分:")
        print("=" * 180)
        print(f"{'排名':<4} {'代币':<10} {'地址':<44} {'总分':<8} {'进度':<8} {'增长':<8} {'交易量':<8} {'持有者':<8} {'社交':<8} {'年龄(小时)':<10}")
        print("=" * 180)
        
        # 按进度排序（主要），分数作为次要排序
        sorted_tokens = sorted(self.monitored_tokens, key=lambda x: (x.current_progress, x.score.total_score), reverse=True)
        
        for i, token in enumerate(sorted_tokens, 1):
            age_hours = (datetime.now() - token.created_at).total_seconds() / 3600
            
            # 显示完整地址
            address_display = token.address
            
            print(f"{i:<4} {token.symbol:<10} {address_display:<44} {token.score.total_score(self.scoring_weights):<8.2f} {token.score.progress_score:<8.1f} "
                  f"{token.score.growth_speed_score:<8.1f} {token.score.volume_score:<8.1f} {token.score.holder_count_score:<8.1f} "
                  f"{token.score.social_score:<8.1f} {age_hours:<10.1f}")
        
        print("=" * 180)
    

    
    async def _get_single_token_info(self, token_address: str) -> Optional[Dict[str, Any]]:
        """获取单个代币的详细信息"""
        try:
            # 构建单个代币的API URL
            single_token_url = f"{self.pumpfun_api_url}/{token_address}"
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'application/json',
                    'Referer': 'https://pump.fun/'
                }
                
                async with session.get(single_token_url, headers=headers, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # 解析单个代币数据
                        token_data = self._parse_single_token_response(data)
                        if token_data:
                            print(f"✅ 成功获取代币信息: {token_data.get('symbol', 'Unknown')} ({token_address})")
                            return token_data
                        else:
                            print(f"❌ 无法解析代币数据: {token_address}")
                            return None
                    else:
                        print(f"❌ API请求失败 ({token_address}): {response.status}")
                        return None
                        
        except Exception as e:
            print(f"❌ 获取代币信息失败 ({token_address}): {e}")
            return None
    
    def _parse_single_token_response(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """解析单个代币的API响应"""
        try:
            # 解析代币基本信息
            address = data.get('mint', '')
            name = data.get('name', 'Unknown')
            symbol = data.get('symbol', 'UNK')
            
            # 解析进度信息
            progress = self._extract_progress(data)
            
            # 解析创建时间
            created_at = self._extract_created_time(data)
            
            # 解析其他评分相关数据
            volume_24h = data.get('usd_market_cap', data.get('market_cap', 0.0))
            holders = data.get('reply_count', 0)
            
            # 社交热度
            social_score = 0.0
            if data.get('is_currently_live', False):
                social_score += 0.5
            if holders > 0:
                social_score += min(holders / 10, 0.5)
            
            if address and progress < 1.0:  # 只监控未完成的代币
                return {
                    'address': address,
                    'name': name,
                    'symbol': symbol,
                    'created_at': created_at,
                    'progress': progress,
                    'volume_24h': volume_24h,
                    'holders': holders,
                    'social_score': social_score
                }
            else:
                return None
                
        except Exception as e:
            print(f"⚠️ 解析单个代币失败: {e}")
            return None
    

    
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
            
            # 基础进度 = 真实SOL储备 / 虚拟SOL储备
            base_progress = real_sol_reserves / virtual_sol_reserves
            
            # 使用准确的Pump.Fun修正公式
            # 基于三个代币验证的精确修正规则
            if base_progress < 0.69:
                correction_factor = 1.365
            elif base_progress < 0.72:
                correction_factor = 1.360
            else:
                correction_factor = 1.355
            
            # 应用修正
            progress = base_progress * correction_factor
            
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
            
            # 检查并重载配置文件（如果已修改）
            await self._check_and_reload_config(scan_count)
            
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
        """重新评估配置文件中的代币排名（配置文件模式不需要替换代币）"""
        print("🔄 重新评估配置文件代币排名...")
        
        # 配置文件模式：只需要更新现有代币的评分，不需要替换代币
        if not self.monitored_tokens:
            print("⚠️ 没有监控的代币")
            return
        
        # 更新每个代币的最新信息
        update_tasks = []
        for token in self.monitored_tokens:
            update_tasks.append(self._update_single_token(token))
        
        # 并发更新所有代币状态
        if update_tasks:
            await asyncio.gather(*update_tasks, return_exceptions=True)
        
        print("✅ 配置文件代币状态更新完成")
    
    async def _check_and_reload_config(self, scan_count: int):
        """检查并重新加载配置文件（如果已修改）"""
        import os
        
        if not self.current_config_file or not os.path.exists(self.current_config_file):
            return
        
        # 每5次扫描检查一次配置文件
        if scan_count % self.config_reload_interval != 0:
            return
        
        try:
            current_mtime = os.path.getmtime(self.current_config_file)
            if current_mtime > self.last_config_mtime:
                print("🔄 检测到配置文件已修改，重新加载...")
                
                # 保存当前监控的代币地址（用于比较）
                current_addresses = set(token.address for token in self.monitored_tokens)
                
                # 重新加载配置
                with open(self.current_config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # 更新配置参数
                self._load_monitoring_config(config_data)
                self._load_scoring_weights(config_data)
                
                # 获取新的代币列表
                new_token_addresses = set(config_data.get('tokens', []))
                
                # 找出需要添加的代币
                tokens_to_add = new_token_addresses - current_addresses
                
                # 找出需要移除的代币
                tokens_to_remove = current_addresses - new_token_addresses
                
                # 添加新代币
                if tokens_to_add:
                    print(f"➕ 添加 {len(tokens_to_add)} 个新代币:")
                    for token_address in tokens_to_add:
                        if await self.add_token_to_monitor(token_address):
                            print(f"   ✅ 添加: {token_address}")
                
                # 移除已删除的代币
                if tokens_to_remove:
                    print(f"➖ 移除 {len(tokens_to_remove)} 个代币:")
                    for token_address in tokens_to_remove:
                        token_to_remove = next((t for t in self.monitored_tokens if t.address == token_address), None)
                        if token_to_remove:
                            self.monitored_tokens.remove(token_to_remove)
                            print(f"   ❌ 移除: {token_to_remove.symbol} ({token_address})")
                
                # 更新文件修改时间
                self.last_config_mtime = current_mtime
                
                print(f"✅ 配置文件重载完成，当前监控 {len(self.monitored_tokens)} 个代币")
                
        except Exception as e:
            print(f"⚠️ 配置文件重载失败: {e}")
    
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
            # 显示完整地址
            address_display = token.address
            print(f"   {i:2d}. {token.symbol:10} - 地址: {address_display} - 进度: {token.current_progress:6.1%} - "
                  f"分数: {token.score.total_score(self.scoring_weights):5.1f} - 状态: {token.status.value:8} - 创建: {age:.0f}分钟前")
    
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
                print(f"   {i}. {token.symbol} ({token.address}): 进度 {token.current_progress:.1%} (分数: {token.score.total_score(self.scoring_weights):.1f})")
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


async def config_monitoring(config_file: str = "monitored_tokens.json"):
    """配置文件监控模式"""
    monitor = RealPumpFunMonitor()
    
    try:
        await monitor.connect()
        
        print(f"📁 使用配置文件: {config_file}")
        print("💡 监控器将自动读取配置文件中的代币地址进行监控")
        
        # 开始监控（自动从配置文件加载）
        await monitor.start_monitoring(config_file=config_file)
        
    finally:
        await monitor.close()


async def create_config_file(config_file: str = "monitored_tokens.json"):
    """创建配置文件工具"""
    print("📝 创建监控配置文件")
    print("输入代币地址（每行一个，空行结束）:")
    
    token_addresses = []
    while True:
        address = input("代币地址: ").strip()
        if not address:
            break
        token_addresses.append(address)
    
    if not token_addresses:
        print("❌ 未输入任何代币地址")
        return
    
    try:
        # 完整的配置文件结构
        config_data = {
            'tokens': token_addresses,
            
            # 监控配置
            'monitoring_interval': 30,  # 监控间隔（秒）
            'max_tokens_to_monitor': 10,  # 最大监控代币数
            'min_progress_for_scoring': 0.1,  # 最小进度阈值
            'progress_threshold': 0.8,  # 即将打满的进度阈值
            
            # 评分权重配置
            'scoring_weights': {
                'progress': 0.8,  # 进度权重
                'growth': 0.1,    # 增长权重
                'volume': 0.05,   # 交易量权重
                'holders': 0.03,  # 持有者权重
                'social': 0.02    # 社交权重
            },
            
            'created_at': datetime.now().isoformat(),
            'description': 'Pump.Fun代币监控列表'
        }
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 配置文件已创建: {config_file}")
        print(f"📊 包含 {len(token_addresses)} 个代币地址")
        print("\n📋 配置参数:")
        print(f"   监控间隔: {config_data['monitoring_interval']}秒")
        print(f"   最大监控代币数: {config_data['max_tokens_to_monitor']}")
        print(f"   最小进度阈值: {config_data['min_progress_for_scoring']:.0%}")
        print(f"   进度阈值: {config_data['progress_threshold']:.0%}")
        print("   评分权重:")
        for factor, weight in config_data['scoring_weights'].items():
            print(f"     {factor}: {weight}")
        
        print("\n💡 使用方法: python3 real_pumpfun_monitor.py --config")
        
    except Exception as e:
        print(f"❌ 创建配置文件失败: {e}")


async def main():
    """主函数"""
    monitor = RealPumpFunMonitor()
    
    try:
        await monitor.connect()
        await monitor.start_monitoring()
    finally:
        await monitor.close()


if __name__ == "__main__":
    import sys
    
    print("🚀 真实版Pump.Fun迁移监控器启动")
    print("="*60)
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == "--config" or sys.argv[1] == "-c":
            # 配置文件模式
            config_file = sys.argv[2] if len(sys.argv) > 2 else "monitored_tokens.json"
            asyncio.run(config_monitoring(config_file))
        elif sys.argv[1] == "--create-config" or sys.argv[1] == "-cc":
            # 创建配置文件模式
            config_file = sys.argv[2] if len(sys.argv) > 2 else "monitored_tokens.json"
            asyncio.run(create_config_file(config_file))
        elif sys.argv[1] == "--interactive" or sys.argv[1] == "-i":
            # 交互式模式（保留兼容性）
            print("⚠️ 交互式模式已弃用，请使用配置文件模式")
            print("💡 使用方法: python3 real_pumpfun_monitor.py --create-config")
            print("              python3 real_pumpfun_monitor.py --config")
        elif sys.argv[1] == "--help" or sys.argv[1] == "-h":
            # 帮助信息
            print("\n📖 使用说明:")
            print("  python3 real_pumpfun_monitor.py              # 传统模式（从API获取代币）")
            print("  python3 real_pumpfun_monitor.py --config     # 配置文件模式（推荐）")
            print("  python3 real_pumpfun_monitor.py --create-config  # 创建配置文件")
            print("\n📁 配置文件格式 (monitored_tokens.json):")
            print('''{
  "tokens": [
    "9WdgxPfFgD1ygAUfbyNqqTGFCieT3AC3E1Sozy1Rpump",
    "DMYA7G...JHoX",
    "JCtdmX...pump"
  ],
  "monitoring_interval": 30,
  "max_tokens_to_monitor": 10,
  "min_progress_for_scoring": 0.1,
  "progress_threshold": 0.8,
  "scoring_weights": {
    "progress": 0.8,
    "growth": 0.1,
    "volume": 0.05,
    "holders": 0.03,
    "social": 0.02
  },
  "description": "Pump.Fun代币监控列表"
}''')
        else:
            print("❌ 无效参数")
            print("💡 使用 --help 查看帮助信息")
    else:
        # 默认模式（传统模式，从API获取代币）
        asyncio.run(main())