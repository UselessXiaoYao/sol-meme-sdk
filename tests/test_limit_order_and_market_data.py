"""
Test file for limit order and market data functionality
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from sol_meme_sdk.client import SolMemeClient
from sol_meme_sdk.models import Network, TransactionConfig
from sol_meme_sdk.exceptions import SolMemeError


class TestLimitOrderAndMarketData:
    """Test limit order and market data functionality"""
    
    @pytest.fixture
    def client(self):
        """Create test client with mock setup"""
        # Use a test private key for testing
        test_private_key = "4Z7qL7J2V8z9w3y6x5v4b3n2m1l0k9j8h7g6f5d4s3a2q1w0e9r8t7y6u5i4o3p"
        return SolMemeClient(
            network=Network.DEVNET,  # Use devnet for testing
            private_key=test_private_key,
            config=TransactionConfig()
        )
    
    @pytest.mark.asyncio
    async def test_get_market_data_real_time(self, client):
        """Test getting real-time market data"""
        # Mock Jupiter API responses
        mock_quote_response = {
            "outAmount": "100000000",  # 100 USDC
            "priceImpactPct": "0.1"
        }
        
        with patch.object(client.jupiter_client, 'get_quote', new_callable=AsyncMock) as mock_quote:
            mock_quote.return_value = mock_quote_response
            
            # Test token address (USDC)
            token_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
            
            market_data = await client.get_market_data(token_address)
            
            # Verify the API was called
            mock_quote.assert_called_once()
            
            # Verify response structure
            assert "token_address" in market_data
            assert "price" in market_data
            assert "volume_24h" in market_data
            assert "price_change_24h" in market_data
            assert "liquidity" in market_data
            assert "market_cap" in market_data
            assert "timestamp" in market_data
            
            # Verify data types
            assert isinstance(market_data["price"], float)
            assert isinstance(market_data["volume_24h"], float)
            assert isinstance(market_data["price_change_24h"], float)
            assert isinstance(market_data["liquidity"], float)
    
    @pytest.mark.asyncio
    async def test_place_limit_order_buy(self, client):
        """Test placing a buy limit order"""
        # Mock Jupiter API responses
        mock_quote_response = {
            "outAmount": "500000000",  # 500 tokens
            "priceImpactPct": "0.1"
        }
        
        mock_swap_response = {
            "swapTransaction": "test_transaction_data",
            "fee": "10000"
        }
        
        with patch.object(client.jupiter_client, 'get_quote', new_callable=AsyncMock) as mock_quote,\
             patch.object(client.jupiter_client, 'get_swap_transaction', new_callable=AsyncMock) as mock_swap,\
             patch.object(client, '_execute_transaction', new_callable=AsyncMock) as mock_execute:
            
            mock_quote.return_value = mock_quote_response
            mock_swap.return_value = mock_swap_response
            mock_execute.return_value = {"fee": 0.001}
            
            # Test token address
            token_address = "So11111111111111111111111111111111111111112"  # SOL
            
            result = await client.place_limit_order(
                token_address=token_address,
                side="buy",
                amount=10.0,  # Buy 10 SOL
                price=100.0,  # At 100 USDC per SOL
                slippage=0.5
            )
            
            # Verify API calls
            mock_quote.assert_called_once()
            mock_swap.assert_called_once()
            mock_execute.assert_called_once()
            
            # Verify result
            assert result.success is True
            assert result.amount == 10.0
            assert result.price == 100.0
            assert result.status == "completed"
    
    @pytest.mark.asyncio
    async def test_place_limit_order_sell(self, client):
        """Test placing a sell limit order"""
        # Mock Jupiter API responses for sell order
        mock_quote_response = {
            "outAmount": "1000000000",  # 1000 USDC
            "priceImpactPct": "0.1"
        }
        
        mock_swap_response = {
            "swapTransaction": "test_transaction_data",
            "fee": "10000"
        }
        
        with patch.object(client.jupiter_client, 'get_quote', new_callable=AsyncMock) as mock_quote,\
             patch.object(client.jupiter_client, 'get_swap_transaction', new_callable=AsyncMock) as mock_swap,\
             patch.object(client, '_execute_transaction', new_callable=AsyncMock) as mock_execute:
            
            mock_quote.return_value = mock_quote_response
            mock_swap.return_value = mock_swap_response
            mock_execute.return_value = {"fee": 0.001}
            
            # Test token address
            token_address = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC
            
            result = await client.place_limit_order(
                token_address=token_address,
                side="sell",
                amount=1000.0,  # Sell 1000 USDC
                price=1.0,  # At 1 SOL per USDC
                slippage=0.5
            )
            
            # Verify API calls
            mock_quote.assert_called_once()
            mock_swap.assert_called_once()
            mock_execute.assert_called_once()
            
            # Verify result
            assert result.success is True
            assert result.amount == 1000.0
            assert result.price == 1.0
            assert result.status == "completed"
    
    @pytest.mark.asyncio
    async def test_place_limit_order_pending(self, client):
        """Test placing a limit order that goes to pending status"""
        # Mock quote response with price that doesn't meet limit
        mock_quote_response = {
            "outAmount": "900000000",  # 900 tokens (price not met)
            "priceImpactPct": "0.1"
        }
        
        with patch.object(client.jupiter_client, 'get_quote', new_callable=AsyncMock) as mock_quote:
            mock_quote.return_value = mock_quote_response
            
            token_address = "So11111111111111111111111111111111111111112"  # SOL
            
            result = await client.place_limit_order(
                token_address=token_address,
                side="buy",
                amount=10.0,
                price=95.0,  # Limit price
                slippage=0.5
            )
            
            # Verify order was placed as pending
            assert result.success is True
            assert result.status == "pending"
            assert result.amount == 0.0  # Not executed yet
            assert result.order_id.startswith("limit_")
            
            # Verify order is in pending orders
            assert result.order_id in client._pending_orders
            
            pending_order = client._pending_orders[result.order_id]
            assert pending_order["token_address"] == token_address
            assert pending_order["side"] == "buy"
            assert pending_order["amount"] == 10.0
            assert pending_order["price"] == 95.0
    
    @pytest.mark.asyncio
    async def test_cancel_order(self, client):
        """Test cancelling a pending order"""
        # First place a pending order
        mock_quote_response = {
            "outAmount": "900000000",  # Price not met
            "priceImpactPct": "0.1"
        }
        
        with patch.object(client.jupiter_client, 'get_quote', new_callable=AsyncMock) as mock_quote:
            mock_quote.return_value = mock_quote_response
            
            token_address = "So11111111111111111111111111111111111111112"
            
            result = await client.place_limit_order(
                token_address=token_address,
                side="buy",
                amount=10.0,
                price=95.0,
                slippage=0.5
            )
            
            order_id = result.order_id
            
            # Now cancel the order
            cancellation_result = await client.cancel_order(order_id)
            
            assert cancellation_result is True
            
            # Verify order is no longer in pending orders
            assert order_id not in client._pending_orders
    
    @pytest.mark.asyncio
    async def test_get_order_status(self, client):
        """Test getting order status"""
        # Place a pending order
        mock_quote_response = {
            "outAmount": "900000000",  # Price not met
            "priceImpactPct": "0.1"
        }
        
        with patch.object(client.jupiter_client, 'get_quote', new_callable=AsyncMock) as mock_quote,\
             patch.object(client, 'get_token_price', new_callable=AsyncMock) as mock_price:
            
            mock_quote.return_value = mock_quote_response
            mock_price.return_value = 100.0  # Current price higher than limit
            
            token_address = "So11111111111111111111111111111111111111112"
            
            result = await client.place_limit_order(
                token_address=token_address,
                side="buy",
                amount=10.0,
                price=95.0,  # Limit price
                slippage=0.5
            )
            
            order_id = result.order_id
            
            # Get order status
            status = await client.get_order_status(order_id)
            
            # Verify status structure
            assert "order_id" in status
            assert "status" in status
            assert "token_address" in status
            assert "side" in status
            assert "amount" in status
            assert "price" in status
            assert "current_price" in status
            assert "filled_amount" in status
            assert "remaining_amount" in status
            assert "created_at" in status
            assert "age_seconds" in status
            
            # Verify specific values
            assert status["order_id"] == order_id
            assert status["token_address"] == token_address
            assert status["side"] == "buy"
            assert status["amount"] == 10.0
            assert status["price"] == 95.0
            assert status["current_price"] == 100.0
            
            # Since current price (100) > limit price (95), order should be pending
            assert status["status"] == "pending"
    
    @pytest.mark.asyncio
    async def test_get_order_status_executable(self, client):
        """Test getting order status for executable order"""
        # Place a pending order
        mock_quote_response = {
            "outAmount": "900000000",  # Price not met
            "priceImpactPct": "0.1"
        }
        
        with patch.object(client.jupiter_client, 'get_quote', new_callable=AsyncMock) as mock_quote,\
             patch.object(client, 'get_token_price', new_callable=AsyncMock) as mock_price:
            
            mock_quote.return_value = mock_quote_response
            mock_price.return_value = 90.0  # Current price lower than limit
            
            token_address = "So11111111111111111111111111111111111111112"
            
            result = await client.place_limit_order(
                token_address=token_address,
                side="buy",
                amount=10.0,
                price=95.0,  # Limit price
                slippage=0.5
            )
            
            order_id = result.order_id
            
            # Get order status
            status = await client.get_order_status(order_id)
            
            # Since current price (90) < limit price (95), order should be executable
            assert status["status"] == "executable"
    
    @pytest.mark.asyncio
    async def test_cancel_nonexistent_order(self, client):
        """Test cancelling an order that doesn't exist"""
        with pytest.raises(SolMemeError):
            await client.cancel_order("nonexistent_order_id")
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_order_status(self, client):
        """Test getting status for an order that doesn't exist"""
        status = await client.get_order_status("nonexistent_order_id")
        
        assert status["status"] == "not_found"
        assert status["filled_amount"] == 0.0
        assert status["remaining_amount"] == 0.0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])