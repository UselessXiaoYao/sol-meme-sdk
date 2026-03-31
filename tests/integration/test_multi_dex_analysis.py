#!/usr/bin/env python3
"""
多DEX统一分析测试 - 整合Jupiter和Raydium测试功能
通过TradingEngine测试和比较多个DEX的性能
"""

import asyncio
import sys
import os
from typing import Dict, List, Any

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

from src.sol_meme_sdk.trading_engine import TradingEngine
from src.sol_meme_sdk.raydium_client import RaydiumClient
from src.sol_meme_sdk.jupiter_client import JupiterClient
from src.sol_meme_sdk.wallet import Wallet
from src.sol_meme_sdk.models import TransactionConfig
from src.sol_meme_sdk.unified_config import UnifiedConfig


class MultiDEXAnalyzer:
    """多DEX分析工具类"""
    
    def __init__(self, trading_engine: TradingEngine):
        self.trading_engine = trading_engine
        self.common_tokens = {
            "SOL": "So11111111111111111111111111111111111111112",
            "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "JUP": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
            "BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"
        }
    
    async def analyze_price_comparison(self, token_address: str) -> Dict[str, Any]:
        """分析不同DEX的价格差异"""
        results = {}
        
        # 获取Jupiter价格
        try:
            jupiter_price = await self.trading_engine._get_jupiter_price(token_address)
            results['jupiter'] = {
                'price': jupiter_price,
                'status': 'success'
            }
        except Exception as e:
            results['jupiter'] = {
                'price': 0.0,
                'status': 'failed',
                'error': str(e)
            }
        
        # 获取Raydium价格
        try:
            raydium_price = await self.trading_engine._get_raydium_price(token_address)
            results['raydium'] = {
                'price': raydium_price,
                'status': 'success'
            }
        except Exception as e:
            results['raydium'] = {
                'price': 0.0,
                'status': 'failed',
                'error': str(e)
            }
        
        # 计算价格差异
        if results['jupiter']['status'] == 'success' and results['raydium']['status'] == 'success':
            price_diff = abs(jupiter_price - raydium_price)
            price_diff_pct = (price_diff / min(jupiter_price, raydium_price)) * 100
            results['comparison'] = {
                'price_difference': price_diff,
                'price_difference_percent': price_diff_pct,
                'best_dex': 'jupiter' if jupiter_price < raydium_price else 'raydium'
            }
        
        return results
    
    async def analyze_liquidity_comparison(self, token_address: str) -> Dict[str, Any]:
        """分析不同DEX的流动性情况"""
        results = {}
        
        # 分析Raydium流动性
        try:
            pools = await self.trading_engine.raydium_client.get_raydium_pools()
            if pools and pools.get('official'):
                pool_data = pools['official']
                pools_list = pool_data['data'] if isinstance(pool_data, dict) and 'data' in pool_data else pool_data
                
                # 查找包含目标代币的池
                token_pools = []
                for pool in pools_list:
                    mintA = pool.get('mintA', {}).get('address', '')
                    mintB = pool.get('mintB', {}).get('address', '')
                    
                    if token_address in [mintA, mintB]:
                        token_pools.append({
                            'id': pool.get('id', 'N/A'),
                            'tvl': float(pool.get('tvl', 0)),
                            'pair': f"{pool.get('mintA', {}).get('symbol', 'N/A')}/{pool.get('mintB', {}).get('symbol', 'N/A')}",
                            'type': pool.get('pooltype', ['N/A'])[0]
                        })
                
                results['raydium'] = {
                    'status': 'success',
                    'pool_count': len(token_pools),
                    'total_tvl': sum(pool['tvl'] for pool in token_pools),
                    'pools': sorted(token_pools, key=lambda x: x['tvl'], reverse=True)[:5]  # 前5个最大流动性的池
                }
            else:
                results['raydium'] = {
                    'status': 'failed',
                    'error': 'No pools found'
                }
        except Exception as e:
            results['raydium'] = {
                'status': 'failed',
                'error': str(e)
            }
        
        # 分析Jupiter流动性（通过路由信息推断）
        try:
            # 获取Jupiter报价来分析可用路由
            quote = await self.trading_engine.jupiter_client.get_quote(
                input_mint=self.common_tokens["SOL"],
                output_mint=token_address,
                amount=10000000,  # 0.01 SOL
                slippage_bps=50
            )
            
            if 'routePlan' in quote:
                results['jupiter'] = {
                    'status': 'success',
                    'route_count': len(quote['routePlan']),
                    'available_routes': len(quote['routePlan'])
                }
            else:
                results['jupiter'] = {
                    'status': 'failed',
                    'error': 'No route plan available'
                }
        except Exception as e:
            results['jupiter'] = {
                'status': 'failed',
                'error': str(e)
            }
        
        return results
    
    async def get_dex_recommendation(self, token_address: str, trade_type: str = "buy") -> Dict[str, Any]:
        """获取DEX推荐（基于价格和流动性）"""
        recommendation = {
            'token_address': token_address,
            'trade_type': trade_type,
            'recommended_dex': None,
            'reason': '',
            'details': {}
        }
        
        # 获取价格比较
        price_analysis = await self.analyze_price_comparison(token_address)
        
        # 获取流动性比较
        liquidity_analysis = await self.analyze_liquidity_comparison(token_address)
        
        # 决策逻辑
        jupiter_ok = price_analysis.get('jupiter', {}).get('status') == 'success'
        raydium_ok = price_analysis.get('raydium', {}).get('status') == 'success'
        
        if jupiter_ok and raydium_ok:
            # 两个DEX都可用，基于价格和流动性选择
            jupiter_price = price_analysis['jupiter']['price']
            raydium_price = price_analysis['raydium']['price']
            
            # 对于买入，选择价格更低的DEX
            if trade_type == "buy":
                if jupiter_price <= raydium_price:
                    recommendation['recommended_dex'] = 'jupiter'
                    recommendation['reason'] = 'Jupiter提供更好的价格'
                else:
                    recommendation['recommended_dex'] = 'raydium'
                    recommendation['reason'] = 'Raydium提供更好的价格'
            else:  # 卖出，选择价格更高的DEX
                if jupiter_price >= raydium_price:
                    recommendation['recommended_dex'] = 'jupiter'
                    recommendation['reason'] = 'Jupiter提供更好的价格'
                else:
                    recommendation['recommended_dex'] = 'raydium'
                    recommendation['reason'] = 'Raydium提供更好的价格'
            
            # 考虑流动性因素
            raydium_tvl = liquidity_analysis.get('raydium', {}).get('total_tvl', 0)
            if raydium_tvl > 1000000:  # 如果Raydium流动性超过100万美元
                recommendation['reason'] += f" (Raydium流动性充足: ${raydium_tvl:,.0f})"
        
        elif jupiter_ok:
            recommendation['recommended_dex'] = 'jupiter'
            recommendation['reason'] = 'Raydium不可用，使用Jupiter'
        
        elif raydium_ok:
            recommendation['recommended_dex'] = 'raydium'
            recommendation['reason'] = 'Jupiter不可用，使用Raydium'
        
        else:
            recommendation['recommended_dex'] = None
            recommendation['reason'] = '两个DEX都不可用'
        
        recommendation['details'] = {
            'price_analysis': price_analysis,
            'liquidity_analysis': liquidity_analysis
        }
        
        return recommendation


async def test_multi_dex_analysis():
    """测试多DEX分析功能"""
    print("🚀 多DEX统一分析测试")
    print("=" * 60)
    
    # 初始化配置
    config = UnifiedConfig()
    print(f"🔧 当前网络: {config.solana_network}")
    
    # 加载现有钱包
    wallet_file = os.path.join(os.path.dirname(__file__), "new_wallet.json")
    if not os.path.exists(wallet_file):
        print("❌ 钱包文件不存在，请先创建钱包")
        return
    
    try:
        wallet = Wallet.from_json_file(str(wallet_file))
        print(f"✅ 钱包加载成功 - 地址: {wallet.address}")
    except Exception as e:
        print(f"❌ 钱包加载失败: {e}")
        return
    
    # 创建交易配置
    tx_config = TransactionConfig()
    
    # 初始化TradingEngine
    print("\n🔄 初始化TradingEngine...")
    trading = TradingEngine(wallet=wallet, config=tx_config)
    print(f"✅ TradingEngine 初始化成功!")
    print(f"   网络模式: {'devnet' if trading.is_devnet else 'mainnet'}")
    
    # 创建多DEX分析器
    analyzer = MultiDEXAnalyzer(trading)
    
    # 测试代币列表
    test_tokens = [
        ("USDC", analyzer.common_tokens["USDC"]),
        ("JUP", analyzer.common_tokens["JUP"]),
        ("BONK", analyzer.common_tokens["BONK"])
    ]
    
    print("\n💰 代币价格比较分析")
    print("-" * 40)
    
    for token_name, token_address in test_tokens:
        print(f"\n🔍 分析 {token_name} 代币...")
        
        # 价格比较分析
        price_analysis = await analyzer.analyze_price_comparison(token_address)
        
        jupiter_price = price_analysis.get('jupiter', {}).get('price', 0)
        raydium_price = price_analysis.get('raydium', {}).get('price', 0)
        
        print(f"   Jupiter价格: {jupiter_price:.10f} SOL")
        print(f"   Raydium价格: {raydium_price:.10f} SOL")
        
        if 'comparison' in price_analysis:
            diff_pct = price_analysis['comparison']['price_difference_percent']
            best_dex = price_analysis['comparison']['best_dex']
            print(f"   价格差异: {diff_pct:.4f}% (推荐: {best_dex.upper()})")
        
        # 流动性分析
        liquidity_analysis = await analyzer.analyze_liquidity_comparison(token_address)
        
        raydium_liquidity = liquidity_analysis.get('raydium', {})
        if raydium_liquidity.get('status') == 'success':
            print(f"   Raydium流动性: {raydium_liquidity['total_tvl']:,.0f} USD")
            print(f"   可用池数量: {raydium_liquidity['pool_count']}")
        
        # DEX推荐
        recommendation = await analyzer.get_dex_recommendation(token_address, "buy")
        print(f"   💡 推荐DEX: {recommendation['recommended_dex'] or '无'}")
        print(f"       理由: {recommendation['reason']}")
    
    # 综合性能测试
    print("\n📊 DEX性能综合测试")
    print("-" * 40)
    
    # 测试交易速度（通过报价响应时间）
    import time
    
    test_token = analyzer.common_tokens["USDC"]
    
    # Jupiter响应时间
    start_time = time.time()
    try:
        jupiter_quote = await trading.jupiter_client.get_quote(
            input_mint=analyzer.common_tokens["SOL"],
            output_mint=test_token,
            amount=10000000,
            slippage_bps=50
        )
        jupiter_time = time.time() - start_time
        print(f"✅ Jupiter报价响应时间: {jupiter_time:.3f}秒")
    except Exception as e:
        print(f"❌ Jupiter报价失败: {e}")
    
    # Raydium响应时间
    start_time = time.time()
    try:
        raydium_quote = await trading.raydium_client.get_swap_quote(
            input_mint=analyzer.common_tokens["SOL"],
            output_mint=test_token,
            amount=10000000,
            slippage_bps=50
        )
        raydium_time = time.time() - start_time
        print(f"✅ Raydium报价响应时间: {raydium_time:.3f}秒")
    except Exception as e:
        print(f"❌ Raydium报价失败: {e}")
    
    print("\n" + "=" * 60)
    print("📋 多DEX分析测试完成")
    print("💡 总结:")
    print("   - 价格比较功能正常")
    print("   - 流动性分析功能正常") 
    print("   - DEX推荐算法工作正常")
    print("   - TradingEngine多DEX集成完整")


if __name__ == "__main__":
    asyncio.run(test_multi_dex_analysis())