"""Database seed script for Impact Radar"""
import os
from datetime import datetime, timedelta
from data_manager import DataManager
from api.utils.auth import hash_password

def seed_database():
    """Seed the database with initial data"""
    dm = DataManager()
    print("🌱 Seeding database...")
    
    # 1. Create demo user (for marketing site login)
    print("\n1. Creating demo user...")
    try:
        # Use bcrypt directly
        import bcrypt
        import psycopg2
        from api.config import settings
        
        password_bytes = "demo123".encode('utf-8')
        hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
        hashed_password = hashed.decode('utf-8')
        
        # Connect to database
        conn = psycopg2.connect(settings.DATABASE_URL)
        cur = conn.cursor()
        
        try:
            # Check if user exists
            cur.execute("SELECT id FROM users WHERE email = %s", ('demo@releaseradar.com',))
            existing = cur.fetchone()
            
            if not existing:
                cur.execute("""
                    INSERT INTO users (email, password_hash, created_at)
                    VALUES (%s, %s, NOW())
                """, ('demo@releaseradar.com', hashed_password))
                conn.commit()
                print("✅ Demo user created (email: demo@releaseradar.com, password: demo123)")
            else:
                print("✅ Demo user already exists")
        finally:
            cur.close()
            conn.close()
    except Exception as e:
        print(f"❌ Error creating demo user: {e}")
    
    # 2. Create sample companies
    print("\n2. Creating sample companies...")
    companies = [
        ("AAPL", "Apple Inc.", "Technology", "Consumer Electronics"),
        ("NVDA", "NVIDIA Corporation", "Technology", "Semiconductors"),
        ("MRNA", "Moderna Inc.", "Healthcare", "Biotechnology"),
        ("PFE", "Pfizer Inc.", "Healthcare", "Pharmaceuticals"),
        ("TSLA", "Tesla Inc.", "Consumer Cyclical", "Auto Manufacturers"),
        ("MSFT", "Microsoft Corporation", "Technology", "Software"),
        ("AMZN", "Amazon.com Inc.", "Consumer Cyclical", "Internet Retail"),
        ("GOOGL", "Alphabet Inc.", "Communication Services", "Internet Content"),
    ]
    
    for ticker, name, sector, industry in companies:
        try:
            # Check if company already exists
            existing = dm.get_company(ticker)
            if not existing:
                company = dm.add_company(
                    ticker=ticker,
                    name=name,
                    sector=sector,
                    industry=industry
                )
                print(f"✅ Created {ticker} - {name}")
            else:
                print(f"✅ Company {ticker} already exists")
        except Exception as e:
            print(f"⚠️  Error with company {ticker}: {e}")
    
    # 3. Create sample events with impact scores
    print("\n3. Creating sample events...")
    events = [
        {
            "ticker": "NVDA",
            "title": "NVIDIA Announces New AI Chip Architecture",
            "event_type": "Product Launch",
            "description": "NVIDIA unveiled its next-generation AI chip architecture with 2x performance improvements.",
            "impact_score": 85,
            "direction": "positive",
            "confidence": 0.92,
            "source_url": "https://nvidianews.nvidia.com/news/nvidia-blackwell-platform-arrives-to-power-a-new-era-of-computing",
            "date_offset": -1  # 1 day ago
        },
        {
            "ticker": "MRNA",
            "title": "FDA Approves Moderna's New mRNA Vaccine",
            "event_type": "Regulatory Approval",
            "description": "The FDA has approved Moderna's latest mRNA vaccine for seasonal flu.",
            "impact_score": 78,
            "direction": "positive",
            "confidence": 0.88,
            "source_url": "https://www.fda.gov/vaccines-blood-biologics/vaccines",
            "date_offset": -2  # 2 days ago
        },
        {
            "ticker": "TSLA",
            "title": "Tesla Recalls 50,000 Vehicles Due to Battery Issue",
            "event_type": "Recall",
            "description": "Tesla is recalling 50,000 vehicles worldwide due to a battery management system issue.",
            "impact_score": -45,
            "direction": "negative",
            "confidence": 0.75,
            "source_url": "https://www.nhtsa.gov/recalls",
            "date_offset": -3  # 3 days ago
        },
        {
            "ticker": "AAPL",
            "title": "Apple Announces Q4 Earnings Beat Expectations",
            "event_type": "Earnings",
            "description": "Apple reported Q4 earnings with revenue up 12% YoY, beating analyst expectations.",
            "impact_score": 72,
            "direction": "positive",
            "confidence": 0.90,
            "source_url": "https://www.apple.com/newsroom/2024/10/apple-reports-fourth-quarter-results/",
            "date_offset": 0  # today
        },
        {
            "ticker": "PFE",
            "title": "Pfizer Partners with Leading Research Institute",
            "event_type": "Partnership",
            "description": "Pfizer announces strategic partnership for cancer drug development.",
            "impact_score": 65,
            "direction": "positive",
            "confidence": 0.80,
            "source_url": "https://www.pfizer.com/news",
            "date_offset": -5  # 5 days ago
        },
        {
            "ticker": "MSFT",
            "title": "Microsoft Cloud Revenue Exceeds $30B Quarterly",
            "event_type": "Financial Results",
            "description": "Microsoft's Azure cloud platform drives record quarterly revenue.",
            "impact_score": 70,
            "direction": "positive",
            "confidence": 0.85,
            "source_url": "https://www.microsoft.com/en-us/investor",
            "date_offset": -1
        }
    ]
    
    for event in events:
        try:
            event_date = datetime.now() + timedelta(days=event["date_offset"])
            
            # Check if event already exists
            if not dm.event_exists(
                ticker=event["ticker"],
                event_type=event["event_type"],
                date=event_date,
                title=event["title"]
            ):
                # Get company name
                company = dm.get_company(event["ticker"])
                company_name = company['name'] if company else event["ticker"]
                
                created_event = dm.add_event(
                    ticker=event["ticker"],
                    company_name=company_name,
                    event_type=event["event_type"],
                    title=event["title"],
                    description=event["description"],
                    date=event_date,
                    source="Manual Seed",
                    source_url=event["source_url"],
                    sector=company.get('sector') if company else None,
                    auto_score=False  # We'll set scores manually
                )
                print(f"✅ Created event: {event['title'][:50]}...")
            else:
                print(f"✅ Event already exists: {event['title'][:50]}...")
        except Exception as e:
            print(f"⚠️  Error creating event: {e}")
    
    # 4. Create scanner logs
    print("\n4. Creating scanner logs...")
    scanner_logs = [
        {"source": "sec", "discoveries": 5},
        {"source": "fda", "discoveries": 3},
        {"source": "press", "discoveries": 8},
    ]
    
    for log in scanner_logs:
        try:
            dm.add_scanner_log(
                scanner=log["source"],
                message=f"Found {log['discoveries']} new events",
                level="info"
            )
            print(f"✅ Created {log['source'].upper()} scanner log")
        except Exception as e:
            print(f"⚠️  Scanner log creation failed: {e}")
    
    print("\n✨ Database seeding completed!")
    print("\n📋 Demo Credentials:")
    print("   Email: demo@releaseradar.com")
    print("   Password: demo123")

if __name__ == "__main__":
    seed_database()
