"""
Persistent Topology Service for Market Echo Engine.

Implements Topological Data Analysis (TDA) using persistent homology to extract
topological features from stock price time series around events.

Key Concepts:
- Takens Embedding: Converts 1D time series into higher-dimensional point cloud
- Vietoris-Rips Complex: Builds simplicial complex from point cloud
- Persistent Homology: Tracks birth/death of topological features across scales
- Betti Numbers: β₀ (connected components), β₁ (loops/cycles)

Features Extracted:
- Persistence entropy (measure of topological complexity)
- Betti curve statistics (how topology changes with scale)
- Max/mean lifetimes of features
- Total persistence (sum of all feature lifetimes)
"""

from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session

from releaseradar.log_config import logger


@dataclass
class PersistenceFeatures:
    """Topological features extracted from persistent homology."""
    betti0_count: int = 0
    betti1_count: int = 0
    max_lifetime_h0: float = 0.0
    max_lifetime_h1: float = 0.0
    mean_lifetime_h0: float = 0.0
    mean_lifetime_h1: float = 0.0
    total_persistence_h0: float = 0.0
    total_persistence_h1: float = 0.0
    persistence_entropy: float = 0.0
    betti_curve_h0_mean: float = 0.0
    betti_curve_h1_mean: float = 0.0
    topological_complexity: float = 0.0
    has_persistent_features: bool = False
    computed_at: Optional[datetime] = None
    error_message: Optional[str] = None


@dataclass
class TakensEmbedding:
    """Result of Takens delay embedding."""
    points: np.ndarray
    dimension: int
    delay: int
    original_length: int


class PersistentTopologyService:
    """
    Computes persistent homology features from stock price data.
    
    This service:
    1. Fetches price data around an event
    2. Computes log returns and standardizes
    3. Creates Takens delay embedding (maps 1D → higher-dim point cloud)
    4. Computes Vietoris-Rips persistent homology
    5. Extracts ML-ready features from persistence diagrams
    """
    
    DEFAULT_EMBEDDING_DIM = 3
    DEFAULT_DELAY = 2
    DEFAULT_LOOKBACK_DAYS = 30
    MIN_DATA_POINTS = 15
    
    def __init__(self, db: Session):
        self.db = db
        self._cache: Dict[str, PersistenceFeatures] = {}
        self._ripser_available = self._check_ripser()
    
    def _check_ripser(self) -> bool:
        """Check if ripser library is available."""
        try:
            import ripser
            return True
        except ImportError:
            logger.warning("ripser library not available - persistent homology disabled")
            return False
    
    def get_persistence_features(
        self,
        ticker: str,
        event_date: datetime,
        lookback_days: int = 30,
        embedding_dim: int = 3,
        delay: int = 2,
        use_cache: bool = True
    ) -> PersistenceFeatures:
        """
        Compute persistent homology features for a stock around an event date.
        
        Args:
            ticker: Stock ticker symbol
            event_date: Date of the event
            lookback_days: Days of price history to use
            embedding_dim: Dimension for Takens embedding (m)
            delay: Time delay for Takens embedding (τ)
            use_cache: Whether to use cached results
            
        Returns:
            PersistenceFeatures with topological statistics
        """
        cache_key = f"{ticker}_{event_date.date()}_{lookback_days}_{embedding_dim}_{delay}"
        
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]
        
        if not self._ripser_available:
            return PersistenceFeatures(
                error_message="ripser library not available",
                computed_at=datetime.utcnow()
            )
        
        try:
            returns = self._fetch_returns(ticker, event_date, lookback_days)
            
            if returns is None or len(returns) < self.MIN_DATA_POINTS:
                return PersistenceFeatures(
                    error_message=f"Insufficient data: need {self.MIN_DATA_POINTS}, got {len(returns) if returns is not None else 0}",
                    computed_at=datetime.utcnow()
                )
            
            embedding = self._create_takens_embedding(returns, embedding_dim, delay)
            
            if embedding.points.shape[0] < 5:
                return PersistenceFeatures(
                    error_message="Embedding too small for persistence computation",
                    computed_at=datetime.utcnow()
                )
            
            diagrams = self._compute_persistence(embedding.points)
            
            features = self._extract_features(diagrams)
            features.has_persistent_features = True
            features.computed_at = datetime.utcnow()
            
            if use_cache:
                self._cache[cache_key] = features
            
            return features
            
        except Exception as e:
            logger.error(f"Error computing persistence for {ticker}: {e}")
            return PersistenceFeatures(
                error_message=str(e),
                computed_at=datetime.utcnow()
            )
    
    def _fetch_returns(
        self,
        ticker: str,
        event_date: datetime,
        lookback_days: int
    ) -> Optional[np.ndarray]:
        """Fetch and compute log returns for the ticker."""
        try:
            end_date = event_date.date()
            start_date = end_date - timedelta(days=lookback_days + 10)
            
            query = text("""
                SELECT date, close
                FROM price_history
                WHERE ticker = :ticker
                AND date >= :start_date
                AND date <= :end_date
                ORDER BY date ASC
            """)
            
            result = self.db.execute(query, {
                "ticker": ticker,
                "start_date": start_date,
                "end_date": end_date
            })
            
            prices = [(row[0], float(row[1])) for row in result]
            
            if len(prices) < 2:
                return None
            
            closes = np.array([p[1] for p in prices])
            log_returns = np.diff(np.log(closes))
            
            if len(log_returns) > 0:
                log_returns = (log_returns - np.mean(log_returns)) / (np.std(log_returns) + 1e-8)
            
            return log_returns
            
        except Exception as e:
            logger.error(f"Error fetching returns for {ticker}: {e}")
            return None
    
    def _create_takens_embedding(
        self,
        time_series: np.ndarray,
        embedding_dim: int,
        delay: int
    ) -> TakensEmbedding:
        """
        Create Takens delay embedding from 1D time series.
        
        Takens' theorem: For a dynamical system, the delay embedding
        reconstructs the topology of the underlying attractor.
        
        Given time series x(t), create vectors:
        [x(t), x(t+τ), x(t+2τ), ..., x(t+(m-1)τ)]
        
        where τ = delay, m = embedding_dim
        
        Args:
            time_series: 1D array of values (e.g., returns)
            embedding_dim: Target dimension (m)
            delay: Time delay between coordinates (τ)
            
        Returns:
            TakensEmbedding with point cloud in ℝᵐ
        """
        n = len(time_series)
        n_points = n - (embedding_dim - 1) * delay
        
        if n_points < 1:
            return TakensEmbedding(
                points=np.array([]).reshape(0, embedding_dim),
                dimension=embedding_dim,
                delay=delay,
                original_length=n
            )
        
        points = np.zeros((n_points, embedding_dim))
        
        for i in range(n_points):
            for j in range(embedding_dim):
                points[i, j] = time_series[i + j * delay]
        
        return TakensEmbedding(
            points=points,
            dimension=embedding_dim,
            delay=delay,
            original_length=n
        )
    
    def _compute_persistence(self, point_cloud: np.ndarray, maxdim: int = 1) -> Dict:
        """
        Compute Vietoris-Rips persistent homology.
        
        The Vietoris-Rips complex:
        - At scale ε, connect points within distance ε
        - As ε grows, track when connected components merge (β₀ features)
        - Track when loops form and fill in (β₁ features)
        
        Returns persistence diagrams: list of (birth, death) pairs for each dimension.
        """
        import ripser
        
        result = ripser.ripser(point_cloud, maxdim=maxdim, thresh=2.0)
        
        return {
            'dgms': result['dgms'],
            'num_edges': result.get('num_edges', 0),
            'dperm2all': result.get('dperm2all', None)
        }
    
    def _extract_features(self, persistence_result: Dict) -> PersistenceFeatures:
        """
        Extract ML-ready features from persistence diagrams.
        
        Features extracted:
        1. Betti counts: Number of significant features in H₀, H₁
        2. Lifetimes: Max and mean lifetimes of features
        3. Total persistence: Sum of all lifetimes
        4. Persistence entropy: Shannon entropy of lifetime distribution
        5. Betti curve statistics: How Betti numbers evolve with scale
        6. Topological complexity: Combined measure
        """
        features = PersistenceFeatures()
        diagrams = persistence_result['dgms']
        
        h0_lifetimes = []
        if len(diagrams) > 0 and len(diagrams[0]) > 0:
            for birth, death in diagrams[0]:
                if not np.isinf(death):
                    lifetime = death - birth
                    if lifetime > 0.01:
                        h0_lifetimes.append(lifetime)
        
        h1_lifetimes = []
        if len(diagrams) > 1 and len(diagrams[1]) > 0:
            for birth, death in diagrams[1]:
                if not np.isinf(death):
                    lifetime = death - birth
                    if lifetime > 0.01:
                        h1_lifetimes.append(lifetime)
        
        features.betti0_count = len(h0_lifetimes)
        features.betti1_count = len(h1_lifetimes)
        
        if h0_lifetimes:
            features.max_lifetime_h0 = float(max(h0_lifetimes))
            features.mean_lifetime_h0 = float(np.mean(h0_lifetimes))
            features.total_persistence_h0 = float(sum(h0_lifetimes))
        
        if h1_lifetimes:
            features.max_lifetime_h1 = float(max(h1_lifetimes))
            features.mean_lifetime_h1 = float(np.mean(h1_lifetimes))
            features.total_persistence_h1 = float(sum(h1_lifetimes))
        
        all_lifetimes = h0_lifetimes + h1_lifetimes
        k = len(all_lifetimes)
        if k >= 2:
            total = sum(all_lifetimes)
            if total > 0:
                probabilities = [l / total for l in all_lifetimes]
                entropy = -sum(p * np.log(p + 1e-10) for p in probabilities)
                max_entropy = np.log(k)
                features.persistence_entropy = float(entropy / max_entropy) if max_entropy > 0 else 0.0
        elif k == 1:
            features.persistence_entropy = 0.0
        
        features.betti_curve_h0_mean = self._compute_betti_curve_mean(diagrams[0]) if len(diagrams) > 0 else 0.0
        features.betti_curve_h1_mean = self._compute_betti_curve_mean(diagrams[1]) if len(diagrams) > 1 else 0.0
        
        features.topological_complexity = (
            features.betti1_count * 2.0 +
            features.persistence_entropy +
            features.total_persistence_h1
        )
        
        return features
    
    def _compute_betti_curve_mean(self, diagram: np.ndarray, n_samples: int = 20) -> float:
        """
        Compute mean of the Betti curve.
        
        Betti curve β(ε) = number of features alive at scale ε.
        We sample at n_samples points and return the mean.
        """
        if len(diagram) == 0:
            return 0.0
        
        finite_mask = ~np.isinf(diagram[:, 1])
        if not np.any(finite_mask):
            return 0.0
        
        finite_diagram = diagram[finite_mask]
        if len(finite_diagram) == 0:
            return 0.0
        
        min_birth = np.min(finite_diagram[:, 0])
        max_death = np.max(finite_diagram[:, 1])
        
        if max_death <= min_birth:
            return 0.0
        
        scales = np.linspace(min_birth, max_death, n_samples)
        betti_values = []
        
        for scale in scales:
            count = np.sum((finite_diagram[:, 0] <= scale) & (finite_diagram[:, 1] > scale))
            betti_values.append(count)
        
        return float(np.mean(betti_values))
    
    def compare_events(
        self,
        ticker1: str,
        date1: datetime,
        ticker2: str,
        date2: datetime,
        lookback_days: int = 30
    ) -> float:
        """
        Compare topological similarity between two events.
        
        Uses bottleneck distance between persistence diagrams
        to measure how similar the price patterns are.
        
        Returns:
            Similarity score between 0 and 1 (1 = identical topology)
        """
        try:
            from persim import bottleneck
            
            returns1 = self._fetch_returns(ticker1, date1, lookback_days)
            returns2 = self._fetch_returns(ticker2, date2, lookback_days)
            
            if returns1 is None or returns2 is None:
                return 0.0
            
            if len(returns1) < self.MIN_DATA_POINTS or len(returns2) < self.MIN_DATA_POINTS:
                return 0.0
            
            emb1 = self._create_takens_embedding(returns1, self.DEFAULT_EMBEDDING_DIM, self.DEFAULT_DELAY)
            emb2 = self._create_takens_embedding(returns2, self.DEFAULT_EMBEDDING_DIM, self.DEFAULT_DELAY)
            
            if emb1.points.shape[0] < 5 or emb2.points.shape[0] < 5:
                return 0.0
            
            dgms1 = self._compute_persistence(emb1.points)['dgms']
            dgms2 = self._compute_persistence(emb2.points)['dgms']
            
            h1_dist = 0.0
            if len(dgms1) > 1 and len(dgms2) > 1:
                d1_h1 = dgms1[1][~np.isinf(dgms1[1][:, 1])] if len(dgms1[1]) > 0 else np.array([]).reshape(0, 2)
                d2_h1 = dgms2[1][~np.isinf(dgms2[1][:, 1])] if len(dgms2[1]) > 0 else np.array([]).reshape(0, 2)
                
                if len(d1_h1) > 0 and len(d2_h1) > 0:
                    h1_dist = bottleneck(d1_h1, d2_h1)
            
            similarity = np.exp(-h1_dist)
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Error comparing events: {e}")
            return 0.0
    
    def find_similar_events(
        self,
        ticker: str,
        event_date: datetime,
        candidate_tickers: List[str],
        top_k: int = 5,
        lookback_days: int = 30
    ) -> List[Tuple[str, datetime, float]]:
        """
        Find events with similar topological patterns.
        
        This could help identify similar market situations
        that led to similar outcomes.
        """
        similarities = []
        
        source_features = self.get_persistence_features(ticker, event_date, lookback_days)
        if not source_features.has_persistent_features:
            return []
        
        for cand_ticker in candidate_tickers[:50]:
            try:
                cand_features = self.get_persistence_features(cand_ticker, event_date, lookback_days)
                if not cand_features.has_persistent_features:
                    continue
                
                sim = self._feature_similarity(source_features, cand_features)
                similarities.append((cand_ticker, event_date, sim))
                
            except Exception as e:
                continue
        
        similarities.sort(key=lambda x: x[2], reverse=True)
        return similarities[:top_k]
    
    def _feature_similarity(self, f1: PersistenceFeatures, f2: PersistenceFeatures) -> float:
        """Compute similarity between two feature sets using cosine similarity."""
        v1 = np.array([
            f1.betti0_count, f1.betti1_count,
            f1.max_lifetime_h0, f1.max_lifetime_h1,
            f1.mean_lifetime_h0, f1.mean_lifetime_h1,
            f1.persistence_entropy, f1.topological_complexity
        ])
        
        v2 = np.array([
            f2.betti0_count, f2.betti1_count,
            f2.max_lifetime_h0, f2.max_lifetime_h1,
            f2.mean_lifetime_h0, f2.mean_lifetime_h1,
            f2.persistence_entropy, f2.topological_complexity
        ])
        
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 < 1e-8 or norm2 < 1e-8:
            return 0.0
        
        return float(np.dot(v1, v2) / (norm1 * norm2))


def get_persistent_topology_service(db: Session) -> PersistentTopologyService:
    """Factory function to create PersistentTopologyService."""
    return PersistentTopologyService(db)
