#!/usr/bin/env python3
"""
Simple trading bot example for Sol Meme SDK
"""

import asyncio
import time
from sol_meme_sdk import SolMemeClient, Network


class SimpleTradingBot:
    """Simple trading bot for meme coins"""
    
    def __init__(self, private_key: str, token_address: str):
        self.client = SolMemeClient(
            network=Network.DEVNET,
            private_key=private_key
        )
        self.token_address = token_address
        self.is_running = False
    
    async def start(self):
        """Start the trading bot"""
        await self.client.connect()
        self.is_running = True
        
        print("Trading bot started!")
        print(f"Monitoring token: {self.token_address}")
        
        # Start monitoring
        await self.monitor_and_trade()
    
    async def monitor_and_trade(self):
        """Monitor price and execute trades"""
        last_price = None
        
        while self.is_running:
            try:
                # Get current price
                current_price = await self.client.get_token_price(self.token_address)
                
                print(f"[{time.strftime('%H:%M:%S')}] Price: {current_price:.8f} SOL")
                
                # Simple trading logic
                if last_price is not None:
                    price_change = (current_price - last_price) / last_price
                    
                    if price_change < -0.05:  # 5% drop - buy
                        print("Price dropped 5% - Buying opportunity!")
                        await self.execute_buy(current_price)
                    
                    elif price_change > 0.10:  # 10% gain - sell
                        print("Price increased 10% - Selling opportunity!")
                        await self.execute_sell(current_price)
                
                last_price = current_price
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                print(f"Error in monitoring: {e}")
                await asyncio.sleep(5)
    
    async def execute_buy(self, price: float):
        """Execute buy order"""
        try:
            # Get balance
            balance = await self.client.get_balance()
            
            # Use 10% of balance for buy
            buy_amount = balance * 0.1
            
            if buy_amount > 0.001:  # Minimum 0.001 SOL
                print(f"Executing buy order: {buy_amount:.6f} SOL")
                
                result = await self.client.buy_token(
                    token_address=self.token_address,
                    amount_sol=buy_amount,
                    slippage=1.0
                )
                
                print(f"Buy order executed: {result.executed_amount:.2f} tokens")
                print(f"Transaction: {result.transaction_hash}")
            
        except Exception as e:
            print(f"Buy order failed: {e}")
    
    async def execute_sell(self, price: float):
        """Execute sell order"""
        try:
            # In real implementation, check token balance
            # For this example, we'll assume we have tokens
            print("Sell logic would check token balance and execute sell")
            
            # Example sell (commented out for safety)
            # result = await self.client.sell_token(
            #     token_address=self.token_address,
            #     amount_tokens=100.0,  # Example amount
            #     slippage=1.0
            # )
            
        except Exception as e:
            print(f"Sell order failed: {e}")
    
    async def stop(self):
        """Stop the trading bot"""
        self.is_running = False
        await self.client.close()
        print("Trading bot stopped!")


async def main():
    """Run the trading bot example"""
    
    # IMPORTANT: Replace with your actual private key and token address
    # Use devnet for testing!
    
    private_key = "YOUR_PRIVATE_KEY_HERE"  # Replace with actual private key
    token_address = "TOKEN_MINT_ADDRESS_HERE"  # Replace with actual token
    
    if private_key == "YOUR_PRIVATE_KEY_HERE":
        print("Please set your private key and token address in the code!")
        print("This example is for demonstration purposes only.")
        return
    
    bot = SimpleTradingBot(private_key, token_address)
    
    try:
        # Run for 2 minutes
        await bot.start()
        await asyncio.sleep(120)  # Run for 2 minutes
        await bot.stop()
        
    except KeyboardInterrupt:
        print("\nStopping bot...")
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())