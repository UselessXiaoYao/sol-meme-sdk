"""
简单交易接口类
提供简洁的买卖接口，隐藏复杂的实现细节
"""

import asyncio
import logging
from typing import Optional, Dict, Any

from sol_meme_sdk.wallet import Wallet
from sol_meme_sdk.trading_engine import TradingEngine
from sol_meme_sdk.models import TransactionConfig, OrderSide

logger = logging.getLogger(__name__)
# 设置日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class SimpleTrader:
    """简单交易接口类
    
    功能：
    - 钱包初始化
    - 简单买入接口（SOL -> Token）
    - 简单卖出接口（Token -> SOL）
    - 返回买入的token数量，便于后续卖出
    """
    
    def __init__(self, wallet_file: str = None, private_key: str = None, network: str = "mainnet-beta"):
        """
        初始化交易器
        
        Args:
            wallet_file: 钱包JSON文件路径（可选）
            private_key: 钱包私钥（可选）
            network: 网络类型，默认主网
        """
        # 钱包初始化
        if wallet_file:
            self.wallet = Wallet.from_json_file(wallet_file)
        elif private_key:
            self.wallet = Wallet(private_key=private_key)
        else:
            # 创建新钱包
            self.wallet = Wallet()
            print(f"✅ 创建新钱包: {self.wallet.address}")
        
        print(f"💰 钱包地址: {self.wallet.address}")
        
        # 交易配置
        self.config = TransactionConfig(
            enable_devnet_testing=(network != "mainnet-beta"),
            dex_priority=["jupiter", "raydium"],
            jupiter_slippage_bps=100,  # 1%滑点
            raydium_slippage_bps=100
        )
        
        # 交易引擎
        self.trading_engine = TradingEngine(self.wallet, self.config)
        
        # 网络类型
        self.network = network
        
        print(f"🎯 交易器初始化完成 - 网络: {network}")
    
    async def connect(self) -> bool:
        """连接到网络"""
        try:
            # 测试连接
            rpc_url = self.trading_engine._get_rpc_url()
            print(f"🔗 连接到: {rpc_url}")
            
            # 查询余额验证连接
            sol_balance = await self.trading_engine._get_sol_balance()
            print(f"💰 SOL余额: {sol_balance:.6f} SOL")
            
            return True
            
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            return False
    
    async def buy(self, token_address: str, sol_amount: float, slippage: float = 10.0) -> float:
        """
        买入代币（SOL -> Token）
        
        Args:
            token_address: 代币地址
            sol_amount: 使用的SOL数量
            
        Returns:
            float: 成功买入的token数量
        """
        try:
            print(f"🛒 买入代币 - 使用 {sol_amount:.6f} SOL")
            
            # 检查SOL余额
            current_balance = await self.trading_engine._get_sol_balance()
            if current_balance < sol_amount:
                raise Exception(f"SOL余额不足: {current_balance:.6f} < {sol_amount:.6f}")
            
            # 执行买入
            result = await self.trading_engine.buy_token(
                token_address=token_address,
                amount_sol=sol_amount,
                slippage=slippage
            )
            
            print(f"✅ 买入成功!")
            print(f"   📦 获得代币: {result.executed_amount:.6f}")
            print(f"   💰 平均价格: {result.executed_price:.8f} SOL")
            print(f"   🔗 交易哈希: {result.transaction_hash}")
            
            return result.executed_amount
            
        except Exception as e:
            print(f"❌ 买入失败: {e}")
            raise
    
    async def sell(self, token_address: str, token_amount: float, slippage: float = 10.0) -> float:
        """
        卖出代币（Token -> SOL）
        
        Args:
            token_address: 代币地址
            token_amount: 卖出的token数量
            
        Returns:
            float: 成功获得的SOL数量
        """
        try:
            print(f"💰 卖出代币 - 卖出 {token_amount:.6f} 个")

            # # 检查代币余额(可选，实际交易引擎会自动检查并失败, 且影响速度)
            # current_balance = await self.trading_engine._get_token_balance(token_address)
            # if current_balance < token_amount:
            #     raise Exception(f"代币余额不足: {current_balance:.6f} < {token_amount:.6f}")
            
            # 执行卖出
            result = await self.trading_engine.sell_token(
                token_address=token_address,
                amount_tokens=token_amount,
                slippage=slippage
            )
            
            print(f"✅ 卖出成功!")
            print(f"   💰 获得SOL: {result.executed_amount:.6f} SOL")
            print(f"   📊 平均价格: {result.executed_price:.8f} SOL")
            print(f"   🔗 交易哈希: {result.transaction_hash}")
            
            return result.executed_amount
            
        except Exception as e:
            print(f"❌ 卖出失败: {e}")
            raise
    
    async def get_balance(self, token_address: str = None) -> Dict[str, float]:
        """
        获取余额信息
        
        Args:
            token_address: 代币地址（可选）
            
        Returns:
            Dict: 包含SOL余额和代币余额
        """
        try:
            sol_balance = await self.trading_engine._get_sol_balance()
            result = {"sol": sol_balance}
            
            if token_address:
                token_balance = await self.trading_engine._get_token_balance(token_address)
                result["token"] = token_balance
            
            return result
            
        except Exception as e:
            print(f"❌ 查询余额失败: {e}")
            raise
    
    async def get_price(self, token_address: str) -> float:
        """
        获取代币价格
        
        Args:
            token_address: 代币地址
            
        Returns:
            float: 代币价格（SOL计价）
        """
        try:
            price = await self.trading_engine.get_token_price(token_address)
            return price
            
        except Exception as e:
            print(f"❌ 查询价格失败: {e}")
            raise


# 使用示例
async def example_usage():
    """使用示例"""
    
    # 1. 初始化交易器（使用现有钱包或创建新钱包）
    trader = SimpleTrader(
        wallet_file="new_wallet.json",  # 可选：使用现有钱包
        # private_key="your_private_key",   # 可选：使用私钥
        network="mainnet-beta"
    )
    
    # 2. 连接到网络
    connected = await trader.connect()
    if not connected:
        print("❌ 连接失败")
        return
    
    # 3. 查询余额
    balance = await trader.get_balance()
    print(f"💰 当前余额: {balance['sol']:.6f} SOL")
    
    # 4. 定义代币地址
    token_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC示例
    
    # 5. 查询价格
    price = await trader.get_price(token_address)
    print(f"📊 代币价格: {price:.8f} SOL")
    
    # 6. 买入代币（使用0.01 SOL）
    try:
        token_amount = await trader.buy(token_address, 0.01)
        print(f"✅ 成功买入: {token_amount:.6f} 个代币")
        
        # 7. 卖出代币（卖出刚才买入的全部）
        sol_amount = await trader.sell(token_address, token_amount)
        print(f"✅ 成功卖出: {sol_amount:.6f} SOL")
        
    except Exception as e:
        print(f"❌ 交易失败: {e}")


    # 7. 最后再查询余额
    balance = await trader.get_balance()
    print(f"💰 当前余额: {balance['sol']:.6f} SOL")

if __name__ == "__main__":
    # 运行示例
    asyncio.run(example_usage())