"""
Feature engineering pipeline for ML models.

Extracts features from events, scores, market data, and historical statistics.
"""

from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from releaseradar.db.models import Event, EventScore, EventStats, PriceHistory
from releaseradar.ml.schemas import EventFeatures
from releaseradar.log_config import logger


SECTOR_ETFS = {
    "Healthcare": "XLV",
    "Technology": "XLK",
    "Finance": "XLF",
    "Energy": "XLE",
    "Consumer": "XLY",
    "Industrial": "XLI",
    "Materials": "XLB",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Communication": "XLC",
}


class MarketRegimeDetector:
    """Detects market regime based on trend and volatility indicators."""
    
    @staticmethod
    def detect_regime(
        spy_return_20d: float,
        spy_return_5d: float,
        market_vol: float,
        vol_percentile: float
    ) -> tuple:
        """
        Detect current market regime.
        
        Returns:
            Tuple of (regime_name, regime_strength)
            Regime names: "bull", "bear", "neutral", "high_vol"
        """
        # High volatility regime takes precedence
        if vol_percentile > 80 or market_vol > 0.025:
            return ("high_vol", min(1.0, (vol_percentile - 50) / 50))
        
        # Bull market: strong uptrend
        if spy_return_20d > 0.03 and spy_return_5d > 0:
            strength = min(1.0, spy_return_20d / 0.10)
            return ("bull", strength)
        
        # Bear market: strong downtrend
        if spy_return_20d < -0.03 and spy_return_5d < 0:
            strength = min(1.0, abs(spy_return_20d) / 0.10)
            return ("bear", strength)
        
        # Neutral: ranging market
        return ("neutral", 0.5)


class FeatureExtractor:
    """Extracts ML features from events and context."""
    
    FEATURE_VERSION = "v1.4"  # Updated for options-implied volatility features
    
    def __init__(self, db: Session):
        self.db = db
    
    def extract_features(self, event_id: int) -> Optional[EventFeatures]:
        """
        Extract complete feature vector for an event.
        
        Args:
            event_id: Event ID to extract features for
            
        Returns:
            EventFeatures object or None if event not found
        """
        # Fetch event
        event = self.db.execute(
            select(Event).where(Event.id == event_id)
        ).scalar_one_or_none()
        
        if not event:
            logger.warning(f"Event {event_id} not found")
            return None
        
        # Fetch event score
        score = self.db.execute(
            select(EventScore).where(EventScore.event_id == event_id)
        ).scalar_one_or_none()
        
        # Extract base features
        features = EventFeatures(
            event_id=event.id,
            ticker=event.ticker,
            event_type=event.event_type,
            base_score=score.base_score if score else event.impact_score,
            context_score=score.context_score if score else None,
            confidence=score.confidence / 100.0 if score else event.confidence,
            sector=event.sector,
            info_tier=event.info_tier,
        )
        
        # Add timing features
        features.hour_of_day = event.date.hour
        features.day_of_week = event.date.weekday()
        features.after_hours = event.date.hour < 9 or event.date.hour >= 16
        
        # Add probabilistic features if available
        if event.impact_p_move is not None:
            features.impact_p_move = event.impact_p_move
            features.impact_p_up = event.impact_p_up
            features.impact_p_down = event.impact_p_down
        
        # Add factor contributions if available
        if score:
            features.factor_sector = score.factor_sector
            features.factor_volatility = score.factor_volatility
            features.factor_earnings_proximity = score.factor_earnings_proximity
            features.factor_market_mood = score.factor_market_mood
        
        # Add market context features
        features = self._add_market_features(features, event)
        
        # Add historical features
        features = self._add_historical_features(features, event)
        
        # Add contrarian pattern features (Market Echo Engine learning)
        features = self._add_contrarian_features(features, event)
        
        # Add topology features (v1.2) - ADDITIVE to existing features
        features = self._add_topology_features(features, event)
        
        # Add persistent homology features (v1.3) - Topological Data Analysis
        features = self._add_persistent_features(features, event)
        
        # Add options-implied volatility features (v1.4) - Market expectations
        features = self._add_options_features(features, event)
        
        return features
    
    def _add_market_features(self, features: EventFeatures, event: Event) -> EventFeatures:
        """Add market volatility, SPY returns, market regime indicators, and v1.1 enhanced features."""
        import statistics
        has_market_data = False
        
        try:
            # Get extended SPY price history for regime detection and vol percentile
            spy_prices = self.db.execute(
                select(PriceHistory)
                .where(PriceHistory.ticker == "SPY")
                .where(PriceHistory.date <= event.date.date())
                .order_by(PriceHistory.date.desc())
                .limit(252)  # Get 1 year for percentile calculations
            ).scalars().all()
            
            if spy_prices and len(spy_prices) >= 2:
                has_market_data = True
                
                # Calculate SPY 1-day return
                if len(spy_prices) >= 2:
                    features.spy_return_1d = (
                        (spy_prices[0].close - spy_prices[1].close) / spy_prices[1].close
                    )
                
                # Calculate SPY returns
                if len(spy_prices) >= 5:
                    features.spy_returns_5d = (
                        (spy_prices[0].close - spy_prices[4].close) / spy_prices[4].close
                    )
                
                if len(spy_prices) >= 20:
                    features.spy_returns_20d = (
                        (spy_prices[0].close - spy_prices[19].close) / spy_prices[19].close
                    )
                    features.trend_20d = features.spy_returns_20d
                
                # Calculate market volatility (std dev of returns) at multiple windows
                all_returns = [
                    (spy_prices[i].close - spy_prices[i+1].close) / spy_prices[i+1].close
                    for i in range(min(len(spy_prices) - 1, 90))
                ]
                
                if len(all_returns) >= 20:
                    features.market_vol = statistics.stdev(all_returns[:20])
                    features.market_vol_20d = features.market_vol
                    
                    # VIX proxy - annualized volatility
                    features.vix_level = features.market_vol * 100 * (252 ** 0.5)
                    
                    # Calculate vol percentile over 1 year
                    if len(spy_prices) >= 252:
                        rolling_vols = []
                        for j in range(0, min(len(spy_prices) - 21, 252), 5):  # Every 5 days
                            window_returns = [
                                (spy_prices[i].close - spy_prices[i+1].close) / spy_prices[i+1].close
                                for i in range(j, j + 20)
                            ]
                            if len(window_returns) >= 10:
                                rolling_vols.append(statistics.stdev(window_returns))
                        
                        if rolling_vols:
                            current_vol = features.market_vol
                            below_count = sum(1 for v in rolling_vols if v < current_vol)
                            features.vix_percentile_252d = (below_count / len(rolling_vols)) * 100
                
                # Calculate trend strength (simplified ADX proxy)
                if len(spy_prices) >= 20 and features.spy_returns_20d is not None:
                    # Use absolute return as trend strength indicator
                    features.trend_strength_20d = abs(features.spy_returns_20d) * 10
                
                # Detect market regime
                regime, strength = MarketRegimeDetector.detect_regime(
                    spy_return_20d=features.spy_returns_20d or 0.0,
                    spy_return_5d=features.spy_returns_5d or 0.0,
                    market_vol=features.market_vol or 0.02,
                    vol_percentile=features.vix_percentile_252d or 50.0
                )
                features.market_regime = regime
                features.regime_strength = strength
                
            else:
                # Use default values
                logger.debug(f"No SPY price history found for event {event.id}, using default market features")
                features.spy_return_1d = 0.0
                features.spy_returns_5d = 0.0
                features.spy_returns_20d = 0.0
                features.market_vol = 0.02
                features.market_vol_20d = 0.02
                features.trend_20d = 0.0
                features.vix_level = 20.0
                features.vix_percentile_252d = 50.0
                features.trend_strength_20d = 0.0
                features.market_regime = "neutral"
                features.regime_strength = 0.5
            
            # Add pre-event stock context features with volatility term structure
            stock_prices = self.db.execute(
                select(PriceHistory)
                .where(PriceHistory.ticker == event.ticker)
                .where(PriceHistory.date <= event.date.date())
                .order_by(PriceHistory.date.desc())
                .limit(90)  # Get 90 days for vol percentile
            ).scalars().all()
            
            if stock_prices and len(stock_prices) >= 20:
                # Calculate pre-event stock trend (20-day return)
                features.stock_trend_pre_event = (
                    (stock_prices[0].close - stock_prices[19].close) / stock_prices[19].close
                )
                
                # Calculate volatility term structure
                stock_returns = [
                    (stock_prices[i].close - stock_prices[i+1].close) / stock_prices[i+1].close
                    for i in range(min(len(stock_prices) - 1, 20))
                ]
                
                if len(stock_returns) >= 5:
                    features.vol_5d = statistics.stdev(stock_returns[:5]) if len(stock_returns) >= 5 else 0.02
                    features.vol_10d = statistics.stdev(stock_returns[:10]) if len(stock_returns) >= 10 else features.vol_5d
                    features.vol_20d = statistics.stdev(stock_returns[:20]) if len(stock_returns) >= 20 else features.vol_10d
                    features.stock_vol_pre_event = features.vol_20d
                    
                    # Vol ratio (short/long) - mean reversion signal
                    if features.vol_20d and features.vol_20d > 0:
                        features.vol_ratio_5_20 = features.vol_5d / features.vol_20d
                    else:
                        features.vol_ratio_5_20 = 1.0
                    
                    # Vol percentile over 90 days
                    if len(stock_prices) >= 90:
                        rolling_vols = []
                        for j in range(0, len(stock_prices) - 21, 5):
                            window_returns = [
                                (stock_prices[i].close - stock_prices[i+1].close) / stock_prices[i+1].close
                                for i in range(j, min(j + 20, len(stock_prices) - 1))
                            ]
                            if len(window_returns) >= 10:
                                rolling_vols.append(statistics.stdev(window_returns))
                        
                        if rolling_vols and features.vol_20d:
                            below_count = sum(1 for v in rolling_vols if v < features.vol_20d)
                            features.vol_percentile_90d = (below_count / len(rolling_vols)) * 100
                else:
                    features.vol_5d = 0.02
                    features.vol_10d = 0.02
                    features.vol_20d = 0.02
                    features.vol_ratio_5_20 = 1.0
                    features.vol_percentile_90d = 50.0
                    features.stock_vol_pre_event = 0.02
            else:
                logger.debug(f"No stock price history for {event.ticker}, using default pre-event features")
                features.stock_trend_pre_event = 0.0
                features.stock_vol_pre_event = 0.02
                features.vol_5d = 0.02
                features.vol_10d = 0.02
                features.vol_20d = 0.02
                features.vol_ratio_5_20 = 1.0
                features.vol_percentile_90d = 50.0
            
            # Add sector momentum features
            features = self._add_sector_momentum_features(features, event, spy_prices)
        
        except Exception as e:
            logger.warning(f"Failed to fetch market features for event {event.id}: {e}")
            # Set default values
            features.spy_return_1d = 0.0
            features.spy_returns_5d = 0.0
            features.spy_returns_20d = 0.0
            features.market_vol = 0.02
            features.market_vol_20d = 0.02
            features.trend_20d = 0.0
            features.stock_trend_pre_event = 0.0
            features.stock_vol_pre_event = 0.02
            features.vol_5d = 0.02
            features.vol_10d = 0.02
            features.vol_20d = 0.02
            features.vol_ratio_5_20 = 1.0
            features.vol_percentile_90d = 50.0
            features.vix_level = 20.0
            features.vix_percentile_252d = 50.0
            features.trend_strength_20d = 0.0
            features.market_regime = "neutral"
            features.regime_strength = 0.5
        
        features.has_market_data = has_market_data
        
        return features
    
    def _add_sector_momentum_features(
        self, 
        features: EventFeatures, 
        event: Event,
        spy_prices: list
    ) -> EventFeatures:
        """Add sector momentum features comparing sector ETF to SPY."""
        import statistics
        
        try:
            # Get sector ETF ticker
            sector_etf = SECTOR_ETFS.get(event.sector, "SPY")
            
            # Get sector ETF prices
            sector_prices = self.db.execute(
                select(PriceHistory)
                .where(PriceHistory.ticker == sector_etf)
                .where(PriceHistory.date <= event.date.date())
                .order_by(PriceHistory.date.desc())
                .limit(21)
            ).scalars().all()
            
            if sector_prices and len(sector_prices) >= 5:
                # Calculate sector returns
                if len(sector_prices) >= 5:
                    features.sector_return_5d = (
                        (sector_prices[0].close - sector_prices[4].close) / sector_prices[4].close
                    )
                
                if len(sector_prices) >= 20:
                    features.sector_return_20d = (
                        (sector_prices[0].close - sector_prices[19].close) / sector_prices[19].close
                    )
                
                # Calculate relative strength vs SPY
                if spy_prices and len(spy_prices) >= 20 and features.sector_return_20d is not None:
                    spy_return_20d = features.spy_returns_20d or 0.0
                    features.sector_relative_strength = features.sector_return_20d - spy_return_20d
                
                # Calculate sector momentum z-score
                sector_returns = [
                    (sector_prices[i].close - sector_prices[i+1].close) / sector_prices[i+1].close
                    for i in range(min(len(sector_prices) - 1, 20))
                ]
                
                if len(sector_returns) >= 10:
                    mean_return = statistics.mean(sector_returns)
                    std_return = statistics.stdev(sector_returns) if len(sector_returns) > 1 else 0.01
                    if std_return > 0:
                        features.sector_momentum_zscore = mean_return / std_return
                    else:
                        features.sector_momentum_zscore = 0.0
            else:
                # Default values
                features.sector_return_5d = 0.0
                features.sector_return_20d = 0.0
                features.sector_relative_strength = 0.0
                features.sector_momentum_zscore = 0.0
        
        except Exception as e:
            logger.debug(f"Failed to fetch sector momentum for {event.sector}: {e}")
            features.sector_return_5d = 0.0
            features.sector_return_20d = 0.0
            features.sector_relative_strength = 0.0
            features.sector_momentum_zscore = 0.0
        
        return features
    
    def _add_historical_features(self, features: EventFeatures, event: Event) -> EventFeatures:
        """Add historical statistics for ticker and event type."""
        has_event_stats = False
        has_price_history = False
        
        try:
            # Count similar events for this ticker
            ticker_count = self.db.execute(
                select(Event)
                .where(Event.ticker == event.ticker)
                .where(Event.event_type == event.event_type)
                .where(Event.date < event.date)
            ).scalars().all()
            
            features.ticker_event_count = len(ticker_count)
            
            # Check if we have price history for this ticker
            price_check = self.db.execute(
                select(PriceHistory)
                .where(PriceHistory.ticker == event.ticker)
                .limit(1)
            ).scalar_one_or_none()
            
            has_price_history = price_check is not None
            
            # Get sector average impact
            if event.sector:
                sector_stats = self.db.execute(
                    select(EventStats)
                    .where(EventStats.ticker.in_(
                        select(Event.ticker).where(Event.sector == event.sector).distinct()
                    ))
                ).scalars().all()
                
                if sector_stats:
                    has_event_stats = True
                    avg_impact = sum(s.avg_abs_move_1d or 0 for s in sector_stats) / len(sector_stats)
                    features.sector_avg_impact = avg_impact
                else:
                    logger.warning(f"No EventStats found for sector {event.sector}, using default")
                    features.sector_avg_impact = 2.0  # Default ~2% impact
            
            # Get event type average impact
            event_type_stats = self.db.execute(
                select(EventStats)
                .where(EventStats.event_type == event.event_type)
            ).scalars().all()
            
            if event_type_stats:
                has_event_stats = True
                avg_impact = sum(s.avg_abs_move_1d or 0 for s in event_type_stats) / len(event_type_stats)
                features.event_type_avg_impact = avg_impact
            else:
                logger.warning(f"No EventStats found for event_type {event.event_type}, using default")
                features.event_type_avg_impact = 2.0  # Default ~2% impact
            
            # Get ticker-specific EventStats if available
            ticker_stats = self.db.execute(
                select(EventStats)
                .where(EventStats.ticker == event.ticker)
                .where(EventStats.event_type == event.event_type)
            ).scalar_one_or_none()
            
            if ticker_stats:
                has_event_stats = True
                # Override with more specific data
                features.event_type_avg_impact = ticker_stats.avg_abs_move_1d or features.event_type_avg_impact
        
        except Exception as e:
            logger.warning(f"Failed to fetch historical features for event {event.id}: {e}")
            # Set default values
            features.ticker_event_count = 0
            features.sector_avg_impact = 2.0
            features.event_type_avg_impact = 2.0
        
        features.has_event_stats = has_event_stats
        features.has_price_history = has_price_history
        
        return features
    
    def _add_contrarian_features(self, features: EventFeatures, event: Event) -> EventFeatures:
        """
        Add contrarian pattern features from Market Echo Engine learning.
        
        These features capture historical patterns where similar events led to
        price declines despite positive/neutral predictions, enabling the ML model
        to learn "hidden bearish" signals.
        """
        has_contrarian_history = False
        
        try:
            from releaseradar.db.models import EventOutcome
            from sqlalchemy import func, and_
            
            # Query contrarian outcomes for this ticker + event_type combination
            # (events where direction was positive/neutral but stock declined)
            total_outcomes = self.db.execute(
                select(func.count(EventOutcome.id))
                .join(Event, EventOutcome.event_id == Event.id)
                .where(EventOutcome.horizon == "1d")
                .where(Event.ticker == event.ticker)
                .where(Event.event_type == event.event_type)
                .where(Event.direction.in_(["positive", "neutral"]))
                .where(Event.date < event.date)  # Only consider prior events
            ).scalar() or 0
            
            if total_outcomes >= 2:  # Need at least 2 samples for a pattern
                has_contrarian_history = True
                
                # Count contrarian events (predicted positive/neutral but went down)
                contrarian_count = self.db.execute(
                    select(func.count(EventOutcome.id))
                    .join(Event, EventOutcome.event_id == Event.id)
                    .where(EventOutcome.horizon == "1d")
                    .where(Event.ticker == event.ticker)
                    .where(Event.event_type == event.event_type)
                    .where(Event.direction.in_(["positive", "neutral"]))
                    .where(EventOutcome.return_pct < -1.0)  # Declined > 1%
                    .where(Event.date < event.date)
                ).scalar() or 0
                
                # Calculate contrarian rate
                contrarian_rate = contrarian_count / total_outcomes if total_outcomes > 0 else 0.0
                features.contrarian_rate = contrarian_rate
                features.hidden_bearish_prob = contrarian_rate  # Probability of hidden bearish
                features.contrarian_sample_size = total_outcomes
                
                # Get average decline in contrarian cases
                if contrarian_count > 0:
                    avg_contrarian_return = self.db.execute(
                        select(func.avg(EventOutcome.return_pct))
                        .join(Event, EventOutcome.event_id == Event.id)
                        .where(EventOutcome.horizon == "1d")
                        .where(Event.ticker == event.ticker)
                        .where(Event.event_type == event.event_type)
                        .where(Event.direction.in_(["positive", "neutral"]))
                        .where(EventOutcome.return_pct < -1.0)
                        .where(Event.date < event.date)
                    ).scalar()
                    features.avg_contrarian_return = avg_contrarian_return or 0.0
                else:
                    features.avg_contrarian_return = 0.0
            else:
                # Not enough samples - use defaults
                features.contrarian_rate = 0.0
                features.hidden_bearish_prob = 0.0
                features.avg_contrarian_return = 0.0
                features.contrarian_sample_size = total_outcomes
        
        except Exception as e:
            logger.warning(f"Failed to fetch contrarian features for event {event.id}: {e}")
            features.contrarian_rate = 0.0
            features.hidden_bearish_prob = 0.0
            features.avg_contrarian_return = 0.0
            features.contrarian_sample_size = 0
        
        features.has_contrarian_history = has_contrarian_history
        
        return features
    
    def _add_topology_features(self, features: EventFeatures, event: Event) -> EventFeatures:
        """
        Add topology-based features (v1.2) - ADDITIVE to existing features.
        
        These features provide correlation clustering context and regime detection
        to enhance the existing ML feature set.
        """
        has_topology_context = False
        
        try:
            from releaseradar.services.topology import TopologyContextService
            
            topology_service = TopologyContextService(self.db)
            context = topology_service.get_topology_context(event.ticker, event.date)
            
            if context:
                # Cluster features
                if context.cluster_id is not None:
                    has_topology_context = True
                    features.topology_cluster_id = context.cluster_id
                    features.topology_cluster_size = context.cluster_size
                    features.topology_cluster_volatility = context.cluster_volatility
                    features.topology_cluster_return_5d = context.cluster_return_5d
                    features.topology_cluster_correlation = context.cluster_avg_correlation
                
                # Regime features
                if context.regime:
                    has_topology_context = True
                    features.topology_regime = context.regime
                    features.topology_regime_confidence = context.regime_confidence
                    features.topology_regime_volatility = context.regime_volatility
                    features.topology_regime_breadth = context.regime_breadth
        
        except Exception as e:
            logger.debug(f"Could not add topology features for event {event.id}: {e}")
        
        features.has_topology_context = has_topology_context
        
        return features
    
    def _add_persistent_features(self, features: EventFeatures, event: Event) -> EventFeatures:
        """
        Add persistent homology features (v1.3) - Topological Data Analysis.
        
        Uses Takens delay embedding to convert price time series into a point cloud,
        then computes Vietoris-Rips persistent homology to extract topological features
        that capture the "shape" of price patterns.
        
        Mathematical concepts:
        - Takens embedding: Maps 1D time series → higher-dimensional manifold
        - Persistent homology: Tracks birth/death of topological features
        - Betti numbers: β₀ = connected components, β₁ = loops/cycles
        """
        has_persistent_features = False
        
        try:
            from releaseradar.services.persistent_topology import PersistentTopologyService
            
            persistent_service = PersistentTopologyService(self.db)
            persistence = persistent_service.get_persistence_features(
                ticker=event.ticker,
                event_date=event.date,
                lookback_days=30,
                embedding_dim=3,
                delay=2
            )
            
            if persistence and persistence.has_persistent_features:
                has_persistent_features = True
                
                # Betti number counts
                features.persistent_betti0_count = persistence.betti0_count
                features.persistent_betti1_count = persistence.betti1_count
                
                # Lifetime statistics
                features.persistent_max_lifetime_h0 = persistence.max_lifetime_h0
                features.persistent_max_lifetime_h1 = persistence.max_lifetime_h1
                features.persistent_mean_lifetime_h0 = persistence.mean_lifetime_h0
                features.persistent_mean_lifetime_h1 = persistence.mean_lifetime_h1
                
                # Total persistence
                features.persistent_total_h0 = persistence.total_persistence_h0
                features.persistent_total_h1 = persistence.total_persistence_h1
                
                # Complexity measures
                features.persistent_entropy = persistence.persistence_entropy
                features.persistent_complexity = persistence.topological_complexity
        
        except Exception as e:
            logger.debug(f"Could not add persistent features for event {event.id}: {e}")
        
        features.has_persistent_features = has_persistent_features
        
        return features
    
    def _add_options_features(self, features: EventFeatures, event: Event) -> EventFeatures:
        """
        Add options-implied volatility features (v1.4) - Market expectations.
        
        Fetches ATM implied volatility, IV percentile, and put/call ratio
        from options market data to enrich features with market expectations.
        """
        has_options_data = False
        
        try:
            from releaseradar.services.options_data import get_options_service
            
            options_service = get_options_service()
            options_data = options_service.get_options_data(event.ticker)
            
            if options_data and options_data.has_options_data:
                has_options_data = True
                
                features.implied_volatility_atm = options_data.implied_volatility_atm
                features.iv_percentile_30d = options_data.iv_percentile_30d
                features.put_call_ratio = options_data.put_call_ratio
                features.iv_skew = options_data.iv_skew
        
        except Exception as e:
            logger.debug(f"Could not add options features for event {event.id} ({event.ticker}): {e}")
        
        features.has_options_data = has_options_data
        
        return features
    
    def extract_batch(self, event_ids: List[int]) -> List[EventFeatures]:
        """
        Extract features for multiple events.
        
        Args:
            event_ids: List of event IDs
            
        Returns:
            List of EventFeatures objects
        """
        features = []
        for event_id in event_ids:
            feature = self.extract_features(event_id)
            if feature:
                features.append(feature)
        
        return features
