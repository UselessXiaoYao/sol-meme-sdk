"""
RPC价格提供器 - 直接从Solana节点RPC获取代币价格
通过解析DEX池子的链上数据来计算实时价格
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solders.pubkey import Pubkey
from decimal import Decimal

from .unified_config import UnifiedConfig

logger = logging.getLogger(__name__)


class RPCPriceProvider:
    """RPC价格提供器 - 直接从节点RPC获取实时价格"""
    
    # Raydium池子数据结构常量 (基于Raydium AMM V4)
    RAYDIUM_POOL_LAYOUT = {
        'base_mint': (8, 40),      # 基础代币mint地址
        'quote_mint': (40, 72),    # 报价代币mint地址
        'base_amount': (72, 80),   # 基础代币数量
        'quote_amount': (80, 88),  # 报价代币数量
        'lp_mint': (104, 136),     # LP代币mint地址
        'lp_supply': (136, 144)    # LP代币供应量
    }
    
    # 已知的Raydium池子地址 (SOL-USDC, SOL-USDT等)
    KNOWN_POOLS = {
        "mainnet-beta": {
            "SOL-USDC": "58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2",
            "SOL-USDT": "7XawhbbxtsRcQA8KTkHT9f9nTxftvGQ6q5cJWyWzFFWb",
            "USDC-USDT": "Hk8mDAJFq2B3dS2kX1F3m5wmJYT2D5rqD8L6Q2nY7oJz"
        },
        "devnet": {
            "SOL-USDC": "5rQ5L9h5Y3XvXj5P5P5P5P5P5P5P5P5P5P5P5P5P5P5P",  # 示例地址
        }
    }
    
    def __init__(self, rpc_url: Optional[str] = None, network: str = "mainnet-beta"):
        """初始化RPC价格提供器
        
        Args:
            rpc_url: Solana RPC URL
            network: 网络类型 (mainnet-beta, devnet, testnet)
        """
        self.config = UnifiedConfig()
        self.rpc_url = rpc_url or self.config.solana_rpc_endpoint
        self.network = network
        self.client = AsyncClient(self.rpc_url)
        
        # 常用代币地址
        self.common_tokens = {
            "SOL": "So11111111111111111111111111111111111111112",
            "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"
        }
        
        if network == "devnet":
            self.common_tokens["USDC"] = "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU"
        
        logger.info(f"RPCPriceProvider initialized for {network}")
    
    async def connect(self):
        """连接到Solana网络"""
        await self.client.__aenter__()
    
    async def close(self):
        """关闭连接"""
        await self.client.__aexit__(None, None, None)
    
    async def get_pool_info(self, pool_address: str) -> Dict[str, Any]:
        """获取Raydium池子的详细信息
        
        Args:
            pool_address: 池账户地址
            
        Returns:
            池信息字典，包含代币数量和价格
        """
        try:
            pool_pubkey = Pubkey.from_string(pool_address)
            account_info = await self.client.get_account_info(pool_pubkey, commitment=Confirmed)
            
            if not account_info.value:
                raise Exception(f"池账户不存在: {pool_address}")
                
            data = account_info.value.data
            
            # 解析Raydium AMM池结构
            pool_info = {}
            for field, (start, end) in self.RAYDIUM_POOL_LAYOUT.items():
                if field.endswith('_mint'):
                    # 处理mint地址
                    pool_info[field] = str(Pubkey(data[start:end]))
                else:
                    # 处理数值
                    pool_info[field] = int.from_bytes(data[start:end], 'little')
            
            # 计算价格
            if pool_info['base_amount'] > 0 and pool_info['quote_amount'] > 0:
                # 价格 = 报价代币数量 / 基础代币数量
                pool_info['price'] = Decimal(pool_info['quote_amount']) / Decimal(pool_info['base_amount'])
                
                # 考虑代币小数位数（简化处理）
                # 假设基础代币和报价代币都有6位小数
                pool_info['price_normalized'] = pool_info['price']
            
            pool_info['pool_address'] = pool_address
            pool_info['owner_program'] = str(account_info.value.owner)
            
            return pool_info
            
        except Exception as e:
            raise Exception(f"获取池信息失败: {e}")
    
    async def find_pools_for_token(self, token_address: str) -> List[Dict[str, Any]]:
        """查找包含特定代币的池子
        
        Args:
            token_address: 目标代币地址
            
        Returns:
            包含目标代币的池子列表
        """
        pools = []
        
        # 如果是SOL本身，创建一个虚拟池子
        if token_address == self.common_tokens["SOL"]:
            pools.append({
                'pool_name': 'SOL_BASE',
                'token_price': 1.0,
                'price_direction': 'SOL -> SOL',
                'base_mint': self.common_tokens["SOL"],
                'quote_mint': self.common_tokens["SOL"],
                'base_amount': 1e9,
                'quote_amount': 1e9,
                'liquidity': 1e9
            })
            return pools
        
        # 首先检查已知池子
        known_pools = self.KNOWN_POOLS.get(self.network, {})
        
        for pool_name, pool_address in known_pools.items():
            try:
                pool_info = await self.get_pool_info(pool_address)
                
                # 检查池子是否包含目标代币
                if (pool_info.get('base_mint') == token_address or 
                    pool_info.get('quote_mint') == token_address):
                    
                    # 确定价格方向
                    if pool_info['base_mint'] == token_address:
                        # 目标代币是基础代币，价格 = quote/base
                        pool_info['token_price'] = float(pool_info['price'])
                        pool_info['price_direction'] = 'token -> quote'
                    else:
                        # 目标代币是报价代币，价格 = base/quote
                        pool_info['token_price'] = 1.0 / float(pool_info['price'])
                        pool_info['price_direction'] = 'token -> base'
                    
                    # 计算流动性
                    pool_info['liquidity'] = pool_info.get('base_amount', 0) + pool_info.get('quote_amount', 0)
                    pool_info['pool_name'] = pool_name
                    pools.append(pool_info)
                    
            except Exception as e:
                logger.debug(f"检查池子 {pool_name} 失败: {e}")
                continue
        
        # 如果没有找到池子，尝试通过SOL配对来获取价格
        if not pools and token_address != self.common_tokens["SOL"]:
            # 尝试使用SOL作为配对代币
            sol_pools = await self._find_pools_with_sol_pairing(token_address)
            pools.extend(sol_pools)
        
        return pools
    
    async def _find_pools_with_sol_pairing(self, token_address: str) -> List[Dict[str, Any]]:
        """通过SOL配对查找包含目标代币的池子
        
        Args:
            token_address: 目标代币地址
            
        Returns:
            包含目标代币的池子列表
        """
        pools = []
        
        # 检查已知的SOL配对池子
        sol_pairs = [
            ("SOL-USDC", "58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2"),
            ("SOL-USDT", "7XawhbbxtsRcQA8KTkHT9f9nTxftvGQ6q5cJWyWzFFWb"),
        ]
        
        for pool_name, pool_address in sol_pairs:
            try:
                pool_info = await self.get_pool_info(pool_address)
                
                # 检查池子是否包含SOL和目标代币
                sol_mint = self.common_tokens["SOL"]
                
                # 如果池子包含SOL和另一个代币，计算间接价格
                if (pool_info.get('base_mint') == sol_mint and 
                    pool_info.get('quote_mint') == token_address):
                    
                    # SOL -> 目标代币的价格
                    # 价格 = 目标代币数量 / SOL数量
                    sol_price = float(pool_info['quote_amount']) / float(pool_info['base_amount'])
                    
                    # 目标代币相对于SOL的价格 = 1 / (SOL -> 目标代币价格)
                    token_price = 1.0 / sol_price if sol_price > 0 else 0
                    
                    pool_info['token_price'] = token_price
                    pool_info['price_direction'] = 'token -> SOL'
                    pool_info['liquidity'] = pool_info.get('base_amount', 0) + pool_info.get('quote_amount', 0)
                    pool_info['pool_name'] = f"{pool_name}_indirect"
                    pools.append(pool_info)
                    
                elif (pool_info.get('base_mint') == token_address and 
                      pool_info.get('quote_mint') == sol_mint):
                    
                    # 目标代币 -> SOL的价格
                    # 价格 = SOL数量 / 目标代币数量
                    token_price = float(pool_info['quote_amount']) / float(pool_info['base_amount'])
                    
                    pool_info['token_price'] = token_price
                    pool_info['price_direction'] = 'token -> SOL'
                    pool_info['liquidity'] = pool_info.get('base_amount', 0) + pool_info.get('quote_amount', 0)
                    pool_info['pool_name'] = f"{pool_name}_direct"
                    pools.append(pool_info)
                    
            except Exception as e:
                logger.debug(f"检查SOL配对池子 {pool_name} 失败: {e}")
                continue
        
        return pools
    
    async def get_price_from_rpc(self, token_address: str, quote_token: str = None) -> float:
        """从RPC直接获取代币价格
        
        Args:
            token_address: 目标代币地址
            quote_token: 报价代币地址 (默认使用USDC)
            
        Returns:
            代币价格 (以报价代币计)
        """
        if quote_token is None:
            quote_token = self.common_tokens["USDC"]
        
        # 如果是SOL本身，价格为1 SOL
        if token_address == self.common_tokens["SOL"]:
            return 1.0
        
        # 查找包含目标代币的池子
        pools = await self.find_pools_for_token(token_address)
        
        if not pools:
            raise Exception(f"未找到包含代币 {token_address} 的池子")
        
        # 选择流动性最好的池子（代币数量最多的）
        best_pool = max(pools, key=lambda p: p.get('base_amount', 0) + p.get('quote_amount', 0))
        
        price = best_pool['token_price']
        
        logger.info(f"RPC价格 - 代币 {token_address[:8]}...: {price:.10f} (池: {best_pool['pool_name']})")
        
        return price
    
    async def get_price_comparison(self, token_address: str) -> Dict[str, Any]:
        """获取三种价格源的价格对比
        
        Args:
            token_address: 目标代币地址
            
        Returns:
            价格对比结果
        """
        comparison = {
            'token_address': token_address,
            'timestamp': asyncio.get_event_loop().time(),
            'sources': {}
        }
        
        # 1. RPC价格
        try:
            rpc_price = await self.get_price_from_rpc(token_address)
            comparison['sources']['rpc'] = {
                'price': rpc_price,
                'status': 'success',
                'response_time': 0.0  # 需要实际测量
            }
        except Exception as e:
            comparison['sources']['rpc'] = {
                'price': 0.0,
                'status': 'failed',
                'error': str(e)
            }
        
        return comparison
    
    async def health_check(self) -> bool:
        """检查RPC连接状态"""
        try:
            # 获取最新区块高度
            slot = await self.client.get_slot()
            return slot.value > 0
        except Exception as e:
            logger.warning(f"RPC健康检查失败: {e}")
            return False


class PriceComparisonTool:
    """价格对比工具 - 对比RPC、Jupiter、Raydium三种价格源"""
    
    def __init__(self, trading_engine, rpc_price_provider: RPCPriceProvider):
        """初始化价格对比工具
        
        Args:
            trading_engine: 交易引擎实例
            rpc_price_provider: RPC价格提供器实例
        """
        self.trading_engine = trading_engine
        self.rpc_provider = rpc_price_provider
        
    async def compare_prices(self, token_address: str) -> Dict[str, Any]:
        """对比三种价格源的价格
        
        Args:
            token_address: 目标代币地址
            
        Returns:
            价格对比结果
        """
        import time
        
        comparison = {
            'token_address': token_address,
            'timestamp': time.time(),
            'sources': {},
            'analysis': {}
        }
        
        # 1. RPC价格
        rpc_start = time.time()
        try:
            rpc_price = await self.rpc_provider.get_price_from_rpc(token_address)
            rpc_time = time.time() - rpc_start
            comparison['sources']['rpc'] = {
                'price': rpc_price,
                'status': 'success',
                'response_time': rpc_time
            }
        except Exception as e:
            comparison['sources']['rpc'] = {
                'price': 0.0,
                'status': 'failed',
                'error': str(e),
                'response_time': time.time() - rpc_start
            }
        
        # 2. Jupiter价格
        jupiter_start = time.time()
        try:
            jupiter_price = await self.trading_engine._get_jupiter_price(token_address)
            jupiter_time = time.time() - jupiter_start
            comparison['sources']['jupiter'] = {
                'price': jupiter_price,
                'status': 'success',
                'response_time': jupiter_time
            }
        except Exception as e:
            comparison['sources']['jupiter'] = {
                'price': 0.0,
                'status': 'failed',
                'error': str(e),
                'response_time': time.time() - jupiter_start
            }
        
        # 3. Raydium价格
        raydium_start = time.time()
        try:
            raydium_price = await self.trading_engine._get_raydium_price(token_address)
            raydium_time = time.time() - raydium_start
            comparison['sources']['raydium'] = {
                'price': raydium_price,
                'status': 'success',
                'response_time': raydium_time
            }
        except Exception as e:
            comparison['sources']['raydium'] = {
                'price': 0.0,
                'status': 'failed',
                'error': str(e),
                'response_time': time.time() - raydium_start
            }
        
        # 分析结果
        comparison['analysis'] = await self._analyze_comparison(comparison)
        
        return comparison
    
    async def _analyze_comparison(self, comparison: Dict[str, Any]) -> Dict[str, Any]:
        """分析价格对比结果
        
        Args:
            comparison: 价格对比结果
            
        Returns:
            分析结果
        """
        analysis = {
            'successful_sources': [],
            'fastest_source': None,
            'price_differences': {},
            'recommendations': []
        }
        
        # 统计成功的源
        successful_sources = []
        prices = {}
        
        for source, data in comparison['sources'].items():
            if data['status'] == 'success':
                successful_sources.append(source)
                prices[source] = data['price']
        
        analysis['successful_sources'] = successful_sources
        
        if not successful_sources:
            analysis['recommendations'].append('所有价格源都失败，需要检查网络连接')
            return analysis
        
        # 找出最快的源
        fastest_time = float('inf')
        for source, data in comparison['sources'].items():
            if data['status'] == 'success' and data['response_time'] < fastest_time:
                fastest_time = data['response_time']
                analysis['fastest_source'] = source
        
        # 计算价格差异
        if len(successful_sources) > 1:
            source_list = list(prices.keys())
            for i in range(len(source_list)):
                for j in range(i + 1, len(source_list)):
                    source1 = source_list[i]
                    source2 = source_list[j]
                    
                    price1 = prices[source1]
                    price2 = prices[source2]
                    
                    if price1 > 0 and price2 > 0:
                        diff = abs(price1 - price2)
                        diff_pct = (diff / min(price1, price2)) * 100
                        
                        analysis['price_differences'][f"{source1}_vs_{source2}"] = {
                            'absolute_difference': diff,
                            'percentage_difference': diff_pct
                        }
                        
                        if diff_pct > 5.0:
                            analysis['recommendations'].append(
                                f"{source1}和{source2}价格差异较大 ({diff_pct:.2f}%)"
                            )
        
        # 添加推荐
        if analysis['fastest_source'] == 'rpc':
            analysis['recommendations'].append('RPC价格源响应最快，适合高频监控')
        elif analysis['fastest_source'] == 'jupiter':
            analysis['recommendations'].append('Jupiter价格源响应较快，适合交易决策')
        
        if len(successful_sources) == 3:
            analysis['recommendations'].append('所有价格源都可用，建议使用加权平均')
        
        return analysis
    
    async def monitor_price_real_time(self, token_address: str, duration: int = 60, interval: float = 1.0):
        """实时监控价格对比
        
        Args:
            token_address: 目标代币地址
            duration: 监控时长（秒）
            interval: 监控间隔（秒）
        """
        import time
        
        start_time = time.time()
        results = []
        
        print(f"\n🚀 开始实时价格监控 - 代币: {token_address[:8]}...")
        print(f"⏱️  时长: {duration}秒, 间隔: {interval}秒")
        print("-" * 80)
        
        while time.time() - start_time < duration:
            try:
                comparison = await self.compare_prices(token_address)
                results.append(comparison)
                
                # 打印当前结果
                self._print_comparison_result(comparison)
                
                # 等待下一个间隔
                await asyncio.sleep(interval)
                
            except Exception as e:
                print(f"❌ 监控出错: {e}")
                await asyncio.sleep(interval)
        
        print("-" * 80)
        print(f"✅ 监控完成，共收集 {len(results)} 个数据点")
        
        # 生成统计报告
        await self._generate_statistics_report(results)
        
        return results
    
    def _print_comparison_result(self, comparison: Dict[str, Any]):
        """打印单次对比结果"""
        import time
        
        timestamp = time.strftime('%H:%M:%S', time.localtime(comparison['timestamp']))
        
        print(f"\n[{timestamp}] 价格对比结果:")
        
        for source, data in comparison['sources'].items():
            if data['status'] == 'success':
                print(f"  {source.upper():<8}: {data['price']:.8f} SOL (响应: {data['response_time']:.3f}s)")
            else:
                print(f"  {source.upper():<8}: 失败 - {data.get('error', 'Unknown error')}")
        
        # 打印分析结果
        if comparison['analysis'].get('fastest_source'):
            print(f"  🏃 最快: {comparison['analysis']['fastest_source'].upper()}")
    
    async def _generate_statistics_report(self, results: List[Dict[str, Any]]):
        """生成统计报告"""
        successful_results = [r for r in results if any(
            s['status'] == 'success' for s in r['sources'].values()
        )]
        
        if not successful_results:
            print("❌ 没有成功的数据点")
            return
        
        print("\n📊 统计报告:")
        
        # 统计各源的成功率
        source_stats = {}
        for source in ['rpc', 'jupiter', 'raydium']:
            successful = sum(1 for r in results if r['sources'].get(source, {}).get('status') == 'success')
            total = len(results)
            success_rate = (successful / total) * 100 if total > 0 else 0
            
            source_stats[source] = {
                'success_rate': success_rate,
                'successful_count': successful,
                'total_count': total
            }
            
            print(f"  {source.upper():<8}: 成功率 {success_rate:.1f}% ({successful}/{total})")
        
        # 计算平均响应时间
        for source in ['rpc', 'jupiter', 'raydium']:
            response_times = [
                r['sources'][source]['response_time'] 
                for r in results 
                if r['sources'].get(source, {}).get('status') == 'success'
            ]
            
            if response_times:
                avg_time = sum(response_times) / len(response_times)
                print(f"  {source.upper():<8}: 平均响应时间 {avg_time:.3f}s")


# 使用示例
async def demo_price_comparison():
    """演示价格对比功能"""
    from sol_meme_sdk.wallet import Wallet
    from sol_meme_sdk.trading_engine import TradingEngine
    
    # 初始化
    wallet = Wallet()
    trading_engine = TradingEngine(wallet)
    rpc_provider = RPCPriceProvider()
    
    # 连接
    await rpc_provider.connect()
    
    # 创建对比工具
    comparison_tool = PriceComparisonTool(trading_engine, rpc_provider)
    
    # 测试代币 (SOL-USDC池中的代币)
    test_token = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC
    
    try:
        # 单次对比
        print("🔍 单次价格对比测试:")
        comparison = await comparison_tool.compare_prices(test_token)
        
        # 实时监控（30秒，每2秒一次）
        print("\n📈 开始实时监控...")
        await comparison_tool.monitor_price_real_time(test_token, duration=30, interval=2.0)
        
    except Exception as e:
        print(f"演示失败: {e}")
    finally:
        await rpc_provider.close()


if __name__ == "__main__":
    asyncio.run(demo_price_comparison())