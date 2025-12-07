"""
Quantitative Metrics Service

Provides advanced quantitative risk and volatility metrics for backtesting:
- Sortino Ratio: Downside deviation-based risk-adjusted returns
- Average True Range (ATR): Price volatility measurement
- Parkinson Volatility: High-low range-based volatility estimator
"""

import numpy as np
from typing import List, Optional, Union
import logging

logger = logging.getLogger(__name__)


def calculate_sortino_ratio(
    returns: Union[List[float], np.ndarray],
    risk_free_rate: float = 0.0,
    periods_per_year: float = 252.0
) -> float:
    """
    Calculate Sortino Ratio: annualized risk-adjusted return using downside deviation.
    
    The Sortino Ratio is similar to Sharpe Ratio but only penalizes downside volatility,
    making it more appropriate for strategies where upside volatility is desired.
    
    Formula:
        Sortino Ratio = (Annualized Mean Return - Risk-Free Rate) / Annualized Downside Deviation
        
        Where Downside Deviation = sqrt(mean(min(return - risk_free_rate, 0)^2))
        Annualization Factor = sqrt(periods_per_year)
    
    Args:
        returns: Array of period returns (e.g., daily returns as decimals: 0.05 = 5%)
        risk_free_rate: Risk-free rate for the period (default: 0.0)
        periods_per_year: Number of periods per year for annualization (default: 252 trading days)
    
    Returns:
        float: Annualized Sortino ratio. Higher is better.
               Returns float('inf') if positive returns with no downside risk.
               Returns 0.0 if calculation fails or insufficient data.
    
    Edge Cases:
        - Returns NaN, inf values → Filtered out before calculation
        - Empty array or < 2 returns → Returns 0.0
        - No downside deviation (all returns positive) → Returns float('inf') to indicate perfect upside
        - Zero downside deviation → Returns 0.0 to avoid division by zero
    
    Example:
        >>> returns = [0.02, -0.01, 0.03, -0.02, 0.01]
        >>> sortino = calculate_sortino_ratio(returns, risk_free_rate=0.0)
        >>> print(f"Sortino Ratio: {sortino:.2f}")
    """
    try:
        # Convert to numpy array and filter out NaN/inf
        returns_array = np.array(returns, dtype=float)
        returns_array = returns_array[np.isfinite(returns_array)]
        
        # Need at least 2 returns for meaningful calculation
        if len(returns_array) < 2:
            logger.warning(f"Insufficient data for Sortino ratio: {len(returns_array)} returns")
            return 0.0
        
        # Calculate mean return and annualize
        mean_return = np.mean(returns_array)
        annualized_return = mean_return * periods_per_year
        
        # Calculate downside deviation (only negative returns relative to risk-free rate)
        excess_returns = returns_array - risk_free_rate
        downside_returns = excess_returns[excess_returns < 0]
        
        # If no downside returns but positive mean return, Sortino is infinite (perfect upside)
        if len(downside_returns) == 0:
            if mean_return > risk_free_rate:
                logger.info("No downside returns with positive mean - Sortino ratio is infinite")
                # Cap at very high value for practical use
                return 999.99
            else:
                logger.info("No downside returns found, Sortino ratio undefined")
                return 0.0
        
        # Calculate downside semi-variance and semi-deviation
        downside_variance = np.mean(downside_returns ** 2)
        downside_deviation = np.sqrt(downside_variance)
        
        # Annualize downside deviation
        annualized_downside_deviation = downside_deviation * np.sqrt(periods_per_year)
        
        # Avoid division by zero
        if annualized_downside_deviation == 0 or not np.isfinite(annualized_downside_deviation):
            logger.warning("Zero or invalid annualized downside deviation")
            return 0.0
        
        # Calculate annualized Sortino ratio
        sortino_ratio = (annualized_return - risk_free_rate) / annualized_downside_deviation
        
        # Final validation
        if not np.isfinite(sortino_ratio):
            logger.warning(f"Non-finite Sortino ratio calculated: {sortino_ratio}")
            return 0.0
        
        return float(sortino_ratio)
    
    except Exception as e:
        logger.error(f"Error calculating Sortino ratio: {e}")
        return 0.0


def calculate_average_true_range(
    high: Union[List[float], np.ndarray],
    low: Union[List[float], np.ndarray],
    close: Union[List[float], np.ndarray]
) -> float:
    """
    Calculate Average True Range (ATR): measure of price volatility.
    
    ATR measures the average range of price movement, accounting for gaps.
    It's widely used in trading to assess volatility and set stop-loss levels.
    
    Formula:
        True Range = max(High - Low, |High - Close_prev|, |Low - Close_prev|)
        ATR = mean(True Range)
    
    Args:
        high: Array of high prices for each period
        low: Array of low prices for each period
        close: Array of close prices for each period
    
    Returns:
        float: Average True Range. Higher values indicate higher volatility.
               Returns 0.0 if calculation fails or insufficient data.
    
    Edge Cases:
        - Arrays of different lengths → Uses minimum length
        - NaN, inf values → Filtered out before calculation
        - Empty arrays or < 2 periods → Returns 0.0
        - First period has no previous close → Uses High - Low only
    
    Example:
        >>> high = [110, 115, 112, 118, 120]
        >>> low = [105, 108, 107, 110, 115]
        >>> close = [108, 112, 109, 116, 118]
        >>> atr = calculate_average_true_range(high, low, close)
        >>> print(f"ATR: {atr:.2f}")
    """
    try:
        # Convert to numpy arrays
        high_array = np.array(high, dtype=float)
        low_array = np.array(low, dtype=float)
        close_array = np.array(close, dtype=float)
        
        # Ensure all arrays have same length
        min_length = min(len(high_array), len(low_array), len(close_array))
        if min_length < 2:
            logger.warning(f"Insufficient data for ATR: {min_length} periods")
            return 0.0
        
        high_array = high_array[:min_length]
        low_array = low_array[:min_length]
        close_array = close_array[:min_length]
        
        # Calculate True Range for each period
        true_ranges = []
        
        for i in range(min_length):
            # Skip if any values are NaN or inf
            if not (np.isfinite(high_array[i]) and np.isfinite(low_array[i]) and np.isfinite(close_array[i])):
                continue
            
            # For first period, True Range is just High - Low
            if i == 0:
                tr = high_array[i] - low_array[i]
            else:
                # Skip if previous close is invalid
                if not np.isfinite(close_array[i - 1]):
                    tr = high_array[i] - low_array[i]
                else:
                    # True Range = max(H-L, |H-C_prev|, |L-C_prev|)
                    tr = max(
                        high_array[i] - low_array[i],
                        abs(high_array[i] - close_array[i - 1]),
                        abs(low_array[i] - close_array[i - 1])
                    )
            
            if np.isfinite(tr) and tr >= 0:
                true_ranges.append(tr)
        
        # Need at least 2 true range values
        if len(true_ranges) < 2:
            logger.warning(f"Insufficient valid true ranges: {len(true_ranges)}")
            return 0.0
        
        # Calculate average
        atr = np.mean(true_ranges)
        
        # Final validation
        if not np.isfinite(atr) or atr < 0:
            logger.warning(f"Invalid ATR calculated: {atr}")
            return 0.0
        
        return float(atr)
    
    except Exception as e:
        logger.error(f"Error calculating ATR: {e}")
        return 0.0


def calculate_parkinson_volatility(
    high: Union[List[float], np.ndarray],
    low: Union[List[float], np.ndarray],
    annualized: bool = True
) -> float:
    """
    Calculate Parkinson Volatility: efficient volatility estimator using high-low range.
    
    Parkinson's volatility estimator is more efficient than standard deviation because
    it uses the full high-low range rather than just close-to-close prices.
    It assumes continuous trading and geometric Brownian motion.
    
    Formula:
        Parkinson Vol = sqrt((1 / (4 * ln(2))) * mean((ln(High/Low))^2))
        
        With annualization (252 trading days):
        Annualized Vol = Parkinson Vol * sqrt(252)
    
    Args:
        high: Array of high prices for each period
        low: Array of low prices for each period
        annualized: If True, annualize the volatility (default: True)
    
    Returns:
        float: Parkinson volatility estimate (annualized if requested).
               Returns 0.0 if calculation fails or insufficient data.
    
    Edge Cases:
        - Arrays of different lengths → Uses minimum length
        - NaN, inf, or zero values → Filtered out before calculation
        - Empty arrays or < 2 periods → Returns 0.0
        - High <= Low → Skipped (invalid range)
        - High/Low ratio too extreme → Filtered via isfinite check
    
    Example:
        >>> high = [110, 115, 112, 118, 120]
        >>> low = [105, 108, 107, 110, 115]
        >>> vol = calculate_parkinson_volatility(high, low, annualized=True)
        >>> print(f"Parkinson Volatility: {vol:.4f}")
    """
    try:
        # Convert to numpy arrays
        high_array = np.array(high, dtype=float)
        low_array = np.array(low, dtype=float)
        
        # Ensure both arrays have same length
        min_length = min(len(high_array), len(low_array))
        if min_length < 2:
            logger.warning(f"Insufficient data for Parkinson volatility: {min_length} periods")
            return 0.0
        
        high_array = high_array[:min_length]
        low_array = low_array[:min_length]
        
        # Filter out invalid values and calculate log ratios
        log_hl_ratios_squared = []
        
        for i in range(min_length):
            # Skip if any values are NaN, inf, zero, or negative
            if not (np.isfinite(high_array[i]) and np.isfinite(low_array[i]) and 
                    high_array[i] > 0 and low_array[i] > 0):
                continue
            
            # Skip if high <= low (invalid range)
            if high_array[i] <= low_array[i]:
                continue
            
            # Calculate ln(High/Low)^2
            log_ratio = np.log(high_array[i] / low_array[i])
            
            if np.isfinite(log_ratio):
                log_hl_ratios_squared.append(log_ratio ** 2)
        
        # Need at least 2 valid ratios
        if len(log_hl_ratios_squared) < 2:
            logger.warning(f"Insufficient valid high/low ratios: {len(log_hl_ratios_squared)}")
            return 0.0
        
        # Parkinson's constant: 1 / (4 * ln(2))
        parkinson_constant = 1.0 / (4.0 * np.log(2.0))
        
        # Calculate variance estimate
        variance = parkinson_constant * np.mean(log_hl_ratios_squared)
        
        # Calculate volatility (standard deviation)
        volatility = np.sqrt(variance)
        
        # Annualize if requested (252 trading days per year)
        if annualized:
            volatility *= np.sqrt(252)
        
        # Final validation
        if not np.isfinite(volatility) or volatility < 0:
            logger.warning(f"Invalid Parkinson volatility calculated: {volatility}")
            return 0.0
        
        return float(volatility)
    
    except Exception as e:
        logger.error(f"Error calculating Parkinson volatility: {e}")
        return 0.0
