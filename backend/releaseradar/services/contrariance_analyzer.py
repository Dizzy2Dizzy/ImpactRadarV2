"""
Contrariance Analyzer - Identifies events where predictions diverged from actual outcomes.

This service powers the "Hidden Bearish" detection in the Market Echo Engine by:
1. Finding events classified as neutral/positive that resulted in stock declines
2. Computing contrarian patterns for ticker/event_type combinations
3. Providing training signals for the ML model to learn "hidden bearish" patterns

The goal is to teach the ML model: "When you see this pattern, even if it looks
neutral/positive, the stock tends to go down."
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session

from releaseradar.db.models import Event, EventOutcome, EventStats
from releaseradar.log_config import logger


def utc_now() -> datetime:
    """Return timezone-aware UTC datetime."""
    from datetime import timezone
    return datetime.now(timezone.utc)


@dataclass
class ContrarianEvent:
    """An event where prediction diverged from actual outcome."""
    event_id: int
    ticker: str
    event_type: str
    event_date: datetime
    title: str
    
    # Prediction
    predicted_direction: str  # What we predicted (positive/neutral/negative)
    confidence: float
    impact_score: int
    
    # Actual outcome
    realized_return_1d: float  # Actual T+1 return
    realized_return_5d: Optional[float]
    realized_return_20d: Optional[float]
    
    # Contrariance metrics
    divergence_severity: float  # How bad was the divergence (0-1)
    is_hidden_bearish: bool  # True if predicted positive/neutral but went down
    
    # Pattern-based probability (from Event model)
    hidden_bearish_prob: Optional[float] = None  # Historical probability from ticker/event_type pattern


@dataclass
class ContrarianPattern:
    """A pattern of contrarian outcomes for a ticker/event_type combination."""
    ticker: str
    event_type: str
    
    # Sample metrics
    total_events: int
    contrarian_events: int
    contrarian_rate: float  # % of events that were contrarian
    
    # Severity metrics
    avg_negative_divergence: float  # Average return when predicted positive/neutral but went down
    max_negative_divergence: float  # Worst case
    
    # Hidden bearish probability
    hidden_bearish_probability: float  # Probability that next positive/neutral event will decline
    confidence: float  # Confidence in this pattern (based on sample size)


class ContrarianSeThresholds:
    """Thresholds for identifying contrarian events."""
    
    # Return thresholds (in percentage points)
    MIN_DECLINE_FOR_HIDDEN_BEARISH = -1.0  # Minimum decline to consider "hidden bearish"
    SIGNIFICANT_DECLINE = -3.0  # Threshold for significant decline
    SEVERE_DECLINE = -10.0  # Threshold for severe decline
    
    # Pattern detection thresholds
    MIN_SAMPLE_SIZE = 3  # Minimum events to establish a pattern
    HIGH_CONTRARIAN_RATE = 0.40  # 40%+ contrarian rate is concerning
    VERY_HIGH_CONTRARIAN_RATE = 0.60  # 60%+ is very concerning
    
    # Confidence calculation
    BASE_CONFIDENCE = 0.3
    SAMPLE_SIZE_BOOST = 0.1  # Per 5 samples
    MAX_CONFIDENCE = 0.95


class ContrarianAnalyzer:
    """Analyzes events where predictions diverged from actual outcomes."""
    
    def __init__(self, db: Session):
        self.db = db
        self.thresholds = ContrarianSeThresholds()
    
    def find_contrarian_events(
        self,
        ticker: Optional[str] = None,
        event_type: Optional[str] = None,
        lookback_days: int = 90,
        min_decline: float = None
    ) -> List[ContrarianEvent]:
        """
        Find events where neutral/positive predictions resulted in stock declines.
        
        Args:
            ticker: Optional ticker filter
            event_type: Optional event type filter
            lookback_days: How many days back to search
            min_decline: Minimum decline threshold (default from config)
            
        Returns:
            List of ContrarianEvent objects
        """
        if min_decline is None:
            min_decline = self.thresholds.MIN_DECLINE_FOR_HIDDEN_BEARISH
        
        cutoff_date = utc_now() - timedelta(days=lookback_days)
        
        # Query events with outcomes where:
        # 1. Direction was positive or neutral
        # 2. Actual return was negative (below threshold)
        query = (
            select(Event, EventOutcome)
            .join(EventOutcome, Event.id == EventOutcome.event_id)
            .where(EventOutcome.horizon == "1d")
            .where(Event.date >= cutoff_date)
            .where(Event.direction.in_(["positive", "neutral"]))
            .where(EventOutcome.return_pct < min_decline)
        )
        
        if ticker:
            query = query.where(Event.ticker == ticker)
        if event_type:
            query = query.where(Event.event_type == event_type)
        
        query = query.order_by(EventOutcome.return_pct.asc())  # Most severe first
        
        results = self.db.execute(query).all()
        
        contrarian_events = []
        for event, outcome_1d in results:
            # Get 5d and 20d outcomes if available
            outcome_5d = self.db.execute(
                select(EventOutcome)
                .where(EventOutcome.event_id == event.id)
                .where(EventOutcome.horizon == "5d")
            ).scalar_one_or_none()
            
            outcome_20d = self.db.execute(
                select(EventOutcome)
                .where(EventOutcome.event_id == event.id)
                .where(EventOutcome.horizon == "20d")
            ).scalar_one_or_none()
            
            # Calculate divergence severity
            divergence_severity = self._calculate_divergence_severity(
                predicted_direction=event.direction,
                actual_return=outcome_1d.return_pct,
                confidence=event.confidence
            )
            
            contrarian_event = ContrarianEvent(
                event_id=event.id,
                ticker=event.ticker,
                event_type=event.event_type,
                event_date=event.date,
                title=event.title,
                predicted_direction=event.direction,
                confidence=event.confidence,
                impact_score=event.impact_score,
                realized_return_1d=outcome_1d.return_pct,
                realized_return_5d=outcome_5d.return_pct if outcome_5d else None,
                realized_return_20d=outcome_20d.return_pct if outcome_20d else None,
                divergence_severity=divergence_severity,
                is_hidden_bearish=True,
                hidden_bearish_prob=event.hidden_bearish_prob  # Pattern-based probability from Event model
            )
            contrarian_events.append(contrarian_event)
        
        logger.info(f"Found {len(contrarian_events)} contrarian events "
                   f"(lookback={lookback_days}d, min_decline={min_decline}%)")
        
        return contrarian_events
    
    def _calculate_divergence_severity(
        self,
        predicted_direction: str,
        actual_return: float,
        confidence: float
    ) -> float:
        """
        Calculate how severe the prediction divergence was.
        
        Returns:
            Severity score 0.0 to 1.0 (higher = more severe divergence)
        """
        # Base severity from return magnitude
        if actual_return <= self.thresholds.SEVERE_DECLINE:
            return_severity = 1.0
        elif actual_return <= self.thresholds.SIGNIFICANT_DECLINE:
            return_severity = 0.7
        elif actual_return <= self.thresholds.MIN_DECLINE_FOR_HIDDEN_BEARISH:
            return_severity = 0.4
        else:
            return_severity = 0.2
        
        # Boost severity if prediction was confident
        confidence_boost = 0.0
        if predicted_direction == "positive" and confidence >= 0.6:
            confidence_boost = 0.2  # High confidence positive prediction that failed
        elif predicted_direction == "positive":
            confidence_boost = 0.1  # Any positive prediction that failed
        
        return min(1.0, return_severity + confidence_boost)
    
    def compute_contrarian_patterns(
        self,
        lookback_days: int = 180,
        min_sample_size: int = None
    ) -> List[ContrarianPattern]:
        """
        Compute contrarian patterns for all ticker/event_type combinations.
        
        This identifies which combinations have historically had their
        positive/neutral predictions result in price declines.
        
        Args:
            lookback_days: How many days back to analyze
            min_sample_size: Minimum events required for a pattern
            
        Returns:
            List of ContrarianPattern objects sorted by contrarian rate
        """
        if min_sample_size is None:
            min_sample_size = self.thresholds.MIN_SAMPLE_SIZE
        
        cutoff_date = utc_now() - timedelta(days=lookback_days)
        
        # Get all events with outcomes in lookback period
        query = (
            select(
                Event.ticker,
                Event.event_type,
                Event.direction,
                EventOutcome.return_pct
            )
            .join(EventOutcome, Event.id == EventOutcome.event_id)
            .where(EventOutcome.horizon == "1d")
            .where(Event.date >= cutoff_date)
            .where(Event.direction.in_(["positive", "neutral"]))
        )
        
        results = self.db.execute(query).all()
        
        # Group by ticker + event_type
        patterns_data = defaultdict(lambda: {
            "total": 0,
            "contrarian": 0,
            "negative_returns": []
        })
        
        for ticker, event_type, direction, return_pct in results:
            key = (ticker, event_type)
            patterns_data[key]["total"] += 1
            
            # Check if this was contrarian (predicted positive/neutral but went down)
            if return_pct < self.thresholds.MIN_DECLINE_FOR_HIDDEN_BEARISH:
                patterns_data[key]["contrarian"] += 1
                patterns_data[key]["negative_returns"].append(return_pct)
        
        # Build pattern objects
        patterns = []
        for (ticker, event_type), data in patterns_data.items():
            if data["total"] < min_sample_size:
                continue
            
            contrarian_rate = data["contrarian"] / data["total"]
            negative_returns = data["negative_returns"]
            
            avg_negative = (
                sum(negative_returns) / len(negative_returns) 
                if negative_returns else 0.0
            )
            max_negative = min(negative_returns) if negative_returns else 0.0
            
            # Calculate hidden bearish probability and confidence
            hidden_bearish_prob = contrarian_rate
            confidence = self._calculate_pattern_confidence(
                sample_size=data["total"],
                contrarian_rate=contrarian_rate
            )
            
            pattern = ContrarianPattern(
                ticker=ticker,
                event_type=event_type,
                total_events=data["total"],
                contrarian_events=data["contrarian"],
                contrarian_rate=contrarian_rate,
                avg_negative_divergence=avg_negative,
                max_negative_divergence=max_negative,
                hidden_bearish_probability=hidden_bearish_prob,
                confidence=confidence
            )
            patterns.append(pattern)
        
        # Sort by contrarian rate (descending)
        patterns.sort(key=lambda p: p.contrarian_rate, reverse=True)
        
        logger.info(f"Computed {len(patterns)} contrarian patterns "
                   f"(lookback={lookback_days}d, min_samples={min_sample_size})")
        
        return patterns
    
    def _calculate_pattern_confidence(
        self,
        sample_size: int,
        contrarian_rate: float
    ) -> float:
        """Calculate confidence in a contrarian pattern."""
        # Base confidence
        confidence = self.thresholds.BASE_CONFIDENCE
        
        # Boost for sample size (every 5 samples adds 0.1)
        sample_boost = (sample_size // 5) * self.thresholds.SAMPLE_SIZE_BOOST
        confidence += sample_boost
        
        # Boost for high contrarian rate
        if contrarian_rate >= self.thresholds.VERY_HIGH_CONTRARIAN_RATE:
            confidence += 0.2
        elif contrarian_rate >= self.thresholds.HIGH_CONTRARIAN_RATE:
            confidence += 0.1
        
        return min(self.thresholds.MAX_CONFIDENCE, confidence)
    
    def get_hidden_bearish_probability(
        self,
        ticker: str,
        event_type: str
    ) -> Tuple[float, float, Optional[ContrarianPattern]]:
        """
        Get the probability that a new positive/neutral event for this
        ticker/event_type will actually result in a price decline.
        
        Returns:
            Tuple of (probability, confidence, pattern)
        """
        patterns = self.compute_contrarian_patterns(
            lookback_days=180,
            min_sample_size=2  # Lower threshold for single lookup
        )
        
        # Find matching pattern
        for pattern in patterns:
            if pattern.ticker == ticker and pattern.event_type == event_type:
                return (
                    pattern.hidden_bearish_probability,
                    pattern.confidence,
                    pattern
                )
        
        # No pattern found - return default low probability
        return (0.0, 0.0, None)
    
    def get_contrarian_summary(
        self,
        lookback_days: int = 90
    ) -> Dict:
        """
        Get a summary of contrarian analysis across the dataset.
        
        Returns:
            Dictionary with summary statistics
        """
        cutoff_date = utc_now() - timedelta(days=lookback_days)
        
        # Total events with outcomes
        total_events = self.db.execute(
            select(func.count(EventOutcome.id))
            .join(Event, Event.id == EventOutcome.event_id)
            .where(EventOutcome.horizon == "1d")
            .where(Event.date >= cutoff_date)
            .where(Event.direction.in_(["positive", "neutral"]))
        ).scalar() or 0
        
        # Contrarian events (predicted positive/neutral, went down)
        contrarian_count = self.db.execute(
            select(func.count(EventOutcome.id))
            .join(Event, Event.id == EventOutcome.event_id)
            .where(EventOutcome.horizon == "1d")
            .where(Event.date >= cutoff_date)
            .where(Event.direction.in_(["positive", "neutral"]))
            .where(EventOutcome.return_pct < self.thresholds.MIN_DECLINE_FOR_HIDDEN_BEARISH)
        ).scalar() or 0
        
        # Severe contrarian (>10% decline)
        severe_count = self.db.execute(
            select(func.count(EventOutcome.id))
            .join(Event, Event.id == EventOutcome.event_id)
            .where(EventOutcome.horizon == "1d")
            .where(Event.date >= cutoff_date)
            .where(Event.direction.in_(["positive", "neutral"]))
            .where(EventOutcome.return_pct < self.thresholds.SEVERE_DECLINE)
        ).scalar() or 0
        
        # Get top contrarian patterns
        patterns = self.compute_contrarian_patterns(lookback_days=lookback_days)
        top_patterns = patterns[:10]  # Top 10 by contrarian rate
        
        contrarian_rate = contrarian_count / total_events if total_events > 0 else 0.0
        
        return {
            "lookback_days": lookback_days,
            "total_positive_neutral_events": total_events,
            "contrarian_events": contrarian_count,
            "contrarian_rate": round(contrarian_rate * 100, 2),
            "severe_contrarian_events": severe_count,
            "patterns_detected": len(patterns),
            "top_contrarian_patterns": [
                {
                    "ticker": p.ticker,
                    "event_type": p.event_type,
                    "contrarian_rate": round(p.contrarian_rate * 100, 1),
                    "sample_size": p.total_events,
                    "avg_decline": round(p.avg_negative_divergence, 2),
                    "hidden_bearish_prob": round(p.hidden_bearish_probability * 100, 1),
                    "confidence": round(p.confidence * 100, 1),
                }
                for p in top_patterns
            ],
            "thresholds": {
                "min_decline": self.thresholds.MIN_DECLINE_FOR_HIDDEN_BEARISH,
                "significant_decline": self.thresholds.SIGNIFICANT_DECLINE,
                "severe_decline": self.thresholds.SEVERE_DECLINE,
            }
        }
    
    def export_contrarian_training_samples(
        self,
        lookback_days: int = 180
    ) -> List[Dict]:
        """
        Export contrarian events as training samples for the ML model.
        
        These samples teach the model: "When you see this pattern, even if
        deterministic scoring says positive/neutral, the stock tends to decline."
        
        Returns:
            List of training sample dicts with event features and outcome labels
        """
        contrarian_events = self.find_contrarian_events(
            lookback_days=lookback_days,
            min_decline=-0.5  # Include even small declines for training
        )
        
        training_samples = []
        for ce in contrarian_events:
            sample = {
                "event_id": ce.event_id,
                "ticker": ce.ticker,
                "event_type": ce.event_type,
                "predicted_direction": ce.predicted_direction,
                "confidence": ce.confidence,
                "impact_score": ce.impact_score,
                "realized_return_1d": ce.realized_return_1d,
                "realized_return_5d": ce.realized_return_5d,
                "divergence_severity": ce.divergence_severity,
                "is_hidden_bearish": ce.is_hidden_bearish,
                # Label for ML training: 1 = this was actually bearish
                "hidden_bearish_label": 1,
            }
            training_samples.append(sample)
        
        logger.info(f"Exported {len(training_samples)} contrarian training samples")
        
        return training_samples
