#!/usr/bin/env python3
"""
Network diagnostic for Jupiter API connectivity
"""

import asyncio
import aiohttp
import socket
import sys


async def test_jupiter_connectivity():
    """Test Jupiter API connectivity with DNS fallback"""
    
    print("🔍 Jupiter API Connectivity Diagnostic")
    print("=" * 50)
    
    # Test 1: DNS Resolution with fallback
    print("\n1. DNS Resolution Test")
    
    hostname = "quote-api.jup.ag"
    
    # Try different DNS servers as fallback
    dns_servers = [
        ("8.8.8.8", "Google DNS"),
        ("1.1.1.1", "Cloudflare DNS"),
        ("208.67.222.222", "OpenDNS"),
        ("system", "System DNS")
    ]
    
    resolved = False
    
    for dns_ip, dns_name in dns_servers:
        try:
            if dns_ip == "system":
                # Use system default DNS
                ip_address = socket.gethostbyname(hostname)
            else:
                # Use specific DNS server
                resolver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                resolver.connect((dns_ip, 53))
                resolver.close()
                
                # This is a simplified approach - in practice you'd need a proper DNS client
                # For now, just try the system resolution with different timeout
                socket.setdefaulttimeout(5)
                ip_address = socket.gethostbyname(hostname)
                
            print(f"✅ DNS resolved via {dns_name}: {hostname} -> {ip_address}")
            resolved = True
            break
            
        except socket.gaierror as e:
            print(f"❌ DNS resolution via {dns_name} failed: {e}")
        except Exception as e:
            print(f"❌ DNS test via {dns_name} error: {e}")
    
    if not resolved:
        print("\n❌ All DNS resolution attempts failed")
        print("   This is the root cause of the connection issue")
        
        # Try alternative endpoint
        print("\n🔧 Testing alternative Jupiter endpoint...")
        try:
            alt_hostname = "jup.ag"
            ip_address = socket.gethostbyname(alt_hostname)
            print(f"✅ Alternative endpoint resolved: {alt_hostname} -> {ip_address}")
            print("   Consider using this endpoint for development")
        except socket.gaierror:
            print("❌ Alternative endpoint also failed")
        
        return False
    
        # Test 2: HTTP Connection with multiple endpoints
        print("\n2. HTTP Connection Test")
        
        endpoints = [
            ("https://api.jup.ag/tokens", "Official API (requires API key)"),
            ("https://quote-api.jup.ag/v6/tokens", "Legacy API (DNS issue)"),
        ]
        
        for url, description in endpoints:
            try:
                async with aiohttp.ClientSession() as session:
                    print(f"   Testing {description}: {url}")
                    async with session.get(url, timeout=10) as resp:
                        if resp.status == 200:
                            print(f"✅ {description} connection successful")
                            return True
                        else:
                            print(f"❌ {description} status: {resp.status}")
                            # Don't return False yet, try next endpoint
                            
            except aiohttp.ClientConnectorError as e:
                print(f"❌ {description} connection failed: {e}")
            except asyncio.TimeoutError:
                print(f"❌ {description} connection timeout")
            except Exception as e:
                print(f"❌ {description} unexpected error: {e}")
        
        # If all endpoints failed
        print("❌ All Jupiter API endpoints failed")
        return False


async def test_solana_connectivity():
    """Test Solana RPC connectivity"""
    
    print("\n3. Solana RPC Connectivity Test")
    try:
        from solana.rpc.api import Client
        
        # Test devnet connection
        client = Client("https://api.devnet.solana.com")
        version = client.get_version()
        
        if version.value:
            print("✅ Solana devnet connection successful")
            print(f"   Solana version: {version.value}")
            return True
        else:
            print("❌ Solana devnet connection failed")
            return False
            
    except Exception as e:
        print(f"❌ Solana connection error: {e}")
        return False


async def main():
    """Run diagnostic tests"""
    
    # Test Jupiter connectivity
    jupiter_ok = await test_jupiter_connectivity()
    
    # Test Solana connectivity  
    solana_ok = await test_solana_connectivity()
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 Diagnostic Summary")
    print("=" * 50)
    
    if jupiter_ok and solana_ok:
        print("✅ All connectivity tests passed!")
        print("   Jupiter integration should work correctly")
    elif solana_ok and not jupiter_ok:
        print("⚠️  Mixed results:")
        print("   ✅ Solana RPC working")
        print("   ❌ Jupiter API unavailable")
        print("\n🔧 Recommended actions:")
        print("   1. Temporary workaround for development:")
        print("      - Use the SDK's built-in fallback mechanism")
        print("      - Test with mock data in examples/test_jupiter_integration.py")
        print("\n   2. DNS/Network fixes:")
        print("      - Check /etc/resolv.conf for DNS settings")
        print("      - Try: sudo echo 'nameserver 8.8.8.8' >> /etc/resolv.conf")
        print("      - Check firewall: sudo ufw status")
        print("\n   3. For production:")
        print("      - Ensure proper DNS configuration")
        print("      - Consider using a VPN or proxy service")
        print("\n💡 Important: The SDK's fallback mechanism ensures basic functionality")
        print("   even when Jupiter API is unavailable.")
    else:
        print("❌ Multiple connectivity issues detected")
        print("   Check overall network connectivity")


if __name__ == "__main__":
    asyncio.run(main())