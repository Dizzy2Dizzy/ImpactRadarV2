"""
Backtesting Engine for Impact Radar

Validates accuracy of event impact predictions by comparing predictions to actual price movements.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
import yfinance as yf
import pandas as pd
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session
from database import get_db, close_db_session, Event, Company
from releaseradar.db.models import PriceHistory, EventScore, EventStats, ModelRegistry, EventOutcome
from releaseradar.ml.event_type_families import get_event_family, get_family_display_name
import logging

logger = logging.getLogger(__name__)


class BacktestEngine:
    """
    Backtesting engine for validating event impact prediction accuracy.
    Compares predicted impact scores and directions to actual price movements.
    
    Uses batched yfinance fetching and caching to prevent redundant downloads.
    """
    
    def __init__(self):
        self._price_cache = {}  # Cache ticker prices by date range
    
    def analyze_event_accuracy(self, event_id: int, db: Optional[Session] = None) -> Optional[Dict[str, Any]]:
        """
        Compare predicted impact to actual price movement for a single event.
        
        Args:
            event_id: Event ID to analyze
            db: Optional database session (creates one if not provided)
            
        Returns:
            Dictionary with accuracy metrics:
            {
                'event_id': int,
                'ticker': str,
                'event_type': str,
                'event_date': str,
                'predicted_direction': str,
                'predicted_score': int,
                'predicted_confidence': float,
                'actual_return_1d': float,  # 1-day return %
                'actual_return_5d': float,  # 5-day return %
                'actual_return_20d': float,  # 20-day return %
                'direction_correct_1d': bool,
                'direction_correct_5d': bool,
                'direction_correct_20d': bool,
                'magnitude_error_1d': float,
                'magnitude_error_5d': float,
                'magnitude_error_20d': float,
                'data_available': bool
            }
        """
        should_close = False
        if db is None:
            db = get_db()
            should_close = True
            
        try:
            # Get event details
            event = db.query(Event).filter(Event.id == event_id).first()
            if not event:
                logger.warning(f"Event {event_id} not found")
                return None
            
            # Determine event type family
            event_type_family = get_event_family(event.event_type)
            
            # Get model coverage info (which model was used, if any)
            model_source, model_status = self._get_model_coverage_for_event(event, db)
            
            # Get Market Echo Engine learned data (EventStats for historical patterns)
            event_stats = db.query(EventStats).filter(
                and_(
                    EventStats.ticker == event.ticker,
                    EventStats.event_type == event.event_type
                )
            ).first()
            
            # Get actual price movements using yfinance
            returns = self._calculate_actual_returns(event.ticker, event.date)
            
            if returns is None:
                logger.warning(f"Could not fetch price data for {event.ticker} around {event.date}")
                return {
                    'event_id': event.id,
                    'ticker': event.ticker,
                    'event_type': event.event_type,
                    'event_type_family': event_type_family,
                    'event_date': event.date.isoformat() if event.date else None,
                    'predicted_direction': event.direction,
                    'predicted_score': event.impact_score,
                    'predicted_confidence': event.confidence,
                    # Model coverage info
                    'model_source': model_source,
                    'model_status': model_status,
                    # Market Echo Engine ML predictions
                    'ml_adjusted_score': event.ml_adjusted_score,
                    'ml_confidence': event.ml_confidence,
                    'ml_model_version': event.ml_model_version,
                    # Probability metrics
                    'probability_move': getattr(event, 'impact_p_move', None),
                    'probability_up': getattr(event, 'impact_p_up', None),
                    'probability_down': getattr(event, 'impact_p_down', None),
                    # Historical learned patterns (EventStats)
                    'historical_win_rate': event_stats.win_rate if event_stats else None,
                    'historical_sample_size': event_stats.sample_size if event_stats else None,
                    'historical_mean_move_1d': event_stats.mean_move_1d if event_stats else None,
                    'historical_mean_move_5d': event_stats.mean_move_5d if event_stats else None,
                    'historical_mean_move_20d': event_stats.mean_move_20d if event_stats else None,
                    'actual_return_1d': None,
                    'actual_return_5d': None,
                    'actual_return_20d': None,
                    'direction_correct_1d': None,
                    'direction_correct_5d': None,
                    'direction_correct_20d': None,
                    'magnitude_error_1d': None,
                    'magnitude_error_5d': None,
                    'magnitude_error_20d': None,
                    'ml_magnitude_error_1d': None,
                    'ml_magnitude_error_5d': None,
                    'ml_magnitude_error_20d': None,
                    'data_available': False
                }
            
            # Determine predicted direction
            predicted_direction = event.direction or 'neutral'
            if predicted_direction not in ['bullish', 'bearish', 'neutral']:
                predicted_direction = 'neutral'
            
            # Calculate direction correctness for each horizon
            direction_correct_1d = self._is_direction_correct(predicted_direction, returns['1d'])
            direction_correct_5d = self._is_direction_correct(predicted_direction, returns['5d'])
            direction_correct_20d = self._is_direction_correct(predicted_direction, returns['20d'])
            
            # Calculate magnitude errors (normalized score vs actual absolute return)
            # Impact score is 0-100, we'll compare it to absolute return percentage
            normalized_score = event.impact_score / 100.0 * 10.0  # Convert to 0-10% scale
            
            magnitude_error_1d = abs(normalized_score - abs(returns['1d'])) if returns['1d'] is not None else None
            magnitude_error_5d = abs(normalized_score - abs(returns['5d'])) if returns['5d'] is not None else None
            magnitude_error_20d = abs(normalized_score - abs(returns['20d'])) if returns['20d'] is not None else None
            
            # Calculate ML-adjusted magnitude errors if ML score available
            ml_magnitude_error_1d = None
            ml_magnitude_error_5d = None
            ml_magnitude_error_20d = None
            
            if event.ml_adjusted_score is not None:
                ml_normalized_score = event.ml_adjusted_score / 100.0 * 10.0
                ml_magnitude_error_1d = abs(ml_normalized_score - abs(returns['1d'])) if returns['1d'] is not None else None
                ml_magnitude_error_5d = abs(ml_normalized_score - abs(returns['5d'])) if returns['5d'] is not None else None
                ml_magnitude_error_20d = abs(ml_normalized_score - abs(returns['20d'])) if returns['20d'] is not None else None
            
            return {
                'event_id': event.id,
                'ticker': event.ticker,
                'event_type': event.event_type,
                'event_type_family': event_type_family,
                'event_date': event.date.isoformat() if event.date else None,
                'predicted_direction': predicted_direction,
                'predicted_score': event.impact_score,
                'predicted_confidence': event.confidence,
                # Model coverage info
                'model_source': model_source,
                'model_status': model_status,
                # Market Echo Engine ML predictions
                'ml_adjusted_score': event.ml_adjusted_score,
                'ml_confidence': event.ml_confidence,
                'ml_model_version': event.ml_model_version,
                # Probability metrics from Market Echo Engine
                'probability_move': getattr(event, 'impact_p_move', None),
                'probability_up': getattr(event, 'impact_p_up', None),
                'probability_down': getattr(event, 'impact_p_down', None),
                # Historical learned patterns (EventStats)
                'historical_win_rate': event_stats.win_rate if event_stats else None,
                'historical_sample_size': event_stats.sample_size if event_stats else None,
                'historical_mean_move_1d': event_stats.mean_move_1d if event_stats else None,
                'historical_mean_move_5d': event_stats.mean_move_5d if event_stats else None,
                'historical_mean_move_20d': event_stats.mean_move_20d if event_stats else None,
                # Actual outcomes
                'actual_return_1d': returns['1d'],
                'actual_return_5d': returns['5d'],
                'actual_return_20d': returns['20d'],
                'direction_correct_1d': direction_correct_1d,
                'direction_correct_5d': direction_correct_5d,
                'direction_correct_20d': direction_correct_20d,
                # Base model errors
                'magnitude_error_1d': magnitude_error_1d,
                'magnitude_error_5d': magnitude_error_5d,
                'magnitude_error_20d': magnitude_error_20d,
                # ML model errors (for comparing ML vs base predictions)
                'ml_magnitude_error_1d': ml_magnitude_error_1d,
                'ml_magnitude_error_5d': ml_magnitude_error_5d,
                'ml_magnitude_error_20d': ml_magnitude_error_20d,
                'data_available': True
            }
            
        except Exception as e:
            logger.error(f"Error analyzing event {event_id}: {e}")
            return None
        finally:
            if should_close:
                close_db_session(db)
    
    def analyze_multiple_events(
        self,
        events: List[Event],
        db: Optional[Session] = None
    ) -> List[Dict[str, Any]]:
        """
        Analyze multiple events with batched price fetching.
        
        This is the optimized version that fetches price data once per ticker
        instead of once per event, dramatically reducing API calls.
        
        Args:
            events: List of Event objects to analyze
            db: Optional database session
            
        Returns:
            List of dictionaries with accuracy metrics for each event
        """
        if not events:
            return []
        
        # Build list of (ticker, event_date) pairs
        ticker_date_pairs = []
        for event in events:
            if event.ticker and event.date:
                ticker_date_pairs.append((event.ticker, event.date))
        
        if not ticker_date_pairs:
            return []
        
        # Batch fetch all prices (one call per unique ticker)
        logger.info(f"Batch fetching prices for {len(set(t[0] for t in ticker_date_pairs))} unique tickers across {len(events)} events")
        all_prices = self._batch_fetch_prices(ticker_date_pairs)
        
        # Analyze each event using cached prices
        results = []
        for event in events:
            if event.ticker not in all_prices or all_prices[event.ticker].empty:
                # No price data available
                results.append({
                    'event_id': event.id,
                    'ticker': event.ticker,
                    'event_type': event.event_type,
                    'event_date': event.date.isoformat() if event.date else None,
                    'predicted_direction': event.direction,
                    'predicted_score': event.impact_score,
                    'predicted_confidence': event.confidence,
                    'actual_return_1d': None,
                    'actual_return_5d': None,
                    'actual_return_20d': None,
                    'direction_correct_1d': None,
                    'direction_correct_5d': None,
                    'direction_correct_20d': None,
                    'magnitude_error_1d': None,
                    'magnitude_error_5d': None,
                    'magnitude_error_20d': None,
                    'data_available': False
                })
                continue
            
            # Calculate returns from pre-fetched data
            returns = self._calculate_actual_returns_from_data(
                all_prices[event.ticker],
                event.date
            )
            
            if returns is None:
                results.append({
                    'event_id': event.id,
                    'ticker': event.ticker,
                    'event_type': event.event_type,
                    'event_date': event.date.isoformat() if event.date else None,
                    'predicted_direction': event.direction,
                    'predicted_score': event.impact_score,
                    'predicted_confidence': event.confidence,
                    'actual_return_1d': None,
                    'actual_return_5d': None,
                    'actual_return_20d': None,
                    'direction_correct_1d': None,
                    'direction_correct_5d': None,
                    'direction_correct_20d': None,
                    'magnitude_error_1d': None,
                    'magnitude_error_5d': None,
                    'magnitude_error_20d': None,
                    'data_available': False
                })
                continue
            
            # Determine predicted direction
            predicted_direction = event.direction or 'neutral'
            if predicted_direction not in ['bullish', 'bearish', 'neutral']:
                predicted_direction = 'neutral'
            
            # Calculate direction correctness for each horizon
            direction_correct_1d = self._is_direction_correct(predicted_direction, returns['1d'])
            direction_correct_5d = self._is_direction_correct(predicted_direction, returns['5d'])
            direction_correct_20d = self._is_direction_correct(predicted_direction, returns['20d'])
            
            # Calculate magnitude errors
            normalized_score = event.impact_score / 100.0 * 10.0
            
            magnitude_error_1d = abs(normalized_score - abs(returns['1d'])) if returns['1d'] is not None else None
            magnitude_error_5d = abs(normalized_score - abs(returns['5d'])) if returns['5d'] is not None else None
            magnitude_error_20d = abs(normalized_score - abs(returns['20d'])) if returns['20d'] is not None else None
            
            results.append({
                'event_id': event.id,
                'ticker': event.ticker,
                'event_type': event.event_type,
                'event_date': event.date.isoformat() if event.date else None,
                'predicted_direction': predicted_direction,
                'predicted_score': event.impact_score,
                'predicted_confidence': event.confidence,
                'actual_return_1d': returns['1d'],
                'actual_return_5d': returns['5d'],
                'actual_return_20d': returns['20d'],
                'direction_correct_1d': direction_correct_1d,
                'direction_correct_5d': direction_correct_5d,
                'direction_correct_20d': direction_correct_20d,
                'magnitude_error_1d': magnitude_error_1d,
                'magnitude_error_5d': magnitude_error_5d,
                'magnitude_error_20d': magnitude_error_20d,
                'data_available': True
            })
        
        return results
    
    def aggregate_accuracy_by_type(
        self,
        event_type: Optional[str] = None,
        sector: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        min_confidence: float = 0.0,
        limit: int = 100,
        db: Optional[Session] = None,
        tickers: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Calculate aggregate accuracy metrics using pre-computed EventOutcome data.
        
        This is MUCH faster than fetching from yfinance as it uses cached DB results.
        
        Args:
            event_type: Filter by event type
            sector: Filter by sector
            start_date: Filter events from this date
            end_date: Filter events until this date
            min_confidence: Minimum confidence threshold
            limit: Maximum number of events to analyze
            db: Optional database session
            tickers: Optional list of tickers to filter by (for portfolio/watchlist mode)
            
        Returns:
            Dictionary with aggregated metrics
        """
        should_close = False
        if db is None:
            db = get_db()
            should_close = True
            
        try:
            # Query events joined with outcomes for direct database access
            query = db.query(Event, EventOutcome).join(
                EventOutcome, 
                Event.id == EventOutcome.event_id
            )
            
            if event_type:
                query = query.filter(Event.event_type == event_type)
            
            if sector:
                query = query.filter(Event.sector == sector)
            
            if start_date:
                query = query.filter(Event.date >= start_date)
            
            if end_date:
                query = query.filter(Event.date <= end_date)
            
            if min_confidence > 0:
                query = query.filter(Event.confidence >= min_confidence)
            
            # Filter by tickers if provided (for portfolio/watchlist mode)
            if tickers is not None:
                if len(tickers) == 0:
                    # Empty watchlist/portfolio: return empty metrics immediately
                    return self._empty_metrics_response(event_type, sector)
                else:
                    query = query.filter(Event.ticker.in_(tickers))
            
            # Only analyze past events
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=21)
            query = query.filter(Event.date <= cutoff_date)
            
            # Order by date descending and limit
            query = query.order_by(Event.date.desc()).limit(limit)
            
            results = query.all()
            
            if not results:
                return self._empty_metrics_response(event_type, sector)
            
            # Group outcomes by event and horizon
            events_data = {}
            for event, outcome in results:
                if event.id not in events_data:
                    events_data[event.id] = {
                        'event': event,
                        'outcomes': {}
                    }
                events_data[event.id]['outcomes'][outcome.horizon] = outcome
            
            # Calculate metrics across all horizons
            stats_1d = {'correct': 0, 'total': 0, 'errors': [], 'returns': [], 'high_conf': []}
            stats_5d = {'correct': 0, 'total': 0, 'errors': [], 'returns': [], 'high_conf': []}
            stats_20d = {'correct': 0, 'total': 0, 'errors': [], 'returns': [], 'high_conf': []}
            high_conf_count = 0
            
            for event_id, data in events_data.items():
                event = data['event']
                outcomes = data['outcomes']
                is_high_conf = event.confidence > 0.7
                if is_high_conf:
                    high_conf_count += 1
                
                # Process 1-day outcomes
                if '1d' in outcomes:
                    outcome = outcomes['1d']
                    stats_1d['total'] += 1
                    if outcome.direction_correct:
                        stats_1d['correct'] += 1
                        if is_high_conf:
                            stats_1d['high_conf'].append(True)
                    elif outcome.direction_correct is False:
                        if is_high_conf:
                            stats_1d['high_conf'].append(False)
                    
                    if outcome.magnitude_error is not None:
                        stats_1d['errors'].append(outcome.magnitude_error)
                    if outcome.return_pct is not None:
                        stats_1d['returns'].append(outcome.return_pct)
                
                # Process 5-day outcomes
                if '5d' in outcomes:
                    outcome = outcomes['5d']
                    stats_5d['total'] += 1
                    if outcome.direction_correct:
                        stats_5d['correct'] += 1
                        if is_high_conf:
                            stats_5d['high_conf'].append(True)
                    elif outcome.direction_correct is False:
                        if is_high_conf:
                            stats_5d['high_conf'].append(False)
                    
                    if outcome.magnitude_error is not None:
                        stats_5d['errors'].append(outcome.magnitude_error)
                    if outcome.return_pct is not None:
                        stats_5d['returns'].append(outcome.return_pct)
                
                # Process 20-day outcomes
                if '20d' in outcomes:
                    outcome = outcomes['20d']
                    stats_20d['total'] += 1
                    if outcome.direction_correct:
                        stats_20d['correct'] += 1
                        if is_high_conf:
                            stats_20d['high_conf'].append(True)
                    elif outcome.direction_correct is False:
                        if is_high_conf:
                            stats_20d['high_conf'].append(False)
                    
                    if outcome.magnitude_error is not None:
                        stats_20d['errors'].append(outcome.magnitude_error)
                    if outcome.return_pct is not None:
                        stats_20d['returns'].append(outcome.return_pct)
            
            # Calculate percentages and averages
            def calc_accuracy(correct, total):
                return round((correct / total * 100) if total > 0 else 0.0, 2)
            
            def calc_avg(values):
                return round(sum(values) / len(values) if values else 0.0, 2)
            
            def calc_high_conf_acc(high_conf_list):
                if not high_conf_list:
                    return 0.0
                return round(sum(1 for x in high_conf_list if x) / len(high_conf_list) * 100, 2)
            
            return {
                'event_type': event_type or 'all',
                'sector': sector or 'all',
                'total_events': len(events_data),
                'events_with_data': len(events_data),
                'direction_accuracy_1d': calc_accuracy(stats_1d['correct'], stats_1d['total']),
                'direction_accuracy_5d': calc_accuracy(stats_5d['correct'], stats_5d['total']),
                'direction_accuracy_20d': calc_accuracy(stats_20d['correct'], stats_20d['total']),
                'avg_magnitude_error_1d': calc_avg(stats_1d['errors']),
                'avg_magnitude_error_5d': calc_avg(stats_5d['errors']),
                'avg_magnitude_error_20d': calc_avg(stats_20d['errors']),
                'high_confidence_accuracy_1d': calc_high_conf_acc(stats_1d['high_conf']),
                'high_confidence_accuracy_5d': calc_high_conf_acc(stats_5d['high_conf']),
                'high_confidence_accuracy_20d': calc_high_conf_acc(stats_20d['high_conf']),
                'high_confidence_count': high_conf_count,
                'avg_actual_return_1d': calc_avg(stats_1d['returns']),
                'avg_actual_return_5d': calc_avg(stats_5d['returns']),
                'avg_actual_return_20d': calc_avg(stats_20d['returns'])
            }
            
        except Exception as e:
            logger.error(f"Error aggregating accuracy: {e}", exc_info=True)
            return self._empty_metrics_response(event_type, sector)
        finally:
            if should_close:
                close_db_session(db)
    
    def _empty_metrics_response(self, event_type=None, sector=None):
        """Return empty metrics response"""
        return {
            'event_type': event_type or 'all',
            'sector': sector or 'all',
            'total_events': 0,
            'events_with_data': 0,
            'direction_accuracy_1d': 0.0,
            'direction_accuracy_5d': 0.0,
            'direction_accuracy_20d': 0.0,
            'avg_magnitude_error_1d': 0.0,
            'avg_magnitude_error_5d': 0.0,
            'avg_magnitude_error_20d': 0.0,
            'high_confidence_accuracy_1d': 0.0,
            'high_confidence_accuracy_5d': 0.0,
            'high_confidence_accuracy_20d': 0.0,
            'high_confidence_count': 0,
            'avg_actual_return_1d': 0.0,
            'avg_actual_return_5d': 0.0,
            'avg_actual_return_20d': 0.0
        }
    
    def get_event_type_comparison(self, db: Optional[Session] = None) -> List[Dict[str, Any]]:
        """
        Compare accuracy across different event types.
        
        Returns:
            List of dictionaries with metrics for each event type
        """
        should_close = False
        if db is None:
            db = get_db()
            should_close = True
            
        try:
            # Get all unique event types with at least 5 events
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=21)
            
            event_type_counts = db.query(
                Event.event_type,
                func.count(Event.id).label('count')
            ).filter(
                Event.date <= cutoff_date
            ).group_by(
                Event.event_type
            ).having(
                func.count(Event.id) >= 5
            ).all()
            
            comparisons = []
            for event_type, count in event_type_counts:
                metrics = self.aggregate_accuracy_by_type(
                    event_type=event_type,
                    limit=50,
                    db=db
                )
                comparisons.append(metrics)
            
            # Sort by direction accuracy (5-day)
            comparisons.sort(key=lambda x: x.get('direction_accuracy_5d', 0), reverse=True)
            
            return comparisons
            
        except Exception as e:
            logger.error(f"Error comparing event types: {e}")
            return []
        finally:
            if should_close:
                close_db_session(db)
    
    def get_family_coverage_summary(
        self,
        db: Optional[Session] = None,
        tickers: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get per-family summary showing event counts, labeled counts, and model coverage.
        
        This endpoint surfaces:
        - Event count per family
        - Labeled count per family (events with EventOutcome data)
        - Model status per family (production/experimental/none) for each horizon
        - Error metrics per family (if models exist)
        
        Args:
            db: Optional database session
            tickers: Optional list of tickers to filter by (for portfolio/watchlist mode)
            
        Returns:
            List of family summaries with format:
            {
                'family': str,
                'family_display_name': str,
                'total_events': int,
                'labeled_count_1d': int,
                'labeled_count_5d': int,
                'labeled_count_20d': int,
                'model_status_1d': str,  # "active", "staging", or "none"
                'model_status_5d': str,
                'model_status_20d': str,
                'model_version_1d': Optional[str],
                'model_version_5d': Optional[str],
                'model_version_20d': Optional[str],
                'model_trained_at_1d': Optional[str],
                'model_trained_at_5d': Optional[str],
                'model_trained_at_20d': Optional[str],
                'mae_1d': Optional[float],
                'mae_5d': Optional[float],
                'mae_20d': Optional[float],
                'directional_accuracy_1d': Optional[float],
                'directional_accuracy_5d': Optional[float],
                'directional_accuracy_20d': Optional[float],
            }
        """
        should_close = False
        if db is None:
            db = get_db()
            should_close = True
            
        try:
            # Get all events grouped by family
            query = db.query(Event)
            
            # Filter by tickers if provided
            if tickers is not None:
                if len(tickers) == 0:
                    # Empty watchlist/portfolio: return empty list immediately
                    return []
                else:
                    query = query.filter(Event.ticker.in_(tickers))
            
            all_events = query.all()
            
            # Group events by family
            from collections import defaultdict
            family_events = defaultdict(list)
            
            for event in all_events:
                family = get_event_family(event.event_type)
                family_events[family].append(event)
            
            # Fetch ALL EventOutcome records in a single query (avoids N queries per family)
            all_event_ids = [e.id for e in all_events]
            all_outcomes = {}
            if all_event_ids:
                outcomes = db.query(EventOutcome).filter(
                    EventOutcome.event_id.in_(all_event_ids)
                ).all()
                
                # Group outcomes by (event_id, horizon) for quick lookup
                for outcome in outcomes:
                    key = (outcome.event_id, outcome.horizon)
                    all_outcomes[key] = outcome
            
            # Fetch ALL ModelRegistry records in a single query (avoids N queries per family/horizon)
            # Get all active or staging models
            all_models = db.query(ModelRegistry).filter(
                ModelRegistry.status.in_(["active", "staging"])
            ).all()
            
            # Build lookup dictionary: (family, horizon) -> model
            model_lookup = {}
            for model in all_models:
                key = (model.event_type_family, model.horizon)
                # Keep the best model (prioritize active > staging, latest promoted_at)
                if key not in model_lookup or \
                   (model.status == "active" and model_lookup[key].status == "staging") or \
                   (model.status == model_lookup[key].status and model.promoted_at > model_lookup[key].promoted_at):
                    model_lookup[key] = model
            
            # Build summary for each family
            summaries = []
            for family, events in family_events.items():
                event_ids = [e.id for e in events]
                
                # Count labeled events from the pre-fetched outcomes (in-memory)
                labeled_count_1d = sum(1 for eid in event_ids if (eid, "1d") in all_outcomes)
                labeled_count_5d = sum(1 for eid in event_ids if (eid, "5d") in all_outcomes)
                labeled_count_20d = sum(1 for eid in event_ids if (eid, "20d") in all_outcomes)
                
                # Get model coverage for each horizon using batch-fetched models
                model_info_1d = self._get_model_info_from_lookup(family, "1d", model_lookup)
                model_info_5d = self._get_model_info_from_lookup(family, "5d", model_lookup)
                model_info_20d = self._get_model_info_from_lookup(family, "20d", model_lookup)
                
                # Override status to 'staging' (experimental) for non-SEC-8K families using global models
                # Only SEC 8-K with family-specific models should show as 'active' (Production)
                status_1d = model_info_1d['status']
                if family != 'sec_8k' and model_info_1d['source'] == 'global':
                    status_1d = 'staging'
                
                status_5d = model_info_5d['status']
                if family != 'sec_8k' and model_info_5d['source'] == 'global':
                    status_5d = 'staging'
                
                status_20d = model_info_20d['status']
                if family != 'sec_8k' and model_info_20d['source'] == 'global':
                    status_20d = 'staging'
                
                summaries.append({
                    'family': family,
                    'family_display_name': get_family_display_name(family),
                    'total_events': len(events),
                    'labeled_count_1d': labeled_count_1d,
                    'labeled_count_5d': labeled_count_5d,
                    'labeled_count_20d': labeled_count_20d,
                    'model_status_1d': status_1d,
                    'model_status_5d': status_5d,
                    'model_status_20d': status_20d,
                    'model_source_1d': model_info_1d['source'],
                    'model_source_5d': model_info_5d['source'],
                    'model_source_20d': model_info_20d['source'],
                    'model_version_1d': model_info_1d['version'],
                    'model_version_5d': model_info_5d['version'],
                    'model_version_20d': model_info_20d['version'],
                    'model_trained_at_1d': model_info_1d['trained_at'],
                    'model_trained_at_5d': model_info_5d['trained_at'],
                    'model_trained_at_20d': model_info_20d['trained_at'],
                    'mae_1d': model_info_1d.get('mae'),
                    'mae_5d': model_info_5d.get('mae'),
                    'mae_20d': model_info_20d.get('mae'),
                    'directional_accuracy_1d': model_info_1d.get('directional_accuracy'),
                    'directional_accuracy_5d': model_info_5d.get('directional_accuracy'),
                    'directional_accuracy_20d': model_info_20d.get('directional_accuracy'),
                })
            
            # Sort by total events (descending)
            summaries.sort(key=lambda x: x['total_events'], reverse=True)
            
            return summaries
            
        except Exception as e:
            logger.error(f"Error getting family coverage summary: {e}")
            return []
        finally:
            if should_close:
                close_db_session(db)
    
    def _calculate_actual_returns(
        self,
        ticker: str,
        event_date: datetime,
        horizons: List[int] = [1, 5, 20]
    ) -> Optional[Dict[str, Optional[float]]]:
        """
        Calculate actual stock returns after an event using yfinance.
        
        Args:
            ticker: Stock ticker symbol
            event_date: Event date
            horizons: List of days to calculate returns for
            
        Returns:
            Dictionary with returns for each horizon:
            {'1d': 2.5, '5d': 5.2, '20d': -1.3}
            Returns None if data unavailable
        """
        try:
            # Ensure event_date is timezone-aware
            if event_date.tzinfo is None:
                event_date = event_date.replace(tzinfo=timezone.utc)
            
            # Fetch data from event date to max horizon + buffer
            max_horizon = max(horizons)
            start_date = event_date - timedelta(days=1)  # Get day before for baseline
            end_date = event_date + timedelta(days=max_horizon + 10)  # Buffer for weekends
            
            stock = yf.Ticker(ticker)
            hist = stock.history(start=start_date, end=end_date)
            
            if hist.empty or len(hist) < 2:
                logger.warning(f"Insufficient data for {ticker} around {event_date}")
                return None
            
            # Get baseline price (close on or before event date)
            baseline_prices = hist[hist.index <= event_date]
            if baseline_prices.empty:
                logger.warning(f"No baseline price for {ticker} on {event_date}")
                return None
            
            baseline_price = baseline_prices['Close'].iloc[-1]
            
            # Calculate returns for each horizon
            returns = {}
            for horizon in horizons:
                horizon_date = event_date + timedelta(days=horizon)
                future_prices = hist[hist.index > event_date]
                
                if future_prices.empty or len(future_prices) < horizon:
                    returns[f'{horizon}d'] = None
                else:
                    # Get the price closest to the horizon date (but not before event date)
                    idx = min(horizon, len(future_prices) - 1)
                    future_price = future_prices['Close'].iloc[idx]
                    
                    # Calculate percentage return
                    ret = ((future_price - baseline_price) / baseline_price) * 100.0
                    returns[f'{horizon}d'] = round(ret, 2)
            
            return returns
            
        except Exception as e:
            logger.error(f"Error calculating returns for {ticker}: {e}")
            return None
    
    def _is_direction_correct(self, predicted_direction: str, actual_return: Optional[float]) -> Optional[bool]:
        """
        Check if predicted direction matches actual return direction.
        
        Args:
            predicted_direction: 'bullish', 'bearish', or 'neutral'
            actual_return: Actual return percentage
            
        Returns:
            True if correct, False if incorrect, None if data unavailable
        """
        if actual_return is None:
            return None
        
        # Neutral predictions are correct if abs(return) < 1%
        if predicted_direction == 'neutral':
            return abs(actual_return) < 1.0
        
        # Bullish should have positive return
        if predicted_direction == 'bullish':
            return actual_return > 0
        
        # Bearish should have negative return
        if predicted_direction == 'bearish':
            return actual_return < 0
        
        # Unknown direction - consider as neutral
        return abs(actual_return) < 1.0
    
    def _batch_fetch_prices(
        self,
        ticker_date_pairs: List[tuple],
        horizons: List[int] = [1, 5, 20]
    ) -> Dict[str, pd.DataFrame]:
        """
        Batch fetch prices for multiple tickers across date ranges.
        Groups by ticker and fetches once per ticker with widest date range,
        then returns the full DataFrame for each ticker.
        
        Args:
            ticker_date_pairs: List of (ticker, event_date) tuples
            horizons: List of days to calculate returns for
            
        Returns:
            Dictionary mapping ticker to price DataFrame
        """
        # Group by ticker and find min/max dates needed
        ticker_ranges = {}
        max_horizon = max(horizons)
        
        for ticker, event_date in ticker_date_pairs:
            # Ensure event_date is timezone-aware
            if event_date.tzinfo is None:
                event_date = event_date.replace(tzinfo=timezone.utc)
            
            start_date = event_date - timedelta(days=1)
            end_date = event_date + timedelta(days=max_horizon + 10)
            
            if ticker not in ticker_ranges:
                ticker_ranges[ticker] = {'min': start_date, 'max': end_date}
            else:
                ticker_ranges[ticker]['min'] = min(ticker_ranges[ticker]['min'], start_date)
                ticker_ranges[ticker]['max'] = max(ticker_ranges[ticker]['max'], end_date)
        
        # Fetch once per ticker with full range
        all_prices = {}
        for ticker, range_info in ticker_ranges.items():
            cache_key = f"{ticker}_{range_info['min'].date()}_{range_info['max'].date()}"
            
            if cache_key in self._price_cache:
                all_prices[ticker] = self._price_cache[cache_key]
                logger.info(f"Using cached price data for {ticker}")
            else:
                try:
                    logger.info(f"Fetching price data for {ticker} from {range_info['min'].date()} to {range_info['max'].date()}")
                    stock = yf.Ticker(ticker)
                    hist = stock.history(start=range_info['min'], end=range_info['max'])
                    
                    if not hist.empty:
                        self._price_cache[cache_key] = hist
                        all_prices[ticker] = hist
                    else:
                        logger.warning(f"No price data available for {ticker}")
                        all_prices[ticker] = pd.DataFrame()
                        
                except Exception as e:
                    logger.error(f"Error fetching prices for {ticker}: {e}")
                    all_prices[ticker] = pd.DataFrame()
        
        return all_prices
    
    def _calculate_actual_returns_from_data(
        self,
        price_data: pd.DataFrame,
        event_date: datetime,
        horizons: List[int] = [1, 5, 20]
    ) -> Optional[Dict[str, Optional[float]]]:
        """
        Calculate actual stock returns from pre-fetched price data.
        
        Args:
            price_data: DataFrame with price history
            event_date: Event date
            horizons: List of days to calculate returns for
            
        Returns:
            Dictionary with returns for each horizon:
            {'1d': 2.5, '5d': 5.2, '20d': -1.3}
            Returns None if data unavailable
        """
        try:
            if price_data.empty:
                return None
            
            # Ensure event_date is timezone-aware
            if event_date.tzinfo is None:
                event_date = event_date.replace(tzinfo=timezone.utc)
            
            # Get baseline price (close on or before event date)
            baseline_prices = price_data[price_data.index <= event_date]
            if baseline_prices.empty:
                return None
            
            baseline_price = baseline_prices['Close'].iloc[-1]
            
            # Calculate returns for each horizon
            returns = {}
            for horizon in horizons:
                future_prices = price_data[price_data.index > event_date]
                
                if future_prices.empty or len(future_prices) < horizon:
                    returns[f'{horizon}d'] = None
                else:
                    # Get the price closest to the horizon date (but not before event date)
                    idx = min(horizon, len(future_prices) - 1)
                    future_price = future_prices['Close'].iloc[idx]
                    
                    # Calculate percentage return
                    ret = ((future_price - baseline_price) / baseline_price) * 100.0
                    returns[f'{horizon}d'] = round(ret, 2)
            
            return returns
            
        except Exception as e:
            logger.error(f"Error calculating returns from data: {e}")
            return None
    
    def _get_model_coverage_for_event(
        self,
        event: Event,
        db: Session
    ) -> tuple[str, str]:
        """
        Determine which model was used (or would be used) for an event.
        
        Args:
            event: Event object
            db: Database session
            
        Returns:
            Tuple of (model_source, model_status) where:
            - model_source: "family-specific", "global", or "deterministic"
            - model_status: "active", "staging", or "none"
        """
        # Determine event family
        event_type_family = get_event_family(event.event_type)
        
        # Check if there's a family-specific model (active or staging)
        family_model = db.query(ModelRegistry).filter(
            ModelRegistry.event_type_family == event_type_family,
            ModelRegistry.horizon == "1d",  # Use 1d as representative
            ModelRegistry.status.in_(["active", "staging"])
        ).order_by(
            # Prioritize active over staging
            func.case(
                (ModelRegistry.status == "active", 1),
                else_=2
            )
        ).first()
        
        if family_model:
            return "family-specific", family_model.status
        
        # Check if there's a global model
        global_model = db.query(ModelRegistry).filter(
            ModelRegistry.event_type_family == "all",
            ModelRegistry.horizon == "1d",
            ModelRegistry.status.in_(["active", "staging"])
        ).order_by(
            func.case(
                (ModelRegistry.status == "active", 1),
                else_=2
            )
        ).first()
        
        if global_model:
            return "global", global_model.status
        
        # No models available
        return "deterministic", "none"
    
    def _get_model_info_from_lookup(
        self,
        family: str,
        horizon: str,
        model_lookup: Dict[tuple, 'ModelRegistry']
    ) -> Dict[str, Any]:
        """
        Get model information from pre-fetched models lookup (no database queries).
        
        Args:
            family: Event type family (e.g., "sec_8k", "earnings")
            horizon: Time horizon ("1d", "5d", "20d")
            model_lookup: Dictionary mapping (family, horizon) -> ModelRegistry
            
        Returns:
            Dictionary with model info
        """
        # Try family-specific model first
        family_model = model_lookup.get((family, horizon))
        
        if family_model:
            return {
                'status': family_model.status,
                'source': 'family-specific',
                'version': family_model.version,
                'trained_at': family_model.trained_at.isoformat() if family_model.trained_at else None,
                'mae': family_model.metrics.get('mae') if family_model.metrics else None,
                'directional_accuracy': family_model.metrics.get('directional_accuracy') if family_model.metrics else None
            }
        
        # Try global model
        global_model = model_lookup.get(("all", horizon))
        
        if global_model:
            return {
                'status': global_model.status,
                'source': 'global',
                'version': global_model.version,
                'trained_at': global_model.trained_at.isoformat() if global_model.trained_at else None,
                'mae': global_model.metrics.get('mae') if global_model.metrics else None,
                'directional_accuracy': global_model.metrics.get('directional_accuracy') if global_model.metrics else None
            }
        
        # No model available
        return {
            'status': 'none',
            'source': 'deterministic',
            'version': None,
            'trained_at': None,
            'mae': None,
            'directional_accuracy': None
        }
    
    def _get_model_info_for_family(
        self,
        family: str,
        horizon: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Get model information for a specific family and horizon.
        
        DEPRECATED: Use _get_model_info_from_lookup with batch-fetched models instead.
        This method makes 2 database queries per call and should be avoided.
        
        Args:
            family: Event type family (e.g., "sec_8k", "earnings")
            horizon: Time horizon ("1d", "5d", "20d")
            db: Database session
            
        Returns:
            Dictionary with model info:
            {
                'status': str,  # "active", "staging", or "none"
                'source': str,  # "family-specific", "global", or "deterministic"
                'version': Optional[str],
                'trained_at': Optional[str],
                'mae': Optional[float],
                'directional_accuracy': Optional[float]
            }
        """
        # Try family-specific model first
        family_model = db.query(ModelRegistry).filter(
            ModelRegistry.event_type_family == family,
            ModelRegistry.horizon == horizon,
            ModelRegistry.status.in_(["active", "staging"])
        ).order_by(
            # Prioritize active over staging
            func.case(
                (ModelRegistry.status == "active", 1),
                else_=2
            ),
            ModelRegistry.promoted_at.desc()
        ).first()
        
        if family_model:
            return {
                'status': family_model.status,
                'source': 'family-specific',
                'version': family_model.version,
                'trained_at': family_model.trained_at.isoformat() if family_model.trained_at else None,
                'mae': family_model.metrics.get('mae') if family_model.metrics else None,
                'directional_accuracy': family_model.metrics.get('directional_accuracy') if family_model.metrics else None
            }
        
        # Try global model
        global_model = db.query(ModelRegistry).filter(
            ModelRegistry.event_type_family == "all",
            ModelRegistry.horizon == horizon,
            ModelRegistry.status.in_(["active", "staging"])
        ).order_by(
            func.case(
                (ModelRegistry.status == "active", 1),
                else_=2
            ),
            ModelRegistry.promoted_at.desc()
        ).first()
        
        if global_model:
            return {
                'status': global_model.status,
                'source': 'global',
                'version': global_model.version,
                'trained_at': global_model.trained_at.isoformat() if global_model.trained_at else None,
                'mae': global_model.metrics.get('mae') if global_model.metrics else None,
                'directional_accuracy': global_model.metrics.get('directional_accuracy') if global_model.metrics else None
            }
        
        # No model available
        return {
            'status': 'none',
            'source': 'deterministic',
            'version': None,
            'trained_at': None,
            'mae': None,
            'directional_accuracy': None
        }
