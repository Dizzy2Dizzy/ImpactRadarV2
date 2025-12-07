"""
Topology Feature Extractor for Impact Radar ML System.

Wrapper that extracts topology features from PersistentTopologyService
and integrates them into the feature pipeline for ML models.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from releaseradar.services.persistent_topology import (
    PersistentTopologyService,
    PersistenceFeatures,
)
from releaseradar.ml.feature_store.cache import TopologyFeatureCache
from releaseradar.log_config import logger


@dataclass
class TopologyFeatureVector:
    """
    Topology features ready for ML model consumption.
    
    These features capture the "shape" of price patterns using
    Topological Data Analysis (TDA) and persistent homology.
    """
    betti_0_count: int = 0
    betti_1_count: int = 0
    max_lifetime_h0: float = 0.0
    max_lifetime_h1: float = 0.0
    mean_lifetime_h0: float = 0.0
    mean_lifetime_h1: float = 0.0
    total_persistence_h0: float = 0.0
    total_persistence_h1: float = 0.0
    persistence_entropy: float = 0.0
    topological_complexity: float = 0.0
    betti_curve_h0_mean: float = 0.0
    betti_curve_h1_mean: float = 0.0
    has_features: bool = False
    computed_at: datetime = field(default_factory=datetime.utcnow)
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for ML model input."""
        return {
            "persistent_betti0_count": float(self.betti_0_count),
            "persistent_betti1_count": float(self.betti_1_count),
            "persistent_max_lifetime_h0": self.max_lifetime_h0,
            "persistent_max_lifetime_h1": self.max_lifetime_h1,
            "persistent_mean_lifetime_h0": self.mean_lifetime_h0,
            "persistent_mean_lifetime_h1": self.mean_lifetime_h1,
            "persistent_total_h0": self.total_persistence_h0,
            "persistent_total_h1": self.total_persistence_h1,
            "persistent_entropy": self.persistence_entropy,
            "persistent_complexity": self.topological_complexity,
            "persistent_betti_h0_mean": self.betti_curve_h0_mean,
            "persistent_betti_h1_mean": self.betti_curve_h1_mean,
            "has_persistent_features": float(self.has_features),
        }
    
    @classmethod
    def from_persistence_features(cls, pf: PersistenceFeatures) -> "TopologyFeatureVector":
        """Create from PersistenceFeatures object."""
        return cls(
            betti_0_count=pf.betti0_count,
            betti_1_count=pf.betti1_count,
            max_lifetime_h0=pf.max_lifetime_h0,
            max_lifetime_h1=pf.max_lifetime_h1,
            mean_lifetime_h0=pf.mean_lifetime_h0,
            mean_lifetime_h1=pf.mean_lifetime_h1,
            total_persistence_h0=pf.total_persistence_h0,
            total_persistence_h1=pf.total_persistence_h1,
            persistence_entropy=pf.persistence_entropy,
            topological_complexity=pf.topological_complexity,
            betti_curve_h0_mean=pf.betti_curve_h0_mean,
            betti_curve_h1_mean=pf.betti_curve_h1_mean,
            has_features=pf.has_persistent_features,
            computed_at=pf.computed_at or datetime.utcnow(),
            error_message=pf.error_message,
        )
    
    @classmethod
    def default(cls) -> "TopologyFeatureVector":
        """Return default (zero) features."""
        return cls()


class TopologyFeatureExtractor:
    """
    Extracts topology features for ML models.
    
    Features extracted for each stock/event:
    - betti_0_count, betti_1_count: Topological feature counts
    - max_lifetime_h0, max_lifetime_h1: Feature persistence
    - persistence_entropy: Market chaos/complexity indicator
    - topological_complexity: Combined complexity score
    
    Uses caching to avoid re-computation of expensive TDA operations.
    """
    
    DEFAULT_LOOKBACK_DAYS = 30
    DEFAULT_EMBEDDING_DIM = 3
    DEFAULT_DELAY = 2
    
    def __init__(
        self,
        db: Session,
        use_cache: bool = True,
        cache_ttl_seconds: int = 7200  # 2 hours
    ):
        self.db = db
        self.use_cache = use_cache
        self.topology_service = PersistentTopologyService(db)
        
        if use_cache:
            self._cache = TopologyFeatureCache(ttl_seconds=cache_ttl_seconds)
        else:
            self._cache = None
        
        self._extraction_count = 0
        self._cache_hits = 0
        self._errors = 0
    
    def extract_features(
        self,
        ticker: str,
        event_date: datetime,
        lookback_days: int = DEFAULT_LOOKBACK_DAYS,
        embedding_dim: int = DEFAULT_EMBEDDING_DIM,
        delay: int = DEFAULT_DELAY,
    ) -> TopologyFeatureVector:
        """
        Extract topology features for a stock around an event date.
        
        Args:
            ticker: Stock ticker symbol
            event_date: Date of the event
            lookback_days: Days of price history to use
            embedding_dim: Dimension for Takens embedding
            delay: Time delay for Takens embedding
            
        Returns:
            TopologyFeatureVector with topological statistics
        """
        self._extraction_count += 1
        
        if self.use_cache and self._cache:
            cached = self._cache.get_by_ticker_date(ticker, event_date)
            if cached is not None:
                self._cache_hits += 1
                return TopologyFeatureVector(**cached)
        
        try:
            persistence_features = self.topology_service.get_persistence_features(
                ticker=ticker,
                event_date=event_date,
                lookback_days=lookback_days,
                embedding_dim=embedding_dim,
                delay=delay,
                use_cache=True,  # Use internal cache too
            )
            
            feature_vector = TopologyFeatureVector.from_persistence_features(persistence_features)
            
            if self.use_cache and self._cache and feature_vector.has_features:
                self._cache.set_topology_features(
                    features=feature_vector.to_dict(),
                    ticker=ticker,
                    event_date=event_date,
                )
            
            return feature_vector
            
        except Exception as e:
            self._errors += 1
            logger.warning(f"Topology extraction failed for {ticker} @ {event_date}: {e}")
            return TopologyFeatureVector(
                has_features=False,
                error_message=str(e),
            )
    
    def extract_batch(
        self,
        events: List[Dict[str, Any]],
        lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    ) -> Dict[int, TopologyFeatureVector]:
        """
        Extract topology features for multiple events.
        
        Args:
            events: List of dicts with event_id, ticker, date
            lookback_days: Days of price history to use
            
        Returns:
            Dict mapping event_id to TopologyFeatureVector
        """
        results = {}
        
        for event in events:
            event_id = event.get("event_id")
            ticker = event.get("ticker")
            event_date = event.get("date") or event.get("event_date")
            
            if not event_id or not ticker or not event_date:
                continue
            
            features = self.extract_features(
                ticker=ticker,
                event_date=event_date,
                lookback_days=lookback_days,
            )
            
            results[event_id] = features
        
        logger.info(
            f"Batch extraction complete: {len(results)} events, "
            f"{self._cache_hits}/{self._extraction_count} cache hits"
        )
        
        return results
    
    def get_feature_importance_hints(self) -> Dict[str, str]:
        """
        Get hints about feature importance for model training.
        
        Based on empirical observations from TDA literature:
        - betti_1_count (loops) often correlates with volatility regimes
        - persistence_entropy indicates market complexity/chaos
        - max_lifetime_h1 captures dominant cyclical patterns
        """
        return {
            "persistent_betti1_count": (
                "Number of loops in price pattern - key predictor for regime changes. "
                "High values often precede increased volatility."
            ),
            "persistent_entropy": (
                "Normalized persistence entropy - market chaos indicator. "
                "High entropy suggests unpredictable market conditions."
            ),
            "persistent_max_lifetime_h1": (
                "Longest-lived loop - captures dominant cyclical patterns. "
                "Longer lifetimes suggest more stable market structure."
            ),
            "persistent_complexity": (
                "Combined topological complexity score. "
                "Higher values indicate more complex price dynamics."
            ),
        }
    
    def compute_similarity(
        self,
        ticker1: str,
        date1: datetime,
        ticker2: str,
        date2: datetime,
        lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    ) -> float:
        """
        Compute topological similarity between two events.
        
        Uses the underlying PersistentTopologyService's bottleneck distance
        to measure similarity between price patterns.
        
        Args:
            ticker1, date1: First event
            ticker2, date2: Second event
            lookback_days: Days of price history
            
        Returns:
            Similarity score between 0 and 1 (1 = identical topology)
        """
        return self.topology_service.compare_events(
            ticker1=ticker1,
            date1=date1,
            ticker2=ticker2,
            date2=date2,
            lookback_days=lookback_days,
        )
    
    def find_similar_patterns(
        self,
        ticker: str,
        event_date: datetime,
        candidate_tickers: List[str],
        top_k: int = 5,
        lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    ) -> List[Dict[str, Any]]:
        """
        Find events with similar topological patterns.
        
        Useful for finding historical analogues that might help
        predict the outcome of a new event.
        
        Args:
            ticker: Target ticker
            event_date: Target event date
            candidate_tickers: List of tickers to compare against
            top_k: Number of similar events to return
            lookback_days: Days of price history
            
        Returns:
            List of similar events with similarity scores
        """
        similar = self.topology_service.find_similar_events(
            ticker=ticker,
            event_date=event_date,
            candidate_tickers=candidate_tickers,
            top_k=top_k,
            lookback_days=lookback_days,
        )
        
        return [
            {
                "ticker": t,
                "date": d.isoformat() if d else None,
                "similarity": s,
            }
            for t, d, s in similar
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get extraction statistics."""
        stats = {
            "total_extractions": self._extraction_count,
            "cache_hits": self._cache_hits,
            "errors": self._errors,
            "cache_hit_rate": self._cache_hits / self._extraction_count if self._extraction_count > 0 else 0,
            "ripser_available": self.topology_service._ripser_available,
        }
        
        if self._cache:
            stats["cache_stats"] = self._cache.get_stats().to_dict()
        
        return stats
    
    def clear_cache(self):
        """Clear the topology feature cache."""
        if self._cache:
            self._cache.clear()
            logger.info("Topology feature cache cleared")
    
    def precompute_for_events(
        self,
        event_ids: List[int],
        lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    ) -> int:
        """
        Pre-compute and cache topology features for a list of events.
        
        Args:
            event_ids: List of event IDs to compute features for
            lookback_days: Days of price history
            
        Returns:
            Number of events successfully cached
        """
        from releaseradar.db.models import Event
        from sqlalchemy import select
        
        events = self.db.execute(
            select(Event).where(Event.id.in_(event_ids))
        ).scalars().all()
        
        event_data = [
            {"event_id": e.id, "ticker": e.ticker, "date": e.date}
            for e in events
        ]
        
        results = self.extract_batch(event_data, lookback_days)
        
        cached = sum(1 for v in results.values() if v.has_features)
        logger.info(f"Pre-computed {cached}/{len(results)} topology features")
        
        return cached


def get_topology_extractor(
    db: Session,
    use_cache: bool = True
) -> TopologyFeatureExtractor:
    """Factory function to create TopologyFeatureExtractor."""
    return TopologyFeatureExtractor(db=db, use_cache=use_cache)
