"""
Topology Research Module - Proof of Concept
============================================
Tests correlation clustering and regime detection against real market data
and existing Impact Radar events to validate the approach before full integration.

Components:
1. Correlation Clustering - Groups stocks by price movement similarity
2. Regime Detection - Identifies risk-on/risk-off market states
3. Event Backtesting - Tests if topology features improve predictions
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
import yfinance as yf
from scipy import stats
from sklearn.cluster import SpectralClustering, KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


# ============================================================================
# CONFIGURATION
# ============================================================================

SP500_SECTORS = {
    'Technology': ['AAPL', 'MSFT', 'GOOGL', 'META', 'NVDA', 'AMD', 'INTC', 'CRM', 'ADBE', 'ORCL'],
    'Healthcare': ['JNJ', 'UNH', 'PFE', 'ABBV', 'MRK', 'LLY', 'TMO', 'ABT', 'DHR', 'BMY'],
    'Financials': ['JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'BLK', 'SCHW', 'AXP', 'USB'],
    'Consumer': ['AMZN', 'TSLA', 'HD', 'MCD', 'NKE', 'SBUX', 'TGT', 'COST', 'LOW', 'TJX'],
    'Energy': ['XOM', 'CVX', 'COP', 'SLB', 'EOG', 'MPC', 'PSX', 'VLO', 'OXY', 'HAL'],
    'Industrials': ['CAT', 'DE', 'UNP', 'HON', 'BA', 'GE', 'LMT', 'RTX', 'MMM', 'UPS'],
    'Biotech': ['GILD', 'AMGN', 'BIIB', 'REGN', 'VRTX', 'MRNA', 'ILMN', 'ISRG', 'ZTS', 'INCY'],
}

ALL_TICKERS = [ticker for sector in SP500_SECTORS.values() for ticker in sector]

REGIME_THRESHOLDS = {
    'high_volatility': 0.02,  # Daily return std > 2%
    'high_correlation': 0.6,   # Average correlation > 0.6
    'low_correlation': 0.3,    # Average correlation < 0.3
}


# ============================================================================
# DATA FETCHING
# ============================================================================

def fetch_market_data(tickers: List[str], start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch adjusted close prices for given tickers."""
    print(f"Fetching data for {len(tickers)} tickers from {start_date} to {end_date}...")
    
    try:
        data = yf.download(tickers, start=start_date, end=end_date, progress=False, threads=True)
        
        if data.empty:
            print("No data returned from yfinance")
            return pd.DataFrame()
        
        # Handle multi-level columns
        if isinstance(data.columns, pd.MultiIndex):
            if 'Adj Close' in data.columns.get_level_values(0):
                prices = data['Adj Close']
            elif 'Close' in data.columns.get_level_values(0):
                prices = data['Close']
            else:
                prices = data
        else:
            prices = data
        
        # Handle single ticker case
        if isinstance(prices, pd.Series):
            prices = prices.to_frame(name=tickers[0])
        
        # Drop tickers with too much missing data (more than 20%)
        if len(prices) > 0:
            valid_cols = prices.columns[prices.isna().sum() < len(prices) * 0.2]
            prices = prices[valid_cols].ffill().bfill().dropna()
        
        print(f"Successfully fetched {len(prices.columns)} tickers with {len(prices)} days of data")
        return prices
    except Exception as e:
        print(f"Error fetching data: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def calculate_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Calculate daily returns from prices."""
    returns = prices.pct_change().dropna()
    return returns


# ============================================================================
# CORRELATION CLUSTERING
# ============================================================================

def build_correlation_matrix(returns: pd.DataFrame, window: int = 60) -> pd.DataFrame:
    """Build rolling correlation matrix."""
    if len(returns) < window:
        return returns.corr()
    
    # Use most recent window
    recent_returns = returns.tail(window)
    corr_matrix = recent_returns.corr()
    return corr_matrix


def perform_spectral_clustering(corr_matrix: pd.DataFrame, n_clusters: int = 7) -> Dict[str, int]:
    """
    Perform spectral clustering on correlation matrix.
    Returns mapping of ticker to cluster ID.
    """
    # Convert correlation to affinity (similarity) matrix
    # Use absolute correlation to group both positively and negatively correlated stocks
    affinity = np.abs(corr_matrix.values)
    np.fill_diagonal(affinity, 1.0)
    
    # Handle NaN values
    affinity = np.nan_to_num(affinity, nan=0.0)
    
    # Ensure matrix is symmetric
    affinity = (affinity + affinity.T) / 2
    
    try:
        clustering = SpectralClustering(
            n_clusters=n_clusters,
            affinity='precomputed',
            random_state=42,
            n_init=10
        )
        labels = clustering.fit_predict(affinity)
        
        ticker_clusters = {ticker: int(label) for ticker, label in zip(corr_matrix.columns, labels)}
        return ticker_clusters
    except Exception as e:
        print(f"Spectral clustering failed: {e}, falling back to KMeans")
        # Fallback to KMeans on correlation features
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(corr_matrix.values)
        return {ticker: int(label) for ticker, label in zip(corr_matrix.columns, labels)}


def analyze_clusters(returns: pd.DataFrame, ticker_clusters: Dict[str, int], 
                     sector_mapping: Dict[str, str]) -> Dict:
    """Analyze cluster composition and quality."""
    
    # Reverse sector mapping: ticker -> sector
    ticker_to_sector = {}
    for sector, tickers in SP500_SECTORS.items():
        for ticker in tickers:
            ticker_to_sector[ticker] = sector
    
    # Group by cluster
    clusters = {}
    for ticker, cluster_id in ticker_clusters.items():
        if cluster_id not in clusters:
            clusters[cluster_id] = []
        clusters[cluster_id].append(ticker)
    
    # Analyze each cluster
    analysis = {
        'cluster_count': len(clusters),
        'clusters': {},
        'sector_purity': {},
        'intra_cluster_correlation': {}
    }
    
    for cluster_id, tickers in clusters.items():
        # Sector composition
        sectors = [ticker_to_sector.get(t, 'Unknown') for t in tickers]
        sector_counts = pd.Series(sectors).value_counts().to_dict()
        
        # Dominant sector
        dominant_sector = max(sector_counts, key=sector_counts.get)
        purity = sector_counts[dominant_sector] / len(tickers)
        
        # Intra-cluster correlation
        if len(tickers) > 1:
            cluster_returns = returns[[t for t in tickers if t in returns.columns]]
            if len(cluster_returns.columns) > 1:
                corr = cluster_returns.corr()
                # Get average off-diagonal correlation
                mask = ~np.eye(corr.shape[0], dtype=bool)
                avg_corr = corr.values[mask].mean()
            else:
                avg_corr = 1.0
        else:
            avg_corr = 1.0
        
        analysis['clusters'][cluster_id] = {
            'tickers': tickers,
            'size': len(tickers),
            'sector_composition': sector_counts,
            'dominant_sector': dominant_sector,
            'purity': purity
        }
        analysis['sector_purity'][cluster_id] = purity
        analysis['intra_cluster_correlation'][cluster_id] = avg_corr
    
    # Overall metrics
    analysis['avg_purity'] = np.mean(list(analysis['sector_purity'].values()))
    analysis['avg_intra_correlation'] = np.mean(list(analysis['intra_cluster_correlation'].values()))
    
    return analysis


# ============================================================================
# REGIME DETECTION
# ============================================================================

def detect_market_regime(returns: pd.DataFrame, window: int = 20) -> Dict:
    """
    Detect current market regime based on:
    1. Volatility level (rolling std of returns)
    2. Average correlation (how much stocks move together)
    3. Trend direction (recent returns)
    """
    
    if len(returns) < window:
        return {'regime': 'unknown', 'confidence': 0.0}
    
    recent_returns = returns.tail(window)
    
    # 1. Volatility - average daily volatility across stocks
    volatility = recent_returns.std().mean()
    
    # 2. Average correlation
    corr_matrix = recent_returns.corr()
    mask = ~np.eye(corr_matrix.shape[0], dtype=bool)
    avg_correlation = np.abs(corr_matrix.values[mask]).mean()
    
    # 3. Market trend - average cumulative return
    cumulative_returns = (1 + recent_returns).prod() - 1
    avg_return = cumulative_returns.mean()
    
    # 4. VIX-like measure: percentage of stocks with negative returns
    negative_pct = (cumulative_returns < 0).mean()
    
    # Classify regime
    regime_scores = {
        'risk_on': 0,
        'risk_off': 0,
        'high_volatility': 0,
        'low_volatility': 0,
        'trend_up': 0,
        'trend_down': 0,
        'correlated': 0,
        'dispersed': 0
    }
    
    # Volatility classification
    if volatility > REGIME_THRESHOLDS['high_volatility']:
        regime_scores['high_volatility'] = 1
        regime_scores['risk_off'] += 0.3
    else:
        regime_scores['low_volatility'] = 1
        regime_scores['risk_on'] += 0.2
    
    # Correlation classification
    if avg_correlation > REGIME_THRESHOLDS['high_correlation']:
        regime_scores['correlated'] = 1
        regime_scores['risk_off'] += 0.3  # High correlation often means panic
    elif avg_correlation < REGIME_THRESHOLDS['low_correlation']:
        regime_scores['dispersed'] = 1
        regime_scores['risk_on'] += 0.2  # Stock picking environment
    
    # Trend classification
    if avg_return > 0.02:  # More than 2% gain
        regime_scores['trend_up'] = 1
        regime_scores['risk_on'] += 0.5
    elif avg_return < -0.02:  # More than 2% loss
        regime_scores['trend_down'] = 1
        regime_scores['risk_off'] += 0.5
    
    # Breadth - if most stocks are negative, it's risk-off
    if negative_pct > 0.6:
        regime_scores['risk_off'] += 0.3
    elif negative_pct < 0.4:
        regime_scores['risk_on'] += 0.3
    
    # Determine primary regime
    if regime_scores['risk_on'] > regime_scores['risk_off']:
        primary_regime = 'risk_on'
        confidence = regime_scores['risk_on'] / (regime_scores['risk_on'] + regime_scores['risk_off'])
    else:
        primary_regime = 'risk_off'
        confidence = regime_scores['risk_off'] / (regime_scores['risk_on'] + regime_scores['risk_off'])
    
    return {
        'regime': primary_regime,
        'confidence': round(confidence, 3),
        'volatility': round(volatility, 4),
        'avg_correlation': round(avg_correlation, 3),
        'avg_return': round(avg_return, 4),
        'negative_breadth': round(negative_pct, 3),
        'scores': regime_scores
    }


def get_regime_history(returns: pd.DataFrame, window: int = 20, step: int = 5) -> List[Dict]:
    """Calculate regime at multiple points in time."""
    history = []
    
    for i in range(window, len(returns), step):
        date = returns.index[i]
        regime = detect_market_regime(returns.iloc[:i], window)
        regime['date'] = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)
        history.append(regime)
    
    return history


# ============================================================================
# EVENT BACKTESTING
# ============================================================================

def get_existing_events(limit: int = 100) -> List[Dict]:
    """Fetch existing events from Impact Radar database with outcome data."""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("DATABASE_URL not set, using sample events")
        return []
    
    try:
        engine = create_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Get recent events joined with outcomes for actual returns
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
                eo.price_before,
                eo.price_after,
                eo.return_pct,
                eo.direction_correct,
                eo.horizon
            FROM events e
            JOIN event_outcomes eo ON e.id = eo.event_id
            WHERE e.date > NOW() - INTERVAL '180 days'
            AND eo.horizon = '1d'
            AND eo.price_before IS NOT NULL
            AND eo.price_after IS NOT NULL
            ORDER BY e.date DESC
            LIMIT :limit
        """)
        
        result = session.execute(query, {'limit': limit})
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
                'price_before': float(row[9]) if row[9] else None,
                'price_after': float(row[10]) if row[10] else None,
                'return_pct': float(row[11]) if row[11] else None,
                'direction_correct': row[12],
                'horizon': row[13]
            })
        
        session.close()
        print(f"Fetched {len(events)} events with outcomes from database")
        return events
    except Exception as e:
        print(f"Error fetching events: {e}")
        import traceback
        traceback.print_exc()
        return []


def calculate_actual_returns(events: List[Dict]) -> List[Dict]:
    """Calculate actual price returns for events (already have return_pct from database)."""
    for event in events:
        # Use the return_pct directly from event_outcomes
        event['actual_return_1d'] = event.get('return_pct')
    
    return events


def backtest_with_topology(events: List[Dict], returns: pd.DataFrame, 
                           ticker_clusters: Dict[str, int]) -> Dict:
    """
    Backtest events with topology features to see if they improve predictions.
    
    Hypothesis: Events in the same cluster should have correlated outcomes.
    Regime context should help predict magnitude of moves.
    """
    
    results = {
        'total_events': len(events),
        'events_with_cluster': 0,
        'events_with_regime': 0,
        'baseline_accuracy': 0,
        'topology_enhanced_accuracy': 0,
        'regime_analysis': {},
        'cluster_analysis': {}
    }
    
    if not events:
        return results
    
    # Group events by cluster
    cluster_events = {}
    for event in events:
        ticker = event['ticker']
        if ticker in ticker_clusters:
            cluster_id = ticker_clusters[ticker]
            if cluster_id not in cluster_events:
                cluster_events[cluster_id] = []
            cluster_events[cluster_id].append(event)
            results['events_with_cluster'] += 1
    
    # Analyze baseline prediction accuracy
    correct_direction = 0
    total_with_returns = 0
    
    for event in events:
        if event.get('actual_return_1d') is not None and event.get('direction'):
            total_with_returns += 1
            predicted_positive = event['direction'].lower() in ['positive', 'up', 'bullish']
            actual_positive = event['actual_return_1d'] > 0
            
            if predicted_positive == actual_positive:
                correct_direction += 1
    
    if total_with_returns > 0:
        results['baseline_accuracy'] = correct_direction / total_with_returns
    
    # Analyze by cluster
    for cluster_id, cluster_events_list in cluster_events.items():
        returns_1d = [e['actual_return_1d'] for e in cluster_events_list if e.get('actual_return_1d') is not None]
        
        if returns_1d:
            results['cluster_analysis'][cluster_id] = {
                'event_count': len(cluster_events_list),
                'avg_return_1d': np.mean(returns_1d),
                'std_return_1d': np.std(returns_1d),
                'positive_rate': sum(1 for r in returns_1d if r > 0) / len(returns_1d)
            }
    
    # Regime analysis - group events by market regime at time of event
    # This is simplified - in production would calculate regime at event time
    current_regime = detect_market_regime(returns)
    results['current_regime'] = current_regime
    
    # Calculate topology-enhanced accuracy
    # Hypothesis: if event is in a high-correlation cluster during risk-off,
    # we should expect muted positive reactions
    enhanced_correct = 0
    enhanced_total = 0
    
    for event in events:
        if event.get('actual_return_1d') is None or not event.get('direction'):
            continue
        
        ticker = event['ticker']
        if ticker not in ticker_clusters:
            continue
        
        enhanced_total += 1
        cluster_id = ticker_clusters[ticker]
        
        # Get cluster characteristics
        cluster_info = results['cluster_analysis'].get(cluster_id, {})
        cluster_avg = cluster_info.get('avg_return_1d', 0)
        
        # Adjust prediction based on cluster tendency
        predicted_positive = event['direction'].lower() in ['positive', 'up', 'bullish']
        
        # If cluster tends negative and prediction is positive, be skeptical
        if cluster_avg < -0.01 and predicted_positive:
            adjusted_positive = False
        elif cluster_avg > 0.01 and not predicted_positive:
            adjusted_positive = True
        else:
            adjusted_positive = predicted_positive
        
        actual_positive = event['actual_return_1d'] > 0
        
        if adjusted_positive == actual_positive:
            enhanced_correct += 1
    
    if enhanced_total > 0:
        results['topology_enhanced_accuracy'] = enhanced_correct / enhanced_total
    
    results['improvement'] = results['topology_enhanced_accuracy'] - results['baseline_accuracy']
    
    return results


# ============================================================================
# MAIN RESEARCH FUNCTION
# ============================================================================

def run_topology_research() -> Dict:
    """Run the full topology research pipeline."""
    
    print("=" * 70)
    print("TOPOLOGY RESEARCH MODULE - PROOF OF CONCEPT")
    print("=" * 70)
    print()
    
    # 1. Fetch market data
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    
    prices = fetch_market_data(ALL_TICKERS, start_date, end_date)
    
    if prices.empty:
        return {'error': 'Failed to fetch market data'}
    
    returns = calculate_returns(prices)
    print(f"Calculated returns: {returns.shape}")
    print()
    
    # 2. Build correlation matrix and perform clustering
    print("-" * 70)
    print("CORRELATION CLUSTERING")
    print("-" * 70)
    
    corr_matrix = build_correlation_matrix(returns, window=60)
    ticker_clusters = perform_spectral_clustering(corr_matrix, n_clusters=7)
    
    cluster_analysis = analyze_clusters(returns, ticker_clusters, SP500_SECTORS)
    
    print(f"Created {cluster_analysis['cluster_count']} clusters")
    print(f"Average sector purity: {cluster_analysis['avg_purity']:.1%}")
    print(f"Average intra-cluster correlation: {cluster_analysis['avg_intra_correlation']:.3f}")
    print()
    
    for cluster_id, info in cluster_analysis['clusters'].items():
        print(f"  Cluster {cluster_id}: {info['size']} stocks, "
              f"dominant sector: {info['dominant_sector']} ({info['purity']:.0%})")
        print(f"    Tickers: {', '.join(info['tickers'][:5])}{'...' if len(info['tickers']) > 5 else ''}")
    print()
    
    # 3. Regime detection
    print("-" * 70)
    print("REGIME DETECTION")
    print("-" * 70)
    
    current_regime = detect_market_regime(returns, window=20)
    print(f"Current Market Regime: {current_regime['regime'].upper()}")
    print(f"  Confidence: {current_regime['confidence']:.1%}")
    print(f"  Volatility: {current_regime['volatility']:.2%}")
    print(f"  Avg Correlation: {current_regime['avg_correlation']:.3f}")
    print(f"  Recent Avg Return: {current_regime['avg_return']:.2%}")
    print(f"  Negative Breadth: {current_regime['negative_breadth']:.1%}")
    print()
    
    # Regime history
    regime_history = get_regime_history(returns, window=20, step=10)
    risk_on_pct = sum(1 for r in regime_history if r['regime'] == 'risk_on') / len(regime_history)
    print(f"Historical regime split: {risk_on_pct:.1%} risk-on, {1-risk_on_pct:.1%} risk-off")
    print()
    
    # 4. Backtest with existing events
    print("-" * 70)
    print("EVENT BACKTESTING")
    print("-" * 70)
    
    events = get_existing_events(limit=200)
    events = calculate_actual_returns(events)
    
    if events:
        backtest_results = backtest_with_topology(events, returns, ticker_clusters)
        
        print(f"Total events analyzed: {backtest_results['total_events']}")
        print(f"Events with cluster match: {backtest_results['events_with_cluster']}")
        print()
        print(f"Baseline direction accuracy: {backtest_results['baseline_accuracy']:.1%}")
        print(f"Topology-enhanced accuracy: {backtest_results['topology_enhanced_accuracy']:.1%}")
        print(f"Improvement: {backtest_results['improvement']:+.1%}")
        print()
        
        if backtest_results['cluster_analysis']:
            print("Cluster Performance:")
            for cluster_id, stats in backtest_results['cluster_analysis'].items():
                print(f"  Cluster {cluster_id}: {stats['event_count']} events, "
                      f"avg return: {stats['avg_return_1d']:.2%}, "
                      f"positive rate: {stats['positive_rate']:.1%}")
    else:
        backtest_results = {'note': 'No events available for backtesting'}
        print("No events available in database for backtesting")
    print()
    
    # 5. Compile results
    print("-" * 70)
    print("SUMMARY & RECOMMENDATIONS")
    print("-" * 70)
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'data_range': {'start': start_date, 'end': end_date},
        'stocks_analyzed': len(prices.columns),
        'days_of_data': len(returns),
        'clustering': {
            'method': 'spectral_clustering',
            'n_clusters': cluster_analysis['cluster_count'],
            'avg_purity': cluster_analysis['avg_purity'],
            'avg_intra_correlation': cluster_analysis['avg_intra_correlation'],
            'clusters': cluster_analysis['clusters']
        },
        'regime': current_regime,
        'regime_history_summary': {
            'total_periods': len(regime_history),
            'risk_on_pct': risk_on_pct,
            'risk_off_pct': 1 - risk_on_pct
        },
        'backtest': backtest_results,
        'recommendations': []
    }
    
    # Generate recommendations
    if cluster_analysis['avg_purity'] > 0.5:
        results['recommendations'].append(
            "POSITIVE: Correlation clustering shows strong sector alignment - clusters are meaningful"
        )
    else:
        results['recommendations'].append(
            "CAUTION: Low sector purity in clusters - market correlations crossing sector boundaries"
        )
    
    if current_regime['regime'] == 'risk_off':
        results['recommendations'].append(
            f"REGIME: Market is in RISK-OFF mode (confidence: {current_regime['confidence']:.0%}) - "
            "positive event impacts may be muted"
        )
    else:
        results['recommendations'].append(
            f"REGIME: Market is in RISK-ON mode (confidence: {current_regime['confidence']:.0%}) - "
            "events should drive expected price movements"
        )
    
    if backtest_results.get('improvement', 0) > 0:
        results['recommendations'].append(
            f"VALIDATION: Topology features improved prediction accuracy by {backtest_results['improvement']:.1%} - "
            "recommend integration with Market Echo Engine"
        )
    else:
        results['recommendations'].append(
            "VALIDATION: Topology features did not improve accuracy in this sample - "
            "may need more events or refined methodology"
        )
    
    print()
    for i, rec in enumerate(results['recommendations'], 1):
        print(f"{i}. {rec}")
    print()
    
    return results


# ============================================================================
# VISUALIZATION (Text-based for POC)
# ============================================================================

def print_correlation_heatmap(corr_matrix: pd.DataFrame, n_show: int = 10):
    """Print a text-based correlation summary."""
    print("\nTop Correlations:")
    
    # Get upper triangle of correlation matrix
    corr_pairs = []
    for i, ticker1 in enumerate(corr_matrix.columns):
        for j, ticker2 in enumerate(corr_matrix.columns):
            if i < j:
                corr_pairs.append((ticker1, ticker2, corr_matrix.iloc[i, j]))
    
    # Sort by absolute correlation
    corr_pairs.sort(key=lambda x: abs(x[2]), reverse=True)
    
    for ticker1, ticker2, corr in corr_pairs[:n_show]:
        bar = '█' * int(abs(corr) * 20)
        sign = '+' if corr > 0 else '-'
        print(f"  {ticker1:5} ↔ {ticker2:5}: {sign}{abs(corr):.3f} {bar}")


if __name__ == "__main__":
    results = run_topology_research()
    
    # Save results to JSON
    output_file = "topology_research_results.json"
    with open(output_file, 'w') as f:
        # Convert non-serializable objects
        def convert(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, (np.int64, np.int32)):
                return int(obj)
            if isinstance(obj, (np.float64, np.float32)):
                return float(obj)
            if hasattr(obj, 'isoformat'):
                return obj.isoformat()
            return str(obj)
        
        json.dump(results, f, indent=2, default=convert)
    
    print(f"\nResults saved to {output_file}")
    print("=" * 70)
