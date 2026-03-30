#!/usr/bin/env python3
"""
DEX接口直接检测meme币状态功能验证
测试是否可以直接通过DEX接口获取"即将打满"和"已迁移"状态
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from src.sol_meme_sdk.multi_dex_client import MultiDexClient
from src.sol_meme_sdk.raydium_client import RaydiumClient
from src.sol_meme_sdk.meteora_client import MeteoraClient
from src.sol_meme_sdk.exceptions import TradingError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DEXStatusDetector:
    """DEX状态检测器 - 直接通过DEX接口分析meme币状态"""
    
    def __init__(self, network: str = "mainnet"):
        """初始化检测器
        
        Args:
            network: 网络类型
        """
        self.network = network
        self.multi_dex_client = MultiDexClient(network=network)
        self.raydium_client = RaydiumClient(network=network)
        self.meteora_client = MeteoraClient(network=network)
        
        # 状态检测阈值配置
        self.status_thresholds = {
            "low_liquidity": 1000,  # 低流动性阈值 (SOL)
            "migration_threshold": 10000,  # 迁移阈值 (SOL)
            "volume_ratio_threshold": 0.1,  # 交易量/流动性比率阈值
            "price_volatility_threshold": 0.3,  # 价格波动阈值
        }
    
    async def connect(self):
        """连接到网络"""
        await self.multi_dex_client.connect()
        await self.raydium_client.connect()
        await self.meteora_client.connect()
        logger.info("✅ 已连接到所有DEX客户端")
    
    async def close(self):
        """关闭连接"""
        await self.meteora_client.close()
        await self.raydium_client.close()
        await self.multi_dex_client.close()
        logger.info("🔌 已断开所有连接")
    
    async def analyze_token_pools(self, token_address: str) -> Dict[str, Any]:
        """分析代币在所有DEX中的池信息
        
        Args:
            token_address: 代币地址
            
        Returns:
            池分析结果
        """
        try:
            # 获取Raydium池信息
            raydium_pools = await self.raydium_client.get_raydium_pools()
            token_raydium_pools = []
            
            # 在Raydium池中搜索包含该代币的池
            for pool_type in ['official', 'unOfficial']:
                if pool_type in raydium_pools:
                    for pool in raydium_pools[pool_type]:
                        if (pool.get('baseMint') == token_address or 
                            pool.get('quoteMint') == token_address):
                            pool_info = {
                                'dex': 'Raydium',
                                'pool_address': pool.get('id'),
                                'base_mint': pool.get('baseMint'),
                                'quote_mint': pool.get('quoteMint'),
                                'liquidity': pool.get('liquidity', 0),
                                'volume_24h': pool.get('volume24h', 0),
                                'price': pool.get('price', 0)
                            }
                            token_raydium_pools.append(pool_info)
            
            # 获取Meteora池信息
            meteora_pools = await self.meteora_client.get_market_pools()
            token_meteora_pools = []
            
            if 'pools' in meteora_pools:
                for pool in meteora_pools['pools']:
                    token_x = pool.get('token_x', {})
                    token_y = pool.get('token_y', {})
                    
                    if (token_x.get('address') == token_address or 
                        token_y.get('address') == token_address):
                        pool_info = {
                            'dex': 'Meteora',
                            'pool_address': pool.get('address'),
                            'base_mint': token_x.get('address'),
                            'quote_mint': token_y.get('address'),
                            'liquidity': pool.get('tvl', 0),
                            'volume_24h': pool.get('volume', {}).get('24h', 0),
                            'price': pool.get('current_price', 0)
                        }
                        token_meteora_pools.append(pool_info)
            
            # 合并所有池信息
            all_pools = token_raydium_pools + token_meteora_pools
            
            return {
                'token_address': token_address,
                'total_pools': len(all_pools),
                'pools': all_pools,
                'raydium_pools': len(token_raydium_pools),
                'meteora_pools': len(token_meteora_pools)
            }
            
        except Exception as e:
            logger.error(f"分析代币池信息失败: {e}")
            return {
                'token_address': token_address,
                'total_pools': 0,
                'pools': [],
                'error': str(e)
            }
    
    async def get_pool_historical_data(self, pool_address: str, dex: str) -> Dict[str, Any]:
        """获取池的历史数据（模拟实现）
        
        Args:
            pool_address: 池地址
            dex: DEX名称
            
        Returns:
            历史数据分析
        """
        # 这里可以集成DEX历史数据API
        # 暂时返回模拟数据
        return {
            'pool_address': pool_address,
            'dex': dex,
            'liquidity_change_24h': 0.15,  # 24小时流动性变化率
            'volume_change_24h': 0.25,     # 24小时交易量变化率
            'price_change_24h': 0.08,      # 24小时价格变化率
            'unique_traders_24h': 45,      # 24小时独立交易者数量
            'average_trade_size': 0.5      # 平均交易规模 (SOL)
        }
    
    async def detect_migration_status(self, token_address: str) -> Dict[str, Any]:
        """检测meme币的迁移状态
        
        Args:
            token_address: 代币地址
            
        Returns:
            状态检测结果
        """
        try:
            # 分析代币池信息
            pool_analysis = await self.analyze_token_pools(token_address)
            
            if pool_analysis['total_pools'] == 0:
                return {
                    'token_address': token_address,
                    'status': '无池',
                    'confidence': 1.0,
                    'reason': '未在任何DEX找到该代币的流动性池',
                    'details': pool_analysis
                }
            
            # 分析池状态
            total_liquidity = sum(pool.get('liquidity', 0) for pool in pool_analysis['pools'])
            total_volume_24h = sum(pool.get('volume_24h', 0) for pool in pool_analysis['pools'])
            
            # 计算关键指标
            volume_ratio = total_volume_24h / total_liquidity if total_liquidity > 0 else 0
            avg_pool_size = total_liquidity / pool_analysis['total_pools'] if pool_analysis['total_pools'] > 0 else 0
            
            # 状态判断逻辑
            status = "正常"
            confidence = 0.5
            reasons = []
            
            # 低流动性检测 - "即将打满"状态
            if total_liquidity < self.status_thresholds["low_liquidity"]:
                status = "即将打满"
                confidence = 0.7
                reasons.append(f"总流动性低 ({total_liquidity:.2f} SOL < {self.status_thresholds['low_liquidity']} SOL)")
            
            # 高流动性增长检测 - "已迁移"状态
            elif total_liquidity > self.status_thresholds["migration_threshold"]:
                status = "已迁移"
                confidence = 0.8
                reasons.append(f"流动性充足 ({total_liquidity:.2f} SOL > {self.status_thresholds['migration_threshold']} SOL)")
            
            # 高交易量比率检测
            if volume_ratio > self.status_thresholds["volume_ratio_threshold"]:
                if status == "正常":
                    status = "活跃"
                reasons.append(f"交易活跃 (交易量/流动性比率: {volume_ratio:.2%})")
                confidence = max(confidence, 0.6)
            
            # 多池存在检测
            if pool_analysis['total_pools'] > 1:
                reasons.append(f"在 {pool_analysis['total_pools']} 个DEX中有流动性池")
                confidence = max(confidence, 0.6)
            
            return {
                'token_address': token_address,
                'status': status,
                'confidence': confidence,
                'total_liquidity': total_liquidity,
                'total_volume_24h': total_volume_24h,
                'volume_ratio': volume_ratio,
                'pool_count': pool_analysis['total_pools'],
                'reasons': reasons,
                'pools_details': pool_analysis['pools'],
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"检测迁移状态失败: {e}")
            return {
                'token_address': token_address,
                'status': '检测失败',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def monitor_token_status_changes(self, token_address: str, duration_minutes: int = 5) -> Dict[str, Any]:
        """监控代币状态变化
        
        Args:
            token_address: 代币地址
            duration_minutes: 监控时长（分钟）
            
        Returns:
            状态变化分析
        """
        status_history = []
        start_time = datetime.now()
        
        logger.info(f"🔍 开始监控代币 {token_address}，时长 {duration_minutes} 分钟")
        
        for i in range(duration_minutes):
            current_status = await self.detect_migration_status(token_address)
            status_history.append(current_status)
            
            logger.info(f"[{i+1}/{duration_minutes}] 状态: {current_status['status']} "
                       f"(流动性: {current_status.get('total_liquidity', 0):.2f} SOL)")
            
            if i < duration_minutes - 1:  # 不是最后一次迭代
                await asyncio.sleep(60)  # 等待1分钟
        
        # 分析状态变化
        status_changes = []
        for i in range(1, len(status_history)):
            prev_status = status_history[i-1]['status']
            curr_status = status_history[i]['status']
            
            if prev_status != curr_status:
                status_changes.append({
                    'time_index': i,
                    'from': prev_status,
                    'to': curr_status,
                    'timestamp': status_history[i]['timestamp']
                })
        
        return {
            'token_address': token_address,
            'monitoring_duration': duration_minutes,
            'start_time': start_time.isoformat(),
            'end_time': datetime.now().isoformat(),
            'initial_status': status_history[0] if status_history else None,
            'final_status': status_history[-1] if status_history else None,
            'status_changes': status_changes,
            'status_history': status_history,
            'total_status_changes': len(status_changes)
        }


async def test_specific_token():
    """测试特定代币的状态检测"""
    detector = DEXStatusDetector(network="mainnet")
    
    try:
        await detector.connect()
        
        # 测试代币: H7GUQj13vePxBiPADxty3G8z5KcodRsHTiGnwbcBAGS
        token_address = "H7GUQj13vePxBiPADxty3G8z5KcodRsHTiGnwbcBAGS"
        
        logger.info(f"🎯 测试代币: {token_address}")
        
        # 1. 分析池信息
        logger.info("📊 分析代币池信息...")
        pool_analysis = await detector.analyze_token_pools(token_address)
        print("\n=== 池分析结果 ===")
        print(json.dumps(pool_analysis, indent=2, ensure_ascii=False))
        
        # 2. 检测迁移状态
        logger.info("🔍 检测迁移状态...")
        status_result = await detector.detect_migration_status(token_address)
        print("\n=== 状态检测结果 ===")
        print(json.dumps(status_result, indent=2, ensure_ascii=False))
        
        # 3. 短期监控（2分钟）
        logger.info("⏰ 开始短期状态监控...")
        monitoring_result = await detector.monitor_token_status_changes(token_address, duration_minutes=2)
        print("\n=== 监控结果 ===")
        print(json.dumps({
            'token_address': monitoring_result['token_address'],
            'status_changes': monitoring_result['status_changes'],
            'initial_status': monitoring_result['initial_status']['status'],
            'final_status': monitoring_result['final_status']['status'],
            'total_changes': monitoring_result['total_status_changes']
        }, indent=2, ensure_ascii=False))
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
    finally:
        await detector.close()


async def test_multiple_tokens():
    """测试多个代币的状态检测"""
    detector = DEXStatusDetector(network="mainnet")
    
    try:
        await detector.connect()
        
        # 测试多个代币
        test_tokens = [
            "H7GUQj13vePxBiPADxty3G8z5KcodRsHTiGnwbcBAGS",  # 目标代币
            "So11111111111111111111111111111111111111112",   # SOL (高流动性)
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"   # USDC (高流动性)
        ]
        
        results = []
        
        for token_address in test_tokens:
            logger.info(f"🔍 检测代币: {token_address}")
            
            try:
                status_result = await detector.detect_migration_status(token_address)
                results.append(status_result)
                
                print(f"\n=== {token_address} ===")
                print(f"状态: {status_result['status']}")
                print(f"流动性: {status_result.get('total_liquidity', 0):.2f} SOL")
                print(f"置信度: {status_result.get('confidence', 0):.2f}")
                print(f"原因: {', '.join(status_result.get('reasons', []))}")
                
            except Exception as e:
                logger.error(f"检测代币 {token_address} 失败: {e}")
                results.append({
                    'token_address': token_address,
                    'status': '检测失败',
                    'error': str(e)
                })
        
        # 汇总结果
        print("\n=== 汇总结果 ===")
        for result in results:
            print(f"{result['token_address']}: {result['status']}")
        
    except Exception as e:
        logger.error(f"多代币测试失败: {e}")
    finally:
        await detector.close()


async def main():
    """主函数"""
    print("🚀 DEX接口状态检测功能验证")
    print("=" * 50)
    
    # 选择测试模式
    print("选择测试模式:")
    print("1. 测试特定代币 (H7GUQj13vePxBiPADxty3G8z5KcodRsHTiGnwbcBAGS)")
    print("2. 测试多个代币对比")
    
    try:
        choice = input("请输入选择 (1 或 2): ").strip()
        
        if choice == "1":
            await test_specific_token()
        elif choice == "2":
            await test_multiple_tokens()
        else:
            print("无效选择，默认测试特定代币")
            await test_specific_token()
            
    except KeyboardInterrupt:
        print("\n👋 用户中断测试")
    except Exception as e:
        print(f"❌ 测试异常: {e}")


if __name__ == "__main__":
    asyncio.run(main())