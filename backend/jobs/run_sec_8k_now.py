#!/usr/bin/env python3
"""
Manual trigger script for SEC 8-K scanner.
Run this to immediately capture new SEC 8-K filings.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from releaseradar.log_config import configure_logging
configure_logging()

from database import SessionLocal, close_db_session
from releaseradar.db.models import Event, Company
from scanners.impl.sec_8k import scan_sec_8k
from analytics.scoring import compute_event_score
import logging

logger = logging.getLogger(__name__)

def run_sec_8k_scanner():
    """Run SEC 8-K scanner and insert events into database."""
    db = SessionLocal()
    
    try:
        print("=" * 60)
        print("SEC 8-K SCANNER - FULL MANUAL RUN (no short-circuit)")
        print(f"Started at: {datetime.now(timezone.utc).isoformat()}")
        print("=" * 60)
        
        companies = db.query(Company).filter(Company.tracked.is_(True)).all()
        
        if not companies:
            print("ERROR: No tracked companies found")
            return
        
        tickers = [c.ticker for c in companies]
        company_dict = {
            c.ticker: {
                'name': c.name,
                'sector': c.sector if c.sector is not None else 'Unknown',
                'industry': c.industry
            }
            for c in companies
        }
        
        print(f"Scanning {len(tickers)} companies for SEC 8-K filings...")
        print("-" * 60)
        
        normalized_events = scan_sec_8k(
            tickers, 
            company_dict,
            short_circuit=False,
            batch_size=50,
            batch_delay=0.5
        )
        
        if not normalized_events:
            print("\nNo new SEC 8-K filings found.")
            return
        
        print(f"\nFound {len(normalized_events)} SEC 8-K filings. Inserting into database...")
        print("-" * 60)
        
        new_event_count = 0
        duplicate_count = 0
        
        for event_data in normalized_events:
            try:
                raw_id = event_data.get('raw_id')
                
                existing_event = db.query(Event).filter(
                    Event.raw_id == raw_id
                ).first()
                
                if existing_event:
                    duplicate_count += 1
                    continue
                
                event = Event(
                    ticker=event_data['ticker'],
                    company_name=event_data['company_name'],
                    event_type=event_data['event_type'],
                    title=event_data['title'],
                    description=event_data.get('description'),
                    date=event_data['date'],
                    source=event_data['source'],
                    source_url=event_data.get('source_url'),
                    raw_id=event_data.get('raw_id'),
                    source_scanner=event_data.get('source_scanner'),
                    sector=event_data.get('sector'),
                    info_tier=event_data.get('info_tier', 'primary'),
                    info_subtype=event_data.get('info_subtype'),
                    impact_score=50,
                    direction='neutral',
                    confidence=0.5
                )
                
                db.add(event)
                db.commit()
                db.refresh(event)
                
                try:
                    score_result = compute_event_score(
                        event_id=event.id,
                        ticker=event.ticker,
                        event_type=event.event_type,
                        event_date=event.date,
                        source=event.source,
                        sector=event.sector,
                        db=db
                    )
                    
                    event.impact_score = score_result.get('final_score', 50)
                    event.confidence = score_result.get('confidence', 50) / 100.0
                    event.rationale = '; '.join(score_result.get('rationale', []))
                    
                    rationale_text = event.rationale.lower() if event.rationale else ''
                    if 'positive' in rationale_text or event.impact_score >= 60:
                        event.direction = 'positive'
                    elif 'negative' in rationale_text or event.impact_score <= 40:
                        event.direction = 'negative'
                    else:
                        event.direction = 'neutral'
                    
                    db.commit()
                except Exception as e:
                    db.rollback()
                    logger.warning(f"Scoring failed for {event.ticker}: {e}")
                
                new_event_count += 1
                print(f"  + {event.ticker}: {event.title[:60]}... (score={event.impact_score})")
                
            except Exception as e:
                db.rollback()
                logger.error(f"Error inserting event: {e}")
                continue
        
        print("-" * 60)
        print(f"COMPLETED: {new_event_count} new events, {duplicate_count} duplicates skipped")
        print(f"Finished at: {datetime.now(timezone.utc).isoformat()}")
        print("=" * 60)
        
    finally:
        close_db_session(db)


if __name__ == "__main__":
    run_sec_8k_scanner()
