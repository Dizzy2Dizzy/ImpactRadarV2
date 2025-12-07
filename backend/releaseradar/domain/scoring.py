"""
Pure event impact scoring functions (migrated from impact_scoring.py).

All functions are deterministic with no side effects, making them easy to test.
Scoring logic remains identical to preserve existing behavior.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple


# Base scores by event type (must match events.py VALID_EVENT_TYPES)
EVENT_TYPE_SCORES = {
    # FDA Events (High impact for biotech/pharma)
    "fda_approval": 85,
    "fda_rejection": 80,
    "fda_adcom": 75,
    "fda_crl": 75,
    "fda_safety_alert": 70,
    "fda_announcement": 65,
    # SEC Filings
    "sec_8k": 65,
    "sec_10k": 55,
    "sec_10q": 50,
    "sec_s1": 70,
    "sec_13d": 75,
    "sec_13g": 60,
    "sec_def14a": 55,
    "sec_filing": 55,
    # Earnings & Guidance
    "earnings": 70,
    "guidance_raise": 75,
    "guidance_lower": 75,
    "guidance_withdraw": 80,
    # Corporate Actions
    "merger_acquisition": 85,
    "divestiture": 70,
    "restructuring": 65,
    "investigation": 75,
    "lawsuit": 65,
    "executive_change": 60,
    # Product Events
    "product_launch": 65,
    "product_delay": 70,
    "product_recall": 80,
    "flagship_launch": 75,
    # Other
    "analyst_day": 55,
    "conference_presentation": 45,
    "press_release": 50,
    "manual_entry": 50,
}

# Direction keywords for sentiment analysis - EXPANDED for better classification
POSITIVE_KEYWORDS = {
    # Earnings/Financial
    "approval", "approved", "beats", "beat", "exceeded", "exceeds", "topped",
    "surpassed", "above expectations", "better than expected", "eps beat",
    "revenue beat", "profit", "profitable", "record revenue", "record earnings",
    "record quarter", "outperform", "outperformed",
    # Guidance
    "raises", "raised", "upgrade", "upgraded", "upside", "higher guidance",
    "increased guidance", "reaffirm", "reaffirmed",
    # Growth
    "increase", "increased", "growth", "growing", "expand", "expansion",
    "accelerat", "momentum", "surge", "surged", "soar", "soared",
    # Success
    "positive", "success", "successful", "breakthrough", "milestone",
    "achievement", "accomplish", "won", "wins", "award", "awarded",
    # Deals/Partnerships
    "acquisition", "acquired", "partnership", "collaborate", "collaboration",
    "alliance", "contract", "deal", "agreement", "signed",
    # Product/Clinical
    "launch", "launches", "launched", "fda approval", "approved by fda",
    "positive results", "positive data", "met primary endpoint",
    # Financial Strength
    "strong", "robust", "gains", "dividend", "buyback", "repurchase",
    "cash flow", "margin improvement", "cost savings",
    # Leadership
    "appointed", "appointment", "hire", "hired", "new ceo", "new cfo",
    "promotes", "promoted", "named",
}

NEGATIVE_KEYWORDS = {
    # Earnings/Financial
    "reject", "rejected", "rejection", "misses", "missed", "miss",
    "below expectations", "worse than expected", "disappointed", "disappointing",
    "fell short", "shortfall", "underperform", "underperformed",
    "eps miss", "revenue miss", "loss", "losses", "net loss",
    # Guidance
    "lowers", "lowered", "downgrade", "downgraded", "downside",
    "lower guidance", "reduced guidance", "cut guidance", "withdraw",
    "withdrawn", "suspend", "suspended",
    # Decline
    "decrease", "decreased", "decline", "declining", "drop", "dropped",
    "fall", "fell", "plunge", "plunged", "slump", "tumble",
    # Failure
    "fail", "failed", "failure", "negative", "adverse",
    "did not meet", "failed to meet",
    # Legal/Regulatory
    "investigation", "investigated", "lawsuit", "sued", "litigation",
    "subpoena", "sec inquiry", "doj", "ftc", "probe", "fine", "fined",
    "penalty", "settlement", "violation",
    # Product Issues
    "recall", "recalled", "delay", "delayed", "postpone", "postponed",
    "discontinue", "discontinued", "terminate", "terminated",
    # Financial Distress
    "impairment", "write-off", "writeoff", "write-down", "writedown",
    "restructuring", "layoff", "layoffs", "workforce reduction",
    "cost cutting", "bankruptcy", "default", "defaulted", "delisting",
    # Leadership Departures
    "resign", "resigned", "resignation", "departure", "depart", "departed",
    "step down", "steps down", "stepping down", "leave", "leaving", "left",
    "exit", "exits", "exited", "retire", "retired", "retirement",
    # Concern
    "concern", "concerns", "warning", "warns", "warned", "weaken", "weak",
    "risk", "risks", "uncertainty", "uncertain", "headwind", "headwinds",
    "challenge", "challenges", "difficult", "tough",
    # SEC/Compliance
    "non-reliance", "restatement", "restated", "material weakness",
}

# Title-based patterns for quick classification (high confidence)
POSITIVE_TITLE_PATTERNS = {
    "beats", "exceeds", "raises guidance", "record", "approval", "approved",
    "acquisition", "partnership", "agreement", "contract win", "new ceo",
    "appointed", "positive results", "fda approval",
}

NEGATIVE_TITLE_PATTERNS = {
    "misses", "missed", "lowers guidance", "cuts guidance", "recall",
    "investigation", "lawsuit", "departure", "resign", "step down",
    "delisting", "bankruptcy", "layoff", "restructuring", "impairment",
    "write-off", "restatement", "non-reliance", "sec inquiry",
}

# 8-K subtypes that indicate direction (from SEC filing titles)
POSITIVE_8K_SUBTYPES = {
    "entry into material agreement", "completion of acquisition",
    "acquisition of assets", "product announcement", "service announcement",
}

NEGATIVE_8K_SUBTYPES = {
    "termination of material", "departure", "resignation", "non-reliance",
    "impairment", "delisting", "bankruptcy", "receivership", "default",
    "suspension of trading",
}

NEUTRAL_8K_SUBTYPES = {
    "regulation fd", "other events", "financial statements", "exhibits",
    "proxy", "results of operations", "submission of matters",
    "amendments to articles", "changes in certifying accountant",
    "unregistered sales",
}


@dataclass
class ScoringResult:
    """Result of event impact scoring."""
    
    impact_score: int
    direction: str
    confidence: float
    rationale: str


def determine_direction_from_8k_items(items: list, title: str = "", description: str = "") -> Tuple[str, float]:
    """
    Determine direction from 8-K item numbers with text analysis fallback.
    
    Args:
        items: List of 8-K item numbers (e.g., ["2.02", "5.02"])
        title: Event title for text analysis
        description: Event description for text analysis
        
    Returns:
        Tuple of (direction, confidence)
    """
    if not items:
        return analyze_text_for_direction(title, description)
    
    # Positive items (acquisitions, completed acquisitions, earnings results)
    positive_items = {"1.01", "2.01", "2.02"}
    
    # Negative items (impairments, delisting, non-reliance on financials)
    negative_items = {"2.06", "3.01", "4.02"}
    
    # Items that NEED text analysis (not automatically neutral/uncertain)
    # 5.02 = Departure/Election - could be negative (CEO leaves) or positive (new hire)
    # 7.01 = Reg FD Disclosure - could contain guidance, investor updates
    # 8.01 = Other Events - catch-all, needs content analysis
    # 9.01 = Financial Statements/Exhibits - usually neutral but check context
    text_analysis_items = {"5.02", "7.01", "8.01", "9.01"}
    
    # Governance items that are typically neutral (shareholder votes, bylaw changes)
    neutral_items = {"5.01", "5.03", "5.04", "5.05", "5.07", "5.08"}
    
    # Count item types
    positive_count = sum(1 for item in items if item in positive_items)
    negative_count = sum(1 for item in items if item in negative_items)
    neutral_count = sum(1 for item in items if item in neutral_items)
    needs_text_analysis = any(item in text_analysis_items for item in items)
    
    # Priority 1: Clear positive signals (acquisitions, earnings)
    if positive_count > 0 and positive_count >= negative_count:
        return "positive", 0.75
    
    # Priority 2: Clear negative signals (impairments, delisting, non-reliance)
    if negative_count > 0:
        return "negative", 0.85
    
    # Priority 3: Items that need text analysis (5.02 departures, 7.01 Reg FD, 8.01 other)
    if needs_text_analysis:
        direction, confidence = analyze_text_for_direction(title, description)
        # Boost confidence slightly since we have item context
        return direction, min(0.85, confidence + 0.1)
    
    # Priority 4: Pure governance items (neutral)
    if neutral_count > 0:
        return "neutral", 0.65
    
    # Fallback: unknown items - analyze text
    return analyze_text_for_direction(title, description)


def analyze_text_for_direction(title: str, description: str) -> Tuple[str, float]:
    """
    Analyze text content to determine event direction.
    More aggressive classification to reduce neutral/uncertain defaults.
    
    Args:
        title: Event title
        description: Event description
        
    Returns:
        Tuple of (direction, confidence)
    """
    text = f"{title} {description}".lower()
    title_lower = title.lower()
    
    # First check 8-K subtypes from title (high confidence)
    for subtype in NEGATIVE_8K_SUBTYPES:
        if subtype in title_lower:
            return "negative", 0.75
    
    for subtype in POSITIVE_8K_SUBTYPES:
        if subtype in title_lower:
            return "positive", 0.70
    
    # Then check title patterns for high-confidence classification
    for pattern in NEGATIVE_TITLE_PATTERNS:
        if pattern in title_lower:
            return "negative", 0.80
    
    for pattern in POSITIVE_TITLE_PATTERNS:
        if pattern in title_lower:
            return "positive", 0.80
    
    # Count keyword matches in full text
    positive_matches = sum(1 for keyword in POSITIVE_KEYWORDS if keyword in text)
    negative_matches = sum(1 for keyword in NEGATIVE_KEYWORDS if keyword in text)
    
    # Calculate net sentiment with lower threshold for classification
    net_sentiment = positive_matches - negative_matches
    
    if net_sentiment >= 2:
        # Strong positive signal
        confidence = min(0.85, 0.55 + 0.05 * net_sentiment)
        return "positive", confidence
    elif net_sentiment == 1:
        # Slight positive lean
        return "positive", 0.55
    elif net_sentiment <= -2:
        # Strong negative signal
        confidence = min(0.85, 0.55 + 0.05 * abs(net_sentiment))
        return "negative", confidence
    elif net_sentiment == -1:
        # Slight negative lean
        return "negative", 0.55
    elif positive_matches > 0 or negative_matches > 0:
        # Mixed signals but we have keywords - lean toward dominant type
        if positive_matches > 0:
            return "positive", 0.45
        else:
            return "negative", 0.45
    else:
        # No clear signals - check for specific patterns in title
        # Departures/Elections are often negative (leadership changes cause uncertainty)
        if "departure" in title_lower or "depart" in title_lower:
            return "negative", 0.60
        if "election" in title_lower and "director" in title_lower:
            return "neutral", 0.55
        if "vote" in title_lower or "shareholder" in title_lower:
            return "neutral", 0.60
        # Financial statements alone are usually neutral
        if "financial statement" in title_lower or "exhibit" in title_lower:
            return "neutral", 0.55
        
        # Default to neutral only when we truly have no signals
        return "neutral", 0.40


def determine_direction(
    event_type: str, title: str = "", description: str = "", metadata: Optional[Dict[str, Any]] = None
) -> Tuple[str, float]:
    """
    Determine event direction based on event type and text analysis.
    Improved to reduce neutral/uncertain classifications.
    
    Args:
        event_type: Canonical event type (lowercase)
        title: Event title
        description: Event description
        metadata: Optional metadata (e.g., {"8k_items": ["2.02", "5.02"]})
        
    Returns:
        Tuple of (direction, confidence)
        - direction: 'positive', 'negative', 'neutral', or 'uncertain'
        - confidence: 0-1 float indicating confidence in direction
    """
    metadata = metadata or {}
    
    # For 8-K events, use item-based scoring with text analysis fallback
    if event_type == "sec_8k" and "8k_items" in metadata:
        items = metadata.get("8k_items", [])
        if items:
            return determine_direction_from_8k_items(items, title, description)
    
    # Event types with DEFINITE positive direction
    if event_type in ["fda_approval", "guidance_raise", "merger_acquisition", "product_launch", "flagship_launch"]:
        return "positive", 0.90
    
    # Event types with DEFINITE negative direction
    if event_type in [
        "fda_rejection",
        "fda_crl",
        "fda_safety_alert",
        "guidance_lower",
        "guidance_withdraw",
        "product_recall",
        "product_delay",
        "investigation",
        "lawsuit",
        "restructuring",
        "divestiture",
    ]:
        return "negative", 0.85
    
    # Event types that need text analysis (don't default to neutral)
    # These include: earnings, sec_8k, sec_10k, sec_10q, sec_filing,
    # press_release, conference_presentation, analyst_day, executive_change, etc.
    
    # Use enhanced text analysis for all other event types
    direction, confidence = analyze_text_for_direction(title, description)
    
    # For certain event types, adjust based on domain knowledge ONLY with corroborating signals
    if event_type == "earnings":
        # Earnings events: Boost confidence if we found clear signals
        if direction != "neutral":
            confidence = min(0.90, confidence + 0.10)
        # Note: Do NOT default neutral earnings to positive without evidence
    elif event_type in ["sec_8k", "sec_filing"]:
        # 8-K filings: Let the text analysis and 8-K subtype detection handle direction
        pass
    elif event_type == "executive_change":
        # Executive changes: Only classify as negative if departure-related keywords found
        title_lower = title.lower()
        if direction == "neutral":
            if any(kw in title_lower for kw in ["departure", "resign", "step down", "leave", "exit", "retire"]):
                direction = "negative"
                confidence = 0.65
            elif any(kw in title_lower for kw in ["appointed", "hire", "join", "promote", "new ceo", "new cfo"]):
                direction = "positive"
                confidence = 0.65
    elif event_type in ["sec_10k", "sec_10q"]:
        confidence = max(0.40, confidence - 0.10)
    elif event_type == "guidance":
        if direction != "neutral":
            confidence = min(0.85, confidence + 0.15)
    elif event_type == "insider_trading":
        title_lower = title.lower()
        if "purchase" in title_lower or "buys" in title_lower or "acquire" in title_lower:
            direction = "positive"
            confidence = 0.70
        elif "sale" in title_lower or "sells" in title_lower or "disposes" in title_lower:
            direction = "negative"
            confidence = 0.65
    
    return direction, confidence


def calculate_sector_multiplier(event_type: str, sector: Optional[str]) -> Tuple[float, str]:
    """
    Calculate score multiplier based on sector relevance.
    
    Args:
        event_type: Canonical event type
        sector: Company sector (e.g., 'Pharma', 'Tech')
        
    Returns:
        Tuple of (multiplier, rationale)
    """
    if not sector:
        return 1.0, ""
    
    sector_lower = sector.lower()
    
    # FDA events highly impactful for pharma/biotech
    if event_type.startswith("fda_") and sector_lower in ["pharma", "biotech"]:
        return 1.2, "FDA event in pharma/biotech sector (+20%)"
    
    # Product launches impactful for tech
    if event_type == "product_launch" and sector_lower == "tech":
        return 1.1, "Product launch in tech sector (+10%)"
    
    return 1.0, ""


def calculate_market_cap_multiplier(market_cap: Optional[str]) -> Tuple[float, str]:
    """
    Calculate score multiplier based on market capitalization.
    
    Smaller companies have higher volatility, larger companies have lower volatility.
    
    Args:
        market_cap: Market cap category ('small', 'mid', 'large')
        
    Returns:
        Tuple of (multiplier, rationale)
    """
    if not market_cap:
        return 1.0, ""
    
    cap_lower = market_cap.lower()
    
    if cap_lower == "small":
        return 1.15, "Small-cap company (higher volatility, +15%)"
    elif cap_lower == "large":
        return 0.95, "Large-cap company (lower volatility, -5%)"
    
    return 1.0, ""


def calculate_text_intensity_adjustment(title: str, description: str) -> Tuple[float, str]:
    """
    Calculate score adjustment based on text intensity and keyword density.
    
    Produces varied adjustments based on the strength of sentiment signals.
    
    Args:
        title: Event title
        description: Event description
        
    Returns:
        Tuple of (adjustment_multiplier, rationale)
    """
    text = f"{title} {description}".lower()
    
    # Count keyword matches
    positive_matches = sum(1 for keyword in POSITIVE_KEYWORDS if keyword in text)
    negative_matches = sum(1 for keyword in NEGATIVE_KEYWORDS if keyword in text)
    
    # Strong positive signals
    strong_positive = {"breakthrough", "milestone", "record", "surge", "soar"}
    strong_positive_count = sum(1 for kw in strong_positive if kw in text)
    
    # Strong negative signals
    strong_negative = {"investigation", "lawsuit", "recall", "failure", "fraud"}
    strong_negative_count = sum(1 for kw in strong_negative if kw in text)
    
    # Calculate intensity score (-0.15 to +0.15)
    net_sentiment = positive_matches - negative_matches
    strong_boost = (strong_positive_count * 0.03) - (strong_negative_count * 0.03)
    
    if net_sentiment > 3:
        adjustment = min(0.15, 0.05 + 0.02 * net_sentiment + strong_boost)
        return adjustment, f"Strong positive sentiment (+{int(adjustment*100)}%)"
    elif net_sentiment < -3:
        adjustment = max(-0.10, -0.05 + 0.02 * net_sentiment + strong_boost)
        return adjustment, f"Strong negative sentiment ({int(adjustment*100)}%)"
    elif net_sentiment > 0:
        adjustment = 0.03 + 0.01 * net_sentiment + strong_boost
        return adjustment, f"Positive sentiment (+{int(adjustment*100)}%)"
    elif net_sentiment < 0:
        adjustment = -0.03 + 0.01 * net_sentiment + strong_boost
        return adjustment, f"Negative sentiment ({int(adjustment*100)}%)"
    else:
        return strong_boost, ""


def calculate_direction_adjustment(direction: str, confidence: float) -> Tuple[float, str]:
    """
    Calculate score adjustment based on direction and confidence.
    
    Positive events should score higher, negative events should score differently.
    
    Args:
        direction: Event direction ('positive', 'negative', 'neutral', 'uncertain')
        confidence: Confidence in direction (0-1)
        
    Returns:
        Tuple of (adjustment_multiplier, rationale)
    """
    if direction == "positive":
        # Positive events get a boost based on confidence
        adjustment = 0.05 + (confidence * 0.10)  # +5% to +15%
        return adjustment, f"Positive direction (+{int(adjustment*100)}%)"
    elif direction == "negative":
        # Negative events get a different adjustment (not necessarily lower, but different)
        adjustment = -0.05 + (confidence * 0.05)  # -5% to 0%
        return adjustment, f"Negative direction ({int(adjustment*100)}%)"
    elif direction == "neutral":
        # Neutral events stay close to base
        return 0.0, ""
    else:
        # Uncertain events get slight reduction
        return -0.05, "Uncertain direction (-5%)"


def calculate_ticker_variance(ticker: str = "", event_id: int = 0) -> float:
    """
    Generate deterministic variance based on ticker/event characteristics.
    
    This ensures different tickers get slightly different scores even for
    the same event type, while remaining deterministic and reproducible.
    
    Args:
        ticker: Stock ticker symbol
        event_id: Event ID for additional variance
        
    Returns:
        Variance multiplier (-0.08 to +0.08)
    """
    if not ticker:
        return 0.0
    
    # Use ticker hash for deterministic variance
    ticker_hash = sum(ord(c) for c in ticker.upper())
    
    # Combine with event_id for additional variance
    combined_hash = (ticker_hash * 31 + event_id) % 1000
    
    # Map to range -0.08 to +0.08
    variance = ((combined_hash / 1000) - 0.5) * 0.16
    
    return variance


def score_event(
    event_type: str,
    title: str = "",
    description: str = "",
    sector: Optional[str] = None,
    market_cap: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> ScoringResult:
    """
    Score an event and determine its directional impact.
    
    This is a pure function with deterministic output - no randomness.
    Enhanced to produce more varied scores based on multiple factors.
    
    Args:
        event_type: Type of event (e.g., 'fda_approval', 'earnings', 'sec_8k')
        title: Event title
        description: Event description
        sector: Company sector (Pharma, Tech, Finance, etc.)
        market_cap: Market capitalization category (small, mid, large)
        metadata: Additional metadata for scoring (e.g., {"8k_items": ["2.02", "5.02"], "ticker": "AAPL", "event_id": 123})
        
    Returns:
        ScoringResult with impact_score (0-100), direction, confidence (0-1), and rationale
    """
    metadata = metadata or {}
    
    # Get base score (event_type should already be in canonical format)
    event_type_lower = event_type.lower()
    base_score = EVENT_TYPE_SCORES.get(event_type_lower, 50)
    
    # Determine direction from event type and content (includes 8-K item logic)
    direction, direction_confidence = determine_direction(event_type_lower, title, description, metadata)
    
    # Initialize score multiplier and rationale
    score_multiplier = 1.0
    rationale_parts = []
    
    # For 8-K events with items, add item-based rationale
    if event_type_lower == "sec_8k" and "8k_items" in metadata:
        items = metadata.get("8k_items", [])
        if items:
            items_str = ", ".join(items)
            rationale_parts.append(f"8-K Items: {items_str}")
    
    # 1. Direction-based adjustment (NEW) - moderate impact
    direction_adj, direction_rationale = calculate_direction_adjustment(direction, direction_confidence)
    score_multiplier += direction_adj * 0.5  # Scale down to prevent overflow
    if direction_rationale:
        rationale_parts.append(direction_rationale)
    
    # 2. Text intensity adjustment (NEW) - moderate impact
    text_adj, text_rationale = calculate_text_intensity_adjustment(title, description)
    score_multiplier += text_adj * 0.5  # Scale down to prevent overflow
    if text_rationale:
        rationale_parts.append(text_rationale)
    
    # 3. Sector-specific adjustments
    sector_mult, sector_rationale = calculate_sector_multiplier(event_type_lower, sector)
    score_multiplier *= sector_mult
    if sector_rationale:
        rationale_parts.append(sector_rationale)
    
    # 4. Market cap adjustments
    cap_mult, cap_rationale = calculate_market_cap_multiplier(market_cap)
    score_multiplier *= cap_mult
    if cap_rationale:
        rationale_parts.append(cap_rationale)
    
    # 5. Ticker-based variance (NEW) - small impact for differentiation
    ticker = metadata.get("ticker", "")
    event_id = metadata.get("event_id", 0)
    ticker_variance = calculate_ticker_variance(ticker, event_id)
    score_multiplier += ticker_variance * 0.5  # Scale down
    
    # Clamp multiplier to safe range (0.7-1.4) to prevent extreme scores
    score_multiplier = max(0.7, min(1.4, score_multiplier))
    
    # Calculate final score
    final_score = int(base_score * score_multiplier)
    # Clamp to 20-95 range to maintain spread without ceiling/floor pileups
    final_score = max(20, min(95, final_score))
    
    # Build rationale
    if rationale_parts:
        rationale = f"Base score: {base_score}. Adjustments: {', '.join(rationale_parts)}. Direction: {direction} (confidence: {direction_confidence:.2f})"
    else:
        rationale = f"Base score for {event_type_lower}: {base_score}. Direction: {direction} (confidence: {direction_confidence:.2f})"
    
    return ScoringResult(
        impact_score=final_score,
        direction=direction,
        confidence=direction_confidence,
        rationale=rationale,
    )
