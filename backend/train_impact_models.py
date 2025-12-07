#!/usr/bin/env python3
"""
Training script for probabilistic impact scoring models.

This script:
1. Fetches all historical events from the database
2. Computes abnormal returns for each event
3. Groups events by (event_type, sector, cap_bucket)
4. Calculates statistical priors (mu, sigma, n) for each group
5. Writes/upserts priors to event_group_priors table
6. Optionally rescores all events using new priors
7. Prints summary statistics

Usage:
    python train_impact_models.py [--rescore] [--min-events N]
"""

import sys
import argparse
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import pandas as pd
import numpy as np

# Database imports
from releaseradar.db.session import get_db, close_db_session
from releaseradar.db.models import Event, EventGroupPrior

# Impact models imports
from impact_models.definitions import DEFAULT_IMPACT_TARGET
from impact_models.prices import get_window_returns
from impact_models.event_study import make_group_key
from impact_scoring import score_event_probabilistic


def determine_cap_bucket(ticker: str) -> str:
    """
    Determine market cap bucket for a ticker.
    
    In production, this would query market data.
    For now, use simple heuristics based on ticker patterns.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Market cap bucket: "small", "mid", or "large"
    """
    # Simple heuristic: assume well-known tickers are large cap
    large_cap_tickers = {
        'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'META', 'TSLA', 'NVDA',
        'JPM', 'JNJ', 'V', 'PG', 'UNH', 'HD', 'MA', 'DIS', 'PYPL', 'NFLX',
        'ADBE', 'CRM', 'INTC', 'CSCO', 'PFE', 'ABT', 'TMO', 'NKE', 'CVX',
        'WMT', 'VZ', 'KO', 'PEP', 'MRK', 'T', 'XOM', 'BA', 'IBM', 'ORCL'
    }
    
    if ticker in large_cap_tickers:
        return "large"
    
    # Default to mid for most others
    # In production, fetch actual market cap from financial data API
    return "mid"


def fetch_historical_events(db, limit: Optional[int] = None) -> List[Event]:
    """
    Fetch all historical events from database.
    
    Args:
        db: Database session
        limit: Optional limit on number of events to fetch
        
    Returns:
        List of Event objects
    """
    query = db.query(Event).filter(
        Event.event_type.isnot(None),
        Event.ticker.isnot(None),
        Event.sector.isnot(None)
    ).order_by(Event.date.asc())
    
    if limit:
        query = query.limit(limit)
    
    return query.all()


def compute_event_returns(
    events: List[Event],
    benchmark: str,
    horizon_days: int
) -> List[Tuple[Event, Optional[float]]]:
    """
    Compute abnormal returns for a list of events.
    
    Args:
        events: List of Event objects
        benchmark: Benchmark ticker (e.g., "SPY")
        horizon_days: Horizon for return calculation
        
    Returns:
        List of (event, abnormal_return) tuples
    """
    results = []
    
    print(f"\nComputing abnormal returns for {len(events)} events...")
    print(f"Benchmark: {benchmark}, Horizon: {horizon_days} day(s)")
    
    for i, event in enumerate(events):
        if i % 100 == 0 and i > 0:
            print(f"  Processed {i}/{len(events)} events...")
        
        try:
            event_date = pd.Timestamp(event.date)
            abnormal_return = get_window_returns(
                ticker=event.ticker,
                benchmark=benchmark,
                event_date=event_date,
                horizon_days=horizon_days
            )
            results.append((event, abnormal_return))
        except Exception as e:
            print(f"  Warning: Failed to compute returns for {event.ticker} on {event.date}: {e}")
            results.append((event, None))
    
    print(f"  Completed! {len(results)} events processed.")
    
    return results


def group_and_aggregate(
    event_returns: List[Tuple[Event, Optional[float]]],
    min_events: int = 5
) -> Dict[Tuple[str, str, str], Dict]:
    """
    Group events by (event_type, sector, cap_bucket) and compute statistics.
    
    Args:
        event_returns: List of (event, abnormal_return) tuples
        min_events: Minimum number of events required for a group
        
    Returns:
        Dictionary mapping group_key -> {mu, sigma, n, event_type, sector, cap_bucket}
    """
    print(f"\nGrouping events and computing statistics (min_events={min_events})...")
    
    # Collect returns by group
    groups = defaultdict(list)
    
    for event, abnormal_return in event_returns:
        if abnormal_return is None:
            continue
        
        cap_bucket = determine_cap_bucket(event.ticker)
        group_key = make_group_key(event.event_type, event.sector, cap_bucket)
        groups[group_key].append(abnormal_return)
    
    # Compute statistics for each group
    priors = {}
    
    for group_key, returns in groups.items():
        n = len(returns)
        
        if n < min_events:
            continue
        
        event_type, sector, cap_bucket = group_key
        
        # Compute statistics
        mu = float(np.mean(returns))
        sigma = float(np.std(returns, ddof=1))
        
        priors[group_key] = {
            "event_type": event_type,
            "sector": sector,
            "cap_bucket": cap_bucket,
            "mu": mu,
            "sigma": sigma,
            "n": n
        }
    
    print(f"  Found {len(priors)} groups with >= {min_events} events")
    
    return priors


def write_priors_to_db(db, priors: Dict[Tuple[str, str, str], Dict]) -> int:
    """
    Write/upsert priors to event_group_priors table.
    
    Args:
        db: Database session
        priors: Dictionary of group priors
        
    Returns:
        Number of priors written
    """
    print(f"\nWriting {len(priors)} priors to database...")
    
    count = 0
    
    for group_key, stats in priors.items():
        event_type, sector, cap_bucket = group_key
        
        # Check if prior exists
        existing = db.query(EventGroupPrior).filter(
            EventGroupPrior.event_type == event_type,
            EventGroupPrior.sector == sector,
            EventGroupPrior.cap_bucket == cap_bucket
        ).first()
        
        if existing:
            # Update existing
            existing.mu = stats["mu"]
            existing.sigma = stats["sigma"]
            existing.n = stats["n"]
            existing.updated_at = datetime.utcnow()
        else:
            # Create new
            new_prior = EventGroupPrior(
                event_type=event_type,
                sector=sector,
                cap_bucket=cap_bucket,
                mu=stats["mu"],
                sigma=stats["sigma"],
                n=stats["n"]
            )
            db.add(new_prior)
        
        count += 1
    
    db.commit()
    print(f"  Wrote {count} priors to database")
    
    return count


def rescore_events(db, limit: Optional[int] = None) -> int:
    """
    Rescore all events using new probabilistic priors.
    
    Args:
        db: Database session
        limit: Optional limit on number of events to rescore
        
    Returns:
        Number of events rescored
    """
    print("\nRescoring events with probabilistic model...")
    
    # Fetch all priors
    priors_dict = {}
    priors = db.query(EventGroupPrior).all()
    
    for prior in priors:
        key = make_group_key(prior.event_type, prior.sector, prior.cap_bucket)
        priors_dict[key] = prior
    
    print(f"  Loaded {len(priors_dict)} priors from database")
    
    # Fetch events to rescore
    query = db.query(Event).filter(
        Event.event_type.isnot(None),
        Event.sector.isnot(None)
    )
    
    if limit:
        query = query.limit(limit)
    
    events = query.all()
    print(f"  Rescoring {len(events)} events...")
    
    rescored_count = 0
    
    for i, event in enumerate(events):
        if i % 100 == 0 and i > 0:
            print(f"    Processed {i}/{len(events)} events...")
        
        cap_bucket = determine_cap_bucket(event.ticker)
        group_key = make_group_key(event.event_type, event.sector, cap_bucket)
        
        prior = priors_dict.get(group_key)
        
        if not prior:
            # No prior found, use fallback or skip
            continue
        
        # Score event probabilistically
        score_result = score_event_probabilistic(
            event_type=event.event_type,
            sector=event.sector,
            cap_bucket=cap_bucket,
            prior_mu=prior.mu,
            prior_sigma=prior.sigma,
            prior_n=prior.n
        )
        
        # Update event with new scores
        event.impact_score = score_result["impact_score"]
        event.direction = score_result["direction"]
        event.confidence = score_result["confidence"] / 100.0  # Store as 0-1
        event.rationale = score_result["rationale"]
        event.impact_p_move = score_result["p_move"]
        event.impact_p_up = score_result["p_up"]
        event.impact_p_down = score_result["p_down"]
        event.impact_score_version = 2  # Mark as probabilistic scoring
        
        rescored_count += 1
    
    db.commit()
    print(f"  Rescored {rescored_count} events")
    
    return rescored_count


def print_summary(priors: Dict[Tuple[str, str, str], Dict]):
    """
    Print summary statistics of computed priors.
    
    Args:
        priors: Dictionary of group priors
    """
    print("\n" + "="*80)
    print("TRAINING SUMMARY")
    print("="*80)
    
    print(f"\nTotal groups: {len(priors)}")
    
    if not priors:
        print("No priors computed.")
        return
    
    # Statistics by event type
    event_types = defaultdict(list)
    for group_key, stats in priors.items():
        event_types[stats["event_type"]].append(stats)
    
    print(f"\nGroups by event type:")
    for event_type, groups in sorted(event_types.items()):
        total_events = sum(g["n"] for g in groups)
        print(f"  {event_type}: {len(groups)} groups, {total_events} total events")
    
    # Show top 10 groups by sample size
    print(f"\nTop 10 groups by sample size:")
    sorted_priors = sorted(priors.items(), key=lambda x: x[1]["n"], reverse=True)
    
    for i, (group_key, stats) in enumerate(sorted_priors[:10], 1):
        print(f"  {i}. {stats['event_type']} / {stats['sector']} / {stats['cap_bucket']}")
        print(f"     n={stats['n']}, μ={stats['mu']:.2f}%, σ={stats['sigma']:.2f}%")
    
    # Overall statistics
    all_mus = [s["mu"] for s in priors.values()]
    all_sigmas = [s["sigma"] for s in priors.values()]
    all_ns = [s["n"] for s in priors.values()]
    
    print(f"\nOverall statistics:")
    print(f"  Mean μ: {np.mean(all_mus):.2f}% (range: {np.min(all_mus):.2f}% to {np.max(all_mus):.2f}%)")
    print(f"  Mean σ: {np.mean(all_sigmas):.2f}% (range: {np.min(all_sigmas):.2f}% to {np.max(all_sigmas):.2f}%)")
    print(f"  Mean n: {np.mean(all_ns):.1f} (range: {np.min(all_ns)} to {np.max(all_ns)})")
    
    print("\n" + "="*80)


def main():
    """Main training function."""
    parser = argparse.ArgumentParser(
        description="Train probabilistic impact scoring models from historical events"
    )
    parser.add_argument(
        "--rescore",
        action="store_true",
        help="Rescore all events after training"
    )
    parser.add_argument(
        "--min-events",
        type=int,
        default=5,
        help="Minimum number of events required for a group (default: 5)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of events to process (for testing)"
    )
    
    args = parser.parse_args()
    
    print("="*80)
    print("PROBABILISTIC IMPACT SCORING MODEL TRAINING")
    print("="*80)
    print(f"\nConfiguration:")
    print(f"  Benchmark: {DEFAULT_IMPACT_TARGET.benchmark}")
    print(f"  Horizon: {DEFAULT_IMPACT_TARGET.horizon_days} day(s)")
    print(f"  Threshold: {DEFAULT_IMPACT_TARGET.threshold_pct}%")
    print(f"  Min events per group: {args.min_events}")
    if args.limit:
        print(f"  Event limit: {args.limit}")
    
    db = get_db()
    
    try:
        # Step 1: Fetch historical events
        print("\n" + "-"*80)
        print("STEP 1: Fetching historical events")
        print("-"*80)
        events = fetch_historical_events(db, limit=args.limit)
        print(f"Fetched {len(events)} historical events")
        
        if not events:
            print("No events found. Exiting.")
            return
        
        # Step 2: Compute abnormal returns
        print("\n" + "-"*80)
        print("STEP 2: Computing abnormal returns")
        print("-"*80)
        event_returns = compute_event_returns(
            events,
            DEFAULT_IMPACT_TARGET.benchmark,
            DEFAULT_IMPACT_TARGET.horizon_days
        )
        
        valid_returns = sum(1 for _, r in event_returns if r is not None)
        print(f"Computed returns for {valid_returns}/{len(events)} events")
        
        # Step 3: Group and aggregate
        print("\n" + "-"*80)
        print("STEP 3: Grouping and computing statistics")
        print("-"*80)
        priors = group_and_aggregate(event_returns, min_events=args.min_events)
        
        if not priors:
            print("No groups met minimum event threshold. Exiting.")
            return
        
        # Step 4: Write to database
        print("\n" + "-"*80)
        print("STEP 4: Writing priors to database")
        print("-"*80)
        write_priors_to_db(db, priors)
        
        # Step 5: Print summary
        print_summary(priors)
        
        # Step 6: Optionally rescore events
        if args.rescore:
            print("\n" + "-"*80)
            print("STEP 5: Rescoring events")
            print("-"*80)
            rescore_events(db, limit=args.limit)
        
        print("\nTraining completed successfully!")
        
    except Exception as e:
        print(f"\nError during training: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        sys.exit(1)
    
    finally:
        close_db_session(db)


if __name__ == "__main__":
    main()
