"""
Advanced Event Generation System for Impact Radar

Generates realistic events for 1000+ companies with:
- Proper impact scoring using ImpactScorer
- Confidence percentages based on event type
- Linked sources (SEC EDGAR, FDA.gov, company websites)
- Probabilistic scoring integration
- Sector-aware event types
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import random
from loguru import logger
from impact_scoring import ImpactScorer

# Import probabilistic scoring if available
try:
    from impact_models.definitions import DEFAULT_IMPACT_TARGET
    from impact_models.event_study import p_move, p_up, p_down
    from impact_models.confidence import compute_confidence
    PROB_SCORING = True
except ImportError:
    PROB_SCORING = False
    logger.warning("Probabilistic scoring not available")


class ComprehensiveEventGenerator:
    """Generates realistic, scored events for companies."""
    
    # Event templates by sector with realistic patterns
    EVENT_TEMPLATES = {
        'Tech': [
            {
                'type': 'sec_8k',
                'titles': [
                    '{company} Files 8-K: Material Agreement Disclosure',
                    '{company} Reports Entry into Strategic Partnership (8-K)',
                    '{company} 8-K Filing: Departure of Directors/Officers',
                    '{company} Files Current Report on Material Events',
                ],
                'descriptions': [
                    'Material agreement entered or amended',
                    'Changes in control or management structure',
                    'Results of operations and financial condition update',
                    'Regulation FD disclosure of material information',
                ],
                'source_template': 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type=8-K',
            },
            {
                'type': 'sec_10q',
                'titles': [
                    '{company} Files Q{quarter} {year} 10-Q Quarterly Report',
                    '{company} Quarterly Report Filing - Q{quarter} {year}',
                ],
                'descriptions': [
                    'Comprehensive overview of company financial position for the quarter',
                ],
                'source_template': 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type=10-Q',
            },
            {
                'type': 'earnings',
                'titles': [
                    '{company} Q{quarter} {year} Earnings Call',
                    '{company} Reports Q{quarter} {year} Financial Results',
                    '{company} Announces Quarterly Earnings - Q{quarter} {year}',
                ],
                'descriptions': [
                    'Quarterly earnings conference call and financial results',
                    'Revenue, EPS, and forward guidance disclosure',
                ],
                'source_template': 'https://investor.{domain}/quarterly-results',
            },
            {
                'type': 'product_launch',
                'titles': [
                    '{company} Announces New Product Release',
                    '{company} Unveils Next-Generation Platform',
                    '{company} Launches Enterprise Solution Update',
                ],
                'descriptions': [
                    'Major product release with new features and capabilities',
                    'Platform expansion targeting enterprise customers',
                ],
                'source_template': 'https://{domain}/newsroom/product-launch',
            },
        ],
        'Pharma': [
            {
                'type': 'fda_announcement',
                'titles': [
                    'FDA Schedules Advisory Committee Meeting for {company} Drug Candidate',
                    '{company} PDUFA Date Set by FDA',
                    'FDA Accepts {company} New Drug Application for Review',
                    '{company} Receives FDA Fast Track Designation',
                ],
                'descriptions': [
                    'FDA regulatory milestone for drug candidate',
                    'Advisory committee review scheduled',
                    'Prescription Drug User Fee Act (PDUFA) action date announced',
                ],
                'source_template': 'https://www.fda.gov/drugs/news-events-human-drugs/',
            },
            {
                'type': 'sec_8k',
                'titles': [
                    '{company} Files 8-K: Clinical Trial Results',
                    '{company} Reports Material Clinical Data (8-K)',
                    '{company} 8-K Filing: Regulatory Update',
                ],
                'descriptions': [
                    'Disclosure of material clinical trial data',
                    'Update on regulatory submission timeline',
                ],
                'source_template': 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type=8-K',
            },
            {
                'type': 'earnings',
                'titles': [
                    '{company} Q{quarter} {year} Earnings Call',
                    '{company} Reports Quarterly Financial Results',
                ],
                'descriptions': [
                    'Quarterly financial results and pipeline updates',
                ],
                'source_template': 'https://investor.{domain}/quarterly-results',
            },
        ],
        'Finance': [
            {
                'type': 'sec_8k',
                'titles': [
                    '{company} Files 8-K: Material Agreement',
                    '{company} Reports Asset Acquisition (8-K)',
                    '{company} 8-K Filing: Results of Operations Update',
                ],
                'descriptions': [
                    'Material definitive agreement disclosure',
                    'Asset acquisition or disposition',
                ],
                'source_template': 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type=8-K',
            },
            {
                'type': 'earnings',
                'titles': [
                    '{company} Q{quarter} {year} Earnings Release',
                    '{company} Reports Financial Results',
                ],
                'descriptions': [
                    'Quarterly financial results and capital allocation update',
                ],
                'source_template': 'https://investor.{domain}/earnings',
            },
            {
                'type': 'analyst_day',
                'titles': [
                    '{company} Investor Day {year}',
                    '{company} Strategic Update Presentation',
                ],
                'descriptions': [
                    'Annual investor day with long-term strategy presentation',
                ],
                'source_template': 'https://investor.{domain}/events',
            },
        ],
        'Retail': [
            {
                'type': 'earnings',
                'titles': [
                    '{company} Q{quarter} {year} Earnings Report',
                    '{company} Same-Store Sales Results - Q{quarter} {year}',
                ],
                'descriptions': [
                    'Quarterly comparable store sales and financial results',
                ],
                'source_template': 'https://investor.{domain}/financials',
            },
            {
                'type': 'product_launch',
                'titles': [
                    '{company} Announces New Product Line',
                    '{company} Launches Seasonal Collection',
                ],
                'descriptions': [
                    'New product line launch targeting key demographics',
                ],
                'source_template': 'https://{domain}/press-releases',
            },
        ],
        'Other': [
            {
                'type': 'sec_8k',
                'titles': [
                    '{company} Files 8-K Current Report',
                    '{company} Material Event Disclosure (8-K)',
                ],
                'descriptions': [
                    'Material current event disclosure',
                ],
                'source_template': 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type=8-K',
            },
            {
                'type': 'earnings',
                'titles': [
                    '{company} Q{quarter} {year} Earnings',
                    '{company} Quarterly Results',
                ],
                'descriptions': [
                    'Quarterly financial results',
                ],
                'source_template': 'https://investor.{domain}/results',
            },
        ],
    }
    
    def __init__(self):
        self.scorer = ImpactScorer()
        logger.info(f"Event generator initialized (Probabilistic scoring: {PROB_SCORING})")
    
    def generate_source_url(self, ticker: str, domain: str, template: str) -> str:
        """Generate realistic source URL based on template."""
        # Clean domain for URL
        clean_domain = domain.lower().replace(' ', '').replace('.', '')[:20] + '.com'
        return template.format(ticker=ticker, domain=clean_domain)
    
    def generate_events_for_company(
        self,
        company: Dict,
        num_events: int = None,
        days_range: Tuple[int, int] = (7, 180)
    ) -> List[Dict]:
        """
        Generate realistic events for a company.
        
        Args:
            company: Company dict with ticker, name, sector, industry, market_cap
            num_events: Number of events to generate (if None, uses random 2-5)
            days_range: Tuple of (min_days, max_days) for event dates
            
        Returns:
            List of event dictionaries ready for database insertion
        """
        ticker = company['ticker']
        name = company['name']
        sector = company['sector']
        market_cap = company['market_cap']
        
        # Determine number of events based on company size
        if num_events is None:
            if market_cap == 'mega':
                num_events = random.randint(4, 6)  # Mega caps get more events
            elif market_cap == 'large':
                num_events = random.randint(3, 5)
            elif market_cap == 'mid':
                num_events = random.randint(2, 4)
            else:
                num_events = random.randint(1, 3)  # Small caps get fewer
        
        events = []
        base_date = datetime.now()
        
        # Get appropriate templates for sector
        templates = self.EVENT_TEMPLATES.get(sector, self.EVENT_TEMPLATES['Other'])
        
        for i in range(num_events):
            # Select random template
            template = random.choice(templates)
            
            # Generate event date
            days_ahead = random.randint(days_range[0], days_range[1])
            event_date = base_date + timedelta(days=days_ahead)
            
            # Format title and description
            quarter = random.randint(1, 4)
            year = event_date.year
            
            title = random.choice(template['titles']).format(
                company=name,
                quarter=quarter,
                year=year
            )
            
            description = random.choice(template['descriptions'])
            
            # Generate source URL
            source_url = self.generate_source_url(
                ticker,
                name,
                template['source_template']
            )
            
            # Score the event using ImpactScorer
            impact_score, direction, confidence, rationale = self.scorer.score_event(
                event_type=template['type'],
                title=title,
                description=description,
                sector=sector,
                market_cap=market_cap
            )
            
            # Add probabilistic scores if available
            p_move_val = p_up_val = p_down_val = None
            if PROB_SCORING:
                try:
                    p_move_val = p_move(template['type'], sector, market_cap)
                    p_up_val = p_up(template['type'], sector, market_cap)
                    p_down_val = p_down(template['type'], sector, market_cap)
                except Exception as e:
                    logger.debug(f"Prob scoring failed for {ticker}: {e}")
            
            event = {
                'ticker': ticker,
                'company': name,
                'event_type': template['type'],
                'title': title,
                'description': description,
                'date': event_date.strftime('%Y-%m-%d'),
                'impact_score': impact_score,
                'direction': direction,
                'confidence': confidence,
                'rationale': rationale,
                'source_url': source_url,
                'sector': sector,
                'p_move': p_move_val,
                'p_up': p_up_val,
                'p_down': p_down_val,
            }
            
            events.append(event)
        
        return events
    
    def generate_batch(
        self,
        companies: List[Dict],
        events_per_company: int = None
    ) -> List[Dict]:
        """
        Generate events for a batch of companies.
        
        Args:
            companies: List of company dictionaries
            events_per_company: Fixed number of events per company (if None, varies by size)
            
        Returns:
            List of all generated events
        """
        all_events = []
        
        for i, company in enumerate(companies):
            if i % 100 == 0:
                logger.info(f"Generated events for {i}/{len(companies)} companies")
            
            events = self.generate_events_for_company(
                company,
                num_events=events_per_company
            )
            all_events.extend(events)
        
        logger.info(f"Total events generated: {len(all_events)}")
        return all_events


def test_event_generation():
    """Test event generation with sample companies."""
    generator = ComprehensiveEventGenerator()
    
    test_companies = [
        {
            'ticker': 'AAPL',
            'name': 'Apple Inc.',
            'sector': 'Tech',
            'industry': 'Technology',
            'market_cap': 'mega'
        },
        {
            'ticker': 'MRNA',
            'name': 'Moderna Inc.',
            'sector': 'Pharma',
            'industry': 'Biotechnology',
            'market_cap': 'large'
        },
        {
            'ticker': 'JPM',
            'name': 'JPMorgan Chase & Co.',
            'sector': 'Finance',
            'industry': 'Banking',
            'market_cap': 'mega'
        },
    ]
    
    events = generator.generate_batch(test_companies)
    
    print(f"\n=== Generated {len(events)} Events ===\n")
    for event in events[:5]:
        print(f"Ticker: {event['ticker']}")
        print(f"Title: {event['title']}")
        print(f"Type: {event['event_type']}")
        print(f"Score: {event['impact_score']} | Direction: {event['direction']} | Confidence: {event['confidence']:.0%}")
        print(f"Source: {event['source_url']}")
        if event.get('p_move'):
            print(f"Probabilistic: p_move={event['p_move']:.3f}, p_up={event['p_up']:.3f}, p_down={event['p_down']:.3f}")
        print()


if __name__ == "__main__":
    test_event_generation()
