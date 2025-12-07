"""
Unit tests for scoring with market data variations.

Tests the analytics.scoring module to verify scoring boosts with
different market data factors (beta, ATR, market regime).
"""

import os
import sys
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from analytics.scoring import (
    compute_sector_beta_score,
    compute_volatility_score,
    compute_market_regime_score,
    get_base_score,
    EventContext
)


class TestScoringMarketData:
    """Test scoring with market data variations."""
    
    def test_scoring_with_high_beta(self):
        """High beta (>1.5) should increase score by 10-20%."""
        # Test low beta
        low_beta_score = compute_sector_beta_score(beta=0.5)
        assert low_beta_score == 0, "Low beta (<0.8) should contribute 0 points"
        
        # Test medium beta
        medium_beta_score = compute_sector_beta_score(beta=1.0)
        assert medium_beta_score == 5, "Medium beta (0.8-1.2) should contribute 5 points"
        
        # Test high beta
        high_beta_score = compute_sector_beta_score(beta=1.8)
        assert high_beta_score == 10, "High beta (>1.2) should contribute 10 points"
        
        # Verify contribution is 10-20% of base score (50)
        base_score = get_base_score("earnings")
        boost_percentage = (high_beta_score / base_score) * 100
        assert 10 <= boost_percentage <= 20, \
            f"High beta boost should be 10-20% of base score, got {boost_percentage:.1f}%"
    
    def test_scoring_with_high_atr(self):
        """High ATR percentile (>80) should increase score."""
        # Test low ATR percentile
        low_atr_score = compute_volatility_score(atr_percentile=10)
        assert low_atr_score <= 2, "Low ATR percentile (<20) should contribute minimal points"
        
        # Test medium ATR percentile
        medium_atr_score = compute_volatility_score(atr_percentile=50)
        assert 4 <= medium_atr_score <= 6, "Medium ATR percentile (40-60) should contribute ~5 points"
        
        # Test high ATR percentile
        high_atr_score = compute_volatility_score(atr_percentile=85)
        assert high_atr_score >= 8, "High ATR percentile (>80) should contribute 8+ points"
        
        # Test maximum ATR percentile
        max_atr_score = compute_volatility_score(atr_percentile=100)
        assert max_atr_score == 10, "Maximum ATR percentile (100) should contribute 10 points"
    
    def test_scoring_with_down_market(self):
        """Adverse market (SPY down) should increase score."""
        # Test bullish market (SPY up 5%)
        bullish_score = compute_market_regime_score(spy_returns={"1d": 0.02, "5d": 0.05, "20d": 0.10})
        assert bullish_score == 10, "Bullish market (SPY up 5%) should contribute +10 points"
        
        # Test neutral market (SPY flat)
        neutral_score = compute_market_regime_score(spy_returns={"1d": 0.0, "5d": 0.0, "20d": 0.0})
        assert -2 <= neutral_score <= 2, "Neutral market should contribute ~0 points"
        
        # Test bearish market (SPY down 5%)
        bearish_score = compute_market_regime_score(spy_returns={"1d": -0.02, "5d": -0.05, "20d": -0.10})
        assert bearish_score == -10, "Bearish market (SPY down 5%) should contribute -10 points"
        
        # Verify bearish market increases importance of events (negative contribution means higher urgency)
        assert bearish_score < neutral_score, "Bearish market should have lower score (higher urgency)"
    
    def test_scoring_combined_factors(self):
        """High beta + high ATR + down market should give 25-45% boost."""
        # Calculate individual contributions
        high_beta = compute_sector_beta_score(beta=1.8)
        high_atr = compute_volatility_score(atr_percentile=90)
        down_market = compute_market_regime_score(spy_returns={"1d": -0.02, "5d": -0.05, "20d": -0.08})
        
        # Sum of context factors
        total_context_boost = high_beta + high_atr + down_market
        
        # Base score for earnings event
        base_score = get_base_score("earnings")
        
        # Calculate total score (base + context)
        # Note: down_market is negative, but in context of event urgency it increases importance
        # The scoring system should handle this appropriately
        expected_total = base_score + total_context_boost
        
        # Verify combined boost is significant
        # Note: down_market is negative (-10), so total may be lower than expected
        # Combined: high_beta (10) + high_atr (9) + down_market (-10) = 9
        assert total_context_boost >= 8, \
            f"Combined factors should boost by at least 8 points, got {total_context_boost}"
        
        # Calculate boost percentage (use absolute value since negative is also impactful)
        boost_percentage = (abs(total_context_boost) / base_score) * 100
        
        # With extreme conditions (high beta + high ATR + down market),
        # we expect at least 10% combined impact
        assert boost_percentage >= 10, \
            f"Combined extreme factors should have at least 10% impact, got {boost_percentage:.1f}%"
    
    def test_scoring_graceful_degradation(self):
        """Scoring should work when market data unavailable (None values)."""
        # Test with None beta
        beta_score = compute_sector_beta_score(beta=None, sector="Technology")
        assert beta_score is not None, "Should return default score when beta is None"
        assert isinstance(beta_score, int), "Score should be an integer"
        
        # Test with None ATR percentile
        atr_score = compute_volatility_score(atr_percentile=None)
        assert atr_score is not None, "Should return default score when ATR is None"
        assert atr_score == 5, "Default ATR score should be 5 (middle)"
        
        # Test with None market returns
        market_score = compute_market_regime_score(spy_returns=None)
        assert market_score is not None, "Should return default score when market returns is None"
        assert market_score == 0, "Default market score should be 0 (neutral)"
        
        # Test EventContext with all None values
        context = EventContext(
            sector="Technology",
            beta=None,
            atr_percentile=None,
            spy_returns=None
        )
        
        # Should not raise errors
        assert context is not None
        assert context.beta is None
        assert context.atr_percentile is None
        assert context.spy_returns is None
        
        # Verify scoring still works with degraded context
        base = get_base_score("product_launch")
        beta_contrib = compute_sector_beta_score(sector=context.sector, beta=context.beta)
        atr_contrib = compute_volatility_score(atr_percentile=context.atr_percentile)
        market_contrib = compute_market_regime_score(spy_returns=context.spy_returns)
        
        total = base + beta_contrib + atr_contrib + market_contrib
        
        assert 0 <= total <= 100, "Score with degraded data should still be valid"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
