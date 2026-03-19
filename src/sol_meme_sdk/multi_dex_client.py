#!/usr/bin/env python3
"""
多DEX客户端 - 智能处理Raydium、Meteora等不同类型的池
"""

import asyncio
import aiohttp
import json
import base64
from typing import Dict, Any, Optional, List
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solders.pubkey import Pubkey

from .config import get_config
from .exceptions import TradingError
from .wallet import Wallet
from .raydium_client import RaydiumClient
from .meteora_client import MeteoraClient


class MultiDexClient:
    """多DEX客户端类，智能处理不同类型的池"""
    
    def __init__(self, rpc_url: Optional[str] = None, network: str = "mainnet"):
        """初始化多DEX客户端
        
        Args:
            rpc_url: Solana RPC URL
            network: 网络类型 (mainnet, devnet, testnet)
        """
        self.rpc_url = rpc_url or get_config().solana_rpc_endpoint or "https://api.mainnet-beta.solana.com"
        self.network = network
        self.client = AsyncClient(self.rpc_url)
        
        # 初始化各DEX客户端
        self.raydium_client = RaydiumClient(rpc_url, network)
        self.meteora_client = MeteoraClient(rpc_url, network)
        
        # 池类型识别配置
        self.pool_type_indicators = {
            "RAYDIUM_AMM": {
                "display_names": ["Raydium AMM池信息", "Pump AMM池信息"],
                "program_id": "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA",
                "client": self.raydium_client
            },
            "METEORA_DAMM_V2": {
                "display_names": ["METEORA_DAMM_V2 池信息"],
                "program_id": "cpamdpZCGKUy5JxQXB4dcpGPiikHawvSWAd6mEn1sGG",
                "client": self.meteora_client
            },
            "DYNAMIC_BC": {
                "display_names": ["Dynamic BC 池信息"],
                "program_id": None,  # 需要特殊处理
                "client": None
            }
        }
        
    async def connect(self):
        """连接到Solana网络"""
        await self.client.__aenter__()
        await self.raydium_client.connect()
        await self.meteora_client.connect()
        
    async def close(self):
        """关闭连接"""
        await self.meteora_client.close()
        await self.raydium_client.close()
        await self.client.__aexit__(None, None, None)
        
    async def identify_pool_type(self, pool_address: str) -> Dict[str, Any]:
        """识别池的类型
        
        Args:
            pool_address: 池账户地址
            
        Returns:
            池类型识别结果
        """
        try:
            pool_pubkey = Pubkey.from_string(pool_address)
            account_info = await self.client.get_account_info(pool_pubkey, commitment=Confirmed)
            
            if not account_info.value:
                raise TradingError(f"池账户不存在: {pool_address}")
            
            # 通过程序ID识别池类型
            owner_program = str(account_info.value.owner)
            
            for pool_type, config in self.pool_type_indicators.items():
                if config["program_id"] and config["program_id"] == owner_program:
                    return {
                        "pool_type": pool_type,
                        "display_name": config["display_names"][0],
                        "supported": config["client"] is not None,
                        "client": config["client"]
                    }
            
            # 如果无法通过程序ID识别，返回未知类型
            return {
                "pool_type": "UNKNOWN",
                "display_name": "未知池类型",
                "supported": False,
                "client": None
            }
            
        except Exception as e:
            raise TradingError(f"识别池类型失败: {e}")
    
    async def get_pool_info(self, pool_address: str) -> Dict[str, Any]:
        """获取池的详细信息，自动识别池类型
        
        Args:
            pool_address: 池账户地址
            
        Returns:
            池信息字典
        """
        try:
            # 识别池类型
            pool_type_info = await self.identify_pool_type(pool_address)
            
            if not pool_type_info["supported"]:
                raise TradingError(f"不支持的池类型: {pool_type_info['display_name']}")
            
            # 使用对应的客户端获取池信息
            client = pool_type_info["client"]
            pool_info = await client.get_pool_info(pool_address)
            pool_info["pool_type"] = pool_type_info["pool_type"]
            pool_info["display_name"] = pool_type_info["display_name"]
            pool_info["supported"] = pool_type_info["supported"]
            
            return pool_info
            
        except Exception as e:
            raise TradingError(f"获取池信息失败: {e}")
    
    async def get_lp_token_price(self, pool_address: str) -> float:
        """获取LP代币的当前价格
        
        Args:
            pool_address: 池账户地址
            
        Returns:
            LP代币价格（以报价代币计）
        """
        try:
            # 识别池类型
            pool_type_info = await self.identify_pool_type(pool_address)
            
            if not pool_type_info["supported"]:
                raise TradingError(f"不支持的池类型: {pool_type_info['display_name']}")
            
            # 使用对应的客户端获取LP价格
            client = pool_type_info["client"]
            return await client.get_lp_token_price(pool_address)
            
        except Exception as e:
            raise TradingError(f"获取LP价格失败: {e}")
    
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
        try:
            # 识别池类型
            pool_type_info = await self.identify_pool_type(pool_address)
            
            if not pool_type_info["supported"]:
                raise TradingError(f"不支持的池类型: {pool_type_info['display_name']}")
            
            # 使用对应的客户端估算
            client = pool_type_info["client"]
            return await client.estimate_add_liquidity(pool_address, base_amount, quote_amount)
            
        except Exception as e:
            raise TradingError(f"估算添加流动性失败: {e}")
    
    async def estimate_remove_liquidity(self, pool_address: str, lp_amount: int) -> Dict[str, Any]:
        """估算移除流动性的结果
        
        Args:
            pool_address: 池账户地址
            lp_amount: 要移除的LP代币数量
            
        Returns:
            估算结果
        """
        try:
            # 识别池类型
            pool_type_info = await self.identify_pool_type(pool_address)
            
            if not pool_type_info["supported"]:
                raise TradingError(f"不支持的池类型: {pool_type_info['display_name']}")
            
            # 使用对应的客户端估算
            client = pool_type_info["client"]
            return await client.estimate_remove_liquidity(pool_address, lp_amount)
            
        except Exception as e:
            raise TradingError(f"估算移除流动性失败: {e}")
    
    async def add_liquidity(
        self,
        pool_address: str,
        base_amount: int,
        quote_amount: int,
        wallet: Wallet,
        slippage: float = 0.01
    ) -> Dict[str, Any]:
        """添加流动性到池
        
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
            # 识别池类型
            pool_type_info = await self.identify_pool_type(pool_address)
            
            if not pool_type_info["supported"]:
                raise TradingError(f"不支持的池类型: {pool_type_info['display_name']}")
            
            # 使用对应的客户端添加流动性
            client = pool_type_info["client"]
            return await client.add_liquidity(pool_address, base_amount, quote_amount, wallet, slippage)
            
        except Exception as e:
            raise TradingError(f"添加流动性失败: {e}")
    
    async def remove_liquidity(
        self,
        pool_address: str,
        lp_amount: int,
        wallet: Wallet,
        slippage: float = 0.01
    ) -> Dict[str, Any]:
        """从池移除流动性
        
        Args:
            pool_address: 池账户地址
            lp_amount: 要移除的LP代币数量
            wallet: 钱包对象
            slippage: 滑点容忍度（默认1%）
            
        Returns:
            交易结果
        """
        try:
            # 识别池类型
            pool_type_info = await self.identify_pool_type(pool_address)
            
            if not pool_type_info["supported"]:
                raise TradingError(f"不支持的池类型: {pool_type_info['display_name']}")
            
            # 使用对应的客户端移除流动性
            client = pool_type_info["client"]
            return await client.remove_liquidity(pool_address, lp_amount, wallet, slippage)
            
        except Exception as e:
            raise TradingError(f"移除流动性失败: {e}")
    
    async def get_supported_pools(self) -> List[Dict[str, Any]]:
        """获取所有支持的池类型信息
        
        Returns:
            支持的池类型列表
        """
        supported_pools = []
        
        for pool_type, config in self.pool_type_indicators.items():
            if config["client"] is not None:
                supported_pools.append({
                    "pool_type": pool_type,
                    "display_names": config["display_names"],
                    "program_id": config["program_id"],
                    "supported": True
                })
        
        return supported_pools
    
    async def analyze_pool_compatibility(self, pool_address: str) -> Dict[str, Any]:
        """分析池的兼容性
        
        Args:
            pool_address: 池账户地址
            
        Returns:
            兼容性分析结果
        """
        try:
            pool_type_info = await self.identify_pool_type(pool_address)
            
            analysis = {
                "pool_address": pool_address,
                "pool_type": pool_type_info["pool_type"],
                "display_name": pool_type_info["display_name"],
                "supported": pool_type_info["supported"],
                "recommendation": "",
                "actions_available": []
            }
            
            if pool_type_info["supported"]:
                analysis["recommendation"] = "✅ 完全支持，可以立即开始交易"
                analysis["actions_available"] = [
                    "获取池信息",
                    "计算LP价格", 
                    "估算添加流动性",
                    "估算移除流动性",
                    "实际交易操作"
                ]
            else:
                if pool_type_info["pool_type"] == "DYNAMIC_BC":
                    analysis["recommendation"] = "⚠️ Dynamic BC池需要特殊处理，可能需要联系GMGN获取技术细节"
                else:
                    analysis["recommendation"] = "❌ 不支持的池类型，需要额外开发工作"
            
            return analysis
            
        except Exception as e:
            raise TradingError(f"分析池兼容性失败: {e}")


# 示例使用
async def example_usage():
    """多DEX客户端使用示例"""
    
    client = MultiDexClient()
    
    try:
        await client.connect()
        
        # 获取支持的池类型
        supported_pools = await client.get_supported_pools()
        print("支持的池类型:", json.dumps(supported_pools, indent=2, default=str))
        
        # 测试不同池的兼容性
        test_pools = [
            "CSRJSQ5daTA9sehZAboPQYAJqbptJgzQ2e7aGduWzQ8U",  # Raydium AMM池
            "GhnhG6E99o9VrYReKBcPjRmKTyWcwWAm5Vz8SujdLGEs",  # Meteora DAMM V2池
            "EcSrKwco6iun9xDShsMJUFGTc9kiCjkZ6UJGJ8Gr2vQV"   # Dynamic BC池
        ]
        
        for pool_address in test_pools:
            print(f"\n分析池: {pool_address}")
            try:
                # 分析兼容性
                analysis = await client.analyze_pool_compatibility(pool_address)
                print("兼容性分析:", json.dumps(analysis, indent=2, default=str))
                
                # 如果支持，获取详细信息
                if analysis["supported"]:
                    pool_info = await client.get_pool_info(pool_address)
                    print("池详细信息:", json.dumps(pool_info, indent=2, default=str))
                    
                    # 获取LP价格
                    lp_price = await client.get_lp_token_price(pool_address)
                    print(f"LP代币价格: {lp_price:.10f}")
                    
            except Exception as e:
                print(f"分析失败: {e}")
        
    except Exception as e:
        print(f"示例执行失败: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(example_usage())