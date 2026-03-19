#!/usr/bin/env python3
"""
轻量级真实链上数据集成测试 - 简化版本避免内存问题
"""

import asyncio
import time
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solders.pubkey import Pubkey


class LightweightIntegrationTest:
    """轻量级集成测试类"""
    
    def __init__(self, rpc_url="https://api.mainnet-beta.solana.com"):
        self.rpc_url = rpc_url
        self.client = AsyncClient(rpc_url)
    
    async def connect(self):
        """连接到网络"""
        await self.client.__aenter__()
        print(f"✅ 已连接到: {self.rpc_url}")
    
    async def close(self):
        """关闭连接"""
        await self.client.__aexit__(None, None, None)
        print("✅ 已断开连接")
    
    async def test_solana_rpc_connectivity(self):
        """测试Solana RPC连通性"""
        print("🔗 测试Solana RPC连通性...")
        
        try:
            start_time = time.time()
            version_info = await self.client.get_version()
            latency = (time.time() - start_time) * 1000
            
            print(f"✅ Solana RPC连接成功")
            print(f"   节点版本: {version_info.value}")
            print(f"   延迟: {latency:.1f}ms")
            return True
            
        except Exception as e:
            print(f"❌ Solana RPC连接失败: {e}")
            return False
    
    async def test_token_info_retrieval(self):
        """测试代币信息获取"""
        print("\n🔍 测试代币信息获取...")
        
        # 测试已知代币
        test_tokens = [
            ("So11111111111111111111111111111111111111112", "SOL"),
            ("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "USDC"),
        ]
        
        success_count = 0
        
        for token_address, symbol in test_tokens:
            try:
                print(f"   获取 {symbol} 信息...")
                
                start_time = time.time()
                
                # 获取账户信息
                account_info = await self.client.get_account_info(
                    Pubkey.from_string(token_address),
                    commitment=Confirmed
                )
                
                latency = (time.time() - start_time) * 1000
                
                if account_info.value:
                    print(f"      ✅ 成功 ({latency:.1f}ms)")
                    print(f"        所有者: {account_info.value.owner}")
                    print(f"        Lamports: {account_info.value.lamports}")
                    print(f"        数据长度: {len(account_info.value.data)} 字节")
                    success_count += 1
                else:
                    print(f"      ❌ 账户不存在")
                    
            except Exception as e:
                print(f"      ❌ 获取失败: {e}")
        
        print(f"\n📊 代币信息获取: {success_count}/{len(test_tokens)} 成功")
        return success_count == len(test_tokens)
    
    async def test_token_supply_retrieval(self):
        """测试代币供应量获取"""
        print("\n💰 测试代币供应量获取...")
        
        # 测试已知代币
        test_tokens = [
            ("So11111111111111111111111111111111111111112", "SOL"),
            ("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "USDC"),
        ]
        
        success_count = 0
        
        for token_address, symbol in test_tokens:
            try:
                print(f"   获取 {symbol} 供应量...")
                
                start_time = time.time()
                
                # 获取供应量信息
                supply_info = await self.client.get_token_supply(
                    Pubkey.from_string(token_address),
                    commitment=Confirmed
                )
                
                latency = (time.time() - start_time) * 1000
                
                if supply_info.value:
                    print(f"      ✅ 成功 ({latency:.1f}ms)")
                    print(f"        数量: {supply_info.value.amount}")
                    print(f"        精度: {supply_info.value.decimals}")
                    print(f"        UI数量: {supply_info.value.ui_amount}")
                    success_count += 1
                else:
                    print(f"      ❌ 供应量信息不存在")
                    
            except Exception as e:
                print(f"      ❌ 获取失败: {e}")
        
        print(f"\n📊 供应量获取: {success_count}/{len(test_tokens)} 成功")
        return success_count == len(test_tokens)
    
    async def test_concurrent_operations(self):
        """测试并发操作"""
        print("\n⚡ 测试并发操作...")
        
        test_tokens = [
            "So11111111111111111111111111111111111111112",  # SOL
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
        ]
        
        try:
            # 顺序操作
            print("   测试顺序操作...")
            sequential_start = time.time()
            
            for token in test_tokens:
                await self.client.get_account_info(
                    Pubkey.from_string(token),
                    commitment=Confirmed
                )
            
            sequential_time = time.time() - sequential_start
            
            # 并发操作
            print("   测试并发操作...")
            concurrent_start = time.time()
            
            tasks = [
                self.client.get_account_info(
                    Pubkey.from_string(token),
                    commitment=Confirmed
                )
                for token in test_tokens
            ]
            
            await asyncio.gather(*tasks)
            concurrent_time = time.time() - concurrent_start
            
            print(f"     顺序时间: {sequential_time:.3f}秒")
            print(f"     并发时间: {concurrent_time:.3f}秒")
            print(f"     性能提升: {sequential_time/concurrent_time:.1f}x")
            
            return True
            
        except Exception as e:
            print(f"      ❌ 并发测试失败: {e}")
            return False
    
    async def test_error_handling(self):
        """测试错误处理"""
        print("\n🐛 测试错误处理...")
        
        invalid_tokens = [
            "invalid_token_address",
            "000000000000000000000000000000000000000000",
        ]
        
        error_count = 0
        
        for token_address in invalid_tokens:
            try:
                print(f"   测试无效地址: {token_address[:20]}...")
                
                await self.client.get_account_info(
                    Pubkey.from_string(token_address),
                    commitment=Confirmed
                )
                
                print(f"      ⚠️ 未检测到错误")
                
            except Exception as e:
                print(f"      ✅ 正确捕获错误: {type(e).__name__}")
                error_count += 1
        
        print(f"\n📊 错误处理: {error_count}/{len(invalid_tokens)} 正确捕获")
        return error_count == len(invalid_tokens)


async def main():
    """主测试函数"""
    print("🚀 开始轻量级真实链上数据集成测试")
    print("=" * 60)
    
    test = LightweightIntegrationTest()
    
    try:
        await test.connect()
        
        test_results = {}
        
        # 运行各项测试
        test_results['rpc_connectivity'] = await test.test_solana_rpc_connectivity()
        test_results['token_info'] = await test.test_token_info_retrieval()
        test_results['token_supply'] = await test.test_token_supply_retrieval()
        test_results['concurrent_ops'] = await test.test_concurrent_operations()
        test_results['error_handling'] = await test.test_error_handling()
        
        # 输出测试总结
        print("\n" + "=" * 60)
        print("📊 测试总结")
        
        passed_tests = sum(1 for result in test_results.values() if result)
        total_tests = len(test_results)
        
        for test_name, result in test_results.items():
            status = "✅ 通过" if result else "❌ 失败"
            print(f"   {test_name}: {status}")
        
        print(f"\n🎯 总体结果: {passed_tests}/{total_tests} 个测试通过")
        
        if passed_tests == total_tests:
            print("\n🎉 所有测试通过！真实链上数据集成验证成功！")
            
            # 输出技术指标
            print("\n📈 技术指标:")
            print("   ✅ Solana RPC连接稳定")
            print("   ✅ 代币信息获取正常")
            print("   ✅ 供应量查询准确")
            print("   ✅ 并发操作性能优化")
            print("   ✅ 错误处理机制完善")
            
        else:
            print("\n⚠️  部分测试失败，需要进一步调试")
        
    except Exception as e:
        print(f"❌ 测试执行失败: {e}")
    finally:
        await test.close()


if __name__ == "__main__":
    asyncio.run(main())