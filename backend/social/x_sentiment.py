"""
Sentiment Analysis for X.com Posts using OpenAI

Analyzes social media posts to determine sentiment (bullish/bearish/neutral)
and detect event hints (earnings, FDA, guidance, etc.).
Falls back to keyword-based analysis if OpenAI is unavailable.
"""

import os
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional
import re

logger = logging.getLogger(__name__)

# Try to import OpenAI, but handle gracefully if not available
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI package not installed. Using keyword-based sentiment analysis only.")


@dataclass
class PostAnalysis:
    """Analysis result for a social media post"""
    sentiment: str  # 'bullish', 'bearish', or 'neutral'
    strength: float  # 0-1, strength of sentiment
    event_hint: str  # 'earnings', 'fda', 'guidance', 'macro', 'product', 'other'
    confidence: float  # 0-1, confidence in the analysis


# Sentiment keywords for fallback analysis
BULLISH_KEYWORDS = {
    'moon', 'bullish', 'calls', 'buy', 'long', 'breakout', 'rally', 'pump',
    'gains', 'winning', 'beat', 'beats', 'crush', 'soar', 'rocket', 'bull',
    'approval', 'approved', 'partnership', 'breakthrough', 'strong', 'outperform'
}

BEARISH_KEYWORDS = {
    'bearish', 'puts', 'sell', 'short', 'crash', 'dump', 'tank', 'plunge',
    'losses', 'losing', 'miss', 'misses', 'fail', 'failed', 'reject', 'rejected',
    'concern', 'warning', 'investigation', 'recall', 'lawsuit', 'decline', 'bear'
}

# Event hint keywords
EVENT_KEYWORDS = {
    'earnings': {'earnings', 'eps', 'revenue', 'quarterly', 'q1', 'q2', 'q3', 'q4', 'profit', 'beat', 'miss'},
    'fda': {'fda', 'approval', 'clinical', 'trial', 'phase', 'adcom', 'pdufa', 'drug', 'therapy'},
    'guidance': {'guidance', 'forecast', 'outlook', 'raise', 'lower', 'estimates', 'target'},
    'macro': {'fed', 'inflation', 'rate', 'economy', 'gdp', 'unemployment', 'cpi', 'fomc'},
    'product': {'launch', 'product', 'release', 'unveil', 'announce', 'new'}
}


def analyze_posts_with_openai(posts: List['SocialPost']) -> Dict[str, PostAnalysis]:
    """
    Analyze posts using OpenAI API for sentiment and event hints.
    
    Args:
        posts: List of SocialPost objects
        
    Returns:
        Dict mapping post_id to PostAnalysis
    """
    # Import SocialPost type for type hint
    from backend.social.x_client import SocialPost
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.warning("OPENAI_API_KEY not set. Falling back to keyword analysis.")
        return analyze_posts_with_keywords(posts)
    
    if not OPENAI_AVAILABLE:
        logger.warning("OpenAI package not available. Falling back to keyword analysis.")
        return analyze_posts_with_keywords(posts)
    
    # Configure OpenAI client
    client = openai.OpenAI(api_key=api_key)
    
    analyses = {}
    
    # Batch posts for efficiency (analyze up to 10 at a time)
    batch_size = 10
    for i in range(0, len(posts), batch_size):
        batch = posts[i:i + batch_size]
        
        # Build prompt for batch analysis
        posts_text = "\n\n".join([
            f"POST {j+1} (ID: {post.id}):\n{post.text}\nTickers: {', '.join(post.symbols)}"
            for j, post in enumerate(batch)
        ])
        
        prompt = f"""Analyze these stock-related social media posts for sentiment and event hints.

For each post, provide:
1. sentiment: bullish, bearish, or neutral
2. strength: 0-1 (how strong is the sentiment)
3. event_hint: earnings, fda, guidance, macro, product, or other
4. confidence: 0-1 (how confident are you in this analysis)

Posts:
{posts_text}

Respond in this exact format for each post:
POST X: sentiment=<value>, strength=<value>, event_hint=<value>, confidence=<value>
"""
        
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a financial sentiment analysis expert specializing in stock market social media."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            # Parse response
            result_text = response.choices[0].message.content
            
            # Extract analyses using regex
            pattern = r'POST (\d+):\s*sentiment=(\w+),\s*strength=([\d.]+),\s*event_hint=(\w+),\s*confidence=([\d.]+)'
            matches = re.findall(pattern, result_text)
            
            for match in matches:
                post_idx = int(match[0]) - 1  # Convert to 0-indexed
                if post_idx < len(batch):
                    post = batch[post_idx]
                    
                    analyses[post.id] = PostAnalysis(
                        sentiment=match[1].lower(),
                        strength=float(match[2]),
                        event_hint=match[3].lower(),
                        confidence=float(match[4])
                    )
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}. Falling back to keyword analysis for batch.")
            # Fallback to keyword analysis for this batch
            for post in batch:
                if post.id not in analyses:
                    keyword_analyses = analyze_posts_with_keywords([post])
                    analyses.update(keyword_analyses)
    
    return analyses


def analyze_posts_with_keywords(posts: List['SocialPost']) -> Dict[str, PostAnalysis]:
    """
    Analyze posts using keyword-based heuristics (fallback method).
    
    Args:
        posts: List of SocialPost objects
        
    Returns:
        Dict mapping post_id to PostAnalysis
    """
    # Import SocialPost type for type hint
    from backend.social.x_client import SocialPost
    
    analyses = {}
    
    for post in posts:
        text_lower = post.text.lower()
        
        # Count bullish/bearish keywords
        bullish_count = sum(1 for kw in BULLISH_KEYWORDS if kw in text_lower)
        bearish_count = sum(1 for kw in BEARISH_KEYWORDS if kw in text_lower)
        
        # Determine sentiment
        if bullish_count > bearish_count:
            sentiment = 'bullish'
            strength = min(bullish_count / 3.0, 1.0)  # Normalize to 0-1
        elif bearish_count > bullish_count:
            sentiment = 'bearish'
            strength = min(bearish_count / 3.0, 1.0)
        else:
            sentiment = 'neutral'
            strength = 0.5
        
        # Detect event hint
        event_hint = 'other'
        max_matches = 0
        
        for event_type, keywords in EVENT_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw in text_lower)
            if matches > max_matches:
                max_matches = matches
                event_hint = event_type
        
        # Calculate confidence based on keyword matches
        total_keywords = bullish_count + bearish_count + max_matches
        confidence = min(0.3 + (total_keywords * 0.15), 0.8)  # 0.3-0.8 range
        
        analyses[post.id] = PostAnalysis(
            sentiment=sentiment,
            strength=strength,
            event_hint=event_hint,
            confidence=confidence
        )
    
    return analyses


def analyze_posts(posts: List['SocialPost']) -> Dict[str, PostAnalysis]:
    """
    Analyze social media posts for sentiment and event hints.
    
    Tries OpenAI first, falls back to keyword-based analysis if unavailable.
    
    Args:
        posts: List of SocialPost objects
        
    Returns:
        Dict mapping post_id to PostAnalysis
    """
    # Import SocialPost type for type hint
    from backend.social.x_client import SocialPost
    
    if not posts:
        return {}
    
    # Try OpenAI first if available
    if OPENAI_AVAILABLE and os.getenv('OPENAI_API_KEY'):
        logger.info(f"Analyzing {len(posts)} posts with OpenAI")
        return analyze_posts_with_openai(posts)
    else:
        logger.info(f"Analyzing {len(posts)} posts with keyword-based analysis")
        return analyze_posts_with_keywords(posts)
