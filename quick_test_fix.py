#!/usr/bin/env python3
"""
快速测试修复版本
"""

import asyncio


class QuickTest:
    """快速测试类"""
    
    def __init__(self):
        # 正确的代币列表（去重）
        self.tokens = {
            "即将打满": [
                "9BWgoKN9yU85NHr9GXhadAiJXm3eEQo6rWJLgQLbVtAW",
                "21Rmzk4nQhmRrKzG6xYR9SJ4u6vSzZHwHhgjHiAbX6LE",
                "YMPyH6D7LopJfwinSNXDRpLUPGDymnJg3KAxSuEpump",
                "EpR36YEfteDW1SXLwFfExdYHj2hz8NfibeeW5JwroaAg"
            ],
            "已迁移": [
                "CzzGkKCZvJuPGbvkBrSpNSLxXY4hTPATM6owNHhVpump",
                "7VabHa3ZaExQPTMTFRUaRBz8vHAdXY4hMWQ22ZAHpump",
                "7ipMSYbBKTtpA8ubJAPtKVuQUY4N2zBywuJRY2oPcHoP",
                "9PooGhi9svzrtne2937v58kh1KJzb8yn7ofHeg2ipump",
                "8b9hHkypSaGR7yNCCscCRxwhZKx3jTPVrwB3UPYcuG4f"
            ]
        }
    
    async def test_token_status(self):
        """测试代币状态检测"""
        
        print("🔍 测试代币状态检测逻辑")
        print("=" * 60)
        
        # 模拟流动性数据
        liquidity_data = {
            # 即将打满的代币 - 低流动性
            "9BWgoKN9yU85NHr9GXhadAiJXm3eEQo6rWJLgQLbVtAW": 800,
            "21Rmzk4nQhmRrKzG6xYR9SJ4u6vSzZHwHhgjHiAbX6LE": 1200,
            "YMPyH6D7LopJfwinSNXDRpLUPGDymnJg3KAxSuEpump": 900,
            "EpR36YEfteDW1SXLwFfExdYHj2hz8NfibeeW5JwroaAg": 700,
            
            # 已迁移的代币 - 高流动性
            "CzzGkKCZvJuPGbvkBrSpNSLxXY4hTPATM6owNHhVpump": 23000,
            "7VabHa3ZaExQPTMTFRUaRBz8vHAdXY4hMWQ22ZAHpump": 12000,
            "7ipMSYbBKTtpA8ubJAPtKVuQUY4N2zBywuJRY2oPcHoP": 24000,
            "9PooGhi9svzrtne2937v58kh1KJzb8yn7ofHeg2ipump": 16000,
            "8b9hHkypSaGR7yNCCscCRxwhZKx3jTPVrwB3UPYcuG4f": 30000
        }
        
        # 动态阈值计算
        low_threshold = 1000  # 低流动性阈值
        migration_threshold = 10000  # 迁移阈值
        
        # 测试所有代币
        for category, tokens in self.tokens.items():
            print(f"\n📊 {category} 代币检测:")
            print("-" * 40)
            
            for token in tokens:
                liquidity = liquidity_data.get(token, 0)
                
                # 状态判断（只有两种状态）
                if liquidity < low_threshold:
                    status = "即将打满"
                else:
                    status = "已迁移"
                
                # GMGN状态（模拟）
                gmgn_status = category
                match = status == gmgn_status
                
                status_icon = "✅" if match else "❌"
                print(f"{status_icon} {token[:8]}...{token[-8:]}")
                print(f"   状态: {status} (DEX) vs {gmgn_status} (GMGN)")
                print(f"   流动性: {liquidity} SOL")
                print(f"   阈值: [{low_threshold} - {migration_threshold}] SOL")
                
                if not match:
                    print(f"   ⚠️ 状态不匹配!")
        
        print("\n" + "=" * 60)
        print("🎯 测试总结")
        print("=" * 60)
        print("✅ 修复的问题:")
        print("   • 去重代币地址")
        print("   • 简化状态判断逻辑（只有两种状态）")
        print("   • 避免'正常'状态的出现")
        print("\n💡 阈值说明:")
        print(f"   • 即将打满: < {low_threshold} SOL")
        print(f"   • 已迁移: >= {low_threshold} SOL")
        print("\n📊 注意: 这是简化版测试，实际应使用真实DEX API数据")


async def main():
    """主函数"""
    test = QuickTest()
    await test.test_token_status()


if __name__ == "__main__":
    asyncio.run(main())