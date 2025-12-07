"""
Comprehensive Database Population Script for Impact Radar

Populates database with 1200+ real companies and realistic events:
1. Fetches stock universe using yfinance (or loads from cache)
2. Generates realistic events with proper scoring
3. Populates database with all data
4. Applies probabilistic scoring to events

Usage:
    python populate_comprehensive_database.py [--fetch-fresh] [--target-companies 1200]
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import argparse
from loguru import logger
from database import get_db, close_db_session, Company, Event, EventScore
from fetch_stock_universe import fetch_stock_universe, save_stock_universe, load_stock_universe
from generate_comprehensive_events import ComprehensiveEventGenerator
import json
from datetime import datetime


def clear_existing_data(db):
    """Clear existing companies and events from database."""
    logger.info("Clearing existing data...")
    try:
        # Delete in correct order to respect foreign keys
        deleted_scores = db.query(EventScore).delete()
        deleted_events = db.query(Event).delete()
        deleted_companies = db.query(Company).delete()
        db.commit()
        logger.info(f"Deleted {deleted_scores} event scores, {deleted_events} events, {deleted_companies} companies")
    except Exception as e:
        logger.error(f"Error clearing data: {e}")
        db.rollback()
        raise


def populate_companies(db, companies: list) -> int:
    """
    Populate companies table with fetched company data.
    
    Args:
        db: Database session
        companies: List of company dictionaries
        
    Returns:
        Number of companies added
    """
    logger.info(f"Adding {len(companies)} companies to database...")
    added = 0
    
    for company_data in companies:
        try:
            company = Company(
                ticker=company_data['ticker'].upper(),
                name=company_data['name'],
                sector=company_data['sector'],
                industry=company_data['industry'],
                tracked=True  # All companies tracked by default
            )
            db.add(company)
            added += 1
            
            if added % 100 == 0:
                db.commit()
                logger.info(f"Committed {added} companies")
        except Exception as e:
            logger.warning(f"Failed to add {company_data['ticker']}: {e}")
            db.rollback()
            continue
    
    db.commit()
    logger.info(f"Successfully added {added} companies")
    return added


def populate_events(db, events: list) -> int:
    """
    Populate events table with generated events.
    
    Args:
        db: Database session
        events: List of event dictionaries
        
    Returns:
        Number of events added
    """
    logger.info(f"Adding {len(events)} events to database...")
    added = 0
    
    for event_data in events:
        try:
            # Create main event record
            event = Event(
                ticker=event_data['ticker'],
                company=event_data['company'],
                event_type=event_data['event_type'],
                title=event_data['title'],
                description=event_data['description'],
                date=event_data['date'],
                impact_score=event_data['impact_score'],
                direction=event_data['direction'],
                confidence=event_data['confidence'],
                rationale=event_data['rationale'],
                source_url=event_data['source_url'],
                sector=event_data['sector'],
                is_favorite=False,
                scanner_key=None,  # Generated events don't have scanner key
                scanner_run_id=None,
            )
            db.add(event)
            db.flush()  # Get event ID
            
            # Create EventScore record with probabilistic data
            event_score = EventScore(
                event_id=event.id,
                event_type_score=event_data['impact_score'],
                sector_modifier=0,
                market_cap_modifier=0,
                sentiment_score=0,
                timing_score=0,
                materiality_score=0,
                final_score=event_data['impact_score'],
                p_move=event_data.get('p_move'),
                p_up=event_data.get('p_up'),
                p_down=event_data.get('p_down'),
            )
            db.add(event_score)
            
            added += 1
            
            if added % 500 == 0:
                db.commit()
                logger.info(f"Committed {added} events")
        except Exception as e:
            logger.warning(f"Failed to add event for {event_data['ticker']}: {e}")
            db.rollback()
            continue
    
    db.commit()
    logger.info(f"Successfully added {added} events")
    return added


def main():
    """Main population function."""
    parser = argparse.ArgumentParser(description='Populate Impact Radar database with comprehensive stock data')
    parser.add_argument('--fetch-fresh', action='store_true',
                        help='Fetch fresh data from yfinance instead of using cache')
    parser.add_argument('--target-companies', type=int, default=1200,
                        help='Target number of companies to fetch')
    parser.add_argument('--skip-clear', action='store_true',
                        help='Skip clearing existing data')
    parser.add_argument('--cache-file', type=str, default='stock_universe.json',
                        help='Path to cache file for stock universe')
    
    args = parser.parse_args()
    
    logger.info("=== Impact Radar Comprehensive Database Population ===")
    logger.info(f"Target companies: {args.target_companies}")
    logger.info(f"Fetch fresh: {args.fetch_fresh}")
    logger.info(f"Skip clear: {args.skip_clear}")
    
    # Step 1: Fetch or load stock universe
    if args.fetch_fresh or not os.path.exists(args.cache_file):
        logger.info("Fetching fresh stock universe from yfinance...")
        companies = fetch_stock_universe(target_count=args.target_companies)
        save_stock_universe(companies, args.cache_file)
    else:
        logger.info(f"Loading stock universe from cache: {args.cache_file}")
        companies = load_stock_universe(args.cache_file)
    
    logger.info(f"Loaded {len(companies)} companies")
    
    # Step 2: Generate events for all companies
    logger.info("Generating events for all companies...")
    generator = ComprehensiveEventGenerator()
    events = generator.generate_batch(companies)
    logger.info(f"Generated {len(events)} total events")
    
    # Print summary statistics
    sector_counts = {}
    event_type_counts = {}
    for event in events:
        sector = event['sector']
        event_type = event['event_type']
        sector_counts[sector] = sector_counts.get(sector, 0) + 1
        event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1
    
    logger.info(f"\nEvent distribution by sector:")
    for sector, count in sorted(sector_counts.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {sector}: {count}")
    
    logger.info(f"\nEvent distribution by type:")
    for event_type, count in sorted(event_type_counts.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {event_type}: {count}")
    
    # Step 3: Populate database
    db = get_db()
    try:
        if not args.skip_clear:
            clear_existing_data(db)
        
        companies_added = populate_companies(db, companies)
        events_added = populate_events(db, events)
        
        logger.info("\n=== Population Complete ===")
        logger.info(f"Companies added: {companies_added}")
        logger.info(f"Events added: {events_added}")
        logger.info(f"Average events per company: {events_added / companies_added:.1f}")
        
        # Verify data
        total_companies = db.query(Company).count()
        total_events = db.query(Event).count()
        logger.info(f"\nDatabase verification:")
        logger.info(f"Total companies in DB: {total_companies}")
        logger.info(f"Total events in DB: {total_events}")
        
        if total_companies >= 1000:
            logger.info(f"\n✅ SUCCESS: Database populated with {total_companies} companies and {total_events} events")
        else:
            logger.warning(f"\n⚠️ WARNING: Only {total_companies} companies in database (target was 1000+)")
    
    except Exception as e:
        logger.error(f"Population failed: {e}")
        db.rollback()
        raise
    finally:
        close_db_session(db)


if __name__ == "__main__":
    main()
