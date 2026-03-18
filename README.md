# Sol Meme SDK

Python SDK for trading meme coins on Solana blockchain.

## Features

- **Wallet Management**: Create, import, and manage Solana wallets
- **Token Trading**: Buy and sell meme coins with market orders
- **Limit Orders**: Advanced limit order functionality with auto-execution
- **Price Monitoring**: Real-time price tracking and alerts
- **Market Data**: Real-time market data from Jupiter API
- **Transaction Management**: Robust transaction handling with retry logic
- **Risk Management**: Slippage control and balance checks
- **Jupiter Integration**: Seamless integration with Jupiter DEX aggregator
- **Order Persistence**: Orders persist across client restarts
- **Multi-Network Support**: Mainnet, Devnet, and Testnet support

## Installation

```bash
pip install sol-meme-sdk
```

## Quick Start

### Basic Usage

```python
import asyncio
from sol_meme_sdk import SolMemeClient, Network

async def main():
    # Initialize client with new wallet
    client = SolMemeClient(network=Network.DEVNET)
    
    # Connect to network
    await client.connect()
    
    # Get wallet information
    wallet_info = await client.get_wallet_info()
    print(f"Wallet address: {wallet_info['address']}")
    print(f"SOL balance: {wallet_info['balance_sol']:.6f}")
    
    # Get token information
    token_address = "So11111111111111111111111111111111111111112"  # Example token
    token_info = await client.get_token_info(token_address)
    print(f"Token: {token_info.symbol} - {token_info.name}")
    
    await client.close()

asyncio.run(main())
```

### Trading Example

```python
import asyncio
from sol_meme_sdk import SolMemeClient, Network

async def trade_example():
    client = SolMemeClient(
        network=Network.DEVNET,
        private_key="your_private_key_here"
    )
    
    await client.connect()
    
    # Buy token
    token_address = "TOKEN_MINT_ADDRESS"
    result = await client.buy_token(
        token_address=token_address,
        amount_sol=0.1,  # 0.1 SOL
        slippage=1.0    # 1% slippage
    )
    
    print(f"Bought {result.executed_amount} tokens")
    print(f"Transaction: {result.transaction_hash}")
    
    await client.close()

asyncio.run(trade_example())
```

### Advanced Trading with Limit Orders

```python
import asyncio
from sol_meme_sdk import SolMemeClient, Network

async def limit_order_example():
    client = SolMemeClient(
        network=Network.MAINNET,
        private_key="your_private_key_here"
    )
    
    await client.connect()
    
    # Place a limit buy order
    token_address = "TOKEN_MINT_ADDRESS"
    order_id = await client.place_limit_order(
        token_address=token_address,
        amount=1000.0,  # Buy 1000 tokens
        limit_price=0.01,  # When price drops to 0.01 SOL per token
        is_buy=True
    )
    
    print(f"Limit order placed: {order_id}")
    
    # Check order status
    order_status = await client.get_order_status(order_id)
    print(f"Order status: {order_status}")
    
    # Cancel order if needed
    # await client.cancel_order(order_id)
    
    await client.close()

asyncio.run(limit_order_example())
```

### Real-time Market Data

```python
import asyncio
from sol_meme_sdk import SolMemeClient, Network

async def market_data_example():
    client = SolMemeClient(network=Network.MAINNET)
    
    await client.connect()
    
    # Get real-time market data
    token_address = "TOKEN_MINT_ADDRESS"
    market_data = await client.get_market_data(token_address)
    
    print(f"Current Price: ${market_data['price']:.6f}")
    print(f"24h Volume: ${market_data['volume_24h']:,.2f}")
    print(f"24h Change: {market_data['price_change_24h']:+.2f}%")
    print(f"Liquidity: ${market_data['liquidity']:,.2f}")
    
    await client.close()

asyncio.run(market_data_example())
```

## API Reference

### SolMemeClient

Main client class for interacting with Solana blockchain.

#### Initialization

```python
client = SolMemeClient(
    network=Network.MAINNET,  # or Network.DEVNET, Network.TESTNET
    rpc_url=None,            # custom RPC URL
    private_key=None,        # wallet private key
    config=None              # transaction configuration
)
```

#### Core Methods

- `connect()`: Connect to Solana network and load pending orders
- `get_balance()`: Get wallet SOL balance
- `get_wallet_info()`: Get comprehensive wallet information
- `get_token_info(token_address)`: Get token metadata
- `buy_token(token_address, amount_sol, slippage)`: Buy tokens with SOL
- `sell_token(token_address, amount_tokens, slippage)`: Sell tokens for SOL
- `get_trade_history(limit)`: Get recent trade history
- `get_token_price(token_address)`: Get current token price
- `monitor_price(token_address, callback, interval)`: Monitor price changes

#### Advanced Trading Methods

- `get_market_data(token_address)`: Get real-time market data (price, volume, liquidity)
- `place_limit_order(token_address, amount, limit_price, is_buy)`: Place limit buy/sell order
- `cancel_order(order_id)`: Cancel pending limit order
- `get_order_status(order_id)`: Get current status of limit order
- `get_pending_orders()`: Get all pending limit orders

#### Jupiter Integration Methods

- `get_jupiter_quote(input_mint, output_mint, amount)`: Get quote from Jupiter API
- `search_tokens(query)`: Search for tokens using Jupiter API
- `get_swap_quote(token_address, amount)`: Get optimized swap quote

#### Portfolio Management

- `get_portfolio_value()`: Get total portfolio value in SOL
- `get_detailed_portfolio()`: Get detailed portfolio breakdown
- `get_portfolio_performance(period_hours)`: Get portfolio performance metrics

### Wallet Management

```python
from sol_meme_sdk import Wallet

# Create new wallet
wallet = Wallet()

# Create from private key
wallet = Wallet(private_key="base58_private_key")

# Create from mnemonic
wallet = Wallet.from_mnemonic("your mnemonic phrase")

# Export wallet
wallet_json = wallet.export_to_json(password="optional_password")
```

## Examples

Check the `examples/` directory for:
- `basic_usage.py`: Basic SDK functionality
- `trading_bot.py`: Simple trading bot implementation

## Configuration

### Transaction Configuration

```python
from sol_meme_sdk import TransactionConfig

config = TransactionConfig(
    max_retries=3,          # Maximum retry attempts
    retry_delay=1.0,        # Delay between retries (seconds)
    timeout=30.0,           # Transaction timeout (seconds)
    skip_preflight=False,   # Skip preflight checks
    commitment="confirmed"  # Blockchain commitment level
)
```

## Security Notes

⚠️ **Important Security Considerations:**

1. **Never share private keys**: Keep your private keys secure and never commit them to version control
2. **Use test networks**: Always test on devnet/testnet before using mainnet
3. **Start small**: Begin with small amounts to test functionality
4. **Monitor transactions**: Always verify transactions on blockchain explorers
5. **Use hardware wallets**: For large amounts, consider using hardware wallets

## Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/yourusername/sol-meme-sdk.git
cd sol-meme-sdk

# Install dependencies
pip install -e .[dev]

# Run tests
pytest

# Format code
black src/
isort src/
```

### Project Structure

```
sol-meme-sdk/
├── src/sol_meme_sdk/
│   ├── client.py          # Main client class
│   ├── wallet.py          # Wallet management
│   ├── trading.py         # Trading functionality
│   ├── models.py          # Data models
│   ├── exceptions.py      # Exception classes
│   └── utils.py           # Utility functions
├── examples/              # Usage examples
├── tests/                 # Test suite
└── pyproject.toml         # Project configuration
```

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This software is provided for educational and development purposes only. Cryptocurrency trading involves significant risk. Use this software at your own risk. The authors are not responsible for any financial losses incurred through the use of this software.

Always:
- Test thoroughly on test networks
- Understand the risks of cryptocurrency trading
- Never invest more than you can afford to lose
- Keep your private keys secure