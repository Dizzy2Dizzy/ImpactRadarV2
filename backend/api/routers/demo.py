"""
Demo data loading endpoint for first-time users.

Provides sample portfolio, watchlist, and alerts to help new users
understand how the platform works without providing their own data.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from api.dependencies import get_db
from api.utils.auth import get_current_user_id
from releaseradar.db.models import UserPortfolio, PortfolioPosition, WatchlistItem, Alert, Company
from database import get_db as get_legacy_db

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/load")
async def load_demo_data(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Load demo data for new users.
    
    Creates sample portfolio holdings, watchlist items, and an alert
    to help users understand the platform functionality.
    """
    
    # Check if user already has portfolio
    existing_portfolio = db.query(UserPortfolio).filter(
        UserPortfolio.user_id == user_id
    ).first()
    
    portfolio_count = 0
    if not existing_portfolio:
        # Create portfolio
        portfolio = UserPortfolio(user_id=user_id)
        db.add(portfolio)
        db.flush()
        
        # Add demo holdings
        demo_holdings = [
            {"ticker": "AAPL", "qty": 100, "avg_price": 150.00},
            {"ticker": "MSFT", "qty": 50, "avg_price": 300.00},
            {"ticker": "TSLA", "qty": 25, "avg_price": 200.00},
        ]
        
        for holding in demo_holdings:
            position = PortfolioPosition(
                portfolio_id=portfolio.id,
                ticker=holding["ticker"],
                qty=holding["qty"],
                avg_price=holding["avg_price"],
                as_of=datetime.now().date()
            )
            db.add(position)
            portfolio_count += 1
    else:
        # Count existing positions
        portfolio_count = db.query(PortfolioPosition).filter(
            PortfolioPosition.portfolio_id == existing_portfolio.id
        ).count()
    
    # Check if user has watchlist items
    existing_watchlist_count = db.query(WatchlistItem).filter(
        WatchlistItem.user_id == user_id
    ).count()
    
    watchlist_count = existing_watchlist_count
    if existing_watchlist_count == 0:
        # Get company IDs for demo tickers
        demo_tickers = ["NVDA", "GOOGL", "META"]
        
        for ticker in demo_tickers:
            # Find company by ticker
            company = db.query(Company).filter(Company.ticker == ticker).first()
            
            if company:
                watchlist_item = WatchlistItem(
                    user_id=user_id,
                    company_id=company.id,
                    notes="Demo watchlist item"
                )
                db.add(watchlist_item)
                watchlist_count += 1
    
    # Check if user has alerts
    existing_alerts_count = db.query(Alert).filter(
        Alert.user_id == user_id
    ).count()
    
    alerts_count = existing_alerts_count
    if existing_alerts_count == 0:
        # Create demo alert
        alert = Alert(
            user_id=user_id,
            name="High Impact Events",
            min_score=70,
            tickers=["AAPL", "MSFT"],
            event_types=["earnings", "fda_approval"],
            channels=["in_app"],
            active=True
        )
        db.add(alert)
        alerts_count += 1
    
    db.commit()
    
    return {
        "success": True,
        "message": "Demo data loaded successfully",
        "portfolio_holdings": portfolio_count,
        "watchlist_items": watchlist_count,
        "alerts": alerts_count
    }
