"""
Options Data Service for fetching implied volatility from yfinance.

Provides methods to fetch ATM implied volatility, IV term structure,
and put/call ratio for sentiment analysis and feature enrichment.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, NamedTuple
from functools import lru_cache

import numpy as np

from releaseradar.log_config import logger


class OptionsData(NamedTuple):
    """Container for options-derived data."""
    implied_volatility_atm: Optional[float]  # ATM IV annualized
    iv_percentile_30d: Optional[float]  # IV rank vs 30-day history
    put_call_ratio: Optional[float]  # P/C ratio
    iv_skew: Optional[float]  # Put IV - Call IV at same delta
    days_to_nearest_expiry: Optional[int]
    has_options_data: bool
    fetched_at: datetime


class IVTermStructure(NamedTuple):
    """Implied volatility term structure."""
    ticker: str
    iv_1m: Optional[float]  # ~30 day expiry
    iv_2m: Optional[float]  # ~60 day expiry
    iv_3m: Optional[float]  # ~90 day expiry
    term_slope: Optional[float]  # (iv_3m - iv_1m) / iv_1m if available
    fetched_at: datetime


class OptionsDataCache:
    """Simple TTL cache for options data."""
    
    def __init__(self, ttl_seconds: int = 3600):
        self.ttl = ttl_seconds
        self._cache: Dict[str, tuple] = {}  # ticker -> (data, timestamp)
    
    def get(self, ticker: str) -> Optional[OptionsData]:
        if ticker not in self._cache:
            return None
        
        data, timestamp = self._cache[ticker]
        if time.time() - timestamp > self.ttl:
            del self._cache[ticker]
            return None
        
        return data
    
    def set(self, ticker: str, data: OptionsData) -> None:
        self._cache[ticker] = (data, time.time())
    
    def clear(self) -> None:
        self._cache.clear()


class OptionsDataService:
    """
    Service for fetching options-implied volatility data from yfinance.
    
    Provides ATM implied volatility, term structure, and put/call ratio
    for feature enrichment in the ML pipeline.
    
    Caches results with 1-hour TTL to avoid rate limiting.
    """
    
    def __init__(self, cache_ttl_seconds: int = 3600):
        """
        Initialize options data service.
        
        Args:
            cache_ttl_seconds: Cache TTL in seconds (default 1 hour)
        """
        self._cache = OptionsDataCache(ttl_seconds=cache_ttl_seconds)
        self._iv_history: Dict[str, List[tuple]] = {}
    
    def get_atm_implied_volatility(self, ticker: str) -> Optional[float]:
        """
        Get at-the-money implied volatility for a ticker.
        
        ATM is defined as the strike closest to the current stock price.
        Returns annualized IV from nearest expiration options.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            ATM implied volatility (annualized, e.g., 0.30 for 30%) or None
        """
        data = self.get_options_data(ticker)
        return data.implied_volatility_atm if data and data.has_options_data else None
    
    def get_options_data(self, ticker: str, force_refresh: bool = False) -> OptionsData:
        """
        Get comprehensive options data for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            force_refresh: If True, bypass cache
            
        Returns:
            OptionsData with IV, P/C ratio, and other metrics
        """
        if not force_refresh:
            cached = self._cache.get(ticker)
            if cached:
                return cached
        
        try:
            import yfinance as yf
            
            stock = yf.Ticker(ticker)
            
            current_price = self._get_current_price(stock)
            if current_price is None:
                logger.debug(f"Could not get current price for {ticker}")
                return self._empty_options_data()
            
            expirations = stock.options
            if not expirations:
                logger.debug(f"No options data available for {ticker}")
                return self._empty_options_data()
            
            nearest_expiry = expirations[0]
            days_to_expiry = self._days_until_expiry(nearest_expiry)
            
            try:
                chain = stock.option_chain(nearest_expiry)
            except Exception as e:
                logger.debug(f"Failed to get option chain for {ticker}: {e}")
                return self._empty_options_data()
            
            calls = chain.calls
            puts = chain.puts
            
            if calls.empty or puts.empty:
                logger.debug(f"Empty option chain for {ticker}")
                return self._empty_options_data()
            
            atm_iv = self._calculate_atm_iv(calls, puts, current_price)
            put_call_ratio = self._calculate_put_call_ratio(calls, puts)
            iv_skew = self._calculate_iv_skew(calls, puts, current_price)
            iv_percentile = self._calculate_iv_percentile(ticker, atm_iv)
            
            data = OptionsData(
                implied_volatility_atm=atm_iv,
                iv_percentile_30d=iv_percentile,
                put_call_ratio=put_call_ratio,
                iv_skew=iv_skew,
                days_to_nearest_expiry=days_to_expiry,
                has_options_data=True,
                fetched_at=datetime.utcnow()
            )
            
            self._cache.set(ticker, data)
            
            if atm_iv is not None:
                self._update_iv_history(ticker, atm_iv)
            
            return data
            
        except ImportError:
            logger.warning("yfinance not installed, cannot fetch options data")
            return self._empty_options_data()
        except Exception as e:
            logger.warning(f"Failed to fetch options data for {ticker}: {e}")
            return self._empty_options_data()
    
    def get_iv_term_structure(self, ticker: str) -> IVTermStructure:
        """
        Get implied volatility term structure for a ticker.
        
        Returns IV for ~1m, ~2m, ~3m expirations to show term structure slope.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            IVTermStructure with IVs at different expirations
        """
        try:
            import yfinance as yf
            
            stock = yf.Ticker(ticker)
            current_price = self._get_current_price(stock)
            
            if current_price is None:
                return IVTermStructure(
                    ticker=ticker,
                    iv_1m=None, iv_2m=None, iv_3m=None,
                    term_slope=None,
                    fetched_at=datetime.utcnow()
                )
            
            expirations = stock.options
            if not expirations:
                return IVTermStructure(
                    ticker=ticker,
                    iv_1m=None, iv_2m=None, iv_3m=None,
                    term_slope=None,
                    fetched_at=datetime.utcnow()
                )
            
            today = datetime.now().date()
            target_days = [30, 60, 90]
            ivs = {}
            
            for target in target_days:
                target_date = today + timedelta(days=target)
                closest_expiry = min(
                    expirations,
                    key=lambda x: abs((datetime.strptime(x, "%Y-%m-%d").date() - target_date).days)
                )
                
                try:
                    chain = stock.option_chain(closest_expiry)
                    iv = self._calculate_atm_iv(chain.calls, chain.puts, current_price)
                    ivs[target] = iv
                except Exception:
                    ivs[target] = None
            
            term_slope = None
            if ivs.get(30) and ivs.get(90) and ivs[30] > 0:
                term_slope = (ivs[90] - ivs[30]) / ivs[30]
            
            return IVTermStructure(
                ticker=ticker,
                iv_1m=ivs.get(30),
                iv_2m=ivs.get(60),
                iv_3m=ivs.get(90),
                term_slope=term_slope,
                fetched_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.warning(f"Failed to get IV term structure for {ticker}: {e}")
            return IVTermStructure(
                ticker=ticker,
                iv_1m=None, iv_2m=None, iv_3m=None,
                term_slope=None,
                fetched_at=datetime.utcnow()
            )
    
    def get_put_call_ratio(self, ticker: str) -> Optional[float]:
        """
        Get put/call ratio for a ticker.
        
        High P/C ratio (>1) suggests bearish sentiment.
        Low P/C ratio (<1) suggests bullish sentiment.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Put/Call volume ratio or None if unavailable
        """
        data = self.get_options_data(ticker)
        return data.put_call_ratio if data and data.has_options_data else None
    
    def _get_current_price(self, stock) -> Optional[float]:
        """Get current stock price."""
        try:
            info = stock.info
            price = info.get("regularMarketPrice") or info.get("currentPrice")
            if price:
                return float(price)
            
            hist = stock.history(period="1d")
            if not hist.empty:
                return float(hist["Close"].iloc[-1])
            
            return None
        except Exception:
            return None
    
    def _calculate_atm_iv(self, calls, puts, current_price: float) -> Optional[float]:
        """Calculate ATM implied volatility."""
        try:
            call_strikes = calls["strike"].values
            atm_idx = np.abs(call_strikes - current_price).argmin()
            
            call_iv = calls.iloc[atm_idx]["impliedVolatility"]
            
            put_strikes = puts["strike"].values
            put_atm_idx = np.abs(put_strikes - current_price).argmin()
            put_iv = puts.iloc[put_atm_idx]["impliedVolatility"]
            
            if np.isnan(call_iv) and np.isnan(put_iv):
                return None
            elif np.isnan(call_iv):
                return float(put_iv)
            elif np.isnan(put_iv):
                return float(call_iv)
            else:
                return float((call_iv + put_iv) / 2)
            
        except Exception:
            return None
    
    def _calculate_put_call_ratio(self, calls, puts) -> Optional[float]:
        """Calculate put/call volume ratio."""
        try:
            call_volume = calls["volume"].sum()
            put_volume = puts["volume"].sum()
            
            if call_volume == 0 or np.isnan(call_volume):
                return None
            
            return float(put_volume / call_volume)
        except Exception:
            return None
    
    def _calculate_iv_skew(self, calls, puts, current_price: float) -> Optional[float]:
        """Calculate IV skew (OTM put IV - OTM call IV)."""
        try:
            otm_put_strike = current_price * 0.95
            otm_call_strike = current_price * 1.05
            
            put_idx = np.abs(puts["strike"].values - otm_put_strike).argmin()
            call_idx = np.abs(calls["strike"].values - otm_call_strike).argmin()
            
            put_iv = puts.iloc[put_idx]["impliedVolatility"]
            call_iv = calls.iloc[call_idx]["impliedVolatility"]
            
            if np.isnan(put_iv) or np.isnan(call_iv):
                return None
            
            return float(put_iv - call_iv)
        except Exception:
            return None
    
    def _days_until_expiry(self, expiry_str: str) -> int:
        """Calculate days until expiration."""
        try:
            expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").date()
            today = datetime.now().date()
            return (expiry_date - today).days
        except Exception:
            return 0
    
    def _update_iv_history(self, ticker: str, iv: float) -> None:
        """Update IV history for percentile calculation."""
        if ticker not in self._iv_history:
            self._iv_history[ticker] = []
        
        self._iv_history[ticker].append((datetime.utcnow(), iv))
        
        cutoff = datetime.utcnow() - timedelta(days=30)
        self._iv_history[ticker] = [
            (t, v) for t, v in self._iv_history[ticker]
            if t > cutoff
        ]
    
    def _calculate_iv_percentile(self, ticker: str, current_iv: Optional[float]) -> Optional[float]:
        """Calculate IV percentile vs 30-day history."""
        if current_iv is None:
            return None
        
        history = self._iv_history.get(ticker, [])
        if len(history) < 5:
            return 50.0
        
        ivs = [v for _, v in history]
        below_count = sum(1 for v in ivs if v < current_iv)
        
        return float(below_count / len(ivs) * 100)
    
    def _empty_options_data(self) -> OptionsData:
        """Return empty options data object."""
        return OptionsData(
            implied_volatility_atm=None,
            iv_percentile_30d=None,
            put_call_ratio=None,
            iv_skew=None,
            days_to_nearest_expiry=None,
            has_options_data=False,
            fetched_at=datetime.utcnow()
        )
    
    def clear_cache(self) -> None:
        """Clear the options data cache."""
        self._cache.clear()
        logger.info("Options data cache cleared")


_options_service_instance: Optional[OptionsDataService] = None


def get_options_service() -> OptionsDataService:
    """Get singleton instance of OptionsDataService."""
    global _options_service_instance
    if _options_service_instance is None:
        _options_service_instance = OptionsDataService()
    return _options_service_instance
