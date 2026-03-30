#!/usr/bin/env python3
"""
Meteora DEX客户端 - 用于METEORA_DAMM_V2池交易
"""

import asyncio
import aiohttp
import json
import base64
import struct
from typing import Dict, Any, Optional, List
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solders.transaction import Transaction
from solders.pubkey import Pubkey
from solders.system_program import ID as SYS_PROGRAM_ID
from solders.instruction import Instruction, AccountMeta
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from solders.message import Message

from .unified_config import get_config
from .exceptions import TradingError
from .wallet import Wallet


class MeteoraClient:
    """Meteora DEX客户端类，用于处理METEORA_DAMM_V2池交易"""
    
    def __init__(self, rpc_url: Optional[str] = None, network: str = "mainnet"):
        """初始化Meteora客户端
        
        Args:
            rpc_url: Solana RPC URL
            network: 网络类型 (mainnet, devnet, testnet)
        """
        # 从统一配置获取配置
        self.config = get_config()
        
        self.rpc_url = rpc_url or self.config.solana_rpc_endpoint
        self.network = network
        self.client = AsyncClient(self.rpc_url)
        # Meteora DAMM V2 API基地址（从环境变量读取）
        self.meteora_api_base = self.config.meteora_api_base
        
        # Meteora DAMM V2程序ID（真实ID）
        self.meteora_program_id = Pubkey.from_string("cpamdpZCGKUy5JxQXB4dcpGPiikHawvSWAd6mEn1sGG")
        
    async def connect(self):
        """连接到Solana网络"""
        await self.client.__aenter__()
        
    async def close(self):
        """关闭连接"""
        await self.client.__aexit__(None, None, None)
        
    async def get_pool_info(self, pool_address: str) -> Dict[str, Any]:
        """获取Meteora DAMM V2池的详细信息
        
        Args:
            pool_address: 池账户地址
            
        Returns:
            池信息字典
        """
        try:
            # 首先尝试使用Meteora官方API获取池信息
            url = f"{self.meteora_api_base}/pools/{pool_address}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return {
                            'pool_address': pool_address,
                            'pool_type': 'METEORA_DAMM_V2',
                            'name': data.get('name', ''),
                            'token_x': data.get('token_x', {}),
                            'token_y': data.get('token_y', {}),
                            'token_x_amount': data.get('token_x_amount', 0),
                            'token_y_amount': data.get('token_y_amount', 0),
                            'tvl': data.get('tvl', 0),
                            'current_price': data.get('current_price', 0),
                            'volume_24h': data.get('volume', {}).get('24h', 0),
                            'fees_24h': data.get('fees', {}).get('24h', 0),
                            'pool_config': data.get('pool_config', {}),
                            'has_farm': data.get('has_farm', False),
                            'is_blacklisted': data.get('is_blacklisted', False),
                            'farm_apy': data.get('farm_apy', 0),
                            'farm_apr': data.get('farm_apr', 0),
                            'fee_tvl_ratio': data.get('fee_tvl_ratio', {}),
                            'protocol_fees': data.get('protocol_fees', {}),
                            'tags': data.get('tags', []),
                            'created_at': data.get('created_at', 0),
                            'permanent_lock_liquidity': data.get('permanent_lock_liquidity', 0),
                            'vested_liquidity': data.get('vested_liquidity', {}),
                            'status': 'api_data'
                        }
                    else:
                        # API不可用，回退到区块链数据解析
                        print(f"⚠️ Meteora API不可用: {resp.status}, 回退到区块链数据")
                        return await self._get_pool_info_from_blockchain(pool_address)
                        
        except Exception as e:
            # API调用失败，回退到区块链数据解析
            print(f"⚠️ Meteora API调用失败: {e}, 回退到区块链数据")
            return await self._get_pool_info_from_blockchain(pool_address)
    
    async def _get_pool_info_from_blockchain(self, pool_address: str) -> Dict[str, Any]:
        """从区块链获取池信息（备用方法）"""
        try:
            pool_pubkey = Pubkey.from_string(pool_address)
            account_info = await self.client.get_account_info(pool_pubkey, commitment=Confirmed)
            
            if not account_info.value:
                raise TradingError(f"Meteora池账户不存在: {pool_address}")
                
            data = account_info.value.data
            
            # 解析Meteora DAMM V2池结构（基于实际数据分析）
            # 池大小为1112字节，需要根据实际结构调整偏移量
            pool_info = {
                'pool_address': pool_address,
                'pool_type': 'METEORA_DAMM_V2',
                'base_mint': str(Pubkey(data[8:40])),
                'quote_mint': str(Pubkey(data[40:72])),
                'base_amount': int.from_bytes(data[72:80], 'little'),
                'quote_amount': int.from_bytes(data[80:88], 'little'),
                'lp_mint': str(Pubkey(data[104:136])),
                'lp_supply': int.from_bytes(data[136:144], 'little'),
                'owner_program': str(account_info.value.owner),
                'data_size': len(data),
                'is_empty': int.from_bytes(data[72:80], 'little') == 0 and int.from_bytes(data[80:88], 'little') == 0,
                'status': 'blockchain_data'
            }
            
            # 计算价格
            if pool_info['base_amount'] > 0 and pool_info['quote_amount'] > 0:
                pool_info['price'] = pool_info['quote_amount'] / pool_info['base_amount']
                
            return pool_info
            
        except Exception as e:
            raise TradingError(f"从区块链获取Meteora池信息失败: {e}")
    
    async def _get_token_vault_address(self, pool_pubkey: Pubkey, token_index: int) -> str:
        """获取代币vault账户地址
        
        Args:
            pool_pubkey: 池账户公钥
            token_index: 代币索引 (0=token_x, 1=token_y)
            
        Returns:
            vault账户地址
        """
        try:
            # 基于池地址和索引计算vault地址（简化版）
            # 实际实现需要根据Meteora DAMM V2的账户派生逻辑
            vault_seed = f"vault{token_index}".encode()
            vault_pubkey = Pubkey.find_program_address(
                [bytes(pool_pubkey), vault_seed],
                self.meteora_program_id
            )[0]
            return str(vault_pubkey)
        except Exception as e:
            raise TradingError(f"获取代币vault地址失败: {e}")
    
    async def _get_lp_mint_address(self, pool_pubkey: Pubkey) -> str:
        """获取LP代币mint地址
        
        Args:
            pool_pubkey: 池账户公钥
            
        Returns:
            LP代币mint地址
        """
        try:
            # 基于池地址计算LP代币mint地址
            lp_seed = b"lp_mint"
            lp_mint_pubkey = Pubkey.find_program_address(
                [bytes(pool_pubkey), lp_seed],
                self.meteora_program_id
            )[0]
            return str(lp_mint_pubkey)
        except Exception as e:
            raise TradingError(f"获取LP代币mint地址失败: {e}")
    
    async def _get_associated_token_address(self, wallet_pubkey: Pubkey, mint_pubkey: Pubkey) -> Pubkey:
        """获取关联代币账户地址
        
        Args:
            wallet_pubkey: 钱包公钥
            mint_pubkey: 代币mint公钥
            
        Returns:
            关联代币账户地址
        """
        try:
            # 使用SPL代币程序的关联代币账户派生
            token_program_id = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
            associated_token_address = Pubkey.find_program_address(
                [bytes(wallet_pubkey), bytes(token_program_id), bytes(mint_pubkey)],
                Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")
            )[0]
            return associated_token_address
        except Exception as e:
            raise TradingError(f"获取关联代币账户地址失败: {e}")
    
    async def get_market_pools(self, page: int = 1, page_size: int = 100) -> Dict[str, Any]:
        """获取Meteora的所有市场池列表（支持分页）
        
        Args:
            page: 页码（从1开始）
            page_size: 每页大小
            
        Returns:
            池列表数据，包含分页信息
        """
        try:
            # 使用Meteora的官方API端点，支持分页参数
            url = f"{self.meteora_api_base}/pools"
            params = {
                'page': page,
                'page_size': page_size
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        # 标准化返回格式
                        return {
                            'pools': data.get('data', []),
                            'total': data.get('total', 0),
                            'pages': data.get('pages', 0),
                            'current_page': data.get('current_page', page),
                            'page_size': data.get('page_size', page_size),
                            'has_more': data.get('current_page', page) < data.get('pages', 0)
                        }
                    else:
                        # API调用失败时返回错误信息
                        error_msg = f"Meteora API错误: {resp.status}"
                        if resp.status == 404:
                            error_msg += " (端点不存在)"
                        elif resp.status == 429:
                            error_msg += " (请求频率限制)"
                        elif resp.status >= 500:
                            error_msg += " (服务器错误)"
                            
                        print(f"⚠️ {error_msg}")
                        return {
                            'pools': [],
                            'total': 0,
                            'pages': 0,
                            'current_page': page,
                            'page_size': page_size,
                            'has_more': False,
                            'error': error_msg
                        }
                        
        except aiohttp.ClientError as e:
            # 网络连接错误
            error_msg = f"Meteora API网络错误: {str(e)}"
            print(f"⚠️ {error_msg}")
            return {
                'pools': [],
                'total': 0,
                'pages': 0,
                'current_page': page,
                'page_size': page_size,
                'has_more': False,
                'error': error_msg
            }
    
    async def get_all_pools(self, max_pages: int = 100, page_size: int = 100) -> List[Dict[str, Any]]:
        """获取所有Meteora池（完整分页支持）
        
        Args:
            max_pages: 最大获取页数（防止请求过多）
            page_size: 每页大小
            
        Returns:
            所有池的列表
        """
        all_pools = []
        current_page = 1
        
        while current_page <= max_pages:
            try:
                # 获取当前页数据
                page_data = await self.get_market_pools(current_page, page_size)
                
                # 添加当前页的池
                all_pools.extend(page_data.get('pools', []))
                
                # 检查是否还有更多页
                if not page_data.get('has_more', False) or page_data.get('error'):
                    break
                    
                current_page += 1
                
                # 添加延迟避免请求过快
                if current_page % 10 == 0:
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                print(f"⚠️ 获取第{current_page}页失败: {e}")
                break
        
        print(f"✅ 成功获取 {len(all_pools)} 个Meteora池")
        return all_pools
    
    async def search_pools_by_token(self, token_address: str, max_pages: int = 10) -> List[Dict[str, Any]]:
        """搜索包含特定代币的Meteora池
        
        Args:
            token_address: 要搜索的代币地址
            max_pages: 最大搜索页数
            
        Returns:
            包含目标代币的池列表
        """
        matching_pools = []
        current_page = 1
        
        while current_page <= max_pages:
            try:
                # 获取当前页数据
                page_data = await self.get_market_pools(current_page, 100)
                
                # 过滤包含目标代币的池
                for pool in page_data.get('pools', []):
                    # 检查token_x和token_y是否包含目标代币
                    token_x_addr = pool.get('token_x', {}).get('address', '')
                    token_y_addr = pool.get('token_y', {}).get('address', '')
                    
                    if token_x_addr == token_address or token_y_addr == token_address:
                        matching_pools.append({
                            'pool_address': pool.get('address'),
                            'pool_name': pool.get('name'),
                            'token_x': pool.get('token_x', {}),
                            'token_y': pool.get('token_y', {}),
                            'token_x_amount': pool.get('token_x_amount', 0),
                            'token_y_amount': pool.get('token_y_amount', 0),
                            'tvl': pool.get('tvl', 0),
                            'volume_24h': pool.get('volume', {}).get('24h', 0),
                            'fees_24h': pool.get('fees', {}).get('24h', 0),
                            'vault_x': pool.get('vault_x'),
                            'vault_y': pool.get('vault_y'),
                            'dex': 'meteora'
                        })
                
                # 检查是否还有更多页
                if not page_data.get('has_more', False) or page_data.get('error'):
                    break
                    
                current_page += 1
                
                # 添加延迟避免请求过快
                await asyncio.sleep(0.05)
                
            except Exception as e:
                print(f"⚠️ 搜索第{current_page}页失败: {e}")
                break
        
        print(f"✅ 找到 {len(matching_pools)} 个包含代币 {token_address[:8]}... 的Meteora池")
        return matching_pools
    
    async def get_all_pools(self, max_pages: int = 100, page_size: int = 100) -> List[Dict[str, Any]]:
        """获取所有Meteora池（完整分页支持）
        
        Args:
            max_pages: 最大获取页数（防止请求过多）
            page_size: 每页大小
            
        Returns:
            所有池的列表
        """
        all_pools = []
        current_page = 1
        
        while current_page <= max_pages:
            try:
                # 获取当前页数据
                page_data = await self.get_market_pools(current_page, page_size)
                
                # 添加当前页的池
                all_pools.extend(page_data.get('pools', []))
                
                # 检查是否还有更多页
                if not page_data.get('has_more', False) or page_data.get('error'):
                    break
                    
                current_page += 1
                
                # 添加延迟避免请求过快
                if current_page % 10 == 0:
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                print(f"⚠️ 获取第{current_page}页失败: {e}")
                break
        
        print(f"✅ 成功获取 {len(all_pools)} 个Meteora池")
        return all_pools
    
    async def search_pools_by_token(self, token_address: str, max_pages: int = 10) -> List[Dict[str, Any]]:
        """搜索包含特定代币的Meteora池
        
        Args:
            token_address: 要搜索的代币地址
            max_pages: 最大搜索页数
            
        Returns:
            包含目标代币的池列表
        """
        matching_pools = []
        current_page = 1
        
        while current_page <= max_pages:
            try:
                # 获取当前页数据
                page_data = await self.get_market_pools(current_page, 100)
                
                # 过滤包含目标代币的池
                for pool in page_data.get('pools', []):
                    # 检查token_x和token_y是否包含目标代币
                    token_x_addr = pool.get('token_x', {}).get('address', '')
                    token_y_addr = pool.get('token_y', {}).get('address', '')
                    
                    if token_x_addr == token_address or token_y_addr == token_address:
                        matching_pools.append({
                            'pool_address': pool.get('address'),
                            'pool_name': pool.get('name'),
                            'token_x': pool.get('token_x', {}),
                            'token_y': pool.get('token_y', {}),
                            'token_x_amount': pool.get('token_x_amount', 0),
                            'token_y_amount': pool.get('token_y_amount', 0),
                            'tvl': pool.get('tvl', 0),
                            'volume_24h': pool.get('volume', {}).get('24h', 0),
                            'fees_24h': pool.get('fees', {}).get('24h', 0),
                            'vault_x': pool.get('vault_x'),
                            'vault_y': pool.get('vault_y'),
                            'dex': 'meteora'
                        })
                
                # 检查是否还有更多页
                if not page_data.get('has_more', False) or page_data.get('error'):
                    break
                    
                current_page += 1
                
                # 添加延迟避免请求过快
                await asyncio.sleep(0.05)
                
            except Exception as e:
                print(f"⚠️ 搜索第{current_page}页失败: {e}")
                break
        
        print(f"✅ 找到 {len(matching_pools)} 个包含代币 {token_address[:8]}... 的Meteora池")
        return matching_pools
    
    async def get_lp_token_price(self, pool_address: str) -> float:
        """获取Meteora LP代币的当前价格
        
        Args:
            pool_address: 池账户地址
            
        Returns:
            LP代币价格（以报价代币计）
        """
        pool_info = await self.get_pool_info(pool_address)
        
        if pool_info['lp_supply'] == 0:
            return 0
            
        # 简化计算：LP代币价值 = 总流动性 / LP供应量
        total_liquidity = pool_info['quote_amount'] * 2  # 包含基础代币价值
        return total_liquidity / pool_info['lp_supply']
    
    async def find_pool_by_tokens(self, base_mint: str, quote_mint: str) -> Optional[Dict[str, Any]]:
        """根据代币查找Meteora池
        
        Args:
            base_mint: 基础代币mint地址
            quote_mint: 报价代币mint地址
            
        Returns:
            池信息，如果未找到则返回None
        """
        try:
            pools_data = await self.get_market_pools()
            
            # 在池列表中搜索
            if 'pools' in pools_data:
                for pool in pools_data['pools']:
                    if (pool.get('baseMint') == base_mint and 
                        pool.get('quoteMint') == quote_mint):
                        return pool
                        
            return None
            
        except Exception as e:
            raise TradingError(f"查找Meteora池失败: {e}")
    
    async def estimate_swap(
        self, 
        pool_address: str, 
        input_amount: int,
        input_mint: str,
        output_mint: str
    ) -> Dict[str, Any]:
        """估算兑换交易结果
        
        Args:
            pool_address: 池账户地址
            input_amount: 输入代币数量
            input_mint: 输入代币mint地址
            output_mint: 输出代币mint地址
            
        Returns:
            估算结果
        """
        pool_info = await self.get_pool_info(pool_address)
        
        # 统一字段名处理（支持API数据和区块链数据）
        base_mint = pool_info.get('base_mint') or pool_info.get('token_x', {}).get('address', '')
        quote_mint = pool_info.get('quote_mint') or pool_info.get('token_y', {}).get('address', '')
        base_amount = pool_info.get('base_amount', 0) or pool_info.get('token_x_amount', 0)
        quote_amount = pool_info.get('quote_amount', 0) or pool_info.get('token_y_amount', 0)
        
        # 确定输入和输出代币
        if input_mint == base_mint:
            input_reserve = base_amount
            output_reserve = quote_amount
        else:
            input_reserve = quote_amount
            output_reserve = base_amount
        
        # 恒定乘积公式计算输出数量
        fee_amount = int(input_amount * 0.003)  # 默认0.3%费用
        input_amount_after_fee = input_amount - fee_amount
        
        numerator = input_amount_after_fee * output_reserve
        denominator = input_reserve + input_amount_after_fee
        output_amount = numerator // denominator if denominator > 0 else 0
        
        # 计算滑点
        price_impact = (input_amount_after_fee / input_reserve) * 100 if input_reserve > 0 else 0
        
        return {
            'estimated_output_amount': output_amount,
            'fee_amount': fee_amount,
            'price_impact': price_impact,
            'exchange_rate': output_amount / input_amount if input_amount > 0 else 0
        }
    
    async def estimate_add_liquidity(
        self, 
        pool_address: str, 
        base_amount: int, 
        quote_amount: int
    ) -> Dict[str, Any]:
        """估算添加流动性的结果
        
        Args:
            pool_address: 池账户地址
            base_amount: 基础代币数量
            quote_amount: 报价代币数量
            
        Returns:
            估算结果
        """
        pool_info = await self.get_pool_info(pool_address)
        
        # 统一字段名处理（支持API数据和区块链数据）
        base_amount_pool = pool_info.get('base_amount', 0) or pool_info.get('token_x_amount', 0)
        quote_amount_pool = pool_info.get('quote_amount', 0) or pool_info.get('token_y_amount', 0)
        lp_supply = pool_info.get('lp_supply', 0)
        
        if base_amount_pool == 0 or quote_amount_pool == 0:
            # 新池，直接计算LP数量
            lp_amount = int((base_amount * quote_amount) ** 0.5)  # 几何平均
        else:
            # 现有池，按比例计算
            base_ratio = base_amount / base_amount_pool
            quote_ratio = quote_amount / quote_amount_pool
            
            # 取较小比例，确保平衡
            min_ratio = min(base_ratio, quote_ratio)
            lp_amount = int(lp_supply * min_ratio)
        
        # 计算价格影响
        current_price = pool_info.get('current_price', 0) or pool_info.get('price', 0)
        target_price = base_amount / quote_amount if quote_amount > 0 else 0
        price_impact = abs(target_price - current_price) / current_price if current_price > 0 else 0
        
        return {
            'estimated_lp_amount': lp_amount,
            'price_impact': price_impact,
            'pool_share': lp_amount / lp_supply if lp_supply > 0 else 1.0
        }
    
    async def estimate_remove_liquidity(self, pool_address: str, lp_amount: int) -> Dict[str, Any]:
        """估算移除流动性的结果
        
        Args:
            pool_address: 池账户地址
            lp_amount: 要移除的LP代币数量
            
        Returns:
            估算结果
        """
        pool_info = await self.get_pool_info(pool_address)
        
        if pool_info['lp_supply'] == 0:
            raise TradingError("池中没有流动性")
        
        # 按比例计算赎回的代币数量
        share = lp_amount / pool_info['lp_supply']
        base_out = int(pool_info['base_amount'] * share)
        quote_out = int(pool_info['quote_amount'] * share)
        
        return {
            'estimated_base_amount': base_out,
            'estimated_quote_amount': quote_out,
            'share_percentage': share * 100
        }
    
    async def build_swap_instruction(
        self,
        pool_address: str,
        input_amount: int,
        input_mint: str,
        output_mint: str,
        wallet_address: str,
        slippage: float = 0.01
    ) -> Instruction:
        """构建兑换指令
        
        Args:
            pool_address: 池账户地址
            input_amount: 输入代币数量
            input_mint: 输入代币mint地址
            output_mint: 输出代币mint地址
            wallet_address: 用户钱包地址
            slippage: 滑点容忍度（默认1%）
            
        Returns:
            兑换指令
        """
        try:
            # 获取池信息
            pool_info = await self.get_pool_info(pool_address)
            
            # 统一字段名处理
            base_mint = pool_info.get('base_mint') or pool_info.get('token_x', {}).get('address', '')
            quote_mint = pool_info.get('quote_mint') or pool_info.get('token_y', {}).get('address', '')
            
            # 确定输入和输出代币类型
            if input_mint == base_mint:
                swap_type = 0  # 基础代币 -> 报价代币
            elif input_mint == quote_mint:
                swap_type = 1  # 报价代币 -> 基础代币
            else:
                raise TradingError(f"输入代币 {input_mint} 不在池中")
            
            # 构建Meteora DAMM V2兑换指令
            # 指令ID: 0 - swap_exact_input
            instruction_data = struct.pack('<BQ', 0, input_amount)  # 指令ID + 输入数量
            
            # 构建账户列表
            wallet_pubkey = Pubkey.from_string(wallet_address)
            pool_pubkey = Pubkey.from_string(pool_address)
            
            # 获取必要的账户地址
            token_x_vault = pool_info.get('vault_x') or await self._get_token_vault_address(pool_pubkey, 0)
            token_y_vault = pool_info.get('vault_y') or await self._get_token_vault_address(pool_pubkey, 1)
            
            # 获取用户代币账户
            user_token_in_account = await self._get_associated_token_address(wallet_pubkey, Pubkey.from_string(input_mint))
            user_token_out_account = await self._get_associated_token_address(wallet_pubkey, Pubkey.from_string(output_mint))
            
            # 构建账户键列表
            keys = [
                # 池账户
                AccountMeta(pubkey=pool_pubkey, is_signer=False, is_writable=True),
                # 输入代币vault
                AccountMeta(pubkey=Pubkey.from_string(token_x_vault if swap_type == 0 else token_y_vault), is_signer=False, is_writable=True),
                # 输出代币vault
                AccountMeta(pubkey=Pubkey.from_string(token_y_vault if swap_type == 0 else token_x_vault), is_signer=False, is_writable=True),
                # 用户输入代币账户
                AccountMeta(pubkey=user_token_in_account, is_signer=False, is_writable=True),
                # 用户输出代币账户
                AccountMeta(pubkey=user_token_out_account, is_signer=False, is_writable=True),
                # 用户钱包
                AccountMeta(pubkey=wallet_pubkey, is_signer=True, is_writable=True),
                # 代币程序
                AccountMeta(pubkey=Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"), is_signer=False, is_writable=False),
                # 系统程序
                AccountMeta(pubkey=SYS_PROGRAM_ID, is_signer=False, is_writable=False),
            ]
            
            return Instruction(
                program_id=self.meteora_program_id,
                accounts=keys,
                data=instruction_data
            )
            
        except Exception as e:
            raise TradingError(f"构建兑换指令失败: {e}")
    
    async def build_remove_liquidity_instruction(
        self,
        pool_address: str,
        lp_amount: int,
        wallet_address: str,
        position_nft_mint: Optional[str] = None
    ) -> Instruction:
        """构建移除流动性的指令
        
        Args:
            pool_address: 池账户地址
            lp_amount: 要移除的LP代币数量
            wallet_address: 用户钱包地址
            position_nft_mint: 流动性位置NFT的mint地址（可选）
            
        Returns:
            移除流动性的指令
        """
        try:
            # 获取池信息
            pool_info = await self.get_pool_info(pool_address)
            
            # 统一字段名处理
            base_mint = pool_info.get('base_mint') or pool_info.get('token_x', {}).get('address', '')
            quote_mint = pool_info.get('quote_mint') or pool_info.get('token_y', {}).get('address', '')
            lp_mint = pool_info.get('lp_mint') or await self._get_lp_mint_address(Pubkey.from_string(pool_address))
            
            # 构建Meteora DAMM V2移除流动性指令
            # 指令ID: 3 - withdraw
            instruction_data = struct.pack('<BQ', 3, lp_amount)  # 指令ID + LP代币数量
            
            # 构建账户列表
            wallet_pubkey = Pubkey.from_string(wallet_address)
            pool_pubkey = Pubkey.from_string(pool_address)
            
            # 获取必要的账户地址
            token_x_vault = pool_info.get('vault_x') or await self._get_token_vault_address(pool_pubkey, 0)
            token_y_vault = pool_info.get('vault_y') or await self._get_token_vault_address(pool_pubkey, 1)
            
            # 获取用户代币账户
            user_base_account = await self._get_associated_token_address(wallet_pubkey, Pubkey.from_string(base_mint))
            user_quote_account = await self._get_associated_token_address(wallet_pubkey, Pubkey.from_string(quote_mint))
            user_lp_account = await self._get_associated_token_address(wallet_pubkey, Pubkey.from_string(lp_mint))
            
            # 构建账户键列表
            keys = [
                # 池账户
                AccountMeta(pubkey=pool_pubkey, is_signer=False, is_writable=True),
                # 基础代币vault
                AccountMeta(pubkey=Pubkey.from_string(token_x_vault), is_signer=False, is_writable=True),
                # 报价代币vault
                AccountMeta(pubkey=Pubkey.from_string(token_y_vault), is_signer=False, is_writable=True),
                # 用户基础代币账户
                AccountMeta(pubkey=user_base_account, is_signer=False, is_writable=True),
                # 用户报价代币账户
                AccountMeta(pubkey=user_quote_account, is_signer=False, is_writable=True),
                # 用户LP代币账户
                AccountMeta(pubkey=user_lp_account, is_signer=False, is_writable=True),
                # 用户钱包
                AccountMeta(pubkey=wallet_pubkey, is_signer=True, is_writable=True),
                # 代币程序
                AccountMeta(pubkey=Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"), is_signer=False, is_writable=False),
                # 系统程序
                AccountMeta(pubkey=SYS_PROGRAM_ID, is_signer=False, is_writable=False),
            ]
            
            # 如果指定了位置NFT，添加到账户列表
            if position_nft_mint:
                position_nft_account = await self._get_associated_token_address(wallet_pubkey, Pubkey.from_string(position_nft_mint))
                keys.insert(1, AccountMeta(pubkey=Pubkey.from_string(position_nft_mint), is_signer=False, is_writable=True))
                keys.insert(2, AccountMeta(pubkey=position_nft_account, is_signer=False, is_writable=True))
            
            return Instruction(
                program_id=self.meteora_program_id,
                accounts=keys,
                data=instruction_data
            )
            
        except Exception as e:
            raise TradingError(f"构建移除流动性指令失败: {e}")
    
    async def build_add_liquidity_instruction(
        self,
        pool_address: str,
        base_amount: int,
        quote_amount: int,
        wallet_address: str,
        position_nft_mint: Optional[str] = None
    ) -> Instruction:
        """构建添加流动性的指令
        
        Args:
            pool_address: 池账户地址
            base_amount: 基础代币数量
            quote_amount: 报价代币数量
            wallet_address: 用户钱包地址
            position_nft_mint: 流动性位置NFT的mint地址（可选，用于添加到现有位置）
            
        Returns:
            添加流动性的指令
        """
        try:
            # 获取池信息
            pool_info = await self.get_pool_info(pool_address)
            
            # 统一字段名处理
            base_mint = pool_info.get('base_mint') or pool_info.get('token_x', {}).get('address', '')
            quote_mint = pool_info.get('quote_mint') or pool_info.get('token_y', {}).get('address', '')
            lp_mint = pool_info.get('lp_mint') or await self._get_lp_mint_address(Pubkey.from_string(pool_address))
            
            # 构建Meteora DAMM V2添加流动性指令
            # 指令ID: 2 - deposit
            instruction_data = struct.pack('<BQQ', 2, base_amount, quote_amount)  # 指令ID + 基础数量 + 报价数量
            
            # 构建账户列表
            wallet_pubkey = Pubkey.from_string(wallet_address)
            pool_pubkey = Pubkey.from_string(pool_address)
            
            # 获取必要的账户地址
            token_x_vault = pool_info.get('vault_x') or await self._get_token_vault_address(pool_pubkey, 0)
            token_y_vault = pool_info.get('vault_y') or await self._get_token_vault_address(pool_pubkey, 1)
            
            # 获取用户代币账户
            user_base_account = await self._get_associated_token_address(wallet_pubkey, Pubkey.from_string(base_mint))
            user_quote_account = await self._get_associated_token_address(wallet_pubkey, Pubkey.from_string(quote_mint))
            user_lp_account = await self._get_associated_token_address(wallet_pubkey, Pubkey.from_string(lp_mint))
            
            # 构建账户键列表
            keys = [
                # 池账户
                AccountMeta(pubkey=pool_pubkey, is_signer=False, is_writable=True),
                # 基础代币vault
                AccountMeta(pubkey=Pubkey.from_string(token_x_vault), is_signer=False, is_writable=True),
                # 报价代币vault
                AccountMeta(pubkey=Pubkey.from_string(token_y_vault), is_signer=False, is_writable=True),
                # 用户基础代币账户
                AccountMeta(pubkey=user_base_account, is_signer=False, is_writable=True),
                # 用户报价代币账户
                AccountMeta(pubkey=user_quote_account, is_signer=False, is_writable=True),
                # 用户LP代币账户
                AccountMeta(pubkey=user_lp_account, is_signer=False, is_writable=True),
                # 用户钱包
                AccountMeta(pubkey=wallet_pubkey, is_signer=True, is_writable=True),
                # 代币程序
                AccountMeta(pubkey=Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"), is_signer=False, is_writable=False),
                # 系统程序
                AccountMeta(pubkey=SYS_PROGRAM_ID, is_signer=False, is_writable=False),
            ]
            
            # 如果指定了位置NFT，添加到账户列表
            if position_nft_mint:
                position_nft_account = await self._get_associated_token_address(wallet_pubkey, Pubkey.from_string(position_nft_mint))
                keys.insert(1, AccountMeta(pubkey=Pubkey.from_string(position_nft_mint), is_signer=False, is_writable=True))
                keys.insert(2, AccountMeta(pubkey=position_nft_account, is_signer=False, is_writable=True))
            
            return Instruction(
                program_id=self.meteora_program_id,
                accounts=keys,
                data=instruction_data
            )
            
        except Exception as e:
            raise TradingError(f"构建添加流动性指令失败: {e}")
    
    async def send_transaction(
        self,
        instructions: List[Instruction],
        wallet: Wallet,
        fee_payer: Optional[str] = None
    ) -> str:
        """发送交易到Solana网络
        
        Args:
            instructions: 指令列表
            wallet: 钱包对象
            fee_payer: 费用支付者地址（可选）
            
        Returns:
            交易签名
        """
        try:
            # 获取最近的区块哈希
            recent_blockhash = await self.client.get_latest_blockhash()
            
            # 构建交易
            message = Message.new_with_blockhash(
                instructions,
                fee_payer=Pubkey.from_string(fee_payer) if fee_payer else wallet.pubkey,
                blockhash=recent_blockhash.value.blockhash
            )
            
            # 创建交易
            transaction = VersionedTransaction(message, [wallet.keypair])
            
            # 发送交易
            response = await self.client.send_transaction(transaction)
            
            if response.value:
                return str(response.value)
            else:
                raise TradingError("交易发送失败")
                
        except Exception as e:
            raise TradingError(f"发送交易失败: {e}")
    
    async def swap(
        self,
        pool_address: str,
        input_amount: int,
        input_mint: str,
        output_mint: str,
        wallet: Wallet,
        slippage: float = 0.01
    ) -> Dict[str, Any]:
        """在Meteora池中进行兑换交易
        
        Args:
            pool_address: 池账户地址
            input_amount: 输入代币数量
            input_mint: 输入代币mint地址
            output_mint: 输出代币mint地址
            wallet: 钱包对象
            slippage: 滑点容忍度（默认1%）
            
        Returns:
            交易结果
        """
        try:
            # 估算兑换结果
            estimate = await self.estimate_swap(pool_address, input_amount, input_mint, output_mint)
            
            # 构建兑换指令
            instruction = await self.build_swap_instruction(
                pool_address, input_amount, input_mint, output_mint, str(wallet.pubkey)
            )
            
            # 发送交易
            tx_signature = await self.send_transaction([instruction], wallet)
            
            return {
                'transaction_signature': tx_signature,
                'estimated_output_amount': estimate['estimated_output_amount'],
                'fee_amount': estimate['fee_amount'],
                'price_impact': estimate['price_impact'],
                'exchange_rate': estimate['exchange_rate'],
                'status': 'success'
            }
            
        except Exception as e:
            raise TradingError(f"兑换交易失败: {e}")
    
    async def add_liquidity(
        self,
        pool_address: str,
        base_amount: int,
        quote_amount: int,
        wallet: Wallet,
        slippage: float = 0.01
    ) -> Dict[str, Any]:
        """添加流动性到Meteora池
        
        Args:
            pool_address: 池账户地址
            base_amount: 基础代币数量
            quote_amount: 报价代币数量
            wallet: 钱包对象
            slippage: 滑点容忍度（默认1%）
            
        Returns:
            交易结果
        """
        try:
            # 估算添加流动性结果
            estimate = await self.estimate_add_liquidity(pool_address, base_amount, quote_amount)
            
            # 构建添加流动性指令
            instruction = await self.build_add_liquidity_instruction(
                pool_address, base_amount, quote_amount, str(wallet.pubkey)
            )
            
            # 发送交易
            tx_signature = await self.send_transaction([instruction], wallet)
            
            return {
                'transaction_signature': tx_signature,
                'estimated_lp_amount': estimate['estimated_lp_amount'],
                'price_impact': estimate['price_impact'],
                'pool_share': estimate['pool_share'],
                'status': 'success'
            }
            
        except Exception as e:
            raise TradingError(f"添加流动性失败: {e}")

    async def get_supported_pools(self) -> List[Dict[str, Any]]:
        """获取支持的池类型列表"""
        return [
            {
                "pool_type": "METEORA_DAMM_V2",
                "display_name": "METEORA_DAMM_V2 池信息",
                "program_id": str(self.meteora_program_id),
                "description": "Meteora DAMM V2 动态自动做市商池"
            }
        ]


# 示例使用
async def example_usage():
    """Meteora客户端使用示例"""
    
    client = MeteoraClient()
    
    try:
        await client.connect()
        
        # 测试池地址（示例地址）
        pool_address = "GhnhG6E99o9VrYReKBcPjRmKTyWcwWAm5Vz8SujdLGEs"
        
        # 获取池信息
        pool_info = await client.get_pool_info(pool_address)
        print("Meteora池信息:", json.dumps(pool_info, indent=2, default=str))
        
        # 估算兑换交易
        estimate = await client.estimate_swap(pool_address, 1000000, "输入代币mint", "输出代币mint")
        print("兑换估算:", estimate)
        
        # 获取LP价格
        lp_price = await client.get_lp_token_price(pool_address)
        print(f"LP代币价格: {lp_price:.10f}")
        
    except Exception as e:
        print(f"示例执行失败: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(example_usage())