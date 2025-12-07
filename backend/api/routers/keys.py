"""API key management endpoints"""
import hashlib
import secrets
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import SessionLocal, close_db_session
from backend.releaseradar.db.models import ApiKey, User
from backend.api.utils.auth import get_current_user

router = APIRouter(prefix="/keys", tags=["keys"])


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


def _mask_key(key_hash: str) -> str:
    """Mask key hash for display: show last 4 chars only"""
    return f"****...{key_hash[-4:]}"


@router.get("")
async def list_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all API keys for the current user with masked values.
    
    Returns:
        List of API keys with metadata (never returns raw keys)
    """
    keys = db.query(ApiKey).filter(ApiKey.user_id == current_user.user_id).all()
    
    return {
        "keys": [
            {
                "id": key.id,
                "masked_key": _mask_key(key.key_hash),
                "plan": key.plan,
                "status": key.status,
                "monthly_call_limit": key.monthly_call_limit,
                "calls_used": key.calls_used,
                "cycle_start": key.cycle_start.isoformat() if key.cycle_start else None,
                "created_at": key.created_at.isoformat() if key.created_at else None,
                "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
            }
            for key in keys
        ]
    }


@router.post("/create")
async def create_key(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create initial API key for Pro/Team users.
    
    Only works if user has no active API key. Requires Pro or Team plan.
    WARNING: The raw key is returned ONLY ONCE. Store it securely.
    
    Returns:
        New raw API key with metadata
    """
    # Check user plan (API keys only available for Pro and Team)
    if current_user.plan not in ("pro", "team"):
        raise HTTPException(
            status_code=403, 
            detail="API keys are only available for Pro and Team plans. Please upgrade your account."
        )
    
    # Check if user already has an active key
    existing_key = db.query(ApiKey).filter(
        ApiKey.user_id == current_user.user_id,
        ApiKey.status == "active"
    ).first()
    
    if existing_key:
        raise HTTPException(
            status_code=400, 
            detail="You already have an active API key. Use the rotate endpoint to get a new one."
        )
    
    # Set monthly call limit based on plan
    monthly_limit = 100_000 if current_user.plan == "team" else 10_000
    
    # Generate new key
    raw_key = f"rr_{secrets.token_urlsafe(32)}"
    key_hash = _hash_key(raw_key)
    
    new_key = ApiKey(
        user_id=current_user.user_id,
        key_hash=key_hash,
        plan=current_user.plan,
        status="active",
        monthly_call_limit=monthly_limit,
        calls_used=0,
        cycle_start=datetime.utcnow()
    )
    db.add(new_key)
    db.commit()
    db.refresh(new_key)
    
    return {
        "raw_key": raw_key,
        "warning": "This key will not be shown again. Store it securely.",
        "metadata": {
            "id": new_key.id,
            "plan": new_key.plan,
            "monthly_call_limit": new_key.monthly_call_limit,
            "created_at": new_key.created_at.isoformat() if new_key.created_at else None,
        }
    }


@router.post("/rotate")
async def rotate_key(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Rotate API key: revoke existing active key and create new one.
    
    WARNING: The raw key is returned ONLY ONCE. Store it securely.
    
    Returns:
        New raw API key with metadata
    """
    # Find active key
    active_key = db.query(ApiKey).filter(
        ApiKey.user_id == current_user.user_id,
        ApiKey.status == "active"
    ).first()
    
    if not active_key:
        raise HTTPException(status_code=404, detail="No active API key found. Use the create endpoint to generate your first key.")
    
    # Revoke existing key
    active_key.status = "revoked"
    db.commit()
    
    # Create new key with same plan and limit
    raw_key = f"rr_{secrets.token_urlsafe(32)}"
    key_hash = _hash_key(raw_key)
    
    new_key = ApiKey(
        user_id=current_user.user_id,
        key_hash=key_hash,
        plan=active_key.plan,
        status="active",
        monthly_call_limit=active_key.monthly_call_limit,
        calls_used=0,
        cycle_start=datetime.utcnow()
    )
    db.add(new_key)
    db.commit()
    db.refresh(new_key)
    
    return {
        "raw_key": raw_key,
        "warning": "This key will not be shown again. Store it securely.",
        "metadata": {
            "id": new_key.id,
            "plan": new_key.plan,
            "monthly_call_limit": new_key.monthly_call_limit,
            "created_at": new_key.created_at.isoformat() if new_key.created_at else None,
        }
    }
