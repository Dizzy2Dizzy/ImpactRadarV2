#!/usr/bin/env python3
"""
CLI tool for manual event outcome labeling.

This tool allows manual control over the ML learning pipeline,
supporting selective labeling by event family, horizons, and limits.

Usage Examples:
    # Label all events from the last 30 days
    python -m backend.tools.label_events --since 2024-10-01

    # Label specific event families
    python -m backend.tools.label_events --families sec_8k,earnings,fda

    # Label specific horizons only
    python -m backend.tools.label_events --horizons 1d,5d

    # Dry run (no database writes)
    python -m backend.tools.label_events --dry-run

    # Limit number of events processed
    python -m backend.tools.label_events --limit 100

    # Label all historical events (use with caution!)
    python -m backend.tools.label_events --label-all
"""

import argparse
import os
import sys
from datetime import datetime, timedelta, date
from typing import List, Optional, Set
from collections import defaultdict

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from backend.releaseradar.ml.pipelines.label_outcomes import OutcomeLabeler
from backend.releaseradar.ml.event_type_families import get_event_family, EVENT_TYPE_FAMILIES
from backend.releaseradar.db.session import get_db_transaction
from backend.releaseradar.db.models import Event, EventOutcome
from backend.releaseradar.logging import logger
from sqlalchemy import select


def get_event_types_for_families(families: List[str]) -> List[str]:
    """
    Convert event family names to list of event types.
    
    Args:
        families: List of family names (e.g., ["sec_8k", "earnings"])
        
    Returns:
        List of event type strings
    """
    event_types = []
    for family in families:
        if family in EVENT_TYPE_FAMILIES:
            event_types.extend(EVENT_TYPE_FAMILIES[family])
        else:
            logger.warning(f"Unknown event family: {family}")
    
    return event_types


def filter_events_by_horizon_age(
    events: List[Event],
    horizons: List[str],
    today: date
) -> List[Event]:
    """
    Filter events to only include those old enough for the requested horizons.
    
    For example, if requesting 20d horizon, event must be at least 21 days old
    to allow for proper price data availability.
    
    Args:
        events: List of events to filter
        horizons: Horizons being labeled (e.g., ["1d", "5d", "20d"])
        today: Current date for age calculation
        
    Returns:
        Filtered list of events
    """
    # Determine minimum age required
    horizon_to_days = {"1d": 1, "5d": 5, "20d": 20}
    
    # Add buffer days for weekends/holidays (trading days vs calendar days)
    # For 1d we need 3 calendar days, 5d needs 10, 20d needs 30
    horizon_to_min_age = {
        "1d": 3,   # 1 trading day + 2 day buffer
        "5d": 10,  # 5 trading days + 5 day buffer
        "20d": 30  # 20 trading days + 10 day buffer
    }
    
    max_horizon_in_list = max(horizons, key=lambda h: horizon_to_days[h])
    min_age_days = horizon_to_min_age[max_horizon_in_list]
    
    cutoff_date = today - timedelta(days=min_age_days)
    
    filtered = [e for e in events if e.date.date() <= cutoff_date]
    
    skipped_count = len(events) - len(filtered)
    if skipped_count > 0:
        logger.info(f"Filtered out {skipped_count} events that are too recent for {max_horizon_in_list} horizon "
                   f"(need events older than {cutoff_date})")
    
    return filtered


def label_events_with_filters(
    families: Optional[List[str]] = None,
    horizons: Optional[List[str]] = None,
    since: Optional[date] = None,
    until: Optional[date] = None,
    limit: Optional[int] = None,
    dry_run: bool = False,
    label_all: bool = False,
) -> dict:
    """
    Label event outcomes with comprehensive filtering options.
    
    Args:
        families: Event families to label (e.g., ["sec_8k", "earnings"])
        horizons: Time horizons to label (e.g., ["1d", "5d"])
        since: Start date for events to label
        until: End date for events to label
        limit: Maximum number of events to process
        dry_run: If True, don't write to database
        label_all: If True, label all historical events (ignores date filters)
        
    Returns:
        Statistics dictionary with detailed breakdown
    """
    # Validate and set defaults
    if horizons is None:
        horizons = ["1d", "5d", "20d"]
    else:
        valid_horizons = {"1d", "5d", "20d"}
        invalid = [h for h in horizons if h not in valid_horizons]
        if invalid:
            raise ValueError(f"Invalid horizons: {invalid}. Must be one of {valid_horizons}")
    
    # Get event types from families
    event_types_filter = None
    if families:
        event_types_filter = get_event_types_for_families(families)
        if not event_types_filter:
            logger.warning("No valid event types found for specified families")
            return {"events_processed": 0, "outcomes_created": 0, "errors": 0}
    
    logger.info("="*80)
    logger.info("Event Outcome Labeling Tool")
    logger.info("="*80)
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    logger.info(f"Families: {families or 'ALL'}")
    logger.info(f"Horizons: {horizons}")
    logger.info(f"Date range: {since or 'unlimited'} to {until or 'today'}")
    logger.info(f"Limit: {limit or 'unlimited'}")
    logger.info("")
    
    with get_db_transaction() as db:
        # Build query
        today = datetime.utcnow().date()
        
        if label_all:
            query = select(Event)
            logger.info("Labeling ALL historical events (label_all=True)")
        elif since:
            query = select(Event).where(Event.date >= since)
            logger.info(f"Labeling events since {since}")
        else:
            # Default: last 60 days
            cutoff = today - timedelta(days=60)
            query = select(Event).where(Event.date >= cutoff)
            logger.info(f"Labeling events from last 60 days ({cutoff})")
        
        if until:
            query = query.where(Event.date <= until)
        
        if event_types_filter:
            query = query.where(Event.event_type.in_(event_types_filter))
        
        # Order by date ascending (oldest first)
        query = query.order_by(Event.date.asc())
        
        # Fetch events
        all_events = db.execute(query).scalars().all()
        
        logger.info(f"Found {len(all_events)} events matching filters")
        
        # Filter by horizon age requirements
        events = filter_events_by_horizon_age(all_events, horizons, today)
        
        # Apply limit
        if limit and len(events) > limit:
            logger.info(f"Limiting to first {limit} events (out of {len(events)})")
            events = events[:limit]
        
        # Group events by family for logging
        events_by_family = defaultdict(list)
        for event in events:
            family = get_event_family(event.event_type)
            events_by_family[family].append(event)
        
        logger.info(f"Events by family: {dict((k, len(v)) for k, v in events_by_family.items())}")
        logger.info("")
        
        # Statistics tracking
        stats = {
            "events_processed": 0,
            "outcomes_created": 0,
            "outcomes_updated": 0,
            "outcomes_skipped": 0,
            "errors": 0,
            "by_family": defaultdict(lambda: {
                "processed": 0,
                "created": 0,
                "updated": 0,
                "skipped": 0
            }),
            "by_horizon": defaultdict(lambda: {
                "created": 0,
                "updated": 0,
                "skipped": 0
            }),
        }
        
        # Initialize labeler
        labeler = OutcomeLabeler()
        
        # Process events
        for idx, event in enumerate(events):
            try:
                stats["events_processed"] += 1
                family = get_event_family(event.event_type)
                stats["by_family"][family]["processed"] += 1
                
                # Log progress every 10 events
                if (idx + 1) % 10 == 0:
                    logger.info(f"Progress: {idx + 1}/{len(events)} events processed "
                               f"({stats['outcomes_created']} created, "
                               f"{stats['outcomes_updated']} updated, "
                               f"{stats['outcomes_skipped']} skipped)")
                
                # Label for each requested horizon
                for horizon in horizons:
                    # Check if outcome already exists
                    existing = db.execute(
                        select(EventOutcome)
                        .where(EventOutcome.event_id == event.id)
                        .where(EventOutcome.horizon == horizon)
                    ).scalar_one_or_none()
                    
                    if existing:
                        # Update existing outcome (in case price data improved)
                        outcome_data = labeler.label_event_outcome(db, event, horizon, today)
                        
                        if outcome_data is None:
                            stats["outcomes_skipped"] += 1
                            stats["by_family"][family]["skipped"] += 1
                            stats["by_horizon"][horizon]["skipped"] += 1
                            continue
                        
                        if not dry_run:
                            # Update existing record
                            existing.price_before = outcome_data["price_before"]
                            existing.price_after = outcome_data["price_after"]
                            existing.return_pct_raw = outcome_data["return_pct_raw"]
                            existing.benchmark_return_pct = outcome_data["benchmark_return_pct"]
                            existing.return_pct = outcome_data["return_pct"]
                            existing.abs_return_pct = outcome_data["abs_return_pct"]
                            existing.direction_correct = outcome_data["direction_correct"]
                            existing.has_benchmark_data = outcome_data["has_benchmark_data"]
                            existing.label_date = outcome_data["label_date"]
                        
                        stats["outcomes_updated"] += 1
                        stats["by_family"][family]["updated"] += 1
                        stats["by_horizon"][horizon]["updated"] += 1
                    else:
                        # Create new outcome
                        outcome_data = labeler.label_event_outcome(db, event, horizon, today)
                        
                        if outcome_data is None:
                            stats["outcomes_skipped"] += 1
                            stats["by_family"][family]["skipped"] += 1
                            stats["by_horizon"][horizon]["skipped"] += 1
                            continue
                        
                        if not dry_run:
                            # Insert new record
                            new_outcome = EventOutcome(**outcome_data)
                            db.add(new_outcome)
                        
                        stats["outcomes_created"] += 1
                        stats["by_family"][family]["created"] += 1
                        stats["by_horizon"][horizon]["created"] += 1
                
                # Commit every 50 events (if not dry run)
                if not dry_run and stats["events_processed"] % 50 == 0:
                    db.commit()
            
            except Exception as e:
                logger.error(f"Error labeling event {event.id} ({event.ticker}/{event.event_type}): {e}")
                stats["errors"] += 1
                if not dry_run:
                    db.rollback()
                continue
        
        # Final commit (if not dry run)
        if not dry_run:
            db.commit()
        else:
            logger.info("DRY RUN - No changes written to database")
        
        # Convert defaultdicts to regular dicts for JSON serialization
        stats["by_family"] = dict(stats["by_family"])
        stats["by_horizon"] = dict(stats["by_horizon"])
        
        # Print summary
        logger.info("")
        logger.info("="*80)
        logger.info("LABELING COMPLETE")
        logger.info("="*80)
        logger.info(f"Events processed: {stats['events_processed']}")
        logger.info(f"Outcomes created: {stats['outcomes_created']}")
        logger.info(f"Outcomes updated: {stats['outcomes_updated']}")
        logger.info(f"Outcomes skipped: {stats['outcomes_skipped']}")
        logger.info(f"Errors: {stats['errors']}")
        logger.info("")
        
        logger.info("Breakdown by Event Family:")
        for family, family_stats in sorted(stats["by_family"].items()):
            logger.info(f"  {family:15s}: processed={family_stats['processed']:4d}, "
                       f"created={family_stats['created']:4d}, "
                       f"updated={family_stats['updated']:4d}, "
                       f"skipped={family_stats['skipped']:4d}")
        
        logger.info("")
        logger.info("Breakdown by Horizon:")
        for horizon, horizon_stats in sorted(stats["by_horizon"].items()):
            logger.info(f"  {horizon:4s}: created={horizon_stats['created']:4d}, "
                       f"updated={horizon_stats['updated']:4d}, "
                       f"skipped={horizon_stats['skipped']:4d}")
        
        return stats


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Label event outcomes with price data for ML training",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Label events from last 30 days
  python -m backend.tools.label_events --since 2024-11-01

  # Label specific families only
  python -m backend.tools.label_events --families sec_8k,earnings

  # Label specific horizons only
  python -m backend.tools.label_events --horizons 1d,5d

  # Dry run (preview without writing)
  python -m backend.tools.label_events --dry-run --limit 10

  # Label ALL historical events (use with caution!)
  python -m backend.tools.label_events --label-all

Available event families:
  sec_8k, earnings, fda, mergers_acquisitions, guidance, dividends, analyst_ratings
        """,
    )
    
    parser.add_argument(
        "--families",
        type=str,
        help="Comma-separated list of event families to label (e.g., 'sec_8k,earnings,fda')",
    )
    
    parser.add_argument(
        "--horizons",
        type=str,
        help="Comma-separated list of horizons to label (default: '1d,5d,20d'). Options: 1d, 5d, 20d",
    )
    
    parser.add_argument(
        "--since",
        type=str,
        help="Start date for events to label (format: YYYY-MM-DD). Default: 60 days ago",
    )
    
    parser.add_argument(
        "--until",
        type=str,
        help="End date for events to label (format: YYYY-MM-DD). Default: today",
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of events to process (useful for testing)",
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be labeled without writing to database",
    )
    
    parser.add_argument(
        "--label-all",
        action="store_true",
        help="Label ALL historical events (ignores --since). Use with caution!",
    )
    
    args = parser.parse_args()
    
    # Parse arguments
    families = args.families.split(",") if args.families else None
    horizons = args.horizons.split(",") if args.horizons else None
    
    since = datetime.strptime(args.since, "%Y-%m-%d").date() if args.since else None
    until = datetime.strptime(args.until, "%Y-%m-%d").date() if args.until else None
    
    # Validate families
    if families:
        valid_families = set(EVENT_TYPE_FAMILIES.keys())
        invalid_families = [f for f in families if f not in valid_families]
        if invalid_families:
            logger.error(f"Invalid event families: {invalid_families}")
            logger.error(f"Valid families: {sorted(valid_families)}")
            sys.exit(1)
    
    try:
        stats = label_events_with_filters(
            families=families,
            horizons=horizons,
            since=since,
            until=until,
            limit=args.limit,
            dry_run=args.dry_run,
            label_all=args.label_all,
        )
        
        if stats["errors"] > 0:
            logger.warning(f"Completed with {stats['errors']} errors")
            sys.exit(1)
        else:
            logger.info("✅ Labeling completed successfully")
            sys.exit(0)
    
    except Exception as e:
        logger.error(f"Labeling failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
