"""
Basic tests for Sol Meme SDK
"""

import pytest
import asyncio
from sol_meme_sdk import SolMemeClient, Network, Wallet
from sol_meme_sdk.exceptions import WalletError, TradingError


class TestWallet:
    """Test wallet functionality"""
    
    def test_wallet_creation(self):
        """Test wallet creation"""
        wallet = Wallet()
        assert wallet.address is not None
        assert len(wallet.address) > 0
    
    def test_wallet_from_private_key(self):
        """Test wallet creation from private key"""
        # Create a wallet first to get a valid private key
        original_wallet = Wallet()
        private_key = original_wallet.get_private_key()
        
        # Create new wallet from private key
        new_wallet = Wallet(private_key=private_key)
        assert new_wallet.address == original_wallet.address
    
    def test_invalid_private_key(self):
        """Test invalid private key handling"""
        with pytest.raises(WalletError):
            Wallet(private_key="invalid_key")
    
    def test_wallet_export_import(self):
        """Test wallet export and import"""
        wallet = Wallet()
        
        # Export wallet
        wallet_json = wallet.export_to_json()
        assert "address" in wallet_json
        assert "private_key" in wallet_json
        
        # Import wallet
        imported_wallet = Wallet.import_from_json(wallet_json)
        assert imported_wallet.address == wallet.address


class TestClient:
    """Test client functionality"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return SolMemeClient(network=Network.DEVNET)
    
    @pytest.mark.asyncio
    async def test_client_initialization(self, client):
        """Test client initialization"""
        assert client.network == Network.DEVNET
        assert client.wallet is not None
        assert client.trading is not None
    
    @pytest.mark.asyncio
    async def test_connection(self, client):
        """Test network connection"""
        connected = await client.connect()
        assert connected is True
    
    @pytest.mark.asyncio
    async def test_get_balance(self, client):
        """Test balance retrieval"""
        await client.connect()
        balance = await client.get_balance()
        assert isinstance(balance, float)
        assert balance >= 0
    
    @pytest.mark.asyncio
    async def test_get_wallet_info(self, client):
        """Test wallet info retrieval"""
        await client.connect()
        wallet_info = await client.get_wallet_info()
        
        assert "address" in wallet_info
        assert "balance_sol" in wallet_info
        assert "tokens" in wallet_info
        
        assert wallet_info["address"] == client.wallet.address
        assert isinstance(wallet_info["balance_sol"], float)
        assert isinstance(wallet_info["tokens"], dict)


class TestTrading:
    """Test trading functionality"""
    
    @pytest.fixture
    def trading_engine(self):
        """Create test trading engine"""
        from solana.rpc.api import Client
        from sol_meme_sdk.trading import TradingEngine
        
        client = Client("https://api.devnet.solana.com")
        wallet = Wallet()
        
        return TradingEngine(client, wallet)
    
    @pytest.mark.asyncio
    async def test_token_info_retrieval(self, trading_engine):
        """Test token information retrieval"""
        # Test with SOL token address
        sol_address = "So11111111111111111111111111111111111111112"
        
        token_info = await trading_engine._get_token_info(sol_address)
        
        assert token_info["address"] == sol_address
        assert "decimals" in token_info
        assert "symbol" in token_info
    
    @pytest.mark.asyncio
    async def test_invalid_token_address(self, trading_engine):
        """Test invalid token address handling"""
        with pytest.raises(TradingError):
            await trading_engine._get_token_info("invalid_address")
    
    @pytest.mark.asyncio
    async def test_price_calculation(self, trading_engine):
        """Test price calculation"""
        sol_address = "So11111111111111111111111111111111111111112"
        
        price = await trading_engine._get_token_price(sol_address)
        assert isinstance(price, float)
        assert price >= 0


class TestUtils:
    """Test utility functions"""
    
    def test_sol_to_lamports(self):
        """Test SOL to lamports conversion"""
        from sol_meme_sdk.utils import sol_to_lamports, lamports_to_sol
        
        # Test conversion
        sol_amount = 1.5
        lamports = sol_to_lamports(sol_amount)
        assert lamports == 1500000000
        
        # Test reverse conversion
        converted_sol = lamports_to_sol(lamports)
        assert abs(converted_sol - sol_amount) < 0.000001
    
    def test_slippage_calculation(self):
        """Test slippage calculation"""
        from sol_meme_sdk.utils import calculate_slippage_amount
        
        amount = 100.0
        slippage = 1.0  # 1%
        
        min_amount, max_amount = calculate_slippage_amount(amount, slippage)
        
        assert min_amount == 99.0
        assert max_amount == 101.0
    
    def test_address_validation(self):
        """Test Solana address validation"""
        from sol_meme_sdk.utils import validate_solana_address
        
        # Valid address
        valid_address = "So11111111111111111111111111111111111111112"
        assert validate_solana_address(valid_address) is True
        
        # Invalid address
        invalid_address = "invalid_address"
        assert validate_solana_address(invalid_address) is False


if __name__ == "__main__":
    pytest.main([__file__])