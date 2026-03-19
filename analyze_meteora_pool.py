#!/usr/bin/env python3
"""
分析Meteora池的实际数据结构和程序ID
"""

import asyncio
from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey


async def check_meteora_pool():
    """检查Meteora池的实际数据"""
    client = AsyncClient('https://api.mainnet-beta.solana.com')
    
    # 检查Meteora池地址
    pool_address = 'GhnhG6E99o9VrYReKBcPjRmKTyWcwWAm5Vz8SujdLGEs'
    
    try:
        await client.__aenter__()
        pool_pubkey = Pubkey.from_string(pool_address)
        account_info = await client.get_account_info(pool_pubkey)
        
        if account_info.value:
            print(f'池账户存在，数据大小: {len(account_info.value.data)} 字节')
            print(f'所有者程序ID: {account_info.value.owner}')
            
            # 显示前200字节的数据（用于分析结构）
            data_hex = account_info.value.data[:200].hex()
            print(f'池数据 (前200字节): {data_hex}')
            
            # 尝试解析可能的字段
            data = account_info.value.data
            if len(data) >= 144:
                print('\n尝试解析池结构:')
                print(f'偏移8-40: {data[8:40].hex()} (可能是基础代币mint)')
                print(f'偏移40-72: {data[40:72].hex()} (可能是报价代币mint)')
                print(f'偏移72-80: {int.from_bytes(data[72:80], "little")} (基础代币数量)')
                print(f'偏移80-88: {int.from_bytes(data[80:88], "little")} (报价代币数量)')
                print(f'偏移104-136: {data[104:136].hex()} (可能是LP代币mint)')
                print(f'偏移136-144: {int.from_bytes(data[136:144], "little")} (LP供应量)')
                
                # 检查是否是有效的mint地址
                try:
                    base_mint = str(Pubkey(data[8:40]))
                    quote_mint = str(Pubkey(data[40:72]))
                    lp_mint = str(Pubkey(data[104:136]))
                    
                    print(f'\n解析后的地址:')
                    print(f'基础代币mint: {base_mint}')
                    print(f'报价代币mint: {quote_mint}') 
                    print(f'LP代币mint: {lp_mint}')
                    
                    # 检查这些mint账户是否存在
                    for mint_name, mint_address in [('基础代币', base_mint), ('报价代币', quote_mint), ('LP代币', lp_mint)]:
                        try:
                            mint_info = await client.get_account_info(Pubkey.from_string(mint_address))
                            if mint_info.value:
                                print(f'{mint_name}: ✅ 有效账户 ({len(mint_info.value.data)} 字节)')
                            else:
                                print(f'{mint_name}: ❌ 无效账户')
                        except:
                            print(f'{mint_name}: ❌ 无法获取账户信息')
                            
                except Exception as e:
                    print(f'地址解析错误: {e}')
                    
        else:
            print('池账户不存在')
            
    except Exception as e:
        print(f'错误: {e}')
    finally:
        await client.close()


async def search_meteora_program_ids():
    """搜索已知的Meteora程序ID"""
    client = AsyncClient('https://api.mainnet-beta.solana.com')
    
    # 已知的Meteora相关程序ID（从公开信息收集）
    known_meteora_programs = [
        "DAMMv2L1Q4tL8KMXhKjK1Q4xM3Y7dUz7J6wJ5qJ8wJ9",  # 我们的假设ID
        "DAMMv2L1Q4tL8KMXhKjK1Q4xM3Y7dUz7J6wJ5qJ8wJ8",  # 可能的变体
        "DAMMv2L1Q4tL8KMXhKjK1Q4xM3Y7dUz7J6wJ5qJ8wJ7",
        # 从其他来源收集的可能ID
        "DLMMv2L1Q4tL8KMXhKjK1Q4xM3Y7dUz7J6wJ5qJ8wJ9",  # DLMM变体
        "DBCv2L1Q4tL8KMXhKjK1Q4xM3Y7dUz7J6wJ5qJ8wJ9",   # DBC变体
    ]
    
    try:
        await client.__aenter__()
        
        print("\n搜索已知的Meteora程序ID:")
        for program_id in known_meteora_programs:
            try:
                program_pubkey = Pubkey.from_string(program_id)
                program_info = await client.get_account_info(program_pubkey)
                
                if program_info.value:
                    print(f"✅ {program_id}: 有效程序账户 ({len(program_info.value.data)} 字节)")
                else:
                    print(f"❌ {program_id}: 无效程序账户")
                    
            except Exception as e:
                print(f"❌ {program_id}: 错误 - {e}")
                
    except Exception as e:
        print(f'错误: {e}')
    finally:
        await client.close()


async def main():
    """主函数"""
    print("🔍 分析Meteora池的实际数据结构和程序ID")
    print("=" * 60)
    
    await check_meteora_pool()
    await search_meteora_program_ids()
    
    print("\n🎯 分析完成！")


if __name__ == "__main__":
    asyncio.run(main())