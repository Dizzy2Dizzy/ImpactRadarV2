"""
Persistent Topology Research Module - Proof of Concept
=======================================================
Tests persistent homology on stock price data to validate the approach
before full integration with Market Echo Engine.

This script:
1. Fetches stock price data and computes Takens embeddings
2. Computes persistent homology (Vietoris-Rips)
3. Extracts topological features
4. Backtests against historical events to measure improvement

Key Concepts:
- Takens Embedding: Converts 1D time series to point cloud in ℝᵐ
- Persistent Homology: Tracks birth/death of topological features
- Betti Numbers: β₀ (connected components), β₁ (loops)
"""

import os
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def fetch_price_data_yfinance(tickers: List[str], start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch price data using yfinance."""
    import yfinance as yf
    
    print(f"Fetching data for {len(tickers)} tickers from {start_date} to {end_date}...")
    
    try:
        data = yf.download(tickers, start=start_date, end=end_date, progress=False)
        
        if data.empty:
            print("No data returned from yfinance")
            return pd.DataFrame()
        
        if isinstance(data.columns, pd.MultiIndex):
            if 'Adj Close' in data.columns.get_level_values(0):
                prices = data['Adj Close']
            elif 'Close' in data.columns.get_level_values(0):
                prices = data['Close']
            else:
                prices = data
        else:
            prices = data
        
        if isinstance(prices, pd.Series):
            prices = prices.to_frame(name=tickers[0])
        
        if len(prices) > 0:
            valid_cols = prices.columns[prices.isna().sum() < len(prices) * 0.2]
            prices = prices[valid_cols].ffill().bfill().dropna()
        
        print(f"Successfully fetched {len(prices.columns)} tickers with {len(prices)} days of data")
        return prices
    except Exception as e:
        print(f"Error fetching data: {e}")
        return pd.DataFrame()


def calculate_log_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Calculate log returns from prices."""
    log_prices = np.log(prices)
    returns = log_prices.diff().dropna()
    return returns


def create_takens_embedding(time_series: np.ndarray, embedding_dim: int = 3, delay: int = 2) -> np.ndarray:
    """
    Create Takens delay embedding from 1D time series.
    
    Takens' theorem (1981): For a dynamical system, the delay embedding
    reconstructs the topology of the underlying attractor.
    
    Given time series x(t), create vectors:
    [x(t), x(t+τ), x(t+2τ), ..., x(t+(m-1)τ)]
    
    Args:
        time_series: 1D array of values
        embedding_dim: Target dimension (m)
        delay: Time delay between coordinates (τ)
        
    Returns:
        Point cloud in ℝᵐ
    """
    n = len(time_series)
    n_points = n - (embedding_dim - 1) * delay
    
    if n_points < 1:
        return np.array([]).reshape(0, embedding_dim)
    
    points = np.zeros((n_points, embedding_dim))
    
    for i in range(n_points):
        for j in range(embedding_dim):
            points[i, j] = time_series[i + j * delay]
    
    return points


def compute_persistence(point_cloud: np.ndarray, maxdim: int = 1) -> Dict:
    """
    Compute Vietoris-Rips persistent homology.
    
    The Vietoris-Rips complex:
    - At scale ε, connect points within distance ε
    - As ε grows, track when connected components merge (H0)
    - Track when loops form and fill in (H1)
    
    Returns persistence diagrams.
    """
    import ripser
    
    result = ripser.ripser(point_cloud, maxdim=maxdim, thresh=2.0)
    
    return {
        'dgms': result['dgms'],
        'num_edges': result.get('num_edges', 0)
    }


def extract_topological_features(diagrams: List[np.ndarray]) -> Dict:
    """
    Extract ML-ready features from persistence diagrams.
    
    Features:
    - Betti counts: Number of features in H0, H1
    - Lifetimes: Max and mean lifetimes
    - Total persistence: Sum of lifetimes
    - Persistence entropy: Complexity measure
    """
    features = {
        'betti0_count': 0,
        'betti1_count': 0,
        'max_lifetime_h0': 0.0,
        'max_lifetime_h1': 0.0,
        'mean_lifetime_h0': 0.0,
        'mean_lifetime_h1': 0.0,
        'total_persistence_h0': 0.0,
        'total_persistence_h1': 0.0,
        'persistence_entropy': 0.0,
        'topological_complexity': 0.0
    }
    
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
    
    features['betti0_count'] = len(h0_lifetimes)
    features['betti1_count'] = len(h1_lifetimes)
    
    if h0_lifetimes:
        features['max_lifetime_h0'] = max(h0_lifetimes)
        features['mean_lifetime_h0'] = np.mean(h0_lifetimes)
        features['total_persistence_h0'] = sum(h0_lifetimes)
    
    if h1_lifetimes:
        features['max_lifetime_h1'] = max(h1_lifetimes)
        features['mean_lifetime_h1'] = np.mean(h1_lifetimes)
        features['total_persistence_h1'] = sum(h1_lifetimes)
    
    all_lifetimes = h0_lifetimes + h1_lifetimes
    k = len(all_lifetimes)
    if k >= 2:
        total = sum(all_lifetimes)
        if total > 0:
            probabilities = [l / total for l in all_lifetimes]
            entropy = -sum(p * np.log(p + 1e-10) for p in probabilities)
            max_entropy = np.log(k)
            features['persistence_entropy'] = entropy / max_entropy if max_entropy > 0 else 0.0
    elif k == 1:
        features['persistence_entropy'] = 0.0
    
    features['topological_complexity'] = (
        features['betti1_count'] * 2.0 +
        features['persistence_entropy'] +
        features['total_persistence_h1']
    )
    
    return features


def analyze_single_stock(returns: pd.Series, ticker: str) -> Dict:
    """Analyze a single stock's topological features."""
    returns_array = returns.values
    
    if len(returns_array) < 15:
        return None
    
    returns_std = (returns_array - np.mean(returns_array)) / (np.std(returns_array) + 1e-8)
    
    embedding = create_takens_embedding(returns_std, embedding_dim=3, delay=2)
    
    if embedding.shape[0] < 5:
        return None
    
    persistence = compute_persistence(embedding)
    features = extract_topological_features(persistence['dgms'])
    
    features['ticker'] = ticker
    features['n_points'] = len(returns_array)
    features['embedding_points'] = embedding.shape[0]
    
    return features


def compare_topological_similarity(features1: Dict, features2: Dict) -> float:
    """
    Compute topological similarity between two feature sets.
    Uses cosine similarity on normalized feature vectors.
    """
    v1 = np.array([
        features1['betti0_count'], features1['betti1_count'],
        features1['max_lifetime_h0'], features1['max_lifetime_h1'],
        features1['mean_lifetime_h0'], features1['mean_lifetime_h1'],
        features1['persistence_entropy'], features1['topological_complexity']
    ])
    
    v2 = np.array([
        features2['betti0_count'], features2['betti1_count'],
        features2['max_lifetime_h0'], features2['max_lifetime_h1'],
        features2['mean_lifetime_h0'], features2['mean_lifetime_h1'],
        features2['persistence_entropy'], features2['topological_complexity']
    ])
    
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    
    if norm1 < 1e-8 or norm2 < 1e-8:
        return 0.0
    
    return float(np.dot(v1, v2) / (norm1 * norm2))


def get_events_with_outcomes() -> List[Dict]:
    """Fetch events with outcomes from Impact Radar database."""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("DATABASE_URL not set")
        return []
    
    try:
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker
        
        engine = create_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        query = text("""
            SELECT 
                e.id,
                e.ticker,
                e.title,
                e.event_type,
                e.impact_score,
                e.direction,
                e.confidence,
                e.date,
                e.sector,
                eo.return_pct,
                eo.direction_correct,
                eo.horizon
            FROM events e
            JOIN event_outcomes eo ON e.id = eo.event_id
            WHERE e.date > NOW() - INTERVAL '180 days'
            AND eo.horizon = '1d'
            AND eo.return_pct IS NOT NULL
            ORDER BY e.date DESC
            LIMIT 200
        """)
        
        result = session.execute(query)
        events = []
        for row in result:
            events.append({
                'id': row[0],
                'ticker': row[1],
                'title': row[2],
                'event_type': row[3],
                'impact_score': float(row[4]) if row[4] else 0,
                'direction': row[5],
                'confidence': float(row[6]) if row[6] else 0,
                'date': row[7],
                'sector': row[8],
                'return_pct': float(row[9]) if row[9] else None,
                'direction_correct': row[10],
                'horizon': row[11]
            })
        
        session.close()
        print(f"Fetched {len(events)} events with outcomes")
        return events
    except Exception as e:
        print(f"Error fetching events: {e}")
        import traceback
        traceback.print_exc()
        return []


def backtest_persistent_features(events: List[Dict], returns: pd.DataFrame) -> Dict:
    """
    Backtest persistent homology features against historical events.
    
    Tests if topological features help predict event outcomes.
    """
    results = {
        'total_events': len(events),
        'events_with_features': 0,
        'baseline_accuracy': 0.0,
        'topology_enhanced_accuracy': 0.0,
        'improvement': 0.0,
        'feature_correlation_with_returns': {},
        'cluster_analysis': {}
    }
    
    if not events:
        return results
    
    baseline_correct = 0
    total_with_returns = 0
    
    event_features = []
    
    for event in events:
        if event.get('return_pct') is not None and event.get('direction'):
            total_with_returns += 1
            predicted_positive = event['direction'].lower() in ['positive', 'up', 'bullish']
            actual_positive = event['return_pct'] > 0
            
            if predicted_positive == actual_positive:
                baseline_correct += 1
            
            ticker = event['ticker']
            if ticker in returns.columns:
                event_date = event['date']
                if hasattr(event_date, 'strftime'):
                    event_date_str = event_date.strftime('%Y-%m-%d')
                else:
                    event_date_str = str(event_date)[:10]
                
                try:
                    event_idx = returns.index.get_loc(event_date_str, method='pad')
                except:
                    event_idx = len(returns) - 1
                
                start_idx = max(0, event_idx - 30)
                ticker_returns = returns[ticker].iloc[start_idx:event_idx]
                
                if len(ticker_returns) >= 15:
                    features = analyze_single_stock(ticker_returns, ticker)
                    if features:
                        features['event_id'] = event['id']
                        features['return_pct'] = event['return_pct']
                        features['direction'] = event['direction']
                        features['actual_positive'] = actual_positive
                        features['predicted_positive'] = predicted_positive
                        event_features.append(features)
    
    results['events_with_features'] = len(event_features)
    
    if total_with_returns > 0:
        results['baseline_accuracy'] = baseline_correct / total_with_returns
    
    if event_features:
        feature_names = ['betti0_count', 'betti1_count', 'max_lifetime_h0', 
                        'max_lifetime_h1', 'persistence_entropy', 'topological_complexity']
        
        for feature in feature_names:
            values = [f[feature] for f in event_features]
            returns_vals = [f['return_pct'] for f in event_features]
            
            if len(values) > 2 and np.std(values) > 0:
                corr = np.corrcoef(values, returns_vals)[0, 1]
                results['feature_correlation_with_returns'][feature] = round(corr, 4)
        
        enhanced_correct = 0
        for features in event_features:
            adjusted_prediction = features['predicted_positive']
            
            if features['topological_complexity'] > 2.0 and features['betti1_count'] > 3:
                adjusted_prediction = not adjusted_prediction
            
            if adjusted_prediction == features['actual_positive']:
                enhanced_correct += 1
        
        results['topology_enhanced_accuracy'] = enhanced_correct / len(event_features)
        results['improvement'] = results['topology_enhanced_accuracy'] - results['baseline_accuracy']
        
        complexity_values = [f['topological_complexity'] for f in event_features]
        median_complexity = np.median(complexity_values)
        
        high_complexity = [f for f in event_features if f['topological_complexity'] >= median_complexity]
        low_complexity = [f for f in event_features if f['topological_complexity'] < median_complexity]
        
        results['cluster_analysis'] = {
            'high_complexity': {
                'count': len(high_complexity),
                'avg_return': np.mean([f['return_pct'] for f in high_complexity]) if high_complexity else 0,
                'positive_rate': sum(1 for f in high_complexity if f['actual_positive']) / len(high_complexity) if high_complexity else 0
            },
            'low_complexity': {
                'count': len(low_complexity),
                'avg_return': np.mean([f['return_pct'] for f in low_complexity]) if low_complexity else 0,
                'positive_rate': sum(1 for f in low_complexity if f['actual_positive']) / len(low_complexity) if low_complexity else 0
            }
        }
    
    return results


def run_persistent_topology_research() -> Dict:
    """Run the full persistent topology research pipeline."""
    
    print("=" * 70)
    print("PERSISTENT TOPOLOGY RESEARCH MODULE")
    print("=" * 70)
    print()
    print("Testing if persistent homology can improve event predictions")
    print()
    
    test_tickers = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA',
        'JPM', 'BAC', 'GS', 'JNJ', 'PFE', 'XOM', 'CVX'
    ]
    
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    
    prices = fetch_price_data_yfinance(test_tickers, start_date, end_date)
    
    if prices.empty:
        return {'error': 'Failed to fetch market data'}
    
    returns = calculate_log_returns(prices)
    print(f"Calculated returns: {returns.shape}")
    print()
    
    print("-" * 70)
    print("ANALYZING TOPOLOGICAL FEATURES")
    print("-" * 70)
    print()
    
    all_features = []
    for ticker in returns.columns:
        features = analyze_single_stock(returns[ticker], ticker)
        if features:
            all_features.append(features)
            print(f"{ticker}: β₀={features['betti0_count']}, β₁={features['betti1_count']}, "
                  f"entropy={features['persistence_entropy']:.3f}, "
                  f"complexity={features['topological_complexity']:.2f}")
    
    print()
    print(f"Successfully analyzed {len(all_features)} stocks")
    print()
    
    avg_betti0 = np.mean([f['betti0_count'] for f in all_features])
    avg_betti1 = np.mean([f['betti1_count'] for f in all_features])
    avg_entropy = np.mean([f['persistence_entropy'] for f in all_features])
    avg_complexity = np.mean([f['topological_complexity'] for f in all_features])
    
    print(f"Average β₀ (connected components): {avg_betti0:.1f}")
    print(f"Average β₁ (loops): {avg_betti1:.1f}")
    print(f"Average persistence entropy: {avg_entropy:.3f}")
    print(f"Average topological complexity: {avg_complexity:.2f}")
    print()
    
    print("-" * 70)
    print("TOPOLOGICAL SIMILARITY MATRIX")
    print("-" * 70)
    print()
    
    if len(all_features) >= 2:
        similarities = []
        for i, f1 in enumerate(all_features[:5]):
            row = []
            for j, f2 in enumerate(all_features[:5]):
                if i != j:
                    sim = compare_topological_similarity(f1, f2)
                    similarities.append(sim)
                    row.append(f"{sim:.2f}")
                else:
                    row.append("1.00")
            print(f"{f1['ticker']:6s} | " + " | ".join(row))
        
        print()
        print(f"Average pairwise similarity: {np.mean(similarities):.3f}")
    print()
    
    print("-" * 70)
    print("BACKTESTING WITH EVENTS")
    print("-" * 70)
    print()
    
    events = get_events_with_outcomes()
    
    if events:
        backtest_results = backtest_persistent_features(events, returns)
        
        print(f"Total events analyzed: {backtest_results['total_events']}")
        print(f"Events with topological features: {backtest_results['events_with_features']}")
        print()
        print(f"Baseline direction accuracy: {backtest_results['baseline_accuracy']:.1%}")
        print(f"Topology-enhanced accuracy: {backtest_results['topology_enhanced_accuracy']:.1%}")
        print(f"Improvement: {backtest_results['improvement']:+.1%}")
        print()
        
        if backtest_results['feature_correlation_with_returns']:
            print("Feature correlations with returns:")
            for feature, corr in backtest_results['feature_correlation_with_returns'].items():
                print(f"  {feature}: {corr:+.4f}")
        print()
        
        if backtest_results['cluster_analysis']:
            print("Cluster analysis (by topological complexity):")
            for cluster, stats in backtest_results['cluster_analysis'].items():
                print(f"  {cluster}: {stats['count']} events, "
                      f"avg return: {stats['avg_return']:.2%}, "
                      f"positive rate: {stats['positive_rate']:.1%}")
    else:
        print("No events found for backtesting")
        backtest_results = {}
    
    print()
    print("-" * 70)
    print("CONCLUSIONS")
    print("-" * 70)
    print()
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'stocks_analyzed': len(all_features),
        'feature_summary': {
            'avg_betti0': avg_betti0,
            'avg_betti1': avg_betti1,
            'avg_entropy': avg_entropy,
            'avg_complexity': avg_complexity
        },
        'backtest': backtest_results,
        'recommendations': []
    }
    
    if avg_betti1 > 0.5:
        results['recommendations'].append(
            "POSITIVE: Detected non-trivial H1 features (loops) - price patterns have meaningful topology"
        )
    
    if backtest_results and backtest_results.get('improvement', 0) > 0:
        results['recommendations'].append(
            f"POSITIVE: Persistent features improved accuracy by {backtest_results['improvement']:.1%}"
        )
    
    if results['feature_summary']['avg_entropy'] > 0.3:
        results['recommendations'].append(
            "INSIGHT: High persistence entropy indicates complex market dynamics"
        )
    
    results['recommendations'].append(
        "NEXT STEP: Integrate persistent features into Market Echo Engine ML pipeline"
    )
    
    for rec in results['recommendations']:
        print(f"  - {rec}")
    
    print()
    print("=" * 70)
    
    output_file = 'persistent_topology_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Results saved to {output_file}")
    
    return results


if __name__ == '__main__':
    run_persistent_topology_research()
