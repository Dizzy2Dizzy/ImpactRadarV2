import pandas as pd
import yfinance as yf
from datetime import timedelta
from typing import Optional


def get_window_returns(
    ticker: str,
    benchmark: str,
    event_date: pd.Timestamp,
    horizon_days: int,
) -> Optional[float]:
    """
    Returns abnormal return R (in percent) over [event_date, event_date + horizon_days].
    R = (stock_return) - (benchmark_return)
    Returns None if data is unavailable.
    """
    try:
        start_date = event_date
        end_date = event_date + timedelta(days=horizon_days + 5)  # buffer for weekends
        
        # Fetch stock data
        stock = yf.Ticker(ticker)
        stock_df = stock.history(start=start_date, end=end_date)
        
        # Fetch benchmark data
        bench = yf.Ticker(benchmark)
        bench_df = bench.history(start=start_date, end=end_date)
        
        if len(stock_df) < 2 or len(bench_df) < 2:
            return None
            
        # Get prices at start and after horizon
        stock_start = stock_df.iloc[0]['Close']
        stock_end = stock_df.iloc[min(horizon_days, len(stock_df)-1)]['Close']
        
        bench_start = bench_df.iloc[0]['Close']
        bench_end = bench_df.iloc[min(horizon_days, len(bench_df)-1)]['Close']
        
        # Calculate returns
        stock_return = ((stock_end / stock_start) - 1.0) * 100.0
        bench_return = ((bench_end / bench_start) - 1.0) * 100.0
        
        # Abnormal return
        abnormal_return = stock_return - bench_return
        return abnormal_return
        
    except Exception:
        return None
