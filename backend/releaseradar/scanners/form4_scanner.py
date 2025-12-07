"""
SEC Form 4 Insider Trading Scanner

Monitors SEC EDGAR for Form 4 filings (insider transactions) and analyzes
sentiment based on transaction type, insider role, and transaction size.

Form 4 is filed when corporate insiders (officers, directors, 10% owners)
buy or sell company stock. These transactions can signal insider confidence
or concern about the company's prospects.
"""

import logging
import re
import time
from datetime import datetime, timedelta, timezone, date
from typing import List, Dict, Any, Optional
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

SEC_HEADERS = {
    'User-Agent': 'Impact Radar Scanner contact@impactradar.com',
    'Accept-Encoding': 'gzip, deflate',
    'Host': 'www.sec.gov'
}

# SEC EDGAR rate limit: 10 requests per second
SEC_RATE_LIMIT_DELAY = 0.11  # 110ms between requests for safety margin


def rate_limit_sleep():
    """Sleep to respect SEC EDGAR rate limits (10 req/sec)."""
    time.sleep(SEC_RATE_LIMIT_DELAY)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def fetch_recent_form4_filings(days_back: int = 7, max_filings: int = 100) -> List[str]:
    """
    Fetch recent Form 4 filing URLs from SEC EDGAR RSS feed.
    
    Args:
        days_back: Number of days to look back for filings
        max_filings: Maximum number of filings to return
        
    Returns:
        List of Form 4 filing URLs
    """
    logger.info(f"Fetching Form 4 filings from last {days_back} days")
    
    try:
        # SEC EDGAR Atom feed for Form 4 filings
        rss_url = "https://www.sec.gov/cgi-bin/browse-edgar"
        params = {
            'action': 'getcurrent',
            'type': '4',
            'company': '',
            'dateb': '',
            'owner': 'include',
            'start': '0',
            'count': max_filings,
            'output': 'atom'
        }
        
        rate_limit_sleep()
        response = requests.get(rss_url, params=params, headers=SEC_HEADERS, timeout=15)
        response.raise_for_status()
        
        filing_urls = []
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        
        try:
            root = ET.fromstring(response.content)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            
            for entry in root.findall('.//atom:entry', ns):
                # Extract filing date
                updated_elem = entry.find('.//atom:updated', ns)
                if updated_elem is None or not updated_elem.text:
                    continue
                
                try:
                    filing_date = datetime.fromisoformat(updated_elem.text.replace('Z', '+00:00'))
                except:
                    continue
                
                # Filter by date
                if filing_date < cutoff_date:
                    continue
                
                # Extract filing URL
                link_elem = entry.find('.//atom:link[@rel="alternate"]', ns)
                if link_elem is not None:
                    filing_url = link_elem.get('href', '')
                    if filing_url and 'Archives/edgar' in filing_url:
                        filing_urls.append(filing_url)
            
            logger.info(f"Found {len(filing_urls)} Form 4 filings from last {days_back} days")
            return filing_urls[:max_filings]
        
        except ET.ParseError as e:
            logger.error(f"Failed to parse SEC EDGAR RSS feed: {e}")
            return []
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch Form 4 filings: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching Form 4 filings: {e}")
        return []


def parse_form4(filing_url: str) -> Optional[Dict[str, Any]]:
    """
    Parse a Form 4 filing and extract transaction data.
    
    Args:
        filing_url: URL to the Form 4 filing on SEC EDGAR
        
    Returns:
        Dictionary with parsed transaction data or None if parsing fails
    """
    try:
        rate_limit_sleep()
        
        # Fetch the filing index page
        response = requests.get(filing_url, headers=SEC_HEADERS, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the XML document link (primary-doc.xml or form4.xml)
        xml_link = None
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.endswith('.xml') and ('primary' in href.lower() or 'form4' in href.lower() or 'doc4' in href.lower()):
                if not href.startswith('http'):
                    xml_link = f"https://www.sec.gov{href}"
                else:
                    xml_link = href
                break
        
        if not xml_link:
            logger.debug(f"No XML document found in Form 4 filing: {filing_url}")
            return None
        
        # Fetch and parse the XML document
        rate_limit_sleep()
        xml_response = requests.get(xml_link, headers=SEC_HEADERS, timeout=15)
        xml_response.raise_for_status()
        
        # Parse XML
        root = ET.fromstring(xml_response.content)
        
        # Extract issuer (company) information
        issuer = root.find('.//issuer')
        if issuer is None:
            logger.debug(f"No issuer found in Form 4: {filing_url}")
            return None
        
        ticker_elem = issuer.find('.//issuerTradingSymbol')
        company_name_elem = issuer.find('.//issuerName')
        
        ticker = ticker_elem.text.strip() if ticker_elem is not None and ticker_elem.text else None
        company_name = company_name_elem.text.strip() if company_name_elem is not None and company_name_elem.text else None
        
        if not ticker or not company_name:
            logger.debug(f"Missing ticker or company name in Form 4: {filing_url}")
            return None
        
        # Extract reporting owner (insider) information
        owner = root.find('.//reportingOwner')
        if owner is None:
            logger.debug(f"No reporting owner found in Form 4: {filing_url}")
            return None
        
        owner_name_elem = owner.find('.//rptOwnerName')
        insider_name = owner_name_elem.text.strip() if owner_name_elem is not None and owner_name_elem.text else "Unknown"
        
        # Extract insider title and relationship
        relationship = owner.find('.//reportingOwnerRelationship')
        is_director = False
        is_officer = False
        is_ten_percent_owner = False
        insider_title = None
        
        if relationship is not None:
            is_director_elem = relationship.find('.//isDirector')
            is_officer_elem = relationship.find('.//isOfficer')
            is_ten_percent_elem = relationship.find('.//isTenPercentOwner')
            officer_title_elem = relationship.find('.//officerTitle')
            
            is_director = is_director_elem is not None and is_director_elem.text == '1'
            is_officer = is_officer_elem is not None and is_officer_elem.text == '1'
            is_ten_percent_owner = is_ten_percent_elem is not None and is_ten_percent_elem.text == '1'
            
            if officer_title_elem is not None and officer_title_elem.text:
                insider_title = officer_title_elem.text.strip()
            elif is_director:
                insider_title = "Director"
            elif is_ten_percent_owner:
                insider_title = "10% Owner"
        
        # Extract transactions (focus on non-derivative transactions)
        transactions = []
        
        for transaction in root.findall('.//nonDerivativeTransaction'):
            # Transaction date
            trans_date_elem = transaction.find('.//transactionDate/value')
            if trans_date_elem is None or not trans_date_elem.text:
                continue
            
            try:
                transaction_date = datetime.strptime(trans_date_elem.text.strip(), '%Y-%m-%d').date()
            except:
                continue
            
            # Transaction code (P=Purchase, S=Sale, A=Award, etc.)
            trans_code_elem = transaction.find('.//transactionCode')
            transaction_code = trans_code_elem.text.strip() if trans_code_elem is not None and trans_code_elem.text else None
            
            if not transaction_code:
                continue
            
            # Shares
            shares_elem = transaction.find('.//transactionShares/value')
            shares = float(shares_elem.text.strip()) if shares_elem is not None and shares_elem.text else 0
            
            if shares == 0:
                continue
            
            # Price per share
            price_elem = transaction.find('.//transactionPricePerShare/value')
            price_per_share = float(price_elem.text.strip()) if price_elem is not None and price_elem.text else None
            
            # Shares owned after transaction
            shares_owned_elem = transaction.find('.//sharesOwnedFollowingTransaction/value')
            shares_owned_after = float(shares_owned_elem.text.strip()) if shares_owned_elem is not None and shares_owned_elem.text else None
            
            # Calculate transaction value
            transaction_value = None
            if price_per_share is not None and shares:
                transaction_value = shares * price_per_share
            
            transactions.append({
                'transaction_date': transaction_date,
                'transaction_code': transaction_code,
                'shares': shares,
                'price_per_share': price_per_share,
                'transaction_value': transaction_value,
                'shares_owned_after': shares_owned_after
            })
        
        if not transactions:
            logger.debug(f"No valid transactions found in Form 4: {filing_url}")
            return None
        
        # Extract filing date
        filed_date_elem = root.find('.//periodOfReport')
        filed_date = None
        if filed_date_elem is not None and filed_date_elem.text:
            try:
                filed_date = datetime.strptime(filed_date_elem.text.strip(), '%Y-%m-%d').date()
            except:
                filed_date = date.today()
        else:
            filed_date = date.today()
        
        # Return parsed data for all transactions
        return {
            'ticker': ticker,
            'company_name': company_name,
            'insider_name': insider_name,
            'insider_title': insider_title,
            'is_director': is_director,
            'is_officer': is_officer,
            'is_ten_percent_owner': is_ten_percent_owner,
            'transactions': transactions,
            'form_4_url': filing_url,
            'filed_date': filed_date
        }
    
    except requests.exceptions.RequestException as e:
        logger.warning(f"Failed to fetch Form 4 filing {filing_url}: {e}")
        return None
    except ET.ParseError as e:
        logger.warning(f"Failed to parse Form 4 XML {filing_url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error parsing Form 4 {filing_url}: {e}")
        return None


def calculate_insider_sentiment(transaction: Dict[str, Any], insider_data: Dict[str, Any]) -> tuple[float, str]:
    """
    Calculate sentiment score for an insider transaction.
    
    Args:
        transaction: Transaction details (code, shares, value, etc.)
        insider_data: Insider details (name, title, roles)
        
    Returns:
        Tuple of (sentiment_score, sentiment_rationale)
        - sentiment_score: -1.0 (bearish) to +1.0 (bullish)
        - sentiment_rationale: Human-readable explanation
    """
    transaction_code = transaction['transaction_code']
    shares = transaction['shares']
    transaction_value = transaction['transaction_value']
    
    insider_title = insider_data.get('insider_title', '')
    is_officer = insider_data.get('is_officer', False)
    is_director = insider_data.get('is_director', False)
    is_ten_percent_owner = insider_data.get('is_ten_percent_owner', False)
    
    # Base sentiment from transaction code
    base_sentiment = 0.0
    action = ""
    
    if transaction_code == 'P':
        # Purchase - bullish signal
        base_sentiment = 0.8
        action = "purchased"
    elif transaction_code == 'S':
        # Sale - bearish signal (but could be planned)
        base_sentiment = -0.5
        action = "sold"
    elif transaction_code == 'A':
        # Award/Grant - neutral to slightly positive (compensation)
        base_sentiment = 0.2
        action = "received grant of"
    elif transaction_code == 'M':
        # Exercise of options - neutral (often followed by sale)
        base_sentiment = 0.0
        action = "exercised options for"
    else:
        # Other codes (D=return, F=tax withholding, etc.) - neutral
        base_sentiment = 0.0
        action = "transacted"
    
    # Adjust for insider importance
    importance_multiplier = 1.0
    title_desc = ""
    
    if insider_title:
        title_upper = insider_title.upper()
        
        # C-suite executives (most important)
        if any(x in title_upper for x in ['CEO', 'CHIEF EXECUTIVE', 'PRESIDENT']):
            importance_multiplier = 1.5
            title_desc = "CEO"
        elif any(x in title_upper for x in ['CFO', 'CHIEF FINANCIAL']):
            importance_multiplier = 1.4
            title_desc = "CFO"
        elif any(x in title_upper for x in ['COO', 'CHIEF OPERATING']):
            importance_multiplier = 1.3
            title_desc = "COO"
        elif any(x in title_upper for x in ['CTO', 'CHIEF TECHNOLOGY']):
            importance_multiplier = 1.3
            title_desc = "CTO"
        elif 'CHIEF' in title_upper:
            importance_multiplier = 1.25
            title_desc = "C-level executive"
        # VP level
        elif any(x in title_upper for x in ['VP', 'VICE PRESIDENT']):
            importance_multiplier = 1.1
            title_desc = "VP"
        # Board members
        elif is_director and not is_officer:
            importance_multiplier = 1.15
            title_desc = "Director"
        # 10% owners
        elif is_ten_percent_owner:
            importance_multiplier = 1.2
            title_desc = "10% owner"
        else:
            title_desc = insider_title
    elif is_director:
        importance_multiplier = 1.15
        title_desc = "Director"
    elif is_ten_percent_owner:
        importance_multiplier = 1.2
        title_desc = "10% owner"
    
    # Adjust for transaction size
    size_multiplier = 1.0
    size_desc = ""
    
    if transaction_value:
        if transaction_value >= 10_000_000:  # $10M+
            size_multiplier = 1.5
            size_desc = f"${transaction_value/1_000_000:.1f}M"
        elif transaction_value >= 5_000_000:  # $5M+
            size_multiplier = 1.3
            size_desc = f"${transaction_value/1_000_000:.1f}M"
        elif transaction_value >= 1_000_000:  # $1M+
            size_multiplier = 1.2
            size_desc = f"${transaction_value/1_000_000:.1f}M"
        elif transaction_value >= 500_000:  # $500K+
            size_multiplier = 1.1
            size_desc = f"${transaction_value/1_000:.0f}K"
        elif transaction_value >= 100_000:  # $100K+
            size_multiplier = 1.0
            size_desc = f"${transaction_value/1_000:.0f}K"
        else:
            size_multiplier = 0.8
            size_desc = f"${transaction_value/1_000:.0f}K"
    elif shares >= 100_000:
        size_multiplier = 1.3
        size_desc = f"{shares:,.0f} shares"
    elif shares >= 50_000:
        size_multiplier = 1.2
        size_desc = f"{shares:,.0f} shares"
    elif shares >= 10_000:
        size_multiplier = 1.1
        size_desc = f"{shares:,.0f} shares"
    else:
        size_multiplier = 1.0
        size_desc = f"{shares:,.0f} shares"
    
    # Calculate final sentiment
    sentiment_score = base_sentiment * importance_multiplier * size_multiplier
    
    # Clamp to [-1, 1]
    sentiment_score = max(-1.0, min(1.0, sentiment_score))
    
    # Generate rationale
    if transaction_code == 'P':
        sentiment_rationale = f"{title_desc} {action} {size_desc} - strong bullish signal"
        if sentiment_score >= 0.9:
            sentiment_rationale += " (very significant insider buying)"
        elif sentiment_score >= 0.7:
            sentiment_rationale += " (significant insider buying)"
    elif transaction_code == 'S':
        sentiment_rationale = f"{title_desc} {action} {size_desc} - bearish signal"
        if abs(sentiment_score) >= 0.7:
            sentiment_rationale += " (significant insider selling, may indicate concerns)"
        else:
            sentiment_rationale += " (could be planned sale or diversification)"
    elif transaction_code == 'A':
        sentiment_rationale = f"{title_desc} {action} {size_desc} - routine compensation grant"
    else:
        sentiment_rationale = f"{title_desc} {action} {size_desc} - neutral transaction"
    
    return sentiment_score, sentiment_rationale


def scan_form4_filings(tickers: List[str] = None, companies: Dict[str, Dict] = None) -> List[Dict[str, Any]]:
    """
    Main scanner function for SEC Form 4 filings.
    
    Fetches recent Form 4 filings, parses transactions, calculates sentiment,
    and returns data ready for insertion into insider_transactions table.
    
    Args:
        tickers: Optional list of tickers to filter (not used - we scan all recent filings)
        companies: Optional company info dict (not used - we get info from Form 4)
        
    Returns:
        List of insider transaction dictionaries ready for database insertion
    """
    logger.info("Starting Form 4 insider trading scanner")
    
    try:
        # Fetch recent Form 4 filings from SEC EDGAR
        filing_urls = fetch_recent_form4_filings(days_back=7, max_filings=100)
        
        if not filing_urls:
            logger.info("No recent Form 4 filings found")
            return []
        
        logger.info(f"Processing {len(filing_urls)} Form 4 filings")
        
        insider_transactions = []
        
        for filing_url in filing_urls:
            # Parse Form 4 filing
            parsed_data = parse_form4(filing_url)
            
            if not parsed_data:
                continue
            
            # Process each transaction in the filing
            for transaction in parsed_data['transactions']:
                # Calculate sentiment
                sentiment_score, sentiment_rationale = calculate_insider_sentiment(
                    transaction=transaction,
                    insider_data=parsed_data
                )
                
                # Create insider transaction record
                insider_transaction = {
                    'ticker': parsed_data['ticker'],
                    'company_name': parsed_data['company_name'],
                    'insider_name': parsed_data['insider_name'],
                    'insider_title': parsed_data['insider_title'],
                    'is_director': parsed_data['is_director'],
                    'is_officer': parsed_data['is_officer'],
                    'is_ten_percent_owner': parsed_data['is_ten_percent_owner'],
                    'transaction_date': transaction['transaction_date'],
                    'transaction_code': transaction['transaction_code'],
                    'shares': transaction['shares'],
                    'price_per_share': transaction['price_per_share'],
                    'transaction_value': transaction['transaction_value'],
                    'shares_owned_after': transaction['shares_owned_after'],
                    'sentiment_score': sentiment_score,
                    'sentiment_rationale': sentiment_rationale,
                    'form_4_url': parsed_data['form_4_url'],
                    'filed_date': parsed_data['filed_date']
                }
                
                insider_transactions.append(insider_transaction)
                
                logger.info(
                    f"Parsed Form 4: {parsed_data['ticker']} - {parsed_data['insider_name']} "
                    f"({transaction['transaction_code']}) {transaction['shares']:,.0f} shares, "
                    f"sentiment={sentiment_score:.2f}"
                )
        
        logger.info(f"Form 4 scanner completed: {len(insider_transactions)} transactions found")
        return insider_transactions
    
    except Exception as e:
        logger.error(f"Form 4 scanner failed: {e}", exc_info=True)
        return []


def save_insider_transactions_to_db(transactions: List[Dict[str, Any]], db) -> tuple[int, int, int]:
    """
    Save insider transactions to database and optionally create Event records
    for significant insider activity.
    
    Args:
        transactions: List of insider transaction dictionaries
        db: SQLAlchemy database session
        
    Returns:
        Tuple of (inserted_count, duplicate_count, events_created_count)
    """
    from releaseradar.db.models import InsiderTransaction, Event, Company
    from sqlalchemy.exc import IntegrityError
    from datetime import datetime, timezone
    
    inserted_count = 0
    duplicate_count = 0
    events_created_count = 0
    
    for trans_data in transactions:
        try:
            # Check for duplicate using unique constraint
            existing = db.query(InsiderTransaction).filter(
                InsiderTransaction.ticker == trans_data['ticker'],
                InsiderTransaction.transaction_date == trans_data['transaction_date'],
                InsiderTransaction.insider_name == trans_data['insider_name'],
                InsiderTransaction.transaction_code == trans_data['transaction_code'],
                InsiderTransaction.shares == trans_data['shares']
            ).first()
            
            if existing:
                duplicate_count += 1
                continue
            
            # Create InsiderTransaction record
            insider_transaction = InsiderTransaction(**trans_data)
            db.add(insider_transaction)
            db.flush()
            
            inserted_count += 1
            
            # Create Event for significant insider activity (sentiment > 0.7 or < -0.7)
            sentiment_score = trans_data.get('sentiment_score', 0)
            if abs(sentiment_score) >= 0.7:
                # Check if company exists
                company = db.query(Company).filter(Company.ticker == trans_data['ticker']).first()
                sector = company.sector if company else None
                
                # Determine event type and direction
                if sentiment_score >= 0.7:
                    event_type = 'insider_buy'
                    direction = 'positive'
                    title = f"Significant Insider Purchase by {trans_data['insider_title'] or trans_data['insider_name']}"
                else:
                    event_type = 'insider_sell'
                    direction = 'negative'
                    title = f"Significant Insider Sale by {trans_data['insider_title'] or trans_data['insider_name']}"
                
                # Create Event record
                event = Event(
                    ticker=trans_data['ticker'],
                    company_name=trans_data['company_name'],
                    event_type=event_type,
                    title=title,
                    description=trans_data['sentiment_rationale'],
                    date=datetime.combine(trans_data['transaction_date'], datetime.min.time()).replace(tzinfo=timezone.utc),
                    source='SEC Form 4',
                    source_url=trans_data['form_4_url'],
                    raw_id=f"form4_{trans_data['ticker']}_{trans_data['transaction_date']}_{trans_data['insider_name']}_{trans_data['transaction_code']}",
                    source_scanner='form4',
                    sector=sector,
                    impact_score=int(abs(sentiment_score) * 100),
                    direction=direction,
                    confidence=abs(sentiment_score),
                    rationale=trans_data['sentiment_rationale'],
                    info_tier='secondary',  # Insider trading is secondary information
                    info_subtype='insider_trading'
                )
                
                db.add(event)
                events_created_count += 1
            
            db.commit()
        
        except IntegrityError:
            db.rollback()
            duplicate_count += 1
            logger.debug(f"Duplicate insider transaction skipped: {trans_data['ticker']} {trans_data['insider_name']}")
        except Exception as e:
            db.rollback()
            logger.error(f"Error saving insider transaction: {e}")
            continue
    
    logger.info(
        f"Saved insider transactions: {inserted_count} inserted, "
        f"{duplicate_count} duplicates, {events_created_count} events created"
    )
    
    return inserted_count, duplicate_count, events_created_count
