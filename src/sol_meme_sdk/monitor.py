"""
Market monitoring and price alert system for Sol Meme SDK
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum

from .exceptions import TradingError

logger = logging.getLogger(__name__)


class AlertType(str, Enum):
    """Alert types"""
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    PRICE_CHANGE = "price_change"
    VOLUME_SPIKE = "volume_spike"
    LIQUIDITY_CHANGE = "liquidity_change"


@dataclass
class AlertConfig:
    """Alert configuration"""
    alert_type: AlertType
    token_address: str
    threshold: float
    enabled: bool = True
    cooldown: float = 300.0  # 5 minutes cooldown
    last_triggered: float = 0.0


class PriceMonitor:
    """Real-time price and market data monitor"""
    
    def __init__(self, trading_engine):
        self.trading_engine = trading_engine
        self.monitored_tokens: Dict[str, Dict] = {}
        self.price_history: Dict[str, List[float]] = {}
        self.alerts: List[AlertConfig] = []
        self.callbacks: List[Callable] = []
        self.running = False
        self.history_length = 100  # Keep last 100 price points
    
    def add_monitored_token(self, token_address: str, interval: float = 5.0):
        """Add a token to monitor"""
        self.monitored_tokens[token_address] = {
            'interval': interval,
            'last_check': 0,
            'current_price': 0,
            'price_history': []
        }
        self.price_history[token_address] = []
        logger.info(f"Added token to monitor: {token_address}")
    
    def remove_monitored_token(self, token_address: str):
        """Remove a token from monitoring"""
        if token_address in self.monitored_tokens:
            del self.monitored_tokens[token_address]
            del self.price_history[token_address]
            logger.info(f"Removed token from monitor: {token_address}")
    
    def add_alert(self, alert_config: AlertConfig):
        """Add a price alert"""
        self.alerts.append(alert_config)
        logger.info(f"Added alert: {alert_config.alert_type} for {alert_config.token_address}")
    
    def add_callback(self, callback: Callable):
        """Add a callback function for price changes"""
        self.callbacks.append(callback)
        logger.info("Added price change callback")
    
    async def start(self):
        """Start monitoring"""
        self.running = True
        logger.info(f"Price monitor started for {len(self.monitored_tokens)} tokens")
        
        while self.running:
            try:
                await self._check_prices()
                await self._check_alerts()
                await asyncio.sleep(1.0)  # Check every second
            except Exception as e:
                logger.error(f"Price monitoring error: {e}")
                await asyncio.sleep(5.0)
    
    async def stop(self):
        """Stop monitoring"""
        self.running = False
        logger.info("Price monitor stopped")
    
    async def _check_prices(self):
        """Check prices for all monitored tokens"""
        current_time = time.time()
        
        for token_address, config in self.monitored_tokens.items():
            if current_time - config['last_check'] >= config['interval']:
                try:
                    # Get current price
                    price = await self.trading_engine._get_token_price(token_address)
                    
                    # Update price history
                    self._update_price_history(token_address, price)
                    
                    # Check for significant price changes
                    await self._check_price_changes(token_address, price)
                    
                    # Update config
                    config['last_check'] = current_time
                    config['current_price'] = price
                    
                    logger.debug(f"Price update: {token_address} = {price} SOL")
                    
                except Exception as e:
                    logger.error(f"Failed to get price for {token_address}: {e}")
    
    def _update_price_history(self, token_address: str, price: float):
        """Update price history for a token"""
        if token_address not in self.price_history:
            self.price_history[token_address] = []
        
        self.price_history[token_address].append(price)
        
        # Keep only last N price points
        if len(self.price_history[token_address]) > self.history_length:
            self.price_history[token_address].pop(0)
    
    async def _check_price_changes(self, token_address: str, current_price: float):
        """Check for significant price changes and trigger callbacks"""
        history = self.price_history.get(token_address, [])
        
        if len(history) >= 2:
            previous_price = history[-2] if len(history) >= 2 else history[0]
            
            if previous_price > 0:  # Avoid division by zero
                change_percent = ((current_price - previous_price) / previous_price) * 100
                
                # Trigger callbacks for significant changes (>1%)
                if abs(change_percent) > 1.0:
                    for callback in self.callbacks:
                        try:
                            await callback(token_address, current_price, previous_price, change_percent)
                        except Exception as e:
                            logger.error(f"Callback error: {e}")
    
    async def _check_alerts(self):
        """Check all configured alerts"""
        current_time = time.time()
        
        for alert in self.alerts:
            if not alert.enabled:
                continue
            
            # Check cooldown
            if current_time - alert.last_triggered < alert.cooldown:
                continue
            
            try:
                # Get current price
                price = await self.trading_engine._get_token_price(alert.token_address)
                
                # Check alert condition
                triggered = False
                
                if alert.alert_type == AlertType.PRICE_ABOVE and price > alert.threshold:
                    triggered = True
                elif alert.alert_type == AlertType.PRICE_BELOW and price < alert.threshold:
                    triggered = True
                elif alert.alert_type == AlertType.PRICE_CHANGE:
                    # This would require more sophisticated logic
                    pass
                
                if triggered:
                    await self._trigger_alert(alert, price)
                    alert.last_triggered = current_time
                    
            except Exception as e:
                logger.error(f"Alert check failed for {alert.token_address}: {e}")
    
    async def _trigger_alert(self, alert: AlertConfig, current_price: float):
        """Trigger an alert"""
        alert_message = f"ALERT: {alert.token_address} {alert.alert_type.value} threshold {alert.threshold}. Current price: {current_price}"
        logger.info(alert_message)
        
        # In production, this would send notifications (email, SMS, etc.)
        # For now, just log the alert
        print(f"🚨 {alert_message}")
    
    def get_price_history(self, token_address: str) -> List[float]:
        """Get price history for a token"""
        return self.price_history.get(token_address, [])
    
    def get_current_price(self, token_address: str) -> Optional[float]:
        """Get current price for a token"""
        if token_address in self.monitored_tokens:
            return self.monitored_tokens[token_address].get('current_price')
        return None
    
    def get_price_stats(self, token_address: str) -> Dict[str, float]:
        """Get price statistics for a token"""
        history = self.price_history.get(token_address, [])
        
        if not history:
            return {}
        
        return {
            'current': history[-1] if history else 0,
            'min': min(history) if history else 0,
            'max': max(history) if history else 0,
            'average': sum(history) / len(history) if history else 0,
            'volatility': self._calculate_volatility(history)
        }
    
    def _calculate_volatility(self, prices: List[float]) -> float:
        """Calculate price volatility"""
        if len(prices) < 2:
            return 0.0
        
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                returns.append((prices[i] - prices[i-1]) / prices[i-1])
        
        if not returns:
            return 0.0
        
        import statistics
        return statistics.stdev(returns) * 100  # As percentage


class PortfolioMonitor:
    """Portfolio value and performance monitor"""
    
    def __init__(self, client):
        self.client = client
        self.portfolio_history: List[Dict] = []
        self.max_history = 1000  # Keep last 1000 portfolio snapshots
    
    async def track_portfolio(self, interval: float = 60.0):
        """Start tracking portfolio value"""
        logger.info("Portfolio tracking started")
        
        while True:
            try:
                portfolio_value = await self._calculate_portfolio_value()
                
                snapshot = {
                    'timestamp': time.time(),
                    'total_value': portfolio_value,
                    'sol_balance': await self.client.get_balance(),
                    'token_values': await self._get_token_values()
                }
                
                self.portfolio_history.append(snapshot)
                
                # Keep history manageable
                if len(self.portfolio_history) > self.max_history:
                    self.portfolio_history.pop(0)
                
                logger.debug(f"Portfolio snapshot: {portfolio_value} SOL")
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Portfolio tracking error: {e}")
                await asyncio.sleep(interval)
    
    async def _calculate_portfolio_value(self) -> float:
        """Calculate total portfolio value"""
        try:
            # Get SOL balance
            sol_balance = await self.client.get_balance()
            
            # Get token values (simplified)
            token_values = await self._get_token_values()
            
            total_token_value = sum(token_values.values())
            
            return sol_balance + total_token_value
            
        except Exception as e:
            logger.error(f"Portfolio calculation error: {e}")
            return 0.0
    
    async def _get_token_values(self) -> Dict[str, float]:
        """Get current values of all tokens in portfolio"""
        try:
            # This would query token balances and current prices
            # Simplified implementation
            return {}
        except Exception as e:
            logger.error(f"Token value calculation error: {e}")
            return {}
    
    def get_portfolio_performance(self, period_hours: int = 24) -> Dict[str, float]:
        """Get portfolio performance over specified period"""
        if not self.portfolio_history:
            return {}
        
        current_time = time.time()
        period_start = current_time - (period_hours * 3600)
        
        # Filter history for the period
        period_history = [
            snap for snap in self.portfolio_history 
            if snap['timestamp'] >= period_start
        ]
        
        if not period_history:
            return {}
        
        start_value = period_history[0]['total_value']
        end_value = period_history[-1]['total_value']
        
        if start_value > 0:
            return_percent = ((end_value - start_value) / start_value) * 100
        else:
            return_percent = 0.0
        
        return {
            'start_value': start_value,
            'end_value': end_value,
            'return_percent': return_percent,
            'period_hours': period_hours
        }