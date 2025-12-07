"""
Bearish Pattern Detector Service

Detects clusters of negative/bearish events for tickers within rolling windows.
Implements pattern detection for:
1. Event clusters - Multiple bearish events for same ticker in short window
2. Sector contagion - Multiple bearish events across sector peers
3. Severity escalation - Increasing bearish scores over time
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict

from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import Session

from releaseradar.db.models import Event
from releaseradar.log_config import logger


def utc_now() -> datetime:
    """Return timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


@dataclass
class BearishPattern:
    """Represents a detected bearish pattern."""
    pattern_type: str  # 'cluster', 'escalation', 'sector_contagion'
    ticker: str
    sector: Optional[str]
    window_days: int
    event_count: int
    avg_bearish_score: float
    max_bearish_score: float
    total_bearish_score: float
    confidence: float
    detected_at: datetime
    event_ids: List[int] = field(default_factory=list)
    description: str = ""


@dataclass 
class BearishPatternConfig:
    """Configuration for pattern detection thresholds."""
    
    # Cluster detection
    CLUSTER_WINDOW_DAYS = 7  # Rolling window for cluster detection
    MIN_CLUSTER_EVENTS = 2  # Minimum events to form a cluster
    MIN_CLUSTER_SCORE = 1.2  # Minimum cumulative bearish score for cluster
    
    # Escalation detection
    ESCALATION_WINDOW_DAYS = 14  # Window for escalation detection
    MIN_ESCALATION_EVENTS = 3  # Minimum events for escalation pattern
    ESCALATION_THRESHOLD = 0.15  # Minimum score increase per event
    
    # Sector contagion
    SECTOR_WINDOW_DAYS = 7  # Window for sector analysis
    MIN_SECTOR_EVENTS = 3  # Minimum events across sector
    MIN_UNIQUE_TICKERS = 2  # Minimum unique tickers for contagion
    
    # General thresholds
    MIN_PATTERN_CONFIDENCE = 0.6  # Minimum confidence to report pattern


class BearishPatternDetector:
    """
    Detects bearish patterns across events.
    
    Pattern Types:
    1. Cluster: Multiple bearish events for same ticker in short window
    2. Escalation: Increasing bearish severity over time
    3. Sector Contagion: Multiple bearish events across sector peers
    """
    
    def __init__(self, config: BearishPatternConfig = None):
        self.config = config or BearishPatternConfig()
    
    def detect_ticker_clusters(
        self,
        db: Session,
        ticker: Optional[str] = None,
        window_days: int = None
    ) -> List[BearishPattern]:
        """
        Detect clusters of bearish events for tickers.
        
        Args:
            db: Database session
            ticker: Optional specific ticker to analyze
            window_days: Rolling window in days (default: config value)
            
        Returns:
            List of detected cluster patterns
        """
        window_days = window_days or self.config.CLUSTER_WINDOW_DAYS
        cutoff_date = utc_now() - timedelta(days=window_days)
        
        # Query for bearish events in window
        query = (
            select(Event)
            .where(Event.bearish_signal == True)
            .where(Event.date >= cutoff_date)
            .order_by(Event.ticker, Event.date.desc())
        )
        
        if ticker:
            query = query.where(Event.ticker == ticker)
        
        events = db.execute(query).scalars().all()
        
        # Group by ticker
        ticker_events: Dict[str, List[Event]] = defaultdict(list)
        for event in events:
            ticker_events[event.ticker].append(event)
        
        patterns = []
        for tkr, tkr_events in ticker_events.items():
            if len(tkr_events) >= self.config.MIN_CLUSTER_EVENTS:
                # Calculate cluster metrics
                total_score = sum(e.bearish_score or 0 for e in tkr_events)
                
                if total_score >= self.config.MIN_CLUSTER_SCORE:
                    avg_score = total_score / len(tkr_events)
                    max_score = max(e.bearish_score or 0 for e in tkr_events)
                    
                    # Calculate confidence based on event count and scores
                    count_factor = min(1.0, len(tkr_events) / 5)
                    score_factor = min(1.0, total_score / 3.0)
                    confidence = 0.5 * count_factor + 0.5 * score_factor
                    
                    if confidence >= self.config.MIN_PATTERN_CONFIDENCE:
                        pattern = BearishPattern(
                            pattern_type='cluster',
                            ticker=tkr,
                            sector=tkr_events[0].sector,
                            window_days=window_days,
                            event_count=len(tkr_events),
                            avg_bearish_score=round(avg_score, 3),
                            max_bearish_score=round(max_score, 3),
                            total_bearish_score=round(total_score, 3),
                            confidence=round(confidence, 3),
                            detected_at=utc_now(),
                            event_ids=[e.id for e in tkr_events],
                            description=f"{len(tkr_events)} bearish events in {window_days} days"
                        )
                        patterns.append(pattern)
        
        return sorted(patterns, key=lambda p: p.total_bearish_score, reverse=True)
    
    def detect_escalation(
        self,
        db: Session,
        ticker: str,
        window_days: int = None
    ) -> Optional[BearishPattern]:
        """
        Detect escalating bearish severity for a ticker.
        
        Returns pattern if bearish scores are increasing over time.
        """
        window_days = window_days or self.config.ESCALATION_WINDOW_DAYS
        cutoff_date = utc_now() - timedelta(days=window_days)
        
        events = db.execute(
            select(Event)
            .where(Event.ticker == ticker)
            .where(Event.bearish_signal == True)
            .where(Event.date >= cutoff_date)
            .order_by(Event.date.asc())
        ).scalars().all()
        
        if len(events) < self.config.MIN_ESCALATION_EVENTS:
            return None
        
        # Check for escalation trend
        scores = [e.bearish_score or 0 for e in events]
        
        # Calculate average score increase
        increases = []
        for i in range(1, len(scores)):
            increases.append(scores[i] - scores[i-1])
        
        avg_increase = sum(increases) / len(increases) if increases else 0
        
        if avg_increase >= self.config.ESCALATION_THRESHOLD:
            total_score = sum(scores)
            max_score = max(scores)
            
            # Higher confidence for stronger escalation
            confidence = min(1.0, 0.6 + avg_increase)
            
            return BearishPattern(
                pattern_type='escalation',
                ticker=ticker,
                sector=events[0].sector,
                window_days=window_days,
                event_count=len(events),
                avg_bearish_score=round(total_score / len(events), 3),
                max_bearish_score=round(max_score, 3),
                total_bearish_score=round(total_score, 3),
                confidence=round(confidence, 3),
                detected_at=utc_now(),
                event_ids=[e.id for e in events],
                description=f"Escalating bearish severity (+{avg_increase:.2f} per event)"
            )
        
        return None
    
    def detect_sector_contagion(
        self,
        db: Session,
        sector: str,
        window_days: int = None
    ) -> Optional[BearishPattern]:
        """
        Detect bearish contagion across sector peers.
        
        Returns pattern if multiple tickers in sector have bearish events.
        """
        window_days = window_days or self.config.SECTOR_WINDOW_DAYS
        cutoff_date = utc_now() - timedelta(days=window_days)
        
        events = db.execute(
            select(Event)
            .where(Event.sector == sector)
            .where(Event.bearish_signal == True)
            .where(Event.date >= cutoff_date)
            .order_by(Event.date.desc())
        ).scalars().all()
        
        if len(events) < self.config.MIN_SECTOR_EVENTS:
            return None
        
        unique_tickers = set(e.ticker for e in events)
        
        if len(unique_tickers) < self.config.MIN_UNIQUE_TICKERS:
            return None
        
        total_score = sum(e.bearish_score or 0 for e in events)
        max_score = max(e.bearish_score or 0 for e in events)
        
        # Confidence based on ticker spread and event density
        ticker_factor = min(1.0, len(unique_tickers) / 5)
        event_factor = min(1.0, len(events) / 10)
        confidence = 0.4 * ticker_factor + 0.4 * event_factor + 0.2 * (total_score / 5)
        
        if confidence >= self.config.MIN_PATTERN_CONFIDENCE:
            return BearishPattern(
                pattern_type='sector_contagion',
                ticker=','.join(sorted(unique_tickers)[:5]),  # Top 5 tickers
                sector=sector,
                window_days=window_days,
                event_count=len(events),
                avg_bearish_score=round(total_score / len(events), 3),
                max_bearish_score=round(max_score, 3),
                total_bearish_score=round(total_score, 3),
                confidence=round(min(1.0, confidence), 3),
                detected_at=utc_now(),
                event_ids=[e.id for e in events],
                description=f"Sector contagion: {len(unique_tickers)} tickers affected"
            )
        
        return None
    
    def detect_all_patterns(
        self,
        db: Session,
        ticker: Optional[str] = None,
        sector: Optional[str] = None
    ) -> Dict[str, List[BearishPattern]]:
        """
        Run all pattern detection algorithms.
        
        Args:
            db: Database session
            ticker: Optional ticker filter
            sector: Optional sector filter
            
        Returns:
            Dictionary with pattern types as keys and pattern lists as values
        """
        result = {
            'clusters': [],
            'escalations': [],
            'sector_contagions': []
        }
        
        # Detect clusters
        clusters = self.detect_ticker_clusters(db, ticker)
        result['clusters'] = clusters
        
        # Detect escalations for specific ticker or all tickers with clusters
        if ticker:
            escalation = self.detect_escalation(db, ticker)
            if escalation:
                result['escalations'].append(escalation)
        else:
            # Check escalation for tickers that have clusters
            checked_tickers = set()
            for cluster in clusters:
                if cluster.ticker not in checked_tickers:
                    escalation = self.detect_escalation(db, cluster.ticker)
                    if escalation:
                        result['escalations'].append(escalation)
                    checked_tickers.add(cluster.ticker)
        
        # Detect sector contagion
        if sector:
            contagion = self.detect_sector_contagion(db, sector)
            if contagion:
                result['sector_contagions'].append(contagion)
        else:
            # Check all sectors with bearish events
            cutoff = utc_now() - timedelta(days=self.config.SECTOR_WINDOW_DAYS)
            sectors = db.execute(
                select(Event.sector)
                .where(Event.bearish_signal == True)
                .where(Event.date >= cutoff)
                .where(Event.sector.isnot(None))
                .distinct()
            ).scalars().all()
            
            for sect in sectors:
                contagion = self.detect_sector_contagion(db, sect)
                if contagion:
                    result['sector_contagions'].append(contagion)
        
        logger.info(f"Pattern detection complete: {len(result['clusters'])} clusters, "
                   f"{len(result['escalations'])} escalations, "
                   f"{len(result['sector_contagions'])} sector contagions")
        
        return result
    
    def get_ticker_bearish_summary(
        self,
        db: Session,
        ticker: str,
        window_days: int = 30
    ) -> Dict[str, Any]:
        """
        Get comprehensive bearish summary for a ticker.
        
        Returns:
            Dictionary with bearish event stats, patterns, and risk assessment
        """
        cutoff_date = utc_now() - timedelta(days=window_days)
        
        # Get bearish events
        events = db.execute(
            select(Event)
            .where(Event.ticker == ticker)
            .where(Event.bearish_signal == True)
            .where(Event.date >= cutoff_date)
            .order_by(Event.date.desc())
        ).scalars().all()
        
        if not events:
            return {
                'ticker': ticker,
                'window_days': window_days,
                'bearish_event_count': 0,
                'total_bearish_score': 0,
                'avg_bearish_score': 0,
                'max_bearish_score': 0,
                'risk_level': 'low',
                'patterns': [],
                'recent_events': []
            }
        
        total_score = sum(e.bearish_score or 0 for e in events)
        avg_score = total_score / len(events)
        max_score = max(e.bearish_score or 0 for e in events)
        
        # Determine risk level
        if total_score >= 3.0 or len(events) >= 5:
            risk_level = 'high'
        elif total_score >= 1.5 or len(events) >= 3:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        # Detect patterns
        patterns = []
        cluster = self.detect_ticker_clusters(db, ticker)
        if cluster:
            patterns.extend([{
                'type': p.pattern_type,
                'confidence': p.confidence,
                'description': p.description
            } for p in cluster])
        
        escalation = self.detect_escalation(db, ticker)
        if escalation:
            patterns.append({
                'type': escalation.pattern_type,
                'confidence': escalation.confidence,
                'description': escalation.description
            })
        
        return {
            'ticker': ticker,
            'window_days': window_days,
            'bearish_event_count': len(events),
            'total_bearish_score': round(total_score, 3),
            'avg_bearish_score': round(avg_score, 3),
            'max_bearish_score': round(max_score, 3),
            'risk_level': risk_level,
            'patterns': patterns,
            'recent_events': [{
                'id': e.id,
                'date': e.date.isoformat() if e.date else None,
                'event_type': e.event_type,
                'title': e.title,
                'bearish_score': e.bearish_score,
                'bearish_rationale': e.bearish_rationale
            } for e in events[:10]]
        }
