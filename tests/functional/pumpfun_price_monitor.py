#!/usr/bin/env python3
"""
PumpFun代币价格监控脚本
专门处理PumpFun平台的代币价格获取
"""

import asyncio
import sys
import csv
import os
import aiohttp
import json
from datetime import datetime, timedelta


class PumpFunPriceMonitor:
    """PumpFun代币价格监控器"""
    
    def __init__(self):
        self.base_url = "https://frontend-api-v3.pump.fun"
        
    async def get_token_info(self, token_address: str) -> dict:
        """获取PumpFun代币信息"""
        url = f"{self.base_url}/coins/{token_address}"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    else:
                        raise Exception(f"API请求失败: {response.status}")
            except Exception as e:
                raise Exception(f"获取代币信息失败: {e}")
    
    async def calculate_token_price(self, token_info: dict) -> tuple:
        """计算代币价格（SOL和USD）"""
        try:
            # 从API数据中提取关键信息
            virtual_sol_reserves = token_info.get('virtual_sol_reserves', 0)
            virtual_token_reserves = token_info.get('virtual_token_reserves', 0)
            
            # 转换为SOL单位（1 SOL = 1,000,000,000 lamports）
            sol_reserves = virtual_sol_reserves / 1_000_000_000
            
            # 计算1个代币的价格（SOL）
            if virtual_token_reserves > 0 and sol_reserves > 0:
                # 价格公式：price = (k / token_reserves^2) 或直接计算
                # 简化计算：price = sol_reserves / token_reserves
                price_per_token_sol = sol_reserves / virtual_token_reserves
            else:
                price_per_token_sol = 0.0
            
            # 获取USD价格（从API数据中直接获取）
            usd_market_cap = token_info.get('usd_market_cap', 0)
            total_supply = token_info.get('total_supply', 1)
            
            if total_supply > 0:
                price_per_token_usd = usd_market_cap / total_supply
            else:
                price_per_token_usd = 0.0
            
            return price_per_token_sol, price_per_token_usd
            
        except Exception as e:
            raise Exception(f"计算价格失败: {e}")


async def monitor_pumpfun_token(token_address: str, duration_minutes: int = 10):
    """监控PumpFun代币价格"""
    print(f"🔄 开始监控PumpFun代币价格")
    print(f"代币地址: {token_address}")
    print(f"持续时间: {duration_minutes}分钟")
    print("-" * 60)
    
    # 创建CSV文件
    csv_filename = f"pumpfun_price_{token_address[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    # 初始化监控器
    monitor = PumpFunPriceMonitor()
    
    # 先测试地址是否有效
    try:
        print("🔍 测试代币地址有效性...")
        token_info = await monitor.get_token_info(token_address)
        
        # 检查代币是否完成初始化
        if not token_info.get('initialized', False):
            raise Exception("代币未初始化")
        
        if not token_info.get('complete', False):
            raise Exception("代币未完成发行")
        
        price_sol, price_usd = await monitor.calculate_token_price(token_info)
        
        print(f"✅ 代币信息获取成功")
        print(f"代币名称: {token_info.get('name', 'N/A')}")
        print(f"代币符号: {token_info.get('symbol', 'N/A')}")
        print(f"当前价格: {price_sol:.10f} SOL (${price_usd:.10f} USD)")
        print(f"市值: ${token_info.get('usd_market_cap', 0):.2f} USD")
        print("-" * 60)
        
    except Exception as e:
        print(f"❌ 代币地址无效或无法获取信息: {e}")
        print("💡 可能的原因:")
        print("  - 代币地址不正确")
        print("  - 代币未在PumpFun上发行")
        print("  - 网络连接问题")
        return
    
    # 计算结束时间
    end_time = datetime.now() + timedelta(minutes=duration_minutes)
    record_count = 0
    
    # 创建CSV文件并写入表头
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(['timestamp', 'price_sol', 'price_usd', 'market_cap_usd', 'sol_reserves', 'token_reserves'])
    
    print(f"📊 数据将保存到: {csv_filename}")
    print("⏰ 开始记录，按 Ctrl+C 可提前终止")
    print("-" * 60)
    
    # 开始监控循环
    while datetime.now() < end_time:
        try:
            # 获取精确到毫秒的时间戳
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            
            # 获取代币信息
            token_info = await monitor.get_token_info(token_address)
            
            # 计算价格
            price_sol, price_usd = await monitor.calculate_token_price(token_info)
            
            # 检查价格是否归零
            if price_sol <= 0.0:
                print(f"⚠️ 检测到价格归零: {price_sol:.10f} SOL")
                print("🔴 价格归零，停止监控")
                break
            
            # 提取其他有用信息
            market_cap = token_info.get('usd_market_cap', 0)
            sol_reserves = token_info.get('virtual_sol_reserves', 0) / 1_000_000_000
            token_reserves = token_info.get('virtual_token_reserves', 0)
            
            # 输出结果
            print(f"[{timestamp}] 价格: {price_sol:.10f} SOL (${price_usd:.10f} USD)")
            
            # 保存到CSV文件
            with open(csv_filename, 'a', newline='', encoding='utf-8') as csvfile:
                csv_writer = csv.writer(csvfile)
                csv_writer.writerow([
                    timestamp, 
                    f"{price_sol:.10f}", 
                    f"{price_usd:.10f}",
                    f"{market_cap:.2f}",
                    f"{sol_reserves:.6f}",
                    token_reserves
                ])
            
            record_count += 1
            
            # 等待1秒
            await asyncio.sleep(1)
                
        except Exception as e:
            print(f"❌ 获取价格失败: {e}")
            # 继续尝试，不退出
            await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 用户中断监控")
            break
    
    # 统计信息
    print("-" * 60)
    print(f"✅ 监控完成")
    print(f"📈 总共记录: {record_count} 条数据")
    print(f"💾 数据文件: {csv_filename}")
    
    # 显示文件大小
    if os.path.exists(csv_filename):
        file_size = os.path.getsize(csv_filename)
        print(f"📄 文件大小: {file_size} 字节")


def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("使用方法: python pumpfun_price_monitor.py <PumpFun代币地址>")
        print("示例: python pumpfun_price_monitor.py 8oERQvrzYTa7j2wHrvsfvWHFTF7jtB3k3JshkpN9pump")
        print("\n功能说明:")
        print("  - 专门处理PumpFun平台代币")
        print("  - 每1秒记录一次价格")
        print("  - 持续10分钟或价格归零时自动停止")
        print("  - 保存为CSV文件，包含详细市场数据")
        sys.exit(1)
    
    token_address = sys.argv[1]
    
    # 验证地址格式（PumpFun地址通常是44字符）
    if len(token_address) != 44 or not token_address.endswith('pump'):
        print(f"⚠️ 注意: 这看起来不是标准的PumpFun地址")
        print(f"地址格式: 应为44字符并以'pump'结尾")
    
    # 运行监控（10分钟）
    try:
        asyncio.run(monitor_pumpfun_token(token_address, duration_minutes=10))
    except Exception as e:
        print(f"❌ 脚本执行失败: {e}")


if __name__ == "__main__":
    main()