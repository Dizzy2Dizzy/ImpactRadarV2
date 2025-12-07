"""
AI Router for RadarQuant

Provides endpoints for AI-powered event analysis and portfolio insights.
Implements plan-based quotas and usage tracking.
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from typing import Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from ai.radarquant import RadarQuantOrchestrator
from api.utils.auth import get_current_user_id
from api.utils.metrics import increment_metric, increment_counter, observe_ai_latency
from api.utils.paywall import require_plan
from api.ratelimit import limiter
from releaseradar.db.session import get_db
from database import close_db_session
from releaseradar.db.models import User
from sqlalchemy import select
import time
import threading
from collections import defaultdict


router = APIRouter(prefix="/ai", tags=["ai"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class AnalyzeRequest(BaseModel):
    """Request for AI analysis"""
    question: str = Field(..., min_length=1, max_length=2000, description="User's question")
    tickers: Optional[List[str]] = Field(None, description="Optional list of specific tickers to analyze")
    event_ids: Optional[List[int]] = Field(None, description="Optional list of specific event IDs")
    portfolio_focus: bool = Field(True, description="Include portfolio analysis if True")
    context_mode: Optional[str] = Field(None, description="Dashboard mode: watchlist or portfolio")


class Message(BaseModel):
    """Chat message"""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., min_length=1, description="Message content")


class ChatRequest(BaseModel):
    """Request for chat conversation"""
    messages: List[Message] = Field(..., description="Conversation history")
    tickers: Optional[List[str]] = Field(None, description="Optional list of specific tickers")
    event_ids: Optional[List[int]] = Field(None, description="Optional list of specific event IDs")
    portfolio_focus: bool = Field(True, description="Include portfolio analysis")
    context_mode: Optional[str] = Field(None, description="Dashboard mode: watchlist or portfolio")


class AnalyzeResponse(BaseModel):
    """Response from AI analysis"""
    analysis: str
    context_used: dict
    metadata: dict


class QuotaStatus(BaseModel):
    """AI quota status"""
    remaining: int
    limit: int
    resets_at: str


# ============================================================================
# QUOTA MANAGEMENT
# ============================================================================

class AIQuotaManager:
    """Manages daily AI request quotas per plan"""
    
    QUOTAS = {
        "free": 3,
        "pro": 30,
        "team": 100,
        "enterprise": 1000
    }
    
    # In-memory usage tracking (day -> user_id -> count)
    # Format: {date: {user_id: count}}
    _usage_cache: dict = defaultdict(lambda: defaultdict(int))
    _lock = threading.Lock()
    
    @staticmethod
    def get_daily_limit(plan: str) -> int:
        """Get daily limit for plan"""
        return AIQuotaManager.QUOTAS.get(plan.lower(), 0)
    
    @staticmethod
    def _get_today_key() -> str:
        """Get today's date key for cache"""
        return datetime.utcnow().strftime("%Y-%m-%d")
    
    @staticmethod
    def _cleanup_old_days():
        """Remove entries from previous days to prevent memory leak"""
        today = AIQuotaManager._get_today_key()
        with AIQuotaManager._lock:
            old_keys = [k for k in AIQuotaManager._usage_cache.keys() if k != today]
            for key in old_keys:
                del AIQuotaManager._usage_cache[key]
    
    @staticmethod
    def get_usage(user_id: int) -> int:
        """Get current usage for today"""
        today = AIQuotaManager._get_today_key()
        with AIQuotaManager._lock:
            return max(0, AIQuotaManager._usage_cache[today][user_id])
    
    @staticmethod
    def check_and_increment(user_id: int, plan: str) -> int:
        """
        Atomically check quota and increment usage.
        Returns remaining requests after increment.
        Raises HTTPException if quota exceeded.
        
        Thread-safe operation prevents race conditions.
        """
        # Cleanup old days occasionally
        AIQuotaManager._cleanup_old_days()
        
        # Get daily limit
        daily_limit = AIQuotaManager.get_daily_limit(plan)
        if daily_limit == 0:
            raise HTTPException(status_code=403, detail=f"Invalid plan: {plan}")
        
        # ATOMIC: Check and increment under lock (prevents race conditions)
        today = AIQuotaManager._get_today_key()
        with AIQuotaManager._lock:
            current_usage = AIQuotaManager._usage_cache[today][user_id]
            
            if current_usage >= daily_limit:
                increment_metric("ai_requests_blocked_quota_total")
                raise HTTPException(
                    status_code=429,
                    detail=f"Daily AI quota exceeded. {plan.title()} plan allows {daily_limit} requests per day. Resets at midnight UTC."
                )
            
            # Increment counter
            AIQuotaManager._usage_cache[today][user_id] += 1
            new_usage = AIQuotaManager._usage_cache[today][user_id]
            
            return daily_limit - new_usage
    
    @staticmethod
    def rollback_usage(user_id: int) -> None:
        """
        Rollback usage counter on error.
        Call this when AI request fails to ensure errors don't consume quota.
        """
        today = AIQuotaManager._get_today_key()
        with AIQuotaManager._lock:
            # Only decrement if usage is greater than 0
            if AIQuotaManager._usage_cache[today][user_id] > 0:
                AIQuotaManager._usage_cache[today][user_id] -= 1


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/analyze", response_model=AnalyzeResponse)
@limiter.limit("120/minute")
async def analyze(
    request: Request,
    request_data: AnalyzeRequest,
    user_id: int = Depends(get_current_user_id)
):
    """
    Analyze events, portfolio, or watchlist using RadarQuant AI.
    
    Free plan: 5 requests per day
    Pro plan: 30 requests per day
    Team plan: 100 requests per day
    Enterprise plan: 1000 requests per day
    
    The AI provides:
    - Event impact probability estimates based on historical stats
    - Event importance ranking for your portfolio/watchlist
    - Company catalyst assessment
    - Hypothetical P&L projections
    
    All responses are grounded in Impact Radar data and labeled as hypothetical.
    This is not financial advice.
    """
    start_time = time.time()
    
    # Get user's plan
    db = get_db()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        plan = str(user.plan) if user.plan else "free"
    finally:
        close_db_session(db)
    
    # ATOMIC: Check and increment quota (prevents race conditions)
    try:
        usage_remaining = AIQuotaManager.check_and_increment(user_id, plan)
    except HTTPException:
        raise
    
    # Track metrics
    increment_metric("ai_requests_total")
    
    try:
        # Get active tickers if context_mode is specified
        # Follow same pattern as backtesting and correlation endpoints
        tickers_filter = None
        if request_data.context_mode and request_data.context_mode in ['watchlist', 'portfolio']:
            from api.dependencies import get_data_manager
            dm = get_data_manager()
            active_tickers = dm.get_user_active_tickers(user_id, request_data.context_mode)
            # Convert empty list to None to show all results (global context)
            tickers_filter = active_tickers if active_tickers else None
        elif request_data.tickers:
            # Use explicit tickers from request if no context_mode
            tickers_filter = request_data.tickers
        
        # Initialize RadarQuant
        orchestrator = RadarQuantOrchestrator()
        
        # Get AI response
        result = orchestrator.ask(
            question=request_data.question,
            user_id=user_id,
            tickers=tickers_filter,
            event_ids=request_data.event_ids,
            portfolio_focus=request_data.portfolio_focus
        )
        
        latency = time.time() - start_time
        observe_ai_latency("analyze", latency)
        if latency > 5.0:
            increment_metric("ai_slow_requests_total", 1)
        
        return AnalyzeResponse(
            analysis=result["answer"],
            context_used=result["context_used"],
            metadata={
                "timestamp": result["timestamp"],
                "model": "gpt-5.1",
                "tokens_used": 0,
                "processing_time": latency
            }
        )
        
    except Exception as e:
        AIQuotaManager.rollback_usage(user_id)
        increment_metric("ai_requests_error_total")
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {str(e)}")


@router.post("/chat", response_model=AnalyzeResponse)
@limiter.limit("120/minute")
async def chat(
    request: Request,
    request_data: ChatRequest,
    user_id: int = Depends(get_current_user_id)
):
    """
    Multi-turn chat with RadarQuant AI.
    
    Maintains conversation history for context.
    Each message counts against daily quota.
    """
    start_time = time.time()
    
    # Get user's plan
    db = get_db()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        plan = str(user.plan) if user.plan else "free"
    finally:
        close_db_session(db)
    
    # ATOMIC: Check and increment quota (prevents race conditions)
    try:
        usage_remaining = AIQuotaManager.check_and_increment(user_id, plan)
    except HTTPException:
        raise
    
    # Track metrics
    increment_metric("ai_requests_total")
    
    try:
        # Get active tickers if context_mode is specified
        # Follow same pattern as backtesting and correlation endpoints
        tickers_filter = None
        if request_data.context_mode and request_data.context_mode in ['watchlist', 'portfolio']:
            from api.dependencies import get_data_manager
            dm = get_data_manager()
            active_tickers = dm.get_user_active_tickers(user_id, request_data.context_mode)
            # Convert empty list to None to show all results (global context)
            tickers_filter = active_tickers if active_tickers else None
        elif request_data.tickers:
            # Use explicit tickers from request if no context_mode
            tickers_filter = request_data.tickers
        
        # Find the last user message (current question or retry)
        # This supports both new questions and regenerating previous responses
        last_user_index = None
        for i in range(len(request_data.messages) - 1, -1, -1):
            if request_data.messages[i].role == "user":
                last_user_index = i
                break
        
        if last_user_index is None:
            raise HTTPException(
                status_code=400,
                detail="No user message found in conversation"
            )
        
        # Extract the question from the last user message
        last_user_message = request_data.messages[last_user_index].content
        
        # Build history from all messages BEFORE the last user message
        # This excludes both the current question AND any assistant responses after it
        # (which would be old responses we're regenerating in retry scenarios)
        history = [
            {"role": msg.role, "content": msg.content}
            for i, msg in enumerate(request_data.messages)
            if i < last_user_index
        ]
        
        # Initialize RadarQuant
        orchestrator = RadarQuantOrchestrator()
        
        # Get AI response with conversation history
        result = orchestrator.ask(
            question=last_user_message,
            user_id=user_id,
            tickers=tickers_filter,
            event_ids=request_data.event_ids,
            portfolio_focus=request_data.portfolio_focus,
            conversation_history=history if history else None
        )
        
        latency = time.time() - start_time
        observe_ai_latency("chat", latency)
        if latency > 5.0:
            increment_metric("ai_slow_requests_total", 1)
        
        return AnalyzeResponse(
            analysis=result["answer"],
            context_used=result["context_used"],
            metadata={
                "timestamp": result["timestamp"],
                "model": "gpt-5.1",
                "tokens_used": 0,
                "processing_time": latency
            }
        )
        
    except Exception as e:
        AIQuotaManager.rollback_usage(user_id)
        increment_metric("ai_requests_error_total")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.get("/quota", response_model=QuotaStatus)
async def get_quota_status(
    user_id: int = Depends(get_current_user_id)
):
    """
    Get current AI quota status for the user.
    
    Returns usage stats and remaining requests for today.
    """
    db = get_db()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        plan = str(user.plan) if user.plan else "free"
        daily_limit = AIQuotaManager.get_daily_limit(plan)
        
        # Get actual usage count
        requests_used_today = AIQuotaManager.get_usage(user_id)
        
        # Calculate next reset time (midnight UTC)
        now = datetime.utcnow()
        next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        return QuotaStatus(
            remaining=max(0, daily_limit - requests_used_today),
            limit=daily_limit,
            resets_at=next_midnight.isoformat() + "Z"
        )
        
    finally:
        close_db_session(db)
