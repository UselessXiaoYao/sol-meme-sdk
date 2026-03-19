#!/usr/bin/env python3
"""
GMGN代币信息读取器 - 直接从GMGN获取代币信息
"""

import asyncio
import aiohttp
import json
import re
from typing import Dict, Any, Optional
from urllib.parse import urlparse

class GMGNTokenReader:
    """GMGN代币信息读取器"""
    
    def __init__(self):
        self.base_url = "https://gmgn.ai"
        self.api_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://gmgn.ai/"
        }
        
        # GMGN池类型映射
        self.pool_types = {
            "Pump AMM池信息": "PUMP_AMM",
            "Dynamic BC 池信息": "DYNAMIC_BC", 
            "METEORA_DAMM_V2 池信息": "METEORA_DAMM_V2",
            "Raydium AMM池信息": "RAYDIUM_AMM"
        }
    
    async def extract_token_address_from_url(self, url: str) -> Optional[str]:
        """从GMGN URL中提取代币地址"""
        try:
            # 解析URL路径
            parsed = urlparse(url)
            path_parts = parsed.path.strip('/').split('/')
            
            # GMGN URL格式: /sol/token/{token_address}
            if len(path_parts) >= 3 and path_parts[0] == 'sol' and path_parts[1] == 'token':
                return path_parts[2]
            
            return None
        except Exception as e:
            print(f"URL解析失败: {e}")
            return None
    
    async def get_token_info_from_gmgn(self, token_address: str) -> Dict[str, Any]:
        """从GMGN获取代币信息"""
        try:
            # 构建API URL (可能需要根据实际API调整)
            api_url = f"{self.base_url}/api/sol/token/{token_address}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, headers=self.api_headers, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return self._parse_gmgn_response(data)
                    else:
                        # 如果API不可用，尝试网页抓取
                        return await self._scrape_gmgn_page(token_address)
                        
        except Exception as e:
            print(f"GMGN API调用失败: {e}")
            # 回退到网页抓取
            return await self._scrape_gmgn_page(token_address)
    
    async def _scrape_gmgn_page(self, token_address: str) -> Dict[str, Any]:
        """从GMGN页面抓取代币信息"""
        try:
            page_url = f"{self.base_url}/sol/token/{token_address}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(page_url, headers=self.api_headers, timeout=10) as resp:
                    if resp.status == 200:
                        html_content = await resp.text()
                        return self._parse_gmgn_html(html_content, token_address)
                    else:
                        return {"error": f"页面请求失败: {resp.status}"}
                        
        except Exception as e:
            return {"error": f"页面抓取失败: {e}"}
    
    def _parse_gmgn_response(self, data: Dict) -> Dict[str, Any]:
        """解析GMGN API响应"""
        # 这里需要根据实际的API响应结构进行调整
        return {
            "source": "GMGN_API",
            "token_address": data.get("address", ""),
            "symbol": data.get("symbol", ""),
            "name": data.get("name", ""),
            "price": data.get("price", 0),
            "market_cap": data.get("market_cap", 0),
            "volume_24h": data.get("volume_24h", 0),
            "holders": data.get("holders", 0),
            "pool_info": data.get("pool_info", {})
        }
    
    def _parse_gmgn_html(self, html: str, token_address: str) -> Dict[str, Any]:
        """解析GMGN HTML页面"""
        result = {
            "source": "GMGN_HTML",
            "token_address": token_address,
            "symbol": "",
            "name": "", 
            "price": 0,
            "market_cap": 0,
            "volume_24h": 0,
            "holders": 0,
            "pool_info": {},
            "pool_type": "UNKNOWN"
        }
        
        try:
            # 改进的HTML解析逻辑
            
            # 提取页面标题（可能包含代币信息）
            title_match = re.search(r'<title[^>]*>([^<]+)</title>', html)
            if title_match:
                title = title_match.group(1)
                # 尝试从标题提取符号
                if '|' in title:
                    parts = title.split('|')
                    if len(parts) > 0:
                        symbol_part = parts[0].strip()
                        result["symbol"] = symbol_part
            
            # 提取JSON数据（现代网站常用）
            json_matches = re.findall(r'<script[^>]*>\s*window\.__NUXT__\s*=\s*({[^<]+})', html)
            if json_matches:
                try:
                    json_data = json.loads(json_matches[0])
                    # 尝试从JSON中提取代币信息
                    if 'state' in json_data and 'token' in json_data['state']:
                        token_data = json_data['state']['token']
                        result["symbol"] = token_data.get('symbol', '')
                        result["name"] = token_data.get('name', '')
                        result["price"] = token_data.get('price', 0)
                except:
                    pass
            
            # 提取池类型信息
            for pool_type_display, pool_type_code in self.pool_types.items():
                if pool_type_display in html:
                    result["pool_type"] = pool_type_code
                    break
            
            # 提取Solana地址（44字符的base58）
            solana_address_match = re.search(r'[1-9A-HJ-NP-Za-km-z]{32,44}', html)
            if solana_address_match:
                addr = solana_address_match.group(0)
                # 检查是否是有效的Solana地址长度
                if len(addr) >= 32 and len(addr) <= 44:
                    result["pool_info"]["address"] = addr
            
        except Exception as e:
            result["error"] = f"HTML解析失败: {e}"
        
        return result
    
    async def analyze_token_compatibility(self, token_info: Dict[str, Any]) -> Dict[str, Any]:
        """分析代币与SDK的兼容性"""
        pool_type = token_info.get("pool_type", "UNKNOWN")
        
        compatibility = {
            "PUMP_AMM": {
                "status": "✅ 完全支持",
                "description": "Pump AMM池是Raydium的变种，我们的SDK可以处理",
                "actions": ["池信息获取", "LP价格计算", "流动性操作", "实际交易"],
                "difficulty": "低"
            },
            "RAYDIUM_AMM": {
                "status": "✅ 完全支持", 
                "description": "标准Raydium AMM池，SDK完全兼容",
                "actions": ["池信息获取", "LP价格计算", "流动性操作", "实际交易"],
                "difficulty": "低"
            },
            "DYNAMIC_BC": {
                "status": "⚠️ 有限支持",
                "description": "Dynamic BC池需要特殊处理，可能需要自定义逻辑",
                "actions": ["池信息获取", "需要深度分析", "可能需要联系GMGN"],
                "difficulty": "高"
            },
            "METEORA_DAMM_V2": {
                "status": "❌ 需要集成",
                "description": "需要Meteora SDK集成，目前不支持",
                "actions": ["需要额外开发", "需要Meteora SDK"],
                "difficulty": "中"
            },
            "UNKNOWN": {
                "status": "❓ 未知",
                "description": "池类型未知，需要进一步分析",
                "actions": ["需要池类型识别", "需要技术分析"],
                "difficulty": "未知"
            }
        }
        
        return compatibility.get(pool_type, compatibility["UNKNOWN"])

async def demonstrate_gmgn_token_reading():
    """演示GMGN代币信息读取"""
    
    reader = GMGNTokenReader()
    
    # 你提供的GMGN代币URL
    gmgn_url = "https://gmgn.ai/sol/token/moUrwgoiXBk7sZhpAHRvc7D6yXARwJYSUb3mH2iBAGS"
    
    print("🚀 GMGN代币信息读取器")
    print("=" * 70)
    
    # 提取代币地址
    token_address = await reader.extract_token_address_from_url(gmgn_url)
    
    if not token_address:
        print("❌ 无法从URL中提取代币地址")
        return
    
    print(f"🔗 GMGN URL: {gmgn_url}")
    print(f"🎯 代币地址: {token_address}")
    print("-" * 70)
    
    # 获取代币信息
    print("📥 正在从GMGN获取代币信息...")
    token_info = await reader.get_token_info_from_gmgn(token_address)
    
    print("\n📊 代币信息:")
    print(f"   数据来源: {token_info.get('source', '未知')}")
    print(f"   代币地址: {token_info.get('token_address', '未知')}")
    print(f"   代币符号: {token_info.get('symbol', '未知')}")
    print(f"   代币名称: {token_info.get('name', '未知')}")
    print(f"   当前价格: ${token_info.get('price', 0):.6f}")
    print(f"   池类型: {token_info.get('pool_type', '未知')}")
    
    if 'pool_info' in token_info and token_info['pool_info']:
        print(f"   池地址: {token_info['pool_info'].get('address', '未知')}")
    
    # 分析兼容性
    print("\n🔧 SDK兼容性分析:")
    compatibility = await reader.analyze_token_compatibility(token_info)
    
    print(f"   支持状态: {compatibility['status']}")
    print(f"   描述: {compatibility['description']}")
    print(f"   操作难度: {compatibility['difficulty']}")
    
    print("\n🛠️ 支持的操作:")
    for action in compatibility.get('actions', []):
        print(f"   • {action}")
    
    print("\n" + "=" * 70)
    print("🎯 实际操作建议")
    print("=" * 70)
    
    pool_type = token_info.get('pool_type', 'UNKNOWN')
    
    if pool_type in ['PUMP_AMM', 'RAYDIUM_AMM']:
        print("""
✅ 立即可行：这个代币可以使用我们的SDK进行交易！

操作步骤：
1. 使用我们的Raydium客户端获取池信息
2. 计算LP代币价格和流动性
3. 构建交易指令
4. 发送实际交易

示例代码：
```python
from src.sol_meme_sdk.raydium_client import RaydiumClient

# 初始化客户端
client = RaydiumClient()

# 获取池信息（需要池地址）
pool_info = await client.get_pool_info(pool_address)

# 进行流动性操作
result = await client.add_liquidity(pool_address, amount, wallet)
```
""")
    elif pool_type == 'DYNAMIC_BC':
        print("""
⚠️ 需要额外工作：Dynamic BC池需要特殊处理

建议：
1. 联系GMGN获取技术文档
2. 分析池的特殊数据结构
3. 可能需要实现自定义交易逻辑
4. 或者选择其他标准AMM池的代币
""")
    else:
        print("""
❓ 需要进一步分析：池类型未知或不受支持

建议：
1. 确认代币是否在活跃交易
2. 检查是否有其他可用的池信息
3. 考虑选择更成熟的代币进行交易
""")

if __name__ == "__main__":
    print("🎯 GMGN代币信息读取器启动...")
    asyncio.run(demonstrate_gmgn_token_reading())
    print("\n✅ 分析完成！")