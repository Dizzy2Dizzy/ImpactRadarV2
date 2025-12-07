"""
Comprehensive Real Data Population for Impact Radar

Populates database with 1200+ real companies and REAL events from official sources:
- Fetches company data from yfinance (validated tickers)
- Runs actual scanners to get real SEC filings, FDA announcements, etc.
- All events have real sources, dates, and proper scoring

Usage:
    python populate_real_data.py [--target-companies 1200] [--no-scan]
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import argparse
import time
from loguru import logger
from database import get_db, close_db_session, Company, Event
from releaseradar.db.models import EventScore
from data_manager import DataManager
import yfinance as yf
from typing import List, Dict, Optional
import pandas as pd


# Use actual current S&P 500, NASDAQ, and Russell tickers
# These will be validated via yfinance to ensure they're real and current

def fetch_sp500_tickers() -> List[str]:
    """Fetch current S&P 500 tickers from Wikipedia."""
    try:
        logger.info("Fetching S&P 500 tickers from Wikipedia...")
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        tables = pd.read_html(url)
        df = tables[0]
        tickers = df['Symbol'].tolist()
        # Fix ticker formats (replace dots with hyphens for yfinance)
        tickers = [t.replace('.', '-') for t in tickers]
        logger.info(f"Found {len(tickers)} S&P 500 tickers")
        return tickers
    except Exception as e:
        logger.error(f"Failed to fetch S&P 500 tickers: {e}")
        return []


def fetch_nasdaq100_tickers() -> List[str]:
    """Fetch current NASDAQ 100 tickers."""
    try:
        logger.info("Fetching NASDAQ 100 tickers from Wikipedia...")
        url = 'https://en.wikipedia.org/wiki/Nasdaq-100'
        tables = pd.read_html(url)
        df = tables[4]  # NASDAQ 100 components table
        tickers = df['Ticker'].tolist()
        logger.info(f"Found {len(tickers)} NASDAQ 100 tickers")
        return tickers
    except Exception as e:
        logger.warning(f"Failed to fetch NASDAQ 100 tickers: {e}")
        return []


def fetch_russell2000_sample() -> List[str]:
    """Get a representative sample of Russell 2000 tickers."""
    # Since Russell 2000 is hard to scrape, use known high-quality small caps
    return [
        # Biotech small caps with active FDA pipelines
        "ACAD", "ALNY", "ALPN", "ARDX", "ARWR", "ARVN", "AXSM", "BCRX", "BGNE",
        "BLUE", "BPMC", "CARA", "CLDX", "CORT", "CRBP", "CRIS", "CRSP", "CRTX",
        "CVAC", "DNLI", "DRNA", "DVAX", "EDIT", "ETNB", "FATE", "FDMT", "FOLD",
        "GTHX", "HCAT", "HOOK", "HROW", "IBRX", "IDYA", "IGMS", "IMAB", "IMNM",
        "IMTX", "IPSC", "IRWD", "ITCI", "JNCE", "KALA", "KALV", "KPTI", "KRYS",
        "KYMR", "LCTX", "LEGN", "LENZ", "LMNR", "LOGC", "LPTX", "LYEL", "MDGL",
        "MGNX", "MIRM", "MRTX", "MRUS", "MRVI", "NTLA", "NVAX", "OCUL", "PGEN",
        "PRTA", "PRTK", "PTCT", "PTGX", "PRVB", "REPL", "RGNX", "ROIV", "RXRX",
        "SAGE", "SAVA", "SDGR", "SGMO", "SNDX", "SUPN", "TGTX", "VBIV", "VCEL",
        "VKTX", "VRDN", "VYGR", "XLRN", "YMAB", "ZLAB", "ZNTL", "ZYME",
        
        # Tech small caps
        "ACIW", "AFRM", "ALRM", "AMBA", "APPN", "ASAN", "AVID", "BAND", "BOX",
        "CALX", "CDAY", "CEVA", "CFLT", "CLVT", "CVLT", "CVNA", "CYBR", "DAKT",
        "DOCN", "DOMO", "ENSG", "FIVN", "FROG", "GTLB", "IOT", "JAMF", "NCNO",
        "NEWR", "NTNX", "PATH", "PCTY", "PD", "QLYS", "RPD", "S", "SAIL", "SMAR",
        "SPSC", "TENB", "VEEV", "VRNS", "ZI", "ZUO",
        
        # Industrial/Manufacturing small caps
        "AIT", "ATKR", "BOOM", "CSWI", "ENS", "ESAB", "ERII", "FSS", "GTLS",
        "HSII", "LECO", "MANT", "MLI", "MATW", "NP", "NPO", "PRIM", "RBC",
        "RXO", "SLGN", "SXI", "TPC", "TRN", "TRS", "VSM", "WERN",
        
        # Healthcare small caps
        "ACHC", "ADMA", "ALHC", "AMN", "CRVL", "ENSG", "EVH", "GMED", "HIMS",
        "KNSA", "LMAT", "OMCL", "PDCO", "PNTG", "PRVA", "RDNT", "SGRY", "TMDX",
        
        # Retail/Consumer small caps  
        "BOOT", "CBRL", "CASY", "CHDN", "DNUT", "FIVE", "GRBK", "HIBB", "LE",
        "MNRO", "OLLI", "PLCE", "PRDO", "SAH", "TXRH", "UPBD", "WINA",
    ]


def validate_and_fetch_company_info(ticker: str, retries: int = 2) -> Optional[Dict]:
    """
    Validate ticker and fetch company info from yfinance.
    
    Returns None if ticker is invalid or delisted.
    """
    for attempt in range(retries):
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Check if we got real data (not empty/error)
            if not info or 'longName' not in info:
                return None
            
            # Check if delisted/suspended
            if info.get('quoteType') == 'NONE' or info.get('exchange') == 'OTC':
                logger.warning(f"{ticker} is delisted or OTC, skipping")
                return None
            
            # Map sector to Impact Radar categories
            sector_map = {
                'Technology': 'Tech',
                'Healthcare': 'Pharma',
                'Financial Services': 'Finance',
                'Communication Services': 'Tech',
                'Consumer Cyclical': 'Retail',
                'Consumer Defensive': 'Retail',
                'Industrials': 'Other',
                'Energy': 'Other',
                'Utilities': 'Other',
                'Real Estate': 'Other',
                'Basic Materials': 'Other',
            }
            
            yf_sector = info.get('sector', 'Unknown')
            if yf_sector == 'Unknown':
                logger.warning(f"{ticker} has no sector data")
                return None
            
            mapped_sector = sector_map.get(yf_sector, 'Other')
            
            return {
                'ticker': ticker.upper(),
                'name': info.get('longName', ticker),
                'sector': mapped_sector,
                'industry': info.get('industry', yf_sector),
            }
            
        except Exception as e:
            logger.debug(f"Attempt {attempt + 1} failed for {ticker}: {e}")
            if attempt < retries - 1:
                time.sleep(0.5)
            continue
    
    return None


def fetch_validated_companies(target_count: int = 1200) -> List[Dict]:
    """
    Fetch and validate companies from multiple sources until target is reached.
    """
    logger.info(f"Fetching validated companies (target: {target_count})")
    
    # Gather tickers from all sources
    all_tickers = []
    
    # S&P 500 (most reliable)
    sp500 = fetch_sp500_tickers()
    all_tickers.extend(sp500)
    
    # NASDAQ 100
    nasdaq = fetch_nasdaq100_tickers()
    all_tickers.extend(nasdaq)
    
    # Russell 2000 sample
    russell_sample = fetch_russell2000_sample()
    all_tickers.extend(russell_sample)
    
    # Remove duplicates
    all_tickers = list(set(all_tickers))
    logger.info(f"Total unique tickers to validate: {len(all_tickers)}")
    
    # Validate each ticker
    validated_companies = []
    failed_count = 0
    
    for i, ticker in enumerate(all_tickers):
        if i % 50 == 0:
            logger.info(f"Progress: {i}/{len(all_tickers)} ({len(validated_companies)} validated)")
        
        company_info = validate_and_fetch_company_info(ticker)
        
        if company_info:
            validated_companies.append(company_info)
        else:
            failed_count += 1
        
        # Rate limiting
        if i % 10 == 0 and i > 0:
            time.sleep(0.3)
        
        # Stop if target reached
        if len(validated_companies) >= target_count:
            logger.info(f"Reached target of {target_count} validated companies")
            break
    
    logger.info(f"Validation complete: {len(validated_companies)} companies validated, {failed_count} failed")
    
    return validated_companies


def populate_companies_to_db(companies: List[Dict]) -> int:
    """Add companies to database."""
    logger.info(f"Adding {len(companies)} companies to database...")
    
    dm = DataManager()
    added = 0
    
    for company in companies:
        try:
            dm.add_company(
                ticker=company['ticker'],
                name=company['name'],
                sector=company['sector'],
                industry=company['industry'],
                tracked=True
            )
            added += 1
            
            if added % 100 == 0:
                logger.info(f"Added {added} companies")
        except Exception as e:
            logger.warning(f"Failed to add {company['ticker']}: {e}")
            continue
    
    logger.info(f"Successfully added {added} companies to database")
    return added


def run_scanners_for_all_companies():
    """
    Run all active scanners to fetch real events for all companies.
    This uses the existing scanner infrastructure.
    """
    logger.info("Starting comprehensive scanner run for all companies...")
    
    # Import scanner functions
    from scanners.impl.sec_8k import scan_sec_8k
    from scanners.impl.sec_edgar import scan_sec_edgar
    from scanners.impl.sec_10q import scan_sec_10q
    from scanners.impl.fda import scan_fda
    from scanners.impl.earnings import scan_earnings_calls
    from scanners.impl.guidance import scan_guidance
    from scanners.impl.product_launch import scan_product_launch
    from scanners.impl.ma import scan_ma
    from scanners.impl.dividend import scan_dividend_buyback
    from scanners.impl.press import scan_press
    from scanners.utils import save_events_to_db
    
    dm = DataManager()
    
    # Get all company tickers
    companies = dm.get_companies(tracked_only=True)
    tickers = [c['ticker'] for c in companies]
    company_map = {c['ticker']: c for c in companies}
    
    logger.info(f"Running scanners for {len(tickers)} companies...")
    
    total_events = 0
    scanner_results = {}
    
    # Run each scanner
    scanners = [
        ('SEC 8-K', scan_sec_8k, 5),  # 5 per ticker
        ('SEC EDGAR', scan_sec_edgar, 3),
        ('SEC 10-Q', scan_sec_10q, 2),
        ('FDA', scan_fda, 3),
        ('Earnings', scan_earnings_calls, 2),
        ('Guidance', scan_guidance, 2),
        ('Product Launch', scan_product_launch, 2),
        ('M&A', scan_ma, 2),
        ('Dividend/Buyback', scan_dividend_buyback, 2),
        ('Press Releases', scan_press, 3),
    ]
    
    for scanner_name, scanner_fn, limit in scanners:
        try:
            logger.info(f"Running {scanner_name} scanner...")
            events = scanner_fn(tickers, company_map, limit_per_ticker=limit)
            
            # Save events to database
            saved_count = save_events_to_db(events)
            
            scanner_results[scanner_name] = {
                'found': len(events),
                'saved': saved_count
            }
            total_events += saved_count
            
            logger.info(f"{scanner_name}: Found {len(events)}, Saved {saved_count}")
            
            # Brief pause between scanners to avoid rate limits
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"{scanner_name} scanner failed: {e}")
            scanner_results[scanner_name] = {'found': 0, 'saved': 0, 'error': str(e)}
            continue
    
    logger.info(f"\n=== Scanner Run Complete ===")
    logger.info(f"Total events saved: {total_events}")
    for scanner_name, results in scanner_results.items():
        if 'error' in results:
            logger.error(f"{scanner_name}: ERROR - {results['error']}")
        else:
            logger.info(f"{scanner_name}: {results['saved']} events saved")
    
    return total_events


def main():
    parser = argparse.ArgumentParser(description='Populate Impact Radar with REAL data from official sources')
    parser.add_argument('--target-companies', type=int, default=1200,
                        help='Target number of companies')
    parser.add_argument('--no-scan', action='store_true',
                        help='Skip scanner run (only add companies)')
    parser.add_argument('--skip-clear', action='store_true',
                        help='Skip clearing existing data')
    
    args = parser.parse_args()
    
    logger.info("=== Impact Radar Real Data Population ===")
    logger.info(f"Target companies: {args.target_companies}")
    logger.info(f"Run scanners: {not args.no_scan}")
    
    # Clear existing data
    if not args.skip_clear:
        db = get_db()
        try:
            logger.info("Clearing existing data...")
            db.query(EventScore).delete()
            db.query(Event).delete()
            db.query(Company).delete()
            db.commit()
            logger.info("Database cleared")
        except Exception as e:
            logger.error(f"Failed to clear database: {e}")
            db.rollback()
            raise
        finally:
            close_db_session(db)
    
    # Fetch and validate companies
    companies = fetch_validated_companies(target_count=args.target_companies)
    
    if len(companies) < 1000:
        logger.warning(f"⚠️  Only {len(companies)} companies validated (target was 1000+)")
        logger.warning("Continuing anyway, but you may want to re-run with more sources")
    
    # Add to database
    companies_added = populate_companies_to_db(companies)
    
    # Run scanners to fetch real events
    events_added = 0
    if not args.no_scan:
        logger.info("\nStarting scanner run (this may take 30-60 minutes for real data)...")
        events_added = run_scanners_for_all_companies()
    else:
        logger.info("Skipping scanner run (--no-scan flag set)")
    
    # Final verification
    db = get_db()
    try:
        total_companies = db.query(Company).count()
        total_events = db.query(Event).count()
        
        logger.info(f"\n=== Population Complete ===")
        logger.info(f"Companies in database: {total_companies}")
        logger.info(f"Events in database: {total_events}")
        logger.info(f"Average events per company: {total_events / max(total_companies, 1):.1f}")
        
        if total_companies >= 1000:
            logger.info(f"\n✅ SUCCESS: {total_companies} companies with {total_events} REAL events")
        else:
            logger.warning(f"\n⚠️  WARNING: Only {total_companies} companies (target was 1000+)")
    finally:
        close_db_session(db)


if __name__ == "__main__":
    main()
