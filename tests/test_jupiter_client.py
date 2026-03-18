"""
Tests for Jupiter client functionality
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from sol_meme_sdk.jupiter_client import JupiterClient
from sol_meme_sdk.exceptions import TradingError


class TestJupiterClient:
    """Test Jupiter client functionality"""
    
    @pytest.fixture
    def client(self):
        """Create test client with mock API key"""
        return JupiterClient(network="mainnet-beta", api_key="test_api_key")
    
    @pytest.mark.asyncio
    async def test_client_initialization(self, client):
        """Test client initialization"""
        assert client.network == "mainnet-beta"
        assert client.api_key == "test_api_key"
        assert client.base_url == "https://api.jup.ag"
        assert client.quote_endpoint == "/ultra/v1/order"
        assert client.swap_endpoint == "/ultra/v1/execute"
        assert client.tokens_endpoint == "/ultra/v1/search"
    
    @pytest.mark.asyncio
    async def test_get_quote_sol_to_usdc(self, client):
        """Test getting quote for SOL to USDC swap"""
        
        # Mock successful API response
        mock_response = {
            "inAmount": "1000000000",
            "outAmount": "100000000",
            "priceImpactPct": "0.1",
            "routePlan": [],
            "swapMode": "ExactIn"
        }
        
        with patch.object(client, '_make_api_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            quote = await client.get_quote(
                input_mint="So11111111111111111111111111111111111111112",
                output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                amount=1.0,
                slippage_bps=50
            )
            
            # Verify the API was called with correct parameters
            mock_request.assert_called_once()
            call_args = mock_request.call_args[0]
            assert call_args[0] == "/ultra/v1/order"
            
            params = call_args[1]
            assert params["inputMint"] == "So11111111111111111111111111111111111111112"
            assert params["outputMint"] == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
            assert params["amount"] == "1000000000"  # 1 SOL in lamports
            assert params["slippageBps"] == 50
            
            # Verify response
            assert quote == mock_response
    
    @pytest.mark.asyncio
    async def test_get_quote_with_taker(self, client):
        """Test getting quote with taker address"""
        
        mock_response = {
            "inAmount": "1000000000",
            "outAmount": "100000000",
            "priceImpactPct": "0.1"
        }
        
        with patch.object(client, '_make_api_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            taker_address = "BQ72nSv9f3PRyRKCBnHLVrerrv37CYTHm5h3s9VSGQDV"
            
            quote = await client.get_quote(
                input_mint="So11111111111111111111111111111111111111112",
                output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                amount=1.0,
                taker=taker_address
            )
            
            params = mock_request.call_args[0][1]
            assert params["taker"] == taker_address
    
    @pytest.mark.asyncio
    async def test_search_tokens(self, client):
        """Test token search functionality"""
        
        mock_response = [
            {
                "id": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
                "symbol": "JUP",
                "name": "Jupiter",
                "decimals": 6
            }
        ]
        
        with patch.object(client, '_make_api_request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            results = await client.search_tokens("JUP")
            
            mock_request.assert_called_once()
            call_args = mock_request.call_args[0]
            assert call_args[0] == "/ultra/v1/search"
            
            params = call_args[1]
            assert params["query"] == "JUP"
            assert params["limit"] == 20
            
            assert results == mock_response
    
    @pytest.mark.asyncio
    async def test_get_price_sol_to_usdc(self, client):
        """Test getting price for SOL to USDC"""
        
        mock_quote_response = {
            "outAmount": "100000000"  # 100 USDC for 1 SOL
        }
        
        with patch.object(client, 'get_quote', new_callable=AsyncMock) as mock_quote:
            mock_quote.return_value = mock_quote_response
            
            price = await client.get_price(
                input_mint="So11111111111111111111111111111111111111112",
                output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
            )
            
            # Verify get_quote was called with correct parameters
            mock_quote.assert_called_once_with(
                input_mint="So11111111111111111111111111111111111111112",
                output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                amount=1.0,
                slippage_bps=50,
                taker=None,
                restrict_intermediate_tokens=True
            )
            
            # Verify price calculation (100 USDC / 1 SOL = 100)
            assert price == 100.0
    
    @pytest.mark.asyncio
    async def test_get_token_price_usd(self, client):
        """Test getting token price in USD"""
        
        # Mock SOL to USDC price (100 USDC per SOL)
        mock_quote_response = {
            "outAmount": "100000000"  # 100 USDC for 1 SOL
        }
        
        with patch.object(client, 'get_quote', new_callable=AsyncMock) as mock_quote:
            mock_quote.return_value = mock_quote_response
            
            price = await client.get_token_price_usd("So11111111111111111111111111111111111111112")
            
            # Should return 100.0 (100 USDC per SOL)
            assert price == 100.0
    
    @pytest.mark.asyncio
    async def test_get_token_price_usd_for_usdc(self, client):
        """Test getting USD price for USDC (should be 1.0)"""
        
        price = await client.get_token_price_usd("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
        
        # USDC should always be 1.0
        assert price == 1.0
    
    @pytest.mark.asyncio
    async def test_api_error_handling(self, client):
        """Test API error handling"""
        
        with patch.object(client, '_make_api_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = TradingError("API Error")
            
            with pytest.raises(TradingError):
                await client.get_quote(
                    input_mint="So11111111111111111111111111111111111111112",
                    output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                    amount=1.0
                )
    
    @pytest.mark.asyncio
    async def test_network_support(self, client):
        """Test network support checks"""
        
        assert client.is_network_supported() is True
        assert client.is_devnet() is False
        
        # Test devnet client
        devnet_client = JupiterClient(network="devnet", api_key="test_api_key")
        assert devnet_client.is_devnet() is True
    
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check functionality"""
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_response
            
            healthy = await client.health_check()
            assert healthy is True
            
            # Test unhealthy scenario
            mock_response.status = 500
            healthy = await client.health_check()
            assert healthy is False


class TestJupiterClientIntegration:
    """Integration tests for Jupiter client (requires actual API key)"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_live_quote_retrieval(self):
        """Test live quote retrieval (requires API key)"""
        
        # Skip if no API key is available
        client = JupiterClient(network="mainnet-beta")
        
        if not client.api_key:
            pytest.skip("No Jupiter API key available for integration test")
        
        try:
            quote = await client.get_quote(
                input_mint="So11111111111111111111111111111111111111112",
                output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                amount=0.001,  # Small amount for testing
                slippage_bps=50
            )
            
            # Verify response structure
            assert "inAmount" in quote
            assert "outAmount" in quote
            assert "routePlan" in quote
            
            # Verify amounts are positive
            assert int(quote["inAmount"]) > 0
            assert int(quote["outAmount"]) > 0
            
        except TradingError as e:
            # API might be down or rate limited, log but don't fail
            print(f"Jupiter API error during integration test: {e}")
            pytest.skip("Jupiter API temporarily unavailable")


if __name__ == "__main__":
    pytest.main([__file__])