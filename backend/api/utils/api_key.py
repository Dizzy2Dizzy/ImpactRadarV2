"""API key authentication and validation utilities"""
import hashlib
from datetime import datetime, timedelta
from fastapi import Header, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import update
from backend.database import SessionLocal, close_db_session
from backend.releaseradar.db.models import ApiKey


RESET_DAYS = 30


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        close_db_session(db)


def _hash_key(key: str) -> str:
    """Hash API key using SHA-256"""
    return hashlib.sha256(key.encode()).hexdigest()


PLAN_ORDER = {"pro": 1, "team": 2}


def _reset_cycle_if_needed(db: Session, rec: ApiKey) -> None:
    """Reset monthly cycle if 30+ days have passed since cycle_start"""
    if rec.cycle_start is None or (datetime.utcnow() - rec.cycle_start) >= timedelta(days=RESET_DAYS):
        rec.calls_used = 0
        rec.cycle_start = datetime.utcnow()
        db.commit()


def _consume_one_token(db: Session, key_hash: str, monthly_limit: int) -> bool:
    """
    Atomically increment calls_used if below limit.
    
    Returns:
        bool: True if token consumed successfully, False if limit reached
    """
    result = db.execute(
        update(ApiKey)
        .where(
            ApiKey.key_hash == key_hash,
            ApiKey.calls_used < ApiKey.monthly_call_limit,
            ApiKey.status == "active"
        )
        .values(
            calls_used=ApiKey.calls_used + 1,
            last_used_at=datetime.utcnow()
        )
    )
    db.commit()
    return result.rowcount == 1


def require_api_key(
    request: Request,
    x_api_key: str | None = Header(None),
    db: Session = Depends(get_db),
    min_plan: str = "pro",
):
    """
    Dependency to require and validate API key with 30-day rolling cycle reset.
    
    Args:
        request: FastAPI request object
        x_api_key: API key from header
        db: Database session
        min_plan: Minimum plan required ("pro" or "team")
    
    Raises:
        HTTPException: 401 if key missing, 403 if invalid/revoked, 402 if plan insufficient, 429 if monthly limit exceeded
    
    Returns:
        ApiKey: The validated API key record
    """
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing x-api-key header")
    
    key_hash = _hash_key(x_api_key)
    rec = db.query(ApiKey).filter(
        ApiKey.key_hash == key_hash,
        ApiKey.status == "active"
    ).first()
    
    if not rec:
        raise HTTPException(status_code=403, detail="Invalid or revoked API key")
    
    if PLAN_ORDER.get(rec.plan, 0) < PLAN_ORDER.get(min_plan, 0):
        raise HTTPException(status_code=402, detail="Upgrade required for this endpoint")
    
    # Reset cycle if 30+ days have passed
    _reset_cycle_if_needed(db, rec)
    
    # Atomically consume one token
    if not _consume_one_token(db, rec.key_hash, rec.monthly_call_limit):
        raise HTTPException(status_code=429, detail="Monthly API quota exceeded")
    
    request.state.plan = rec.plan
    request.state.api_key_hash = rec.key_hash
    
    return rec
