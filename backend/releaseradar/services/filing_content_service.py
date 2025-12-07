"""
Filing Content Service - Fetches and parses actual SEC/FDA filing content.

Selectively reads full content for high-value filings:
- 8-K filings with items 1.01, 2.01, 2.02, 7.01
- FDA approval letters and announcements
- Major SEC filings (S-1, 13D)

Implements caching to avoid redundant fetches and respects rate limits.
"""

import os
import re
import hashlib
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import requests
from bs4 import BeautifulSoup
import trafilatura
from loguru import logger

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


@dataclass
class FilingContent:
    """Parsed filing content with metadata."""
    source_url: str
    content_type: str
    raw_text: str
    extracted_text: str
    key_sections: Dict[str, str]
    financial_data: Dict[str, Any]
    fetched_at: datetime
    cache_key: str
    error: Optional[str] = None


class FilingContentCache:
    """Simple in-memory cache for filing content with TTL."""
    
    def __init__(self, max_size: int = 500, ttl_hours: int = 24):
        self._cache: Dict[str, Tuple[FilingContent, datetime]] = {}
        self._max_size = max_size
        self._ttl = timedelta(hours=ttl_hours)
    
    def get(self, key: str) -> Optional[FilingContent]:
        if key in self._cache:
            content, timestamp = self._cache[key]
            if content.error:
                del self._cache[key]
                return None
            if datetime.utcnow() - timestamp < self._ttl:
                return content
            else:
                del self._cache[key]
        return None
    
    def set(self, key: str, content: FilingContent):
        if content.error:
            return
        if len(self._cache) >= self._max_size:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]
        self._cache[key] = (content, datetime.utcnow())
    
    def clear(self):
        self._cache.clear()


class FilingContentService:
    """
    Service for fetching and parsing actual SEC/FDA filing content.
    
    Implements selective reading for high-value filings to balance
    accuracy improvements with cost and rate limit considerations.
    """
    
    HIGH_VALUE_8K_ITEMS = {"1.01", "2.01", "2.02", "7.01", "8.01"}
    
    SEC_EDGAR_BASE = "https://www.sec.gov"
    FDA_BASE = "https://www.fda.gov"
    
    USER_AGENT = "Impact Radar Filing Analyzer contact@impactradar.com"
    
    def __init__(self):
        self._cache = FilingContentCache()
        self._last_sec_request = datetime.min
        self._sec_rate_limit_delay = 0.2
    
    def _generate_cache_key(self, url: str) -> str:
        """Generate cache key from URL."""
        return hashlib.md5(url.encode()).hexdigest()
    
    def should_fetch_full_content(
        self,
        event_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Determine if this event type warrants full content fetching.
        
        Args:
            event_type: The event type (sec_8k, fda_approval, etc.)
            metadata: Event metadata including 8K items, etc.
            
        Returns:
            True if full content should be fetched
        """
        metadata = metadata or {}
        
        if event_type == "sec_8k":
            items = metadata.get("8k_items", [])
            if items:
                return any(item in self.HIGH_VALUE_8K_ITEMS for item in items)
            return True
        
        if event_type in ["fda_approval", "fda_rejection", "fda_crl", "fda_adcom"]:
            return True
        
        if event_type in ["sec_13d", "sec_s1", "merger_acquisition"]:
            return True
        
        if event_type in ["guidance_raise", "guidance_lower", "guidance_withdraw"]:
            return True
        
        return False
    
    def fetch_filing_content(
        self,
        source_url: str,
        event_type: str,
        use_cache: bool = True
    ) -> FilingContent:
        """
        Fetch and parse filing content from source URL.
        
        Args:
            source_url: URL to the filing
            event_type: Type of event for parsing hints
            use_cache: Whether to use cached content
            
        Returns:
            FilingContent with parsed text and extracted data
        """
        cache_key = self._generate_cache_key(source_url)
        
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for {source_url[:50]}...")
                return cached
        
        try:
            if "sec.gov" in source_url:
                content = self._fetch_sec_filing(source_url, event_type)
            elif "fda.gov" in source_url:
                content = self._fetch_fda_content(source_url, event_type)
            else:
                content = self._fetch_generic_content(source_url, event_type)
            
            content.cache_key = cache_key
            self._cache.set(cache_key, content)
            return content
            
        except Exception as e:
            logger.error(f"Error fetching filing from {source_url}: {e}")
            return FilingContent(
                source_url=source_url,
                content_type=event_type,
                raw_text="",
                extracted_text="",
                key_sections={},
                financial_data={},
                fetched_at=datetime.utcnow(),
                cache_key=cache_key,
                error=str(e)
            )
    
    def _respect_sec_rate_limit(self):
        """Ensure we respect SEC EDGAR rate limits (10 requests/second max)."""
        import time
        elapsed = (datetime.utcnow() - self._last_sec_request).total_seconds()
        if elapsed < self._sec_rate_limit_delay:
            time.sleep(self._sec_rate_limit_delay - elapsed)
        self._last_sec_request = datetime.utcnow()
    
    def _fetch_sec_filing(self, url: str, event_type: str) -> FilingContent:
        """Fetch and parse SEC EDGAR filing."""
        self._respect_sec_rate_limit()
        
        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml",
            "Accept-Encoding": "gzip, deflate",
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        raw_text = response.text
        
        extracted_text = trafilatura.extract(
            raw_text,
            include_tables=True,
            include_comments=False,
            no_fallback=False
        ) or ""
        
        key_sections = self._extract_8k_sections(raw_text, extracted_text)
        financial_data = self._extract_financial_numbers(extracted_text)
        
        return FilingContent(
            source_url=url,
            content_type=event_type,
            raw_text=raw_text[:50000],
            extracted_text=extracted_text[:20000],
            key_sections=key_sections,
            financial_data=financial_data,
            fetched_at=datetime.utcnow(),
            cache_key=""
        )
    
    def _fetch_fda_content(self, url: str, event_type: str) -> FilingContent:
        """Fetch and parse FDA announcement content."""
        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        raw_text = response.text
        
        extracted_text = trafilatura.extract(
            raw_text,
            include_tables=True,
            no_fallback=False
        ) or ""
        
        key_sections = self._extract_fda_sections(raw_text, extracted_text)
        
        return FilingContent(
            source_url=url,
            content_type=event_type,
            raw_text=raw_text[:50000],
            extracted_text=extracted_text[:20000],
            key_sections=key_sections,
            financial_data={},
            fetched_at=datetime.utcnow(),
            cache_key=""
        )
    
    def _fetch_generic_content(self, url: str, event_type: str) -> FilingContent:
        """Fetch and parse generic web content."""
        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        raw_text = response.text
        
        extracted_text = trafilatura.extract(
            raw_text,
            include_tables=True,
            no_fallback=False
        ) or ""
        
        return FilingContent(
            source_url=url,
            content_type=event_type,
            raw_text=raw_text[:30000],
            extracted_text=extracted_text[:15000],
            key_sections={},
            financial_data=self._extract_financial_numbers(extracted_text),
            fetched_at=datetime.utcnow(),
            cache_key=""
        )
    
    def _extract_8k_sections(self, raw_html: str, text: str) -> Dict[str, str]:
        """Extract key sections from 8-K filing."""
        sections = {}
        
        item_patterns = [
            (r"Item\s*1\.01[:\s\-]+(.{100,2000}?)(?=Item\s*\d|$)", "entry_material_agreement"),
            (r"Item\s*2\.01[:\s\-]+(.{100,2000}?)(?=Item\s*\d|$)", "acquisition_disposition"),
            (r"Item\s*2\.02[:\s\-]+(.{100,2000}?)(?=Item\s*\d|$)", "results_operations"),
            (r"Item\s*2\.06[:\s\-]+(.{100,2000}?)(?=Item\s*\d|$)", "asset_impairment"),
            (r"Item\s*5\.02[:\s\-]+(.{100,2000}?)(?=Item\s*\d|$)", "officer_departure"),
            (r"Item\s*7\.01[:\s\-]+(.{100,2000}?)(?=Item\s*\d|$)", "regulation_fd"),
            (r"Item\s*8\.01[:\s\-]+(.{100,2000}?)(?=Item\s*\d|$)", "other_events"),
        ]
        
        for pattern, section_name in item_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                sections[section_name] = match.group(1).strip()[:2000]
        
        return sections
    
    def _extract_fda_sections(self, raw_html: str, text: str) -> Dict[str, str]:
        """Extract key sections from FDA announcement."""
        sections = {}
        
        approval_match = re.search(
            r"(approved|granted approval|received approval).{0,500}",
            text, re.IGNORECASE
        )
        if approval_match:
            sections["approval_statement"] = approval_match.group(0)[:500]
        
        indication_match = re.search(
            r"(treatment of|indicated for|approved for).{0,300}",
            text, re.IGNORECASE
        )
        if indication_match:
            sections["indication"] = indication_match.group(0)[:300]
        
        conditions_match = re.search(
            r"(conditions?|restrictions?|requirements?|black box|warning).{0,500}",
            text, re.IGNORECASE
        )
        if conditions_match:
            sections["conditions"] = conditions_match.group(0)[:500]
        
        drug_match = re.search(
            r"([A-Z][a-z]+(?:mab|nib|zumab|tinib|ciclib|lisib))",
            text
        )
        if drug_match:
            sections["drug_name"] = drug_match.group(1)
        
        return sections
    
    def _extract_financial_numbers(self, text: str) -> Dict[str, Any]:
        """Extract financial numbers from text."""
        data = {}
        
        revenue_match = re.search(
            r"revenue[s]?\s+(?:of\s+)?\$?([\d,.]+)\s*(billion|million|B|M)?",
            text, re.IGNORECASE
        )
        if revenue_match:
            amount = float(revenue_match.group(1).replace(",", ""))
            unit = (revenue_match.group(2) or "").lower()
            if unit in ["billion", "b"]:
                amount *= 1_000_000_000
            elif unit in ["million", "m"]:
                amount *= 1_000_000
            data["revenue"] = amount
        
        eps_match = re.search(
            r"(?:EPS|earnings per share)[:\s]+\$?([\d.]+)",
            text, re.IGNORECASE
        )
        if eps_match:
            data["eps"] = float(eps_match.group(1))
        
        guidance_match = re.search(
            r"(?:guidance|outlook|expects?|forecast)[:\s]+.{0,100}?\$?([\d,.]+)\s*(?:to|-)\s*\$?([\d,.]+)",
            text, re.IGNORECASE
        )
        if guidance_match:
            data["guidance_low"] = float(guidance_match.group(1).replace(",", ""))
            data["guidance_high"] = float(guidance_match.group(2).replace(",", ""))
        
        percent_matches = re.findall(
            r"([\d.]+)\s*%\s*(increase|decrease|growth|decline|up|down)",
            text, re.IGNORECASE
        )
        if percent_matches:
            data["percentage_changes"] = [
                {"value": float(m[0]), "direction": m[1].lower()}
                for m in percent_matches[:5]
            ]
        
        return data
    
    def get_filing_summary_for_ai(
        self,
        source_url: str,
        event_type: str,
        max_length: int = 4000
    ) -> str:
        """
        Get a formatted summary of filing content suitable for AI analysis.
        
        Args:
            source_url: URL to the filing
            event_type: Type of event
            max_length: Maximum length of the summary
            
        Returns:
            Formatted string with key filing content
        """
        content = self.fetch_filing_content(source_url, event_type)
        
        if content.error:
            return f"[Unable to fetch filing content: {content.error}]"
        
        parts = []
        
        if content.key_sections:
            parts.append("KEY FILING SECTIONS:")
            for section_name, section_text in content.key_sections.items():
                parts.append(f"\n{section_name.upper().replace('_', ' ')}:")
                parts.append(section_text[:800])
        
        if content.financial_data:
            parts.append("\n\nEXTRACTED FINANCIAL DATA:")
            for key, value in content.financial_data.items():
                if key == "percentage_changes":
                    for change in value:
                        parts.append(f"- {change['value']}% {change['direction']}")
                else:
                    parts.append(f"- {key}: {value}")
        
        if not parts and content.extracted_text:
            parts.append("FILING CONTENT EXCERPT:")
            parts.append(content.extracted_text[:3000])
        
        summary = "\n".join(parts)
        
        if len(summary) > max_length:
            summary = summary[:max_length - 20] + "\n[...truncated]"
        
        return summary


_filing_service_instance: Optional[FilingContentService] = None


def get_filing_content_service() -> FilingContentService:
    """Get singleton instance of FilingContentService."""
    global _filing_service_instance
    if _filing_service_instance is None:
        _filing_service_instance = FilingContentService()
    return _filing_service_instance
