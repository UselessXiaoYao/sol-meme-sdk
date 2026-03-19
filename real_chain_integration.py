#!/usr/bin/env python3
"""
真实链上数据集成 - 连接真实Solana RPC和DEX API
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solana.rpc.types import TokenAccountOpts
from solders.pubkey import Pubkey

from src.sol_meme_sdk.config import get_config


class RealChainIntegration:
    """真实链上数据集成类"""
    
    def __init__(self, rpc_url: Optional[str] = None):
        """初始化集成器
        
        Args:
            rpc_url: Solana RPC URL
        """
        self.rpc_url = rpc_url or get_config().solana_rpc_endpoint
        self.client = AsyncClient(self.rpc_url)
        
        # API端点配置
        self.raydium_api_base = "https://api.raydium.io/v2"
        self.meteora_api_base = "https://damm-v2.datapi.meteora.ag"  # 官方DAMM V2 API
        self.jupiter_api_base = "https://quote-api.jup.ag/v6"
        
        # Pump.Fun相关地址（需要更新为真实地址）
        self.pumpfun_program_ids = [
            "6EF8rrecthR5DkZ8HtH7vPjJpZk5QnWJ8YV7jKqL9mNp",  # 需要替换为真实地址
        ]
    
    async def connect(self):
        """连接到网络"""
        await self.client.__aenter__()
        print(f"✅ 已连接到Solana RPC: {self.rpc_url}")
    
    async def close(self):
        """关闭连接"""
        await self.client.__aexit__(None, None, None)
        print("✅ 已断开连接")
    
    async def get_token_info(self, token_address: str) -> Dict[str, Any]:
        """获取代币基本信息
        
        Args:
            token_address: 代币地址
            
        Returns:
            代币信息
        """
        try:
            # 获取代币mint账户
            mint_account = await self.client.get_account_info(
                Pubkey.from_string(token_address),
                commitment=Confirmed
            )
            
            if not mint_account.value:
                return {'error': '代币账户不存在'}
            
            # 解析mint账户数据
            mint_data = mint_account.value.data
            
            # 这里需要解析SPL代币mint账户结构
            # 暂时返回基础信息
            return {
                'address': token_address,
                'owner': str(mint_account.value.owner),
                'data_length': len(mint_data),
                'lamports': mint_account.value.lamports,
                'is_spl_token': str(mint_account.value.owner) == "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
            }
            
        except Exception as e:
            return {'error': f'获取代币信息失败: {e}'}
    
    async def get_token_metadata(self, token_address: str) -> Dict[str, Any]:
        """获取代币元数据（通过Metaplex）
        
        Args:
            token_address: 代币地址
            
        Returns:
            元数据信息
        """
        try:
            # 通过Metaplex获取元数据
            metadata_pda = await self.find_metadata_account(token_address)
            
            if not metadata_pda:
                return {'error': '未找到元数据账户'}
            
            # 获取元数据账户信息
            metadata_account = await self.client.get_account_info(
                Pubkey.from_string(metadata_pda),
                commitment=Confirmed
            )
            
            if not metadata_account.value:
                return {'error': '元数据账户不存在'}
            
            # 解析元数据（需要实现Metaplex元数据解析）
            return {
                'metadata_account': metadata_pda,
                'data_length': len(metadata_account.value.data)
            }
            
        except Exception as e:
            return {'error': f'获取元数据失败: {e}'}
    
    async def find_metadata_account(self, token_address: str) -> Optional[str]:
        """查找代币的元数据账户
        
        Args:
            token_address: 代币地址
            
        Returns:
            元数据账户地址
        """
        try:
            # 使用Metaplex的PDA推导算法
            # metadata_seeds = [b"metadata", metaplex_program_id, mint_address]
            # 这里需要实现实际的PDA推导
            
            # 暂时返回None
            return None
            
        except Exception:
            return None
    
    async def get_token_holders_count(self, token_address: str) -> int:
        """获取代币持有者数量
        
        Args:
            token_address: 代币地址
            
        Returns:
            持有者数量
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
            
            return len(token_accounts.value)
            
        except Exception as e:
            print(f"❌ 获取持有者数量失败: {e}")
            return 0
    
    async def get_token_supply(self, token_address: str) -> Dict[str, Any]:
        """获取代币供应量信息
        
        Args:
            token_address: 代币地址
            
        Returns:
            供应量信息
        """
        try:
            # 获取代币供应量
            supply_info = await self.client.get_token_supply(
                Pubkey.from_string(token_address),
                commitment=Confirmed
            )
            
            if supply_info.value:
                return {
                    'amount': supply_info.value.amount,
                    'decimals': supply_info.value.decimals,
                    'ui_amount': supply_info.value.ui_amount
                }
            else:
                return {'error': '无法获取供应量信息'}
                
        except Exception as e:
            return {'error': f'获取供应量失败: {e}'}
    
    async def search_raydium_pools_real(self, token_address: str) -> List[Dict[str, Any]]:
        """通过Raydium API搜索真实池信息
        
        Args:
            token_address: 代币地址
            
        Returns:
            池信息列表
        """
        try:
            async with aiohttp.ClientSession() as session:
                # 获取Raydium池列表
                url = f"{self.raydium_api_base}/main/pairs"
                async with session.get(url) as response:
                    if response.status == 200:
                        pools_data = await response.json()
                        
                        # 过滤包含目标代币的池
                        matching_pools = []
                        for pool in pools_data:
                            if (pool.get('baseMint') == token_address or 
                                pool.get('quoteMint') == token_address):
                                
                                matching_pools.append({
                                    'pool_address': pool.get('id'),
                                    'base_mint': pool.get('baseMint'),
                                    'quote_mint': pool.get('quoteMint'),
                                    'liquidity': pool.get('liquidity'),
                                    'volume_24h': pool.get('volume24h'),
                                    'price': pool.get('price'),
                                    'dex': 'raydium'
                                })
                        
                        return matching_pools
                    else:
                        print(f"❌ Raydium API请求失败: {response.status}")
                        return []
                        
        except Exception as e:
            print(f"❌ Raydium搜索失败: {e}")
            return []
    
    async def search_meteora_pools_real(self, token_address: str, max_pages: int = 5) -> List[Dict[str, Any]]:
        """通过Meteora API搜索真实池信息（支持分页和错误处理）
        
        Args:
            token_address: 代币地址
            max_pages: 最大搜索页数
            
        Returns:
            池信息列表
        """
        matching_pools = []
        current_page = 1
        
        print(f"🔍 搜索Meteora池 (代币: {token_address[:8]}...{token_address[-8:]})")
        
        while current_page <= max_pages:
            try:
                async with aiohttp.ClientSession() as session:
                    # 使用分页参数获取Meteora池列表
                    url = f"{self.meteora_api_base}/pools"
                    params = {
                        'page': current_page,
                        'page_size': 100
                    }
                    
                    async with session.get(url, params=params, timeout=15) as response:
                        if response.status == 200:
                            pools_data = await response.json()
                            
                            # 检查响应结构
                            if 'data' not in pools_data:
                                print(f"⚠️ Meteora API响应结构异常: {list(pools_data.keys())}")
                                break
                            
                            # 过滤包含目标代币的池
                            for pool in pools_data.get('data', []):
                                # 使用正确的字段名：token_x和token_y
                                token_x_addr = pool.get('token_x', {}).get('address', '')
                                token_y_addr = pool.get('token_y', {}).get('address', '')
                                
                                if token_x_addr == token_address or token_y_addr == token_address:
                                    
                                    matching_pools.append({
                                        'pool_address': pool.get('address'),
                                        'pool_name': pool.get('name', ''),
                                        'token_x': pool.get('token_x', {}),
                                        'token_y': pool.get('token_y', {}),
                                        'token_x_amount': pool.get('token_x_amount', 0),
                                        'token_y_amount': pool.get('token_y_amount', 0),
                                        'liquidity': pool.get('tvl', 0),  # TVL作为流动性
                                        'volume_24h': pool.get('volume', {}).get('24h', 0),
                                        'fees_24h': pool.get('fees', {}).get('24h', 0),
                                        'vault_x': pool.get('vault_x'),
                                        'vault_y': pool.get('vault_y'),
                                        'dex': 'meteora'
                                    })
                            
                            # 检查分页信息
                            total_pages = pools_data.get('pages', 0)
                            current_page_num = pools_data.get('current_page', current_page)
                            
                            # 检查是否还有更多页
                            if current_page_num >= total_pages or not pools_data.get('data'):
                                break
                            
                            current_page += 1
                            
                            # 添加延迟避免请求过快
                            await asyncio.sleep(0.05)
                            
                        elif response.status == 429:
                            print("⚠️ Meteora API请求频率限制，稍后重试")
                            await asyncio.sleep(1)  # 等待1秒后重试
                            continue
                        elif response.status == 404:
                            print("❌ Meteora API端点不存在")
                            break
                        else:
                            print(f"❌ Meteora API请求失败: {response.status}")
                            break
                            
            except asyncio.TimeoutError:
                print(f"⚠️ Meteora API请求超时 (第{current_page}页)")
                break
            except aiohttp.ClientError as e:
                print(f"❌ Meteora API网络错误: {e}")
                break
            except Exception as e:
                print(f"❌ Meteora搜索失败: {e}")
                break
        
        print(f"✅ 找到 {len(matching_pools)} 个Meteora池")
        return matching_pools
    
    async def get_jupiter_quote(self, input_mint: str, output_mint: str, amount: int) -> Dict[str, Any]:
        """通过Jupiter获取报价
        
        Args:
            input_mint: 输入代币地址
            output_mint: 输出代币地址
            amount: 输入数量
            
        Returns:
            报价信息
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.jupiter_api_base}/quote"
                params = {
                    'inputMint': input_mint,
                    'outputMint': output_mint,
                    'amount': amount,
                    'slippageBps': 100  # 1%滑点
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {'error': f'Jupiter API请求失败: {response.status}'}
                        
        except Exception as e:
            return {'error': f'获取报价失败: {e}'}
    
    async def analyze_token_real_time(self, token_address: str) -> Dict[str, Any]:
        """实时分析代币
        
        Args:
            token_address: 代币地址
            
        Returns:
            分析结果
        """
        print(f"🔍 实时分析代币: {token_address[:8]}...{token_address[-8:]}")
        
        try:
            # 并行获取所有信息
            tasks = [
                self.get_token_info(token_address),
                self.get_token_supply(token_address),
                self.get_token_holders_count(token_address),
                self.search_raydium_pools_real(token_address),
                self.search_meteora_pools_real(token_address)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            token_info = results[0] if not isinstance(results[0], Exception) else {}
            supply_info = results[1] if not isinstance(results[1], Exception) else {}
            holders_count = results[2] if not isinstance(results[2], Exception) else 0
            raydium_pools = results[3] if not isinstance(results[3], Exception) else []
            meteora_pools = results[4] if not isinstance(results[4], Exception) else []
            
            # 计算总流动性
            total_liquidity = 0
            for pool in raydium_pools + meteora_pools:
                liquidity = pool.get('liquidity', 0)
                if isinstance(liquidity, (int, float)):
                    total_liquidity += liquidity
            
            # 估算进度
            progress = min(holders_count / 200, 0.95)  # 经验公式
            
            # 判断状态
            if total_liquidity >= 1000:
                status = "已迁移"
                priority = "低"
            elif progress >= 0.8:
                status = "即将打满"
                priority = "高"
            else:
                status = "监控中"
                priority = "中"
            
            return {
                'token_address': token_address,
                'token_info': token_info,
                'supply_info': supply_info,
                'holders_count': holders_count,
                'progress': progress,
                'raydium_pools': raydium_pools,
                'meteora_pools': meteora_pools,
                'total_liquidity': total_liquidity,
                'status': status,
                'priority': priority,
                'analysis_time': datetime.now().isoformat(),
                'success': True
            }
            
        except Exception as e:
            return {
                'token_address': token_address,
                'error': str(e),
                'success': False
            }
    
    async def test_network_connectivity(self) -> Dict[str, Any]:
        """测试网络连通性
        
        Returns:
            连通性测试结果
        """
        print("🔗 测试网络连通性...")
        
        test_results = {}
        
        try:
            # 测试Solana RPC
            version_info = await self.client.get_version()
            test_results['solana_rpc'] = {
                'status': '✅ 连接成功',
                'version': str(version_info.value),
                'latency': 'N/A'
            }
            
        except Exception as e:
            test_results['solana_rpc'] = {
                'status': '❌ 连接失败',
                'error': str(e)
            }
        
        # 测试Raydium API
        try:
            async with aiohttp.ClientSession() as session:
                start_time = time.time()
                async with session.get(f"{self.raydium_api_base}/main/pairs", timeout=10) as response:
                    latency = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        test_results['raydium_api'] = {
                            'status': '✅ 连接成功',
                            'latency': f'{latency:.1f}ms'
                        }
                    else:
                        test_results['raydium_api'] = {
                            'status': f'❌ API错误: {response.status}',
                            'latency': f'{latency:.1f}ms'
                        }
                        
        except Exception as e:
            test_results['raydium_api'] = {
                'status': '❌ 连接失败',
                'error': str(e)
            }
        
        # 测试Meteora API
        try:
            async with aiohttp.ClientSession() as session:
                start_time = time.time()
                async with session.get(f"{self.meteora_api_base}/pools", timeout=10) as response:
                    latency = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        test_results['meteora_api'] = {
                            'status': '✅ 连接成功',
                            'latency': f'{latency:.1f}ms'
                        }
                    else:
                        test_results['meteora_api'] = {
                            'status': f'❌ API错误: {response.status}',
                            'latency': f'{latency:.1f}ms'
                        }
                        
        except Exception as e:
            test_results['meteora_api'] = {
                'status': '❌ 连接失败',
                'error': str(e)
            }
        
        # 测试Jupiter API
        try:
            async with aiohttp.ClientSession() as session:
                start_time = time.time()
                async with session.get(f"{self.jupiter_api_base}/quote", params={
                    'inputMint': 'So11111111111111111111111111111111111111112',  # SOL
                    'outputMint': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',  # USDC
                    'amount': 1000000000,  # 1 SOL
                    'slippageBps': 100
                }, timeout=10) as response:
                    latency = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        test_results['jupiter_api'] = {
                            'status': '✅ 连接成功',
                            'latency': f'{latency:.1f}ms'
                        }
                    else:
                        test_results['jupiter_api'] = {
                            'status': f'❌ API错误: {response.status}',
                            'latency': f'{latency:.1f}ms'
                        }
                        
        except Exception as e:
            test_results['jupiter_api'] = {
                'status': '❌ 连接失败',
                'error': str(e)
            }
        
        return test_results


async def main():
    """主函数"""
    integration = RealChainIntegration()
    
    try:
        await integration.connect()
        
        # 测试网络连通性
        print("\n🌐 网络连通性测试")
        connectivity = await integration.test_network_connectivity()
        
        for service, result in connectivity.items():
            print(f"   {service.upper()}: {result['status']}")
            if 'latency' in result:
                print(f"     延迟: {result['latency']}")
            if 'error' in result:
                print(f"     错误: {result['error']}")
        
        # 测试分析一些已知代币
        test_tokens = [
            "So11111111111111111111111111111111111111112",  # SOL
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
            "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",  # RAY
        ]
        
        print(f"\n🔍 测试代币分析")
        for token_address in test_tokens:
            analysis = await integration.analyze_token_real_time(token_address)
            
            if analysis.get('success'):
                print(f"\n   {token_address[:8]}...{token_address[-8:]}")
                print(f"      持有者: {analysis['holders_count']}")
                print(f"      进度: {analysis['progress']:.1%}")
                print(f"      流动性: {analysis['total_liquidity']:.0f} SOL")
                print(f"      状态: {analysis['status']} ({analysis['priority']}优先级)")
                print(f"      Raydium池: {len(analysis['raydium_pools'])} 个")
                print(f"      Meteora池: {len(analysis['meteora_pools'])} 个")
            else:
                print(f"\n   ❌ {token_address[:8]}...{token_address[-8:]} 分析失败")
                print(f"      错误: {analysis.get('error', '未知错误')}")
        
        print("\n✅ 真实链上数据集成测试完成")
        
    except Exception as e:
        print(f"❌ 集成测试失败: {e}")
    finally:
        await integration.close()


if __name__ == "__main__":
    asyncio.run(main())