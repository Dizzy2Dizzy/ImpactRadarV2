"""
Export API endpoints for CSV data export.

Provides endpoints to export events and portfolio data to CSV format.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import csv
import io

from api.dependencies import get_db
from api.utils.auth import get_current_user_with_plan
from api.ratelimit import limiter, plan_limit
from releaseradar.db.models import Event, UserPortfolio, PortfolioPosition, Company


router = APIRouter(prefix="/export", tags=["export"])


def generate_csv_stream(rows: List[dict], fieldnames: List[str]):
    """Generate a streaming CSV response from rows of data."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    
    for row in rows:
        writer.writerow(row)
    
    output.seek(0)
    return output.getvalue()


@router.get("/events")
@limiter.limit(plan_limit)
async def export_events_csv(
    request: Request,
    from_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    to_date: Optional[str] = Query(None, description="End date (ISO format)"),
    tickers: Optional[List[str]] = Query(None, description="Filter by ticker symbols"),
    sectors: Optional[List[str]] = Query(None, description="Filter by sectors"),
    event_types: Optional[List[str]] = Query(None, description="Filter by event types"),
    user_data: dict = Depends(get_current_user_with_plan),
    db: Session = Depends(get_db)
):
    """
    Export events to CSV file.
    
    Filters events by date range, tickers, sectors, and event types.
    Returns a downloadable CSV file with event data.
    """
    try:
        query = db.query(Event)
        
        filters = []
        
        if from_date:
            try:
                from_dt = datetime.fromisoformat(from_date.replace('Z', '+00:00'))
                filters.append(Event.date >= from_dt)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid from_date format: {from_date}")
        
        if to_date:
            try:
                to_dt = datetime.fromisoformat(to_date.replace('Z', '+00:00'))
                filters.append(Event.date <= to_dt)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid to_date format: {to_date}")
        
        if tickers:
            upper_tickers = [t.upper() for t in tickers]
            filters.append(Event.ticker.in_(upper_tickers))
        
        if sectors:
            filters.append(Event.sector.in_(sectors))
        
        if event_types:
            filters.append(Event.event_type.in_(event_types))
        
        if filters:
            query = query.filter(and_(*filters))
        
        query = query.order_by(Event.date.desc()).limit(10000)
        events = query.all()
        
        fieldnames = [
            'id', 'ticker', 'company_name', 'event_type', 'title', 
            'description', 'date', 'source', 'source_url', 'impact_score',
            'direction', 'confidence', 'sector', 'info_tier', 'detected_at'
        ]
        
        rows = []
        for event in events:
            rows.append({
                'id': event.id,
                'ticker': event.ticker,
                'company_name': event.company_name,
                'event_type': event.event_type,
                'title': event.title,
                'description': (event.description or '')[:500],
                'date': event.date.isoformat() if event.date else '',
                'source': event.source,
                'source_url': event.source_url or '',
                'impact_score': event.impact_score,
                'direction': event.direction or '',
                'confidence': event.confidence,
                'sector': event.sector or '',
                'info_tier': event.info_tier or 'primary',
                'detected_at': event.detected_at.isoformat() if event.detected_at else ''
            })
        
        csv_content = generate_csv_stream(rows, fieldnames)
        
        filename = f"events_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "text/csv; charset=utf-8"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export events: {str(e)}")


@router.get("/portfolio/{portfolio_id}")
@limiter.limit(plan_limit)
async def export_portfolio_csv(
    request: Request,
    portfolio_id: int,
    user_data: dict = Depends(get_current_user_with_plan),
    db: Session = Depends(get_db)
):
    """
    Export portfolio analysis to CSV file.
    
    Returns a CSV with positions and their associated event exposures.
    """
    try:
        portfolio = db.query(UserPortfolio).filter(
            UserPortfolio.id == portfolio_id,
            UserPortfolio.user_id == user_data["user_id"]
        ).first()
        
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found or access denied")
        
        positions = db.query(PortfolioPosition).filter(
            PortfolioPosition.portfolio_id == portfolio_id
        ).all()
        
        fieldnames = [
            'ticker', 'quantity', 'avg_price', 'as_of', 'label',
            'sector', 'industry', 'total_events_30d', 'high_impact_events',
            'avg_impact_score', 'market_value'
        ]
        
        rows = []
        for position in positions:
            company = db.query(Company).filter(Company.ticker == position.ticker).first()
            
            thirty_days_ago = datetime.now() - __import__('datetime').timedelta(days=30)
            events = db.query(Event).filter(
                Event.ticker == position.ticker,
                Event.date >= thirty_days_ago
            ).all()
            
            total_events = len(events)
            high_impact_events = len([e for e in events if (e.impact_score or 0) >= 70])
            avg_impact = sum(e.impact_score or 0 for e in events) / total_events if total_events > 0 else 0
            
            rows.append({
                'ticker': position.ticker,
                'quantity': position.qty,
                'avg_price': position.avg_price,
                'as_of': position.as_of.isoformat() if position.as_of else '',
                'label': position.label or '',
                'sector': company.sector if company else '',
                'industry': company.industry if company else '',
                'total_events_30d': total_events,
                'high_impact_events': high_impact_events,
                'avg_impact_score': round(avg_impact, 2),
                'market_value': round(position.qty * position.avg_price, 2)
            })
        
        csv_content = generate_csv_stream(rows, fieldnames)
        
        safe_name = "".join(c for c in portfolio.name if c.isalnum() or c in (' ', '-', '_')).strip()
        filename = f"portfolio_{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "text/csv; charset=utf-8"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export portfolio: {str(e)}")
