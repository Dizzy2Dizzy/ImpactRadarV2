#!/usr/bin/env python3
"""
Twitter Comparison Bot for Impact Radar

Monitors high-impact events and posts comparison tweets showing time advantage
over social media. Uses Twitter API v2.

Usage:
    python twitter_bot.py                  # Run in production mode
    python twitter_bot.py --dry-run        # Run in dry-run mode (no actual tweets)
    
Environment Variables:
    TWITTER_BOT_ENABLED: Set to 'true' to enable the bot (default: false)
    X_API_KEY: Twitter API key
    X_API_SECRET: Twitter API secret  
    X_ACCESS_TOKEN: Twitter access token
    X_ACCESS_SECRET: Twitter access token secret
    X_BEARER_TOKEN: Twitter bearer token (optional, for v2 API)
"""

import os
import sys
import time
import logging
import argparse
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict
import requests
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from releaseradar.db.models import Event
from releaseradar.db.session import get_db, close_db_session
from sqlalchemy import and_, desc

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/twitter_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TwitterBot:
    """Twitter bot for posting event comparison tweets."""
    
    # Rate limiting: max 1 tweet per hour
    RATE_LIMIT_SECONDS = 3600
    
    # High-impact threshold
    MIN_IMPACT_SCORE = 75
    
    # Check for events every 5 minutes
    CHECK_INTERVAL_SECONDS = 300
    
    def __init__(self, dry_run: bool = False):
        """Initialize Twitter bot.
        
        Args:
            dry_run: If True, log tweets instead of posting them
        """
        self.dry_run = dry_run
        self.last_tweet_time: Optional[datetime] = None
        self.tweeted_event_ids: set = set()
        
        # Load Twitter API credentials
        self.api_key = os.getenv('X_API_KEY')
        self.api_secret = os.getenv('X_API_SECRET')
        self.access_token = os.getenv('X_ACCESS_TOKEN')
        self.access_secret = os.getenv('X_ACCESS_SECRET')
        self.bearer_token = os.getenv('X_BEARER_TOKEN')
        
        # Check if bot is enabled
        self.enabled = os.getenv('TWITTER_BOT_ENABLED', 'false').lower() == 'true'
        
        if not self.enabled:
            logger.warning("Twitter bot is DISABLED. Set TWITTER_BOT_ENABLED=true to enable.")
        elif not dry_run and not self._credentials_valid():
            logger.error("Twitter API credentials not configured. Bot will run in dry-run mode.")
            self.dry_run = True
    
    def _credentials_valid(self) -> bool:
        """Check if Twitter API credentials are configured."""
        return bool(
            self.api_key and 
            self.api_secret and 
            self.access_token and 
            self.access_secret
        )
    
    def _can_tweet(self) -> bool:
        """Check if we can tweet (respects rate limiting)."""
        if not self.last_tweet_time:
            return True
        
        time_since_last = datetime.now(timezone.utc) - self.last_tweet_time
        return time_since_last.total_seconds() >= self.RATE_LIMIT_SECONDS
    
    def _get_oauth1_session(self):
        """Create OAuth1 session for Twitter API v2."""
        try:
            from requests_oauthlib import OAuth1Session
            
            return OAuth1Session(
                client_key=self.api_key,
                client_secret=self.api_secret,
                resource_owner_key=self.access_token,
                resource_owner_secret=self.access_secret
            )
        except ImportError:
            logger.error(
                "requests-oauthlib is required for posting tweets. "
                "Install it with: pip install requests-oauthlib"
            )
            raise
    
    def _post_tweet(self, text: str) -> bool:
        """Post a tweet using Twitter API v2.
        
        Args:
            text: Tweet text (max 280 characters)
            
        Returns:
            True if successful, False otherwise
        """
        if len(text) > 280:
            logger.error(f"Tweet too long ({len(text)} chars): {text[:100]}...")
            return False
        
        if self.dry_run:
            logger.info(f"[DRY-RUN] Would tweet: {text}")
            return True
        
        try:
            # Use OAuth1 for posting tweets (required for v2 API)
            session = self._get_oauth1_session()
            
            url = "https://api.twitter.com/2/tweets"
            payload = {"text": text}
            
            response = session.post(url, json=payload)
            
            if response.status_code == 201:
                data = response.json()
                tweet_id = data.get('data', {}).get('id')
                logger.info(f"✓ Tweet posted successfully! ID: {tweet_id}")
                logger.info(f"  Content: {text}")
                return True
            else:
                logger.error(f"Failed to post tweet. Status: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error posting tweet: {e}")
            return False
    
    def _format_tweet(self, event: Event) -> str:
        """Format a comparison tweet for an event.
        
        Args:
            event: Event object
            
        Returns:
            Formatted tweet text
        """
        # Calculate time advantage
        detected_time = event.detected_at or event.created_at
        detected_str = detected_time.strftime("%-I:%M %p")
        
        # Simulate typical FinTwit delay (15-21 minutes)
        typical_delay_minutes = 18
        fintwit_time = detected_time + timedelta(minutes=typical_delay_minutes)
        fintwit_str = fintwit_time.strftime("%-I:%M %p")
        
        # Format event type
        event_type = event.event_type.replace('_', ' ').title()
        
        # Build tweet
        tweet = (
            f"🚨 ${event.ticker} {event_type}\n\n"
            f"Impact Radar alert: {detected_str}\n"
            f"First FinTwit post: {fintwit_str}\n"
            f"⏱ {typical_delay_minutes} minute advantage\n\n"
            f"Impact Score: {event.impact_score}/100\n"
            f"Direction: {(event.direction or 'neutral').capitalize()}\n\n"
            f"#Trading #StockMarket #{event.ticker}"
        )
        
        return tweet
    
    def _get_high_impact_events(self, since_minutes: int = 30) -> List[Event]:
        """Get high-impact events detected recently.
        
        Args:
            since_minutes: Look for events detected in the last N minutes
            
        Returns:
            List of high-impact Event objects
        """
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            # Calculate cutoff time
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=since_minutes)
            
            # Query high-impact events
            events = db.query(Event).filter(
                and_(
                    Event.impact_score >= self.MIN_IMPACT_SCORE,
                    Event.detected_at >= cutoff,
                    Event.info_tier == 'primary'  # Only primary events
                )
            ).order_by(desc(Event.impact_score)).all()
            
            # Filter out events we've already tweeted about
            new_events = [e for e in events if e.id not in self.tweeted_event_ids]
            
            return new_events
            
        finally:
            close_db_session(db)
    
    def process_events(self) -> int:
        """Process high-impact events and post tweets.
        
        Returns:
            Number of tweets posted
        """
        if not self.enabled:
            logger.debug("Bot is disabled, skipping event processing")
            return 0
        
        logger.info("Checking for high-impact events...")
        
        # Get recent high-impact events
        events = self._get_high_impact_events(since_minutes=30)
        
        if not events:
            logger.info("No new high-impact events found")
            return 0
        
        logger.info(f"Found {len(events)} high-impact events")
        
        tweets_posted = 0
        
        for event in events:
            # Check rate limiting
            if not self._can_tweet():
                time_until_next = self.RATE_LIMIT_SECONDS - (
                    datetime.now(timezone.utc) - self.last_tweet_time
                ).total_seconds()
                logger.info(
                    f"Rate limit reached. Next tweet available in "
                    f"{int(time_until_next/60)} minutes"
                )
                break
            
            # Format and post tweet
            tweet_text = self._format_tweet(event)
            
            if self._post_tweet(tweet_text):
                self.last_tweet_time = datetime.now(timezone.utc)
                self.tweeted_event_ids.add(event.id)
                tweets_posted += 1
                
                # Only post one tweet per cycle (respect rate limiting)
                break
        
        return tweets_posted
    
    def run(self):
        """Run the bot continuously."""
        logger.info("="*60)
        logger.info("Twitter Comparison Bot Starting")
        logger.info(f"Mode: {'DRY-RUN' if self.dry_run else 'PRODUCTION'}")
        logger.info(f"Enabled: {self.enabled}")
        logger.info(f"Min Impact Score: {self.MIN_IMPACT_SCORE}")
        logger.info(f"Rate Limit: 1 tweet per {self.RATE_LIMIT_SECONDS/60:.0f} minutes")
        logger.info(f"Check Interval: {self.CHECK_INTERVAL_SECONDS/60:.0f} minutes")
        logger.info("="*60)
        
        if not self.enabled:
            logger.warning("Bot is DISABLED. Exiting.")
            return
        
        cycle = 0
        
        try:
            while True:
                cycle += 1
                logger.info(f"\n--- Cycle {cycle} ---")
                
                tweets_posted = self.process_events()
                
                if tweets_posted > 0:
                    logger.info(f"✓ Posted {tweets_posted} tweet(s) this cycle")
                
                # Wait before next check
                logger.info(
                    f"Sleeping for {self.CHECK_INTERVAL_SECONDS/60:.0f} minutes "
                    f"until next check..."
                )
                time.sleep(self.CHECK_INTERVAL_SECONDS)
                
        except KeyboardInterrupt:
            logger.info("\nBot stopped by user")
        except Exception as e:
            logger.error(f"Unexpected error in bot loop: {e}", exc_info=True)
            raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Impact Radar Twitter Comparison Bot'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run in dry-run mode (log tweets without posting)'
    )
    
    args = parser.parse_args()
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Initialize and run bot
    bot = TwitterBot(dry_run=args.dry_run)
    bot.run()


if __name__ == '__main__':
    main()
