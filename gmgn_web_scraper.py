#!/usr/bin/env python3
"""
GMGN网页抓取器 - 直接从GMGN页面解析代币和池信息
"""

import asyncio
import aiohttp
import re
import json
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup

class GMGNWebScraper:
    """GMGN网页抓取器"""
    
    def __init__(self):
        self.base_url = "https://gmgn.ai"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        
        # GMGN池类型关键词
        self.pool_keywords = {
            "Pump AMM池信息": "PUMP_AMM",
            "Dynamic BC 池信息": "DYNAMIC_BC",
            "METEORA_DAMM_V2 池信息": "METEORA_DAMM_V2", 
            "Raydium AMM池信息": "RAYDIUM_AMM",
            "池信息": "UNKNOWN_POOL"
        }
    
    async def scrape_token_page(self, url: str) -> Dict[str, Any]:
        """抓取GMGN代币页面"""
        try:
            print(f"🌐 正在访问: {url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, timeout=15) as response:
                    if response.status == 200:
                        html_content = await response.text()
                        return self._parse_gmgn_page(html_content, url)
                    else:
                        return {"error": f"HTTP {response.status}: {await response.text()}"}
                        
        except Exception as e:
            return {"error": f"抓取失败: {str(e)}"}
    
    def _parse_gmgn_page(self, html: str, url: str) -> Dict[str, Any]:
        """解析GMGN页面"""
        result = {
            "url": url,
            "token_address": self._extract_token_address(url),
            "token_symbol": "",
            "token_name": "",
            "pool_type": "UNKNOWN",
            "pool_address": "",
            "price": 0,
            "market_cap": 0,
            "volume_24h": 0,
            "holders": 0,
            "raw_data": {}
        }
        
        try:
            # 使用BeautifulSoup解析HTML
            soup = BeautifulSoup(html, 'html.parser')
            
            # 提取页面标题
            title = soup.find('title')
            if title:
                title_text = title.get_text()
                result["raw_data"]["title"] = title_text
                
                # 从标题提取代币符号
                if '|' in title_text:
                    symbol = title_text.split('|')[0].strip()
                    result["token_symbol"] = symbol
            
            # 查找池类型信息
            pool_type_found = self._find_pool_type(html, soup)
            if pool_type_found:
                result["pool_type"] = pool_type_found
            
            # 查找池地址
            pool_address = self._find_pool_address(html, soup)
            if pool_address:
                result["pool_address"] = pool_address
            
            # 查找价格信息
            price_info = self._find_price_info(html, soup)
            result.update(price_info)
            
            # 提取JSON数据（现代网站常用）
            json_data = self._extract_json_data(html)
            if json_data:
                result["raw_data"]["json"] = json_data
                
                # 尝试从JSON中提取更多信息
                self._enhance_from_json(result, json_data)
            
            # 提取页面中的关键文本
            key_texts = self._extract_key_texts(soup)
            result["raw_data"]["key_texts"] = key_texts
            
        except Exception as e:
            result["error"] = f"解析失败: {str(e)}"
        
        return result
    
    def _extract_token_address(self, url: str) -> str:
        """从URL提取代币地址"""
        # GMGN URL格式: /sol/token/{address}
        parts = url.rstrip('/').split('/')
        if len(parts) >= 5 and parts[-2] == 'token':
            return parts[-1]
        return ""
    
    def _find_pool_type(self, html: str, soup: BeautifulSoup) -> str:
        """查找池类型"""
        # 方法1: 直接在HTML文本中搜索关键词
        for display_text, pool_code in self.pool_keywords.items():
            if display_text in html:
                print(f"🔍 找到池类型: {display_text} -> {pool_code}")
                return pool_code
        
        # 方法2: 在特定元素中搜索
        pool_elements = soup.find_all(['div', 'span', 'p'], string=re.compile(r'.*池信息.*'))
        for element in pool_elements:
            text = element.get_text()
            for display_text, pool_code in self.pool_keywords.items():
                if display_text in text:
                    print(f"🔍 在元素中找到池类型: {display_text} -> {pool_code}")
                    return pool_code
        
        return "UNKNOWN"
    
    def _find_pool_address(self, html: str, soup: BeautifulSoup) -> str:
        """查找池地址"""
        # 查找Solana地址（32-44字符的base58）
        addresses = re.findall(r'[1-9A-HJ-NP-Za-km-z]{32,44}', html)
        
        # 过滤掉代币地址本身
        token_addr = self._extract_token_address(html)
        valid_addresses = [addr for addr in addresses if addr != token_addr and len(addr) >= 32]
        
        if valid_addresses:
            # 取第一个有效的地址作为池地址
            return valid_addresses[0]
        
        return ""
    
    def _find_price_info(self, html: str, soup: BeautifulSoup) -> Dict[str, Any]:
        """查找价格信息"""
        result = {"price": 0, "market_cap": 0, "volume_24h": 0, "holders": 0}
        
        # 查找价格模式
        price_patterns = [
            r'\$([0-9]+[.,][0-9]+)',  # $1.23
            r'价格[:：]\s*\$?([0-9.,]+)',  # 价格: $1.23
        ]
        
        for pattern in price_patterns:
            matches = re.findall(pattern, html)
            if matches:
                try:
                    price_str = matches[0].replace(',', '')
                    result["price"] = float(price_str)
                    break
                except:
                    pass
        
        return result
    
    def _extract_json_data(self, html: str) -> Optional[Dict]:
        """提取JSON数据"""
        # 查找常见的JSON数据模式
        json_patterns = [
            r'window\.__NUXT__\s*=\s*({[^<]+})',
            r'window\.__INITIAL_STATE__\s*=\s*({[^<]+})',
            r'<script[^>]*>\s*({[^<]+})\s*</script>',
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, html, re.DOTALL)
            for match in matches:
                try:
                    return json.loads(match)
                except:
                    continue
        
        return None
    
    def _enhance_from_json(self, result: Dict, json_data: Dict):
        """从JSON数据增强结果"""
        # 尝试从不同的JSON结构中提取信息
        
        # 方法1: 深度搜索
        def deep_search(obj, target_keys):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key in target_keys:
                        return value
                    found = deep_search(value, target_keys)
                    if found:
                        return found
            elif isinstance(obj, list):
                for item in obj:
                    found = deep_search(item, target_keys)
                    if found:
                        return found
            return None
        
        # 搜索关键字段
        symbol = deep_search(json_data, ['symbol', 'tokenSymbol', 'name'])
        if symbol and not result["token_symbol"]:
            result["token_symbol"] = str(symbol)
        
        price = deep_search(json_data, ['price', 'currentPrice', 'value'])
        if price and not result["price"]:
            try:
                result["price"] = float(price)
            except:
                pass
    
    def _extract_key_texts(self, soup: BeautifulSoup) -> list:
        """提取关键文本"""
        key_texts = []
        
        # 提取标题和重要文本
        important_selectors = ['h1', 'h2', 'h3', '.title', '.header', '.important', '.pool-info']
        
        for selector in important_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text().strip()
                if text and len(text) > 5:
                    key_texts.append(text)
        
        return key_texts
    
    def analyze_scraped_data(self, data: Dict) -> Dict[str, Any]:
        """分析抓取的数据"""
        analysis = {
            "pool_type_found": data.get("pool_type", "UNKNOWN") != "UNKNOWN",
            "pool_address_found": bool(data.get("pool_address", "")),
            "price_found": data.get("price", 0) > 0,
            "symbol_found": bool(data.get("token_symbol", "")),
            "recommendation": ""
        }
        
        pool_type = data.get("pool_type", "UNKNOWN")
        
        if pool_type in ["PUMP_AMM", "RAYDIUM_AMM"]:
            analysis["recommendation"] = "✅ 立即可用 - 我们的SDK完全支持"
        elif pool_type == "DYNAMIC_BC":
            analysis["recommendation"] = "⚠️ 需要特殊处理 - Dynamic BC池"
        elif pool_type == "METEORA_DAMM_V2":
            analysis["recommendation"] = "❌ 需要集成 - Meteora DAMM V2"
        else:
            analysis["recommendation"] = "❓ 未知池类型 - 需要进一步确认"
        
        return analysis

async def demonstrate_gmgn_scraping():
    """演示GMGN页面抓取"""
    
    scraper = GMGNWebScraper()
    
    # 你提供的GMGN代币URL
    target_url = "https://gmgn.ai/sol/token/moUrwgoiXBk7sZhpAHRvc7D6yXARwJYSUb3mH2iBAGS"
    
    print("🚀 GMGN网页抓取器")
    print("=" * 70)
    
    # 抓取页面
    print(f"📥 正在抓取: {target_url}")
    data = await scraper.scrape_token_page(target_url)
    
    # 显示结果
    print("\n📊 抓取结果:")
    print(f"   代币地址: {data.get('token_address', '未知')}")
    print(f"   代币符号: {data.get('token_symbol', '未知')}")
    print(f"   池类型: {data.get('pool_type', '未知')}")
    print(f"   池地址: {data.get('pool_address', '未知')}")
    print(f"   价格: ${data.get('price', 0):.6f}")
    
    # 分析结果
    analysis = scraper.analyze_scraped_data(data)
    print(f"\n🔍 分析结果:")
    print(f"   池类型识别: {'✅' if analysis['pool_type_found'] else '❌'}")
    print(f"   池地址识别: {'✅' if analysis['pool_address_found'] else '❌'}")
    print(f"   价格信息: {'✅' if analysis['price_found'] else '❌'}")
    print(f"   代币符号: {'✅' if analysis['symbol_found'] else '❌'}")
    print(f"   建议: {analysis['recommendation']}")
    
    # 显示详细数据（如果有）
    if 'raw_data' in data and data['raw_data']:
        print(f"\n📋 原始数据摘要:")
        if 'title' in data['raw_data']:
            print(f"   页面标题: {data['raw_data']['title'][:100]}...")
        if 'key_texts' in data['raw_data'] and data['raw_data']['key_texts']:
            print(f"   关键文本: {len(data['raw_data']['key_texts'])} 条")
            for i, text in enumerate(data['raw_data']['key_texts'][:3]):
                print(f"     {i+1}. {text[:80]}...")
    
    print("\n" + "=" * 70)
    print("🎯 操作建议")
    print("=" * 70)
    
    pool_type = data.get("pool_type", "UNKNOWN")
    
    if pool_type in ["PUMP_AMM", "RAYDIUM_AMM"]:
        print("""
✅ 立即可行！检测到Pump AMM或Raydium AMM池

操作步骤：
1. 使用池地址进行交易
2. 我们的SDK完全支持
3. 可以进行流动性操作

示例代码：
```python
from src.sol_meme_sdk.raydium_client import RaydiumClient

client = RaydiumClient()
# 使用抓取到的池地址
pool_info = await client.get_pool_info("池地址")
result = await client.add_liquidity("池地址", amount, wallet)
```
""")
    elif pool_type == "DYNAMIC_BC":
        print("""
⚠️ 需要额外处理 - Dynamic BC池

建议：
1. 可能需要联系GMGN获取技术细节
2. 或者选择其他标准AMM池的代币
3. 我们的SDK可能需要扩展才能支持
""")
    else:
        print("""
❓ 池类型未识别或未知

可能的原因：
1. 页面结构可能已改变
2. 可能需要手动检查GMGN页面
3. 或者提供池地址进行直接分析

建议手动检查GMGN页面确认池类型。
""")

if __name__ == "__main__":
    print("🎯 GMGN网页抓取器启动...")
    asyncio.run(demonstrate_gmgn_scraping())
    print("\n✅ 抓取完成！")