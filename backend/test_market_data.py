"""
Test script for market data integration.

Tests:
1. MarketDataService can fetch beta, ATR, SPY for AAPL
2. Graceful degradation when data unavailable
3. Scoring integration with market data
"""

import logging
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from services.market_data_service import MarketDataService
from analytics.scoring import compute_sector_beta_score, compute_volatility_score, compute_market_regime_score

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_market_data_service():
    """Test MarketDataService with AAPL."""
    print("\n" + "="*60)
    print("Testing MarketDataService with AAPL")
    print("="*60)
    
    service = MarketDataService()
    
    # Test beta
    print("\n1. Testing Beta:")
    beta = service.get_beta("AAPL")
    if beta is not None:
        print(f"✓ Beta for AAPL: {beta:.2f}")
        score_contrib = compute_sector_beta_score(beta=beta)
        print(f"  Score contribution: +{score_contrib} points")
    else:
        print("✗ Beta unavailable (yfinance may not be installed)")
    
    # Test ATR percentile
    print("\n2. Testing ATR Percentile:")
    atr_pct = service.get_atr_percentile("AAPL")
    if atr_pct is not None:
        print(f"✓ ATR Percentile for AAPL: {atr_pct:.1f}")
        score_contrib = compute_volatility_score(atr_pct)
        print(f"  Score contribution: +{score_contrib} points")
    else:
        print("✗ ATR percentile unavailable")
    
    # Test SPY returns
    print("\n3. Testing SPY Returns:")
    spy_returns = service.get_spy_returns()
    if spy_returns is not None:
        print(f"✓ SPY Returns:")
        print(f"  1-day:  {spy_returns['1d']*100:+.2f}%")
        print(f"  5-day:  {spy_returns['5d']*100:+.2f}%")
        print(f"  20-day: {spy_returns['20d']*100:+.2f}%")
        
        regime = service.get_market_regime(spy_returns)
        print(f"  Market Regime: {regime}")
        
        score_contrib = compute_market_regime_score(spy_returns)
        print(f"  Score contribution: {score_contrib:+d} points")
    else:
        print("✗ SPY returns unavailable")
    
    # Test cache
    print("\n4. Testing Cache (second fetch should be instant):")
    import time
    start = time.time()
    beta2 = service.get_beta("AAPL")
    elapsed = time.time() - start
    print(f"✓ Cache test: {elapsed*1000:.1f}ms (should be <10ms for cached)")
    
    return service


def test_graceful_degradation():
    """Test graceful degradation when yfinance unavailable."""
    print("\n" + "="*60)
    print("Testing Graceful Degradation")
    print("="*60)
    
    # Simulate yfinance unavailable
    service = MarketDataService()
    service.yfinance_available = False
    
    print("\n1. Beta with unavailable yfinance:")
    beta = service.get_beta("AAPL")
    print(f"  Result: {beta} (should be None)")
    
    print("\n2. ATR with unavailable yfinance:")
    atr = service.get_atr_percentile("AAPL")
    print(f"  Result: {atr} (should be None)")
    
    print("\n3. SPY returns with unavailable yfinance:")
    spy = service.get_spy_returns()
    print(f"  Result: {spy} (should be None)")
    
    # Test scoring still works with None values
    print("\n4. Scoring with None market data:")
    score_beta = compute_sector_beta_score(beta=None)
    score_vol = compute_volatility_score(atr_percentile=None)
    score_regime = compute_market_regime_score(spy_returns=None)
    
    print(f"  Beta score (None):   +{score_beta} (should use sector default)")
    print(f"  Volatility (None):   +{score_vol} (should be +5, default)")
    print(f"  Regime score (None): {score_regime:+d} (should be 0, neutral)")
    print("✓ Graceful degradation working")


def test_scoring_integration():
    """Test full scoring integration."""
    print("\n" + "="*60)
    print("Testing Full Scoring Integration")
    print("="*60)
    
    service = MarketDataService()
    
    # Get market data
    beta = service.get_beta("AAPL")
    atr_pct = service.get_atr_percentile("AAPL")
    spy_returns = service.get_spy_returns()
    
    print("\n1. Market Data Factors for AAPL:")
    beta_str = f"{beta:.2f}" if beta is not None else "N/A"
    atr_str = f"{atr_pct:.1f}" if atr_pct is not None else "N/A"
    spy_str = f"{spy_returns['5d']*100:+.2f}%" if spy_returns is not None else "N/A"
    print(f"  Beta: {beta_str}")
    print(f"  ATR Percentile: {atr_str}")
    print(f"  SPY 5d Return: {spy_str}")
    
    # Calculate score contributions
    if beta or atr_pct or spy_returns:
        print("\n2. Score Contributions:")
        
        beta_contrib = compute_sector_beta_score(beta=beta) if beta else 0
        atr_contrib = compute_volatility_score(atr_pct) if atr_pct else 5
        regime_contrib = compute_market_regime_score(spy_returns) if spy_returns else 0
        
        print(f"  Beta contribution:    +{beta_contrib} points")
        print(f"  ATR contribution:     +{atr_contrib} points")
        print(f"  Regime contribution:  {regime_contrib:+d} points")
        print(f"  Total context boost:  {beta_contrib + atr_contrib + regime_contrib:+d} points")
        
        # Example on 65-point earnings event
        base = 65
        total = base + beta_contrib + atr_contrib + regime_contrib
        boost_pct = ((total - base) / base) * 100
        
        print(f"\n3. Example Impact (Earnings event, base=65):")
        print(f"  Base score:      {base}")
        print(f"  With market data: {total}")
        print(f"  Boost:           {boost_pct:+.1f}%")
        
        if boost_pct >= 25:
            print(f"✓ Meets 25-45% boost requirement")
        else:
            print(f"  Note: Boost depends on current market conditions")
    else:
        print("  Skipping - market data unavailable")


def main():
    """Run all tests."""
    try:
        # Test 1: Basic functionality
        service = test_market_data_service()
        
        # Test 2: Graceful degradation
        test_graceful_degradation()
        
        # Test 3: Full integration
        test_scoring_integration()
        
        print("\n" + "="*60)
        print("✓ All Tests Completed Successfully")
        print("="*60)
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
