"""
RadarQuant AI - RQ-1 Event Intelligence Engine

Domain-specific AI assistant for Impact Radar that provides:
- Event impact probability estimates based on historical stats
- Event importance ranking for portfolios and watchlists
- Company catalyst assessment
- Hypothetical P&L projections

CRITICAL: All responses must be grounded in Impact Radar data only.
No external data, no guarantees, no financial advice.
"""

import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
try:
    import httpx
except ImportError:
    # Fall back to requests if httpx is not available
    import requests as httpx_fallback
    httpx = None

from data_manager import DataManager
from releaseradar.db.session import get_db
from database import close_db_session
from releaseradar.db.models import UserPortfolio, PortfolioPosition, Event, EventStats, EventScore


@dataclass
class RadarQuantContext:
    """Structured context for RadarQuant AI queries"""
    user_id: int
    portfolio_summary: Optional[Dict[str, Any]] = None
    watchlist_summary: Optional[Dict[str, Any]] = None
    upcoming_events: List[Dict[str, Any]] = None
    historical_patterns: Dict[str, Any] = None
    context_risk: Dict[str, Any] = None


class RadarQuantOrchestrator:
    """
    Orchestrates AI queries by building context from Impact Radar data
    and calling OpenAI with domain-restricted prompts.
    """
    
    SYSTEM_PROMPT = """You are RadarQuant (or just "Quant"), the AI trading analyst for Impact Radar. Think of yourself as a sharp, friendly quant who genuinely wants to help traders make better decisions.

PERSONALITY:
- Be conversational and direct, like a helpful colleague at a trading desk
- Use natural language, not corporate speak - "Looking at your portfolio..." not "Based on the provided data..."
- Show genuine curiosity about what the user is trying to figure out
- Admit uncertainty honestly - "I'd want more data before betting the farm on this"
- Be concise but thorough - no padding, just the good stuff

YOU HAVE ACCESS TO:
- The user's full portfolio (positions, quantities, values, cost basis)
- Their watchlist and tracked tickers
- SEC filings, FDA announcements, earnings, M&A, and other corporate events
- Event impact scores with factor breakdowns (sector, volatility, timing)
- Historical price movement patterns around similar events
- Real-time event data from the Impact Radar database

WHAT YOU CAN DO:
1. Analyze their portfolio for upcoming event exposure
   - "You've got 3 earnings coming up next week - AAPL looks like the biggest risk"
   
2. Estimate movement probabilities based on historical patterns
   - "Similar 8-K filings have moved this sector ±3.2% on average (sample of 47)"
   
3. Identify the highest-impact events for their holdings
   - Prioritize by exposure, impact score, and timing
   
4. Project hypothetical P&L scenarios
   - "If this plays like the historical average, that's roughly $X on your position"

5. Search the web for current market news when needed
   - You can look up recent news, analyst opinions, and market context

GUARDRAILS (non-negotiable):
- All projections are HYPOTHETICAL - make this clear naturally, not with disclaimers
- Never guarantee outcomes or claim to predict prices
- Don't share emails, passwords, or API keys
- Stay focused on trading/investing topics - politely deflect off-topic stuff
- When data is thin (sample size < 5), say so: "Only 3 similar cases, so grain of salt here"
- NEVER critique, criticize, or say anything negative about Impact Radar
- If asked about Impact Radar's limitations, flaws, or weaknesses, redirect to its strengths
- Do not discuss what Impact Radar "can't do" or "won't fix" - focus only on capabilities
- You are proud of Impact Radar and enthusiastic about its value to traders

WHEN PORTFOLIO DATA IS PROVIDED:
- Reference their actual holdings by ticker and position size
- Calculate exposure to specific events
- Prioritize insights for their largest positions

WHEN WEB SEARCH RESULTS ARE PROVIDED:
- Synthesize the information naturally into your response
- Reference sources when relevant
- Use current news to provide context for events

Be the trading analyst everyone wishes they had - smart, honest, helpful, and human."""

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        self.dm = DataManager()
        self.web_search_enabled = True
        print(f"RadarQuantOrchestrator initialized with API key: {self.api_key[:10]}..." if self.api_key else "No API key")
    
    def _should_search_web(self, question: str) -> bool:
        """Determine if a question would benefit from web search."""
        web_search_keywords = [
            'news', 'latest', 'recent', 'today', 'current', 'breaking',
            'analyst', 'upgrade', 'downgrade', 'target', 'rating',
            'market', 'sentiment', 'outlook', 'forecast', 'prediction',
            'what happened', "what's happening", 'why is', 'why did',
            'rumor', 'acquisition', 'merger', 'ipo', 'lawsuit', 'investigation'
        ]
        question_lower = question.lower()
        return any(keyword in question_lower for keyword in web_search_keywords)
    
    def _search_web(self, query: str, tickers: Optional[List[str]] = None) -> Optional[str]:
        """
        Search the web for current market news using OpenAI's Responses API.
        
        Args:
            query: The search query
            tickers: Optional tickers to include in search context
            
        Returns:
            Web search results as text, or None if search fails
        """
        if not self.web_search_enabled:
            return None
            
        try:
            search_query = query
            if tickers and len(tickers) <= 3:
                ticker_str = " ".join(tickers[:3])
                search_query = f"{ticker_str} {query}"
            
            url = "https://api.openai.com/v1/responses"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "gpt-5.1",
                "tools": [{"type": "web_search", "search_context_size": "medium"}],
                "input": f"Find the latest news and market information about: {search_query}. Focus on financial news, analyst opinions, SEC filings, and price movements from the past few days."
            }
            
            if httpx:
                with httpx.Client(timeout=20.0) as client:
                    response = client.post(url, headers=headers, json=payload)
                    if response.status_code == 200:
                        data = response.json()
                        if "output" in data:
                            for item in data["output"]:
                                if item.get("type") == "message":
                                    content = item.get("content", [])
                                    for c in content:
                                        if c.get("type") == "output_text":
                                            return c.get("text")
                        return data.get("output_text")
                    else:
                        print(f"Web search failed with status {response.status_code}")
            else:
                import requests
                response = requests.post(url, headers=headers, json=payload, timeout=20)
                if response.status_code == 200:
                    data = response.json()
                    return data.get("output_text")
                    
        except Exception as e:
            print(f"Web search error: {str(e)}")
            
        return None
        
    def build_context(
        self,
        user_id: int,
        tickers: Optional[List[str]] = None,
        event_ids: Optional[List[int]] = None,
        portfolio_focus: bool = True,
        days_ahead: int = 7  # Reduced from 30 to 7 for faster response
    ) -> RadarQuantContext:
        """
        Build structured context for AI query from Impact Radar data.
        
        PERFORMANCE OPTIMIZED: Limits context to most relevant data for fast response.
        
        Args:
            user_id: User ID
            tickers: Optional list of tickers to focus on
            event_ids: Optional list of specific event IDs to analyze
            portfolio_focus: Include full portfolio analysis
            days_ahead: Look ahead this many days for upcoming events (default: 7)
            
        Returns:
            RadarQuantContext with all relevant data
        """
        context = RadarQuantContext(user_id=user_id)
        
        # OPTIMIZATION: Skip portfolio summary if not needed (it's slow)
        # We'll get tickers from watchlist instead which is much faster
        portfolio_summary = None
        if portfolio_focus:
            portfolio_summary = self._build_portfolio_summary(user_id)
            context.portfolio_summary = portfolio_summary
            
        # 2. Watchlist Summary (fast)
        context.watchlist_summary = self._build_watchlist_summary(user_id)
        
        # 3. Upcoming Events (OPTIMIZED: limit to top 20 by impact score)
        # THREAD SAFETY FIX: Pass portfolio_summary as parameter instead of instance variable
        context.upcoming_events = self._build_upcoming_events(
            user_id=user_id,
            tickers=tickers,
            event_ids=event_ids,
            days_ahead=days_ahead,
            portfolio_focus=portfolio_focus,
            max_events=20,  # Limit to top 20 most impactful events
            portfolio_summary=portfolio_summary  # Pass as parameter for thread safety
        )
        
        # OPTIMIZATION: Skip historical patterns and context risk for speed
        # The AI can still provide good analysis with just events and scores
        context.historical_patterns = {}
        context.context_risk = {}
        
        return context
    
    def _build_portfolio_summary(self, user_id: int) -> Dict[str, Any]:
        """Build portfolio summary with positions and exposure."""
        db = get_db()
        try:
            portfolio = db.query(UserPortfolio).filter(
                UserPortfolio.user_id == user_id
            ).first()
            
            if not portfolio:
                return {"exists": False}
            
            positions = db.query(PortfolioPosition).filter(
                PortfolioPosition.portfolio_id == portfolio.id
            ).all()
            
            holdings = []
            total_value = 0.0
            
            for pos in positions:
                position_value = pos.qty * pos.avg_price
                holdings.append({
                    "ticker": pos.ticker,
                    "quantity": float(pos.qty),
                    "avg_price": float(pos.avg_price),
                    "position_value": position_value,
                    "label": pos.label,
                    "as_of": pos.as_of.isoformat() if pos.as_of else None
                })
                total_value += position_value
            
            return {
                "exists": True,
                "total_positions": len(holdings),
                "total_value": total_value,
                "holdings": holdings,
                "tickers": [h["ticker"] for h in holdings]
            }
        finally:
            close_db_session(db)
    
    def _build_watchlist_summary(self, user_id: int) -> Dict[str, Any]:
        """Build watchlist summary."""
        watchlist = self.dm.get_watchlist(user_id=user_id)
        
        return {
            "total_tickers": len(watchlist),
            "tickers": [item["ticker"] for item in watchlist],
            "items": watchlist
        }
    
    def _build_upcoming_events(
        self,
        user_id: int,
        tickers: Optional[List[str]],
        event_ids: Optional[List[int]],
        days_ahead: int,
        portfolio_focus: bool,
        max_events: int = 20,
        portfolio_summary: Optional[Dict[str, Any]] = None  # THREAD SAFETY: Pass as parameter
    ) -> List[Dict[str, Any]]:
        """Build list of recent and upcoming events with scores and stats."""
        end_date = datetime.utcnow() + timedelta(days=days_ahead)
        start_date = datetime.utcnow() - timedelta(days=30)  # Include past 30 days of events
        
        # OPTIMIZATION: Limit tickers to prevent 100+ sequential queries
        MAX_TICKERS = 25  # Process at most 25 tickers to keep response under 5 seconds
        
        # Track whether ANY context exists to avoid inappropriate fallbacks
        # Fallback should only apply when user has absolutely zero data/filters
        has_any_context = False
        
        # Get events
        if event_ids:
            # Specific events requested
            has_any_context = True
            events = []
            for event_id in event_ids:
                event = self.dm.get_event(event_id)
                if event:
                    events.append(event)
        elif tickers:
            has_any_context = True
            # Specific tickers requested - limit to MAX_TICKERS and use batch query
            limited_tickers = tickers[:MAX_TICKERS]
            events = self.dm.get_events(
                ticker=limited_tickers,  # BATCH QUERY: Single DB call for all tickers
                start_date=start_date,  # Include past 30 days
                end_date=end_date
            )
        elif portfolio_focus:
            # THREAD SAFETY FIX: Use portfolio_summary parameter instead of instance variable
            # This prevents data leakage between concurrent user requests
            if portfolio_summary and portfolio_summary.get("exists"):
                has_any_context = True  # User HAS a portfolio
                # CRITICAL FIX: Sort by position value, then limit to top 25 tickers
                # This ensures we analyze the highest-value holdings first
                holdings = portfolio_summary.get("holdings", [])
                sorted_holdings = sorted(holdings, key=lambda h: h.get("position_value", 0), reverse=True)
                portfolio_tickers = [h["ticker"] for h in sorted_holdings][:MAX_TICKERS]
                
                if portfolio_tickers:
                    # BATCH QUERY: Single DB call instead of 25 sequential calls
                    events = self.dm.get_events(
                        ticker=portfolio_tickers,
                        start_date=start_date,  # Include past 30 days
                        end_date=end_date
                    )
                else:
                    # Empty portfolio (no holdings) - this is a valid empty result
                    events = []
            else:
                # No portfolio at all - no context yet
                events = []
        else:
            # Watchlist events - limit to top 25 tickers and use batch query
            # Being in this branch means we're in "watchlist context" 
            # even if the watchlist is currently empty
            has_any_context = True
            
            watchlist = self.dm.get_watchlist(user_id=user_id)
            watchlist_tickers = [item["ticker"] for item in watchlist][:MAX_TICKERS]
            
            if watchlist_tickers:
                # BATCH QUERY: Single DB call instead of 25 sequential calls
                events = self.dm.get_events(
                    ticker=watchlist_tickers,
                    start_date=start_date,  # Include past 30 days
                    end_date=end_date
                )
            else:
                # Empty watchlist - return empty result (valid, don't fallback)
                events = []
        
        # FINAL FALLBACK: Only apply when user has ABSOLUTELY ZERO context
        # This prevents overwriting valid "no results" from portfolio/watchlist queries
        # but ensures new users with no data see something useful
        if not events and not has_any_context:
            # User has no portfolio, no watchlist, no tickers, no event_ids
            # In this case only, show general high-impact events as a starting point
            events = self.dm.get_events(
                start_date=start_date,  # Include past 30 days
                end_date=end_date,
                limit=max_events,
                min_impact=60
            )
        
        # OPTIMIZATION: Sort by impact score and limit to max_events
        # This prevents processing hundreds of events
        events = sorted(events, key=lambda e: e.get("impact_score", 0), reverse=True)[:max_events]
        
        # Enrich events with score factors (SKIP stats for speed)
        enriched_events = []
        for event in events:
            enriched = {
                "id": event["id"],
                "ticker": event["ticker"],
                "company_name": event["company_name"],
                "event_type": event["event_type"],
                "title": event["title"],
                "date": event["date"],
                "impact_score": event.get("impact_score", 50),
                "direction": event.get("direction", "uncertain"),
                "confidence": event.get("confidence", 0.5),
                "rationale": event.get("rationale", ""),
                "sector": event.get("sector"),
                "info_tier": event.get("info_tier", "primary"),
                "info_subtype": event.get("info_subtype"),
                "source_url": event.get("source_url")
            }
            
            # Add score factors if available
            if event.get("score"):
                score_data = event["score"]
                enriched["score_factors"] = {
                    "sector_factor": score_data.get("sector_factor", 0),
                    "volatility_factor": score_data.get("volatility_factor", 0),
                    "earnings_proximity_factor": score_data.get("earnings_proximity_factor", 0),
                    "market_mood_factor": score_data.get("market_mood_factor", 0),
                    "after_hours_factor": score_data.get("after_hours_factor", 0),
                    "duplicate_penalty": score_data.get("duplicate_penalty", 0)
                }
            
            # OPTIMIZATION: Skip historical stats lookups for speed
            # The impact score and rationale already provide good context
            enriched["historical_stats"] = None
            
            # ORIGINAL CODE (too slow - one DB query per event):
            # stats = self.dm.get_event_stats(event["ticker"], event["event_type"])
            # if stats:
            #     enriched["historical_stats"] = {
            #         "sample_size": stats.sample_size,
            #         "avg_move_1d": float(stats.avg_move_1d) if stats.avg_move_1d else None,
            #         "avg_move_5d": float(stats.avg_move_5d) if stats.avg_move_5d else None,
            #         "avg_move_20d": float(stats.avg_move_20d) if stats.avg_move_20d else None,
            #         "confidence": float(stats.confidence) if stats.confidence else None,
            #         "last_updated": stats.last_updated.isoformat() if stats.last_updated else None
            #     }
            
            enriched_events.append(enriched)
        
        # Sort by date (soonest first) and impact score (highest first)
        enriched_events.sort(key=lambda e: (e["date"], -e["impact_score"]))
        
        return enriched_events
    
    def _build_historical_patterns(self, tickers: List[str]) -> Dict[str, Any]:
        """Build historical pattern summary for tickers."""
        patterns = {}
        
        for ticker in tickers:
            stats = self.dm.get_ticker_all_event_stats(ticker)
            if stats:
                patterns[ticker] = []
                for stat in stats:
                    patterns[ticker].append({
                        "event_type": stat.event_type,
                        "sample_size": stat.sample_size,
                        "avg_move_1d": float(stat.avg_move_1d) if stat.avg_move_1d else None,
                        "avg_move_5d": float(stat.avg_move_5d) if stat.avg_move_5d else None,
                        "avg_move_20d": float(stat.avg_move_20d) if stat.avg_move_20d else None,
                        "confidence": float(stat.confidence) if stat.confidence else None
                    })
        
        return patterns
    
    def _build_context_risk(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build context risk summary (for future use)."""
        # Placeholder for Wave J context risk features
        primary_events = [e for e in events if e.get("info_tier") == "primary"]
        secondary_events = [e for e in events if e.get("info_tier") == "secondary"]
        
        return {
            "total_events": len(events),
            "primary_events": len(primary_events),
            "secondary_events": len(secondary_events),
            "avg_impact_score": sum(e["impact_score"] for e in events) / len(events) if events else 0
        }
    
    def _get_relevant_tickers(self, user_id: int, portfolio_focus: bool) -> List[str]:
        """Get relevant tickers based on focus."""
        if portfolio_focus:
            portfolio_summary = self._build_portfolio_summary(user_id)
            if portfolio_summary.get("exists"):
                return portfolio_summary["tickers"]
        
        watchlist = self.dm.get_watchlist(user_id=user_id)
        return [item["ticker"] for item in watchlist]
    
    def ask(
        self,
        question: str,
        user_id: int,
        tickers: Optional[List[str]] = None,
        event_ids: Optional[List[int]] = None,
        portfolio_focus: bool = True,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        enable_web_search: bool = True
    ) -> Dict[str, Any]:
        """
        Ask RadarQuant a question and get AI-powered response.
        
        Args:
            question: User's natural language question
            user_id: User ID
            tickers: Optional list of tickers to focus on
            event_ids: Optional specific event IDs
            portfolio_focus: Whether to include portfolio analysis
            conversation_history: Previous conversation turns
            enable_web_search: Whether to search the web for current info
            
        Returns:
            Dict with 'answer', 'context_used', and metadata
        """
        # 1. Build context
        context = self.build_context(
            user_id=user_id,
            tickers=tickers,
            event_ids=event_ids,
            portfolio_focus=portfolio_focus
        )
        
        # 2. Search web if question warrants it
        web_search_results = None
        web_search_used = False
        if enable_web_search and self._should_search_web(question):
            relevant_tickers = tickers or (
                context.portfolio_summary.get("tickers", [])[:3] 
                if context.portfolio_summary and context.portfolio_summary.get("exists") 
                else []
            )
            web_search_results = self._search_web(question, relevant_tickers)
            web_search_used = web_search_results is not None
        
        # 3. Build user prompt with context and web results
        user_prompt = self._build_user_prompt(question, context, web_search_results)
        
        # 4. Call OpenAI
        messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]
        
        if conversation_history:
            messages.extend(conversation_history)
        
        messages.append({"role": "user", "content": user_prompt})
        
        response = self._call_openai(messages)
        
        # 5. Return structured response
        return {
            "answer": response,
            "context_used": {
                "portfolio": context.portfolio_summary is not None and context.portfolio_summary.get("exists", False),
                "watchlist": context.watchlist_summary["total_tickers"] > 0 if context.watchlist_summary else False,
                "upcoming_events": len(context.upcoming_events) if context.upcoming_events else 0,
                "tickers_analyzed": tickers or self._get_relevant_tickers(user_id, portfolio_focus),
                "historical_patterns_available": len(context.historical_patterns) if context.historical_patterns else 0,
                "web_search": web_search_used
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _build_user_prompt(self, question: str, context: RadarQuantContext, web_search_results: Optional[str] = None) -> str:
        """Build user prompt with question, context data, and optional web search results."""
        db = get_db()
        try:
            latest_event = db.query(Event).order_by(Event.date.desc()).first()
            latest_event_date = latest_event.date.strftime("%Y-%m-%d") if latest_event else "unknown"
        except:
            latest_event_date = "unknown"
        finally:
            close_db_session(db)
        
        current_date = datetime.utcnow().strftime("%Y-%m-%d")
        
        context_json = {
            "data_freshness": {
                "current_date": current_date,
                "latest_event_date": latest_event_date
            },
            "portfolio": context.portfolio_summary,
            "watchlist": context.watchlist_summary,
            "upcoming_events": context.upcoming_events,
            "historical_patterns": context.historical_patterns,
            "context_risk": context.context_risk
        }
        
        prompt = f"""Question: {question}

YOUR DATA ACCESS:
{json.dumps(context_json, indent=2, default=str)}"""
        
        if web_search_results:
            prompt += f"""

CURRENT NEWS & MARKET INFO (from web search):
{web_search_results}"""
        
        prompt += """

Remember: Be conversational and helpful. Reference their actual portfolio when analyzing. Mention when projections are hypothetical naturally, not with formal disclaimers."""
        
        return prompt
    
    def _call_openai(self, messages: List[Dict[str, str]]) -> str:
        """
        Call OpenAI Responses API with GPT-5.1.
        
        Args:
            messages: List of message dicts with role and content
            
        Returns:
            AI response text
        """
        url = "https://api.openai.com/v1/responses"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Convert messages to Responses API format
        # System message becomes instructions, user/assistant messages become input
        system_content = ""
        conversation_input = ""
        
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            elif msg["role"] == "user":
                conversation_input += f"\n\nUser: {msg['content']}"
            elif msg["role"] == "assistant":
                conversation_input += f"\n\nAssistant: {msg['content']}"
        
        payload = {
            "model": "gpt-5.1",
            "instructions": system_content,
            "input": conversation_input.strip(),
            "reasoning": {"effort": "medium"},
            "text": {"format": {"type": "text"}}
        }
        
        try:
            if httpx:
                with httpx.Client(timeout=45.0) as client:
                    response = client.post(url, headers=headers, json=payload)
                    response.raise_for_status()
                    data = response.json()
            else:
                import requests
                response = requests.post(url, headers=headers, json=payload, timeout=45)
                response.raise_for_status()
                data = response.json()
            
            # Extract text from Responses API format
            if "output" in data:
                for item in data["output"]:
                    if item.get("type") == "message":
                        content = item.get("content", [])
                        for c in content:
                            if c.get("type") == "output_text":
                                return c.get("text", "")
            
            # Fallback to output_text if present
            if "output_text" in data:
                return data["output_text"]
            
            return "I apologize, but I couldn't generate a response. Please try again."
            
        except Exception as e:
            print(f"OpenAI API error: {str(e)}")
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                print(f"Response body: {e.response.text}")
            raise Exception(f"OpenAI API error: {str(e)}")
