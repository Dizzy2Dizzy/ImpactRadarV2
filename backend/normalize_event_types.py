"""
Event Type Normalization Migration Script

Migrates legacy human-readable event types to standardized technical codes
and re-scores all affected events.
"""

from database import get_db, close_db_session, Event
from impact_scoring import score_event
from datetime import datetime


def normalize_event_type(old_type: str, title: str, description: str = "", sector: str = None) -> str:
    """
    Map legacy human-readable event types to canonical technical codes.
    
    For ambiguous cases, defaults to safe generic types rather than making assumptions.
    """
    old_type_lower = old_type.lower()
    title_lower = title.lower() if title else ""
    desc_lower = description.lower() if description else ""
    combined_text = f"{title_lower} {desc_lower}"
    sector_lower = sector.lower() if sector else ""
    
    # Direct mappings
    if old_type_lower == "earnings report":
        return "earnings"
    
    elif old_type_lower == "product launch":
        return "product_launch"
    
    elif old_type_lower == "conference":
        return "conference_presentation"
    
    elif old_type_lower == "investor day":
        return "analyst_day"
    
    # SEC Filing - infer specific type from form number in title
    elif old_type_lower == "sec filing":
        if "8-k" in combined_text or "8k" in combined_text:
            return "sec_8k"
        elif "10-k" in combined_text or "10k" in combined_text:
            return "sec_10k"
        elif "10-q" in combined_text or "10q" in combined_text:
            return "sec_10q"
        elif "s-1" in combined_text or "s1" in combined_text:
            return "sec_s1"
        elif "13d" in combined_text:
            return "sec_13d"
        elif "13g" in combined_text:
            return "sec_13g"
        elif "def 14a" in combined_text or "proxy" in combined_text:
            return "sec_def14a"
        else:
            # Default to generic SEC filing if we can't determine type
            return "sec_8k"
    
    # Regulatory Filing - ONLY map to FDA events for pharma/biotech sector
    elif old_type_lower == "regulatory filing":
        # Only treat as FDA event if sector is pharma/biotech AND has FDA keywords
        if sector_lower in ['pharma', 'biotech', 'healthcare']:
            if "fda" in combined_text:
                if "approval" in combined_text or "approved" in combined_text:
                    return "fda_approval"
                elif "reject" in combined_text or "rejection" in combined_text:
                    return "fda_rejection"
                elif "advisory committee" in combined_text or "adcom" in combined_text:
                    return "fda_adcom"
                elif "complete response" in combined_text or "crl" in combined_text:
                    return "fda_crl"
                elif "safety" in combined_text or "alert" in combined_text:
                    return "fda_safety_alert"
                else:
                    return "press_release"  # FDA-related but unclear type
            else:
                # Pharma regulatory but not FDA - generic
                return "press_release"
        else:
            # Non-pharma company - definitely not FDA
            # Could be SEC filing, environmental, trade, etc.
            return "press_release"
    
    # Already normalized or unknown
    else:
        return old_type


def migrate_event_types():
    """Main migration function."""
    db = get_db()
    
    try:
        print("Starting event type normalization migration...")
        
        # Get all events
        events = db.query(Event).all()
        total = len(events)
        
        print(f"Found {total} events to process")
        
        updated_count = 0
        rescored_count = 0
        
        for i, event in enumerate(events, 1):
            old_type = event.event_type
            
            # Normalize the event type (include sector for context)
            new_type = normalize_event_type(
                old_type, 
                event.title or "", 
                event.description or "",
                event.sector
            )
            
            # Update if changed
            if new_type != old_type:
                event.event_type = new_type
                updated_count += 1
                print(f"  [{i}/{total}] {event.ticker}: '{old_type}' → '{new_type}'")
            
            # Re-score the event with normalized type
            result = score_event(
                event_type=new_type,
                title=event.title or "",
                description=event.description or "",
                sector=event.sector
            )
            
            # Update scoring fields
            event.impact_score = result.get('impact_score', 50)
            event.direction = result.get('direction', 'neutral')
            event.confidence = result.get('confidence', 0.5)
            event.rationale = result.get('rationale')
            rescored_count += 1
            
            # Progress indicator
            if i % 50 == 0:
                print(f"  Progress: {i}/{total} events processed...")
        
        # Commit all changes
        db.commit()
        
        print("\n" + "="*60)
        print("Migration Complete!")
        print(f"  Total events processed: {total}")
        print(f"  Event types updated: {updated_count}")
        print(f"  Events re-scored: {rescored_count}")
        print("="*60)
        
    except Exception as e:
        db.rollback()
        print(f"\nERROR during migration: {str(e)}")
        raise
    finally:
        close_db_session(db)


if __name__ == "__main__":
    migrate_event_types()
