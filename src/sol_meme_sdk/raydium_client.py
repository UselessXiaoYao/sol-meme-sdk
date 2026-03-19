"""
Raydium客户端 - 用于LP代币交易
"""

import asyncio
import aiohttp
import json
import base64
from typing import Dict, Any, Optional, List
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solders.transaction import Transaction
from solders.pubkey import Pubkey
from solders.system_program import ID as SYS_PROGRAM_ID
from solders.instruction import Instruction
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from solders.message import Message

from .config import get_config
from .exceptions import TradingError
from .wallet import Wallet
from .api_config import get_api_config


class RaydiumClient:
    """Raydium客户端类，用于处理LP代币交易"""
    
    def __init__(self, rpc_url: Optional[str] = None, network: str = "mainnet"):
        """初始化Raydium客户端
        
        Args:
            rpc_url: Solana RPC URL
            network: 网络类型 (mainnet, devnet, testnet)
        """
        # 从API配置获取URL
        self.api_config = get_api_config()
        self.rpc_url = rpc_url or self.api_config.solana_rpc_endpoint
        self.network = network
        self.client = AsyncClient(self.rpc_url)
        self.raydium_api_base = self.api_config.raydium_api_base
        
        # Raydium程序ID（从环境变量获取）
        self.raydium_program_id = Pubkey.from_string(self.api_config.raydium_program_id)
        
    async def connect(self):
        """连接到Solana网络"""
        await self.client.__aenter__()
        
    async def close(self):
        """关闭连接"""
        await self.client.__aexit__(None, None, None)
        
    async def get_pool_info(self, pool_address: str) -> Dict[str, Any]:
        """获取Raydium池的详细信息
        
        Args:
            pool_address: 池账户地址
            
        Returns:
            池信息字典
        """
        try:
            pool_pubkey = Pubkey.from_string(pool_address)
            account_info = await self.client.get_account_info(pool_pubkey, commitment=Confirmed)
            
            if not account_info.value:
                raise TradingError(f"池账户不存在: {pool_address}")
                
            data = account_info.value.data
            
            # 解析Raydium AMM池结构
            pool_info = {
                'pool_address': pool_address,
                'base_mint': str(Pubkey(data[8:40])),
                'quote_mint': str(Pubkey(data[40:72])),
                'base_amount': int.from_bytes(data[72:80], 'little'),
                'quote_amount': int.from_bytes(data[80:88], 'little'),
                'lp_mint': str(Pubkey(data[104:136])),
                'lp_supply': int.from_bytes(data[136:144], 'little'),
                'owner_program': str(account_info.value.owner)
            }
            
            # 计算价格
            if pool_info['base_amount'] > 0 and pool_info['quote_amount'] > 0:
                pool_info['price'] = pool_info['quote_amount'] / pool_info['base_amount']
                
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
        pool_info = await self.get_pool_info(pool_address)
        
        if pool_info['lp_supply'] == 0:
            return 0
            
        # 简化计算：LP代币价值 = 总流动性 / LP供应量
        total_liquidity = pool_info['quote_amount'] * 2  # 包含基础代币价值
        return total_liquidity / pool_info['lp_supply']
    
    async def get_raydium_pools(self) -> Dict[str, Any]:
        """获取Raydium的所有池列表
        
        Returns:
            池列表数据
        """
        try:
            # 使用Raydium的官方API端点
            url = f"{self.raydium_api_base}/v2/sdk/liquidity/mainnet"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data
                    else:
                        # 如果API失败，返回空数据
                        print(f"⚠️ Raydium API暂时不可用: {resp.status}")
                        return {
                            'official': [],
                            'unOfficial': []
                        }
                        
        except Exception as e:
            # API调用失败时返回空数据
            print(f"⚠️ Raydium API调用失败: {e}")
            return {
                'official': [],
                'unOfficial': []
            }
    
    async def find_pool_by_tokens(self, base_mint: str, quote_mint: str) -> Optional[Dict[str, Any]]:
        """根据代币查找Raydium池
        
        Args:
            base_mint: 基础代币mint地址
            quote_mint: 报价代币mint地址
            
        Returns:
            池信息，如果未找到则返回None
        """
        try:
            pools_data = await self.get_raydium_pools()
            
            # 在所有池类型中搜索
            for pool_type in ['official', 'unOfficial']:
                if pool_type in pools_data:
                    for pool in pools_data[pool_type]:
                        if (pool.get('baseMint') == base_mint and 
                            pool.get('quoteMint') == quote_mint):
                            return pool
                            
            return None
            
        except Exception as e:
            raise TradingError(f"查找池失败: {e}")
    
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
        
        if pool_info['base_amount'] == 0 or pool_info['quote_amount'] == 0:
            # 新池，直接计算LP数量
            lp_amount = int((base_amount * quote_amount) ** 0.5)  # 几何平均
        else:
            # 现有池，按比例计算
            base_ratio = base_amount / pool_info['base_amount']
            quote_ratio = quote_amount / pool_info['quote_amount']
            
            # 取较小比例，确保平衡
            min_ratio = min(base_ratio, quote_ratio)
            lp_amount = int(pool_info['lp_supply'] * min_ratio)
        
        return {
            'estimated_lp_amount': lp_amount,
            'price_impact': abs(base_amount / quote_amount - pool_info.get('price', 0)) / pool_info.get('price', 1),
            'pool_share': lp_amount / pool_info['lp_supply'] if pool_info['lp_supply'] > 0 else 1.0
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
    
    async def get_pool_apy(self, pool_address: str) -> float:
        """估算池的年化收益率(APY)
        
        Args:
            pool_address: 池账户地址
            
        Returns:
            估算的APY
        """
        try:
            # 这里可以集成更多数据源来计算APY
            # 暂时返回一个估算值
            pool_info = await self.get_pool_info(pool_address)
            
            # 简化计算：基于交易量和流动性估算
            if pool_info['base_amount'] > 0 and pool_info['quote_amount'] > 0:
                # 假设年化交易费率为流动性的一定比例
                daily_fee_rate = 0.001  # 0.1% 日交易费率
                annual_apy = (1 + daily_fee_rate) ** 365 - 1
                return annual_apy * 100  # 转换为百分比
            
            return 0.0
            
        except Exception as e:
            raise TradingError(f"计算APY失败: {e}")
    
    async def get_pool_volume_24h(self, pool_address: str) -> Dict[str, float]:
        """获取池的24小时交易量
        
        Args:
            pool_address: 池账户地址
            
        Returns:
            交易量信息
        """
        # 这里可以集成DEX数据源获取真实交易量
        # 暂时返回模拟数据
        pool_info = await self.get_pool_info(pool_address)
        
        # 模拟计算：基于流动性的估算
        base_volume = pool_info.get('base_amount', 0) * 0.1  # 10%的流动性作为交易量
        quote_volume = pool_info.get('quote_amount', 0) * 0.1
        
        return {
            'base_volume': base_volume,
            'quote_volume': quote_volume,
            'total_volume_usd': (base_volume + quote_volume) * 100  # 简化USD估值
        }
    
    async def build_add_liquidity_instruction(
        self,
        pool_address: str,
        base_amount: int,
        quote_amount: int,
        wallet_address: str
    ) -> Instruction:
        """构建添加流动性的指令
        
        Args:
            pool_address: 池账户地址
            base_amount: 基础代币数量
            quote_amount: 报价代币数量
            wallet_address: 用户钱包地址
            
        Returns:
            添加流动性的指令
        """
        try:
            # 获取池信息
            pool_info = await self.get_pool_info(pool_address)
            
            # 构建添加流动性的指令
            # 这里需要实现具体的Raydium指令构建逻辑
            # 暂时返回一个模拟指令
            
            keys = [
                # 添加必要的账户键
            ]
            
            data = b''  # 指令数据
            
            return Instruction(
                program_id=self.raydium_program_id,
                accounts=keys,
                data=data
            )
            
        except Exception as e:
            raise TradingError(f"构建添加流动性指令失败: {e}")
    
    async def build_remove_liquidity_instruction(
        self,
        pool_address: str,
        lp_amount: int,
        wallet_address: str
    ) -> Instruction:
        """构建移除流动性的指令
        
        Args:
            pool_address: 池账户地址
            lp_amount: 要移除的LP代币数量
            wallet_address: 用户钱包地址
            
        Returns:
            移除流动性的指令
        """
        try:
            # 获取池信息
            pool_info = await self.get_pool_info(pool_address)
            
            # 构建移除流动性的指令
            # 这里需要实现具体的Raydium指令构建逻辑
            # 暂时返回一个模拟指令
            
            keys = [
                # 添加必要的账户键
            ]
            
            data = b''  # 指令数据
            
            return Instruction(
                program_id=self.raydium_program_id,
                accounts=keys,
                data=data
            )
            
        except Exception as e:
            raise TradingError(f"构建移除流动性指令失败: {e}")
    
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
    
    async def add_liquidity(
        self,
        pool_address: str,
        base_amount: int,
        quote_amount: int,
        wallet: Wallet,
        slippage: float = 0.01
    ) -> Dict[str, Any]:
        """添加流动性到Raydium池
        
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
    
    async def remove_liquidity(
        self,
        pool_address: str,
        lp_amount: int,
        wallet: Wallet,
        slippage: float = 0.01
    ) -> Dict[str, Any]:
        """从Raydium池移除流动性
        
        Args:
            pool_address: 池账户地址
            lp_amount: 要移除的LP代币数量
            wallet: 钱包对象
            slippage: 滑点容忍度（默认1%）
            
        Returns:
            交易结果
        """
        try:
            # 估算移除流动性结果
            estimate = await self.estimate_remove_liquidity(pool_address, lp_amount)
            
            # 构建移除流动性指令
            instruction = await self.build_remove_liquidity_instruction(
                pool_address, lp_amount, str(wallet.pubkey)
            )
            
            # 发送交易
            tx_signature = await self.send_transaction([instruction], wallet)
            
            return {
                'transaction_signature': tx_signature,
                'estimated_base_amount': estimate['estimated_base_amount'],
                'estimated_quote_amount': estimate['estimated_quote_amount'],
                'share_percentage': estimate['share_percentage'],
                'status': 'success'
            }
            
        except Exception as e:
            raise TradingError(f"移除流动性失败: {e}")
    
    async def wait_for_confirmation(self, tx_signature: str, timeout: int = 30) -> bool:
        """等待交易确认
        
        Args:
            tx_signature: 交易签名
            timeout: 超时时间（秒）
            
        Returns:
            是否确认成功
        """
        try:
            signature_pubkey = Pubkey.from_string(tx_signature)
            
            # 等待交易确认
            for _ in range(timeout):
                response = await self.client.get_signature_statuses([signature_pubkey])
                
                if response.value:
                    status = response.value[0]
                    if status and status.confirmation_status == "finalized":
                        return True
                
                await asyncio.sleep(1)
            
            return False
            
        except Exception as e:
            raise TradingError(f"等待交易确认失败: {e}")


# 示例使用
async def example_usage():
    """Raydium客户端使用示例"""
    
    client = RaydiumClient()
    
    try:
        await client.connect()
        
        # 测试池地址
        pool_address = "CSRJSQ5daTA9sehZAboPQYAJqbptJgzQ2e7aGduWzQ8U"
        
        # 获取池信息
        pool_info = await client.get_pool_info(pool_address)
        print("池信息:", json.dumps(pool_info, indent=2, default=str))
        
        # 估算添加流动性
        estimate = await client.estimate_add_liquidity(pool_address, 1000000, 276748)
        print("添加流动性估算:", estimate)
        
        # 获取LP价格
        lp_price = await client.get_lp_token_price(pool_address)
        print(f"LP代币价格: {lp_price:.10f}")
        
        # 估算APY
        apy = await client.get_pool_apy(pool_address)
        print(f"估算APY: {apy:.2f}%")
        
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(example_usage())