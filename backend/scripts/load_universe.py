#!/usr/bin/env python3
"""
Load company universe from CSV file into database.

Usage:
    python scripts/load_universe.py data/universe/sp500.csv
"""

import csv
import sys
import os
from datetime import datetime
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from releaseradar.db.session import SessionLocal
from releaseradar.db.models import Company
from sqlalchemy import select


def load_universe(csv_path: str) -> dict:
    """
    Load companies from CSV into database with idempotent upserts.
    
    Args:
        csv_path: Path to CSV file with columns: ticker,name,sector
        
    Returns:
        Dictionary with stats: added, updated, total
    """
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found: {csv_path}")
        sys.exit(1)
    
    session = SessionLocal()
    stats = {"added": 0, "updated": 0, "errors": 0, "total": 0}
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            if not all(col in reader.fieldnames for col in ['ticker', 'name', 'sector']):
                print("Error: CSV must have columns: ticker, name, sector")
                sys.exit(1)
            
            for row in reader:
                ticker = row['ticker'].strip().upper()
                name = row['name'].strip()
                sector = row['sector'].strip() if row.get('sector') else None
                
                if not ticker or not name:
                    stats['errors'] += 1
                    print(f"Warning: Skipping invalid row: {row}")
                    continue
                
                try:
                    # Check if company exists
                    existing = session.execute(
                        select(Company).where(Company.ticker == ticker)
                    ).scalar_one_or_none()
                    
                    if existing:
                        # Update existing company
                        existing.name = name
                        existing.sector = sector
                        existing.tracked = True
                        existing.updated_at = datetime.utcnow()
                        stats['updated'] += 1
                    else:
                        # Create new company
                        company = Company(
                            ticker=ticker,
                            name=name,
                            sector=sector,
                            tracked=True,
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow()
                        )
                        session.add(company)
                        stats['added'] += 1
                    
                    stats['total'] += 1
                    
                    # Commit in batches of 100 for performance
                    if stats['total'] % 100 == 0:
                        session.commit()
                        print(f"Processed {stats['total']} companies...")
                
                except Exception as e:
                    stats['errors'] += 1
                    print(f"Error processing {ticker}: {e}")
                    session.rollback()
                    continue
        
        # Final commit
        session.commit()
        
        print("\n" + "="*60)
        print("Universe Load Complete")
        print("="*60)
        print(f"Total processed: {stats['total']}")
        print(f"Added:          {stats['added']}")
        print(f"Updated:        {stats['updated']}")
        print(f"Errors:         {stats['errors']}")
        print("="*60)
        
        return stats
        
    except Exception as e:
        print(f"Fatal error: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/load_universe.py <csv_path>")
        print("Example: python scripts/load_universe.py data/universe/sp500.csv")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    load_universe(csv_path)
