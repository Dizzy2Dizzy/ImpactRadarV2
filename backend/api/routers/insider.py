"""
Insider Trading API Router

Provides endpoints for querying insider transactions (SEC Form 4 filings)
and analyzing insider sentiment trends.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_, case
from typing import List, Optional
from datetime import datetime, timedelta, date
from pydantic import BaseModel

from api.dependencies import get_db
from releaseradar.db.models import InsiderTransaction, Company
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/insider",
    tags=["insider"]
)


# ============================================================================
# Pydantic Schemas
# ============================================================================

class InsiderTransactionResponse(BaseModel):
    """Insider transaction detail response"""
    id: int
    ticker: str
    company_name: str
    insider_name: str
    insider_title: Optional[str]
    is_officer: bool
    is_director: bool
    is_ten_percent_owner: bool
    transaction_date: date
    transaction_code: str
    shares: float
    price_per_share: Optional[float]
    transaction_value: Optional[float]
    shares_owned_after: Optional[float]
    sentiment_score: Optional[float]
    sentiment_rationale: Optional[str]
    form_4_url: Optional[str]
    filed_date: Optional[date]
    created_at: datetime
    
    class Config:
        from_attributes = True


class InsiderSummaryResponse(BaseModel):
    """Insider sentiment summary for a ticker"""
    ticker: str
    company_name: str
    total_transactions: int
    total_buys: int
    total_sells: int
    total_buy_value: float
    total_sell_value: float
    avg_sentiment: float
    net_sentiment: float  # Weighted average considering transaction values
    recent_transactions: List[InsiderTransactionResponse]
    top_insiders: List[dict]  # Top insiders by transaction volume
    period_days: int


class TrendingInsiderActivity(BaseModel):
    """Tickers with unusual insider activity"""
    ticker: str
    company_name: str
    sector: Optional[str]
    transaction_count: int
    net_buy_value: float  # Buy value - sell value
    avg_sentiment: float
    recent_transactions: List[InsiderTransactionResponse]


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/transactions", response_model=List[InsiderTransactionResponse])
async def list_insider_transactions(
    ticker: Optional[str] = Query(None, description="Filter by ticker symbol"),
    start_date: Optional[date] = Query(None, description="Start date for transaction date filter"),
    end_date: Optional[date] = Query(None, description="End date for transaction date filter"),
    min_sentiment: Optional[float] = Query(None, description="Minimum sentiment score (-1 to 1)", ge=-1, le=1),
    max_sentiment: Optional[float] = Query(None, description="Maximum sentiment score (-1 to 1)", ge=-1, le=1),
    transaction_code: Optional[str] = Query(None, description="Filter by transaction code (P, S, A, M, etc.)"),
    is_officer: Optional[bool] = Query(None, description="Filter to officer transactions only"),
    is_director: Optional[bool] = Query(None, description="Filter to director transactions only"),
    limit: int = Query(100, description="Maximum number of results", le=500),
    offset: int = Query(0, description="Pagination offset"),
    db: Session = Depends(get_db)
):
    """
    List insider transactions with flexible filtering.
    
    Returns recent Form 4 insider transactions with sentiment scoring.
    Useful for tracking insider buying/selling activity.
    
    **Examples:**
    - `/insider/transactions?ticker=AAPL` - All Apple insider transactions
    - `/insider/transactions?min_sentiment=0.7` - Significant bullish insider buys
    - `/insider/transactions?transaction_code=P&is_officer=true` - Officer purchases only
    """
    query = db.query(InsiderTransaction)
    
    # Apply filters
    if ticker:
        query = query.filter(InsiderTransaction.ticker == ticker.upper())
    
    if start_date:
        query = query.filter(InsiderTransaction.transaction_date >= start_date)
    
    if end_date:
        query = query.filter(InsiderTransaction.transaction_date <= end_date)
    
    if min_sentiment is not None:
        query = query.filter(InsiderTransaction.sentiment_score >= min_sentiment)
    
    if max_sentiment is not None:
        query = query.filter(InsiderTransaction.sentiment_score <= max_sentiment)
    
    if transaction_code:
        query = query.filter(InsiderTransaction.transaction_code == transaction_code.upper())
    
    if is_officer is not None:
        query = query.filter(InsiderTransaction.is_officer == is_officer)
    
    if is_director is not None:
        query = query.filter(InsiderTransaction.is_director == is_director)
    
    # Order by transaction date (most recent first)
    query = query.order_by(desc(InsiderTransaction.transaction_date))
    
    # Pagination
    total_count = query.count()
    transactions = query.offset(offset).limit(limit).all()
    
    logger.info(
        f"Fetched {len(transactions)} insider transactions (total: {total_count}) "
        f"with filters: ticker={ticker}, codes={transaction_code}, sentiment=[{min_sentiment},{max_sentiment}]"
    )
    
    return transactions


@router.get("/summary/{ticker}", response_model=InsiderSummaryResponse)
async def get_insider_summary(
    ticker: str,
    days: int = Query(90, description="Number of days to analyze", ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Get insider sentiment summary for a specific ticker.
    
    Provides aggregated insider trading metrics:
    - Total buys vs. sells
    - Average sentiment score
    - Net sentiment (weighted by transaction value)
    - Top insiders by activity
    - Recent transactions
    
    **Use cases:**
    - Gauge insider confidence in a stock
    - Identify significant insider accumulation or distribution
    - Track insider activity patterns
    """
    ticker = ticker.upper()
    
    # Validate ticker exists
    company = db.query(Company).filter(Company.ticker == ticker).first()
    if not company:
        raise HTTPException(status_code=404, detail=f"Company with ticker {ticker} not found")
    
    # Date range
    cutoff_date = date.today() - timedelta(days=days)
    
    # Fetch transactions
    transactions = db.query(InsiderTransaction).filter(
        InsiderTransaction.ticker == ticker,
        InsiderTransaction.transaction_date >= cutoff_date
    ).order_by(desc(InsiderTransaction.transaction_date)).all()
    
    if not transactions:
        return InsiderSummaryResponse(
            ticker=ticker,
            company_name=company.name,
            total_transactions=0,
            total_buys=0,
            total_sells=0,
            total_buy_value=0.0,
            total_sell_value=0.0,
            avg_sentiment=0.0,
            net_sentiment=0.0,
            recent_transactions=[],
            top_insiders=[],
            period_days=days
        )
    
    # Calculate metrics
    total_buys = sum(1 for t in transactions if t.transaction_code == 'P')
    total_sells = sum(1 for t in transactions if t.transaction_code == 'S')
    
    total_buy_value = sum(
        t.transaction_value for t in transactions 
        if t.transaction_code == 'P' and t.transaction_value is not None
    )
    
    total_sell_value = sum(
        t.transaction_value for t in transactions 
        if t.transaction_code == 'S' and t.transaction_value is not None
    )
    
    # Average sentiment
    sentiments = [t.sentiment_score for t in transactions if t.sentiment_score is not None]
    avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.0
    
    # Net sentiment (weighted by transaction value)
    weighted_sentiments = [
        t.sentiment_score * (t.transaction_value or 0)
        for t in transactions
        if t.sentiment_score is not None
    ]
    total_value = sum(t.transaction_value or 0 for t in transactions)
    net_sentiment = sum(weighted_sentiments) / total_value if total_value > 0 else avg_sentiment
    
    # Top insiders by transaction count
    insider_activity = {}
    for t in transactions:
        key = t.insider_name
        if key not in insider_activity:
            insider_activity[key] = {
                'insider_name': t.insider_name,
                'insider_title': t.insider_title,
                'transaction_count': 0,
                'total_value': 0.0,
                'avg_sentiment': 0.0,
                'sentiment_sum': 0.0
            }
        
        insider_activity[key]['transaction_count'] += 1
        insider_activity[key]['total_value'] += t.transaction_value or 0
        if t.sentiment_score is not None:
            insider_activity[key]['sentiment_sum'] += t.sentiment_score
    
    # Calculate average sentiment per insider
    for insider in insider_activity.values():
        if insider['transaction_count'] > 0:
            insider['avg_sentiment'] = insider['sentiment_sum'] / insider['transaction_count']
        del insider['sentiment_sum']  # Remove intermediate field
    
    # Sort by transaction count and take top 5
    top_insiders = sorted(
        insider_activity.values(),
        key=lambda x: x['transaction_count'],
        reverse=True
    )[:5]
    
    # Recent transactions (up to 10)
    recent_transactions = transactions[:10]
    
    return InsiderSummaryResponse(
        ticker=ticker,
        company_name=company.name,
        total_transactions=len(transactions),
        total_buys=total_buys,
        total_sells=total_sells,
        total_buy_value=total_buy_value,
        total_sell_value=total_sell_value,
        avg_sentiment=avg_sentiment,
        net_sentiment=net_sentiment,
        recent_transactions=recent_transactions,
        top_insiders=top_insiders,
        period_days=days
    )


@router.get("/trending", response_model=List[TrendingInsiderActivity])
async def get_trending_insider_activity(
    days: int = Query(30, description="Number of days to analyze", ge=1, le=90),
    min_transactions: int = Query(3, description="Minimum number of transactions to be considered trending", ge=1),
    limit: int = Query(20, description="Number of trending tickers to return", le=100),
    db: Session = Depends(get_db)
):
    """
    Get tickers with unusual or significant insider trading activity.
    
    Identifies stocks with:
    - Multiple insider transactions
    - High net buy/sell values
    - Strong sentiment signals (concentrated buying or selling)
    
    **Use cases:**
    - Discover stocks with insider accumulation
    - Identify potential insider selling pressure
    - Find companies with unusual insider activity patterns
    """
    cutoff_date = date.today() - timedelta(days=days)
    
    # Group transactions by ticker
    ticker_groups = db.query(
        InsiderTransaction.ticker,
        InsiderTransaction.company_name,
        func.count(InsiderTransaction.id).label('transaction_count'),
        func.avg(InsiderTransaction.sentiment_score).label('avg_sentiment'),
        func.sum(
            case(
                (InsiderTransaction.transaction_code == 'P', InsiderTransaction.transaction_value),
                else_=0
            )
        ).label('buy_value'),
        func.sum(
            case(
                (InsiderTransaction.transaction_code == 'S', InsiderTransaction.transaction_value),
                else_=0
            )
        ).label('sell_value')
    ).filter(
        InsiderTransaction.transaction_date >= cutoff_date
    ).group_by(
        InsiderTransaction.ticker,
        InsiderTransaction.company_name
    ).having(
        func.count(InsiderTransaction.id) >= min_transactions
    ).all()
    
    # Calculate net buy value and sort
    trending = []
    for group in ticker_groups:
        buy_value = group.buy_value or 0.0
        sell_value = group.sell_value or 0.0
        net_buy_value = buy_value - sell_value
        
        # Get company sector
        company = db.query(Company).filter(Company.ticker == group.ticker).first()
        sector = company.sector if company else None
        
        # Get recent transactions for this ticker
        recent_transactions = db.query(InsiderTransaction).filter(
            InsiderTransaction.ticker == group.ticker,
            InsiderTransaction.transaction_date >= cutoff_date
        ).order_by(desc(InsiderTransaction.transaction_date)).limit(5).all()
        
        trending.append(TrendingInsiderActivity(
            ticker=group.ticker,
            company_name=group.company_name,
            sector=sector,
            transaction_count=group.transaction_count,
            net_buy_value=net_buy_value,
            avg_sentiment=group.avg_sentiment or 0.0,
            recent_transactions=recent_transactions
        ))
    
    # Sort by absolute net buy value (biggest moves, either buy or sell)
    trending.sort(key=lambda x: abs(x.net_buy_value), reverse=True)
    
    # Return top N
    result = trending[:limit]
    
    logger.info(
        f"Found {len(result)} trending insider activity tickers "
        f"(last {days} days, min {min_transactions} transactions)"
    )
    
    return result
