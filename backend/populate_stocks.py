from database import get_db, close_db_session, Company, Event
from datetime import datetime, timedelta
import random

def populate_database():
    """Populate database with hundreds of real stocks and upcoming events."""
    
    db = get_db()
    
    try:
        # Clear existing data
        print("Clearing existing data...")
        db.query(Event).delete()
        db.query(Company).delete()
        db.commit()
        
        print("Adding companies and events...")
        
        # Comprehensive list of real companies across sectors
        companies_data = [
            # Tech Giants & Software
            {"ticker": "AAPL", "name": "Apple Inc.", "industry": "Technology", "sector": "Tech"},
            {"ticker": "MSFT", "name": "Microsoft Corporation", "industry": "Technology", "sector": "Tech"},
            {"ticker": "GOOGL", "name": "Alphabet Inc.", "industry": "Technology", "sector": "Tech"},
            {"ticker": "AMZN", "name": "Amazon.com Inc.", "industry": "Technology", "sector": "Tech"},
            {"ticker": "META", "name": "Meta Platforms Inc.", "industry": "Technology", "sector": "Tech"},
            {"ticker": "NVDA", "name": "NVIDIA Corporation", "industry": "Semiconductors", "sector": "Tech"},
            {"ticker": "TSLA", "name": "Tesla Inc.", "industry": "Automotive", "sector": "Tech"},
            {"ticker": "NFLX", "name": "Netflix Inc.", "industry": "Entertainment", "sector": "Tech"},
            {"ticker": "ORCL", "name": "Oracle Corporation", "industry": "Technology", "sector": "Tech"},
            {"ticker": "CRM", "name": "Salesforce Inc.", "industry": "Technology", "sector": "Tech"},
            {"ticker": "ADBE", "name": "Adobe Inc.", "industry": "Technology", "sector": "Tech"},
            {"ticker": "NOW", "name": "ServiceNow Inc.", "industry": "Technology", "sector": "Tech"},
            {"ticker": "SNOW", "name": "Snowflake Inc.", "industry": "Technology", "sector": "Tech"},
            {"ticker": "PLTR", "name": "Palantir Technologies", "industry": "Technology", "sector": "Tech"},
            {"ticker": "DDOG", "name": "Datadog Inc.", "industry": "Technology", "sector": "Tech"},
            {"ticker": "MDB", "name": "MongoDB Inc.", "industry": "Technology", "sector": "Tech"},
            {"ticker": "TEAM", "name": "Atlassian Corporation", "industry": "Technology", "sector": "Tech"},
            {"ticker": "ZM", "name": "Zoom Video Communications", "industry": "Technology", "sector": "Tech"},
            {"ticker": "DOCU", "name": "DocuSign Inc.", "industry": "Technology", "sector": "Tech"},
            {"ticker": "WDAY", "name": "Workday Inc.", "industry": "Technology", "sector": "Tech"},
            {"ticker": "SHOP", "name": "Shopify Inc.", "industry": "Technology", "sector": "Tech"},
            {"ticker": "UBER", "name": "Uber Technologies", "industry": "Technology", "sector": "Tech"},
            {"ticker": "LYFT", "name": "Lyft Inc.", "industry": "Technology", "sector": "Tech"},
            {"ticker": "ABNB", "name": "Airbnb Inc.", "industry": "Technology", "sector": "Tech"},
            {"ticker": "DASH", "name": "DoorDash Inc.", "industry": "Technology", "sector": "Tech"},
            {"ticker": "SPOT", "name": "Spotify Technology", "industry": "Technology", "sector": "Tech"},
            {"ticker": "TWLO", "name": "Twilio Inc.", "industry": "Technology", "sector": "Tech"},
            {"ticker": "NET", "name": "Cloudflare Inc.", "industry": "Technology", "sector": "Tech"},
            {"ticker": "OKTA", "name": "Okta Inc.", "industry": "Technology", "sector": "Tech"},
            
            # Semiconductors
            {"ticker": "INTC", "name": "Intel Corporation", "industry": "Semiconductors", "sector": "Tech"},
            {"ticker": "AMD", "name": "Advanced Micro Devices", "industry": "Semiconductors", "sector": "Tech"},
            {"ticker": "QCOM", "name": "Qualcomm Inc.", "industry": "Semiconductors", "sector": "Tech"},
            {"ticker": "AVGO", "name": "Broadcom Inc.", "industry": "Semiconductors", "sector": "Tech"},
            {"ticker": "TXN", "name": "Texas Instruments", "industry": "Semiconductors", "sector": "Tech"},
            {"ticker": "AMAT", "name": "Applied Materials", "industry": "Semiconductors", "sector": "Tech"},
            {"ticker": "LRCX", "name": "Lam Research", "industry": "Semiconductors", "sector": "Tech"},
            {"ticker": "KLAC", "name": "KLA Corporation", "industry": "Semiconductors", "sector": "Tech"},
            {"ticker": "MRVL", "name": "Marvell Technology", "industry": "Semiconductors", "sector": "Tech"},
            {"ticker": "NXPI", "name": "NXP Semiconductors", "industry": "Semiconductors", "sector": "Tech"},
            {"ticker": "ADI", "name": "Analog Devices", "industry": "Semiconductors", "sector": "Tech"},
            {"ticker": "MU", "name": "Micron Technology", "industry": "Semiconductors", "sector": "Tech"},
            
            # Cybersecurity
            {"ticker": "PANW", "name": "Palo Alto Networks", "industry": "Cybersecurity", "sector": "Tech"},
            {"ticker": "CRWD", "name": "CrowdStrike Holdings", "industry": "Cybersecurity", "sector": "Tech"},
            {"ticker": "ZS", "name": "Zscaler Inc.", "industry": "Cybersecurity", "sector": "Tech"},
            {"ticker": "FTNT", "name": "Fortinet Inc.", "industry": "Cybersecurity", "sector": "Tech"},
            {"ticker": "S", "name": "SentinelOne Inc.", "industry": "Cybersecurity", "sector": "Tech"},
            
            # Pharma & Healthcare
            {"ticker": "JNJ", "name": "Johnson & Johnson", "industry": "Pharmaceuticals", "sector": "Pharma"},
            {"ticker": "PFE", "name": "Pfizer Inc.", "industry": "Pharmaceuticals", "sector": "Pharma"},
            {"ticker": "UNH", "name": "UnitedHealth Group", "industry": "Healthcare", "sector": "Pharma"},
            {"ticker": "ABBV", "name": "AbbVie Inc.", "industry": "Pharmaceuticals", "sector": "Pharma"},
            {"ticker": "LLY", "name": "Eli Lilly and Company", "industry": "Pharmaceuticals", "sector": "Pharma"},
            {"ticker": "MRK", "name": "Merck & Co.", "industry": "Pharmaceuticals", "sector": "Pharma"},
            {"ticker": "TMO", "name": "Thermo Fisher Scientific", "industry": "Healthcare", "sector": "Pharma"},
            {"ticker": "ABT", "name": "Abbott Laboratories", "industry": "Healthcare", "sector": "Pharma"},
            {"ticker": "BMY", "name": "Bristol-Myers Squibb", "industry": "Pharmaceuticals", "sector": "Pharma"},
            {"ticker": "AMGN", "name": "Amgen Inc.", "industry": "Biotechnology", "sector": "Pharma"},
            {"ticker": "GILD", "name": "Gilead Sciences", "industry": "Pharmaceuticals", "sector": "Pharma"},
            {"ticker": "REGN", "name": "Regeneron Pharmaceuticals", "industry": "Biotechnology", "sector": "Pharma"},
            {"ticker": "VRTX", "name": "Vertex Pharmaceuticals", "industry": "Biotechnology", "sector": "Pharma"},
            {"ticker": "MRNA", "name": "Moderna Inc.", "industry": "Biotechnology", "sector": "Pharma"},
            {"ticker": "ISRG", "name": "Intuitive Surgical", "industry": "Medical Devices", "sector": "Pharma"},
            {"ticker": "BIIB", "name": "Biogen Inc.", "industry": "Biotechnology", "sector": "Pharma"},
            {"ticker": "ILMN", "name": "Illumina Inc.", "industry": "Biotechnology", "sector": "Pharma"},
            {"ticker": "ALNY", "name": "Alnylam Pharmaceuticals", "industry": "Biotechnology", "sector": "Pharma"},
            {"ticker": "NBIX", "name": "Neurocrine Biosciences", "industry": "Biotechnology", "sector": "Pharma"},
            {"ticker": "INCY", "name": "Incyte Corporation", "industry": "Biotechnology", "sector": "Pharma"},
            {"ticker": "EXEL", "name": "Exelixis Inc.", "industry": "Biotechnology", "sector": "Pharma"},
            {"ticker": "SGEN", "name": "Seagen Inc.", "industry": "Biotechnology", "sector": "Pharma"},
            {"ticker": "JAZZ", "name": "Jazz Pharmaceuticals", "industry": "Pharmaceuticals", "sector": "Pharma"},
            {"ticker": "TECH", "name": "Bio-Techne Corporation", "industry": "Biotechnology", "sector": "Pharma"},
            {"ticker": "IONS", "name": "Ionis Pharmaceuticals", "industry": "Biotechnology", "sector": "Pharma"},
            {"ticker": "BMRN", "name": "BioMarin Pharmaceutical", "industry": "Biotechnology", "sector": "Pharma"},
            {"ticker": "HALO", "name": "Halozyme Therapeutics", "industry": "Biotechnology", "sector": "Pharma"},
            {"ticker": "RARE", "name": "Ultragenyx Pharmaceutical", "industry": "Biotechnology", "sector": "Pharma"},
            {"ticker": "UTHR", "name": "United Therapeutics", "industry": "Biotechnology", "sector": "Pharma"},
            {"ticker": "CYTK", "name": "Cytokinetics Inc.", "industry": "Biotechnology", "sector": "Pharma"},
            
            # Finance & Banking
            {"ticker": "JPM", "name": "JPMorgan Chase & Co.", "industry": "Banking", "sector": "Finance"},
            {"ticker": "BAC", "name": "Bank of America", "industry": "Banking", "sector": "Finance"},
            {"ticker": "WFC", "name": "Wells Fargo", "industry": "Banking", "sector": "Finance"},
            {"ticker": "C", "name": "Citigroup Inc.", "industry": "Banking", "sector": "Finance"},
            {"ticker": "GS", "name": "Goldman Sachs", "industry": "Investment Banking", "sector": "Finance"},
            {"ticker": "MS", "name": "Morgan Stanley", "industry": "Investment Banking", "sector": "Finance"},
            {"ticker": "BLK", "name": "BlackRock Inc.", "industry": "Asset Management", "sector": "Finance"},
            {"ticker": "SCHW", "name": "Charles Schwab", "industry": "Financial Services", "sector": "Finance"},
            {"ticker": "USB", "name": "U.S. Bancorp", "industry": "Banking", "sector": "Finance"},
            {"ticker": "PNC", "name": "PNC Financial Services", "industry": "Banking", "sector": "Finance"},
            {"ticker": "TFC", "name": "Truist Financial", "industry": "Banking", "sector": "Finance"},
            {"ticker": "COF", "name": "Capital One Financial", "industry": "Banking", "sector": "Finance"},
            {"ticker": "AXP", "name": "American Express", "industry": "Financial Services", "sector": "Finance"},
            {"ticker": "BK", "name": "Bank of New York Mellon", "industry": "Banking", "sector": "Finance"},
            {"ticker": "STT", "name": "State Street Corporation", "industry": "Banking", "sector": "Finance"},
            
            # Payments & Fintech
            {"ticker": "V", "name": "Visa Inc.", "industry": "Payments", "sector": "Finance"},
            {"ticker": "MA", "name": "Mastercard Inc.", "industry": "Payments", "sector": "Finance"},
            {"ticker": "PYPL", "name": "PayPal Holdings", "industry": "Payments", "sector": "Finance"},
            {"ticker": "SQ", "name": "Block Inc.", "industry": "Payments", "sector": "Finance"},
            {"ticker": "COIN", "name": "Coinbase Global", "industry": "Cryptocurrency", "sector": "Finance"},
            {"ticker": "SOFI", "name": "SoFi Technologies", "industry": "Fintech", "sector": "Finance"},
            {"ticker": "AFRM", "name": "Affirm Holdings", "industry": "Fintech", "sector": "Finance"},
            {"ticker": "UPST", "name": "Upstart Holdings", "industry": "Fintech", "sector": "Finance"},
            
            # Insurance
            {"ticker": "BRK.B", "name": "Berkshire Hathaway", "industry": "Insurance", "sector": "Finance"},
            {"ticker": "PGR", "name": "Progressive Corporation", "industry": "Insurance", "sector": "Finance"},
            {"ticker": "ALL", "name": "Allstate Corporation", "industry": "Insurance", "sector": "Finance"},
            {"ticker": "MET", "name": "MetLife Inc.", "industry": "Insurance", "sector": "Finance"},
            {"ticker": "PRU", "name": "Prudential Financial", "industry": "Insurance", "sector": "Finance"},
            
            # Retail & Consumer
            {"ticker": "WMT", "name": "Walmart Inc.", "industry": "Retail", "sector": "Retail"},
            {"ticker": "COST", "name": "Costco Wholesale", "industry": "Retail", "sector": "Retail"},
            {"ticker": "HD", "name": "Home Depot", "industry": "Retail", "sector": "Retail"},
            {"ticker": "TGT", "name": "Target Corporation", "industry": "Retail", "sector": "Retail"},
            {"ticker": "LOW", "name": "Lowe's Companies", "industry": "Retail", "sector": "Retail"},
            {"ticker": "TJX", "name": "TJX Companies", "industry": "Retail", "sector": "Retail"},
            {"ticker": "DG", "name": "Dollar General", "industry": "Retail", "sector": "Retail"},
            {"ticker": "DLTR", "name": "Dollar Tree", "industry": "Retail", "sector": "Retail"},
            {"ticker": "BBY", "name": "Best Buy", "industry": "Retail", "sector": "Retail"},
            
            # Apparel & Fashion
            {"ticker": "NKE", "name": "Nike Inc.", "industry": "Apparel", "sector": "Retail"},
            {"ticker": "LULU", "name": "Lululemon Athletica", "industry": "Apparel", "sector": "Retail"},
            {"ticker": "GAP", "name": "Gap Inc.", "industry": "Apparel", "sector": "Retail"},
            {"ticker": "ROST", "name": "Ross Stores", "industry": "Apparel", "sector": "Retail"},
            {"ticker": "UAA", "name": "Under Armour", "industry": "Apparel", "sector": "Retail"},
            
            # Restaurants & Food
            {"ticker": "SBUX", "name": "Starbucks Corporation", "industry": "Restaurants", "sector": "Retail"},
            {"ticker": "MCD", "name": "McDonald's Corporation", "industry": "Restaurants", "sector": "Retail"},
            {"ticker": "CMG", "name": "Chipotle Mexican Grill", "industry": "Restaurants", "sector": "Retail"},
            {"ticker": "YUM", "name": "Yum! Brands", "industry": "Restaurants", "sector": "Retail"},
            {"ticker": "QSR", "name": "Restaurant Brands", "industry": "Restaurants", "sector": "Retail"},
            {"ticker": "DPZ", "name": "Domino's Pizza", "industry": "Restaurants", "sector": "Retail"},
            {"ticker": "WING", "name": "Wingstop Inc.", "industry": "Restaurants", "sector": "Retail"},
            {"ticker": "SHAK", "name": "Shake Shack", "industry": "Restaurants", "sector": "Retail"},
            
            # Beverages & Consumer Goods
            {"ticker": "KO", "name": "Coca-Cola Company", "industry": "Beverages", "sector": "Retail"},
            {"ticker": "PEP", "name": "PepsiCo Inc.", "industry": "Beverages", "sector": "Retail"},
            {"ticker": "MNST", "name": "Monster Beverage", "industry": "Beverages", "sector": "Retail"},
            {"ticker": "PG", "name": "Procter & Gamble", "industry": "Consumer Goods", "sector": "Retail"},
            {"ticker": "CL", "name": "Colgate-Palmolive", "industry": "Consumer Goods", "sector": "Retail"},
            {"ticker": "KMB", "name": "Kimberly-Clark", "industry": "Consumer Goods", "sector": "Retail"},
            
            # Gaming & Entertainment
            {"ticker": "EA", "name": "Electronic Arts", "industry": "Gaming", "sector": "Gaming"},
            {"ticker": "ATVI", "name": "Activision Blizzard", "industry": "Gaming", "sector": "Gaming"},
            {"ticker": "TTWO", "name": "Take-Two Interactive", "industry": "Gaming", "sector": "Gaming"},
            {"ticker": "RBLX", "name": "Roblox Corporation", "industry": "Gaming", "sector": "Gaming"},
            {"ticker": "U", "name": "Unity Software", "industry": "Gaming", "sector": "Gaming"},
            {"ticker": "DKNG", "name": "DraftKings Inc.", "industry": "Gaming", "sector": "Gaming"},
            {"ticker": "LNW", "name": "Light & Wonder", "industry": "Gaming", "sector": "Gaming"},
            {"ticker": "GLPI", "name": "Gaming and Leisure", "industry": "Gaming", "sector": "Gaming"},
            
            # Energy
            {"ticker": "XOM", "name": "Exxon Mobil", "industry": "Energy", "sector": "Other"},
            {"ticker": "CVX", "name": "Chevron Corporation", "industry": "Energy", "sector": "Other"},
            {"ticker": "COP", "name": "ConocoPhillips", "industry": "Energy", "sector": "Other"},
            {"ticker": "SLB", "name": "Schlumberger", "industry": "Energy", "sector": "Other"},
            {"ticker": "EOG", "name": "EOG Resources", "industry": "Energy", "sector": "Other"},
            {"ticker": "MPC", "name": "Marathon Petroleum", "industry": "Energy", "sector": "Other"},
            {"ticker": "PSX", "name": "Phillips 66", "industry": "Energy", "sector": "Other"},
            {"ticker": "VLO", "name": "Valero Energy", "industry": "Energy", "sector": "Other"},
            
            # Telecom
            {"ticker": "T", "name": "AT&T Inc.", "industry": "Telecom", "sector": "Other"},
            {"ticker": "VZ", "name": "Verizon Communications", "industry": "Telecom", "sector": "Other"},
            {"ticker": "TMUS", "name": "T-Mobile US", "industry": "Telecom", "sector": "Other"},
            
            # Aerospace & Defense
            {"ticker": "BA", "name": "Boeing Company", "industry": "Aerospace", "sector": "Other"},
            {"ticker": "LMT", "name": "Lockheed Martin", "industry": "Aerospace", "sector": "Other"},
            {"ticker": "RTX", "name": "Raytheon Technologies", "industry": "Aerospace", "sector": "Other"},
            {"ticker": "NOC", "name": "Northrop Grumman", "industry": "Aerospace", "sector": "Other"},
            {"ticker": "GD", "name": "General Dynamics", "industry": "Aerospace", "sector": "Other"},
            {"ticker": "LHX", "name": "L3Harris Technologies", "industry": "Aerospace", "sector": "Other"},
            
            # Industrials
            {"ticker": "CAT", "name": "Caterpillar Inc.", "industry": "Industrial", "sector": "Other"},
            {"ticker": "DE", "name": "Deere & Company", "industry": "Industrial", "sector": "Other"},
            {"ticker": "GE", "name": "General Electric", "industry": "Industrial", "sector": "Other"},
            {"ticker": "HON", "name": "Honeywell International", "industry": "Industrial", "sector": "Other"},
            {"ticker": "MMM", "name": "3M Company", "industry": "Industrial", "sector": "Other"},
            {"ticker": "UPS", "name": "United Parcel Service", "industry": "Logistics", "sector": "Other"},
            {"ticker": "FDX", "name": "FedEx Corporation", "industry": "Logistics", "sector": "Other"},
            
            # Automotive
            {"ticker": "F", "name": "Ford Motor Company", "industry": "Automotive", "sector": "Other"},
            {"ticker": "GM", "name": "General Motors", "industry": "Automotive", "sector": "Other"},
            {"ticker": "RIVN", "name": "Rivian Automotive", "industry": "Automotive", "sector": "Other"},
            {"ticker": "LCID", "name": "Lucid Group", "industry": "Automotive", "sector": "Other"},
        ]
        
        # Add companies
        for company_data in companies_data:
            company = Company(
                ticker=company_data["ticker"],
                name=company_data["name"],
                industry=company_data["industry"],
                tracked=False
            )
            db.add(company)
        
        db.commit()
        print(f"Added {len(companies_data)} companies")
        
        # Generate upcoming events for all companies
        base_date = datetime.now()
        event_templates = [
            {"type": "Product Launch", "titles": [
                "{company} announces new product lineup for {year}",
                "{company} unveils next-generation innovation",
                "{company} reveals breakthrough technology advancement",
                "{company} set to launch flagship product update"
            ]},
            {"type": "Earnings Report", "titles": [
                "{company} Q{quarter} {year} Earnings Call",
                "{company} Quarterly Financial Results Release",
                "{company} Investor Conference Q{quarter} {year}"
            ]},
            {"type": "Investor Day", "titles": [
                "{company} Annual Investor Day {year}",
                "{company} Strategic Vision Presentation",
                "{company} Long-term Growth Strategy Unveiling"
            ]},
            {"type": "Conference", "titles": [
                "{company} Developer Conference {year}",
                "{company} Annual User Summit",
                "{company} Technology Showcase Event"
            ]},
            {"type": "Regulatory Filing", "titles": [
                "{company} Expected FDA Decision Date",
                "{company} Clinical Trial Results Publication",
                "{company} Regulatory Approval Milestone"
            ]}
        ]
        
        events_added = 0
        for company_data in companies_data:
            # Add 2-4 upcoming events per company
            num_events = random.randint(2, 4)
            
            for i in range(num_events):
                days_ahead = random.randint(7, 180)
                event_date = base_date + timedelta(days=days_ahead)
                
                template = random.choice(event_templates)
                title_template = random.choice(template["titles"])
                
                quarter = random.randint(1, 4)
                year = event_date.year
                
                title = title_template.format(
                    company=company_data["name"],
                    quarter=quarter,
                    year=year
                )
                
                impact_score = random.randint(60, 90)
                
                event = Event(
                    ticker=company_data["ticker"],
                    company=company_data["name"],
                    event_type=template["type"],
                    title=title,
                    description=f"Upcoming {template['type'].lower()} event for {company_data['name']}",
                    date=event_date.strftime('%Y-%m-%d'),
                    impact_score=impact_score,
                    source="Manual Entry",
                    sector=company_data["sector"],
                    is_favorite=False
                )
                db.add(event)
                events_added += 1
        
        db.commit()
        print(f"Added {events_added} upcoming events")
        print("Database population completed successfully!")
        
    except Exception as e:
        print(f"Error populating database: {e}")
        db.rollback()
    finally:
        close_db_session(db)

if __name__ == "__main__":
    populate_database()
