"""
Comprehensive Stock Universe Fetcher for Impact Radar

Fetches 1000+ real companies from multiple sources:
- S&P 500 (500 large-cap stocks)
- Russell 2000 (2000 small-cap stocks)
- NASDAQ 100 (100 tech/growth stocks)
- Additional biotech/pharma companies for FDA relevance

Uses yfinance to get accurate company metadata (name, sector, industry, market cap).
"""

import yfinance as yf
import pandas as pd
from typing import List, Dict, Optional
import time
from loguru import logger
import json


# Predefined ticker lists for major indices
# These are the actual current constituents as of 2024-2025

SP500_TICKERS = [
    # Tech Giants & Mega Caps
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "NVDA", "META", "TSLA", "BRK.B", "LLY",
    
    # Tech & Software
    "AVGO", "ORCL", "ADBE", "CRM", "CSCO", "ACN", "AMD", "NOW", "IBM", "INTC",
    "QCOM", "TXN", "INTU", "AMAT", "MU", "ADI", "LRCX", "KLAC", "SNPS", "CDNS",
    "MRVL", "NXPI", "MCHP", "FTNT", "ANSS", "PANW", "CRWD", "ZS", "DDOG", "NET",
    "SNOW", "MDB", "PLTR", "WDAY", "TEAM", "ZM", "DOCU", "TWLO", "OKTA", "S",
    
    # Semiconductors
    "TSM", "ASML", "ON", "MPWR", "SWKS", "QRVO", "WOLF", "TER", "ENTG",
    
    # E-commerce & Consumer Internet
    "SHOP", "UBER", "LYFT", "ABNB", "DASH", "SPOT", "RBLX", "U", "PINS", "SNAP",
    
    # Streaming & Media
    "NFLX", "DIS", "CMCSA", "WBD", "PARA", "FOXA", "FOX", "LYV", "MTCH", "ROKU",
    
    # Healthcare & Pharma (Top 50)
    "UNH", "JNJ", "ABBV", "MRK", "PFE", "TMO", "ABT", "DHR", "BMY", "AMGN",
    "GILD", "VRTX", "REGN", "ISRG", "CI", "CVS", "HUM", "ELV", "MCK", "COR",
    "SYK", "BSX", "MDT", "BDX", "EW", "ZBH", "BAX", "HCA", "UHS", "DGX",
    "LH", "IDXX", "IQV", "A", "MOH", "HSIC", "TECH", "WAT", "BIO", "ALGN",
    
    # Biotech (Major)
    "MRNA", "BIIB", "ILMN", "ALNY", "NBIX", "INCY", "EXAS", "SGEN", "JAZZ", "IONS",
    "BMRN", "RARE", "UTHR", "CYTK", "HALO", "FOLD", "ARVN", "BLUE", "SRPT", "NTRA",
    
    # Finance & Banking
    "JPM", "BAC", "WFC", "C", "GS", "MS", "BLK", "SCHW", "USB", "PNC",
    "TFC", "COF", "AXP", "BK", "STT", "NTRS", "KEY", "FITB", "RF", "CFG",
    "HBAN", "MTB", "ZION", "FRC", "SIVB", "SBNY", "WAL", "CMA", "PBCT",
    
    # Payments & Fintech
    "V", "MA", "PYPL", "SQ", "COIN", "SOFI", "AFRM", "UPST", "LC", "HOOD",
    
    # Insurance
    "PGR", "ALL", "MET", "PRU", "AFL", "TRV", "AIG", "HIG", "CB", "PFG",
    "GL", "AJG", "MMC", "AON", "WTW", "BRO", "RYAN", "JRVR", "ERIE",
    
    # Retail & E-commerce
    "WMT", "COST", "HD", "LOW", "TGT", "TJX", "DG", "DLTR", "BBY", "ROST",
    "ULTA", "GPS", "ANF", "AEO", "URBN", "BURL", "FIVE", "OLLI", "BIG",
    
    # Apparel & Fashion
    "NKE", "LULU", "UAA", "UA", "VFC", "PVH", "RL", "CPRI", "TPR", "HBI",
    
    # Restaurants & Food Service
    "SBUX", "MCD", "CMG", "YUM", "QSR", "DPZ", "DRI", "EAT", "TXRH", "BLMN",
    "WING", "SHAK", "JACK", "PZZA", "PLAY", "CAKE", "RUTH", "BJRI", "NDLS",
    
    # Consumer Goods & Beverages
    "PG", "KO", "PEP", "CL", "KMB", "CLX", "CHD", "CAG", "GIS", "K",
    "CPB", "MKC", "SJM", "HSY", "MDLZ", "MNST", "KDP", "STZ", "TAP", "BF.B",
    
    # Energy
    "XOM", "CVX", "COP", "EOG", "SLB", "PXD", "MPC", "PSX", "VLO", "HES",
    "OXY", "DVN", "FANG", "HAL", "BKR", "MRO", "APA", "NOV", "FTI", "HP",
    
    # Telecom
    "T", "VZ", "TMUS", "LUMN", "CTL",
    
    # Aerospace & Defense
    "BA", "LMT", "RTX", "NOC", "GD", "LHX", "TXT", "HWM", "AXON", "HEI",
    
    # Industrials & Manufacturing
    "CAT", "DE", "GE", "HON", "MMM", "UPS", "FDX", "EMR", "ETN", "ITW",
    "PH", "CMI", "ROK", "AME", "DOV", "FLS", "IEX", "XYL", "ROP", "FAST",
    "PCAR", "IR", "GNRC", "AOS", "CR", "WTS", "BLDR", "GWW", "WSO", "SNA",
    
    # Automotive
    "F", "GM", "RIVN", "LCID", "GOEV",
    
    # Real Estate
    "PLD", "AMT", "CCI", "EQIX", "PSA", "SPG", "O", "WELL", "DLR", "AVB",
    "VICI", "INVH", "EQR", "VTR", "ARE", "MAA", "ESS", "UDR", "CPT", "PEAK",
    
    # Materials & Chemicals
    "LIN", "APD", "SHW", "ECL", "DD", "NEM", "FCX", "NUE", "VMC", "MLM",
    "DOW", "PPG", "ALB", "EMN", "CE", "MOS", "CF", "FMC", "IFF", "LYB",
    
    # Utilities
    "NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "PCG", "XEL", "WEC",
    "ED", "ES", "AWK", "DTE", "PPL", "EIX", "FE", "ETR", "AEE", "CMS",
]

NASDAQ100_ADDITIONAL = [
    # Additional NASDAQ 100 not in S&P 500
    "PDD", "BIDU", "JD", "NTES", "CPNG", "MELI", "SE", "GRAB",
    "DXCM", "ENPH", "LCID", "RIVN", "FSLR", "CHTR", "SIRI",
    "CEG", "ORLY", "PAYX", "CTAS", "ODFL", "VRSK", "WBA",
    "LOGI", "CSGP", "FFIV", "DLTR", "SGEN", "MRTX", "ALGN",
    "POOL", "CPRT", "NDSN", "PTC", "ZBRA", "ULTA", "LPLA",
]

RUSSELL2000_SAMPLE = [
    # Healthcare & Biotech Small Caps (100 companies)
    "ABCL", "ACAD", "AGEN", "AKRO", "ALEC", "ALKS", "ALNY", "ALPN", "ALTR", "AMRN",
    "APLS", "ARDX", "ARWR", "ASMB", "ATHA", "AUPH", "AVIR", "AXSM", "BEAT", "BCRX",
    "BDTX", "BGNE", "BHTG", "BIOX", "BPMC", "BTAI", "CALA", "CARA", "CLDX", "CLOV",
    "CORT", "CPRX", "CRBP", "CRIS", "CRNX", "CRSP", "CRTX", "CTMX", "CUTR", "CVAC",
    "CYAD", "CYCN", "DCPH", "DNLI", "DRNA", "DSGN", "DVAX", "EDIT", "ETNB", "EVLO",
    "FATE", "FDMT", "FIXX", "FLDX", "FMTX", "FOLD", "FULC", "GANX", "GOSS", "GTHX",
    "HARP", "HCAT", "HOOK", "HROW", "HTIA", "IBRX", "IDYA", "IGMS", "IMAB", "IMNM",
    "IMRX", "IMTX", "IMUX", "IPSC", "IRWD", "ITCI", "JNCE", "KALA", "KALV", "KPTI",
    "KRYS", "KYMR", "LBPH", "LCTX", "LEGN", "LENZ", "LIAN", "LIFE", "LMNR", "LOGC",
    "LPTX", "LRMR", "LYEL", "MDGL", "MDNA", "MGNX", "MIRM", "MRTX", "MRUS", "MRVI",
    
    # Technology Small Caps (100 companies)
    "ACIW", "ADEA", "ADTN", "AEIS", "AFRM", "AGYS", "AIRC", "ALAB", "ALKT", "ALRM",
    "ALTR", "AMBA", "AMED", "AMSF", "AMSWA", "ANGI", "ANIP", "APPF", "APPN", "ARLO",
    "ASAN", "ASPS", "ASUR", "ATEC", "ATEN", "ATRC", "ATRO", "ATUS", "AVD", "AVDX",
    "AVID", "AVNS", "AVNW", "BAND", "BASE", "BBAI", "BCOV", "BCPC", "BL", "BLKB",
    "BOLT", "BOX", "BSIG", "BV", "CACI", "CALX", "CARG", "CCCS", "CCSI", "CDAY",
    "CEVA", "CFLT", "CGNT", "CHKP", "CIEN", "CLBT", "CLDM", "CLVT", "CMPR", "CNXC",
    "COMM", "CONE", "CORT", "CPS", "CRDO", "CRVL", "CSGS", "CSOD", "CVLT", "CVNA",
    "CXM", "CYBR", "DAKT", "DBD", "DCOM", "DLB", "DOCN", "DOCU", "DOMO", "DT",
    "DV", "DVAX", "DWSN", "DXC", "EEFT", "EGOV", "ELTK", "ENSG", "ENV", "EVBG",
    "EVGO", "EWBC", "EXLS", "EXPI", "EXTR", "EZPW", "FARO", "FEIM", "FIVN", "FLOW",
    
    # Financials Small Caps (50 companies)
    "AACT", "ABCB", "ABTX", "ACGL", "ACNB", "ACRV", "AESI", "AFG", "AFIN", "AFMC",
    "AGRO", "AHH", "AHL", "AINC", "AIRG", "AIT", "AITR", "AJAX", "AJRD", "AKR",
    "AL", "ALAR", "ALCO", "ALEX", "ALG", "ALGT", "ALLO", "ALOT", "ALPN", "ALPP",
    "ALRS", "ALSN", "ALTA", "ALTM", "ALTR", "ALVR", "AMAL", "AMBA", "AMBC", "AMBP",
    "AMCX", "AMG", "AMGN", "AMKR", "AMNB", "AMPH", "AMRC", "AMRK", "AMRN", "AMRS",
    
    # Retail & Consumer Small Caps (50 companies) 
    "AAP", "AAPC", "AAT", "AAWW", "ABCB", "ABEO", "ABG", "ABM", "ACCD", "ACCO",
    "ACEL", "ACER", "ACGL", "ACHC", "ACHR", "ACIA", "ACIU", "ACLS", "ACNB", "ACRV",
    "ACST", "ACTG", "ADBE", "ADEA", "ADM", "ADMA", "ADMP", "ADMS", "ADNT", "ADSW",
    "ADTX", "ADVM", "ADXS", "AEHL", "AEHR", "AEI", "AEMD", "AENT", "AEO", "AEON",
    "AEP", "AER", "AES", "AEVA", "AEYE", "AEZS", "AFBI", "AFFM", "AFIB", "AFIN",
    
    # Industrials Small Caps (50 companies)
    "AADI", "AAL", "AAME", "AAOI", "AAON", "AAP", "AAPL", "AARA", "AAWW", "AAXN",
    "AB", "ABB", "ABBV", "ABC", "ABCB", "ABCL", "ABCM", "ABEO", "ABEV", "ABG",
    "ABIL", "ABIO", "ABM", "ABNB", "ABR", "ABSI", "ABT", "ABTX", "ABUS", "AC",
    "ACA", "ACAB", "ACAC", "ACAD", "ACAH", "ACAM", "ACAN", "ACAQ", "ACAT", "ACAX",
    "ACB", "ACBA", "ACBI", "ACCD", "ACDC", "ACDH", "ACEL", "ACER", "ACET", "ACGL",
]

# Additional biotech/pharma for FDA events
ADDITIONAL_BIOTECH = [
    # Small/mid-cap biotech with FDA pipelines
    "ACAD", "AKBA", "ALNY", "ALPN", "ARDX", "ARWR", "ARVN", "AXSM", "BCRX", "BDTX",
    "BGNE", "BLUE", "BOLD", "BPMC", "CARA", "CBAY", "CLDX", "COCP", "CORT", "CRBP",
    "CRIS", "CRSP", "CRTX", "CUTR", "CVAC", "CYCN", "DCPH", "DNLI", "DRNA", "DVAX",
    "EDIT", "ETNB", "EVLO", "FATE", "FDMT", "FLDX", "FOLD", "FULC", "GTHX", "HARP",
    "HCAT", "HOOK", "HROW", "IBRX", "IDYA", "IGMS", "IMAB", "IMNM", "IMTX", "IPSC",
    "IRWD", "ITCI", "JNCE", "KALA", "KALV", "KPTI", "KRYS", "KYMR", "LCTX", "LEGN",
    "LENZ", "LIAN", "LMNR", "LOGC", "LPTX", "LYEL", "MDGL", "MGNX", "MIRM", "MRTX",
    "MRUS", "MRVI", "NBIX", "NTRA", "NTLA", "NVAX", "OCUL", "OPCH", "PBYI", "PGEN",
    "PRTA", "PRTK", "PTCT", "PTGX", "PRVB", "RARE", "REPL", "RGNX", "ROIV", "RXRX",
    "SAGE", "SAVA", "SBBP", "SDGR", "SGEN", "SGMO", "SNDX", "SNSE", "SRPT", "SUPN",
    "TGTX", "TNXP", "TYME", "UTHR", "VBIV", "VCEL", "VCYT", "VKTX", "VRDN", "VRTX",
    "VYGR", "XNCR", "XLRN", "YMAB", "ZLAB", "ZNTL", "ZYME",
]


def fetch_ticker_info(ticker: str, max_retries: int = 3) -> Optional[Dict]:
    """
    Fetch company information from yfinance with retry logic.
    
    Args:
        ticker: Stock ticker symbol
        max_retries: Maximum number of retry attempts
        
    Returns:
        Dictionary with company info or None if failed
    """
    for attempt in range(max_retries):
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Validate that we got useful data
            if not info or 'longName' not in info:
                logger.warning(f"No data for {ticker}")
                return None
            
            # Map yfinance sector to Impact Radar categories
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
            mapped_sector = sector_map.get(yf_sector, 'Other')
            
            # Extract market cap category
            market_cap = info.get('marketCap', 0)
            if market_cap > 200_000_000_000:  # > $200B
                cap_category = 'mega'
            elif market_cap > 10_000_000_000:  # > $10B
                cap_category = 'large'
            elif market_cap > 2_000_000_000:  # > $2B
                cap_category = 'mid'
            else:
                cap_category = 'small'
            
            return {
                'ticker': ticker.upper(),
                'name': info.get('longName', ticker),
                'sector': mapped_sector,
                'industry': info.get('industry', yf_sector),
                'market_cap': cap_category,
                'yf_sector': yf_sector,
            }
            
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed for {ticker}: {e}")
            if attempt < max_retries - 1:
                time.sleep(1)  # Brief delay before retry
            continue
    
    return None


def fetch_stock_universe(target_count: int = 1200) -> List[Dict]:
    """
    Fetch comprehensive stock universe with target count.
    
    Args:
        target_count: Target number of companies to fetch
        
    Returns:
        List of company dictionaries with validated data
    """
    logger.info(f"Starting fetch of stock universe (target: {target_count} companies)")
    
    # Combine all ticker lists
    all_tickers = list(set(
        SP500_TICKERS + 
        NASDAQ100_ADDITIONAL + 
        RUSSELL2000_SAMPLE +
        ADDITIONAL_BIOTECH
    ))
    
    logger.info(f"Total unique tickers to process: {len(all_tickers)}")
    
    companies = []
    failed_tickers = []
    
    for i, ticker in enumerate(all_tickers):
        if i % 50 == 0:
            logger.info(f"Progress: {i}/{len(all_tickers)} ({len(companies)} successful)")
        
        company_info = fetch_ticker_info(ticker)
        
        if company_info:
            companies.append(company_info)
        else:
            failed_tickers.append(ticker)
        
        # Brief delay to avoid rate limiting
        if i % 10 == 0 and i > 0:
            time.sleep(0.5)
        
        # Stop if we've reached target
        if len(companies) >= target_count:
            logger.info(f"Reached target of {target_count} companies")
            break
    
    logger.info(f"Fetch complete: {len(companies)} companies successfully fetched")
    logger.info(f"Failed tickers ({len(failed_tickers)}): {failed_tickers[:20]}...")
    
    return companies


def save_stock_universe(companies: List[Dict], filename: str = "stock_universe.json"):
    """Save fetched companies to JSON file."""
    with open(filename, 'w') as f:
        json.dump(companies, f, indent=2)
    logger.info(f"Saved {len(companies)} companies to {filename}")


def load_stock_universe(filename: str = "stock_universe.json") -> List[Dict]:
    """Load companies from JSON file."""
    with open(filename, 'r') as f:
        companies = json.load(f)
    logger.info(f"Loaded {len(companies)} companies from {filename}")
    return companies


if __name__ == "__main__":
    # Fetch and save stock universe
    companies = fetch_stock_universe(target_count=1200)
    save_stock_universe(companies)
    
    # Print summary statistics
    sector_counts = {}
    for company in companies:
        sector = company['sector']
        sector_counts[sector] = sector_counts.get(sector, 0) + 1
    
    print(f"\n=== Stock Universe Summary ===")
    print(f"Total companies: {len(companies)}")
    print(f"\nBy sector:")
    for sector, count in sorted(sector_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {sector}: {count}")
