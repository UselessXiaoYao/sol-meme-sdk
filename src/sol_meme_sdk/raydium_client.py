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

from .unified_config import get_config
from .exceptions import TradingError
from .wallet import Wallet
from .priority_fee import PriorityFeeEstimator


class RaydiumClient:
    """Raydium客户端类，用于处理LP代币交易"""
    
    def __init__(self, rpc_url: Optional[str] = None, network: str = "mainnet"):
        """初始化Raydium客户端
        
        Args:
            rpc_url: Solana RPC URL
            network: 网络类型 (mainnet, devnet, testnet)
        """
        # 从统一配置获取URL
        self.config = get_config()
        self.rpc_url = rpc_url or self.config.solana_rpc_endpoint
        self.network = network
        self.client = AsyncClient(self.rpc_url)
        self.raydium_api_base = self.config.raydium_api_base
        
        # Raydium程序ID（从环境变量获取）
        self.raydium_program_id = Pubkey.from_string(self.config.raydium_program_id)
        
        # 初始化优先级费用估算服务
        self.priority_fee_estimator = PriorityFeeEstimator(self.rpc_url)
    
    # _get_rpc_url 方法已移除，使用全局配置函数 get_private_rpc_url() 和 get_public_rpc_url()
        
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
            # 使用Raydium API v3的官方端点（基于官方文档）
            url = f"{self.raydium_api_base}/pools/info/list-v2"
            params = {
                "size": 100,
                "sortField": "liquidity", 
                "sortType": "desc"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # API v3返回的数据结构不同，需要适配
                        if 'data' in data:
                            return {
                                'official': data['data'],
                                'unOfficial': []
                            }
                        else:
                            return {
                                'official': [],
                                'unOfficial': []
                            }
                    else:
                        # 如果API v3失败，尝试旧的API端点作为备用
                        print(f"⚠️ Raydium API v3暂时不可用: {resp.status}")
                        fallback_url = "https://api.raydium.io/v2/sdk/liquidity/mainnet"
                        async with session.get(fallback_url, timeout=10) as fallback_resp:
                            if fallback_resp.status == 200:
                                fallback_data = await fallback_resp.json()
                                return fallback_data
                            else:
                                print(f"⚠️ Raydium API备用端点也失败: {fallback_resp.status}")
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
    
    async def get_swap_quote(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        slippage_bps: int = 50,
        tx_version: str = "V0"
    ) -> Dict[str, Any]:
        """获取交易报价
        
        Args:
            input_mint: 输入代币mint地址
            output_mint: 输出代币mint地址
            amount: 输入金额（基础单位）
            slippage_bps: 滑点容忍度（basis points，50 = 0.5%）
            tx_version: 交易版本（V0 或 LEGACY）
            
        Returns:
            交易报价信息
        """
        try:
            url = f"https://transaction-v1.raydium.io/compute/swap-base-in"
            params = {
                'inputMint': input_mint,
                'outputMint': output_mint,
                'amount': str(amount),
                'slippageBps': slippage_bps,
                'txVersion': tx_version
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get('success'):
                            return data
                        else:
                            raise TradingError(f"获取报价失败: {data}")
                    else:
                        raise TradingError(f"API请求失败: {resp.status}")
                        
        except Exception as e:
            raise TradingError(f"获取交易报价失败: {e}")
    
    async def build_swap_transaction(
        self,
        swap_response: Dict[str, Any],
        wallet_address: str,
        tx_version: str = "V0",
        wrap_sol: bool = False,
        unwrap_sol: bool = False,
        input_account: Optional[str] = None,
        output_account: Optional[str] = None,
        compute_unit_price_micro_lamports: Optional[str] = None
    ) -> Dict[str, Any]:
        """构建交易
        
        Args:
            swap_response: 报价响应
            wallet_address: 钱包地址
            tx_version: 交易版本
            wrap_sol: 是否包装SOL
            unwrap_sol: 是否解包SOL
            input_account: 输入代币账户（SOL为None）
            output_account: 输出代币账户（SOL为None）
            compute_unit_price_micro_lamports: 优先级费用（微lamports）
            
        Returns:
            交易构建结果
        """
        try:
            url = f"https://transaction-v1.raydium.io/transaction/swap-base-in"
            
            payload = {
                'swapResponse': swap_response,
                'wallet': wallet_address,
                'txVersion': tx_version,
                'wrapSol': wrap_sol,
                'unwrapSol': unwrap_sol
            }
            
            if input_account:
                payload['inputAccount'] = input_account
            if output_account:
                payload['outputAccount'] = output_account
            if compute_unit_price_micro_lamports:
                payload['computeUnitPriceMicroLamports'] = compute_unit_price_micro_lamports
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get('success'):
                            return data
                        else:
                            raise TradingError(f"构建交易失败: {data}")
                    else:
                        raise TradingError(f"API请求失败: {resp.status}")
                        
        except Exception as e:
            raise TradingError(f"构建交易失败: {e}")
    
    async def swap_tokens(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        wallet: Wallet,
        slippage_bps: int = 50,
        tx_version: str = "V0",
        priority_fee_micro_lamports: Optional[int] = None,
        jito_tip: Optional[int] = None
    ) -> Dict[str, Any]:
        """执行代币交换
        
        Args:
            input_mint: 输入代币mint地址
            output_mint: 输出代币mint地址
            amount: 输入金额
            wallet: 钱包对象
            slippage_bps: 滑点容忍度
            tx_version: 交易版本
            priority_fee_micro_lamports: 优先级费用（微lamports）
            jito_tip: Jito小费（lamports）
            
        Returns:
            交易结果
        """
        try:
            # 获取交易报价
            quote = await self.get_swap_quote(input_mint, output_mint, amount, slippage_bps, tx_version)
            
            # 构建交易
            transaction_data = await self.build_swap_transaction(
                quote['data'],
                str(wallet.pubkey),
                tx_version,
                compute_unit_price_micro_lamports=str(priority_fee_micro_lamports) if priority_fee_micro_lamports else None
            )
            
            # 发送交易
            if transaction_data.get('data') and len(transaction_data['data']) > 0:
                # 解码交易
                transaction_bytes = base64.b64decode(transaction_data['data'][0]['transaction'])
                
                # 创建交易对象
                transaction = VersionedTransaction.from_bytes(transaction_bytes)
                
                # 添加Jito小费（如果提供）
                if jito_tip:
                    transaction = self.mev_protection.add_jito_tip(transaction, jito_tip)
                
                # 发送交易（跳过预检以加快速度）
                response = await self.client.send_transaction(transaction, skip_preflight=True)
                
                if response.value:
                    tx_signature = str(response.value)
                    
                    # 等待确认
                    confirmed = await self.wait_for_confirmation(tx_signature)
                    
                    return {
                        'transaction_signature': tx_signature,
                        'confirmed': confirmed,
                        'input_amount': amount,
                        'output_amount': quote['data'].get('outputAmount', 0),
                        'price_impact': quote['data'].get('priceImpactPct', 0),
                        'slippage_bps': slippage_bps,
                        'priority_fee': priority_fee_micro_lamports,
                        'jito_tip': jito_tip,
                        'status': 'success' if confirmed else 'pending'
                    }
                else:
                    raise TradingError("交易发送失败")
            else:
                raise TradingError("交易构建失败")
                
        except Exception as e:
            raise TradingError(f"代币交换失败: {e}")
    
    async def buy_token(
        self,
        token_mint: str,
        sol_amount: int,
        wallet: Wallet,
        slippage_bps: int = 50,
        priority_fee_micro_lamports: Optional[int] = None,
        jito_tip: Optional[int] = None
    ) -> Dict[str, Any]:
        """购买代币（用SOL购买）
        
        Args:
            token_mint: 目标代币mint地址
            sol_amount: SOL数量（lamports）
            wallet: 钱包对象
            slippage_bps: 滑点容忍度
            priority_fee_micro_lamports: 优先级费用（微lamports）
            jito_tip: Jito小费（lamports）
            
        Returns:
            购买结果
        """
        # SOL的mint地址
        sol_mint = "So11111111111111111111111111111111111111112"
        
        return await self.swap_tokens(
            input_mint=sol_mint,
            output_mint=token_mint,
            amount=sol_amount,
            wallet=wallet,
            slippage_bps=slippage_bps,
            tx_version="V0",
            priority_fee_micro_lamports=priority_fee_micro_lamports,
            jito_tip=jito_tip
        )
    
    async def sell_token(
        self,
        token_mint: str,
        token_amount: int,
        wallet: Wallet,
        slippage_bps: int = 50,
        priority_fee_micro_lamports: Optional[int] = None,
        jito_tip: Optional[int] = None
    ) -> Dict[str, Any]:
        """出售代币（换成SOL）
        
        Args:
            token_mint: 代币mint地址
            token_amount: 代币数量
            wallet: 钱包对象
            slippage_bps: 滑点容忍度
            priority_fee_micro_lamports: 优先级费用（微lamports）
            jito_tip: Jito小费（lamports）
            
        Returns:
            出售结果
        """
        # SOL的mint地址
        sol_mint = "So11111111111111111111111111111111111111112"
        
        return await self.swap_tokens(
            input_mint=token_mint,
            output_mint=sol_mint,
            amount=token_amount,
            wallet=wallet,
            slippage_bps=slippage_bps,
            tx_version="V0",
            priority_fee_micro_lamports=priority_fee_micro_lamports,
            jito_tip=jito_tip
        )
    
    async def execute_trade_with_mev_protection(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        wallet: Wallet,
        slippage_bps: int = 50,
        priority_level: str = "medium",
        jito_tip: Optional[int] = None,
        max_attempts: int = 3
    ) -> Dict[str, Any]:
        """执行交易并包含MEV防护功能
        
        Args:
            input_mint: 输入代币mint地址
            output_mint: 输出代币mint地址
            amount: 输入金额
            wallet: 钱包对象
            slippage_bps: 滑点容忍度
            priority_level: 优先级级别（low, medium, high, very_high）
            jito_tip: Jito小费金额
            max_attempts: 最大尝试次数
            
        Returns:
            交易结果
        """
        return await self.mev_protection.execute_with_mev_protection(
            self.swap_tokens,
            input_mint,
            output_mint,
            amount,
            wallet,
            slippage_bps=slippage_bps,
            priority_level=priority_level,
            jito_tip=jito_tip,
            max_attempts=max_attempts
        )


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
        
        # 测试交易报价（示例）
        sol_mint = "So11111111111111111111111111111111111111112"
        usdc_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        
        try:
            quote = await client.get_swap_quote(
                input_mint=sol_mint,
                output_mint=usdc_mint,
                amount=100000000,  # 0.1 SOL
                slippage_bps=50
            )
            print("交易报价:", json.dumps(quote, indent=2))
        except Exception as e:
            print(f"获取报价失败（正常，因为需要真实代币）: {e}")
        
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(example_usage())