#!/usr/bin/env python3
"""
统一配置管理模块 - 简化版本，直接使用环境变量
"""

import os
from typing import Optional, Dict, Any


class UnifiedConfig:
    """统一配置管理类"""
    
    def __init__(self, env_file: str = None):
        # 加载环境文件 - 优先使用提供的文件，否则自动查找项目根目录的.env文件
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        if env_file and os.path.exists(env_file):
            from dotenv import load_dotenv
            load_dotenv(env_file)
        else:
            # 自动查找项目根目录的.env文件
            env_path = os.path.join(project_root, ".env")
            if os.path.exists(env_path):
                from dotenv import load_dotenv
                load_dotenv(env_path)
        
        # Solana网络配置
        self.solana_network = os.getenv("SOLANA_NETWORK", "mainnet-beta")
        
        # 直接使用配置文件中的RPC端点，无需复杂逻辑
        self.solana_private_rpc_endpoint = os.getenv(
            "SOLANA_PRIVATE_RPC_ENDPOINT", 
            "https://api.mainnet-beta.solana.com"
        )
        self.solana_public_rpc_endpoint = os.getenv(
            "SOLANA_PUBLIC_RPC_ENDPOINT", 
            "https://api.mainnet-beta.solana.com"
        )
        
        # Devnet专用配置
        self.devnet_enabled = os.getenv("DEVNET_ENABLED", "false").lower() == "true"
        self.devnet_usdc_mint = os.getenv("DEVNET_USDC_MINT", "4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU")
        self.devnet_wrapped_sol = os.getenv("DEVNET_WRAPPED_SOL", "So11111111111111111111111111111111111111112")
        self.devnet_supported_dex = os.getenv("DEVNET_SUPPORTED_DEX", "RAYDIUM,METEORA").split(",")
        
        # API密钥配置
        self.jupiter_api_key = os.getenv("JUPITER_API_KEY", "")
        
        # DEX API端点配置
        self.pumpfun_api_base = os.getenv("PUMPFUN_API_BASE", "https://frontend-api-v3.pump.fun")
        self.pumpfun_coins_endpoint = os.getenv("PUMPFUN_COINS_ENDPOINT", "/coins")
        
        self.meteora_api_base = os.getenv("METEORA_API_BASE", "https://damm-v2.datapi.meteora.ag")
        self.meteora_pools_endpoint = os.getenv("METEORA_POOLS_ENDPOINT", "/pools")
        
        self.raydium_api_base = os.getenv("RAYDIUM_API_BASE", "https://api-v3.raydium.io")
        self.raydium_pairs_endpoint = os.getenv("RAYDIUM_PAIRS_ENDPOINT", "/pools/info/list-v2")
        
        self.gmgn_api_base = os.getenv("GMGN_API_BASE", "https://gmgn.ai")
        
        # 监控配置
        self.monitor_interval = int(os.getenv("MONITOR_INTERVAL", "30"))
        self.max_concurrent_requests = int(os.getenv("MAX_CONCURRENT_REQUESTS", "10"))
        
        # 交易配置
        self.slippage_tolerance = float(os.getenv("SLIPPAGE_TOLERANCE", "0.01"))
        self.max_position_size = float(os.getenv("MAX_POSITION_SIZE", "0.1"))
        
        # 程序ID配置
        self.pumpfun_program_id = os.getenv("PUMPFUN_PROGRAM_ID", "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P")
        self.pumpfun_amm_program_id = os.getenv("PUMPFUN_AMM_PROGRAM_ID", "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA")
        self.pumpfun_fees_program_id = os.getenv("PUMPFUN_FEES_PROGRAM_ID", "pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ")
        self.meteora_program_id = os.getenv("METEORA_PROGRAM_ID", "cpamdpZCGKUy5JxQXB4dcpGPiikHawvSWAd6mEn1sGG")
        self.raydium_program_id = os.getenv("RAYDIUM_PROGRAM_ID", "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8")
        
        # 验证配置
        self._validate_config()
    
    def get_public_rpc_url(self) -> str:
        """获取公共RPC URL - 直接从配置文件读取"""
        return self.solana_public_rpc_endpoint
    
    def get_private_rpc_url(self) -> str:
        """获取私有RPC URL - 直接从配置文件读取"""
        return self.solana_private_rpc_endpoint
    
    def is_private_rpc(self) -> bool:
        """检查是否使用私有RPC - 简单比较两个RPC是否不同"""
        return self.solana_private_rpc_endpoint != self.solana_public_rpc_endpoint
    
    def _validate_config(self):
        """验证配置设置"""
        if not self.jupiter_api_key:
            print("⚠️  Warning: JUPITER_API_KEY not found in environment variables")
            print("   Get a free API key at: https://portal.jup.ag/")
        
        # Devnet环境验证
        if self.solana_network == "devnet":
            print("🔧 Devnet环境配置:")
            print(f"   USDC代币地址: {self.devnet_usdc_mint}")
            print(f"   支持的DEX: {', '.join(self.devnet_supported_dex)}")
            print("   ⚠️  Jupiter API在devnet上功能受限，建议使用Raydium或Meteora")
    
    def get_jupiter_api_key(self) -> str:
        """获取Jupiter API密钥（带验证）"""
        if not self.jupiter_api_key:
            raise ValueError(
                "Jupiter API key is required. "
                "Set JUPITER_API_KEY in .env file or get a free key at https://portal.jup.ag/"
            )
        return self.jupiter_api_key
    
    def get_solana_config(self) -> Dict[str, Any]:
        """获取Solana网络配置"""
        return {
            "network": self.solana_network,
            "private_rpc_endpoint": self.solana_private_rpc_endpoint,
            "public_rpc_endpoint": self.solana_public_rpc_endpoint
        }
    
    def get_devnet_config(self) -> Dict[str, Any]:
        """获取devnet专用配置"""
        return {
            "enabled": self.devnet_enabled,
            "usdc_mint": self.devnet_usdc_mint,
            "wrapped_sol": self.devnet_wrapped_sol,
            "supported_dex": self.devnet_supported_dex,
            "jupiter_limited": True  # Jupiter API在devnet上功能受限
        }
    
    def is_devnet(self) -> bool:
        """检查是否devnet环境"""
        return self.solana_network == "devnet"
    
    def get_token_mint_address(self, symbol: str) -> str:
        """根据网络获取代币mint地址"""
        if self.is_devnet():
            # Devnet专用代币地址
            devnet_tokens = {
                "USDC": self.devnet_usdc_mint,
                "SOL": self.devnet_wrapped_sol
            }
            return devnet_tokens.get(symbol.upper(), symbol)
        else:
            # Mainnet代币地址
            mainnet_tokens = {
                "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                "SOL": "So11111111111111111111111111111111111111112"
            }
            return mainnet_tokens.get(symbol.upper(), symbol)
    
    def get_pumpfun_api_url(self) -> str:
        """获取完整的Pump.Fun API URL"""
        return f"{self.pumpfun_api_base.rstrip('/')}/{self.pumpfun_coins_endpoint.lstrip('/')}"
    
    def get_meteora_api_url(self, endpoint: str = "") -> str:
        """获取完整的Meteora API URL"""
        base_url = f"{self.meteora_api_base.rstrip('/')}/{self.meteora_pools_endpoint.lstrip('/')}"
        if endpoint:
            return f"{base_url}/{endpoint.lstrip('/')}"
        return base_url
    
    def get_raydium_api_url(self, endpoint: str = "") -> str:
        """获取完整的Raydium API URL"""
        base_url = f"{self.raydium_api_base.rstrip('/')}/{self.raydium_pairs_endpoint.lstrip('/')}"
        if endpoint:
            return f"{base_url}/{endpoint.lstrip('/')}"
        return base_url
    
    def get_gmgn_api_url(self, endpoint: str = "") -> str:
        """获取完整的GMGN API URL"""
        if endpoint:
            return f"{self.gmgn_api_base.rstrip('/')}/{endpoint.lstrip('/')}"
        return self.gmgn_api_base
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            # 网络配置
            'solana_network': self.solana_network,
            'solana_private_rpc_endpoint': self.solana_private_rpc_endpoint,
            'solana_public_rpc_endpoint': self.solana_public_rpc_endpoint,
            
            # API基础URL
            'pumpfun_api_base': self.pumpfun_api_base,
            'meteora_api_base': self.meteora_api_base,
            'raydium_api_base': self.raydium_api_base,
            'gmgn_api_base': self.gmgn_api_base,
            
            # 完整API URL
            'pumpfun_api_url': self.get_pumpfun_api_url(),
            'meteora_api_url': self.get_meteora_api_url(),
            'raydium_api_url': self.get_raydium_api_url(),
            
            # 监控配置
            'monitor_interval': self.monitor_interval,
            'max_concurrent_requests': self.max_concurrent_requests,
            
            # 交易配置
            'slippage_tolerance': self.slippage_tolerance,
            'max_position_size': self.max_position_size,
            
            # 程序ID
            'pumpfun_program_id': self.pumpfun_program_id,
            'pumpfun_amm_program_id': self.pumpfun_amm_program_id,
            'pumpfun_fees_program_id': self.pumpfun_fees_program_id,
            'meteora_program_id': self.meteora_program_id,
            'raydium_program_id': self.raydium_program_id
        }


# 全局配置实例
_config: Optional[UnifiedConfig] = None


def get_config() -> UnifiedConfig:
    """获取全局配置实例"""
    global _config
    if _config is None:
        _config = UnifiedConfig()
    return _config


def set_jupiter_api_key(api_key: str) -> None:
    """设置Jupiter API密钥"""
    _config.jupiter_api_key = api_key


def set_solana_network(network: str) -> None:
    """设置Solana网络"""
    _config.solana_network = network
    # 重新验证以更新RPC端点
    _config._validate_config()


def reload_config() -> UnifiedConfig:
    """重新加载配置"""
    global _config
    # 直接重新加载配置，自动查找项目根目录的.env文件
    _config = UnifiedConfig()
    return _config


def print_config():
    """打印当前配置"""
    config = get_config()
    config_dict = config.to_dict()
    
    print("🔧 当前配置:")
    print("=" * 50)
    
    for key, value in config_dict.items():
        if 'key' in key.lower() and value:
            # 隐藏API密钥的中间部分
            masked_value = value[:8] + "*" * 8 + value[-8:]
            print(f"{key}: {masked_value}")
        else:
            print(f"{key}: {value}")
    
    print("=" * 50)


def get_public_rpc_url() -> str:
    """获取公共RPC URL"""
    return get_config().get_public_rpc_url()


def get_private_rpc_url() -> str:
    """获取私有RPC URL"""
    return get_config().get_private_rpc_url()


def is_private_rpc() -> bool:
    """检查当前是否使用私有RPC"""
    return get_config().is_private_rpc()