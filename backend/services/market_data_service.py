"""
Market Data Service for fetching beta, ATR, and SPY returns.

Provides cached market data to enhance event scoring with:
- Beta: Stock volatility vs market (60-day rolling)
- ATR Percentile: Recent volatility vs historical (14-day ATR vs 200-day distribution)
- SPY Returns: Market regime detection (1d, 5d, 20d returns)

All data cached for 24 hours to avoid rate limits.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

import pandas as pd

logger = logging.getLogger(__name__)

# In-memory cache with 24h TTL
_CACHE: Dict[str, Dict] = {}
_CACHE_TTL_HOURS = 24


class MarketDataService:
    """Service for fetching market data with caching."""
    
    def __init__(self):
        """Initialize market data service."""
        self._ensure_yfinance()
    
    def _ensure_yfinance(self):
        """Ensure yfinance is available, log warning if not."""
        try:
            import yfinance as yf
            self.yf = yf
            self.yfinance_available = True
        except ImportError:
            logger.warning(
                "yfinance not available. Market data features will be disabled. "
                "Install with: pip install yfinance"
            )
            self.yf = None
            self.yfinance_available = False
    
    def _get_cached(self, key: str) -> Optional[any]:
        """Get cached value if not expired."""
        if key in _CACHE:
            entry = _CACHE[key]
            if datetime.utcnow() < entry["expires_at"]:
                logger.debug(f"Cache hit for {key}")
                return entry["value"]
            else:
                del _CACHE[key]
                logger.debug(f"Cache expired for {key}")
        return None
    
    def _set_cache(self, key: str, value: any):
        """Set cached value with 24h TTL."""
        _CACHE[key] = {
            "value": value,
            "expires_at": datetime.utcnow() + timedelta(hours=_CACHE_TTL_HOURS)
        }
        logger.debug(f"Cached {key} for {_CACHE_TTL_HOURS}h")
    
    def get_beta(self, ticker: str) -> Optional[float]:
        """
        Calculate 60-day beta (stock returns vs SPY).
        
        Beta measures stock volatility relative to the market:
        - β > 1.5: High volatility (amplifies market moves)
        - 0.8 ≤ β ≤ 1.2: Average volatility
        - β < 0.8: Low volatility (defensive)
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            Beta value (typically 0.5-2.0), or None if unavailable
        """
        if not self.yfinance_available:
            return None
        
        cache_key = f"beta_{ticker}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        
        try:
            # Fetch 90 days of data to compute 60-day beta
            stock = self.yf.Ticker(ticker)
            spy = self.yf.Ticker("SPY")
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=90)
            
            # Get historical prices
            stock_hist = stock.history(start=start_date, end=end_date)
            spy_hist = spy.history(start=start_date, end=end_date)
            
            if stock_hist.empty or spy_hist.empty:
                logger.warning(f"No historical data for {ticker} or SPY")
                self._set_cache(cache_key, None)
                return None
            
            # Calculate daily returns
            stock_returns = stock_hist['Close'].pct_change().dropna()
            spy_returns = spy_hist['Close'].pct_change().dropna()
            
            # Align dates and take last 60 days
            aligned = pd.concat([stock_returns, spy_returns], axis=1, join='inner')
            aligned.columns = ['stock', 'spy']
            aligned = aligned.tail(60)
            
            if len(aligned) < 30:
                logger.warning(f"Insufficient data for {ticker} beta (only {len(aligned)} days)")
                self._set_cache(cache_key, None)
                return None
            
            # Calculate beta using covariance
            covariance = aligned['stock'].cov(aligned['spy'])
            variance = aligned['spy'].var()
            
            if variance == 0:
                logger.warning(f"Zero variance for SPY, cannot calculate beta for {ticker}")
                self._set_cache(cache_key, None)
                return None
            
            beta = covariance / variance
            
            # Sanity check: beta should typically be in range [-2, 5]
            if beta < -2 or beta > 5:
                logger.warning(f"Unusual beta value for {ticker}: {beta:.2f}")
            
            self._set_cache(cache_key, beta)
            logger.info(f"Calculated beta for {ticker}: {beta:.2f}")
            return beta
            
        except Exception as e:
            logger.warning(f"Failed to calculate beta for {ticker}: {e}")
            self._set_cache(cache_key, None)
            return None
    
    def get_atr_percentile(self, ticker: str) -> Optional[float]:
        """
        Calculate ATR percentile (14-day ATR vs 200-day distribution).
        
        Average True Range (ATR) measures recent volatility:
        - Percentile > 80: Very high recent volatility
        - Percentile 50-80: Elevated volatility
        - Percentile < 50: Normal/low volatility
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            ATR percentile (0-100), or None if unavailable
        """
        if not self.yfinance_available:
            return None
        
        cache_key = f"atr_percentile_{ticker}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        
        try:
            # Fetch 250 days of data to compute 200-day ATR distribution
            stock = self.yf.Ticker(ticker)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=250)
            
            hist = stock.history(start=start_date, end=end_date)
            
            if hist.empty or len(hist) < 50:
                logger.warning(f"Insufficient historical data for {ticker} ATR")
                self._set_cache(cache_key, None)
                return None
            
            # Calculate True Range
            high = hist['High']
            low = hist['Low']
            close = hist['Close']
            prev_close = close.shift(1)
            
            tr1 = high - low
            tr2 = abs(high - prev_close)
            tr3 = abs(low - prev_close)
            
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            # Calculate 14-day ATR
            atr_14 = true_range.rolling(window=14).mean()
            
            if atr_14.isna().all():
                logger.warning(f"Could not calculate ATR for {ticker}")
                self._set_cache(cache_key, None)
                return None
            
            # Get current ATR (most recent 14-day)
            current_atr = atr_14.iloc[-1]
            
            # Calculate percentile relative to 200-day distribution
            atr_200 = atr_14.dropna().tail(200)
            
            if len(atr_200) < 50:
                logger.warning(f"Insufficient ATR history for {ticker} percentile")
                self._set_cache(cache_key, None)
                return None
            
            percentile = (atr_200 < current_atr).sum() / len(atr_200) * 100
            
            self._set_cache(cache_key, percentile)
            logger.info(f"Calculated ATR percentile for {ticker}: {percentile:.1f}")
            return percentile
            
        except Exception as e:
            logger.warning(f"Failed to calculate ATR percentile for {ticker}: {e}")
            self._set_cache(cache_key, None)
            return None
    
    def get_spy_returns(self) -> Optional[Dict[str, float]]:
        """
        Fetch SPY returns for market regime detection.
        
        Returns dict with:
        - "1d": 1-day return
        - "5d": 5-day return  
        - "20d": 20-day return
        
        Used to detect market conditions:
        - Bull market: 5d > 2%, 20d > 5%
        - Bear market: 5d < -2%, 20d < -5%
        - Neutral: Otherwise
        
        Returns:
            Dict of {"1d": float, "5d": float, "20d": float}, or None if unavailable
        """
        if not self.yfinance_available:
            return None
        
        cache_key = "spy_returns"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        
        try:
            spy = self.yf.Ticker("SPY")
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            hist = spy.history(start=start_date, end=end_date)
            
            if hist.empty or len(hist) < 20:
                logger.warning("Insufficient SPY data for returns calculation")
                self._set_cache(cache_key, None)
                return None
            
            close = hist['Close']
            
            # Calculate returns
            returns = {
                "1d": (close.iloc[-1] / close.iloc[-2] - 1) if len(close) >= 2 else 0.0,
                "5d": (close.iloc[-1] / close.iloc[-6] - 1) if len(close) >= 6 else 0.0,
                "20d": (close.iloc[-1] / close.iloc[-21] - 1) if len(close) >= 21 else 0.0,
            }
            
            self._set_cache(cache_key, returns)
            logger.info(f"Calculated SPY returns: 1d={returns['1d']:.3f}, 5d={returns['5d']:.3f}, 20d={returns['20d']:.3f}")
            return returns
            
        except Exception as e:
            logger.warning(f"Failed to calculate SPY returns: {e}")
            self._set_cache(cache_key, None)
            return None
    
    def clear_cache(self):
        """Clear all cached data. Useful for testing or forced refresh."""
        _CACHE.clear()
        logger.info("Market data cache cleared")
    
    def get_market_regime(self, spy_returns: Optional[Dict[str, float]] = None) -> str:
        """
        Determine market regime from SPY returns.
        
        Args:
            spy_returns: Dict with 1d, 5d, 20d returns (fetched if None)
        
        Returns:
            "bull", "bear", or "neutral"
        """
        if spy_returns is None:
            spy_returns = self.get_spy_returns()
        
        if spy_returns is None:
            return "neutral"
        
        # Bull market: strong recent gains
        if spy_returns["5d"] > 0.02 and spy_returns["20d"] > 0.05:
            return "bull"
        
        # Bear market: significant recent losses
        if spy_returns["5d"] < -0.02 and spy_returns["20d"] < -0.05:
            return "bear"
        
        # Mixed or sideways
        return "neutral"
