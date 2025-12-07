"""
Corrective Migration: Fix FDA Events for Non-Pharma Companies

Removes FDA event types from non-pharma/biotech companies and re-scores them.
"""

from database import get_db, close_db_session, Event, Company
from impact_scoring import score_event


def fix_fda_events():
    """Fix wrongly classified FDA events for non-pharma companies."""
    db = get_db()
    
    try:
        print("Starting FDA event correction migration...")
        
        # Get all events with FDA event types
        fda_events = db.query(Event).filter(
            Event.event_type.like('fda%')
        ).all()
        
        print(f"Found {len(fda_events)} FDA events to check")
        
        fixed_count = 0
        
        for event in fda_events:
            # Get company sector
            company = db.query(Company).filter(Company.ticker == event.ticker).first()
            
            if not company:
                print(f"  WARNING: No company found for ticker {event.ticker}")
                continue
            
            sector = company.sector or ""
            sector_lower = sector.lower()
            
            # If sector is NOT pharma/biotech, this is a mistake
            if sector_lower not in ['pharma', 'biotech', 'healthcare']:
                old_type = event.event_type
                
                # Change to press_release (safe generic type)
                event.event_type = 'press_release'
                
                # Re-score
                result = score_event(
                    event_type='press_release',
                    title=event.title or "",
                    description=event.description or "",
                    sector=sector
                )
                
                event.impact_score = result.get('impact_score', 50)
                event.direction = result.get('direction', 'neutral')
                event.confidence = result.get('confidence', 0.5)
                event.rationale = result.get('rationale')
                
                print(f"  FIXED: {event.ticker} ({sector}): '{old_type}' → 'press_release'")
                fixed_count += 1
            else:
                # This is a legitimate pharma FDA event - keep it but re-score
                result = score_event(
                    event_type=event.event_type,
                    title=event.title or "",
                    description=event.description or "",
                    sector=sector
                )
                
                event.impact_score = result.get('impact_score', 50)
                event.direction = result.get('direction', 'neutral')
                event.confidence = result.get('confidence', 0.5)
                event.rationale = result.get('rationale')
        
        db.commit()
        
        print("\n" + "="*60)
        print("Correction Complete!")
        print(f"  FDA events checked: {len(fda_events)}")
        print(f"  Non-pharma events fixed: {fixed_count}")
        print(f"  Legitimate pharma events kept: {len(fda_events) - fixed_count}")
        print("="*60)
        
    except Exception as e:
        db.rollback()
        print(f"\nERROR during correction: {str(e)}")
        raise
    finally:
        close_db_session(db)


if __name__ == "__main__":
    fix_fda_events()
