"""
Impact Scoring Module for Impact Radar

Provides both deterministic and probabilistic event impact scoring.

Two scoring approaches:
1. Deterministic: Rule-based scoring by event type, sector, and market conditions
2. Probabilistic: Statistical scoring based on historical event studies

Scoring Rules (Deterministic):
- FDA/Regulatory: High impact (70-95) with clear directional signals
- SEC Filings: Variable impact based on filing type and content
- Earnings: Medium-high impact (60-85) based on guidance and beats/misses  
- Product Launches: Medium impact (50-75) based on market position
- Corporate Actions: Variable impact (40-90) based on materiality

All scores are deterministic - no randomness.
"""

from typing import Tuple, Dict, Any, Optional
from datetime import datetime
import math

# Import probabilistic scoring components
try:
    from impact_models.definitions import DEFAULT_IMPACT_TARGET
    from impact_models.event_study import p_move, p_up, p_down
    from impact_models.confidence import compute_confidence
    PROBABILISTIC_SCORING_AVAILABLE = True
except ImportError:
    PROBABILISTIC_SCORING_AVAILABLE = False


class ImpactScorer:
    """Deterministic event impact scoring engine."""
    
    # Base scores by event type
    EVENT_TYPE_SCORES = {
        # FDA Events (High impact for biotech/pharma)
        'fda_approval': 85,
        'fda_rejection': 80,
        'fda_adcom': 75,
        'fda_crl': 75,  # Complete Response Letter
        'fda_safety_alert': 70,
        'fda_announcement': 65,  # Generic FDA announcement
        
        # SEC Filings
        'sec_8k': 65,  # Current report - can be highly material
        'sec_10k': 55,  # Annual report
        'sec_10q': 50,  # Quarterly report
        'sec_s1': 70,  # IPO registration
        'sec_13d': 75,  # Beneficial ownership (activist/acquisition)
        'sec_13g': 60,  # Passive ownership
        'sec_def14a': 55,  # Proxy statement
        
        # Earnings & Guidance
        'earnings': 70,
        'guidance_raise': 75,
        'guidance_lower': 75,
        'guidance_withdraw': 80,
        
        # Corporate Actions
        'merger_acquisition': 85,
        'divestiture': 70,
        'restructuring': 65,
        'investigation': 75,
        'lawsuit': 65,
        'executive_change': 60,
        
        # Product Events
        'product_launch': 65,
        'product_delay': 70,
        'product_recall': 80,
        'flagship_launch': 75,
        
        # Other
        'analyst_day': 55,
        'conference_presentation': 45,
        'press_release': 50,
        'manual_entry': 50,
    }
    
    # Direction keywords for sentiment analysis - EXPANDED for better classification
    POSITIVE_KEYWORDS = {
        # Earnings/Financial
        'approval', 'approved', 'beats', 'beat', 'exceeded', 'exceeds', 'topped',
        'surpassed', 'above expectations', 'better than expected', 'eps beat',
        'revenue beat', 'profit', 'profitable', 'record revenue', 'record earnings',
        'record quarter', 'outperform', 'outperformed',
        # Guidance
        'raises', 'raised', 'upgrade', 'upgraded', 'upside', 'higher guidance',
        'increased guidance', 'reaffirm', 'reaffirmed',
        # Growth
        'increase', 'increased', 'growth', 'growing', 'expand', 'expansion',
        'accelerat', 'momentum', 'surge', 'surged', 'soar', 'soared',
        # Success
        'positive', 'success', 'successful', 'breakthrough', 'milestone',
        'achievement', 'accomplish', 'won', 'wins', 'award', 'awarded',
        # Deals/Partnerships
        'acquisition', 'acquired', 'partnership', 'collaborate', 'collaboration',
        'alliance', 'contract', 'deal', 'agreement', 'signed',
        # Product/Clinical
        'launch', 'launches', 'launched', 'fda approval', 'approved by fda',
        'positive results', 'positive data', 'met primary endpoint',
        # Financial Strength
        'strong', 'robust', 'gains', 'dividend', 'buyback', 'repurchase',
        'cash flow', 'margin improvement', 'cost savings',
        # Leadership
        'appointed', 'appointment', 'hire', 'hired', 'new ceo', 'new cfo',
        'promotes', 'promoted', 'named',
    }
    
    NEGATIVE_KEYWORDS = {
        # Earnings/Financial
        'reject', 'rejected', 'rejection', 'misses', 'missed', 'miss',
        'below expectations', 'worse than expected', 'disappointed', 'disappointing',
        'fell short', 'shortfall', 'underperform', 'underperformed',
        'eps miss', 'revenue miss', 'loss', 'losses', 'net loss',
        # Guidance
        'lowers', 'lowered', 'downgrade', 'downgraded', 'downside',
        'lower guidance', 'reduced guidance', 'cut guidance', 'withdraw',
        'withdrawn', 'suspend', 'suspended',
        # Decline
        'decrease', 'decreased', 'decline', 'declining', 'drop', 'dropped',
        'fall', 'fell', 'plunge', 'plunged', 'slump', 'tumble',
        # Failure
        'fail', 'failed', 'failure', 'negative', 'adverse',
        'did not meet', 'failed to meet',
        # Legal/Regulatory
        'investigation', 'investigated', 'lawsuit', 'sued', 'litigation',
        'subpoena', 'sec inquiry', 'doj', 'ftc', 'probe', 'fine', 'fined',
        'penalty', 'settlement', 'violation',
        # Product Issues
        'recall', 'recalled', 'delay', 'delayed', 'postpone', 'postponed',
        'discontinue', 'discontinued', 'terminate', 'terminated',
        # Financial Distress
        'impairment', 'write-off', 'writeoff', 'write-down', 'writedown',
        'restructuring', 'layoff', 'layoffs', 'workforce reduction',
        'cost cutting', 'bankruptcy', 'default', 'defaulted', 'delisting',
        # Leadership Departures
        'resign', 'resigned', 'resignation', 'departure', 'depart', 'departed',
        'step down', 'steps down', 'stepping down', 'leave', 'leaving', 'left',
        'exit', 'exits', 'exited', 'retire', 'retired', 'retirement',
        # Concern
        'concern', 'concerns', 'warning', 'warns', 'warned', 'weaken', 'weak',
        'risk', 'risks', 'uncertainty', 'uncertain', 'headwind', 'headwinds',
        'challenge', 'challenges', 'difficult', 'tough',
        # SEC/Compliance
        'non-reliance', 'restatement', 'restated', 'material weakness',
    }
    
    # Title-based patterns for quick classification (high confidence)
    POSITIVE_TITLE_PATTERNS = {
        'beats', 'exceeds', 'raises guidance', 'record', 'approval', 'approved',
        'acquisition', 'partnership', 'agreement', 'contract win', 'new ceo',
        'appointed', 'positive results', 'fda approval',
    }
    
    NEGATIVE_TITLE_PATTERNS = {
        'misses', 'missed', 'lowers guidance', 'cuts guidance', 'recall',
        'investigation', 'lawsuit', 'departure', 'resign', 'step down',
        'delisting', 'bankruptcy', 'layoff', 'restructuring', 'impairment',
        'write-off', 'restatement', 'non-reliance', 'sec inquiry',
    }
    
    @staticmethod
    def score_event(
        event_type: str,
        title: str = "",
        description: str = "",
        sector: str = None,
        market_cap: str = None,
        metadata: Dict[str, Any] = None
    ) -> Tuple[int, str, float, str]:
        """
        Score an event and determine its directional impact.
        
        Args:
            event_type: Type of event (e.g., 'fda_approval', 'earnings', 'sec_8k')
            title: Event title
            description: Event description
            sector: Company sector (Pharma, Tech, Finance, etc.)
            market_cap: Market capitalization category (small, mid, large)
            metadata: Additional metadata for scoring (e.g., {"8k_items": ["2.02", "5.02"]})
            
        Returns:
            Tuple of (impact_score, direction, confidence, rationale)
            - impact_score: 0-100 integer
            - direction: 'positive', 'negative', 'neutral', or 'uncertain'
            - confidence: 0-1 float
            - rationale: Human-readable explanation
        """
        metadata = metadata or {}
        
        # Get base score (event_type should already be in canonical format)
        event_type_lower = event_type.lower()
        base_score = ImpactScorer.EVENT_TYPE_SCORES.get(event_type_lower, 50)
        
        # Determine direction from event type and content (includes 8-K item logic)
        direction, direction_confidence = ImpactScorer._determine_direction(
            event_type_lower, title, description, metadata
        )
        
        # Adjust score based on sector and market cap
        score_multiplier = 1.0
        rationale_parts = []
        
        # For 8-K events with items, add item-based rationale
        if event_type_lower == 'sec_8k' and '8k_items' in metadata:
            items = metadata.get('8k_items', [])
            if items:
                items_str = ', '.join(items)
                rationale_parts.append(f"8-K Items: {items_str}")
        
        # Sector-specific adjustments
        if sector:
            sector_lower = sector.lower()
            if event_type_lower.startswith('fda_') and sector_lower in ['pharma', 'biotech']:
                score_multiplier *= 1.2
                rationale_parts.append("FDA event in pharma/biotech sector")
            elif event_type_lower == 'product_launch' and sector_lower == 'tech':
                score_multiplier *= 1.1
                rationale_parts.append("Product launch in tech sector")
        
        # Market cap adjustments (smaller companies = higher volatility)
        if market_cap:
            if market_cap.lower() == 'small':
                score_multiplier *= 1.15
                rationale_parts.append("Small-cap company (higher volatility)")
            elif market_cap.lower() == 'large':
                score_multiplier *= 0.95
                rationale_parts.append("Large-cap company (lower volatility)")
        
        # Calculate final score
        final_score = min(100, int(base_score * score_multiplier))
        
        # Build rationale
        event_type_clean = event_type.replace('_', ' ').title()
        rationale = f"{event_type_clean} event"
        
        if final_score >= 80:
            rationale = f"High impact: {rationale}"
        elif final_score >= 60:
            rationale = f"Medium-high impact: {rationale}"
        elif final_score >= 40:
            rationale = f"Medium impact: {rationale}"
        else:
            rationale = f"Low impact: {rationale}"
        
        if rationale_parts:
            rationale += f" ({', '.join(rationale_parts)})"
        
        rationale += f". Direction: {direction} (confidence: {direction_confidence:.2f})"
        
        return final_score, direction, direction_confidence, rationale
    
    # 8-K subtypes that indicate direction (from SEC filing titles)
    # Note: Order matters - check more specific patterns first
    POSITIVE_8K_SUBTYPES = {
        'entry into material agreement',
        'completion of acquisition',
        'acquisition of assets',
        'product announcement',
        'service announcement',
    }
    
    NEGATIVE_8K_SUBTYPES = {
        'termination of material',  # Termination of agreements is negative
        'departure',
        'resignation',
        'non-reliance',
        'impairment',
        'delisting',
        'bankruptcy',
        'receivership',
        'default',
        'suspension of trading',
    }
    
    NEUTRAL_8K_SUBTYPES = {
        'regulation fd',
        'other events',
        'financial statements',
        'exhibits',
        'proxy',
        'results of operations',  # Neutral without beat/miss context
        'submission of matters',
        'amendments to articles',
        'changes in certifying accountant',
        'unregistered sales',
    }
    
    @staticmethod
    def _analyze_text_for_direction(title: str, description: str) -> Tuple[str, float]:
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
        for subtype in ImpactScorer.NEGATIVE_8K_SUBTYPES:
            if subtype in title_lower:
                return 'negative', 0.75
        
        for subtype in ImpactScorer.POSITIVE_8K_SUBTYPES:
            if subtype in title_lower:
                return 'positive', 0.70
        
        # Then check title patterns for high-confidence classification
        for pattern in ImpactScorer.NEGATIVE_TITLE_PATTERNS:
            if pattern in title_lower:
                return 'negative', 0.80
        
        for pattern in ImpactScorer.POSITIVE_TITLE_PATTERNS:
            if pattern in title_lower:
                return 'positive', 0.80
        
        # Count keyword matches in full text
        positive_matches = sum(1 for keyword in ImpactScorer.POSITIVE_KEYWORDS if keyword in text)
        negative_matches = sum(1 for keyword in ImpactScorer.NEGATIVE_KEYWORDS if keyword in text)
        
        # Calculate net sentiment with lower threshold for classification
        net_sentiment = positive_matches - negative_matches
        
        if net_sentiment >= 2:
            # Strong positive signal
            confidence = min(0.85, 0.55 + 0.05 * net_sentiment)
            return 'positive', confidence
        elif net_sentiment == 1:
            # Slight positive lean
            return 'positive', 0.55
        elif net_sentiment <= -2:
            # Strong negative signal
            confidence = min(0.85, 0.55 + 0.05 * abs(net_sentiment))
            return 'negative', confidence
        elif net_sentiment == -1:
            # Slight negative lean
            return 'negative', 0.55
        elif positive_matches > 0 or negative_matches > 0:
            # Mixed signals but we have keywords - lean toward dominant type
            if positive_matches > 0:
                return 'positive', 0.45
            else:
                return 'negative', 0.45
        else:
            # No clear signals - check for specific patterns in title
            if 'departure' in title_lower or 'depart' in title_lower:
                return 'negative', 0.60
            if 'election' in title_lower and 'director' in title_lower:
                return 'neutral', 0.55
            if 'vote' in title_lower or 'shareholder' in title_lower:
                return 'neutral', 0.60
            if 'financial statement' in title_lower or 'exhibit' in title_lower:
                return 'neutral', 0.55
            
            # Default to neutral only when we truly have no signals
            return 'neutral', 0.40
    
    @staticmethod
    def _determine_direction_from_8k_items(items: list, title: str = "", description: str = "") -> Tuple[str, float]:
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
            return ImpactScorer._analyze_text_for_direction(title, description)
        
        # Positive items (acquisitions, completed acquisitions, earnings results)
        positive_items = {'1.01', '2.01', '2.02'}
        
        # Negative items (impairments, delisting, non-reliance on financials)
        negative_items = {'2.06', '3.01', '4.02'}
        
        # Items that NEED text analysis (not automatically neutral/uncertain)
        # 5.02 = Departure/Election - could be negative (CEO leaves) or positive (new hire)
        # 7.01 = Reg FD Disclosure - could contain guidance, investor updates
        # 8.01 = Other Events - catch-all, needs content analysis
        # 9.01 = Financial Statements/Exhibits - usually neutral but check context
        text_analysis_items = {'5.02', '7.01', '8.01', '9.01'}
        
        # Governance items that are typically neutral (shareholder votes, bylaw changes)
        neutral_items = {'5.01', '5.03', '5.04', '5.05', '5.07', '5.08'}
        
        # Count item types
        positive_count = sum(1 for item in items if item in positive_items)
        negative_count = sum(1 for item in items if item in negative_items)
        neutral_count = sum(1 for item in items if item in neutral_items)
        needs_text_analysis = any(item in text_analysis_items for item in items)
        
        # Priority 1: Clear positive signals (acquisitions, earnings)
        if positive_count > 0 and positive_count >= negative_count:
            return 'positive', 0.75
        
        # Priority 2: Clear negative signals (impairments, delisting, non-reliance)
        if negative_count > 0:
            return 'negative', 0.85
        
        # Priority 3: Items that need text analysis (5.02 departures, 7.01 Reg FD, 8.01 other)
        if needs_text_analysis:
            direction, confidence = ImpactScorer._analyze_text_for_direction(title, description)
            # Boost confidence slightly since we have item context
            return direction, min(0.85, confidence + 0.1)
        
        # Priority 4: Pure governance items (neutral)
        if neutral_count > 0:
            return 'neutral', 0.65
        
        # Fallback: unknown items - analyze text
        return ImpactScorer._analyze_text_for_direction(title, description)
    
    @staticmethod
    def _determine_direction(
        event_type: str,
        title: str,
        description: str,
        metadata: Dict[str, Any] = None
    ) -> Tuple[str, float]:
        """
        Determine event direction (positive/negative/neutral/uncertain) and confidence.
        Improved to reduce neutral/uncertain classifications.
        
        Args:
            event_type: Event type
            title: Event title
            description: Event description
            metadata: Optional metadata (e.g., {"8k_items": ["2.02", "5.02"]})
        
        Returns:
            Tuple of (direction, confidence)
        """
        metadata = metadata or {}
        
        # For 8-K events, use item-based scoring with text analysis fallback
        if event_type.lower() == 'sec_8k' and '8k_items' in metadata:
            items = metadata.get('8k_items', [])
            if items:
                return ImpactScorer._determine_direction_from_8k_items(items, title, description)
        
        # Event types with DEFINITE positive direction
        event_type_lower = event_type.lower()
        if event_type_lower in ['fda_approval', 'guidance_raise', 'merger_acquisition', 'product_launch', 'flagship_launch']:
            return 'positive', 0.90
        
        # Event types with DEFINITE negative direction
        if event_type_lower in [
            'fda_rejection', 'fda_crl', 'fda_safety_alert', 'guidance_lower',
            'guidance_withdraw', 'product_recall', 'product_delay',
            'investigation', 'lawsuit', 'restructuring', 'divestiture',
        ]:
            return 'negative', 0.85
        
        # Use enhanced text analysis for all other event types
        direction, confidence = ImpactScorer._analyze_text_for_direction(title, description)
        
        # For certain event types, adjust based on domain knowledge ONLY with corroborating signals
        if event_type_lower == 'earnings':
            # Earnings events: Boost confidence if we found clear signals
            if direction != 'neutral':
                confidence = min(0.90, confidence + 0.10)
            # Note: Do NOT default neutral earnings to positive without evidence
        elif event_type_lower in ['sec_8k', 'sec_filing']:
            # 8-K filings: Let the text analysis and 8-K subtype detection handle direction
            # Don't force defaults without corroborating evidence
            pass
        elif event_type_lower == 'executive_change':
            # Executive changes: Only classify as negative if departure-related keywords found
            title_lower = title.lower()
            if direction == 'neutral':
                # Look for specific departure signals
                if any(kw in title_lower for kw in ['departure', 'resign', 'step down', 'leave', 'exit', 'retire']):
                    direction = 'negative'
                    confidence = 0.65
                elif any(kw in title_lower for kw in ['appointed', 'hire', 'join', 'promote', 'new ceo', 'new cfo']):
                    direction = 'positive'
                    confidence = 0.65
                # Otherwise keep neutral - we don't know if it's departure or appointment
        elif event_type_lower in ['sec_10k', 'sec_10q']:
            # Quarterly/annual reports - these are routine, lower confidence
            confidence = max(0.40, confidence - 0.10)
        elif event_type_lower == 'guidance':
            # Guidance events - boost confidence for clear signals
            if direction != 'neutral':
                confidence = min(0.85, confidence + 0.15)
        elif event_type_lower == 'insider_trading':
            # Insider trades: Use title keywords as corroborating evidence
            title_lower = title.lower()
            if 'purchase' in title_lower or 'buys' in title_lower or 'acquire' in title_lower:
                direction = 'positive'
                confidence = 0.70
            elif 'sale' in title_lower or 'sells' in title_lower or 'disposes' in title_lower:
                direction = 'negative'
                confidence = 0.65
        
        return direction, confidence
    
    @staticmethod
    def batch_score_events(events: list) -> list:
        """
        Score multiple events in batch.
        
        Args:
            events: List of event dictionaries with keys: event_type, title, description, sector
            
        Returns:
            List of events with added scoring fields: impact_score, direction, confidence, rationale
        """
        scored_events = []
        
        for event in events:
            score, direction, confidence, rationale = ImpactScorer.score_event(
                event_type=event.get('event_type', ''),
                title=event.get('title', ''),
                description=event.get('description', ''),
                sector=event.get('sector'),
                market_cap=event.get('market_cap'),
                metadata=event.get('metadata', {})
            )
            
            scored_event = event.copy()
            scored_event['impact_score'] = score
            scored_event['direction'] = direction
            scored_event['confidence'] = confidence
            scored_event['rationale'] = rationale
            
            scored_events.append(scored_event)
        
        return scored_events


# Convenience function for single event scoring
def score_event(event_type: str, title: str = "", description: str = "", 
                sector: str = None, market_cap: str = None, 
                metadata: Dict[str, Any] = None,
                market_regime: str = None,
                regime_confidence: float = None) -> Dict[str, Any]:
    """
    Score a single event with optional probabilistic scoring.
    
    This function attempts to use probabilistic scoring if historical priors are available,
    otherwise falls back to deterministic rule-based scoring.
    
    Args:
        event_type: Type of event (e.g., 'fda_approval', 'earnings', 'sec_8k')
        title: Event title
        description: Event description
        sector: Company sector (Pharma, Tech, Finance, etc.)
        market_cap: Market capitalization category (small, mid, large)
        metadata: Additional metadata for scoring (e.g., {"8k_items": ["2.02", "5.02"]})
        market_regime: Optional market regime context ("risk_on", "risk_off")
        regime_confidence: Optional confidence in regime classification (0-1)
    
    Returns:
        Dictionary with:
            - impact_score (int): 0-100 score
            - direction (str): "positive", "negative", "neutral", or "uncertain"
            - confidence (float): 0-1 confidence score
            - rationale (str): Human-readable explanation
            - p_move (float or None): Probability of |move| > threshold (if probabilistic)
            - p_up (float or None): Probability of upward move > threshold (if probabilistic)
            - p_down (float or None): Probability of downward move > threshold (if probabilistic)
            - score_version (int): 1=deterministic, 2=probabilistic
    """
    # Use deterministic scoring
    impact_score, direction, confidence, rationale = ImpactScorer.score_event(
        event_type, title, description, sector, market_cap, metadata
    )
    
    # Apply regime context modifier (ADDITIVE - enhances confidence, does not change direction)
    if market_regime and regime_confidence:
        confidence, rationale = apply_regime_context(
            direction, confidence, rationale,
            market_regime, regime_confidence
        )
    
    # Return as dict with probability fields set to None (deterministic scoring)
    return {
        'impact_score': impact_score,
        'direction': direction,
        'confidence': confidence,
        'rationale': rationale,
        'p_move': None,
        'p_up': None,
        'p_down': None,
        'score_version': 1  # 1 = deterministic scoring
    }


def apply_regime_context(
    direction: str,
    confidence: float,
    rationale: str,
    market_regime: str,
    regime_confidence: float
) -> Tuple[float, str]:
    """
    Apply market regime context as a confidence modifier (ADDITIVE enhancement).
    
    This does NOT change the direction - it only adjusts confidence based on
    whether the event direction aligns with the current market regime.
    
    Args:
        direction: Event direction ("positive", "negative", "neutral", "uncertain")
        confidence: Base confidence score (0-1)
        rationale: Base rationale string
        market_regime: Current market regime ("risk_on", "risk_off")
        regime_confidence: Confidence in regime classification (0-1)
    
    Returns:
        Tuple of (adjusted_confidence, updated_rationale)
    """
    # Only apply adjustment for non-neutral events with high regime confidence
    if regime_confidence < 0.6 or direction in ("neutral", "uncertain"):
        return confidence, rationale
    
    regime_boost = 0.0
    regime_note = ""
    
    if market_regime == "risk_on":
        # Risk-on: boost confidence for positive events, slight reduction for negative
        if direction == "positive":
            regime_boost = 0.05 * regime_confidence  # Up to +5% confidence
            regime_note = "Risk-on market supports bullish outlook."
        elif direction == "negative":
            regime_boost = -0.02 * regime_confidence  # Slight reduction
            regime_note = "Risk-on market may dampen bearish reaction."
    
    elif market_regime == "risk_off":
        # Risk-off: boost confidence for negative events, slight reduction for positive
        if direction == "negative":
            regime_boost = 0.05 * regime_confidence  # Up to +5% confidence
            regime_note = "Risk-off market amplifies bearish concern."
        elif direction == "positive":
            regime_boost = -0.02 * regime_confidence  # Slight reduction
            regime_note = "Risk-off market may dampen bullish reaction."
    
    # Apply adjustment (keep confidence in 0-1 range)
    adjusted_confidence = max(0.3, min(0.95, confidence + regime_boost))
    
    # Append regime note to rationale if there was an adjustment
    if regime_note:
        updated_rationale = f"{rationale} {regime_note}"
    else:
        updated_rationale = rationale
    
    return adjusted_confidence, updated_rationale


# ============================================================================
# PROBABILISTIC IMPACT SCORING FUNCTIONS
# ============================================================================

def to_impact_score(p_move_val: float) -> int:
    """
    Map p_move probability to 0-100 impact score.
    
    Uses a tanh transformation to shape the score so that:
    - 50% probability maps to ~50 score
    - Higher probabilities saturate towards 100
    - Lower probabilities saturate towards 0
    
    Args:
        p_move_val: Probability of move exceeding threshold (0-1)
        
    Returns:
        Impact score (0-100)
    """
    s = 100.0 * p_move_val
    k = 15.0
    shaped = 50.0 + 50.0 * math.tanh((s - 50.0) / k)
    return int(round(max(0.0, min(100.0, shaped))))


def infer_direction(p_up_val: float, p_down_val: float, buffer: float = 0.05) -> str:
    """
    Determine direction from up/down probabilities.
    
    Args:
        p_up_val: Probability of upward move
        p_down_val: Probability of downward move
        buffer: Threshold for distinguishing directions
        
    Returns:
        Direction string: "positive", "negative", or "neutral"
    """
    if p_up_val > p_down_val + buffer:
        return "positive"
    if p_down_val > p_up_val + buffer:
        return "negative"
    return "neutral"


def to_confidence_score(conf_01: float) -> int:
    """
    Map confidence from [0,1] to [0,100].
    
    Args:
        conf_01: Confidence in [0, 1]
        
    Returns:
        Confidence score (0-100)
    """
    return int(round(max(0.0, min(1.0, conf_01)) * 100.0))


def build_rationale(
    event_type: str,
    sector: str,
    cap_bucket: str,
    mu: float,
    sigma: float,
    n: int,
    p_move_val: float,
    p_up_val: float,
    p_down_val: float
) -> str:
    """
    Build human-readable rationale for probabilistic scoring.
    
    Args:
        event_type: Type of event
        sector: Company sector
        cap_bucket: Market cap bucket (small, mid, large)
        mu: Mean abnormal return from historical data (%)
        sigma: Std dev of abnormal returns (%)
        n: Number of historical events
        p_move_val: Probability of move > threshold
        p_up_val: Probability of upward move > threshold
        p_down_val: Probability of downward move > threshold
        
    Returns:
        Human-readable rationale string
    """
    if not PROBABILISTIC_SCORING_AVAILABLE:
        return "Probabilistic scoring not available"
    
    horizon_days = DEFAULT_IMPACT_TARGET.horizon_days
    threshold_pct = DEFAULT_IMPACT_TARGET.threshold_pct
    
    return (
        f"Based on {n} similar {event_type} events in the {sector} sector "
        f"for {cap_bucket} companies, the historical mean abnormal move over "
        f"{horizon_days} day(s) is {mu:.2f}% with volatility {sigma:.2f}%. "
        f"Estimated probability of a move larger than {threshold_pct:.1f}% is "
        f"{p_move_val*100:.1f}% (up: {p_up_val*100:.1f}%, down: {p_down_val*100:.1f}%)."
    )


def score_event_probabilistic(
    event_type: str,
    sector: str,
    cap_bucket: str,
    prior_mu: float,
    prior_sigma: float,
    prior_n: int
) -> Dict[str, Any]:
    """
    Score an event using probabilistic model based on historical priors.
    
    This function computes impact scores based on statistical analysis of
    similar historical events. It calculates probabilities of price moves
    exceeding a threshold and derives impact scores, direction, and confidence.
    
    Args:
        event_type: Type of event (e.g., 'earnings', 'fda_approval')
        sector: Company sector (e.g., 'Tech', 'Pharma')
        cap_bucket: Market cap bucket ('small', 'mid', 'large')
        prior_mu: Mean abnormal return from historical data (%)
        prior_sigma: Std dev of abnormal returns (%)
        prior_n: Number of historical events in this group
        
    Returns:
        Dictionary with:
            - impact_score (int): 0-100 score
            - direction (str): "positive", "negative", or "neutral"
            - confidence (int): 0-100 confidence score
            - rationale (str): Human-readable explanation
            - p_move (float): Probability of |move| > threshold
            - p_up (float): Probability of upward move > threshold
            - p_down (float): Probability of downward move > threshold
    """
    if not PROBABILISTIC_SCORING_AVAILABLE:
        return {
            "impact_score": 50,
            "direction": "neutral",
            "confidence": 0,
            "rationale": "Probabilistic scoring not available - using default values",
            "p_move": 0.0,
            "p_up": 0.0,
            "p_down": 0.0,
        }
    
    T = DEFAULT_IMPACT_TARGET.threshold_pct
    
    # Compute probabilities
    p_move_val = p_move(prior_mu, prior_sigma, T)
    p_up_val = p_up(prior_mu, prior_sigma, T)
    p_down_val = p_down(prior_mu, prior_sigma, T)
    
    # Compute confidence
    conf_01 = compute_confidence(prior_n, prior_sigma)
    
    # Map to output scores
    impact_score = to_impact_score(p_move_val)
    direction = infer_direction(p_up_val, p_down_val)
    confidence = to_confidence_score(conf_01)
    rationale = build_rationale(
        event_type, sector, cap_bucket, prior_mu, prior_sigma, prior_n,
        p_move_val, p_up_val, p_down_val
    )
    
    return {
        "impact_score": impact_score,
        "direction": direction,
        "confidence": confidence,
        "rationale": rationale,
        "p_move": p_move_val,
        "p_up": p_up_val,
        "p_down": p_down_val,
    }


# ============================================================================
# BEARISH SIGNAL SCORING
# ============================================================================

class BearishSignalConfig:
    """Configuration for bearish signal determination thresholds."""
    
    # Probability thresholds (relaxed for actual data)
    P_DOWN_MIN_THRESHOLD = 0.40  # Minimum p_down to trigger bearish signal
    P_DOWN_UP_DELTA_THRESHOLD = 0.10  # Minimum p_down - p_up difference
    
    # Direction confidence thresholds (relaxed)
    DIRECTION_CONFIDENCE_THRESHOLD = 0.50  # Minimum confidence for negative direction
    
    # Impact score thresholds (higher impact negative events are more bearish)
    HIGH_IMPACT_THRESHOLD = 70  # Impact score considered "high impact"
    LOW_ML_SCORE_THRESHOLD = 35  # ML score below this considered bearish
    
    # Event types that are inherently bearish
    BEARISH_EVENT_TYPES = {
        'fda_rejection', 'fda_crl', 'guidance_lower', 'guidance_withdraw',
        'product_recall', 'investigation', 'lawsuit', 'product_delay',
        'restructuring', 'divestiture'
    }
    
    # Severely bearish event types (highest confidence)
    SEVERE_BEARISH_TYPES = {
        'fda_rejection', 'fda_crl', 'product_recall', 'investigation'
    }
    
    # 8-K items that indicate bearish signals
    BEARISH_8K_ITEMS = {'2.06', '3.01', '4.02', '5.02'}  # Impairments, delisting, non-reliance, departure
    
    # Negative keywords with severity weights (higher = more bearish)
    # These are used for text-based bearish detection
    WEIGHTED_NEGATIVE_KEYWORDS = {
        'bankruptcy': 1.0, 'default': 0.95, 'fraud': 0.95, 'delisting': 0.9,
        'investigation': 0.85, 'recall': 0.8, 'lawsuit': 0.75, 'failure': 0.75,
        'rejection': 0.8, 'impairment': 0.7, 'writeoff': 0.7, 'loss': 0.6,
        'decline': 0.55, 'missed': 0.6, 'disappointing': 0.55, 'warning': 0.65,
        'cut': 0.6, 'layoff': 0.7, 'terminate': 0.6, 'downgrade': 0.65,
        'concern': 0.5, 'weaker': 0.5, 'weak': 0.45, 'lower': 0.4, 'below': 0.4,
        'shortfall': 0.55, 'deficit': 0.6, 'negative': 0.5, 'adversely': 0.55,
        'material weakness': 0.75, 'restatement': 0.7, 'resignation': 0.5,
        'departure': 0.45, 'terminated': 0.6, 'violation': 0.65, 'breach': 0.6
    }
    
    # Minimum keyword score to trigger bearish signal
    MIN_KEYWORD_SCORE = 0.6  # At least one significant keyword needed
    MIN_BEARISH_CONFIDENCE = 0.5  # Reduced from 0.6 to capture more events
    
    # Hidden Bearish (Contrarian Pattern) thresholds
    HIDDEN_BEARISH_MIN_RATE = 0.40  # 40%+ contrarian rate triggers hidden bearish
    HIDDEN_BEARISH_CONFIDENCE_BOOST = 0.5  # Confidence when hidden bearish is detected


def compute_bearish_signal(
    event_type: str,
    direction: str,
    confidence: float,
    impact_score: int,
    title: str = "",
    description: str = "",
    p_down: float = None,
    p_up: float = None,
    ml_adjusted_score: int = None,
    ml_confidence: float = None,
    metadata: Dict[str, Any] = None,
    hidden_bearish_prob: float = None,
    contrarian_sample_size: int = None
) -> Dict[str, Any]:
    """
    Compute bearish signal for an event using multiple signal sources.
    
    Combines:
    1. Event-based signals (bearish event types)
    2. Threshold-based signals (p_down vs p_up)
    3. Text analysis (weighted negative keywords)
    4. ML predictions (negative predicted returns)
    5. Hidden Bearish patterns (contrarian outcomes from Market Echo Engine)
    
    Args:
        event_type: Event type string
        direction: Determined direction (positive/negative/neutral/uncertain)
        confidence: Direction confidence (0-1)
        impact_score: Impact score (0-100)
        title: Event title for text analysis
        description: Event description for text analysis
        p_down: Probability of downward move (0-1, optional)
        p_up: Probability of upward move (0-1, optional)
        ml_adjusted_score: ML-adjusted score (0-100, optional)
        ml_confidence: ML model confidence (0-1, optional)
        metadata: Additional metadata (e.g., 8k_items)
        hidden_bearish_prob: Probability of hidden bearish from contrarian patterns (0-1, optional)
        contrarian_sample_size: Number of historical samples for contrarian pattern (optional)
        
    Returns:
        Dictionary with:
            - bearish_signal (bool): Whether event is flagged as bearish
            - bearish_score (float): Normalized severity score (0-1)
            - bearish_confidence (float): Confidence in bearish classification (0-1)
            - bearish_rationale (str): Human-readable explanation
    """
    metadata = metadata or {}
    config = BearishSignalConfig
    
    signals = []  # List of (score, confidence, reason) tuples
    
    # Signal 1: Event type-based bearish detection
    event_type_lower = event_type.lower()
    if event_type_lower in config.SEVERE_BEARISH_TYPES:
        signals.append((0.95, 0.95, f"Severely bearish event type: {event_type}"))
    elif event_type_lower in config.BEARISH_EVENT_TYPES:
        signals.append((0.75, 0.85, f"Bearish event type: {event_type}"))
    
    # Signal 2: Direction-based bearish detection
    if direction == 'negative' and confidence >= config.DIRECTION_CONFIDENCE_THRESHOLD:
        signals.append((
            min(0.8, confidence), 
            confidence, 
            f"Negative direction with {confidence:.0%} confidence"
        ))
    
    # Signal 3: Probability threshold-based (p_down vs p_up)
    if p_down is not None and p_up is not None:
        if p_down >= config.P_DOWN_MIN_THRESHOLD:
            delta = p_down - p_up
            if delta >= config.P_DOWN_UP_DELTA_THRESHOLD:
                prob_score = min(0.9, p_down)
                signals.append((
                    prob_score,
                    0.85,
                    f"High down probability: {p_down:.0%} (delta: {delta:+.0%})"
                ))
    
    # Signal 4: 8-K item-based bearish detection
    if event_type_lower == 'sec_8k' and '8k_items' in metadata:
        items = metadata.get('8k_items', [])
        bearish_items = [item for item in items if item in config.BEARISH_8K_ITEMS]
        if bearish_items:
            signals.append((
                0.8,
                0.85,
                f"Bearish 8-K items: {', '.join(bearish_items)}"
            ))
    
    # Signal 5: Weighted keyword analysis (primary signal for text-based detection)
    text = f"{title} {description}".lower()
    keyword_score = 0.0
    matched_keywords = []
    for keyword, weight in config.WEIGHTED_NEGATIVE_KEYWORDS.items():
        if keyword in text:
            keyword_score += weight
            matched_keywords.append(keyword)
    
    if keyword_score >= config.MIN_KEYWORD_SCORE:
        # Normalize: 2+ high-weight keywords = max severity
        normalized_keyword_score = min(0.85, keyword_score / 2.0)
        if matched_keywords:
            # Higher confidence when more keywords match
            keyword_confidence = 0.5 + min(0.4, len(matched_keywords) * 0.1)
            signals.append((
                normalized_keyword_score,
                keyword_confidence,
                f"Bearish keywords: {', '.join(matched_keywords[:5])}"
            ))
    
    # Signal 6: ML-based bearish detection (low ML score indicates potential decline)
    if ml_adjusted_score is not None:
        if ml_adjusted_score < config.LOW_ML_SCORE_THRESHOLD:
            # Use ML confidence if available, otherwise estimate
            ml_conf = ml_confidence if ml_confidence is not None else 0.5
            signals.append((
                0.6,
                ml_conf,
                f"Low ML impact score ({ml_adjusted_score})"
            ))
    
    # Signal 7: Neutral direction with negative context in title
    # If deterministic scoring says neutral but text suggests negative
    if direction == 'neutral' and keyword_score > 0:
        # Weak signal but worth noting
        signals.append((
            min(0.5, keyword_score / 3.0),
            0.4,
            "Neutral direction with negative context"
        ))
    
    # Signal 8: Hidden Bearish detection (Market Echo Engine contrarian learning)
    # This uses historical patterns where positive/neutral predictions led to declines
    if hidden_bearish_prob is not None and hidden_bearish_prob >= config.HIDDEN_BEARISH_MIN_RATE:
        # Calculate confidence based on sample size
        sample_confidence = config.HIDDEN_BEARISH_CONFIDENCE_BOOST
        if contrarian_sample_size is not None:
            # Boost confidence with more samples (max +0.3 for 10+ samples)
            sample_boost = min(0.3, contrarian_sample_size * 0.03)
            sample_confidence += sample_boost
        
        # Score scales with contrarian probability
        hidden_score = min(0.85, hidden_bearish_prob)
        
        signals.append((
            hidden_score,
            sample_confidence,
            f"Hidden bearish pattern ({hidden_bearish_prob:.0%} historical decline rate)"
        ))
    
    # Combine signals
    if not signals:
        return {
            'bearish_signal': False,
            'bearish_score': 0.0,
            'bearish_confidence': 0.0,
            'bearish_rationale': None
        }
    
    # Calculate weighted average score and confidence
    total_weight = sum(s[1] for s in signals)  # Use confidence as weight
    weighted_score = sum(s[0] * s[1] for s in signals) / total_weight
    max_confidence = max(s[1] for s in signals)
    
    # Average confidence, boosted by multiple signals
    signal_boost = min(0.15, (len(signals) - 1) * 0.05)
    combined_confidence = min(1.0, max_confidence + signal_boost)
    
    # Determine if bearish signal threshold is met
    # Require minimum score AND confidence (using config thresholds)
    is_bearish = weighted_score >= 0.4 and combined_confidence >= config.MIN_BEARISH_CONFIDENCE
    
    # Build rationale
    reasons = [s[2] for s in signals]
    rationale = "; ".join(reasons)
    
    return {
        'bearish_signal': is_bearish,
        'bearish_score': round(weighted_score, 3),
        'bearish_confidence': round(combined_confidence, 3),
        'bearish_rationale': rationale if is_bearish else None
    }


def score_event_with_bearish(
    event_type: str,
    title: str = "",
    description: str = "",
    sector: str = None,
    market_cap: str = None,
    metadata: Dict[str, Any] = None,
    p_down: float = None,
    p_up: float = None,
    ml_adjusted_score: int = None,
    ml_confidence: float = None,
    hidden_bearish_prob: float = None,
    contrarian_sample_size: int = None
) -> Dict[str, Any]:
    """
    Score an event with both impact scoring and bearish signal detection.
    
    This is the main entry point for scoring events with bearish analysis.
    
    Args:
        hidden_bearish_prob: Probability (0-1) of hidden bearish pattern from contrarian analysis
        contrarian_sample_size: Number of historical samples supporting the pattern
    
    Returns:
        Dictionary with all scoring fields plus bearish signal fields
    """
    # Get base scoring
    result = score_event(event_type, title, description, sector, market_cap, metadata)
    
    # Compute bearish signal with contrarian learning data
    bearish_result = compute_bearish_signal(
        event_type=event_type,
        direction=result['direction'],
        confidence=result['confidence'],
        impact_score=result['impact_score'],
        title=title,
        description=description,
        p_down=p_down,
        p_up=p_up,
        ml_adjusted_score=ml_adjusted_score,
        ml_confidence=ml_confidence,
        metadata=metadata,
        hidden_bearish_prob=hidden_bearish_prob,
        contrarian_sample_size=contrarian_sample_size
    )
    
    # Merge results
    result.update(bearish_result)
    return result
