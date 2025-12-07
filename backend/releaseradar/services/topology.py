"""
Topology Context Service for Market Echo Engine.

Provides correlation-based clustering and regime detection as ADDITIONAL features
for the existing ML models. This is purely additive - it does not replace any
existing features or scoring logic.

Features:
- Correlation clustering: Groups stocks by price correlation patterns
- Regime detection: Risk-on/risk-off market state with confidence
- Daily caching: Recalculates clusters and regime once per day
"""

from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session

from releaseradar.log_config import logger


@dataclass
class TopologyContext:
    """Topology context for a specific ticker at a point in time."""
    cluster_id: Optional[int] = None
    cluster_size: Optional[int] = None
    cluster_volatility: Optional[float] = None
    cluster_return_5d: Optional[float] = None
    cluster_avg_correlation: Optional[float] = None
    regime: Optional[str] = None  # "risk_on", "risk_off"
    regime_confidence: Optional[float] = None
    regime_volatility: Optional[float] = None
    regime_breadth: Optional[float] = None  # % of positive stocks
    calculated_at: Optional[datetime] = None


@dataclass
class MarketRegime:
    """Current market regime state."""
    regime: str  # "risk_on" or "risk_off"
    confidence: float  # 0-1
    volatility: float  # Current market volatility
    avg_correlation: float  # Average pairwise correlation
    avg_return: float  # Recent average return
    negative_breadth: float  # % of stocks negative
    scores: Dict[str, float]  # Component scores


class TopologyContextService:
    """
    Calculates topology-based context features for events.
    
    These features are ADDED to existing ML features, not replacing them.
    The service caches results daily for efficiency.
    """
    
    TICKERS = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "AMD", "INTC",
        "JPM", "BAC", "GS", "MS", "WFC", "C", "AXP", "BLK", "SCHW", "USB",
        "JNJ", "PFE", "MRK", "ABBV", "LLY", "AMGN", "GILD", "BMY", "BIIB",
        "ABT", "TMO", "DHR", "REGN", "VRTX", "MRNA", "ILMN", "INCY", "ZTS",
        "XOM", "CVX", "COP", "EOG", "SLB", "OXY", "MPC", "VLO", "PSX", "HAL",
        "HD", "LOW", "MCD", "SBUX", "NKE", "TGT", "COST", "TJX",
        "BA", "CAT", "GE", "HON", "UNP", "UPS", "LMT", "MMM", "DE", "ISRG",
        "CRM", "ADBE", "ORCL", "UNH",
    ]
    
    SECTOR_MAP = {
        "AAPL": "Technology", "MSFT": "Technology", "GOOGL": "Technology",
        "AMZN": "Consumer", "META": "Technology", "NVDA": "Technology",
        "TSLA": "Consumer", "AMD": "Technology", "INTC": "Technology",
        "JPM": "Financials", "BAC": "Financials", "GS": "Financials",
        "MS": "Financials", "WFC": "Financials", "C": "Financials",
        "AXP": "Financials", "BLK": "Financials", "SCHW": "Financials",
        "USB": "Financials",
        "JNJ": "Healthcare", "PFE": "Healthcare", "MRK": "Healthcare",
        "ABBV": "Healthcare", "LLY": "Healthcare", "AMGN": "Biotech",
        "GILD": "Biotech", "BMY": "Healthcare", "BIIB": "Biotech",
        "ABT": "Healthcare", "TMO": "Healthcare", "DHR": "Healthcare",
        "REGN": "Biotech", "VRTX": "Biotech", "MRNA": "Biotech",
        "ILMN": "Biotech", "INCY": "Biotech", "ZTS": "Biotech",
        "XOM": "Energy", "CVX": "Energy", "COP": "Energy",
        "EOG": "Energy", "SLB": "Energy", "OXY": "Energy",
        "MPC": "Energy", "VLO": "Energy", "PSX": "Energy", "HAL": "Energy",
        "HD": "Consumer", "LOW": "Consumer", "MCD": "Consumer",
        "SBUX": "Consumer", "NKE": "Consumer", "TGT": "Consumer",
        "COST": "Consumer", "TJX": "Consumer",
        "BA": "Industrials", "CAT": "Industrials", "GE": "Industrials",
        "HON": "Industrials", "UNP": "Industrials", "UPS": "Industrials",
        "LMT": "Industrials", "MMM": "Industrials", "DE": "Industrials",
        "ISRG": "Industrials",
        "CRM": "Technology", "ADBE": "Technology", "ORCL": "Technology",
        "UNH": "Healthcare",
    }
    
    def __init__(self, db: Session):
        self.db = db
        self._cache: Dict[str, any] = {}
        self._cache_date: Optional[date] = None
        self._cluster_map: Dict[str, int] = {}
        self._cluster_stats: Dict[int, Dict] = {}
        self._current_regime: Optional[MarketRegime] = None
    
    def get_topology_context(self, ticker: str, event_date: Optional[datetime] = None) -> TopologyContext:
        """
        Get topology context for a ticker.
        
        This provides ADDITIONAL context features, not replacing existing features.
        
        Args:
            ticker: Stock ticker symbol
            event_date: Date of event (defaults to today)
            
        Returns:
            TopologyContext with cluster and regime information
        """
        today = (event_date or datetime.utcnow()).date()
        
        # Refresh cache if needed
        if self._cache_date != today:
            self._refresh_cache()
        
        # Build context
        context = TopologyContext(calculated_at=datetime.utcnow())
        
        # Add cluster information if ticker is in our universe
        if ticker in self._cluster_map:
            cluster_id = self._cluster_map[ticker]
            context.cluster_id = cluster_id
            
            if cluster_id in self._cluster_stats:
                stats = self._cluster_stats[cluster_id]
                context.cluster_size = stats.get("size", 0)
                context.cluster_volatility = stats.get("volatility", None)
                context.cluster_return_5d = stats.get("return_5d", None)
                context.cluster_avg_correlation = stats.get("avg_correlation", None)
        
        # Add regime information
        if self._current_regime:
            context.regime = self._current_regime.regime
            context.regime_confidence = self._current_regime.confidence
            context.regime_volatility = self._current_regime.volatility
            context.regime_breadth = 1.0 - self._current_regime.negative_breadth
        
        return context
    
    def get_current_regime(self) -> Optional[MarketRegime]:
        """Get current market regime."""
        today = datetime.utcnow().date()
        if self._cache_date != today:
            self._refresh_cache()
        return self._current_regime
    
    def _refresh_cache(self):
        """Refresh clustering and regime detection from price data."""
        logger.info("Refreshing topology context cache...")
        
        try:
            # Fetch price data for clustering
            returns_data = self._fetch_returns_data()
            
            if returns_data is None or len(returns_data) < 20:
                logger.warning("Insufficient price data for topology analysis")
                self._cache_date = datetime.utcnow().date()
                return
            
            # Calculate correlation matrix and clusters
            self._calculate_clusters(returns_data)
            
            # Detect current market regime
            self._detect_regime(returns_data)
            
            self._cache_date = datetime.utcnow().date()
            logger.info(f"Topology cache refreshed: {len(self._cluster_map)} tickers in {len(self._cluster_stats)} clusters")
            
        except Exception as e:
            logger.error(f"Error refreshing topology cache: {e}")
            self._cache_date = datetime.utcnow().date()
    
    def _fetch_returns_data(self) -> Optional[Dict[str, List[float]]]:
        """Fetch and calculate returns from price history."""
        try:
            # Get last 60 days of price data
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=90)
            
            # Dynamically find tickers with enough data
            # First, get tickers with at least 15 records in the time period
            ticker_query = text("""
                SELECT ticker, COUNT(*) as cnt
                FROM price_history
                WHERE date >= :start_date AND date <= :end_date
                GROUP BY ticker
                HAVING COUNT(*) >= 15
                ORDER BY COUNT(*) DESC
                LIMIT 100
            """)
            
            ticker_result = self.db.execute(ticker_query, {
                "start_date": start_date,
                "end_date": end_date
            })
            available_tickers = [row[0] for row in ticker_result]
            
            if len(available_tickers) < 10:
                logger.warning(f"Only {len(available_tickers)} tickers have sufficient data for topology analysis")
                return None
            
            query = text("""
                SELECT ticker, date, close
                FROM price_history
                WHERE ticker = ANY(:tickers)
                AND date >= :start_date
                AND date <= :end_date
                ORDER BY ticker, date
            """)
            
            result = self.db.execute(query, {
                "tickers": available_tickers,
                "start_date": start_date,
                "end_date": end_date
            })
            
            # Organize by ticker
            prices_by_ticker: Dict[str, List[Tuple[date, float]]] = {}
            for row in result:
                ticker = row[0]
                price_date = row[1]
                close = float(row[2])
                
                if ticker not in prices_by_ticker:
                    prices_by_ticker[ticker] = []
                prices_by_ticker[ticker].append((price_date, close))
            
            # Calculate daily returns
            returns_by_ticker: Dict[str, List[float]] = {}
            for ticker, prices in prices_by_ticker.items():
                if len(prices) < 10:
                    continue
                    
                # Sort by date
                prices.sort(key=lambda x: x[0])
                
                # Calculate returns
                returns = []
                for i in range(1, len(prices)):
                    prev_close = prices[i-1][1]
                    curr_close = prices[i][1]
                    if prev_close > 0:
                        ret = (curr_close - prev_close) / prev_close
                        returns.append(ret)
                
                if len(returns) >= 10:
                    returns_by_ticker[ticker] = returns
            
            return returns_by_ticker
            
        except Exception as e:
            logger.error(f"Error fetching returns data: {e}")
            return None
    
    def _calculate_clusters(self, returns_data: Dict[str, List[float]]):
        """Calculate correlation clusters using spectral clustering."""
        try:
            from sklearn.cluster import SpectralClustering
            
            tickers = list(returns_data.keys())
            if len(tickers) < 10:
                logger.warning("Too few tickers for clustering")
                return
            
            # Align returns to same length
            min_len = min(len(r) for r in returns_data.values())
            aligned_returns = np.array([returns_data[t][-min_len:] for t in tickers])
            
            # Calculate correlation matrix
            corr_matrix = np.corrcoef(aligned_returns)
            corr_matrix = np.nan_to_num(corr_matrix, nan=0.0)
            
            # Convert to similarity matrix (affinity)
            affinity = (corr_matrix + 1) / 2  # Map [-1, 1] to [0, 1]
            np.fill_diagonal(affinity, 1.0)
            
            # Spectral clustering
            n_clusters = min(7, len(tickers) // 5)
            clustering = SpectralClustering(
                n_clusters=n_clusters,
                affinity='precomputed',
                assign_labels='kmeans',
                random_state=42
            )
            labels = clustering.fit_predict(affinity)
            
            # Build cluster map
            self._cluster_map = {tickers[i]: int(labels[i]) for i in range(len(tickers))}
            
            # Calculate cluster statistics
            self._cluster_stats = {}
            for cluster_id in range(n_clusters):
                cluster_tickers = [t for t, c in self._cluster_map.items() if c == cluster_id]
                if not cluster_tickers:
                    continue
                
                # Get indices
                indices = [tickers.index(t) for t in cluster_tickers]
                
                # Cluster volatility (average of member volatilities)
                cluster_returns = aligned_returns[indices]
                volatilities = [np.std(cluster_returns[i]) for i in range(len(indices))]
                avg_volatility = np.mean(volatilities)
                
                # Cluster 5-day return
                recent_returns = [np.sum(cluster_returns[i, -5:]) for i in range(len(indices))]
                avg_return_5d = np.mean(recent_returns)
                
                # Intra-cluster correlation
                if len(indices) > 1:
                    cluster_corr = corr_matrix[np.ix_(indices, indices)]
                    avg_corr = (cluster_corr.sum() - len(indices)) / (len(indices) * (len(indices) - 1))
                else:
                    avg_corr = 1.0
                
                self._cluster_stats[cluster_id] = {
                    "size": len(cluster_tickers),
                    "tickers": cluster_tickers,
                    "volatility": float(avg_volatility),
                    "return_5d": float(avg_return_5d),
                    "avg_correlation": float(avg_corr)
                }
            
            logger.info(f"Created {n_clusters} clusters from {len(tickers)} tickers")
            
        except ImportError:
            logger.warning("scikit-learn not available for clustering")
        except Exception as e:
            logger.error(f"Error in clustering: {e}")
    
    def _detect_regime(self, returns_data: Dict[str, List[float]]):
        """Detect current market regime."""
        try:
            tickers = list(returns_data.keys())
            if len(tickers) < 10:
                return
            
            # Align returns
            min_len = min(len(r) for r in returns_data.values())
            aligned_returns = np.array([returns_data[t][-min_len:] for t in tickers])
            
            # Recent returns (last 5 days)
            recent_window = min(5, min_len)
            recent_returns = aligned_returns[:, -recent_window:]
            
            # Calculate regime indicators
            # 1. Market volatility (average stock volatility)
            volatility = np.mean([np.std(aligned_returns[i]) for i in range(len(tickers))])
            
            # 2. Average correlation
            corr_matrix = np.corrcoef(aligned_returns)
            corr_matrix = np.nan_to_num(corr_matrix, nan=0.0)
            upper_tri = corr_matrix[np.triu_indices_from(corr_matrix, k=1)]
            avg_correlation = np.mean(upper_tri)
            
            # 3. Average recent return
            avg_return = np.mean(recent_returns)
            
            # 4. Breadth (% of stocks with negative recent return)
            stock_recent_returns = np.sum(recent_returns, axis=1)
            negative_breadth = np.mean(stock_recent_returns < 0)
            
            # Score components
            scores = {
                "risk_on": 0.0,
                "risk_off": 0.0,
                "high_volatility": 0.0,
                "low_volatility": 0.0,
                "trend_up": 0.0,
                "trend_down": 0.0,
                "correlated": 0.0,
                "dispersed": 0.0,
            }
            
            # Volatility scoring
            if volatility < 0.015:
                scores["low_volatility"] = 1.0
            elif volatility > 0.025:
                scores["high_volatility"] = 1.0
            
            # Trend scoring
            if avg_return > 0.002:
                scores["trend_up"] = 1.0
            elif avg_return < -0.002:
                scores["trend_down"] = 1.0
            
            # Correlation scoring
            if avg_correlation > 0.4:
                scores["correlated"] = 1.0
            elif avg_correlation < 0.2:
                scores["dispersed"] = 1.0
            
            # Breadth scoring
            if negative_breadth < 0.4:
                scores["risk_on"] = 1.0
            elif negative_breadth > 0.6:
                scores["risk_off"] = 1.0
            
            # Determine regime
            risk_on_score = (
                scores["low_volatility"] * 0.3 +
                scores["trend_up"] * 0.3 +
                scores["dispersed"] * 0.2 +
                scores["risk_on"] * 0.2
            )
            
            risk_off_score = (
                scores["high_volatility"] * 0.3 +
                scores["trend_down"] * 0.3 +
                scores["correlated"] * 0.2 +
                scores["risk_off"] * 0.2
            )
            
            if risk_on_score > risk_off_score:
                regime = "risk_on"
                confidence = min(1.0, risk_on_score / (risk_on_score + risk_off_score + 0.001))
            else:
                regime = "risk_off"
                confidence = min(1.0, risk_off_score / (risk_on_score + risk_off_score + 0.001))
            
            self._current_regime = MarketRegime(
                regime=regime,
                confidence=confidence,
                volatility=float(volatility),
                avg_correlation=float(avg_correlation),
                avg_return=float(avg_return),
                negative_breadth=float(negative_breadth),
                scores=scores
            )
            
            logger.info(f"Market regime: {regime} (confidence: {confidence:.1%})")
            
        except Exception as e:
            logger.error(f"Error detecting regime: {e}")


def get_topology_service(db: Session) -> TopologyContextService:
    """Factory function to create TopologyContextService."""
    return TopologyContextService(db)
