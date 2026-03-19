#!/usr/bin/env python3
"""
API配置管理模块 - 从环境变量读取所有API端点和配置
"""

import os
from typing import Optional


class APIConfig:
    """API配置管理类"""
    
    def __init__(self):
        # Solana网络配置
        self.solana_network = os.getenv("SOLANA_NETWORK", "mainnet-beta")
        self.solana_rpc_endpoint = os.getenv(
            "SOLANA_RPC_ENDPOINT", 
            "https://api.mainnet-beta.solana.com"
        )
        
        # Jupiter API配置
        self.jupiter_api_key = os.getenv("JUPITER_API_KEY", "")
        
        # Pump.Fun API配置
        self.pumpfun_api_base = os.getenv("PUMPFUN_API_BASE", "https://frontend-api-v3.pump.fun")
        self.pumpfun_coins_endpoint = os.getenv("PUMPFUN_COINS_ENDPOINT", "/coins")
        
        # Meteora API配置
        self.meteora_api_base = os.getenv("METEORA_API_BASE", "https://damm-v2.datapi.meteora.ag")
        self.meteora_pools_endpoint = os.getenv("METEORA_POOLS_ENDPOINT", "/pools")
        
        # Raydium API配置
        self.raydium_api_base = os.getenv("RAYDIUM_API_BASE", "https://api.raydium.io")
        self.raydium_pairs_endpoint = os.getenv("RAYDIUM_PAIRS_ENDPOINT", "/v2/main/pairs")
        
        # GMGN API配置
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
        self.raydium_program_id = os.getenv("RAYDIUM_PROGRAM_ID", "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA")
    
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
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            # 网络配置
            'solana_network': self.solana_network,
            'solana_rpc_endpoint': self.solana_rpc_endpoint,
            
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
_api_config: Optional[APIConfig] = None


def get_api_config() -> APIConfig:
    """获取全局API配置实例"""
    global _api_config
    if _api_config is None:
        _api_config = APIConfig()
    return _api_config


def reload_api_config() -> APIConfig:
    """重新加载API配置"""
    global _api_config
    _api_config = APIConfig()
    return _api_config


def print_api_config():
    """打印当前API配置"""
    config = get_api_config()
    config_dict = config.to_dict()
    
    print("🔧 当前API配置:")
    print("=" * 50)
    
    for key, value in config_dict.items():
        if 'key' in key.lower() and value:
            # 隐藏API密钥的中间部分
            masked_value = value[:8] + "*" * 8 + value[-8:]
            print(f"{key}: {masked_value}")
        else:
            print(f"{key}: {value}")
    
    print("=" * 50)