# Populate 1000+ Companies Script

## Overview

Production-quality script to populate the ReleaseRadar database with 1000+ real companies and events from official sources.

**Created:** `backend/scripts/populate_1000_companies.py`

## Features

- **1953 companies** hardcoded from S&P 500, NASDAQ-100, Russell 2000, and biotech/tech sectors
- Uses **9 active scanners** to fetch real events:
  - SEC 8-K (Material Events)
  - SEC 10-Q (Quarterly Reports)
  - Earnings Calls
  - FDA Announcements
  - Guidance Updates
  - M&A Activity
  - Dividend/Buyback Programs
  - Product Launches
  - Press Releases

- Robust error handling with per-scanner and per-event error tracking
- Progress logging with batch processing
- Automatic deduplication using raw_id
- All events scored using ImpactScorer

## Usage

### Full Populate (Companies + Events)
```bash
cd backend
python scripts/populate_1000_companies.py
```

### Only Add Companies (Skip Scanning)
```bash
python scripts/populate_1000_companies.py --skip-events
```

### Only Run Scanners (Skip Company Creation)
```bash
python scripts/populate_1000_companies.py --skip-companies
```

### Adjust Batch Size
```bash
python scripts/populate_1000_companies.py --batch-size 100
```

Default batch size is 50 tickers per batch to avoid overwhelming APIs.

## Expected Runtime

- **Company population**: ~30 seconds for 1953 companies
- **Event scanning**: ~2-4 hours for all scanners (depends on API rate limits)
  - Each scanner processes batches with 5-10 second delays between batches
  - Rate limiting between scanners (10 seconds)

## Output

The script provides detailed logging:
- Company addition progress (every 100 companies)
- Scanner progress by batch
- Events saved/skipped/errors per scanner
- Final summary statistics:
  - Total companies in database
  - Total events in database
  - Events by scanner breakdown

## Database Schema

Companies are added with:
- ticker (e.g., "AAPL")
- name (e.g., "AAPL Corp")
- sector (Tech, Pharma, Finance, Retail, Other)
- industry
- tracked=True

Events are added with:
- All fields from scanner normalization
- Automatic deduplication via raw_id
- Impact scoring via ImpactScorer
- Information tier classification (primary/secondary)

## Error Handling

The script is designed to be fault-tolerant:
- Failed company additions are logged but don't stop the process
- Failed scanner runs are logged and skipped
- Failed event additions are logged and skipped
- Duplicate events are automatically skipped

## Customization

To modify the company list, edit the following in `populate_1000_companies.py`:
- `SP500_TICKERS` - S&P 500 companies
- `BIOTECH_TECH_TICKERS` - Biotech and tech companies

To modify scanners or their configurations, edit the `scanners` list in `run_all_scanners()`.

## Requirements

All required scanners and dependencies are already installed:
- DataManager (database operations)
- All scanner implementations in `backend/scanners/impl/`
- Impact scoring module
- Event normalization utilities

## Notes

- The script uses hardcoded ticker lists (no yfinance validation) for speed
- All tickers are representative of real, active companies as of Nov 2025
- Events are fetched from real official sources (SEC EDGAR, FDA.gov, etc.)
- No mock or synthetic data is generated

