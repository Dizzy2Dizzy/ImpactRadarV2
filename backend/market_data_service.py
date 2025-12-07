"""
MarketDataService - Efficient OHLCV data fetching with caching
"""
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
from functools import lru_cache

_market_data_service_instance = None

def get_market_data_service() -> 'MarketDataService':
    """Get singleton instance of MarketDataService with persistent cache"""
    global _market_data_service_instance
    if _market_data_service_instance is None:
        _market_data_service_instance = MarketDataService()
    return _market_data_service_instance

class MarketDataService:
    def __init__(self):
        self._cache = {}  # In-memory cache for OHLCV data
        
    def get_ohlcv(
        self, 
        ticker: str, 
        interval: str = '1d',  # 1m, 5m, 15m, 30m, 1h, 1d, 1w
        period: str = '1mo',  # 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Fetch OHLCV data with caching.
        Returns list of dicts with: time, open, high, low, close, volume
        """
        cache_key = f"{ticker}_{interval}_{period}_{start_date}_{end_date}"
        
        # Check cache (60 second TTL for intraday, 5 min for daily+)
        if cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            ttl = 60 if interval in ['1m', '5m', '15m', '30m', '1h'] else 300
            if (datetime.now() - cached_time).total_seconds() < ttl:
                return cached_data
        
        # Fetch from yfinance
        try:
            ticker_obj = yf.Ticker(ticker)
            
            if start_date and end_date:
                df = ticker_obj.history(start=start_date, end=end_date, interval=interval)
            else:
                df = ticker_obj.history(period=period, interval=interval)
            
            if df.empty:
                return []
            
            # Convert to lightweight charts format
            data = []
            for index, row in df.iterrows():
                data.append({
                    'time': int(index.timestamp()),  # Unix timestamp
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
                    'volume': int(row['Volume'])
                })
            
            # Cache result
            self._cache[cache_key] = (data, datetime.now())
            return data
            
        except Exception as e:
            print(f"Error fetching OHLCV for {ticker}: {e}")
            return []
    
    def calculate_sma(self, prices: List[float], period: int) -> List[Optional[float]]:
        """Calculate Simple Moving Average"""
        if len(prices) < period:
            return [None] * len(prices)
        
        sma = []
        for i in range(len(prices)):
            if i < period - 1:
                sma.append(None)
            else:
                sma.append(sum(prices[i-period+1:i+1]) / period)
        return sma
    
    def calculate_ema(self, prices: List[float], period: int) -> List[Optional[float]]:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return [None] * len(prices)
        
        multiplier = 2 / (period + 1)
        ema = [None] * (period - 1)
        ema.append(sum(prices[:period]) / period)  # First EMA is SMA
        
        for i in range(period, len(prices)):
            ema.append((prices[i] - ema[-1]) * multiplier + ema[-1])
        
        return ema
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> List[Optional[float]]:
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return [None] * len(prices)
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        # Calculate initial averages
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        rsi = []
        
        # First period - prepend Nones for the prices before we have enough data
        for _ in range(period):
            rsi.append(None)
        
        # First RSI value
        if avg_loss == 0:
            rsi.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi.append(100 - (100 / (1 + rs)))
        
        # Subsequent RSI values
        for i in range(period, len(deltas)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            
            if avg_loss == 0:
                rsi.append(100.0)
            else:
                rs = avg_gain / avg_loss
                rsi.append(100 - (100 / (1 + rs)))
        
        return rsi
    
    def calculate_macd(
        self, 
        prices: List[float], 
        fast_period: int = 12, 
        slow_period: int = 26, 
        signal_period: int = 9
    ) -> Tuple[List[Optional[float]], List[Optional[float]], List[Optional[float]]]:
        """
        Calculate MACD (Moving Average Convergence Divergence)
        Returns: (macd_line, signal_line, histogram)
        """
        ema_fast = self.calculate_ema(prices, fast_period)
        ema_slow = self.calculate_ema(prices, slow_period)
        
        # MACD line = EMA(12) - EMA(26)
        macd_line = []
        for i in range(len(prices)):
            if ema_fast[i] is None or ema_slow[i] is None:
                macd_line.append(None)
            else:
                macd_line.append(ema_fast[i] - ema_slow[i])
        
        # Signal line = EMA(9) of MACD line
        macd_values_only = [v for v in macd_line if v is not None]
        if len(macd_values_only) < signal_period:
            signal_line = [None] * len(prices)
            histogram = [None] * len(prices)
        else:
            signal_line = self.calculate_ema(macd_values_only, signal_period)
            # Pad signal line with Nones to match length
            none_count = len(prices) - len(signal_line)
            signal_line = [None] * none_count + signal_line
            
            # Histogram = MACD - Signal
            histogram = []
            for i in range(len(prices)):
                if macd_line[i] is None or signal_line[i] is None:
                    histogram.append(None)
                else:
                    histogram.append(macd_line[i] - signal_line[i])
        
        return (macd_line, signal_line, histogram)
