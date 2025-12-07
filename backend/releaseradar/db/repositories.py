"""
Repository pattern for data access.

Provides clean interfaces for database operations, abstracting SQLAlchemy details.
Each repository handles a single aggregate (Company, Event, User, Watchlist).
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy import and_, or_, func, desc
from sqlalchemy.orm import Session
from loguru import logger

from releaseradar.db.models import Company, Event, User, WatchlistItem, ScannerLog, VerificationCode
from releaseradar.utils.errors import RecordNotFoundError, DuplicateRecordError


class CompanyRepository:
    """Repository for Company operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, company_id: int) -> Optional[Company]:
        """Get company by ID."""
        return self.db.query(Company).filter(Company.id == company_id).first()
    
    def get_by_ticker(self, ticker: str) -> Optional[Company]:
        """Get company by ticker."""
        return self.db.query(Company).filter(Company.ticker == ticker.upper()).first()
    
    def get_all(
        self,
        tracked_only: bool = False,
        sector: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Company]:
        """Get all companies with optional filtering."""
        query = self.db.query(Company)
        
        if tracked_only:
            query = query.filter(Company.tracked == True)
        
        if sector:
            query = query.filter(Company.sector == sector)
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def create(self, ticker: str, name: str, **kwargs) -> Company:
        """Create a new company."""
        existing = self.get_by_ticker(ticker)
        if existing:
            raise DuplicateRecordError(f"Company with ticker {ticker} already exists")
        
        company = Company(ticker=ticker.upper(), name=name, **kwargs)
        self.db.add(company)
        self.db.flush()
        return company
    
    def update(self, company_id: int, **kwargs) -> Company:
        """Update a company."""
        company = self.get_by_id(company_id)
        if not company:
            raise RecordNotFoundError(f"Company {company_id} not found")
        
        for key, value in kwargs.items():
            if hasattr(company, key):
                setattr(company, key, value)
        
        company.updated_at = datetime.utcnow()
        self.db.flush()
        return company


class EventRepository:
    """Repository for Event operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, event_id: int) -> Optional[Event]:
        """Get event by ID."""
        return self.db.query(Event).filter(Event.id == event_id).first()
    
    def get_all(
        self,
        ticker: Optional[str] = None,
        event_type: Optional[str] = None,
        sector: Optional[str] = None,
        direction: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        min_impact: Optional[int] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Event]:
        """Get events with comprehensive filtering."""
        query = self.db.query(Event)
        
        if ticker:
            query = query.filter(Event.ticker == ticker.upper())
        
        if event_type:
            query = query.filter(Event.event_type == event_type)
        
        if sector:
            query = query.filter(Event.sector == sector)
        
        if direction:
            query = query.filter(Event.direction == direction)
        
        if date_from:
            query = query.filter(Event.date >= date_from)
        
        if date_to:
            query = query.filter(Event.date <= date_to)
        
        if min_impact is not None:
            query = query.filter(Event.impact_score >= min_impact)
        
        query = query.order_by(desc(Event.date))
        
        if offset:
            query = query.offset(offset)
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def create(self, **kwargs) -> Event:
        """Create a new event."""
        event = Event(**kwargs)
        self.db.add(event)
        self.db.flush()
        return event
    
    def exists(self, ticker: str, event_type: str, title: str, date: datetime) -> bool:
        """Check if event already exists (simple dedupe)."""
        return (
            self.db.query(Event)
            .filter(
                Event.ticker == ticker.upper(),
                Event.event_type == event_type,
                Event.title == title,
                Event.date == date,
            )
            .first()
            is not None
        )


class UserRepository:
    """Repository for User operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.db.query(User).filter(User.email == email.lower()).first()
    
    def get_by_phone(self, phone: str) -> Optional[User]:
        """Get user by phone."""
        return self.db.query(User).filter(User.phone == phone).first()
    
    def create(self, password_hash: str, email: Optional[str] = None, phone: Optional[str] = None, **kwargs) -> User:
        """Create a new user."""
        if email and self.get_by_email(email):
            raise DuplicateRecordError(f"User with email {email} already exists")
        
        if phone and self.get_by_phone(phone):
            raise DuplicateRecordError(f"User with phone {phone} already exists")
        
        user = User(
            email=email.lower() if email else None,
            phone=phone,
            password_hash=password_hash,
            **kwargs,
        )
        self.db.add(user)
        self.db.flush()
        return user
    
    def update(self, user_id: int, **kwargs) -> User:
        """Update a user."""
        user = self.get_by_id(user_id)
        if not user:
            raise RecordNotFoundError(f"User {user_id} not found")
        
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        self.db.flush()
        return user
    
    def update_last_login(self, user_id: int) -> None:
        """Update user's last login timestamp."""
        user = self.get_by_id(user_id)
        if user:
            user.last_login = datetime.utcnow()
            self.db.flush()


class WatchlistRepository:
    """Repository for Watchlist operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_watchlist(self, user_id: int) -> List[WatchlistItem]:
        """Get all watchlist items for a user."""
        return (
            self.db.query(WatchlistItem)
            .filter(WatchlistItem.user_id == user_id)
            .order_by(WatchlistItem.created_at.desc())
            .all()
        )
    
    def add_to_watchlist(self, user_id: int, ticker: str, notes: Optional[str] = None) -> WatchlistItem:
        """Add a ticker to user's watchlist."""
        existing = (
            self.db.query(WatchlistItem)
            .filter(WatchlistItem.user_id == user_id, WatchlistItem.ticker == ticker.upper())
            .first()
        )
        
        if existing:
            raise DuplicateRecordError(f"Ticker {ticker} already in watchlist")
        
        item = WatchlistItem(user_id=user_id, ticker=ticker.upper(), notes=notes)
        self.db.add(item)
        self.db.flush()
        return item
    
    def remove_from_watchlist(self, user_id: int, ticker: str) -> bool:
        """Remove a ticker from user's watchlist."""
        item = (
            self.db.query(WatchlistItem)
            .filter(WatchlistItem.user_id == user_id, WatchlistItem.ticker == ticker.upper())
            .first()
        )
        
        if item:
            self.db.delete(item)
            self.db.flush()
            return True
        return False
    
    def is_in_watchlist(self, user_id: int, ticker: str) -> bool:
        """Check if ticker is in user's watchlist."""
        return (
            self.db.query(WatchlistItem)
            .filter(WatchlistItem.user_id == user_id, WatchlistItem.ticker == ticker.upper())
            .first()
            is not None
        )


class ScannerLogRepository:
    """Repository for ScannerLog operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def log(self, scanner: str, message: str, level: str = "info") -> ScannerLog:
        """Create a new scanner log entry."""
        log_entry = ScannerLog(scanner=scanner, message=message, level=level)
        self.db.add(log_entry)
        self.db.flush()
        return log_entry
    
    def get_recent_logs(self, scanner: Optional[str] = None, limit: int = 100) -> List[ScannerLog]:
        """Get recent scanner logs."""
        query = self.db.query(ScannerLog).order_by(desc(ScannerLog.timestamp))
        
        if scanner:
            query = query.filter(ScannerLog.scanner == scanner)
        
        return query.limit(limit).all()
