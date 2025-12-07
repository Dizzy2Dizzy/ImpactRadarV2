"""
Peer Comparison Engine for Impact Radar

Helps traders contextualize events by comparing to similar events on peer companies.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy import and_, or_, func
from database import get_db, close_db_session, Company, Event
import logging

logger = logging.getLogger(__name__)


class PeerEngine:
    """
    Engine for finding peer companies and comparing similar events.
    """
    
    def get_company_peers(
        self, 
        ticker: str, 
        limit: int = 5,
        min_event_count: int = 3
    ) -> List[str]:
        """
        Find peer companies based on sector and market cap similarity.
        
        Args:
            ticker: Target company ticker
            limit: Maximum number of peers to return
            min_event_count: Minimum event count for a company to be considered a peer
            
        Returns:
            List of peer company tickers (excluding the target ticker)
        """
        db = get_db()
        try:
            # Get target company
            target_company = db.query(Company).filter(Company.ticker == ticker).first()
            
            if not target_company:
                logger.warning(f"Company {ticker} not found")
                return []
            
            # Get target company sector
            target_sector = target_company.sector
            
            if not target_sector:
                logger.warning(f"Company {ticker} has no sector defined")
                return []
            
            # Find peers: same sector, active, with events, excluding target
            peers_query = db.query(Company.ticker).filter(
                and_(
                    Company.sector == target_sector,
                    Company.tracked == True,
                    Company.ticker != ticker
                )
            )
            
            # Filter by companies that have at least min_event_count events
            # Using a subquery for event counts
            event_counts_subq = db.query(
                Event.ticker,
                func.count(Event.id).label('event_count')
            ).group_by(Event.ticker).subquery()
            
            peers_query = peers_query.join(
                event_counts_subq,
                Company.ticker == event_counts_subq.c.ticker
            ).filter(
                event_counts_subq.c.event_count >= min_event_count
            ).order_by(
                event_counts_subq.c.event_count.desc()
            ).limit(limit)
            
            peers = [row[0] for row in peers_query.all()]
            
            logger.info(f"Found {len(peers)} peers for {ticker} in sector {target_sector}")
            
            return peers
            
        finally:
            close_db_session(db)
    
    def find_similar_events(
        self,
        event_id: int,
        lookback_days: int = 365
    ) -> List[Dict]:
        """
        Find similar events on peer companies.
        
        Match on: event_type, sector, similar timeframe
        
        Args:
            event_id: Target event ID
            lookback_days: How far back to look for similar events
            
        Returns:
            List of similar event dictionaries with comparison metrics
        """
        db = get_db()
        try:
            # Get target event
            target_event = db.query(Event).filter(Event.id == event_id).first()
            
            if not target_event:
                logger.warning(f"Event {event_id} not found")
                return []
            
            # Get peer companies
            peer_tickers = self.get_company_peers(target_event.ticker, limit=10)
            
            if not peer_tickers:
                logger.info(f"No peers found for {target_event.ticker}")
                return []
            
            # Define lookback window
            target_date = target_event.date
            lookback_start = target_date - timedelta(days=lookback_days)
            
            # Find similar events on peer companies
            # Match on: event_type, peer tickers, within timeframe
            similar_events_query = db.query(Event).filter(
                and_(
                    Event.ticker.in_(peer_tickers),
                    Event.event_type == target_event.event_type,
                    Event.date >= lookback_start,
                    Event.date <= target_date,
                    Event.id != event_id  # Exclude the target event itself
                )
            ).order_by(Event.date.desc())
            
            similar_events = similar_events_query.all()
            
            # Convert to dictionaries with additional context
            result = []
            for event in similar_events:
                result.append({
                    'id': event.id,
                    'ticker': event.ticker,
                    'company_name': event.company_name,
                    'event_type': event.event_type,
                    'title': event.title,
                    'description': event.description,
                    'date': event.date.isoformat() if event.date else None,
                    'source': event.source,
                    'source_url': event.source_url,
                    'impact_score': event.impact_score,
                    'direction': event.direction,
                    'confidence': event.confidence,
                    'sector': event.sector,
                    'impact_p_move': event.impact_p_move,
                    'impact_p_up': event.impact_p_up,
                    'impact_p_down': event.impact_p_down,
                    'info_tier': event.info_tier,
                    'info_subtype': event.info_subtype,
                    # Add days_before_target for context
                    'days_before_target': (target_date - event.date).days if event.date else None
                })
            
            logger.info(f"Found {len(result)} similar events for event {event_id}")
            
            return result
            
        finally:
            close_db_session(db)
    
    def compare_impact(
        self, 
        event_id: int, 
        peer_event_ids: Optional[List[int]] = None
    ) -> Dict:
        """
        Compare impact scores and actual outcomes between target event and peer events.
        
        Args:
            event_id: Target event ID
            peer_event_ids: Optional list of specific peer event IDs to compare
                           If None, automatically finds similar events
        
        Returns:
            Dictionary with target event, peer events, and comparison metrics
        """
        db = get_db()
        try:
            # Get target event
            target_event = db.query(Event).filter(Event.id == event_id).first()
            
            if not target_event:
                logger.warning(f"Event {event_id} not found")
                return {
                    'target_event': None,
                    'peer_events': [],
                    'comparison': {
                        'avg_peer_score': 0,
                        'target_vs_peers': 'unknown',
                        'peer_count': 0
                    }
                }
            
            # Get peer events
            if peer_event_ids:
                # Use specified peer event IDs
                peer_events = db.query(Event).filter(Event.id.in_(peer_event_ids)).all()
            else:
                # Auto-find similar events
                similar_events = self.find_similar_events(event_id)
                peer_event_ids = [e['id'] for e in similar_events]
                peer_events = db.query(Event).filter(Event.id.in_(peer_event_ids)).all()
            
            # Calculate comparison metrics
            peer_scores = [e.impact_score for e in peer_events if e.impact_score is not None]
            
            if peer_scores:
                avg_peer_score = sum(peer_scores) / len(peer_scores)
                
                # Determine relationship
                target_score = target_event.impact_score or 50
                score_diff = target_score - avg_peer_score
                
                if abs(score_diff) <= 5:
                    comparison_text = 'similar'
                elif score_diff > 5:
                    comparison_text = 'higher'
                else:
                    comparison_text = 'lower'
                
                # Calculate direction distribution
                directions = [e.direction for e in peer_events if e.direction]
                direction_counts = {}
                for direction in directions:
                    direction_counts[direction] = direction_counts.get(direction, 0) + 1
                
                # Calculate confidence distribution
                confidences = [e.confidence for e in peer_events if e.confidence is not None]
                avg_confidence = sum(confidences) / len(confidences) if confidences else None
                
            else:
                avg_peer_score = 0
                comparison_text = 'unknown'
                direction_counts = {}
                avg_confidence = None
            
            # Build result
            result = {
                'target_event': {
                    'id': target_event.id,
                    'ticker': target_event.ticker,
                    'company_name': target_event.company_name,
                    'event_type': target_event.event_type,
                    'title': target_event.title,
                    'description': target_event.description,
                    'date': target_event.date.isoformat() if target_event.date else None,
                    'impact_score': target_event.impact_score,
                    'direction': target_event.direction,
                    'confidence': target_event.confidence,
                    'sector': target_event.sector,
                    'impact_p_move': target_event.impact_p_move,
                    'impact_p_up': target_event.impact_p_up,
                    'impact_p_down': target_event.impact_p_down,
                },
                'peer_events': [
                    {
                        'id': e.id,
                        'ticker': e.ticker,
                        'company_name': e.company_name,
                        'event_type': e.event_type,
                        'title': e.title,
                        'description': e.description,
                        'date': e.date.isoformat() if e.date else None,
                        'impact_score': e.impact_score,
                        'direction': e.direction,
                        'confidence': e.confidence,
                        'sector': e.sector,
                        'source_url': e.source_url,
                        'impact_p_move': e.impact_p_move,
                        'impact_p_up': e.impact_p_up,
                        'impact_p_down': e.impact_p_down,
                    }
                    for e in peer_events
                ],
                'comparison': {
                    'avg_peer_score': round(avg_peer_score, 1),
                    'target_vs_peers': comparison_text,
                    'peer_count': len(peer_events),
                    'score_diff': round(target_event.impact_score - avg_peer_score, 1) if target_event.impact_score else 0,
                    'direction_distribution': direction_counts,
                    'avg_peer_confidence': round(avg_confidence, 2) if avg_confidence else None,
                }
            }
            
            return result
            
        finally:
            close_db_session(db)
    
    def get_peer_companies_detailed(
        self,
        ticker: str,
        limit: int = 5
    ) -> List[Dict]:
        """
        Get detailed information about peer companies.
        
        Args:
            ticker: Target company ticker
            limit: Maximum number of peers to return
            
        Returns:
            List of peer company details with event statistics
        """
        db = get_db()
        try:
            # Get peer tickers
            peer_tickers = self.get_company_peers(ticker, limit=limit)
            
            if not peer_tickers:
                return []
            
            # Get detailed company information with event counts
            result = []
            for peer_ticker in peer_tickers:
                company = db.query(Company).filter(Company.ticker == peer_ticker).first()
                
                if not company:
                    continue
                
                # Get event count for this company
                event_count = db.query(func.count(Event.id)).filter(
                    Event.ticker == peer_ticker
                ).scalar()
                
                # Get recent event
                recent_event = db.query(Event).filter(
                    Event.ticker == peer_ticker
                ).order_by(Event.date.desc()).first()
                
                result.append({
                    'ticker': company.ticker,
                    'name': company.name,
                    'sector': company.sector,
                    'industry': company.industry,
                    'event_count': event_count,
                    'most_recent_event': recent_event.date.isoformat() if recent_event and recent_event.date else None
                })
            
            return result
            
        finally:
            close_db_session(db)
