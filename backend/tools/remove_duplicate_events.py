"""Remove duplicate events based on source_url

This script cleans up duplicate events that have the same source_url.
It keeps the oldest event (by created_at) and deletes the rest.

Usage:
    cd backend
    python tools/remove_duplicate_events.py
"""

import sys
import os

# Add parent directory to path to import database module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db, Event
from sqlalchemy import func


def remove_duplicate_events():
    """Remove duplicate events based on source_url."""
    db = get_db()
    
    try:
        # Find duplicates by source_url (excluding null source_urls)
        duplicates = db.query(
            Event.source_url, 
            func.count(Event.id).label('count')
        ).filter(
            Event.source_url.isnot(None),
            Event.source_url != ''
        ).group_by(
            Event.source_url
        ).having(
            func.count(Event.id) > 1
        ).all()
        
        if not duplicates:
            print("No duplicate events found.")
            return
        
        print(f"Found {len(duplicates)} groups of duplicate events")
        print("-" * 80)
        
        total_deleted = 0
        batch_size = 50  # Commit every 50 groups to avoid timeout
        processed = 0
        
        for source_url, count in duplicates:
            # Keep the oldest event, delete the rest
            events = db.query(Event).filter(
                Event.source_url == source_url
            ).order_by(
                Event.created_at
            ).all()
            
            if len(events) <= 1:
                continue
            
            print(f"\nDuplicate group: {source_url}")
            print(f"  Total events: {len(events)}")
            print(f"  Keeping: ID {events[0].id} - {events[0].title[:50]} (created {events[0].created_at})")
            
            # Delete all except the first (oldest)
            for event in events[1:]:
                print(f"  Deleting: ID {event.id} - {event.title[:50]} (created {event.created_at})")
                db.delete(event)
                total_deleted += 1
            
            processed += 1
            
            # Commit in batches to avoid timeout
            if processed % batch_size == 0:
                db.commit()
                print(f"\n  [Committed batch: {processed}/{len(duplicates)} groups processed]")
        
        # Commit remaining deletions
        db.commit()
        print("-" * 80)
        print(f"\nSuccessfully cleaned up {total_deleted} duplicate events from {len(duplicates)} groups")
        
    except Exception as e:
        db.rollback()
        print(f"Error cleaning up duplicates: {e}")
        raise
    finally:
        from database import close_db_session
        close_db_session(db)


if __name__ == "__main__":
    print("Starting duplicate event cleanup...")
    remove_duplicate_events()
    print("Cleanup complete!")
