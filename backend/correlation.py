"""
Event correlation analysis module for identifying related events and patterns.

This module provides functionality to:
- Get timeline of all events for a specific ticker
- Find common event sequence patterns
- Identify related events within time windows
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import Session

from database import Event, get_db
from releaseradar.db.models import EventStats


class CorrelationEngine:
    """Engine for analyzing event correlations and patterns."""
    
    def __init__(self, session: Session = None):
        """Initialize correlation engine with database session."""
        self.session = session or next(get_db())
    
    def get_ticker_timeline(
        self, 
        ticker: str, 
        days: int = 90,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get all events for a ticker in chronological order.
        
        Args:
            ticker: Stock ticker symbol
            days: Number of days to look back (default: 90)
            limit: Maximum number of events to return
            
        Returns:
            List of event dictionaries sorted by date (newest first)
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        events = (
            self.session.query(Event)
            .filter(
                and_(
                    Event.ticker == ticker.upper(),
                    Event.date >= cutoff_date
                )
            )
            .order_by(Event.date.desc())
            .limit(limit)
            .all()
        )
        
        return [self._event_to_dict(event) for event in events]
    
    def find_event_patterns(
        self, 
        event_type: Optional[str] = None,
        days_window: int = 30,
        min_frequency: int = 3,
        tickers: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Find common event sequences across all tickers.
        
        Args:
            event_type: Filter by specific event type (optional)
            days_window: Time window to look for follow-on events (default: 30 days)
            min_frequency: Minimum number of times a pattern must occur (default: 3)
            tickers: Filter by specific tickers (optional, for watchlist/portfolio mode)
            
        Returns:
            List of patterns with frequency and timing statistics
        """
        # Get all events, optionally filtered by type and tickers
        query = self.session.query(Event).order_by(Event.ticker, Event.date)
        
        if event_type:
            query = query.filter(Event.event_type == event_type)
        
        if tickers is not None and len(tickers) > 0:
            query = query.filter(Event.ticker.in_(tickers))
        
        events = query.all()
        
        # Group events by ticker
        ticker_events = defaultdict(list)
        for event in events:
            ticker_events[event.ticker].append(event)
        
        # Find sequences (event pairs within the time window)
        sequences = []
        for ticker, ticker_event_list in ticker_events.items():
            for i in range(len(ticker_event_list) - 1):
                for j in range(i + 1, len(ticker_event_list)):
                    event1 = ticker_event_list[i]
                    event2 = ticker_event_list[j]
                    
                    # Calculate days between events
                    days_diff = (event2.date - event1.date).days
                    
                    # If within window, record the sequence
                    if 0 < days_diff <= days_window:
                        pattern = f"{event1.event_type} → {event2.event_type}"
                        sequences.append({
                            'pattern': pattern,
                            'days_between': days_diff,
                            'ticker': ticker,
                            'event1_type': event1.event_type,
                            'event2_type': event2.event_type,
                            'event1': event1,
                            'event2': event2
                        })
        
        # Aggregate patterns with Market Echo Engine data
        pattern_stats = defaultdict(lambda: {
            'frequency': 0,
            'days_between': [],
            'tickers': set(),
            'ml_confidences': [],
            'ml_scores': [],
            'base_scores': []
        })
        
        for seq in sequences:
            pattern = seq['pattern']
            pattern_stats[pattern]['frequency'] += 1
            pattern_stats[pattern]['days_between'].append(seq['days_between'])
            pattern_stats[pattern]['tickers'].add(seq['ticker'])
            
            # Collect ML data from both events (use getattr for safe access)
            event1 = seq['event1']
            event2 = seq['event2']
            
            ml_conf1 = getattr(event1, 'ml_confidence', None)
            ml_conf2 = getattr(event2, 'ml_confidence', None)
            ml_score1 = getattr(event1, 'ml_adjusted_score', None)
            ml_score2 = getattr(event2, 'ml_adjusted_score', None)
            
            if ml_conf1 is not None:
                pattern_stats[pattern]['ml_confidences'].append(ml_conf1)
            if ml_conf2 is not None:
                pattern_stats[pattern]['ml_confidences'].append(ml_conf2)
                
            if ml_score1 is not None:
                pattern_stats[pattern]['ml_scores'].append(ml_score1)
            if ml_score2 is not None:
                pattern_stats[pattern]['ml_scores'].append(ml_score2)
            
            pattern_stats[pattern]['base_scores'].append(event1.impact_score)
            pattern_stats[pattern]['base_scores'].append(event2.impact_score)
        
        # Format results with Market Echo Engine enrichments
        results = []
        for pattern, stats in pattern_stats.items():
            if stats['frequency'] >= min_frequency:
                avg_days = sum(stats['days_between']) / len(stats['days_between'])
                
                # Calculate average ML metrics
                avg_ml_confidence = None
                avg_ml_score = None
                avg_base_score = None
                
                if stats['ml_confidences']:
                    avg_ml_confidence = round(sum(stats['ml_confidences']) / len(stats['ml_confidences']), 3)
                if stats['ml_scores']:
                    avg_ml_score = round(sum(stats['ml_scores']) / len(stats['ml_scores']), 1)
                if stats['base_scores']:
                    avg_base_score = round(sum(stats['base_scores']) / len(stats['base_scores']), 1)
                
                results.append({
                    'pattern': pattern,
                    'frequency': stats['frequency'],
                    'avg_days_between': round(avg_days, 1),
                    'example_tickers': list(stats['tickers'])[:5],  # Limit to 5 examples
                    # Market Echo Engine ML predictions
                    'avg_ml_confidence': avg_ml_confidence,
                    'avg_ml_adjusted_score': avg_ml_score,
                    'avg_base_score': avg_base_score
                })
        
        # Sort by frequency (most common first)
        results.sort(key=lambda x: x['frequency'], reverse=True)
        
        return results
    
    def get_related_events(
        self, 
        event_id: int, 
        window_days: int = 30
    ) -> List[Dict]:
        """
        Get events on the same ticker within a time window of the specified event.
        
        Args:
            event_id: ID of the event to find related events for
            window_days: Number of days before and after to search (default: 30)
            
        Returns:
            List of related events with time differences
        """
        # Get the target event
        target_event = self.session.query(Event).filter(Event.id == event_id).first()
        
        if not target_event:
            return []
        
        # Calculate date range
        start_date = target_event.date - timedelta(days=window_days)
        end_date = target_event.date + timedelta(days=window_days)
        
        # Get related events on the same ticker within the window
        related_events = (
            self.session.query(Event)
            .filter(
                and_(
                    Event.ticker == target_event.ticker,
                    Event.id != event_id,  # Exclude the target event itself
                    Event.date >= start_date,
                    Event.date <= end_date
                )
            )
            .order_by(Event.date.desc())
            .all()
        )
        
        # Format results with time differences
        results = []
        for event in related_events:
            days_diff = (event.date - target_event.date).days
            result = self._event_to_dict(event)
            result['days_from_target'] = days_diff
            result['is_before'] = days_diff < 0
            results.append(result)
        
        return results
    
    def get_pattern_details(
        self,
        event_type_1: str,
        event_type_2: str,
        days_window: int = 30
    ) -> Dict:
        """
        Get detailed statistics for a specific event pattern.
        
        Args:
            event_type_1: First event type in the pattern
            event_type_2: Second event type in the pattern
            days_window: Time window for pattern detection
            
        Returns:
            Dictionary with pattern statistics and examples
        """
        # Get all events of both types
        events = (
            self.session.query(Event)
            .filter(
                or_(
                    Event.event_type == event_type_1,
                    Event.event_type == event_type_2
                )
            )
            .order_by(Event.ticker, Event.date)
            .all()
        )
        
        # Group by ticker
        ticker_events = defaultdict(list)
        for event in events:
            ticker_events[event.ticker].append(event)
        
        # Find occurrences of the pattern
        occurrences = []
        for ticker, ticker_event_list in ticker_events.items():
            for i in range(len(ticker_event_list) - 1):
                for j in range(i + 1, len(ticker_event_list)):
                    event1 = ticker_event_list[i]
                    event2 = ticker_event_list[j]
                    
                    if (event1.event_type == event_type_1 and 
                        event2.event_type == event_type_2):
                        days_diff = (event2.date - event1.date).days
                        
                        if 0 < days_diff <= days_window:
                            occurrences.append({
                                'ticker': ticker,
                                'event1_date': event1.date.isoformat(),
                                'event2_date': event2.date.isoformat(),
                                'days_between': days_diff,
                                'event1_id': event1.id,
                                'event2_id': event2.id
                            })
        
        if not occurrences:
            return {
                'pattern': f"{event_type_1} → {event_type_2}",
                'frequency': 0,
                'avg_days_between': 0,
                'occurrences': []
            }
        
        avg_days = sum(o['days_between'] for o in occurrences) / len(occurrences)
        
        return {
            'pattern': f"{event_type_1} → {event_type_2}",
            'frequency': len(occurrences),
            'avg_days_between': round(avg_days, 1),
            'occurrences': occurrences[:10]  # Limit to 10 most recent
        }
    
    def _event_to_dict(self, event: Event) -> Dict:
        """Convert Event model to dictionary with Market Echo Engine data."""
        return {
            'id': event.id,
            'ticker': event.ticker,
            'company_name': event.company_name,
            'event_type': event.event_type,
            'title': event.title,
            'description': event.description,
            'date': event.date.isoformat(),
            'source': event.source,
            'source_url': event.source_url,
            'impact_score': event.impact_score,
            'direction': event.direction,
            'confidence': event.confidence,
            'info_tier': event.info_tier,
            'info_subtype': event.info_subtype,
            # Probability metrics from Market Echo Engine (safe access)
            'impact_p_move': getattr(event, 'impact_p_move', None),
            'impact_p_up': getattr(event, 'impact_p_up', None),
            'impact_p_down': getattr(event, 'impact_p_down', None),
            # ML predictions from Market Echo Engine (safe access)
            'ml_adjusted_score': getattr(event, 'ml_adjusted_score', None),
            'ml_confidence': getattr(event, 'ml_confidence', None),
            'ml_model_version': getattr(event, 'ml_model_version', None),
            'sector': event.sector,
        }


# Singleton instance getter
_engine_instance = None

def get_correlation_engine(session: Session = None) -> CorrelationEngine:
    """Get or create a CorrelationEngine instance."""
    global _engine_instance
    if _engine_instance is None or session is not None:
        _engine_instance = CorrelationEngine(session)
    return _engine_instance
