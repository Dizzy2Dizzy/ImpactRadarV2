"""
Backfill ML Scores Job - Manual backfill script for ML scoring.

This standalone CLI script applies ML scores to events that:
- Have no ML scores (ml_adjusted_score IS NULL)
- Have outdated model versions

Usage:
    python3 backend/jobs/backfill_ml_scores.py
    python3 backend/jobs/backfill_ml_scores.py --limit 500
    python3 backend/jobs/backfill_ml_scores.py --families sec_8k,earnings --horizons 1d,5d --since 2024-01-01
    python3 backend/jobs/backfill_ml_scores.py --dry-run

Arguments:
    --families: Comma-separated list of event families to process (default: all)
    --horizons: Comma-separated list of horizons to use (default: 1d)
    --since: Only process events since this date (YYYY-MM-DD format)
    --batch-size: Number of events to commit per batch (default: 50)
    --limit: Maximum number of events to process (default: unlimited)
    --dry-run: Preview changes without committing to database
"""

import argparse
import os
import sys
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Set

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select, or_

from releaseradar.db.models import Event, ModelRegistry
from releaseradar.db.session import get_db_transaction
from releaseradar.ml.serving import MLScoringService
from releaseradar.ml.event_type_families import (
    get_event_family,
    EVENT_TYPE_FAMILIES,
    get_family_display_name,
)
from releaseradar.log_config import logger


def parse_date(date_str: str) -> datetime:
    """Parse date string in YYYY-MM-DD format."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: {date_str}. Use YYYY-MM-DD")


def get_active_model_versions(db, horizons: List[str]) -> Dict[str, Optional[str]]:
    """Get current active model versions for each horizon."""
    active_versions = {}
    for horizon in horizons:
        model = db.execute(
            select(ModelRegistry)
            .where(ModelRegistry.status == "active")
            .where(ModelRegistry.horizon == horizon)
            .order_by(ModelRegistry.promoted_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        
        if model:
            active_versions[horizon] = f"{model.name}:{model.version}"
            logger.info(f"Active model for {horizon}: {active_versions[horizon]}")
        else:
            active_versions[horizon] = None
            logger.warning(f"No active model found for {horizon} horizon")
    
    return active_versions


def build_events_query(
    since: Optional[datetime],
    families: Optional[List[str]],
    active_model_versions: Dict[str, Optional[str]]
):
    """
    Build SQLAlchemy query for events needing ML scores.
    
    Selects events that:
    - Have NULL ml_adjusted_score OR
    - Have outdated ml_model_version
    """
    query = select(Event)
    
    if since:
        query = query.where(Event.date >= since)
    
    active_versions = [v for v in active_model_versions.values() if v]
    
    query = query.where(
        or_(
            Event.ml_adjusted_score.is_(None),
            Event.ml_model_version.is_(None),
            ~Event.ml_model_version.in_(active_versions) if active_versions else True
        )
    )
    
    query = query.order_by(Event.date.desc())
    
    return query


def filter_events_by_family(
    events: List[Event],
    families: Optional[List[str]]
) -> List[Event]:
    """Filter events by family if specified."""
    if not families or "all" in families:
        return events
    
    families_set = set(families)
    return [e for e in events if get_event_family(e.event_type) in families_set]


def backfill_ml_scores(
    families: Optional[List[str]] = None,
    horizons: Optional[List[str]] = None,
    since: Optional[datetime] = None,
    batch_size: int = 50,
    dry_run: bool = False,
    limit: Optional[int] = None,
) -> Dict:
    """
    Backfill ML scores for events.
    
    Args:
        families: List of event families to process (None = all)
        horizons: List of horizons to predict (default: ["1d"])
        since: Only process events since this date
        batch_size: Number of events to commit per batch (default: 50)
        dry_run: If True, don't commit changes
        limit: Maximum total events to process (None = all)
        
    Returns:
        Statistics dict with processing results
    """
    if horizons is None:
        horizons = ["1d"]  # Default to 1d only for faster processing
    
    stats = {
        "started_at": datetime.utcnow().isoformat(),
        "parameters": {
            "families": families or ["all"],
            "horizons": horizons,
            "since": since.isoformat() if since else None,
            "batch_size": batch_size,
            "dry_run": dry_run,
        },
        "total_processed": 0,
        "total_updated": 0,
        "total_skipped": 0,
        "by_family": defaultdict(lambda: {"processed": 0, "updated": 0, "skipped": 0}),
        "by_horizon": defaultdict(lambda: {"processed": 0, "updated": 0, "skipped": 0}),
        "success": False,
    }
    
    print(f"\n{'='*80}")
    print("ML Score Backfill Job")
    print(f"{'='*80}")
    print(f"  Families: {', '.join(families) if families else 'all'}")
    print(f"  Horizons: {', '.join(horizons)}")
    print(f"  Since: {since.strftime('%Y-%m-%d') if since else 'all time'}")
    print(f"  Batch size: {batch_size}")
    print(f"  Dry run: {dry_run}")
    print(f"{'='*80}\n")
    
    with get_db_transaction() as db:
        active_model_versions = get_active_model_versions(db, horizons)
        
        if not any(active_model_versions.values()):
            print("❌ No active models found. Aborting backfill.")
            stats["success"] = False
            stats["error"] = "No active models found"
            stats["finished_at"] = datetime.utcnow().isoformat()
            return stats
        
        query = build_events_query(since, families, active_model_versions)
        events = list(db.execute(query).scalars().all())
        
        events = filter_events_by_family(events, families)
        
        # Apply limit if specified
        if limit and len(events) > limit:
            events = events[:limit]
            print(f"🔢 Limited to {limit} events (out of {len(events) + limit} total)")
        
        total_events = len(events)
        
        print(f"📊 Found {total_events} events needing ML scores\n")
        
        if total_events == 0:
            print("✅ No events need ML scoring")
            stats["success"] = True
            stats["finished_at"] = datetime.utcnow().isoformat()
            return stats
        
        scoring_service = MLScoringService(db)
        
        batch_count = 0
        for i in range(0, total_events, batch_size):
            batch = events[i:i + batch_size]
            batch_count += 1
            batch_updated = 0
            batch_skipped = 0
            
            print(f"Processing batch {batch_count} ({len(batch)} events, {i+1}-{min(i+len(batch), total_events)} of {total_events})...")
            
            for event in batch:
                event_family = get_event_family(event.event_type)
                stats["total_processed"] += 1
                stats["by_family"][event_family]["processed"] += 1
                
                best_prediction = None
                best_horizon = None
                
                for horizon in horizons:
                    if not active_model_versions.get(horizon):
                        continue
                    
                    stats["by_horizon"][horizon]["processed"] += 1
                    
                    try:
                        prediction = scoring_service.predict_single(
                            event_id=event.id,
                            horizon=horizon,
                            confidence_threshold=0.3,
                            max_delta=20,
                            use_blending=True
                        )
                        
                        if prediction:
                            if best_prediction is None or prediction.ml_confidence > best_prediction.ml_confidence:
                                best_prediction = prediction
                                best_horizon = horizon
                            
                            stats["by_horizon"][horizon]["updated"] += 1
                        else:
                            stats["by_horizon"][horizon]["skipped"] += 1
                    
                    except Exception as e:
                        logger.warning(f"Error predicting event {event.id} for {horizon}: {e}")
                        stats["by_horizon"][horizon]["skipped"] += 1
                
                if best_prediction:
                    if not dry_run:
                        event.ml_adjusted_score = best_prediction.ml_adjusted_score
                        event.ml_confidence = best_prediction.ml_confidence
                        event.ml_model_version = best_prediction.ml_model_version
                        event.model_source = best_prediction.model_source
                        event.delta_applied = best_prediction.delta_applied
                    
                    stats["total_updated"] += 1
                    stats["by_family"][event_family]["updated"] += 1
                    batch_updated += 1
                else:
                    stats["total_skipped"] += 1
                    stats["by_family"][event_family]["skipped"] += 1
                    batch_skipped += 1
            
            if not dry_run:
                try:
                    db.commit()
                    print(f"  ✓ Batch {batch_count} committed: {batch_updated} updated, {batch_skipped} skipped")
                except Exception as e:
                    logger.error(f"Error committing batch {batch_count}: {e}")
                    db.rollback()
                    print(f"  ✗ Batch {batch_count} failed: {e}")
            else:
                print(f"  [DRY RUN] Batch {batch_count}: {batch_updated} would be updated, {batch_skipped} skipped")
    
    stats["by_family"] = dict(stats["by_family"])
    stats["by_horizon"] = dict(stats["by_horizon"])
    stats["success"] = True
    stats["finished_at"] = datetime.utcnow().isoformat()
    
    print(f"\n{'='*80}")
    print("📊 Backfill Summary")
    print(f"{'='*80}")
    print(f"\n  Total Events Processed: {stats['total_processed']}")
    print(f"  Total Updated: {stats['total_updated']}")
    print(f"  Total Skipped: {stats['total_skipped']}")
    
    if stats["by_family"]:
        print(f"\n  By Event Family:")
        for family, family_stats in sorted(stats["by_family"].items()):
            display_name = get_family_display_name(family)
            print(f"    {display_name}: processed={family_stats['processed']}, updated={family_stats['updated']}, skipped={family_stats['skipped']}")
    
    if stats["by_horizon"]:
        print(f"\n  By Horizon:")
        for horizon, horizon_stats in sorted(stats["by_horizon"].items()):
            print(f"    {horizon}: processed={horizon_stats['processed']}, updated={horizon_stats['updated']}, skipped={horizon_stats['skipped']}")
    
    print(f"\n{'='*80}")
    if dry_run:
        print("🔍 DRY RUN COMPLETE - No changes were committed")
    else:
        print(f"✅ Backfill Complete: {stats['total_updated']}/{stats['total_processed']} events updated")
    print(f"{'='*80}\n")
    
    return stats


def main():
    """Main entry point for CLI execution."""
    parser = argparse.ArgumentParser(
        description="Backfill ML scores for events",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 backend/jobs/backfill_ml_scores.py --batch-size 500
  python3 backend/jobs/backfill_ml_scores.py --families sec_8k,earnings --horizons 1d
  python3 backend/jobs/backfill_ml_scores.py --since 2024-01-01 --dry-run
  python3 backend/jobs/backfill_ml_scores.py --families all --batch-size 200

Available families:
  sec_8k, sec_10q, sec_10k, earnings, fda, mna, 
  capital_allocation, product_business, guidance, sec_other
        """
    )
    
    parser.add_argument(
        "--families",
        type=str,
        default="all",
        help="Comma-separated list of event families to process (default: all). "
             f"Available: {', '.join(EVENT_TYPE_FAMILIES.keys())}"
    )
    
    parser.add_argument(
        "--horizons",
        type=str,
        default="1d",
        help="Comma-separated list of prediction horizons (default: 1d). Use '1d,5d' for multi-horizon."
    )
    
    parser.add_argument(
        "--since",
        type=parse_date,
        default=None,
        help="Only process events since this date (YYYY-MM-DD format)"
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of events to commit per batch (default: 50). Lower values = less timeout risk."
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without committing to database"
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of events to process (default: unlimited)"
    )
    
    args = parser.parse_args()
    
    families = None
    if args.families and args.families.lower() != "all":
        families = [f.strip() for f in args.families.split(",")]
        invalid_families = set(families) - set(EVENT_TYPE_FAMILIES.keys())
        if invalid_families:
            parser.error(
                f"Invalid families: {', '.join(invalid_families)}. "
                f"Available: {', '.join(EVENT_TYPE_FAMILIES.keys())}"
            )
    
    horizons = [h.strip() for h in args.horizons.split(",")]
    valid_horizons = {"1d", "5d", "20d"}
    invalid_horizons = set(horizons) - valid_horizons
    if invalid_horizons:
        parser.error(
            f"Invalid horizons: {', '.join(invalid_horizons)}. "
            f"Available: {', '.join(valid_horizons)}"
        )
    
    if args.batch_size < 1:
        parser.error("Batch size must be at least 1")
    
    result = backfill_ml_scores(
        families=families,
        horizons=horizons,
        since=args.since,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        limit=args.limit,
    )
    
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
