"""
Feature Cache for Impact Radar ML System.

Provides efficient caching of computed features with TTL-based invalidation.
Pre-computes and caches commonly used features to optimize prediction latency.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from collections import OrderedDict
import hashlib
import json
import threading

from releaseradar.ml.schemas import EventFeatures
from releaseradar.log_config import logger


@dataclass
class CacheEntry:
    """Single cache entry with TTL tracking."""
    key: str
    value: Dict[str, Any]
    created_at: datetime
    expires_at: datetime
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    feature_version: str = "v1.3"
    
    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at
    
    @property
    def age_seconds(self) -> float:
        return (datetime.utcnow() - self.created_at).total_seconds()
    
    def touch(self):
        """Update access tracking."""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()


@dataclass
class CacheStats:
    """Cache performance statistics."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expirations: int = 0
    size: int = 0
    max_size: int = 0
    
    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    def to_dict(self) -> Dict:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "expirations": self.expirations,
            "hit_rate": round(self.hit_rate, 4),
            "size": self.size,
            "max_size": self.max_size,
        }


class FeatureCache:
    """
    In-memory cache for computed features with TTL-based invalidation.
    
    Features:
    - TTL-based expiration (default 1 hour)
    - LRU eviction when max size reached
    - Pre-computation of commonly used features
    - Integration with EventFeatures schema
    - Thread-safe operations
    """
    
    DEFAULT_TTL_SECONDS = 3600  # 1 hour
    DEFAULT_MAX_SIZE = 10000  # Maximum cache entries
    
    def __init__(
        self,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        max_size: int = DEFAULT_MAX_SIZE,
        feature_version: str = "v1.3"
    ):
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self.feature_version = feature_version
        
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = CacheStats(max_size=max_size)
        
        logger.info(f"FeatureCache initialized: ttl={ttl_seconds}s, max_size={max_size}")
    
    def _generate_key(
        self,
        event_id: Optional[int] = None,
        ticker: Optional[str] = None,
        event_date: Optional[datetime] = None,
        feature_type: str = "event"
    ) -> str:
        """Generate cache key from parameters."""
        components = [feature_type, self.feature_version]
        
        if event_id:
            components.append(f"e{event_id}")
        if ticker:
            components.append(ticker)
        if event_date:
            components.append(event_date.strftime("%Y%m%d"))
        
        key_str = "_".join(components)
        return hashlib.md5(key_str.encode()).hexdigest()[:16]
    
    def get(
        self,
        event_id: Optional[int] = None,
        ticker: Optional[str] = None,
        event_date: Optional[datetime] = None,
        feature_type: str = "event"
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached features for an event.
        
        Args:
            event_id: Event ID
            ticker: Stock ticker
            event_date: Event date
            feature_type: Type of features ("event", "topology", "market")
            
        Returns:
            Cached feature dict or None if not found/expired
        """
        key = self._generate_key(event_id, ticker, event_date, feature_type)
        
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._stats.misses += 1
                return None
            
            if entry.is_expired:
                self._remove_entry(key)
                self._stats.expirations += 1
                self._stats.misses += 1
                return None
            
            entry.touch()
            self._cache.move_to_end(key)
            self._stats.hits += 1
            
            return entry.value
    
    def set(
        self,
        features: Dict[str, Any],
        event_id: Optional[int] = None,
        ticker: Optional[str] = None,
        event_date: Optional[datetime] = None,
        feature_type: str = "event",
        ttl_seconds: Optional[int] = None
    ) -> str:
        """
        Cache features for an event.
        
        Args:
            features: Feature dictionary to cache
            event_id: Event ID
            ticker: Stock ticker
            event_date: Event date
            feature_type: Type of features
            ttl_seconds: Custom TTL (uses default if not specified)
            
        Returns:
            Cache key
        """
        key = self._generate_key(event_id, ticker, event_date, feature_type)
        ttl = ttl_seconds or self.ttl_seconds
        
        with self._lock:
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_oldest()
            
            entry = CacheEntry(
                key=key,
                value=features.copy(),
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(seconds=ttl),
                feature_version=self.feature_version,
            )
            
            self._cache[key] = entry
            self._cache.move_to_end(key)
            self._stats.size = len(self._cache)
            
        return key
    
    def set_from_event_features(
        self,
        event_features: EventFeatures,
        ttl_seconds: Optional[int] = None
    ) -> str:
        """Cache from EventFeatures object."""
        return self.set(
            features=event_features.to_vector(),
            event_id=event_features.event_id,
            ticker=event_features.ticker,
            feature_type="event",
            ttl_seconds=ttl_seconds,
        )
    
    def get_or_compute(
        self,
        compute_fn,
        event_id: Optional[int] = None,
        ticker: Optional[str] = None,
        event_date: Optional[datetime] = None,
        feature_type: str = "event",
        ttl_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get from cache or compute and cache if missing.
        
        Args:
            compute_fn: Function to compute features if not cached
            event_id: Event ID
            ticker: Stock ticker
            event_date: Event date
            feature_type: Type of features
            ttl_seconds: Custom TTL
            
        Returns:
            Feature dictionary (from cache or freshly computed)
        """
        cached = self.get(event_id, ticker, event_date, feature_type)
        if cached is not None:
            return cached
        
        features = compute_fn()
        
        if isinstance(features, EventFeatures):
            features = features.to_vector()
        
        self.set(features, event_id, ticker, event_date, feature_type, ttl_seconds)
        return features
    
    def invalidate(
        self,
        event_id: Optional[int] = None,
        ticker: Optional[str] = None,
        event_date: Optional[datetime] = None,
        feature_type: str = "event"
    ) -> bool:
        """
        Invalidate a specific cache entry.
        
        Returns:
            True if entry was found and removed
        """
        key = self._generate_key(event_id, ticker, event_date, feature_type)
        
        with self._lock:
            if key in self._cache:
                self._remove_entry(key)
                return True
            return False
    
    def invalidate_ticker(self, ticker: str) -> int:
        """
        Invalidate all cache entries for a ticker.
        
        Returns:
            Number of entries invalidated
        """
        with self._lock:
            keys_to_remove = [
                key for key, entry in self._cache.items()
                if ticker in str(entry.value.get("ticker", ""))
            ]
            
            for key in keys_to_remove:
                self._remove_entry(key)
            
            return len(keys_to_remove)
    
    def invalidate_expired(self) -> int:
        """
        Remove all expired entries.
        
        Returns:
            Number of entries removed
        """
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired
            ]
            
            for key in expired_keys:
                self._remove_entry(key)
                self._stats.expirations += 1
            
            return len(expired_keys)
    
    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._stats.size = 0
    
    def _remove_entry(self, key: str):
        """Remove a cache entry."""
        if key in self._cache:
            del self._cache[key]
            self._stats.size = len(self._cache)
    
    def _evict_oldest(self):
        """Evict the oldest (least recently used) entry."""
        if self._cache:
            oldest_key = next(iter(self._cache))
            self._remove_entry(oldest_key)
            self._stats.evictions += 1
    
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        with self._lock:
            self._stats.size = len(self._cache)
            return self._stats
    
    def get_entries_by_age(self, max_age_seconds: float = 3600) -> List[CacheEntry]:
        """Get entries younger than max_age_seconds."""
        with self._lock:
            cutoff = datetime.utcnow() - timedelta(seconds=max_age_seconds)
            return [
                entry for entry in self._cache.values()
                if entry.created_at > cutoff
            ]
    
    def precompute_batch(
        self,
        compute_fn,
        items: List[Dict],
        feature_type: str = "event",
        ttl_seconds: Optional[int] = None
    ) -> int:
        """
        Pre-compute and cache features for a batch of items.
        
        Args:
            compute_fn: Function that takes item dict and returns features
            items: List of dicts with event_id, ticker, event_date
            feature_type: Type of features
            ttl_seconds: Custom TTL
            
        Returns:
            Number of items successfully cached
        """
        cached_count = 0
        
        for item in items:
            event_id = item.get("event_id")
            ticker = item.get("ticker")
            event_date = item.get("event_date")
            
            if self.get(event_id, ticker, event_date, feature_type) is not None:
                continue
            
            try:
                features = compute_fn(item)
                if isinstance(features, EventFeatures):
                    features = features.to_vector()
                
                self.set(features, event_id, ticker, event_date, feature_type, ttl_seconds)
                cached_count += 1
                
            except Exception as e:
                logger.warning(f"Failed to compute features for {item}: {e}")
        
        return cached_count
    
    def warm_cache(
        self,
        db_session,
        feature_extractor,
        lookback_hours: int = 24,
        limit: int = 500
    ) -> int:
        """
        Warm the cache with recent events.
        
        Args:
            db_session: Database session
            feature_extractor: FeatureExtractor instance
            lookback_hours: How far back to look for events
            limit: Maximum events to cache
            
        Returns:
            Number of events cached
        """
        from releaseradar.db.models import Event
        from sqlalchemy import select
        
        cutoff = datetime.utcnow() - timedelta(hours=lookback_hours)
        
        events = db_session.execute(
            select(Event)
            .where(Event.date >= cutoff)
            .order_by(Event.date.desc())
            .limit(limit)
        ).scalars().all()
        
        cached_count = 0
        
        for event in events:
            if self.get(event_id=event.id, feature_type="event") is not None:
                continue
            
            try:
                features = feature_extractor.extract_features(event.id)
                if features:
                    self.set_from_event_features(features)
                    cached_count += 1
            except Exception as e:
                logger.debug(f"Failed to cache event {event.id}: {e}")
        
        logger.info(f"Cache warmed with {cached_count} events")
        return cached_count
    
    def to_dict(self) -> Dict:
        """Export cache state to dictionary."""
        with self._lock:
            return {
                "stats": self._stats.to_dict(),
                "config": {
                    "ttl_seconds": self.ttl_seconds,
                    "max_size": self.max_size,
                    "feature_version": self.feature_version,
                },
                "entries_count": len(self._cache),
                "oldest_entry_age": max(
                    (e.age_seconds for e in self._cache.values()),
                    default=0
                ),
            }


class TopologyFeatureCache(FeatureCache):
    """
    Specialized cache for topology features.
    
    Uses longer TTL (topology features are expensive to compute)
    and supports ticker-based lookups.
    """
    
    DEFAULT_TTL_SECONDS = 7200  # 2 hours for topology
    
    def __init__(self, ttl_seconds: int = DEFAULT_TTL_SECONDS, max_size: int = 5000):
        super().__init__(ttl_seconds=ttl_seconds, max_size=max_size, feature_version="topology_v1")
    
    def get_by_ticker_date(
        self,
        ticker: str,
        event_date: datetime
    ) -> Optional[Dict[str, Any]]:
        """Get topology features by ticker and date."""
        return self.get(
            ticker=ticker,
            event_date=event_date,
            feature_type="topology"
        )
    
    def set_topology_features(
        self,
        features: Dict[str, Any],
        ticker: str,
        event_date: datetime,
        ttl_seconds: Optional[int] = None
    ) -> str:
        """Cache topology features."""
        return self.set(
            features=features,
            ticker=ticker,
            event_date=event_date,
            feature_type="topology",
            ttl_seconds=ttl_seconds,
        )
