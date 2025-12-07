"""
Scanner Service for Impact Radar

Background service for automated SEC, FDA, and company release scanning.
Scanners run GLOBALLY across all companies, not just user favorites.
All impact scoring is delegated to impact_scoring.py.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from typing import List, Dict, Optional
from data_manager import DataManager
from impact_scoring import score_event


class ScannerService:
    """
    Background scanning service for event ingestion.
    
    Key Design Principles:
    - Scanners run GLOBALLY for all tracked companies
    - Watchlists only affect what users SEE, not what gets ingested
    - All duplicate checking happens before insertion
    - Impact scoring is deterministic via impact_scoring.py
    """
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.data_manager = DataManager()
        self.is_running = False
    
    def start(self) -> None:
        """Start all scheduled scanners."""
        if not self.is_running:
            # Schedule SEC scanner - every 4 hours
            self.scheduler.add_job(
                func=self.scan_sec_filings,
                trigger=IntervalTrigger(hours=4),
                id='sec_scanner',
                name='SEC EDGAR Scanner',
                replace_existing=True
            )
            
            # Schedule FDA scanner - every 6 hours
            self.scheduler.add_job(
                func=self.scan_fda_announcements,
                trigger=IntervalTrigger(hours=6),
                id='fda_scanner',
                name='FDA Scanner',
                replace_existing=True
            )
            
            # Schedule company releases scanner - every 8 hours
            self.scheduler.add_job(
                func=self.scan_company_releases,
                trigger=IntervalTrigger(hours=8),
                id='company_releases_scanner',
                name='Company Releases Scanner',
                replace_existing=True
            )
            
            self.scheduler.start()
            self.is_running = True
            self.data_manager.add_scanner_log('System', 'All scanners started', 'info')
    
    def stop(self) -> None:
        """Stop all scheduled scanners."""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            self.data_manager.add_scanner_log('System', 'All scanners stopped', 'info')
    
    def scan_sec_filings(self) -> Dict:
        """
        Scan SEC EDGAR for new filings across all tracked companies.
        
        Returns:
            Summary dictionary with scan results
        """
        try:
            self.data_manager.add_scanner_log('SEC', 'Starting SEC EDGAR scan', 'info')
            
            # Get ALL tracked companies (not just user favorites)
            companies = self.data_manager.get_companies(tracked_only=True)
            
            new_filings = 0
            errors = []
            
            for company in companies:
                try:
                    # Import scraper functions
                    from web_scraper import scrape_sec_filings
                    
                    ticker = company['ticker']
                    filings = scrape_sec_filings(ticker, limit=3)
                    
                    if filings:
                        for filing in filings:
                            # Only process material filing types
                            material_forms = ['8-K', '10-Q', '10-K', 'S-1', '13D', '13G', 'DEF 14A']
                            
                            if not any(form in filing['form_type'] for form in material_forms):
                                continue
                            
                            # Determine event type based on form
                            event_type = self._map_sec_form_to_event_type(filing['form_type'])
                            
                            # Parse filing date
                            filing_date = self._parse_date(filing['filing_date'])
                            
                            # Check for duplicates
                            if self.data_manager.event_exists(
                                ticker=ticker,
                                event_type=event_type,
                                date=filing_date,
                                title=filing['description'][:100] if filing.get('description') else filing['form_type']
                            ):
                                continue
                            
                            # Create event with auto-scoring
                            self.data_manager.add_event(
                                ticker=ticker,
                                company_name=company['name'],
                                event_type=event_type,
                                title=f"{filing['form_type']}: {filing.get('description', 'Material Event Disclosure')[:80]}",
                                description=filing.get('description'),
                                date=filing_date,
                                source='SEC',
                                source_url=filing.get('filing_url'),
                                sector=company.get('sector'),
                                auto_score=True
                            )
                            
                            new_filings += 1
                            self.data_manager.add_scanner_log(
                                'SEC',
                                f"Found {filing['form_type']} for {ticker}: {filing.get('description', '')[:50]}",
                                'info'
                            )
                
                except Exception as e:
                    error_msg = f"Error scanning {company['ticker']}: {str(e)}"
                    errors.append(error_msg)
                    self.data_manager.add_scanner_log('SEC', error_msg, 'error')
            
            summary_msg = f"SEC scan complete: {new_filings} new filings found"
            if errors:
                summary_msg += f", {len(errors)} errors"
            
            self.data_manager.add_scanner_log('SEC', summary_msg, 'info')
            
            return {
                'success': True,
                'new_events': new_filings,
                'errors': errors,
                'companies_scanned': len(companies)
            }
            
        except Exception as e:
            error_msg = f"Fatal error in SEC scanner: {str(e)}"
            self.data_manager.add_scanner_log('SEC', error_msg, 'error')
            return {
                'success': False,
                'error': error_msg
            }
    
    def scan_fda_announcements(self) -> Dict:
        """
        Scan FDA for new announcements across relevant companies.
        
        Returns:
            Summary dictionary with scan results
        """
        try:
            self.data_manager.add_scanner_log('FDA', 'Starting FDA announcements scan', 'info')
            
            # Get pharma/biotech companies
            companies = self.data_manager.get_companies(tracked_only=True)
            pharma_companies = [
                c for c in companies
                if c.get('sector') in ['Pharma', 'Biotech'] or
                c.get('industry') in ['Pharmaceuticals', 'Biotechnology', 'Healthcare']
            ]
            
            new_events = 0
            errors = []
            
            try:
                from web_scraper import scrape_fda_announcements
                
                announcements = scrape_fda_announcements()
                
                if announcements:
                    for announcement in announcements[:10]:  # Process top 10
                        # Match to pharma companies
                        for company in pharma_companies:
                            # Simple matching by company name or ticker in announcement
                            if (company['name'].lower() in announcement['title'].lower() or
                                company['ticker'].lower() in announcement['title'].lower()):
                                
                                # Determine FDA event type from title
                                event_type = self._classify_fda_event(announcement['title'])
                                
                                # Parse date
                                event_date = self._parse_date(
                                    announcement.get('date', datetime.utcnow().strftime('%Y-%m-%d'))
                                )
                                
                                # Check duplicates
                                if self.data_manager.event_exists(
                                    ticker=company['ticker'],
                                    event_type=event_type,
                                    date=event_date,
                                    title=announcement['title'][:100]
                                ):
                                    continue
                                
                                # Create event with auto-scoring
                                self.data_manager.add_event(
                                    ticker=company['ticker'],
                                    company_name=company['name'],
                                    event_type=event_type,
                                    title=announcement['title'][:100],
                                    description=f"FDA announcement: {announcement['title']}",
                                    date=event_date,
                                    source='FDA',
                                    source_url=announcement.get('url'),
                                    sector=company.get('sector'),
                                    auto_score=True
                                )
                                
                                new_events += 1
                                self.data_manager.add_scanner_log(
                                    'FDA',
                                    f"Found FDA event for {company['ticker']}: {announcement['title'][:60]}",
                                    'info'
                                )
            
            except ImportError:
                self.data_manager.add_scanner_log('FDA', 'FDA scraper not available', 'warning')
            
            summary_msg = f"FDA scan complete: {new_events} new events found from {len(pharma_companies)} pharma companies"
            self.data_manager.add_scanner_log('FDA', summary_msg, 'info')
            
            return {
                'success': True,
                'new_events': new_events,
                'errors': errors,
                'companies_scanned': len(pharma_companies)
            }
            
        except Exception as e:
            error_msg = f"Fatal error in FDA scanner: {str(e)}"
            self.data_manager.add_scanner_log('FDA', error_msg, 'error')
            return {
                'success': False,
                'error': error_msg
            }
    
    def scan_company_releases(self) -> Dict:
        """
        Scan company IR/PR pages for new announcements.
        
        Returns:
            Summary dictionary with scan results
        """
        try:
            self.data_manager.add_scanner_log('Company Releases', 'Starting company releases scan', 'info')
            
            # Placeholder - extensible for IR/PR RSS or HTML scraping
            companies = self.data_manager.get_companies(tracked_only=True)
            
            self.data_manager.add_scanner_log(
                'Company Releases',
                f'Company releases scanner ready for {len(companies)} companies (implementation pending)',
                'info'
            )
            
            return {
                'success': True,
                'new_events': 0,
                'companies_scanned': len(companies)
            }
            
        except Exception as e:
            error_msg = f"Error in company releases scanner: {str(e)}"
            self.data_manager.add_scanner_log('Company Releases', error_msg, 'error')
            return {
                'success': False,
                'error': error_msg
            }
    
    def run_manual_scan(self) -> Dict:
        """
        Manually trigger all scanners immediately.
        
        Returns:
            Summary dictionary with combined results
        """
        self.data_manager.add_scanner_log('Manual Scan', 'Manual scan triggered by user', 'info')
        
        results = {
            'sec': self.scan_sec_filings(),
            'fda': self.scan_fda_announcements(),
            'company_releases': self.scan_company_releases()
        }
        
        total_new_events = sum(r.get('new_events', 0) for r in results.values())
        self.data_manager.add_scanner_log(
            'Manual Scan',
            f'Manual scan complete: {total_new_events} total new events discovered',
            'info'
        )
        
        return {
            'success': True,
            'total_new_events': total_new_events,
            'scanner_results': results
        }
    
    # ============================================================================
    # HELPER METHODS
    # ============================================================================
    
    def _map_sec_form_to_event_type(self, form_type: str) -> str:
        """Map SEC form type to standardized event type."""
        mapping = {
            '8-K': 'sec_8k',
            '10-K': 'sec_10k',
            '10-Q': 'sec_10q',
            'S-1': 'sec_s1',
            '13D': 'sec_13d',
            '13G': 'sec_13g',
            'DEF 14A': 'sec_def14a'
        }
        
        for key, value in mapping.items():
            if key in form_type:
                return value
        
        return 'sec_filing'  # Generic fallback
    
    def _classify_fda_event(self, title: str) -> str:
        """Classify FDA announcement into event type."""
        title_lower = title.lower()
        
        if 'approval' in title_lower or 'approved' in title_lower:
            return 'fda_approval'
        elif 'reject' in title_lower or 'rejection' in title_lower:
            return 'fda_rejection'
        elif 'advisory committee' in title_lower or 'adcom' in title_lower:
            return 'fda_adcom'
        elif 'complete response' in title_lower or 'crl' in title_lower:
            return 'fda_crl'
        elif 'safety' in title_lower or 'alert' in title_lower or 'warning' in title_lower:
            return 'fda_safety_alert'
        else:
            return 'fda_announcement'
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime object."""
        try:
            # Try common formats
            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S']:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            
            # Fallback to current time
            return datetime.utcnow()
        except:
            return datetime.utcnow()
    
    def get_status(self) -> Dict:
        """Get scanner status summary."""
        return {
            'is_running': self.is_running,
            'scanners': self.data_manager.get_scanner_status()
        }


# Global singleton instance
_scanner_service = None

def get_scanner_service() -> ScannerService:
    """Get the global scanner service instance."""
    global _scanner_service
    if _scanner_service is None:
        _scanner_service = ScannerService()
    return _scanner_service
