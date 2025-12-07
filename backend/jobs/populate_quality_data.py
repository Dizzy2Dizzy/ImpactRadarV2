"""
Populate data quality tables with realistic sample data for dashboard demonstration.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
import random
from releaseradar.database import get_session
from releaseradar.services.quality_metrics import QualityMetricsService
from sqlalchemy import text

def populate_pipeline_runs():
    """Populate pipeline runs for the last 7 days."""
    print("Populating pipeline runs...")
    
    with get_session() as db:
        service = QualityMetricsService(db)
        
        jobs = [
            ("sec_edgar_scanner", 240),  # 4 hours
            ("fda_announcements_scanner", 360),  # 6 hours
            ("company_press_scanner", 480),  # 8 hours
        ]
        
        # Create runs for past 7 days
        now = datetime.utcnow()
        for days_ago in range(7):
            date = now - timedelta(days=days_ago)
            
            for job_name, interval_minutes in jobs:
                # Calculate how many runs per day
                runs_per_day = (24 * 60) // interval_minutes
                
                for run_idx in range(runs_per_day):
                    start_time = date - timedelta(
                        hours=random.randint(0, 23),
                        minutes=random.randint(0, 59)
                    )
                    duration = random.uniform(30, 180)  # 30s to 3min
                    end_time = start_time + timedelta(seconds=duration)
                    
                    # 95% success rate
                    status = "success" if random.random() < 0.95 else "failure"
                    rows = random.randint(5, 50) if status == "success" else 0
                    error = "Connection timeout" if status == "failure" else None
                    
                    run_id = service.record_pipeline_run(
                        job_name=job_name,
                        source_hash=f"hash_{days_ago}_{run_idx}",
                        started_at=start_time
                    )
                    
                    service.update_pipeline_run(
                        run_id=run_id,
                        status=status,
                        rows_written=rows,
                        error_blob=error,
                        completed_at=end_time
                    )
        
        db.commit()
        print(f"✓ Created pipeline runs")


def populate_freshness_snapshots():
    """Populate freshness indicators for various metrics."""
    print("Populating freshness snapshots...")
    
    with get_session() as db:
        service = QualityMetricsService(db)
        
        metrics = [
            ("events_total", "global", "sec_edgar_scanner", 752),
            ("events_primary", "global", "sec_edgar_scanner", 487),
            ("events_secondary", "global", "sec_edgar_scanner", 265),
            ("companies_tracked", "global", "company_press_scanner", 238),
            ("prices_spy", "global", "price_updater", 1),
            ("prices_all", "global", "price_updater", 156),
            ("ml_predictions", "global", "ml_scorer", 624),
            ("events_8k", "global", "sec_edgar_scanner", 312),
            ("events_10q", "global", "sec_edgar_scanner", 89),
            ("events_fda", "global", "fda_announcements_scanner", 76),
            ("events_press", "global", "company_press_scanner", 134),
            ("alerts_active", "user", "alert_matcher", 24),
        ]
        
        now = datetime.utcnow()
        
        for metric_key, scope, source_job, sample_count in metrics:
            # Create snapshots for past 7 days
            for days_ago in range(7):
                timestamp = now - timedelta(days=days_ago, hours=random.randint(0, 23))
                
                # Data gets fresher as we approach today
                age_hours = days_ago * 24 + random.randint(0, 23)
                if age_hours < 6:
                    grade = "excellent"
                elif age_hours < 24:
                    grade = "good"
                elif age_hours < 72:
                    grade = "fair"
                else:
                    grade = "stale"
                
                # Vary sample count slightly
                samples = sample_count + random.randint(-5, 10)
                
                service.record_quality_snapshot(
                    metric_key=metric_key,
                    scope=scope,
                    sample_count=max(samples, 0),
                    freshness_ts=timestamp - timedelta(hours=age_hours),
                    source_job=source_job,
                    quality_grade=grade,
                    summary={"source": "populate_script", "variation": random.randint(1, 100)}
                )
        
        db.commit()
        print(f"✓ Created {len(metrics) * 7} freshness snapshots")


def populate_lineage_records():
    """Populate lineage records for event tracking."""
    print("Populating lineage records...")
    
    with get_session() as db:
        # Get some actual event IDs from database
        result = db.execute(text("SELECT id FROM events LIMIT 100"))
        event_ids = [row[0] for row in result.fetchall()]
        
        if not event_ids:
            print("⚠ No events found in database, skipping lineage records")
            return
        
        service = QualityMetricsService(db)
        
        sources = [
            ("https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000789019", "events_8k"),
            ("https://www.fda.gov/drugs/drug-approvals-and-databases/drug-trials-snapshots", "events_fda"),
            ("https://investors.example.com/news-releases", "events_press"),
        ]
        
        for event_id in random.sample(event_ids, min(len(event_ids), 50)):
            source_url, metric_key = random.choice(sources)
            
            service.record_lineage(
                metric_key=metric_key,
                entity_type="event",
                entity_id=event_id,
                source_url=source_url,
                payload_hash=f"sha256_{random.randint(1000, 9999)}",
                observed_at=datetime.utcnow() - timedelta(days=random.randint(0, 30))
            )
        
        db.commit()
        print(f"✓ Created lineage records")


def populate_audit_log():
    """Populate audit log with sample mutation records."""
    print("Populating audit log...")
    
    with get_session() as db:
        # Get some actual user IDs
        result = db.execute(text("SELECT id FROM users LIMIT 5"))
        user_ids = [row[0] for row in result.fetchall()]
        
        if not user_ids:
            print("⚠ No users found in database, skipping audit log")
            return
        
        service = QualityMetricsService(db)
        
        actions = [
            ("event", "create", {"title": "New Event", "impact_score": 75}),
            ("company", "update", {"old_name": "ACME Inc", "new_name": "ACME Corp"}),
            ("watchlist", "create", {"ticker": "AAPL"}),
            ("alert", "delete", {"criteria": "impact > 80"}),
        ]
        
        for _ in range(30):
            entity_type, action, diff = random.choice(actions)
            performed_by = random.choice(user_ids)
            entity_id = random.randint(1, 100)
            
            service.record_audit_log(
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                diff=diff,
                performed_by=performed_by,
                performed_at=datetime.utcnow() - timedelta(days=random.randint(0, 30))
            )
        
        db.commit()
        print(f"✓ Created audit log entries")


def main():
    """Populate all quality data tables."""
    print("=" * 60)
    print("Populating Data Quality Tables")
    print("=" * 60)
    
    try:
        populate_pipeline_runs()
        populate_freshness_snapshots()
        populate_lineage_records()
        populate_audit_log()
        
        print("\n" + "=" * 60)
        print("✓ Data quality tables populated successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error populating data: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
