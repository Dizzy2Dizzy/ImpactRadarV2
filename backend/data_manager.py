"""
Data Manager for Impact Radar

Clean repository/service layer for database operations.
No magic initialization - all data seeding happens via explicit seed utilities.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple, Union
from sqlalchemy import and_, or_, func
from database import get_db, close_db, close_db_session, init_db, Company, Event, WatchlistItem, ScannerLog, User
from releaseradar.db.models import EventStats
from impact_scoring import score_event
from analytics.scoring import compute_event_score
import logging
from urllib.parse import urlparse
from scoring_customizer import ScoringCustomizer
from releaseradar.services.quality_metrics import QualityMetricsService
from releaseradar.utils.datetime import convert_to_est_date
from services.projection_calculator import calculate_projection_for_event

# Configure logging for validation warnings
logger = logging.getLogger(__name__)

# Canonical event types (must match impact_scoring.py EVENT_TYPE_SCORES)
VALID_EVENT_TYPES = {
    # FDA Events
    'fda_approval', 'fda_rejection', 'fda_adcom', 'fda_crl', 'fda_safety_alert', 'fda_announcement',
    # SEC Filings
    'sec_8k', 'sec_10k', 'sec_10q', 'sec_s1', 'sec_13d', 'sec_13g', 'sec_def14a', 'sec_filing',
    # Earnings & Guidance
    'earnings', 'guidance_raise', 'guidance_lower', 'guidance_withdraw',
    # Corporate Actions
    'merger_acquisition', 'divestiture', 'restructuring', 'investigation', 'lawsuit', 'executive_change',
    # Product Events
    'product_launch', 'product_delay', 'product_recall', 'flagship_launch',
    # Other
    'analyst_day', 'conference_presentation', 'press_release', 'manual_entry'
}


class DataManager:
    """
    Repository/service layer for Impact Radar database operations.
    Handles Companies, Events, Watchlist, and Scanner Logs.
    """
    
    def __init__(self):
        """Initialize data manager. Database schema is initialized at application startup."""
        pass
    
    # ============================================================================
    # COMPANY OPERATIONS
    # ============================================================================
    
    def get_companies(
        self,
        tracked_only: bool = False,
        sector: Optional[str] = None,
        with_event_counts: bool = False
    ) -> List[Dict]:
        """
        Get companies with optional filtering.
        
        Args:
            tracked_only: Only return tracked companies
            sector: Filter by sector
            with_event_counts: Include event counts in results
            
        Returns:
            List of company dictionaries
        """
        db = get_db()
        try:
            query = db.query(Company)
            
            if tracked_only:
                query = query.filter(Company.tracked == True)
            
            if sector:
                query = query.filter(Company.sector == sector)
            
            # Optimize event counts with single aggregated subquery (prevents N+1)
            if with_event_counts:
                # Create subquery that groups events by ticker and counts them
                counts_subq = db.query(
                    Event.ticker.label("ticker"),
                    func.count(Event.id).label("event_count")
                ).group_by(Event.ticker).subquery()
                
                # Outer join to get counts (use COALESCE for companies with 0 events)
                query = query.outerjoin(
                    counts_subq,
                    Company.ticker == counts_subq.c.ticker
                ).add_columns(
                    func.coalesce(counts_subq.c.event_count, 0).label("event_count")
                )
                
                query = query.order_by(Company.name)
                companies_with_counts = query.all()
                
                # Build result from joined query
                result = []
                for row in companies_with_counts:
                    company = row[0]  # Company object
                    event_count = row[1]  # event_count column
                    
                    result.append({
                        'id': company.id,
                        'ticker': company.ticker,
                        'name': company.name,
                        'sector': company.sector,
                        'industry': company.industry,
                        'parent_id': company.parent_id,
                        'tracked': company.tracked,
                        'created_at': company.created_at,
                        'updated_at': company.updated_at,
                        'event_count': event_count
                    })
                
                return result
            else:
                # No event counts needed - simple query
                companies = query.order_by(Company.name).all()
                
                result = []
                for company in companies:
                    result.append({
                        'id': company.id,
                        'ticker': company.ticker,
                        'name': company.name,
                        'sector': company.sector,
                        'industry': company.industry,
                        'parent_id': company.parent_id,
                        'tracked': company.tracked,
                        'created_at': company.created_at,
                        'updated_at': company.updated_at
                    })
                
                return result
        finally:
            close_db_session(db)
    
    def get_company(self, ticker: str) -> Optional[Dict]:
        """Get a single company by ticker."""
        db = get_db()
        try:
            company = db.query(Company).filter(Company.ticker == ticker).first()
            if company:
                return {
                    'id': company.id,
                    'ticker': company.ticker,
                    'name': company.name,
                    'sector': company.sector,
                    'industry': company.industry,
                    'parent_id': company.parent_id,
                    'tracked': company.tracked,
                    'created_at': company.created_at,
                    'updated_at': company.updated_at
                }
            return None
        finally:
            close_db_session(db)
    
    def add_company(
        self,
        ticker: str,
        name: str,
        sector: Optional[str] = None,
        industry: Optional[str] = None,
        parent_id: Optional[int] = None,
        tracked: bool = True
    ) -> Dict:
        """
        Add a new company.
        
        Returns:
            Created company dictionary
        """
        db = get_db()
        try:
            company = Company(
                ticker=ticker,
                name=name,
                sector=sector,
                industry=industry,
                parent_id=parent_id,
                tracked=tracked
            )
            db.add(company)
            db.commit()
            db.refresh(company)
            
            return {
                'id': company.id,
                'ticker': company.ticker,
                'name': company.name,
                'sector': company.sector,
                'industry': company.industry,
                'parent_id': company.parent_id,
                'tracked': company.tracked
            }
        except Exception as e:
            db.rollback()
            raise e
        finally:
            close_db_session(db)
    
    def update_company_tracked(self, ticker: str, tracked: bool) -> bool:
        """Update company tracked status."""
        db = get_db()
        try:
            company = db.query(Company).filter(Company.ticker == ticker).first()
            if company:
                company.tracked = tracked
                company.updated_at = datetime.utcnow()
                db.commit()
                return True
            return False
        finally:
            close_db_session(db)
    
    # ============================================================================
    # EVENT OPERATIONS
    # ============================================================================
    
    def get_events(
        self,
        ticker: Optional[Union[str, List[str]]] = None,
        event_type: Optional[str] = None,
        sector: Optional[str] = None,
        direction: Optional[str] = None,
        min_impact: Optional[int] = None,
        max_impact: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        watchlist_only: bool = False,
        portfolio_only: bool = False,
        user_id: Optional[int] = None,
        limit: Optional[int] = None,
        upcoming_only: bool = False,
        info_tier: Optional[str] = None,
        empty_means_all: bool = False
    ) -> List[Dict]:
        """
        Get events with comprehensive filtering options.
        
        Args:
            ticker: Filter by ticker (single string or list of tickers for batch query)
            event_type: Filter by event type
            sector: Filter by sector
            direction: Filter by direction (positive/negative/neutral/uncertain)
            min_impact: Minimum impact score
            max_impact: Maximum impact score
            start_date: Events on or after this date
            end_date: Events on or before this date
            watchlist_only: Only events for user's watchlist tickers
            portfolio_only: Only events for user's portfolio tickers
            user_id: User ID for watchlist/portfolio filtering
            limit: Maximum number of events to return
            upcoming_only: Only future events
            info_tier: Filter by information tier ("primary", "secondary", "both", or None for all)
            empty_means_all: If True, empty ticker list [] means "show all events" (user mode).
                            If False, empty ticker list [] means "no matches, return empty" (default).
            
        Returns:
            List of event dictionaries
        """
        db = get_db()
        try:
            query = db.query(Event)
            
            # Handle ticker filtering with proper empty list semantics
            if ticker is not None:
                if isinstance(ticker, str):
                    # Single ticker query
                    query = query.filter(Event.ticker == ticker)
                elif isinstance(ticker, list):
                    if len(ticker) == 0:
                        if empty_means_all:
                            # User mode: empty watchlist/portfolio → show all events (good UX)
                            pass  # Don't apply filter
                        else:
                            # Explicit empty filter: no eligible tickers → return empty results
                            return []
                    else:
                        # Batch query for multiple tickers
                        query = query.filter(Event.ticker.in_(ticker))
            # If ticker is None, don't apply filter (show all events)
            
            if event_type:
                query = query.filter(Event.event_type == event_type)
            
            if sector:
                query = query.filter(Event.sector == sector)
            
            if direction:
                query = query.filter(Event.direction == direction)
            
            if info_tier and info_tier != "both":
                query = query.filter(Event.info_tier == info_tier)
            
            if min_impact is not None:
                query = query.filter(Event.impact_score >= min_impact)
            
            if max_impact is not None:
                query = query.filter(Event.impact_score <= max_impact)
            
            if start_date:
                query = query.filter(Event.date >= start_date)
            
            if end_date:
                query = query.filter(Event.date <= end_date)
            
            if upcoming_only:
                query = query.filter(Event.date >= datetime.utcnow())
            
            if watchlist_only and user_id:
                watchlist_tickers = db.query(WatchlistItem.ticker).filter(
                    WatchlistItem.user_id == user_id
                ).all()
                tickers = [t[0] for t in watchlist_tickers]
                if not tickers:
                    if empty_means_all:
                        # User mode: empty watchlist → show all
                        pass  # Don't apply filter
                    else:
                        # Explicit empty: no matches → return empty
                        return []
                else:
                    query = query.filter(Event.ticker.in_(tickers))
            
            if portfolio_only and user_id:
                user_portfolio = self.get_portfolio(user_id)
                if not user_portfolio:
                    if empty_means_all:
                        # User mode: empty portfolio → show all
                        pass  # Don't apply filter
                    else:
                        # Explicit empty: no matches → return empty
                        return []
                else:
                    tickers = [pos['ticker'] for pos in user_portfolio]
                    query = query.filter(Event.ticker.in_(tickers))
            
            query = query.order_by(Event.date.desc())
            
            if limit:
                query = query.limit(limit)
            
            events = query.all()
            
            return [self._event_to_dict(event, user_id=user_id) for event in events]
        finally:
            close_db_session(db)
    
    def get_event(self, event_id: int, user_id: Optional[int] = None) -> Optional[Dict]:
        """Get a single event by ID with optional user scoring weights."""
        db = get_db()
        try:
            event = db.query(Event).filter(Event.id == event_id).first()
            if event:
                return self._event_to_dict(event, user_id=user_id)
            return None
        finally:
            close_db_session(db)
    
    def add_event(
        self,
        ticker: str,
        company_name: str,
        event_type: str,
        title: str,
        date: datetime,
        source: str,
        description: Optional[str] = None,
        source_url: Optional[str] = None,
        subsidiary_name: Optional[str] = None,
        sector: Optional[str] = None,
        auto_score: bool = True,
        info_tier: str = "primary",
        info_subtype: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Add a new event with automatic impact scoring.
        
        Args:
            auto_score: If True, automatically calculate impact score using impact_scoring module
            metadata: Optional metadata dict (e.g., {"8k_items": ["2.02", "5.02"]})
            
        Returns:
            Created event dictionary
        """
        metadata = metadata or {}
        
        # Validate event_type is canonical
        event_type_lower = event_type.lower()
        if event_type_lower not in VALID_EVENT_TYPES:
            logger.warning(
                f"Non-canonical event_type '{event_type}' provided. "
                f"Defaulting to 'press_release'. "
                f"Valid types: {sorted(VALID_EVENT_TYPES)}"
            )
            event_type = 'press_release'
        
        # Validate source_url (warn if missing or invalid)
        if source_url:
            # Strip whitespace and validate URL format
            source_url = source_url.strip()
            if not (source_url.startswith('http://') or source_url.startswith('https://')):
                logger.warning(
                    f"Invalid source_url for event '{title[:50]}': {source_url}. "
                    f"URL must start with http:// or https://. Setting to None."
                )
                source_url = None
            else:
                # Validate URL is parseable
                try:
                    parsed = urlparse(source_url)
                    if not parsed.netloc:
                        logger.warning(
                            f"Invalid source_url for event '{title[:50]}': {source_url}. "
                            f"URL has no domain. Setting to None."
                        )
                        source_url = None
                except Exception as e:
                    logger.warning(
                        f"Failed to parse source_url for event '{title[:50]}': {source_url}. "
                        f"Error: {e}. Setting to None."
                    )
                    source_url = None
        
        if not source_url:
            logger.info(
                f"Event '{title[:50]}' ({ticker}, {event_type}) has no source_url. "
                f"External link will not be available in UI."
            )
        
        db = get_db()
        try:
            # Check for duplicate by source_url (database-level deduplication)
            if source_url:
                from scanners.utils import canonicalize_url
                canonical_url = canonicalize_url(source_url)
                
                # Only use canonical form if valid, otherwise keep original
                if canonical_url:
                    # Check both canonical and raw forms to catch legacy data
                    existing_event = db.query(Event).filter(
                        or_(
                            func.lower(Event.source_url) == canonical_url.lower(),
                            func.lower(Event.source_url) == source_url.lower()
                        )
                    ).first()
                    
                    if existing_event:
                        logger.info(
                            f"Event with source_url '{source_url}' already exists (ID: {existing_event.id}). "
                            f"Skipping duplicate insertion."
                        )
                        return self._event_to_dict(existing_event)
                    
                    # Store canonicalized URL for future exact matching
                    source_url = canonical_url
                else:
                    # Fallback to raw URL comparison if canonicalization fails
                    existing_event = db.query(Event).filter(
                        func.lower(Event.source_url) == source_url.lower()
                    ).first()
                    
                    if existing_event:
                        logger.info(
                            f"Event with source_url '{source_url}' already exists (ID: {existing_event.id}). "
                            f"Skipping duplicate insertion."
                        )
                        return self._event_to_dict(existing_event)
                    
                    # Keep original URL since canonicalization failed
                    logger.warning(
                        f"URL canonicalization failed for '{source_url}', using original URL"
                    )
            
            # Create event first with default scores
            event = Event(
                ticker=ticker,
                company_name=company_name,
                event_type=event_type,
                title=title,
                description=description,
                date=date,
                source=source,
                source_url=source_url,
                impact_score=50,  # Temporary default
                direction='neutral',  # Temporary default
                confidence=0.5,  # Temporary default
                rationale=None,
                subsidiary_name=subsidiary_name,
                sector=sector,
                info_tier=info_tier,
                info_subtype=info_subtype,
                impact_p_move=None,
                impact_p_up=None,
                impact_p_down=None,
                impact_score_version=1
            )
            
            db.add(event)
            db.flush()  # Get event ID without committing
            
            # Auto-score the event using ImpactScorer (with 8-K item support)
            if auto_score:
                try:
                    # Primary: Use ImpactScorer which handles metadata (8-K items) and direction properly
                    result = score_event(
                        event_type=event_type,
                        title=title,
                        description=description or "",
                        sector=sector or "Unknown",
                        metadata=metadata
                    )
                    event.impact_score = result.get('impact_score', 50)
                    event.direction = result.get('direction', 'neutral')
                    event.confidence = result.get('confidence', 0.5)
                    event.rationale = result.get('rationale', '')
                    
                    logger.info(
                        f"Scored event {event.id} ({ticker}): "
                        f"score={event.impact_score}, direction={event.direction}, "
                        f"confidence={event.confidence:.2f}"
                    )
                    
                    # Try to enhance with context-aware scoring from analytics engine
                    try:
                        score_result = compute_event_score(
                            event_id=event.id,
                            ticker=ticker,
                            event_type=event_type,
                            event_date=date,
                            source=source,
                            sector=sector,
                            db=db,
                            info_tier=info_tier,
                            info_subtype=info_subtype
                        )
                        
                        # Blend scores: use analytics score but keep ImpactScorer direction
                        event.impact_score = score_result.get('final_score', event.impact_score)
                        event.confidence = min(event.confidence, score_result.get('confidence', 50) / 100.0)
                        
                        # Enhance rationale with context factors
                        context_rationale = '; '.join(score_result.get('rationale', []))
                        if context_rationale:
                            event.rationale = f"{event.rationale} | Context: {context_rationale}"
                        
                        logger.info(f"Enhanced event {event.id} with context scoring: {event.impact_score}")
                    except Exception as e_context:
                        logger.debug(f"Context scoring enhancement skipped for event {event.id}: {e_context}")
                    
                except Exception as e:
                    logger.error(f"Event scoring failed: {e}, using defaults")
                    # Keep the default values set during event creation
            
            # Apply ML predictions from Market Echo Engine (if models available)
            try:
                from releaseradar.ml.serving import MLScoringService
                ml_service = MLScoringService(db)
                ml_prediction = ml_service.predict_single(
                    event_id=event.id,
                    horizon="1d",
                    confidence_threshold=0.4,  # Lower threshold to include more predictions
                    use_blending=True
                )
                
                if ml_prediction:
                    # Update event with ML predictions
                    event.ml_adjusted_score = ml_prediction.ml_adjusted_score
                    event.ml_confidence = ml_prediction.ml_confidence
                    event.ml_model_version = ml_prediction.ml_model_version
                    event.model_source = ml_prediction.model_source
                    event.delta_applied = ml_prediction.delta_applied
                    
                    # If ML model predicts negative return and confidence is high, override direction
                    if ml_prediction.predicted_return_1d is not None:
                        if ml_prediction.predicted_return_1d < -1.0 and ml_prediction.ml_confidence > 0.5:
                            event.direction = 'negative'
                            logger.info(f"ML predicted negative return ({ml_prediction.predicted_return_1d:.2f}%), overriding direction to 'negative'")
                        elif ml_prediction.predicted_return_1d > 1.0 and ml_prediction.ml_confidence > 0.5:
                            event.direction = 'positive'
                            logger.info(f"ML predicted positive return ({ml_prediction.predicted_return_1d:.2f}%), overriding direction to 'positive'")
                    
                    logger.info(
                        f"ML prediction applied for event {event.id}: "
                        f"base={event.impact_score}, ml={ml_prediction.ml_adjusted_score}, "
                        f"delta={ml_prediction.delta_applied:.1f}, source={ml_prediction.model_source}, "
                        f"conf={ml_prediction.ml_confidence:.2f}"
                    )
                else:
                    logger.debug(f"No ML prediction available for event {event.id}, using deterministic scoring only")
            except Exception as e:
                logger.warning(f"ML scoring failed for event {event.id}: {e}, continuing with deterministic scoring")
            
            db.commit()
            db.refresh(event)
            
            # Record audit log for event creation
            try:
                quality_service = QualityMetricsService(db)
                quality_service.record_audit_log(
                    entity_type="event",
                    entity_id=event.id,
                    action="create",
                    performed_by=None,  # System-created event
                    diff_json={
                        "ticker": ticker,
                        "event_type": event_type,
                        "title": title,
                        "date": date.isoformat(),
                        "impact_score": event.impact_score,
                        "source": source,
                        "info_tier": info_tier
                    }
                )
                logger.debug(f"Audit log created for event {event.id}")
            except Exception as e:
                logger.warning(f"Failed to record audit log for event {event.id}: {e}")
            
            # Broadcast new event via WebSocket
            try:
                from api.websocket.hub import broadcast_event_new_sync
                event_dict = self._event_to_dict(event)
                broadcast_event_new_sync(event_dict)
            except Exception as e:
                logger.warning(f"Failed to broadcast event.new via WebSocket: {e}")
            
            # Trigger alert dispatcher for new event
            try:
                from alerts.dispatch import dispatch_alerts_for_event
                dispatch_alerts_for_event(event.id, db)
            except Exception as e:
                logger.warning(f"Failed to dispatch alerts for event {event.id}: {e}")
            
            return self._event_to_dict(event)
        except Exception as e:
            db.rollback()
            raise e
        finally:
            close_db_session(db)
    
    def event_exists(
        self,
        ticker: str,
        event_type: str,
        date: datetime,
        title: str
    ) -> bool:
        """
        Check if an event already exists (for duplicate prevention).
        
        Returns:
            True if event exists, False otherwise
        """
        db = get_db()
        try:
            event = db.query(Event).filter(
                and_(
                    Event.ticker == ticker,
                    Event.event_type == event_type,
                    Event.date == date,
                    Event.title == title
                )
            ).first()
            return event is not None
        finally:
            close_db_session(db)
    
    def _event_to_dict(self, event: Event, user_id: Optional[int] = None) -> Dict:
        """
        Convert Event model to dictionary with EST-formatted dates.
        
        Args:
            event: Event model instance
            user_id: Optional user ID to apply custom scoring weights
        
        Returns:
            Event dictionary with optional adjusted_impact_score
        """
        # Handle ML provenance fields
        # Only set ML fields when there's an actual ML prediction (ml_model_version exists)
        # Otherwise, leave them as null so frontend knows it's deterministic only
        has_ml_prediction = event.ml_model_version is not None
        
        if has_ml_prediction:
            # Event has ML prediction - use ML values
            model_source = event.model_source or "deterministic"
            ml_adjusted_score = event.ml_adjusted_score
            ml_confidence = event.ml_confidence
        else:
            # No ML prediction - mark as deterministic and keep ML fields null
            model_source = "deterministic"
            ml_adjusted_score = event.impact_score  # Show base score as the display score
            ml_confidence = None  # Don't show ML confidence for deterministic-only events
        
        # Calculate authentic projections for events that don't have them
        impact_p_move = event.impact_p_move
        impact_p_up = event.impact_p_up
        impact_p_down = event.impact_p_down
        direction = event.direction
        
        if impact_p_move is None:
            try:
                # Build minimal event dict for projection calculator
                event_dict = {
                    'id': event.id,
                    'ticker': event.ticker,
                    'event_type': event.event_type,
                    'title': event.title,
                    'direction': event.direction or 'neutral',
                    'impact_score': event.impact_score,
                    'ml_adjusted_score': ml_adjusted_score,
                    'sector': event.sector,
                    'confidence': event.confidence,
                }
                projection = calculate_projection_for_event(event_dict)
                
                # Use absolute value for p_move (probability magnitude, always positive)
                impact_p_move = abs(projection.projected_move_pct) / 100.0
                impact_p_up = projection.probability_up
                impact_p_down = projection.probability_down
                
                # Update direction based on projection if currently neutral
                if not direction or direction == 'neutral':
                    if projection.projected_direction == 'upward':
                        direction = 'positive'
                    elif projection.projected_direction == 'downward':
                        direction = 'negative'
                    else:
                        direction = 'neutral'
            except Exception as e:
                logger.debug(f"Failed to calculate projection for event {event.id}: {e}")
                # Keep None values if projection fails
        
        result = {
            'id': event.id,
            'ticker': event.ticker,
            'company_name': event.company_name,
            'event_type': event.event_type,
            'title': event.title,
            'description': event.description,
            'date': convert_to_est_date(event.date),
            'source': event.source,
            'source_url': event.source_url,
            'impact_score': event.impact_score,
            'direction': direction,
            'confidence': event.confidence,
            'rationale': event.rationale,
            'subsidiary_name': event.subsidiary_name,
            'sector': event.sector,
            'info_tier': event.info_tier,
            'info_subtype': event.info_subtype,
            'impact_p_move': impact_p_move,
            'impact_p_up': impact_p_up,
            'impact_p_down': impact_p_down,
            'impact_score_version': event.impact_score_version,
            'ml_adjusted_score': ml_adjusted_score,
            'model_source': model_source,
            'ml_model_version': event.ml_model_version,
            'ml_confidence': ml_confidence,
            'delta_applied': event.delta_applied,
            'created_at': convert_to_est_date(event.created_at),
            # Bearish signal fields
            'bearish_signal': getattr(event, 'bearish_signal', False) or False,
            'bearish_score': getattr(event, 'bearish_score', None),
            'bearish_confidence': getattr(event, 'bearish_confidence', None),
            'bearish_rationale': getattr(event, 'bearish_rationale', None),
        }
        
        # Apply user scoring preferences if user_id is provided
        if user_id:
            try:
                customizer = ScoringCustomizer()
                preferences = customizer.get_user_preferences(user_id)
                adjusted_score = customizer.apply_user_weights(
                    base_score=event.impact_score,
                    event_type=event.event_type,
                    sector=event.sector,
                    preferences=preferences
                )
                result['adjusted_impact_score'] = adjusted_score
            except Exception as e:
                logger.warning(f"Failed to apply user scoring weights for user {user_id}: {e}")
                result['adjusted_impact_score'] = event.impact_score
        
        return result
    
    # ============================================================================
    # WATCHLIST OPERATIONS
    # ============================================================================
    
    def get_watchlist(self, user_id: Optional[int] = None) -> List[Dict]:
        """Get user's watchlist items."""
        db = get_db()
        try:
            query = db.query(WatchlistItem)
            
            if user_id:
                query = query.filter(WatchlistItem.user_id == user_id)
            
            items = query.order_by(WatchlistItem.created_at.desc()).all()
            
            return [{
                'id': item.id,
                'user_id': item.user_id,
                'ticker': item.ticker,
                'notes': item.notes,
                'created_at': item.created_at
            } for item in items]
        finally:
            close_db_session(db)
    
    def get_portfolio(self, user_id: int) -> List[Dict]:
        """
        Get user's portfolio positions.
        
        Args:
            user_id: User ID
            
        Returns:
            List of portfolio position dictionaries with ticker, qty, avg_price, etc.
            Returns empty list if user has no portfolio.
        """
        db = get_db()
        try:
            from releaseradar.db.models import UserPortfolio, PortfolioPosition
            
            # Get all portfolios for the user
            portfolios = db.query(UserPortfolio).filter(
                UserPortfolio.user_id == user_id
            ).all()
            
            if not portfolios:
                return []
            
            # Get all positions from all portfolios
            portfolio_ids = [p.id for p in portfolios]
            positions = db.query(PortfolioPosition).filter(
                PortfolioPosition.portfolio_id.in_(portfolio_ids)
            ).all()
            
            return [{
                'id': pos.id,
                'portfolio_id': pos.portfolio_id,
                'ticker': pos.ticker,
                'qty': pos.qty,
                'avg_price': pos.avg_price,
                'as_of': pos.as_of,
                'label': pos.label,
                'created_at': pos.created_at,
                'updated_at': pos.updated_at
            } for pos in positions]
        finally:
            close_db_session(db)
    
    def get_user_active_tickers(self, user_id: int, mode: str) -> List[str]:
        """
        Get list of active tickers based on dashboard mode.
        
        Args:
            user_id: User ID
            mode: Dashboard mode ('watchlist' or 'portfolio')
            
        Returns:
            List of ticker symbols
        """
        if mode == 'watchlist':
            watchlist_items = self.get_watchlist(user_id)
            return [item['ticker'] for item in watchlist_items]
        elif mode == 'portfolio':
            db = get_db()
            try:
                from releaseradar.db.models import UserPortfolio, PortfolioPosition
                
                # Get all portfolios for the user
                portfolios = db.query(UserPortfolio).filter(
                    UserPortfolio.user_id == user_id
                ).all()
                
                if not portfolios:
                    return []
                
                # Get all unique tickers from all portfolios
                portfolio_ids = [p.id for p in portfolios]
                positions = db.query(PortfolioPosition).filter(
                    PortfolioPosition.portfolio_id.in_(portfolio_ids)
                ).all()
                
                # Return unique tickers
                tickers = list(set([pos.ticker for pos in positions]))
                return tickers
            finally:
                close_db_session(db)
        else:
            logger.warning(f"Invalid mode '{mode}', defaulting to empty list")
            return []
    
    def add_to_watchlist(
        self,
        ticker: str,
        user_id: Optional[int] = None,
        notes: Optional[str] = None
    ) -> Dict:
        """Add ticker to user's watchlist."""
        db = get_db()
        try:
            # Check if already in watchlist
            existing = db.query(WatchlistItem).filter(
                and_(
                    WatchlistItem.ticker == ticker,
                    WatchlistItem.user_id == user_id
                )
            ).first()
            
            if existing:
                return {
                    'id': existing.id,
                    'ticker': existing.ticker,
                    'user_id': existing.user_id,
                    'notes': existing.notes
                }
            
            item = WatchlistItem(
                ticker=ticker,
                user_id=user_id,
                notes=notes
            )
            db.add(item)
            db.commit()
            db.refresh(item)
            
            return {
                'id': item.id,
                'ticker': item.ticker,
                'user_id': item.user_id,
                'notes': item.notes
            }
        except Exception as e:
            db.rollback()
            raise e
        finally:
            close_db_session(db)
    
    def remove_from_watchlist(self, ticker: str, user_id: Optional[int] = None) -> bool:
        """Remove ticker from user's watchlist."""
        db = get_db()
        try:
            item = db.query(WatchlistItem).filter(
                and_(
                    WatchlistItem.ticker == ticker,
                    WatchlistItem.user_id == user_id
                )
            ).first()
            
            if item:
                db.delete(item)
                db.commit()
                return True
            return False
        finally:
            close_db_session(db)
    
    # ============================================================================
    # SCANNER LOG OPERATIONS
    # ============================================================================
    
    def add_scanner_log(
        self,
        scanner: str,
        message: str,
        level: str = "info"
    ) -> None:
        """Add a scanner log entry."""
        db = get_db()
        try:
            log = ScannerLog(
                scanner=scanner,
                message=message,
                level=level,
                timestamp=datetime.utcnow()
            )
            db.add(log)
            db.commit()
            
            # Keep only last 100 logs per scanner
            log_count = db.query(ScannerLog).filter(
                ScannerLog.scanner == scanner
            ).count()
            
            if log_count > 100:
                oldest_logs = db.query(ScannerLog).filter(
                    ScannerLog.scanner == scanner
                ).order_by(ScannerLog.timestamp).limit(log_count - 100).all()
                
                for old_log in oldest_logs:
                    db.delete(old_log)
                db.commit()
        except Exception as e:
            db.rollback()
            raise e
        finally:
            close_db_session(db)
    
    def create_scanner_log(self, source: str) -> int:
        """
        Create a scanner log entry for manual scanner runs.
        
        Args:
            source: Scanner source identifier (e.g., 'sec', 'fda', 'press')
            
        Returns:
            Log ID of the created entry
        """
        db = get_db()
        try:
            log = ScannerLog(
                scanner=source,
                message=f"Manual scan triggered for {source}",
                level="info",
                timestamp=datetime.utcnow()
            )
            db.add(log)
            db.commit()
            db.refresh(log)
            return log.id
        except Exception as e:
            db.rollback()
            raise e
        finally:
            close_db_session(db)
    
    def get_scanner_logs(
        self,
        scanner: Optional[str] = None,
        level: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Get scanner logs with optional filtering."""
        db = get_db()
        try:
            query = db.query(ScannerLog)
            
            if scanner:
                query = query.filter(ScannerLog.scanner == scanner)
            
            if level:
                query = query.filter(ScannerLog.level == level)
            
            logs = query.order_by(ScannerLog.timestamp.desc()).limit(limit).all()
            
            return [{
                'id': log.id,
                'scanner': log.scanner,
                'message': log.message,
                'level': log.level,
                'timestamp': log.timestamp
            } for log in logs]
        finally:
            close_db_session(db)
    
    def get_scanner_status(self) -> Dict[str, Dict]:
        """
        Get status summary for all scanners.
        
        Returns:
            Dictionary mapping scanner names to their latest status
        """
        db = get_db()
        try:
            scanners = ['SEC', 'FDA', 'Company Releases']
            status = {}
            
            for scanner_name in scanners:
                latest_log = db.query(ScannerLog).filter(
                    ScannerLog.scanner == scanner_name
                ).order_by(ScannerLog.timestamp.desc()).first()
                
                if latest_log:
                    status[scanner_name] = {
                        'last_run': latest_log.timestamp,
                        'last_message': latest_log.message,
                        'last_level': latest_log.level
                    }
                else:
                    status[scanner_name] = {
                        'last_run': None,
                        'last_message': 'Never run',
                        'last_level': 'info'
                    }
            
            return status
        finally:
            close_db_session(db)
    
    # ============================================================================
    # HISTORICAL STATS OPERATIONS
    # ============================================================================
    
    def get_event_stats(self, ticker: str, event_type: str) -> Optional[EventStats]:
        """
        Get historical statistics for a ticker/event_type combination.
        
        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')
            event_type: Event type (e.g., 'earnings', 'fda_approval')
            
        Returns:
            EventStats object if found, None otherwise
        """
        db = get_db()
        try:
            return db.query(EventStats).filter(
                EventStats.ticker == ticker,
                EventStats.event_type == event_type
            ).first()
        finally:
            close_db_session(db)
    
    def get_ticker_all_event_stats(self, ticker: str) -> List[EventStats]:
        """
        Get stats for all event types for a ticker.
        
        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')
            
        Returns:
            List of EventStats objects for all available event types
        """
        db = get_db()
        try:
            return db.query(EventStats).filter(
                EventStats.ticker == ticker
            ).all()
        finally:
            close_db_session(db)
