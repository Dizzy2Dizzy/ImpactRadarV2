"""
Nightly price backfill job using Yahoo Finance.

Fetches historical OHLCV data for all tracked companies and stores in price_history table.
Handles deduplication and incremental updates.
"""

import os
import sys
from datetime import datetime, timedelta
from typing import List, Optional

import yfinance as yf
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from releaseradar.db.models import Company, PriceHistory
from releaseradar.db.session import get_db_context, get_db_transaction
from releaseradar.log_config import logger
from releaseradar.services.quality_metrics import QualityMetricsService


def fetch_price_data(ticker: str, start_date: datetime, end_date: datetime) -> List[dict]:
    """
    Fetch historical price data from Yahoo Finance.
    
    Args:
        ticker: Stock ticker symbol
        start_date: Start date for historical data
        end_date: End date for historical data
        
    Returns:
        List of dictionaries with OHLCV data
    """
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(start=start_date, end=end_date)
        
        if df.empty:
            logger.warning(f"No price data available for {ticker}")
            return []
        
        # Convert DataFrame to list of dicts
        prices = []
        for date_idx, row in df.iterrows():
            prices.append({
                "ticker": ticker,
                "date": date_idx.date(),
                "open": float(row["Open"]),
                "close": float(row["Close"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "volume": int(row["Volume"]),
                "source": os.getenv("PRICE_SOURCE", "yahoo"),
            })
        
        logger.info(f"Fetched {len(prices)} price records for {ticker}")
        return prices
        
    except Exception as e:
        logger.error(f"Failed to fetch prices for {ticker}: {e}")
        return []


def backfill_prices(
    tickers: Optional[List[str]] = None,
    days_back: int = 365,
    force: bool = False
) -> dict:
    """
    Backfill historical prices for specified tickers or all tracked companies.
    
    Args:
        tickers: List of tickers to backfill (None = all tracked companies)
        days_back: Number of days of history to fetch
        force: If True, refetch existing data
        
    Returns:
        Statistics about the backfill operation
    """
    with get_db_transaction() as db:
        # Record pipeline run start
        quality_service = QualityMetricsService(db)
        started_at = datetime.utcnow()
        pipeline_run = quality_service.record_pipeline_run(
            job_name="fetch_prices",
            started_at=started_at,
            status="running"
        )
        
        stats = {
            "tickers_processed": 0,
            "records_inserted": 0,
            "records_updated": 0,
            "errors": 0,
        }
        
        # Get tickers to process
        if tickers is None:
            # Fetch all tracked companies
            result = db.execute(
                select(Company.ticker).where(Company.tracked == True)
            )
            tickers = [row[0] for row in result]
            logger.info(f"Processing {len(tickers)} tracked companies")
        
        end_date = datetime.now()
        base_start_date_dt = end_date - timedelta(days=days_back)
        
        for ticker in tickers:
            try:
                # Determine start date for this ticker (keep as datetime for yfinance)
                ticker_start_dt = base_start_date_dt
                
                # Check for existing data unless force=True
                if not force:
                    existing = db.execute(
                        select(PriceHistory.date)
                        .where(PriceHistory.ticker == ticker)
                        .order_by(PriceHistory.date.desc())
                        .limit(1)
                    ).first()
                    
                    if existing:
                        # Only fetch data after the most recent date
                        # Convert date to datetime for consistent comparison
                        last_date = existing[0]  # This is a date object
                        ticker_start_dt = datetime.combine(last_date, datetime.min.time()) + timedelta(days=1)
                        
                        if ticker_start_dt.date() >= end_date.date():
                            logger.info(f"{ticker}: already up to date")
                            continue
                
                # Fetch price data
                prices = fetch_price_data(ticker, ticker_start_dt, end_date)
                
                if not prices:
                    stats["errors"] += 1
                    continue
                
                # Upsert prices (insert or update on conflict)
                for price_data in prices:
                    stmt = insert(PriceHistory).values(price_data)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["ticker", "date"],
                        set_={
                            "open": stmt.excluded.open,
                            "close": stmt.excluded.close,
                            "high": stmt.excluded.high,
                            "low": stmt.excluded.low,
                            "volume": stmt.excluded.volume,
                        }
                    )
                    db.execute(stmt)
                    stats["records_inserted"] += 1
                
                db.commit()
                stats["tickers_processed"] += 1
                logger.info(f"✓ {ticker}: {len(prices)} records backfilled")
                
            except Exception as e:
                logger.error(f"Error processing {ticker}: {e}")
                db.rollback()
                stats["errors"] += 1
                continue
        
        logger.info(f"Backfill complete: {stats}")
        
        # Update pipeline run status
        completed_at = datetime.utcnow()
        final_status = "success" if stats["errors"] == 0 else "failure"
        quality_service.update_pipeline_run(
            run_id=pipeline_run.id,
            status=final_status,
            completed_at=completed_at,
            rows_written=stats["records_inserted"]
        )
        
        # Record quality snapshot if successful
        if final_status == "success" and stats["records_inserted"] > 0:
            # Determine quality grade based on freshness
            hours_since_start = (completed_at - started_at).total_seconds() / 3600
            if hours_since_start < 1:
                quality_grade = "excellent"
            elif hours_since_start < 6:
                quality_grade = "good"
            else:
                quality_grade = "fair"
            
            quality_service.record_quality_snapshot(
                metric_key="prices_backfill",
                scope="global",
                sample_count=stats["records_inserted"],
                freshness_ts=completed_at,
                source_job="fetch_prices",
                quality_grade=quality_grade,
                summary_json={
                    "tickers_processed": stats["tickers_processed"],
                    "days_back": days_back,
                    "runtime_hours": round(hours_since_start, 2),
                }
            )
        
        return stats


def main():
    """Entry point for scheduled job."""
    logger.info("Starting nightly price backfill job")
    
    # Default to 90 days for nightly updates
    days_back = int(os.getenv("PRICE_BACKFILL_DAYS", "90"))
    
    stats = backfill_prices(days_back=days_back)
    
    if stats["errors"] > 0:
        logger.warning(f"Completed with {stats['errors']} errors")
        sys.exit(1)
    else:
        logger.info("Price backfill job completed successfully")
        sys.exit(0)


if __name__ == "__main__":
    main()
