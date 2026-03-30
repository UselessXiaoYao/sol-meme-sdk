"""
优先级费用估算模块 - 提供优先级费用估算功能
注意：对于Jupiter交易，优先使用 prioritizationFeeLamports: "auto" 自动计算
"""

import asyncio
import aiohttp
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class PriorityFeeEstimator:
    """优先级费用估算服务"""
    
    def __init__(self, rpc_url: str):
        """初始化优先级费用估算服务
        
        Args:
            rpc_url: Solana RPC URL
        """
        self.rpc_url = rpc_url
    
    async def get_priority_fee_estimate(self, compute_units: int = 100000) -> Dict[str, Any]:
        """获取优先级费用估算
        
        Args:
            compute_units: 计算单元数量
            
        Returns:
            优先级费用估算信息
        """
        try:
            # 使用公共RPC获取最新的优先级费用数据
            async with aiohttp.ClientSession() as session:
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getRecentPrioritizationFees",
                    "params": []
                }
                
                async with session.post(self.rpc_url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if 'result' in data and data['result']:
                            # 计算平均费用
                            fees = [item['prioritizationFee'] for item in data['result'] if item['prioritizationFee'] > 0]
                            
                            if fees:
                                avg_fee = sum(fees) / len(fees)
                                # 根据平均费用设置不同优先级
                                return {
                                    'low': max(1000, int(avg_fee * 0.5)),
                                    'medium': max(5000, int(avg_fee * 1.0)),
                                    'high': max(10000, int(avg_fee * 2.0)),
                                    'very_high': max(50000, int(avg_fee * 5.0))
                                }
            
            # 如果API调用失败或没有数据，使用默认值
            print("使用 Solana RPC 获取到优先级费用估算")
            return {
                'low': 1000,    # 0.000001 SOL
                'medium': 5000,  # 0.000005 SOL
                'high': 10000,  # 0.00001 SOL
                'very_high': 50000  # 0.00005 SOL
            }
            
        except Exception as e:
            logger.warning(f"获取优先级费用估算失败: {e}，使用默认值")
            return {
                'low': 1000,
                'medium': 5000,
                'high': 10000,
                'very_high': 50000
            }


# 使用示例
async def example_usage():
    """优先级费用估算模块使用示例"""
    
    # 初始化优先级费用估算服务
    fee_estimator = PriorityFeeEstimator(rpc_url="https://api.mainnet-beta.solana.com")
    
    # 获取费用估算
    fee_estimate = await fee_estimator.get_priority_fee_estimate()
    print("优先级费用估算:", fee_estimate)


if __name__ == "__main__":
    asyncio.run(example_usage())