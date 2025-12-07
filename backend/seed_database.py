"""
Database Seeding Utility for Impact Radar

Explicit seeding functions for development and demo purposes.
No automatic execution - call these functions explicitly when needed.
"""

from datetime import datetime, timedelta
from data_manager import DataManager
from database import init_db


def seed_demo_companies(dm: DataManager) -> None:
    """Seed a small set of demo companies across sectors."""
    print("Seeding demo companies...")
    
    companies = [
        # Tech
        {"ticker": "AAPL", "name": "Apple Inc.", "sector": "Tech", "industry": "Consumer Electronics"},
        {"ticker": "NVDA", "name": "NVIDIA Corporation", "sector": "Tech", "industry": "Semiconductors"},
        {"ticker": "MSFT", "name": "Microsoft Corporation", "sector": "Tech", "industry": "Software"},
        {"ticker": "GOOGL", "name": "Alphabet Inc.", "sector": "Tech", "industry": "Internet"},
        
        # Pharma
        {"ticker": "PFE", "name": "Pfizer Inc.", "sector": "Pharma", "industry": "Pharmaceuticals"},
        {"ticker": "MRNA", "name": "Moderna Inc.", "sector": "Pharma", "industry": "Biotechnology"},
        {"ticker": "LLY", "name": "Eli Lilly and Company", "sector": "Pharma", "industry": "Pharmaceuticals"},
        
        # Finance
        {"ticker": "JPM", "name": "JPMorgan Chase & Co.", "sector": "Finance", "industry": "Banking"},
        {"ticker": "V", "name": "Visa Inc.", "sector": "Finance", "industry": "Payments"},
        
        # Gaming
        {"ticker": "TTWO", "name": "Take-Two Interactive", "sector": "Gaming", "industry": "Video Games"},
        {"ticker": "EA", "name": "Electronic Arts", "sector": "Gaming", "industry": "Video Games"},
    ]
    
    for comp in companies:
        try:
            existing = dm.get_company(comp["ticker"])
            if not existing:
                dm.add_company(**comp)
                print(f"  Added: {comp['ticker']} - {comp['name']}")
        except Exception as e:
            print(f"  Error adding {comp['ticker']}: {e}")
    
    print(f"Demo companies seeded: {len(companies)} companies\n")


def seed_demo_events(dm: DataManager) -> None:
    """Seed realistic demo events across sectors."""
    print("Seeding demo events...")
    
    now = datetime.utcnow()
    
    events = [
        # FDA Events (High Impact)
        {
            "ticker": "PFE",
            "company_name": "Pfizer Inc.",
            "event_type": "fda_approval",
            "title": "FDA PDUFA decision expected for new oncology treatment",
            "description": "FDA approval decision date for novel cancer therapy targeting solid tumors",
            "date": now + timedelta(days=30),
            "source": "FDA",
            "source_url": "https://www.fda.gov/drugs",
            "sector": "Pharma"
        },
        {
            "ticker": "MRNA",
            "company_name": "Moderna Inc.",
            "event_type": "fda_adcom",
            "title": "FDA Advisory Committee meeting for respiratory vaccine candidate",
            "description": "Expert panel review of Phase 3 data for next-generation respiratory vaccine",
            "date": now + timedelta(days=45),
            "source": "FDA",
            "sector": "Pharma"
        },
        
        # SEC Filings
        {
            "ticker": "AAPL",
            "company_name": "Apple Inc.",
            "event_type": "sec_10k",
            "title": "Annual Report (Form 10-K)",
            "description": "Apple Inc. annual report filing with SEC",
            "date": now + timedelta(days=15),
            "source": "SEC",
            "source_url": "https://www.sec.gov",
            "sector": "Tech"
        },
        
        # Earnings
        {
            "ticker": "NVDA",
            "company_name": "NVIDIA Corporation",
            "event_type": "earnings",
            "title": "Q4 2025 Earnings Call",
            "description": "NVIDIA quarterly earnings announcement and investor call",
            "date": now + timedelta(days=20),
            "source": "IR",
            "sector": "Tech"
        },
        {
            "ticker": "JPM",
            "company_name": "JPMorgan Chase & Co.",
            "event_type": "earnings",
            "title": "Q1 2026 Earnings Release",
            "description": "Quarterly earnings report with management commentary",
            "date": now + timedelta(days=35),
            "source": "IR",
            "sector": "Finance"
        },
        
        # Product Launches
        {
            "ticker": "TTWO",
            "company_name": "Take-Two Interactive",
            "event_type": "product_launch",
            "title": "Flagship game title release",
            "description": "Major AAA title launch from Rockstar Games subsidiary",
            "date": now + timedelta(days=60),
            "source": "IR",
            "subsidiary_name": "Rockstar Games",
            "sector": "Gaming"
        },
        {
            "ticker": "AAPL",
            "company_name": "Apple Inc.",
            "event_type": "product_launch",
            "title": "Spring Product Event",
            "description": "Expected announcement of new product lineup",
            "date": now + timedelta(days=90),
            "source": "IR",
            "sector": "Tech"
        },
        
        # Corporate Actions
        {
            "ticker": "MSFT",
            "company_name": "Microsoft Corporation",
            "event_type": "analyst_day",
            "title": "Annual Analyst and Investor Day",
            "description": "Strategic vision presentation and financial outlook",
            "date": now + timedelta(days=50),
            "source": "IR",
            "sector": "Tech"
        },
    ]
    
    for event_data in events:
        try:
            # Check if event exists
            exists = dm.event_exists(
                ticker=event_data["ticker"],
                event_type=event_data["event_type"],
                date=event_data["date"],
                title=event_data["title"]
            )
            
            if not exists:
                dm.add_event(**event_data, auto_score=True)
                print(f"  Added: {event_data['ticker']} - {event_data['title'][:60]}")
        except Exception as e:
            print(f"  Error adding event for {event_data['ticker']}: {e}")
    
    print(f"Demo events seeded: {len(events)} events\n")


def seed_all_demo_data() -> None:
    """Seed all demo data for Impact Radar."""
    print("\n" + "="*60)
    print("Impact Radar Database Seeding")
    print("="*60 + "\n")
    
    # Initialize database
    print("Initializing database schema...")
    init_db()
    print("Database schema initialized\n")
    
    dm = DataManager()
    
    # Seed data
    seed_demo_companies(dm)
    seed_demo_events(dm)
    
    print("="*60)
    print("Seeding complete!")
    print("="*60 + "\n")


if __name__ == "__main__":
    seed_all_demo_data()
