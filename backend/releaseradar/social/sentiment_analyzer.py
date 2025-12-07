"""
Sentiment Analysis for Market Echo Engine.

Provides rule-based and pattern-based sentiment scoring for tweets
without requiring heavy transformer models.
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import numpy as np

from releaseradar.log_config import logger
from .twitter_ingestor import TweetData, SocialEventSignal


@dataclass
class SentimentResult:
    """Result of sentiment analysis for a single tweet."""
    score: float
    label: str
    confidence: float
    signals: List[str]


class SentimentAnalyzer:
    """
    Rule-based sentiment analyzer optimized for financial tweets.
    
    Uses pattern matching, keyword scoring, and engagement weighting
    to determine sentiment without requiring ML inference.
    """
    
    POSITIVE_KEYWORDS = {
        "bull": 0.7, "bullish": 0.8, "buy": 0.5, "long": 0.4,
        "moon": 0.7, "rocket": 0.6, "soar": 0.7, "surge": 0.6,
        "beat": 0.6, "exceed": 0.5, "strong": 0.4, "growth": 0.4,
        "breakout": 0.6, "rally": 0.5, "gain": 0.4, "profit": 0.4,
        "upgrade": 0.6, "outperform": 0.5, "winner": 0.5, "love": 0.3,
        "amazing": 0.4, "great": 0.3, "excellent": 0.4, "impressive": 0.4,
        "approval": 0.5, "approved": 0.6, "success": 0.5, "breakthrough": 0.7,
        "raise": 0.4, "raised": 0.4, "higher": 0.3, "increase": 0.3,
        "positive": 0.4, "optimistic": 0.5, "confident": 0.4
    }
    
    NEGATIVE_KEYWORDS = {
        "bear": 0.7, "bearish": 0.8, "sell": 0.5, "short": 0.4,
        "crash": 0.8, "dump": 0.7, "tank": 0.7, "plunge": 0.7,
        "miss": 0.6, "disappoint": 0.6, "weak": 0.4, "decline": 0.4,
        "breakdown": 0.6, "drop": 0.4, "loss": 0.4, "lose": 0.4,
        "downgrade": 0.6, "underperform": 0.5, "loser": 0.5, "hate": 0.5,
        "terrible": 0.5, "awful": 0.5, "horrible": 0.5, "disaster": 0.6,
        "rejection": 0.6, "rejected": 0.6, "fail": 0.5, "failed": 0.5,
        "cut": 0.4, "lower": 0.3, "decrease": 0.3, "reduce": 0.3,
        "negative": 0.4, "pessimistic": 0.5, "worried": 0.4, "concern": 0.3,
        "warning": 0.5, "risk": 0.3, "fraud": 0.8, "scam": 0.8
    }
    
    AMPLIFIERS = {
        "very": 1.3, "extremely": 1.5, "incredibly": 1.4, "super": 1.3,
        "massively": 1.4, "absolutely": 1.3, "definitely": 1.2, "really": 1.2,
        "huge": 1.4, "major": 1.3, "significant": 1.2
    }
    
    NEGATORS = {"not", "no", "never", "n't", "dont", "don't", "isn't", "won't", "can't"}
    
    EMOJI_SENTIMENT = {
        "🚀": 0.6, "📈": 0.5, "💰": 0.4, "🔥": 0.4, "💎": 0.5,
        "🐂": 0.6, "💪": 0.4, "✅": 0.3, "🎯": 0.3, "⬆️": 0.4,
        "📉": -0.5, "💀": -0.5, "🐻": -0.6, "😱": -0.4, "❌": -0.4,
        "⬇️": -0.4, "🗑️": -0.5, "💩": -0.5, "😢": -0.3, "😭": -0.4
    }
    
    def __init__(self):
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile regex patterns for efficiency."""
        self.ticker_pattern = re.compile(r'\$[A-Z]{1,5}\b')
        self.hashtag_pattern = re.compile(r'#\w+')
        self.url_pattern = re.compile(r'https?://\S+')
        self.mention_pattern = re.compile(r'@\w+')
        self.price_target_pattern = re.compile(
            r'(?:PT|price target|target)[:\s]*\$?(\d+(?:\.\d+)?)',
            re.IGNORECASE
        )
        self.percentage_pattern = re.compile(
            r'([+-]?\d+(?:\.\d+)?)\s*%',
            re.IGNORECASE
        )
    
    def analyze_tweet(self, tweet: TweetData) -> SentimentResult:
        """
        Analyze sentiment of a single tweet.
        
        Args:
            tweet: TweetData object to analyze
            
        Returns:
            SentimentResult with score, label, and confidence
        """
        text = tweet.text.lower()
        text_clean = self.url_pattern.sub('', text)
        text_clean = self.mention_pattern.sub('', text_clean)
        
        signals = []
        sentiment_scores = []
        
        words = text_clean.split()
        negation_window = 0
        amplifier = 1.0
        
        for i, word in enumerate(words):
            word_clean = re.sub(r'[^\w]', '', word)
            
            if word_clean in self.NEGATORS:
                negation_window = 3
                continue
            
            if word_clean in self.AMPLIFIERS:
                amplifier = self.AMPLIFIERS[word_clean]
                continue
            
            if word_clean in self.POSITIVE_KEYWORDS:
                score = self.POSITIVE_KEYWORDS[word_clean] * amplifier
                if negation_window > 0:
                    score = -score * 0.8
                    signals.append(f"negated_positive:{word_clean}")
                else:
                    signals.append(f"positive:{word_clean}")
                sentiment_scores.append(score)
            
            elif word_clean in self.NEGATIVE_KEYWORDS:
                score = -self.NEGATIVE_KEYWORDS[word_clean] * amplifier
                if negation_window > 0:
                    score = -score * 0.8
                    signals.append(f"negated_negative:{word_clean}")
                else:
                    signals.append(f"negative:{word_clean}")
                sentiment_scores.append(score)
            
            amplifier = 1.0
            if negation_window > 0:
                negation_window -= 1
        
        for emoji, score in self.EMOJI_SENTIMENT.items():
            if emoji in tweet.text:
                sentiment_scores.append(score)
                signals.append(f"emoji:{emoji}")
        
        price_targets = self.price_target_pattern.findall(text)
        if price_targets:
            signals.append("has_price_target")
        
        percentages = self.percentage_pattern.findall(text)
        for pct_str in percentages:
            try:
                pct = float(pct_str)
                if pct > 0:
                    sentiment_scores.append(min(0.5, pct / 100))
                    signals.append(f"positive_pct:{pct}")
                elif pct < 0:
                    sentiment_scores.append(max(-0.5, pct / 100))
                    signals.append(f"negative_pct:{pct}")
            except ValueError:
                pass
        
        if sentiment_scores:
            raw_score = np.mean(sentiment_scores)
            final_score = np.clip(raw_score, -1.0, 1.0)
            confidence = min(1.0, len(sentiment_scores) * 0.2 + 0.3)
        else:
            final_score = 0.0
            confidence = 0.2
        
        if final_score > 0.15:
            label = "positive"
        elif final_score < -0.15:
            label = "negative"
        else:
            label = "neutral"
        
        return SentimentResult(
            score=final_score,
            label=label,
            confidence=confidence,
            signals=signals
        )
    
    def aggregate_sentiment(
        self,
        tweets: List[TweetData],
        event_id: int,
        ticker: str,
        event_type: str,
        volume_baseline: Tuple[float, float] = (0.0, 1.0)
    ) -> SocialEventSignal:
        """
        Aggregate sentiment from multiple tweets into event signal.
        
        Args:
            tweets: List of tweets to analyze
            event_id: Associated event ID
            ticker: Stock ticker
            event_type: Type of event
            volume_baseline: (mean, std) for z-score calculation
            
        Returns:
            SocialEventSignal with aggregated metrics
        """
        if not tweets:
            return SocialEventSignal(
                event_id=event_id,
                ticker=ticker,
                event_type=event_type,
                tweet_count=0,
                unique_authors=0,
                avg_sentiment=0.0,
                sentiment_std=0.0,
                positive_ratio=0.0,
                negative_ratio=0.0,
                neutral_ratio=1.0,
                total_engagement=0.0,
                influencer_count=0,
                influencer_sentiment=None,
                volume_zscore=0.0,
                peak_hour=None,
                tweet_velocity=0.0,
                sample_tweets=[]
            )
        
        sentiments = []
        engagement_weighted_sentiments = []
        influencer_sentiments = []
        
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        
        total_engagement = 0.0
        unique_authors = set()
        influencer_count = 0
        
        hour_counts: Dict[int, int] = {}
        
        sample_tweets = []
        
        for tweet in tweets:
            result = self.analyze_tweet(tweet)
            sentiments.append(result.score)
            
            engagement = tweet.engagement_score
            total_engagement += engagement
            engagement_weighted_sentiments.append((result.score, engagement))
            
            unique_authors.add(tweet.author_id)
            
            if tweet.is_influencer:
                influencer_count += 1
                influencer_sentiments.append(result.score)
            
            if result.label == "positive":
                positive_count += 1
            elif result.label == "negative":
                negative_count += 1
            else:
                neutral_count += 1
            
            hour = tweet.created_at.hour
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
            
            if len(sample_tweets) < 5:
                sample_tweets.append({
                    "text": tweet.text[:280],
                    "sentiment": result.score,
                    "label": result.label,
                    "engagement": engagement,
                    "is_influencer": tweet.is_influencer
                })
        
        n = len(tweets)
        avg_sentiment = np.mean(sentiments)
        sentiment_std = np.std(sentiments) if n > 1 else 0.0
        
        if total_engagement > 0:
            weighted_sum = sum(s * w for s, w in engagement_weighted_sentiments)
            avg_sentiment = 0.6 * avg_sentiment + 0.4 * (weighted_sum / total_engagement)
        
        influencer_sentiment = None
        if influencer_sentiments:
            influencer_sentiment = np.mean(influencer_sentiments)
        
        peak_hour = max(hour_counts, key=hour_counts.get) if hour_counts else None
        
        if tweets:
            time_range = (max(t.created_at for t in tweets) - min(t.created_at for t in tweets))
            hours = max(1.0, time_range.total_seconds() / 3600)
            tweet_velocity = n / hours
        else:
            tweet_velocity = 0.0
        
        mean_vol, std_vol = volume_baseline
        volume_zscore = (n - mean_vol) / std_vol if std_vol > 0 else 0.0
        
        return SocialEventSignal(
            event_id=event_id,
            ticker=ticker,
            event_type=event_type,
            tweet_count=n,
            unique_authors=len(unique_authors),
            avg_sentiment=float(avg_sentiment),
            sentiment_std=float(sentiment_std),
            positive_ratio=positive_count / n,
            negative_ratio=negative_count / n,
            neutral_ratio=neutral_count / n,
            total_engagement=total_engagement,
            influencer_count=influencer_count,
            influencer_sentiment=influencer_sentiment,
            volume_zscore=float(volume_zscore),
            peak_hour=peak_hour,
            tweet_velocity=tweet_velocity,
            sample_tweets=sample_tweets
        )
    
    def get_sentiment_features(self, signal: SocialEventSignal) -> Dict[str, float]:
        """
        Extract features from social signal for ML model input.
        
        Returns dict of features that can be merged with EventFeatures.
        """
        return {
            "social_tweet_count": signal.tweet_count,
            "social_unique_authors": signal.unique_authors,
            "social_avg_sentiment": signal.avg_sentiment,
            "social_sentiment_std": signal.sentiment_std,
            "social_positive_ratio": signal.positive_ratio,
            "social_negative_ratio": signal.negative_ratio,
            "social_engagement": min(signal.total_engagement, 10000) / 10000,
            "social_influencer_count": signal.influencer_count,
            "social_influencer_sentiment": signal.influencer_sentiment or 0.0,
            "social_volume_zscore": np.clip(signal.volume_zscore, -5, 5),
            "social_velocity": min(signal.tweet_velocity, 100) / 100
        }
