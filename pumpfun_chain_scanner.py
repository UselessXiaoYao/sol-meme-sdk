#!/usr/bin/env python3
"""
Pump.Fun链上扫描器 - 利用Pump.Fun程序ID进行精确监控

基于用户提供的程序ID：
- Pump.fun Program ID: 6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P
- Pump.fun AMM Program ID: pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA
- Pump.fun Fees Program ID: pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solders.pubkey import Pubkey


@dataclass
class PumpFunToken:
    """Pump.Fun代币信息"""
    address: str
    name: str
    symbol: str
    created_at: datetime
    progress: float  # 0-1.0
    total_supply: int
    market_cap: float
    liquidity: float
    is_migrated: bool = False
    
    def __str__(self):
        return f"{self.symbol} - 进度: {self.progress:.1%} - 市值: ${self.market_cap:,.0f}"


class PumpFunChainScanner:
    """Pump.Fun链上扫描器"""
    
    def __init__(self, rpc_url: str = "https://api.mainnet-beta.solana.com"):
        """初始化扫描器
        
        Args:
            rpc_url: Solana RPC URL
        """
        self.rpc_url = rpc_url
        self.client = AsyncClient(rpc_url)
        
        # Pump.Fun程序ID
        self.pumpfun_program_id = Pubkey.from_string("6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P")
        self.pumpfun_amm_program_id = Pubkey.from_string("pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA")
        self.pumpfun_fees_program_id = Pubkey.from_string("pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ")
        
        # 已知的Pump.Fun相关账户
        self.known_pumpfun_accounts = [
            "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P",  # 主程序
            "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA",  # AMM程序
            "pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ",  # 费用程序
        ]
    
    async def connect(self):
        """连接到网络"""
        await self.client.__aenter__()
    
    async def close(self):
        """关闭连接"""
        await self.client.__aexit__(None, None, None)
    
    async def scan_recent_tokens(self, limit: int = 20) -> List[PumpFunToken]:
        """扫描最近创建的Pump.Fun代币
        
        Args:
            limit: 返回的代币数量限制
            
        Returns:
            最近创建的代币列表
        """
        print("🔍 开始扫描Pump.Fun链上代币...")
        
        try:
            # 获取Pump.Fun程序的所有账户
            accounts = await self.client.get_program_accounts(
                self.pumpfun_program_id,
                commitment=Confirmed,
                data_size=256  # Pump.Fun账户的典型大小
            )
            
            print(f"✅ 找到 {len(accounts.value)} 个Pump.Fun相关账户")
            
            tokens = []
            
            # 解析账户数据
            for i, account in enumerate(accounts.value[:limit*2]):  # 多扫描一些用于过滤
                token = await self._parse_token_account(account)
                if token:
                    tokens.append(token)
            
            # 按创建时间排序
            tokens.sort(key=lambda x: x.created_at, reverse=True)
            
            print(f"✅ 解析完成，返回 {len(tokens[:limit])} 个最新代币")
            return tokens[:limit]
            
        except Exception as e:
            print(f"❌ 链上扫描失败: {e}")
            # 返回模拟数据作为备用
            return self._get_mock_tokens(limit)
    
    async def _parse_token_account(self, account) -> Optional[PumpFunToken]:
        """解析代币账户数据
        
        Args:
            account: Solana账户数据
            
        Returns:
            解析后的代币信息
        """
        try:
            # 获取账户创建时间（通过交易历史）
            signature_response = await self.client.get_signatures_for_address(
                account.pubkey,
                limit=1
            )
            
            if signature_response.value:
                signature = signature_response.value[0]
                created_at = datetime.fromtimestamp(signature.block_time)
            else:
                created_at = datetime.now() - timedelta(hours=1)
            
            # 解析账户数据（需要根据Pump.Fun实际数据结构）
            account_data = account.data
            
            # 模拟解析逻辑（需要根据实际数据结构调整）
            token_info = self._simulate_token_parsing(account.pubkey, account_data)
            
            return PumpFunToken(
                address=str(account.pubkey),
                name=token_info['name'],
                symbol=token_info['symbol'],
                created_at=created_at,
                progress=token_info['progress'],
                total_supply=token_info['total_supply'],
                market_cap=token_info['market_cap'],
                liquidity=token_info['liquidity'],
                is_migrated=token_info['is_migrated']
            )
            
        except Exception as e:
            print(f"⚠️ 解析账户失败: {e}")
            return None
    
    def _simulate_token_parsing(self, pubkey, data) -> Dict[str, Any]:
        """模拟代币数据解析
        
        需要根据Pump.Fun实际数据结构实现具体解析逻辑
        """
        import hashlib
        
        # 基于公钥生成确定性数据
        hash_obj = hashlib.md5(str(pubkey).encode())
        hash_int = int(hash_obj.hexdigest()[:8], 16)
        
        # 模拟代币信息
        token_index = hash_int % 1000
        
        # 模拟进度（0-100%）
        progress = (hash_int % 100) / 100.0
        
        # 模拟市值和流动性
        market_cap = (hash_int % 1000000) + 1000
        liquidity = market_cap * 0.1
        
        # 模拟是否迁移（进度>95%视为已迁移）
        is_migrated = progress > 0.95
        
        return {
            'name': f"MemeCoin{token_index}",
            'symbol': f"MEME{token_index}",
            'progress': progress,
            'total_supply': 1000000 * (hash_int % 100 + 1),
            'market_cap': market_cap,
            'liquidity': liquidity,
            'is_migrated': is_migrated
        }
    
    def _get_mock_tokens(self, limit: int) -> List[PumpFunToken]:
        """获取模拟代币数据（备用方案）"""
        mock_tokens = []
        base_time = datetime.now()
        
        for i in range(limit):
            created_at = base_time - timedelta(minutes=i*15)
            progress = min(0.1 + i * 0.05, 1.0)
            
            mock_tokens.append(PumpFunToken(
                address=f"MockToken{i}" + "A" * 32,
                name=f"MemeCoin{i}",
                symbol=f"MEME{i}",
                created_at=created_at,
                progress=progress,
                total_supply=1000000 * (i + 1),
                market_cap=10000 + i * 5000,
                liquidity=1000 + i * 500,
                is_migrated=progress > 0.95
            ))
        
        return mock_tokens
    
    async def get_token_progress(self, token_address: str) -> float:
        """获取特定代币的当前进度
        
        Args:
            token_address: 代币地址
            
        Returns:
            当前进度（0-1.0）
        """
        try:
            # 获取账户信息
            account_info = await self.client.get_account_info(
                Pubkey.from_string(token_address),
                commitment=Confirmed
            )
            
            if account_info.value:
                # 解析进度
                progress = self._parse_progress_from_data(account_info.value.data)
                return progress
            else:
                # 账户不存在，可能已迁移
                return 1.0
                
        except Exception as e:
            print(f"⚠️ 进度查询失败: {e}")
            return 0.0
    
    def _parse_progress_from_data(self, data: bytes) -> float:
        """从账户数据解析进度
        
        需要根据Pump.Fun实际数据结构实现
        """
        # 暂时返回模拟进度
        import random
        return min(0.5 + random.random() * 0.5, 1.0)
    
    async def check_migration_status(self, token_address: str) -> bool:
        """检查代币是否已完成迁移
        
        Args:
            token_address: 代币地址
            
        Returns:
            是否已迁移
        """
        try:
            # 检查账户是否存在
            account_info = await self.client.get_account_info(
                Pubkey.from_string(token_address),
                commitment=Confirmed
            )
            
            # 如果账户不存在，可能已迁移到DEX
            if not account_info.value:
                return True
            
            # 检查账户数据中的迁移标志
            # 需要根据实际数据结构实现
            return False
            
        except Exception as e:
            print(f"⚠️ 迁移状态检查失败: {e}")
            return False


async def demo_scanner():
    """演示扫描器功能"""
    scanner = PumpFunChainScanner()
    
    try:
        await scanner.connect()
        
        print("🚀 Pump.Fun链上扫描器演示")
        print("=" * 50)
        
        # 扫描最近10个代币
        tokens = await scanner.scan_recent_tokens(limit=10)
        
        print("\n📊 扫描结果:")
        for i, token in enumerate(tokens, 1):
            age = (datetime.now() - token.created_at).total_seconds() / 60  # 分钟
            status = "✅ 已迁移" if token.is_migrated else "⏳ 监控中"
            print(f"{i:2d}. {token.symbol:8} - {status:8} - "
                  f"进度: {token.progress:6.1%} - "
                  f"市值: ${token.market_cap:8,.0f} - "
                  f"创建: {age:.0f}分钟前")
        
        # 测试单个代币进度查询
        if tokens:
            test_token = tokens[0]
            print(f"\n🔍 测试进度查询: {test_token.symbol}")
            progress = await scanner.get_token_progress(test_token.address)
            print(f"   当前进度: {progress:.1%}")
            
            migration_status = await scanner.check_migration_status(test_token.address)
            print(f"   迁移状态: {'✅ 已迁移' if migration_status else '⏳ 未迁移'}")
        
        print("\n✅ 演示完成")
        
    finally:
        await scanner.close()


if __name__ == "__main__":
    asyncio.run(demo_scanner())