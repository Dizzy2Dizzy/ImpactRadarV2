"""
Historical Event Matcher Service - Find similar past events and their outcomes.

Provides concrete precedent data for users by matching current events
to historical similar events and showing their 1d/5d/20d price outcomes.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import re
from loguru import logger

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass
class SimilarEvent:
    """A similar historical event with outcome data."""
    event_id: int
    ticker: str
    company_name: str
    event_type: str
    title: str
    event_date: datetime
    impact_score: int
    direction: str
    
    price_1d_change: Optional[float] = None
    price_5d_change: Optional[float] = None
    price_20d_change: Optional[float] = None
    
    similarity_score: float = 0.0
    match_reasons: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        if result["event_date"]:
            result["event_date"] = result["event_date"].isoformat()
        return result


@dataclass
class HistoricalMatchResult:
    """Result of historical event matching."""
    similar_events: List[SimilarEvent]
    total_matches: int
    avg_1d_change: Optional[float]
    avg_5d_change: Optional[float]
    avg_20d_change: Optional[float]
    positive_outcome_pct: float
    sample_size: int
    pattern_description: str
    confidence_level: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "similar_events": [e.to_dict() for e in self.similar_events],
            "total_matches": self.total_matches,
            "avg_1d_change": self.avg_1d_change,
            "avg_5d_change": self.avg_5d_change,
            "avg_20d_change": self.avg_20d_change,
            "positive_outcome_pct": self.positive_outcome_pct,
            "sample_size": self.sample_size,
            "pattern_description": self.pattern_description,
            "confidence_level": self.confidence_level
        }


class HistoricalEventMatcher:
    """
    Service for finding and analyzing similar historical events.
    
    Uses multiple matching strategies:
    1. Same ticker + same event type (highest relevance)
    2. Same sector + same event type (good for sector-wide patterns)
    3. Same event type + similar score range (useful for rare events)
    4. Keyword matching in title (for specific themes like "iPhone launch")
    """
    
    EVENT_KEYWORDS = {
        "product_launch": [
            r"launch", r"release", r"unveil", r"introduce", r"announce.*product",
            r"iphone", r"ipad", r"pixel", r"galaxy", r"surface"
        ],
        "earnings": [
            r"earnings", r"q[1-4]", r"quarterly", r"annual report",
            r"beat", r"miss", r"guidance"
        ],
        "fda": [
            r"fda", r"approval", r"cleared", r"authorized", r"pdufa",
            r"complete response", r"rejection", r"adcom"
        ],
        "ma": [
            r"merger", r"acquisition", r"acquire", r"takeover",
            r"buyout", r"deal", r"bid"
        ],
        "leadership": [
            r"ceo", r"cfo", r"cto", r"appoint", r"resign", r"retire",
            r"stepping down", r"departure"
        ],
        "lawsuit": [
            r"lawsuit", r"litigation", r"settlement", r"verdict",
            r"sued", r"court", r"judgment"
        ],
        "dividend": [
            r"dividend", r"distribution", r"yield", r"payout"
        ],
        "restructuring": [
            r"restructur", r"layoff", r"workforce", r"cut.*job",
            r"downsize", r"reorganiz"
        ]
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def find_similar_events(
        self,
        event: Dict[str, Any],
        max_results: int = 10,
        min_days_ago: int = 30,
        max_days_ago: int = 730
    ) -> HistoricalMatchResult:
        """
        Find similar historical events for the given event.
        
        Args:
            event: Current event to match against
            max_results: Maximum number of similar events to return
            min_days_ago: Minimum age of events to match (avoid recent duplicates)
            max_days_ago: Maximum age of events to consider (2 years default)
            
        Returns:
            HistoricalMatchResult with similar events and aggregate stats
        """
        event_id = event.get("id")
        ticker = event.get("ticker", "")
        event_type = event.get("event_type", "")
        sector = event.get("sector", "")
        title = event.get("title", "")
        impact_score = event.get("impact_score", 50)
        
        similar_events = []
        
        same_ticker_events = self._find_by_ticker_and_type(
            ticker, event_type, event_id, min_days_ago, max_days_ago
        )
        similar_events.extend(same_ticker_events)
        
        if len(similar_events) < max_results and sector:
            sector_events = self._find_by_sector_and_type(
                sector, event_type, event_id, min_days_ago, max_days_ago,
                exclude_ids=[e.event_id for e in similar_events]
            )
            similar_events.extend(sector_events[:max_results - len(similar_events)])
        
        keywords = self._extract_keywords(title, event_type)
        if keywords and len(similar_events) < max_results:
            keyword_events = self._find_by_keywords(
                keywords, event_type, event_id, min_days_ago, max_days_ago,
                exclude_ids=[e.event_id for e in similar_events]
            )
            similar_events.extend(keyword_events[:max_results - len(similar_events)])
        
        if len(similar_events) < 5:
            type_events = self._find_by_type_and_score(
                event_type, impact_score, event_id, min_days_ago, max_days_ago,
                exclude_ids=[e.event_id for e in similar_events]
            )
            similar_events.extend(type_events[:max_results - len(similar_events)])
        
        similar_events = self._enrich_with_outcomes(similar_events)
        
        similar_events.sort(key=lambda x: x.similarity_score, reverse=True)
        similar_events = similar_events[:max_results]
        
        return self._build_result(similar_events, ticker, event_type, title)
    
    def _find_by_ticker_and_type(
        self,
        ticker: str,
        event_type: str,
        current_event_id: Optional[int],
        min_days_ago: int,
        max_days_ago: int
    ) -> List[SimilarEvent]:
        """Find events with same ticker and event type."""
        if not ticker:
            return []
        
        query = text("""
            SELECT e.id, e.ticker, e.company_name, e.event_type, e.title,
                   e.date, e.impact_score, e.direction
            FROM events e
            WHERE e.ticker = :ticker
              AND e.event_type = :event_type
              AND e.id != :current_id
              AND e.date < NOW() - :min_days * INTERVAL '1 day'
              AND e.date > NOW() - :max_days * INTERVAL '1 day'
            ORDER BY e.date DESC
            LIMIT 20
        """)
        
        try:
            result = self.db.execute(
                query,
                {
                    "ticker": ticker,
                    "event_type": event_type,
                    "current_id": current_event_id or 0,
                    "min_days": min_days_ago,
                    "max_days": max_days_ago
                }
            )
            
            events = []
            for row in result:
                events.append(SimilarEvent(
                    event_id=row[0],
                    ticker=row[1] or "",
                    company_name=row[2] or "",
                    event_type=row[3] or "",
                    title=row[4] or "",
                    event_date=row[5],
                    impact_score=row[6] or 50,
                    direction=row[7] or "neutral",
                    similarity_score=0.95,
                    match_reasons=["Same company", f"Same event type ({event_type})"]
                ))
            return events
        except Exception as e:
            logger.error(f"Error finding ticker+type matches: {e}")
            return []
    
    def _find_by_sector_and_type(
        self,
        sector: str,
        event_type: str,
        current_event_id: Optional[int],
        min_days_ago: int,
        max_days_ago: int,
        exclude_ids: Optional[List[int]] = None
    ) -> List[SimilarEvent]:
        """Find events with same sector and event type."""
        if not sector:
            return []
        
        exclude_ids = exclude_ids or []
        exclude_clause = ""
        if exclude_ids:
            exclude_clause = f"AND e.id NOT IN ({','.join(str(i) for i in exclude_ids)})"
        
        query = text(f"""
            SELECT e.id, e.ticker, e.company_name, e.event_type, e.title,
                   e.date, e.impact_score, e.direction
            FROM events e
            JOIN companies c ON e.ticker = c.ticker
            WHERE c.sector = :sector
              AND e.event_type = :event_type
              AND e.id != :current_id
              AND e.date < NOW() - :min_days * INTERVAL '1 day'
              AND e.date > NOW() - :max_days * INTERVAL '1 day'
              {exclude_clause}
            ORDER BY e.date DESC
            LIMIT 15
        """)
        
        try:
            result = self.db.execute(
                query,
                {
                    "sector": sector,
                    "event_type": event_type,
                    "current_id": current_event_id or 0,
                    "min_days": min_days_ago,
                    "max_days": max_days_ago
                }
            )
            
            events = []
            for row in result:
                events.append(SimilarEvent(
                    event_id=row[0],
                    ticker=row[1] or "",
                    company_name=row[2] or "",
                    event_type=row[3] or "",
                    title=row[4] or "",
                    event_date=row[5],
                    impact_score=row[6] or 50,
                    direction=row[7] or "neutral",
                    similarity_score=0.75,
                    match_reasons=[f"Same sector ({sector})", f"Same event type ({event_type})"]
                ))
            return events
        except Exception as e:
            logger.error(f"Error finding sector+type matches: {e}")
            return []
    
    def _find_by_keywords(
        self,
        keywords: List[str],
        event_type: str,
        current_event_id: Optional[int],
        min_days_ago: int,
        max_days_ago: int,
        exclude_ids: Optional[List[int]] = None
    ) -> List[SimilarEvent]:
        """Find events matching keywords in title."""
        if not keywords:
            return []
        
        exclude_ids = exclude_ids or []
        exclude_clause = ""
        if exclude_ids:
            exclude_clause = f"AND e.id NOT IN ({','.join(str(i) for i in exclude_ids)})"
        
        keyword_conditions = " OR ".join([f"LOWER(e.title) LIKE '%{kw.lower()}%'" for kw in keywords[:5]])
        
        query = text(f"""
            SELECT e.id, e.ticker, e.company_name, e.event_type, e.title,
                   e.date, e.impact_score, e.direction
            FROM events e
            WHERE ({keyword_conditions})
              AND e.id != :current_id
              AND e.date < NOW() - :min_days * INTERVAL '1 day'
              AND e.date > NOW() - :max_days * INTERVAL '1 day'
              {exclude_clause}
            ORDER BY e.date DESC
            LIMIT 10
        """)
        
        try:
            result = self.db.execute(
                query,
                {
                    "current_id": current_event_id or 0,
                    "min_days": min_days_ago,
                    "max_days": max_days_ago
                }
            )
            
            events = []
            for row in result:
                matched_keywords = [kw for kw in keywords if kw.lower() in (row[4] or "").lower()]
                events.append(SimilarEvent(
                    event_id=row[0],
                    ticker=row[1] or "",
                    company_name=row[2] or "",
                    event_type=row[3] or "",
                    title=row[4] or "",
                    event_date=row[5],
                    impact_score=row[6] or 50,
                    direction=row[7] or "neutral",
                    similarity_score=0.6 + (0.1 * len(matched_keywords)),
                    match_reasons=[f"Similar theme: {', '.join(matched_keywords[:3])}"]
                ))
            return events
        except Exception as e:
            logger.error(f"Error finding keyword matches: {e}")
            return []
    
    def _find_by_type_and_score(
        self,
        event_type: str,
        impact_score: int,
        current_event_id: Optional[int],
        min_days_ago: int,
        max_days_ago: int,
        exclude_ids: Optional[List[int]] = None
    ) -> List[SimilarEvent]:
        """Find events with same type and similar impact score."""
        exclude_ids = exclude_ids or []
        exclude_clause = ""
        if exclude_ids:
            exclude_clause = f"AND e.id NOT IN ({','.join(str(i) for i in exclude_ids)})"
        
        score_low = max(0, impact_score - 15)
        score_high = min(100, impact_score + 15)
        
        query = text(f"""
            SELECT e.id, e.ticker, e.company_name, e.event_type, e.title,
                   e.date, e.impact_score, e.direction
            FROM events e
            WHERE e.event_type = :event_type
              AND e.impact_score BETWEEN :score_low AND :score_high
              AND e.id != :current_id
              AND e.date < NOW() - :min_days * INTERVAL '1 day'
              AND e.date > NOW() - :max_days * INTERVAL '1 day'
              {exclude_clause}
            ORDER BY ABS(e.impact_score - :impact_score), e.date DESC
            LIMIT 10
        """)
        
        try:
            result = self.db.execute(
                query,
                {
                    "event_type": event_type,
                    "score_low": score_low,
                    "score_high": score_high,
                    "current_id": current_event_id or 0,
                    "impact_score": impact_score,
                    "min_days": min_days_ago,
                    "max_days": max_days_ago
                }
            )
            
            events = []
            for row in result:
                events.append(SimilarEvent(
                    event_id=row[0],
                    ticker=row[1] or "",
                    company_name=row[2] or "",
                    event_type=row[3] or "",
                    title=row[4] or "",
                    event_date=row[5],
                    impact_score=row[6] or 50,
                    direction=row[7] or "neutral",
                    similarity_score=0.5,
                    match_reasons=[f"Same event type", f"Similar impact score ({row[6]})"]
                ))
            return events
        except Exception as e:
            logger.error(f"Error finding type+score matches: {e}")
            return []
    
    def _extract_keywords(self, title: str, event_type: str) -> List[str]:
        """Extract relevant keywords from title for matching."""
        keywords = []
        title_lower = title.lower()
        
        for category, patterns in self.EVENT_KEYWORDS.items():
            for pattern in patterns:
                if re.search(pattern, title_lower):
                    keywords.append(pattern.replace(r".*", "").replace(r"\b", ""))
        
        product_patterns = [
            r"\b(iphone|ipad|mac|pixel|galaxy|surface|playstation|xbox)\b",
            r"\b(model [a-z0-9]+)\b",
        ]
        for pattern in product_patterns:
            match = re.search(pattern, title_lower)
            if match:
                keywords.append(match.group(1))
        
        return list(set(keywords))[:5]
    
    def _enrich_with_outcomes(self, events: List[SimilarEvent]) -> List[SimilarEvent]:
        """Enrich events with actual price outcome data."""
        if not events:
            return events
        
        event_ids = [e.event_id for e in events]
        
        query = text("""
            SELECT event_id, horizon, actual_return
            FROM event_outcomes
            WHERE event_id = ANY(:event_ids)
              AND horizon IN ('1d', '5d', '20d')
        """)
        
        try:
            result = self.db.execute(query, {"event_ids": event_ids})
            
            outcomes_map: Dict[int, Dict[str, float]] = {}
            for row in result:
                event_id, horizon, actual_return = row[0], row[1], row[2]
                if event_id not in outcomes_map:
                    outcomes_map[event_id] = {}
                outcomes_map[event_id][horizon] = actual_return
            
            for event in events:
                if event.event_id in outcomes_map:
                    outcomes = outcomes_map[event.event_id]
                    event.price_1d_change = outcomes.get("1d")
                    event.price_5d_change = outcomes.get("5d")
                    event.price_20d_change = outcomes.get("20d")
            
            return events
        except Exception as e:
            logger.warning(f"Could not enrich with outcomes: {e}")
            return events
    
    def _build_result(
        self,
        events: List[SimilarEvent],
        ticker: str,
        event_type: str,
        title: str
    ) -> HistoricalMatchResult:
        """Build the final result with aggregate statistics."""
        if not events:
            return HistoricalMatchResult(
                similar_events=[],
                total_matches=0,
                avg_1d_change=None,
                avg_5d_change=None,
                avg_20d_change=None,
                positive_outcome_pct=0.0,
                sample_size=0,
                pattern_description=f"No similar historical events found for {event_type}",
                confidence_level="low"
            )
        
        changes_1d = [e.price_1d_change for e in events if e.price_1d_change is not None]
        changes_5d = [e.price_5d_change for e in events if e.price_5d_change is not None]
        changes_20d = [e.price_20d_change for e in events if e.price_20d_change is not None]
        
        avg_1d = sum(changes_1d) / len(changes_1d) if changes_1d else None
        avg_5d = sum(changes_5d) / len(changes_5d) if changes_5d else None
        avg_20d = sum(changes_20d) / len(changes_20d) if changes_20d else None
        
        all_changes = changes_1d + changes_5d + changes_20d
        positive_count = sum(1 for c in all_changes if c and c > 0)
        positive_pct = (positive_count / len(all_changes) * 100) if all_changes else 0
        
        sample_size = len(events)
        if sample_size >= 10:
            confidence = "high"
        elif sample_size >= 5:
            confidence = "medium"
        else:
            confidence = "low"
        
        ticker_matches = sum(1 for e in events if e.ticker == ticker)
        if ticker_matches >= 3:
            pattern_desc = f"Found {ticker_matches} similar {event_type.replace('_', ' ')} events for {ticker}"
        else:
            pattern_desc = f"Found {sample_size} similar {event_type.replace('_', ' ')} events across the market"
        
        return HistoricalMatchResult(
            similar_events=events,
            total_matches=len(events),
            avg_1d_change=round(avg_1d, 2) if avg_1d else None,
            avg_5d_change=round(avg_5d, 2) if avg_5d else None,
            avg_20d_change=round(avg_20d, 2) if avg_20d else None,
            positive_outcome_pct=round(positive_pct, 1),
            sample_size=sample_size,
            pattern_description=pattern_desc,
            confidence_level=confidence
        )


def get_historical_matcher(db: Session) -> HistoricalEventMatcher:
    """Get instance of HistoricalEventMatcher."""
    return HistoricalEventMatcher(db)
