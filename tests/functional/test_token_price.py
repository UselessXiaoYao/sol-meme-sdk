#!/usr/bin/env python3
"""
定时获取代币价格的脚本
使用Jupiter Price API直接获取价格，支持批量查询
"""

import asyncio
import sys
import csv
import os
from datetime import datetime, timedelta
from src.sol_meme_sdk.jupiter_client import JupiterClient
from src.sol_meme_sdk.exceptions import TradingError


async def get_token_prices_direct(token_address: str, jupiter_client: JupiterClient) -> tuple:
    """直接使用Jupiter Price API v3获取代币价格"""
    try:
        # 使用Jupiter Price API v3获取批量价格（SOL和当前代币）
        tokens = [token_address, "So11111111111111111111111111111111111111112"]
        prices = await jupiter_client.get_prices(tokens)
        
        # 解析价格数据
        if token_address in prices and isinstance(prices[token_address], dict):
            token_price_data = prices[token_address]
            usd_price = float(token_price_data.get('usdPrice', 0))
        else:
            usd_price = 0.0
        
        if "So11111111111111111111111111111111111111112" in prices and isinstance(prices["So11111111111111111111111111111111111111112"], dict):
            sol_price_data = prices["So11111111111111111111111111111111111111112"]
            sol_usd_price = float(sol_price_data.get('usdPrice', 0))
        else:
            sol_usd_price = 0.0
        
        # 计算SOL价格（USD价格 / SOL的USD价格）
        if sol_usd_price > 0 and usd_price > 0:
            price_in_sol = usd_price / sol_usd_price
        else:
            price_in_sol = 0.0
        
        return price_in_sol, usd_price
        
    except Exception as e:
        print(f"❌ 获取价格失败: {e}")
        raise TradingError(f"无法获取代币价格: {e}")


async def monitor_token_price(token_address: str, duration_minutes: int = 10):
    """定时监控代币价格"""
    print(f"🔄 开始监控代币价格（使用Jupiter Price API）")
    print(f"代币地址: {token_address}")
    print(f"持续时间: {duration_minutes}分钟")
    print("-" * 60)
    
    # 创建CSV文件
    csv_filename = f"token_price_{token_address[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    # 初始化Jupiter客户端
    jupiter_client = JupiterClient()
    
    # 先测试地址是否有效
    try:
        print("🔍 测试代币地址有效性...")
        test_price_sol, test_price_usd = await get_token_prices_direct(token_address, jupiter_client)
        print(f"✅ 代币地址有效")
        print(f"当前价格: {test_price_sol:.10f} SOL (${test_price_usd:.6f} USD)")
        print("-" * 60)
    except Exception as e:
        print(f"❌ 代币地址无效或无法获取价格: {e}")
        print("💡 可能的原因:")
        print("  - 代币地址不正确")
        print("  - 代币没有流动性")
        print("  - 网络连接问题")
        return
    
    # 计算结束时间
    end_time = datetime.now() + timedelta(minutes=duration_minutes)
    record_count = 0
    
    # 创建CSV文件并写入表头
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(['timestamp', 'price_sol', 'price_usd'])
    
    print(f"📊 数据将保存到: {csv_filename}")
    print("⏰ 开始记录，按 Ctrl+C 可提前终止")
    print("-" * 60)
    
    # 开始监控循环
    while datetime.now() < end_time:
        try:
            # 获取精确到毫秒的时间戳
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            
            # 获取价格
            price_sol, price_usd = await get_token_prices_direct(token_address, jupiter_client)
            
            # 检查价格是否归零
            if price_sol <= 0.0:
                print(f"⚠️ 检测到价格归零: {price_sol:.10f} SOL")
                print("🔴 价格归零，停止监控")
                break
            
            # 输出结果
            print(f"[{timestamp}] 价格: {price_sol:.10f} SOL (${price_usd:.6f} USD)")
            
            # 保存到CSV文件
            with open(csv_filename, 'a', newline='', encoding='utf-8') as csvfile:
                csv_writer = csv.writer(csvfile)
                csv_writer.writerow([timestamp, f"{price_sol:.10f}", f"{price_usd:.6f}"])
            
            record_count += 1
            
            # 等待1秒
            await asyncio.sleep(1)
                
        except Exception as e:
            print(f"❌ 获取价格失败: {e}")
            print("🚫 脚本异常退出")
            break
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
        print("使用方法: python test_token_price.py <代币地址>")
        print("示例: python test_token_price.py EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
        print("\n功能说明:")
        print("  - 使用Jupiter Price API直接获取价格")
        print("  - 每1秒记录一次代币价格")
        print("  - 持续10分钟或价格归零时自动停止")
        print("  - 保存为CSV文件，包含时间戳、SOL价格、USD价格")
        sys.exit(1)
    
    token_address = sys.argv[1]
    
    # 验证地址格式（Solana地址通常是32-44个字符）
    if len(token_address) < 32 or len(token_address) > 44:
        print(f"❌ 地址格式错误: 长度应在32-44字符之间，实际为{len(token_address)}字符")
        sys.exit(1)
    
    # 运行监控（10分钟）
    try:
        asyncio.run(monitor_token_price(token_address, duration_minutes=10))
    except Exception as e:
        print(f"❌ 脚本执行失败: {e}")


if __name__ == "__main__":
    main()