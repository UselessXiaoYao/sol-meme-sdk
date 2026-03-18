"""
Advanced trading strategies for Sol Meme SDK
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from decimal import Decimal

from .models import TradeOrder, TradeResult, OrderSide, OrderType
from .exceptions import TradingError

logger = logging.getLogger(__name__)


class StrategyType(str, Enum):
    """Trading strategy types"""
    MARKET_MAKER = "market_maker"
    ARBITRAGE = "arbitrage"
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"


@dataclass
class StrategyConfig:
    """Strategy configuration"""
    strategy_type: StrategyType
    enabled: bool = True
    max_position_size: float = 0.1  # Max 10% of portfolio per trade
    stop_loss: float = 0.05  # 5% stop loss
    take_profit: float = 0.1  # 10% take profit
    max_daily_trades: int = 10
    cooldown_period: float = 60.0  # 60 seconds between trades


class BaseStrategy(ABC):
    """Base class for all trading strategies"""
    
    def __init__(self, trading_engine, config: StrategyConfig):
        self.trading_engine = trading_engine
        self.config = config
        self.last_trade_time = 0
        self.today_trades = 0
        self.last_trade_day = time.localtime().tm_yday
        
    def _can_trade(self) -> bool:
        """Check if trading is allowed based on limits"""
        current_time = time.time()
        current_day = time.localtime().tm_yday
        
        # Reset daily counter if new day
        if current_day != self.last_trade_day:
            self.today_trades = 0
            self.last_trade_day = current_day
        
        # Check daily limit
        if self.today_trades >= self.config.max_daily_trades:
            logger.info("Daily trade limit reached")
            return False
        
        # Check cooldown period
        if current_time - self.last_trade_time < self.config.cooldown_period:
            logger.info("In cooldown period")
            return False
        
        return True
    
    async def execute_trade(self, order: TradeOrder) -> Optional[TradeResult]:
        """Execute trade with strategy constraints"""
        if not self._can_trade():
            return None
        
        try:
            if order.side == OrderSide.BUY:
                result = await self.trading_engine.buy_token(
                    order.token_address, order.amount, order.slippage
                )
            else:
                result = await self.trading_engine.sell_token(
                    order.token_address, order.amount, order.slippage
                )
            
            self.last_trade_time = time.time()
            self.today_trades += 1
            
            logger.info(f"Strategy trade executed: {order.side} {order.amount} {order.token_address}")
            return result
            
        except Exception as e:
            logger.error(f"Strategy trade failed: {e}")
            return None
    
    @abstractmethod
    async def analyze(self, token_address: str, market_data: Dict[str, Any]) -> Optional[TradeOrder]:
        """Analyze market and generate trade signals"""
        pass


class MarketMakerStrategy(BaseStrategy):
    """Market making strategy for providing liquidity"""
    
    def __init__(self, trading_engine, config: StrategyConfig):
        super().__init__(trading_engine, config)
        self.spread = 0.01  # 1% spread
        self.position_size = 0.01  # 1% of portfolio per position
    
    async def analyze(self, token_address: str, market_data: Dict[str, Any]) -> Optional[TradeOrder]:
        """Market making analysis"""
        try:
            current_price = market_data.get('price', 0)
            volume = market_data.get('volume_24h', 0)
            liquidity = market_data.get('liquidity', 0)
            
            # Simple market making logic
            if volume > 1000 and liquidity > 100:  # Arbitrary thresholds
                # Calculate bid and ask prices
                bid_price = current_price * (1 - self.spread/2)
                ask_price = current_price * (1 + self.spread/2)
                
                # For now, use market orders
                # In real implementation, would create limit orders
                if current_price < bid_price:
                    return TradeOrder(
                        token_address=token_address,
                        side=OrderSide.BUY,
                        order_type=OrderType.MARKET,
                        amount=self.position_size,
                        slippage=0.5
                    )
                elif current_price > ask_price:
                    return TradeOrder(
                        token_address=token_address,
                        side=OrderSide.SELL,
                        order_type=OrderType.MARKET,
                        amount=self.position_size,
                        slippage=0.5
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Market maker analysis failed: {e}")
            return None


class TrendFollowingStrategy(BaseStrategy):
    """Trend following strategy"""
    
    def __init__(self, trading_engine, config: StrategyConfig):
        super().__init__(trading_engine, config)
        self.price_history: Dict[str, List[float]] = {}
        self.lookback_period = 20  # Number of periods to look back
    
    async def analyze(self, token_address: str, market_data: Dict[str, Any]) -> Optional[TradeOrder]:
        """Trend following analysis"""
        try:
            current_price = market_data.get('price', 0)
            
            # Initialize price history
            if token_address not in self.price_history:
                self.price_history[token_address] = []
            
            # Add current price to history
            self.price_history[token_address].append(current_price)
            
            # Keep only lookback_period prices
            if len(self.price_history[token_address]) > self.lookback_period:
                self.price_history[token_address].pop(0)
            
            # Calculate moving averages
            if len(self.price_history[token_address]) >= self.lookback_period:
                prices = self.price_history[token_address]
                short_ma = sum(prices[-5:]) / 5  # 5-period MA
                long_ma = sum(prices) / len(prices)  # Full-period MA
                
                # Trend following logic
                if short_ma > long_ma and prices[-1] > short_ma:  # Uptrend
                    return TradeOrder(
                        token_address=token_address,
                        side=OrderSide.BUY,
                        order_type=OrderType.MARKET,
                        amount=self.config.max_position_size,
                        slippage=0.5
                    )
                elif short_ma < long_ma and prices[-1] < short_ma:  # Downtrend
                    return TradeOrder(
                        token_address=token_address,
                        side=OrderSide.SELL,
                        order_type=OrderType.MARKET,
                        amount=self.config.max_position_size,
                        slippage=0.5
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Trend following analysis failed: {e}")
            return None


class StrategyManager:
    """Manager for multiple trading strategies"""
    
    def __init__(self, trading_engine):
        self.trading_engine = trading_engine
        self.strategies: Dict[str, BaseStrategy] = {}
        self.monitored_tokens: List[str] = []  # List of tokens to monitor
        self.running = False
    
    def add_strategy(self, name: str, strategy: BaseStrategy):
        """Add a trading strategy"""
        self.strategies[name] = strategy
        logger.info(f"Added strategy: {name}")
    
    def remove_strategy(self, name: str):
        """Remove a trading strategy"""
        if name in self.strategies:
            del self.strategies[name]
            logger.info(f"Removed strategy: {name}")
    
    def add_monitored_token(self, token_address: str):
        """Add a token to monitor for strategies"""
        if token_address not in self.monitored_tokens:
            self.monitored_tokens.append(token_address)
            logger.info(f"Added token to strategy monitoring: {token_address}")
    
    def remove_monitored_token(self, token_address: str):
        """Remove a token from strategy monitoring"""
        if token_address in self.monitored_tokens:
            self.monitored_tokens.remove(token_address)
            logger.info(f"Removed token from strategy monitoring: {token_address}")
    
    async def start(self, interval: float = 30.0):
        """Start strategy execution"""
        self.running = True
        logger.info(f"Strategy manager started with {len(self.strategies)} strategies")
        
        while self.running:
            try:
                await self._execute_strategies()
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Strategy execution error: {e}")
                await asyncio.sleep(interval)
    
    async def stop(self):
        """Stop strategy execution"""
        self.running = False
        logger.info("Strategy manager stopped")
    
    async def _execute_strategies(self):
        """Execute all strategies for monitored tokens"""
        if not self.monitored_tokens:
            logger.warning("No tokens being monitored for strategies")
            return
            
        for token_address in self.monitored_tokens:
            for name, strategy in self.strategies.items():
                if not strategy.config.enabled:
                    continue
                
                try:
                    # Get market data for the specific token
                    market_data = await self.trading_engine.client.get_market_data(token_address)
                    
                    # Analyze and generate trade signal for this token
                    trade_order = await strategy.analyze(token_address, market_data)
                    
                    if trade_order:
                        # Execute the trade
                        await strategy.execute_trade(trade_order)
                        
                except Exception as e:
                    logger.error(f"Strategy {name} execution failed for {token_address}: {e}")