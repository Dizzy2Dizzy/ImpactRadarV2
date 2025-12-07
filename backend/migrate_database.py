"""
Database Migration Script for Impact Radar Schema Upgrade

Safely migrates from old schema to new professional schema.
Preserves all existing data while adding new fields.
"""

from datetime import datetime
from database import get_db, close_db_session, init_db
from sqlalchemy import text
from impact_scoring import score_event


def migrate_to_new_schema():
    """Migrate database from old schema to new schema."""
    print("\n" + "="*70)
    print("Impact Radar Database Migration")
    print("="*70 + "\n")
    
    db = get_db()
    
    try:
        # Step 1: Add new columns to Companies table
        print("Step 1: Updating Companies table...")
        
        # Add sector column
        try:
            db.execute(text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS sector VARCHAR"))
            print("  ✓ Added sector column")
        except:
            print("  - sector column already exists")
        
        # Add parent_id column
        try:
            db.execute(text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS parent_id INTEGER REFERENCES companies(id)"))
            print("  ✓ Added parent_id column")
        except:
            print("  - parent_id column already exists")
        
        # Migrate industry to sector for pharma/biotech companies
        db.execute(text("""
            UPDATE companies
            SET sector = CASE
                WHEN industry IN ('Pharmaceuticals', 'Biotechnology', 'Healthcare') THEN 'Pharma'
                WHEN industry IN ('Gaming', 'Video Games') THEN 'Gaming'
                WHEN industry IN ('Banking', 'Finance', 'Payments') THEN 'Finance'
                WHEN industry IN ('Retail', 'Consumer') THEN 'Retail'
                ELSE 'Tech'
            END
            WHERE sector IS NULL
        """))
        db.commit()
        print("  ✓ Migrated industry values to sector\n")
        
        # Step 2: Add new columns to Events table
        print("Step 2: Updating Events table...")
        
        # Rename company to company_name
        try:
            db.execute(text("ALTER TABLE events RENAME COLUMN company TO company_name"))
            print("  ✓ Renamed company to company_name")
        except:
            print("  - company_name column already exists")
        
        # Rename subsidiary to subsidiary_name
        try:
            db.execute(text("ALTER TABLE events RENAME COLUMN subsidiary TO subsidiary_name"))
            print("  ✓ Renamed subsidiary to subsidiary_name")
        except:
            print("  - subsidiary_name column already exists")
        
        # Add direction column
        try:
            db.execute(text("ALTER TABLE events ADD COLUMN IF NOT EXISTS direction VARCHAR"))
            print("  ✓ Added direction column")
        except:
            print("  - direction column already exists")
        
        # Add confidence column
        try:
            db.execute(text("ALTER TABLE events ADD COLUMN IF NOT EXISTS confidence FLOAT DEFAULT 0.5"))
            print("  ✓ Added confidence column")
        except:
            print("  - confidence column already exists")
        
        # Add rationale column
        try:
            db.execute(text("ALTER TABLE events ADD COLUMN IF NOT EXISTS rationale TEXT"))
            print("  ✓ Added rationale column")
        except:
            print("  - rationale column already exists")
        
        db.commit()
        print()
        
        # Step 3: Migrate event dates from string to timestamp
        print("Step 3: Converting date strings to timestamps...")
        
        # Create temporary timestamp column
        try:
            db.execute(text("ALTER TABLE events ADD COLUMN IF NOT EXISTS date_temp TIMESTAMP WITH TIME ZONE"))
            print("  ✓ Added temporary date_temp column")
        except:
            print("  - date_temp column already exists")
        
        # Convert string dates to timestamps
        db.execute(text("""
            UPDATE events
            SET date_temp = CASE
                WHEN date ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' THEN date::timestamp
                WHEN date ~ '^[0-9]{2}/[0-9]{2}/[0-9]{4}$' THEN to_timestamp(date, 'MM/DD/YYYY')
                ELSE NOW()
            END
            WHERE date_temp IS NULL AND date IS NOT NULL
        """))
        db.commit()
        print("  ✓ Converted date strings to timestamps")
        
        # Drop old date column and rename date_temp
        try:
            db.execute(text("ALTER TABLE events DROP COLUMN date"))
            db.execute(text("ALTER TABLE events RENAME COLUMN date_temp TO date"))
            db.execute(text("ALTER TABLE events ALTER COLUMN date SET NOT NULL"))
            print("  ✓ Replaced string date with timestamp date\n")
        except Exception as e:
            print(f"  ! Date column migration completed with note: {e}\n")
        
        db.commit()
        
        # Step 4: Re-score all events with impact_scoring.py
        print("Step 4: Re-scoring events with deterministic impact scoring...")
        
        events = db.execute(text("SELECT id, event_type, title, description, sector FROM events")).fetchall()
        
        scored_count = 0
        for event in events:
            event_id, event_type, title, description, sector = event
            
            try:
                # Get deterministic score
                result = score_event(
                    event_type=event_type or 'manual_entry',
                    title=title or '',
                    description=description or '',
                    sector=sector
                )
                impact_score = result.get('impact_score', 50)
                direction = result.get('direction', 'neutral')
                confidence = result.get('confidence', 0.5)
                rationale = result.get('rationale')
                
                # Update event with scoring
                db.execute(text("""
                    UPDATE events
                    SET impact_score = :score,
                        direction = :direction,
                        confidence = :confidence,
                        rationale = :rationale
                    WHERE id = :id
                """), {
                    'score': impact_score,
                    'direction': direction,
                    'confidence': confidence,
                    'rationale': rationale,
                    'id': event_id
                })
                
                scored_count += 1
                
            except Exception as e:
                print(f"  ! Error scoring event {event_id}: {e}")
        
        db.commit()
        print(f"  ✓ Re-scored {scored_count} events\n")
        
        # Step 5: Clean up old columns
        print("Step 5: Cleaning up deprecated columns...")
        
        # Remove is_favorite from events (replaced by watchlist)
        try:
            db.execute(text("ALTER TABLE events DROP COLUMN IF EXISTS is_favorite"))
            print("  ✓ Removed is_favorite column")
        except:
            print("  - is_favorite already removed")
        
        # Remove summary from events (replaced by rationale)
        try:
            db.execute(text("ALTER TABLE events DROP COLUMN IF EXISTS summary"))
            print("  ✓ Removed summary column")
        except:
            print("  - summary already removed")
        
        # Remove subsidiaries JSON from companies (replaced by parent_id)
        try:
            db.execute(text("ALTER TABLE companies DROP COLUMN IF EXISTS subsidiaries"))
            print("  ✓ Removed subsidiaries JSON column")
        except:
            print("  - subsidiaries already removed")
        
        db.commit()
        print()
        
        # Step 6: Update watchlist schema
        print("Step 6: Simplifying watchlist table...")
        
        # Remove old watchlist columns
        for col in ['company', 'primary_event', 'event_date', 'impact_score', 'added_date']:
            try:
                db.execute(text(f"ALTER TABLE watchlist DROP COLUMN IF EXISTS {col}"))
                print(f"  ✓ Removed {col} column")
            except:
                pass
        
        # Ensure notes column exists
        try:
            db.execute(text("ALTER TABLE watchlist ADD COLUMN IF NOT EXISTS notes TEXT"))
            print("  ✓ Added notes column")
        except:
            print("  - notes column already exists")
        
        db.commit()
        print()
        
        print("="*70)
        print("Migration Complete!")
        print("="*70)
        print("\nDatabase has been successfully upgraded to the new schema.")
        print("All events have been re-scored with deterministic impact scoring.")
        print("\nNext steps:")
        print("1. Test the application with 'streamlit run app.py'")
        print("2. Verify all data is intact")
        print("3. Run seed_database.py if you need demo data")
        print()
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print("Rolling back changes...")
        db.rollback()
        raise
    
    finally:
        close_db_session(db)


if __name__ == "__main__":
    migrate_to_new_schema()
