"""Seed sample data for development"""
from datetime import datetime, timedelta
from backend.database import SessionLocal, engine, close_db_session
from backend.releaseradar.db.models import Base, Company, Event

# Create all tables
Base.metadata.create_all(bind=engine)

db = SessionLocal()

# Create sample companies
companies_data = [
    {"name": "Tesla Inc", "ticker": "TSLA", "sector": "Automotive", "industry": "Electric Vehicles"},
    {"name": "Biogen Inc", "ticker": "BIIB", "sector": "Healthcare", "industry": "Biotechnology"},
    {"name": "JPMorgan Chase & Co", "ticker": "JPM", "sector": "Financial", "industry": "Banking"},
    {"name": "Moderna Inc", "ticker": "MRNA", "sector": "Healthcare", "industry": "Biotechnology"},
    {"name": "NVIDIA Corporation", "ticker": "NVDA", "sector": "Technology", "industry": "Semiconductors"},
]

companies = []
for comp_data in companies_data:
    # Check if company already exists
    existing = db.query(Company).filter_by(ticker=comp_data["ticker"]).first()
    if not existing:
        company = Company(**comp_data)
        db.add(company)
        companies.append(company)
    else:
        companies.append(existing)

db.commit()

# Refresh to get IDs
for c in companies:
    db.refresh(c)

# Create sample events
events_data = [
    {
        "ticker": "BIIB",
        "company_name": "Biogen Inc",
        "event_type": "FDA",
        "title": "FDA Approval - Alzheimer's Drug",
        "description": "FDA approves new Alzheimer's treatment after Phase 3 trials",
        "date": datetime.utcnow() + timedelta(days=1),
        "source": "FDA",
        "source_url": "https://www.fda.gov/news-events",
        "impact_score": 90,
        "direction": "positive",
        "confidence": 0.85,
        "rationale": "Major FDA approval for blockbuster drug, significant revenue potential",
        "sector": "Healthcare"
    },
    {
        "ticker": "TSLA",
        "company_name": "Tesla Inc",
        "event_type": "Earnings",
        "title": "Q4 Earnings Report",
        "description": "Tesla reports record quarterly deliveries",
        "date": datetime.utcnow() + timedelta(days=7),
        "source": "SEC",
        "source_url": "https://www.sec.gov/edgar",
        "impact_score": 75,
        "direction": "positive",
        "confidence": 0.70,
        "rationale": "Record deliveries indicate strong demand and potential earnings beat",
        "sector": "Automotive"
    },
    {
        "ticker": "NVDA",
        "company_name": "NVIDIA Corporation",
        "event_type": "Product Launch",
        "title": "New AI Chip Announcement",
        "description": "NVIDIA announces next-generation AI accelerator chips",
        "date": datetime.utcnow() + timedelta(days=3),
        "source": "Press Release",
        "source_url": "https://nvidianews.nvidia.com",
        "impact_score": 85,
        "direction": "positive",
        "confidence": 0.80,
        "rationale": "New AI chips could capture growing data center market share",
        "sector": "Technology"
    },
    {
        "ticker": "JPM",
        "company_name": "JPMorgan Chase & Co",
        "event_type": "Regulatory",
        "title": "Fed Stress Test Results",
        "description": "JPMorgan passes annual Federal Reserve stress test",
        "date": datetime.utcnow() + timedelta(days=5),
        "source": "Federal Reserve",
        "source_url": "https://www.federalreserve.gov",
        "impact_score": 65,
        "direction": "positive",
        "confidence": 0.75,
        "rationale": "Passing stress test confirms capital adequacy and allows for buybacks",
        "sector": "Financial"
    },
    {
        "ticker": "MRNA",
        "company_name": "Moderna Inc",
        "event_type": "Clinical Trial",
        "title": "Phase 3 Cancer Vaccine Results",
        "description": "Positive interim results from personalized cancer vaccine trial",
        "date": datetime.utcnow() + timedelta(days=2),
        "source": "Press Release",
        "source_url": "https://investors.modernatx.com",
        "impact_score": 88,
        "direction": "positive",
        "confidence": 0.78,
        "rationale": "Successful trial could open new revenue stream beyond COVID vaccines",
        "sector": "Healthcare"
    }
]

for event_data in events_data:
    # Check if event already exists
    existing = db.query(Event).filter_by(
        ticker=event_data["ticker"],
        title=event_data["title"]
    ).first()
    
    if not existing:
        event = Event(**event_data)
        db.add(event)

db.commit()

print("✅ Seeded sample companies and events")
print(f"Companies: {len(companies_data)}")
print(f"Events: {len(events_data)}")

close_db_session(db)
