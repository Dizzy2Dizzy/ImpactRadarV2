"""
DataService facade for backward compatibility with existing app.py.

Wraps the repository layer while maintaining the same interface as data_manager.py.
This allows incremental migration without breaking existing functionality.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional

from loguru import logger

from releaseradar.db.session import get_db_context
from releaseradar.db.repositories import (
    CompanyRepository,
    EventRepository,
    UserRepository,
    WatchlistRepository,
    ScannerLogRepository,
)
from releaseradar.domain.scoring import score_event as domain_score_event


class DataService:
    """
    Service facade providing backward-compatible interface to new repository layer.
    
    This maintains the same API as DataManager for gradual migration.
    """
    
    def __init__(self):
        """Initialize database schema."""
        from releaseradar.db.session import init_db
        init_db()
    
    # ========================================================================
    # COMPANY OPERATIONS
    # ========================================================================
    
    def get_companies(
        self,
        tracked_only: bool = False,
        sector: Optional[str] = None,
        with_event_counts: bool = False,
        limit: Optional[int] = None,
    ) -> List[Dict]:
        """Get companies with optional filtering."""
        with get_db_context() as db:
            repo = CompanyRepository(db)
            companies = repo.get_all(tracked_only=tracked_only, sector=sector, limit=limit)
            
            result = []
            for company in companies:
                company_dict = {
                    "id": company.id,
                    "ticker": company.ticker,
                    "name": company.name,
                    "sector": company.sector,
                    "industry": company.industry,
                    "tracked": company.tracked,
                    "created_at": company.created_at,
                }
                
                if with_event_counts:
                    event_repo = EventRepository(db)
                    upcoming = event_repo.get_all(
                        ticker=company.ticker, date_from=datetime.utcnow(), limit=100
                    )
                    company_dict["upcoming_events"] = len(upcoming)
                
                result.append(company_dict)
            
            return result
    
    def create_company(self, ticker: str, name: str, **kwargs) -> Dict:
        """Create a new company."""
        with get_db_context() as db:
            repo = CompanyRepository(db)
            company = repo.create(ticker=ticker, name=name, **kwargs)
            return {
                "id": company.id,
                "ticker": company.ticker,
                "name": company.name,
                "sector": company.sector,
            }
    
    # ========================================================================
    # EVENT OPERATIONS
    # ========================================================================
    
    def get_events(
        self,
        ticker: Optional[str] = None,
        event_type: Optional[str] = None,
        sector: Optional[str] = None,
        direction: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        min_impact: Optional[int] = None,
        watchlist_only: bool = False,
        user_id: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[Dict]:
        """Get events with comprehensive filtering."""
        with get_db_context() as db:
            event_repo = EventRepository(db)
            
            # Handle watchlist filtering
            if watchlist_only and user_id:
                watchlist_repo = WatchlistRepository(db)
                watchlist = watchlist_repo.get_user_watchlist(user_id)
                watchlist_tickers = [item.ticker for item in watchlist]
                
                if not watchlist_tickers:
                    return []
                
                # Get events for watchlist tickers
                events = []
                for ticker_item in watchlist_tickers:
                    ticker_events = event_repo.get_all(
                        ticker=ticker_item,
                        event_type=event_type,
                        sector=sector,
                        direction=direction,
                        date_from=date_from,
                        date_to=date_to,
                        min_impact=min_impact,
                        limit=limit,
                    )
                    events.extend(ticker_events)
            else:
                events = event_repo.get_all(
                    ticker=ticker,
                    event_type=event_type,
                    sector=sector,
                    direction=direction,
                    date_from=date_from,
                    date_to=date_to,
                    min_impact=min_impact,
                    limit=limit,
                )
            
            return [self._event_to_dict(event) for event in events]
    
    def create_event(
        self,
        ticker: str,
        company_name: str,
        event_type: str,
        title: str,
        date: datetime,
        source: str,
        description: Optional[str] = None,
        source_url: Optional[str] = None,
        impact_score: Optional[int] = None,
        direction: Optional[str] = None,
        confidence: Optional[float] = None,
        rationale: Optional[str] = None,
        subsidiary_name: Optional[str] = None,
        sector: Optional[str] = None,
        auto_score: bool = True,
    ) -> Dict:
        """Create a new event with optional auto-scoring."""
        with get_db_context() as db:
            event_repo = EventRepository(db)
            
            # Auto-score if requested
            if auto_score and (impact_score is None or direction is None):
                scoring_result = domain_score_event(
                    event_type=event_type,
                    title=title,
                    description=description or "",
                    sector=sector,
                )
                impact_score = scoring_result.impact_score
                direction = scoring_result.direction
                confidence = scoring_result.confidence
                rationale = scoring_result.rationale
            
            event = event_repo.create(
                ticker=ticker,
                company_name=company_name,
                event_type=event_type,
                title=title,
                description=description,
                date=date,
                source=source,
                source_url=source_url,
                impact_score=impact_score or 50,
                direction=direction,
                confidence=confidence or 0.5,
                rationale=rationale,
                subsidiary_name=subsidiary_name,
                sector=sector,
            )
            
            return self._event_to_dict(event)
    
    def event_exists(
        self, ticker: str, event_type: str, title: str, date: datetime
    ) -> bool:
        """Check if event already exists."""
        with get_db_context() as db:
            repo = EventRepository(db)
            return repo.exists(ticker, event_type, title, date)
    
    # ========================================================================
    # WATCHLIST OPERATIONS
    # ========================================================================
    
    def get_watchlist(self, user_id: int = 1) -> List[Dict]:
        """Get user's watchlist."""
        with get_db_context() as db:
            repo = WatchlistRepository(db)
            items = repo.get_user_watchlist(user_id)
            return [
                {
                    "id": item.id,
                    "ticker": item.ticker,
                    "notes": item.notes,
                    "created_at": item.created_at,
                }
                for item in items
            ]
    
    def add_to_watchlist(
        self, ticker: str, user_id: int = 1, notes: Optional[str] = None
    ) -> Dict:
        """Add ticker to watchlist."""
        with get_db_context() as db:
            repo = WatchlistRepository(db)
            item = repo.add_to_watchlist(user_id, ticker, notes)
            return {"id": item.id, "ticker": item.ticker, "notes": item.notes}
    
    def remove_from_watchlist(self, ticker: str, user_id: int = 1) -> bool:
        """Remove ticker from watchlist."""
        with get_db_context() as db:
            repo = WatchlistRepository(db)
            return repo.remove_from_watchlist(user_id, ticker)
    
    # ========================================================================
    # SCANNER LOG OPERATIONS
    # ========================================================================
    
    def log_scanner_event(
        self, scanner: str, message: str, level: str = "info"
    ) -> None:
        """Log a scanner event."""
        with get_db_context() as db:
            repo = ScannerLogRepository(db)
            repo.log(scanner, message, level)
    
    def get_scanner_status(self, limit: int = 50) -> List[Dict]:
        """Get recent scanner logs."""
        with get_db_context() as db:
            repo = ScannerLogRepository(db)
            logs = repo.get_recent_logs(limit=limit)
            return [
                {
                    "id": log.id,
                    "scanner": log.scanner,
                    "message": log.message,
                    "level": log.level,
                    "timestamp": log.timestamp,
                }
                for log in logs
            ]
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    @staticmethod
    def _event_to_dict(event) -> Dict:
        """Convert Event model to dictionary."""
        return {
            "id": event.id,
            "ticker": event.ticker,
            "company_name": event.company_name,
            "event_type": event.event_type,
            "title": event.title,
            "description": event.description,
            "date": event.date,
            "source": event.source,
            "source_url": event.source_url,
            "impact_score": event.impact_score,
            "direction": event.direction,
            "confidence": event.confidence,
            "rationale": event.rationale,
            "subsidiary_name": event.subsidiary_name,
            "sector": event.sector,
            "created_at": event.created_at,
        }
