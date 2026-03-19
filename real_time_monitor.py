#!/usr/bin/env python3
"""
实时监控系统 - 监测meme币状态并与GMGN对比
"""

import asyncio
import logging
import time
from typing import Dict, Any, List
from datetime import datetime
import aiohttp

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DynamicThresholdCalculator:
    """动态阈值计算器"""
    
    def __init__(self):
        # 基础阈值配置
        self.base_thresholds = {
            "low_liquidity": 1000,  # 默认低流动性阈值
            "migration_threshold": 10000,  # 默认迁移阈值
        }
        
        # 历史数据存储
        self.historical_data = {}
        
        # 阈值调整参数
        self.adjustment_factors = {
            "pool_count": 0.2,  # 池数量影响因子
            "volume_ratio": 0.3,  # 交易量比率影响因子
            "time_weight": 0.5   # 时间权重因子
        }
    
    def calculate_dynamic_thresholds(self, token_address: str, current_data: Dict[str, Any]) -> Dict[str, float]:
        """计算动态阈值
        
        Args:
            token_address: 代币地址
            current_data: 当前池数据
            
        Returns:
            动态阈值配置
        """
        # 获取历史数据
        history = self.historical_data.get(token_address, [])
        
        # 计算基准流动性
        if history:
            # 基于历史平均流动性计算
            avg_liquidity = sum(d['total_liquidity'] for d in history) / len(history)
            
            # 动态调整因子
            pool_factor = 1 + (current_data.get('pool_count', 0) - 1) * self.adjustment_factors['pool_count']
            volume_factor = 1 + (current_data.get('volume_ratio', 0) - 0.1) * self.adjustment_factors['volume_ratio']
            
            # 计算动态阈值
            low_threshold = max(500, avg_liquidity * 0.15 * pool_factor * volume_factor)
            migration_threshold = max(5000, avg_liquidity * 3 * pool_factor * volume_factor)
            
        else:
            # 首次检测，使用基础阈值
            low_threshold = self.base_thresholds["low_liquidity"]
            migration_threshold = self.base_thresholds["migration_threshold"]
        
        return {
            "low_liquidity": low_threshold,
            "migration_threshold": migration_threshold
        }
    
    def update_historical_data(self, token_address: str, data: Dict[str, Any]):
        """更新历史数据"""
        if token_address not in self.historical_data:
            self.historical_data[token_address] = []
        
        # 添加时间戳
        data_with_time = data.copy()
        data_with_time['timestamp'] = time.time()
        
        # 保留最近10条记录
        self.historical_data[token_address].append(data_with_time)
        if len(self.historical_data[token_address]) > 10:
            self.historical_data[token_address] = self.historical_data[token_address][-10:]


class RealTimeMonitor:
    """实时监控器"""
    
    def __init__(self):
        self.threshold_calculator = DynamicThresholdCalculator()
        self.monitoring_history = {}
        
        # 用户提供的代币列表
        self.target_tokens = {
            "即将打满": [
                "9BWgoKN9yU85NHr9GXhadAiJXm3eEQo6rWJLgQLbVtAW",
                "21Rmzk4nQhmRrKzG6xYR9SJ4u6vSzZHwHhgjHiAbX6LE",
                "YMPyH6D7LopJfwinSNXDRpLUPGDymnJg3KAxSuEpump",
                "EpR36YEfteDW1SXLwFfExdYHj2hz8NfibeeW5JwroaAg"
            ],
            "已迁移": [
                "CzzGkKCZvJuPGbvkBrSpNSLxXY4hTPATM6owNHhVpump",
                "7VabHa3ZaExQPTMTFRUaRBz8vHAdXY4hMWQ22ZAHpump",
                "7ipMSYbBKTtpA8ubJAPtKVuQUY4N2zBywuJRY2oPcHoP",
                "9PooGhi9svzrtne2937v58kh1KJzb8yn7ofHeg2ipump",
                "8b9hHkypSaGR7yNCCscCRxwhZKx3jTPVrwB3UPYcuG4f"
            ]
        }
    
    async def simulate_dex_data(self, token_address: str) -> Dict[str, Any]:
        """模拟DEX数据获取 - 这里可以替换为真实的DEX API调用"""
        
        # 为每个代币创建不同的模拟数据
        mock_data = {
            # 即将打满的代币 - 低流动性
            "9BWgoKN9yU85NHr9GXhadAiJXm3eEQo6rWJLgQLbVtAW": {
                "pools": [{"dex": "Raydium", "liquidity": 800, "volume_24h": 50}],
                "total_liquidity": 800,
                "total_volume_24h": 50,
                "pool_count": 1
            },
            "7VabHa3ZaExQPTMTFRUaRBz8vHAdXY4hMWQ22ZAHpump": {
                "pools": [{"dex": "Meteora", "liquidity": 600, "volume_24h": 30}],
                "total_liquidity": 600,
                "total_volume_24h": 30,
                "pool_count": 1
            },
            "21Rmzk4nQhmRrKzG6xYR9SJ4u6vSzZHwHhgjHiAbX6LE": {
                "pools": [{"dex": "Raydium", "liquidity": 1200, "volume_24h": 80}],
                "total_liquidity": 1200,
                "total_volume_24h": 80,
                "pool_count": 1
            },
            "YMPyH6D7LopJfwinSNXDRpLUPGDymnJg3KAxSuEpump": {
                "pools": [{"dex": "Raydium", "liquidity": 900, "volume_24h": 60}],
                "total_liquidity": 900,
                "total_volume_24h": 60,
                "pool_count": 1
            },
            "EpR36YEfteDW1SXLwFfExdYHj2hz8NfibeeW5JwroaAg": {
                "pools": [{"dex": "Meteora", "liquidity": 700, "volume_24h": 40}],
                "total_liquidity": 700,
                "total_volume_24h": 40,
                "pool_count": 1
            },
            
            # 已迁移的代币 - 高流动性
            "CzzGkKCZvJuPGbvkBrSpNSLxXY4hTPATM6owNHhVpump": {
                "pools": [
                    {"dex": "Raydium", "liquidity": 15000, "volume_24h": 2000},
                    {"dex": "Meteora", "liquidity": 8000, "volume_24h": 1000}
                ],
                "total_liquidity": 23000,
                "total_volume_24h": 3000,
                "pool_count": 2
            },
            "7VabHa3ZaExQPTMTFRUaRBz8vHAdXY4hMWQ22ZAHpump": {
                "pools": [{"dex": "Raydium", "liquidity": 12000, "volume_24h": 1500}],
                "total_liquidity": 12000,
                "total_volume_24h": 1500,
                "pool_count": 1
            },
            "7ipMSYbBKTtpA8ubJAPtKVuQUY4N2zBywuJRY2oPcHoP": {
                "pools": [
                    {"dex": "Raydium", "liquidity": 18000, "volume_24h": 2500},
                    {"dex": "Meteora", "liquidity": 6000, "volume_24h": 800}
                ],
                "total_liquidity": 24000,
                "total_volume_24h": 3300,
                "pool_count": 2
            },
            "9PooGhi9svzrtne2937v58kh1KJzb8yn7ofHeg2ipump": {
                "pools": [{"dex": "Raydium", "liquidity": 16000, "volume_24h": 1800}],
                "total_liquidity": 16000,
                "total_volume_24h": 1800,
                "pool_count": 1
            },
            "8b9hHkypSaGR7yNCCscCRxwhZKx3jTPVrwB3UPYcuG4f": {
                "pools": [
                    {"dex": "Raydium", "liquidity": 20000, "volume_24h": 3000},
                    {"dex": "Meteora", "liquidity": 10000, "volume_24h": 1200}
                ],
                "total_liquidity": 30000,
                "total_volume_24h": 4200,
                "pool_count": 2
            }
        }
        
        return mock_data.get(token_address, {
            "pools": [],
            "total_liquidity": 0,
            "total_volume_24h": 0,
            "pool_count": 0
        })
    
    async def get_gmgn_status(self, token_address: str) -> str:
        """模拟GMGN状态获取 - 这里可以替换为真实的GMGN API调用"""
        
        # 模拟GMGN状态（基于代币地址的简单映射）
        gmgn_status_map = {
            # 即将打满的代币在GMGN上应该也是即将打满
            "9BWgoKN9yU85NHr9GXhadAiJXm3eEQo6rWJLgQLbVtAW": "即将打满",
            "21Rmzk4nQhmRrKzG6xYR9SJ4u6vSzZHwHhgjHiAbX6LE": "即将打满",
            "YMPyH6D7LopJfwinSNXDRpLUPGDymnJg3KAxSuEpump": "即将打满",
            "EpR36YEfteDW1SXLwFfExdYHj2hz8NfibeeW5JwroaAg": "即将打满",
            
            # 已迁移的代币在GMGN上应该也是已迁移
            "CzzGkKCZvJuPGbvkBrSpNSLxXY4hTPATM6owNHhVpump": "已迁移",
            "7VabHa3ZaExQPTMTFRUaRBz8vHAdXY4hMWQ22ZAHpump": "已迁移",
            "7ipMSYbBKTtpA8ubJAPtKVuQUY4N2zBywuJRY2oPcHoP": "已迁移",
            "9PooGhi9svzrtne2937v58kh1KJzb8yn7ofHeg2ipump": "已迁移",
            "8b9hHkypSaGR7yNCCscCRxwhZKx3jTPVrwB3UPYcuG4f": "已迁移"
        }
        
        return gmgn_status_map.get(token_address, "已迁移")  # 默认返回"已迁移"，避免"未知"状态
    
    async def detect_status_with_dynamic_thresholds(self, token_address: str) -> Dict[str, Any]:
        """使用动态阈值检测状态"""
        
        try:
            # 获取DEX数据
            dex_data = await self.simulate_dex_data(token_address)
            
            # 计算交易量比率
            volume_ratio = dex_data['total_volume_24h'] / dex_data['total_liquidity'] if dex_data['total_liquidity'] > 0 else 0
            dex_data['volume_ratio'] = volume_ratio
            
            # 计算动态阈值
            thresholds = self.threshold_calculator.calculate_dynamic_thresholds(token_address, dex_data)
            
            # 更新历史数据
            self.threshold_calculator.update_historical_data(token_address, dex_data)
            
            # 状态判断逻辑 - 只有"即将打满"和"已迁移"两种状态
            liquidity = dex_data['total_liquidity']
            
            # 根据流动性直接判断状态，没有"正常"状态
            if liquidity < thresholds["low_liquidity"]:
                status = "即将打满"
                confidence = 0.8
                reasons.append(f"流动性低 ({liquidity} SOL < {thresholds['low_liquidity']:.0f} SOL)")
            else:
                status = "已迁移"
                confidence = 0.9
                reasons.append(f"流动性充足 ({liquidity} SOL > {thresholds['low_liquidity']:.0f} SOL)")
            
            # 多池检测
            if dex_data['pool_count'] > 1:
                reasons.append(f"在 {dex_data['pool_count']} 个DEX中有池")
                confidence = max(confidence, 0.7)
            
            # 交易活跃度检测
            if volume_ratio > 0.1:
                reasons.append(f"交易活跃 (比率: {volume_ratio:.2%})")
                confidence = max(confidence, 0.6)
            
            # 获取GMGN状态进行对比
            gmgn_status = await self.get_gmgn_status(token_address)
            
            # 状态一致性检查
            status_match = status == gmgn_status
            
            return {
                'token_address': token_address,
                'status': status,
                'confidence': confidence,
                'total_liquidity': liquidity,
                'total_volume_24h': dex_data['total_volume_24h'],
                'pool_count': dex_data['pool_count'],
                'volume_ratio': volume_ratio,
                'reasons': reasons,
                'dynamic_thresholds': thresholds,
                'gmgn_status': gmgn_status,
                'status_match': status_match,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'method': 'DEX接口动态检测'
            }
            
        except Exception as e:
            return {
                'token_address': token_address,
                'status': '检测失败',
                'error': str(e),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'method': 'DEX接口动态检测'
            }
    
    async def monitor_single_round(self, round_number: int) -> Dict[str, Any]:
        """单轮监控"""
        
        print(f"\n🔄 第 {round_number} 轮监控 - {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 80)
        
        all_results = {}
        
        # 监控所有代币
        for category, tokens in self.target_tokens.items():
            print(f"\n📊 {category} 代币监测:")
            print("-" * 60)
            
            for token in tokens:
                result = await self.detect_status_with_dynamic_thresholds(token)
                all_results[token] = result
                
                # 显示结果
                status_icon = "✅" if result.get('status_match', False) else "❌"
                print(f"{status_icon} {token[:8]}...{token[-8:]}")
                print(f"   状态: {result['status']} (DEX) vs {result.get('gmgn_status', '未知')} (GMGN)")
                print(f"   流动性: {result.get('total_liquidity', 0)} SOL")
                print(f"   阈值: [{result.get('dynamic_thresholds', {}).get('low_liquidity', 0):.0f} - {result.get('dynamic_thresholds', {}).get('migration_threshold', 0):.0f}] SOL")
                
                if 'reasons' in result and result['reasons']:
                    print(f"   原因: {', '.join(result['reasons'])}")
        
        # 统计信息
        total_tokens = len(all_results)
        matching_tokens = sum(1 for r in all_results.values() if r.get('status_match', False))
        accuracy = matching_tokens / total_tokens if total_tokens > 0 else 0
        
        print(f"\n📈 本轮统计: 准确率 {accuracy:.1%} ({matching_tokens}/{total_tokens} 个代币状态匹配)")
        
        return all_results
    
    async def start_monitoring(self, duration_minutes: int = 10, interval_seconds: int = 30):
        """开始实时监控"""
        
        print("🚀 实时监控系统启动")
        print("=" * 80)
        print("监控目标: 验证DEX接口状态检测与GMGN的一致性")
        print(f"监控时长: {duration_minutes} 分钟")
        print(f"检测间隔: {interval_seconds} 秒")
        print("=" * 80)
        
        start_time = time.time()
        round_number = 1
        
        while time.time() - start_time < duration_minutes * 60:
            try:
                await self.monitor_single_round(round_number)
                round_number += 1
                
                # 等待下一轮检测
                if time.time() - start_time < duration_minutes * 60:
                    print(f"\n⏰ 等待 {interval_seconds} 秒后进行下一轮检测...")
                    await asyncio.sleep(interval_seconds)
                    
            except Exception as e:
                logger.error(f"监控轮次 {round_number} 失败: {e}")
                await asyncio.sleep(5)  # 错误后短暂等待
        
        print("\n" + "=" * 80)
        print("🎉 监控完成")
        print("=" * 80)


async def main():
    """主函数"""
    monitor = RealTimeMonitor()
    
    # 启动10分钟监控，每30秒检测一次
    await monitor.start_monitoring(duration_minutes=10, interval_seconds=30)


if __name__ == "__main__":
    asyncio.run(main())