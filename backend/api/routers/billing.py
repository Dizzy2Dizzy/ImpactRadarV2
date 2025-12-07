"""Billing and subscription management router"""
import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
import stripe

from backend.database import SessionLocal, close_db_session
from backend.releaseradar.db.models import User, ApiKey
from api.utils.auth import decode_access_token

router = APIRouter(prefix="/billing", tags=["billing"])

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        close_db_session(db)


class TrialStartRequest(BaseModel):
    """Request to start a Pro trial"""
    pass


class TrialStartResponse(BaseModel):
    """Response after starting trial"""
    trial_ends_at: datetime
    plan: str
    message: str


def _hash_key(key: str) -> str:
    """Hash API key using SHA-256"""
    return hashlib.sha256(key.encode()).hexdigest()


def issue_api_key(db: Session, user: User, plan: str) -> str:
    """
    Issue a new API key for a user and plan with proper monthly limits.
    
    Args:
        db: Database session
        user: User object
        plan: Plan name ("pro" or "team")
    
    Returns:
        str: Raw API key (store this securely, it's shown only once)
    """
    raw_key = f"rk_{secrets.token_urlsafe(32)}"
    key_hash = _hash_key(raw_key)
    
    # Set monthly call limit based on plan
    monthly_limit = 100_000 if plan == "team" else 10_000
    
    api_key = ApiKey(
        user_id=user.id,
        key_hash=key_hash,
        plan=plan,
        status="active",
        monthly_call_limit=monthly_limit,
        calls_used=0
    )
    db.add(api_key)
    db.commit()
    
    return raw_key


@router.post("/start-trial", response_model=TrialStartResponse)
async def start_trial(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Start a 14-day Pro trial for the authenticated user.
    
    Creates Stripe customer if needed, sets trial_ends_at, and upgrades plan to 'pro'.
    No credit card required during trial period.
    """
    # Get user from JWT token
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    
    token = auth_header.replace("Bearer ", "")
    try:
        token_data = decode_access_token(token)
        user_id = token_data.user_id
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if user already has an active trial or paid plan
    if user.plan in ("pro", "team"):
        raise HTTPException(status_code=400, detail="User already has an active plan")
    
    if user.trial_ends_at and user.trial_ends_at > datetime.utcnow():
        raise HTTPException(status_code=400, detail="User already has an active trial")
    
    # Create Stripe customer if doesn't exist
    if not user.stripe_customer_id:
        try:
            customer = stripe.Customer.create(
                email=user.email,
                metadata={"user_id": user.id}
            )
            user.stripe_customer_id = customer.id
        except Exception as e:
            import logging
            logging.error(f"Failed to create Stripe customer: {e}")
            # Continue without Stripe - trial can still work
    
    # Set trial period (14 days)
    trial_ends_at = datetime.utcnow() + timedelta(days=14)
    user.trial_ends_at = trial_ends_at
    user.plan = "pro"
    
    db.commit()
    
    import logging
    logging.info(f"Trial started for user_id={user.id}, expires={trial_ends_at}")
    
    return TrialStartResponse(
        trial_ends_at=trial_ends_at,
        plan="pro",
        message="14-day Pro trial started successfully"
    )


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handle Stripe webhook events for subscription management.
    
    Supported events:
    - checkout.session.completed: Issue API key on new subscription
    - customer.subscription.updated: Update API key on plan change
    - customer.subscription.deleted: Revoke API key on cancellation
    - invoice.payment_failed: Revoke API key on payment failure
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    
    if not webhook_secret:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")
    
    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    event_type = event["type"]
    data = event["data"]["object"]
    
    if event_type in ("checkout.session.completed", "customer.subscription.updated"):
        # Try to find user by Stripe customer ID first (more reliable)
        customer_id = data.get("customer")
        user = None
        
        if customer_id:
            user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
        
        # Fallback to email lookup if no customer ID match
        if not user:
            customer_details = data.get("customer_details") or {}
            email = customer_details.get("email") or data.get("customer_email")
            
            if email:
                user = db.query(User).filter(User.email == email).first()
        
        if not user:
            return {"ok": True, "message": "User not found"}
        
        metadata = data.get("metadata") or {}
        plan_name = metadata.get("plan", "")
        
        plan = "team" if "team" in plan_name.lower() else "pro"
        
        # Update user plan and clear trial
        user.plan = plan
        user.trial_ends_at = None
        
        # Save Stripe customer ID if not present
        customer_id = data.get("customer")
        if customer_id and not user.stripe_customer_id:
            user.stripe_customer_id = customer_id
        
        # Revoke old API keys and issue new one
        db.query(ApiKey).filter(ApiKey.user_id == user.id).update({"status": "revoked"})
        db.commit()
        
        raw_key = issue_api_key(db, user, plan)
        
        # Note: API key generated successfully - user must retrieve from dashboard
        # DO NOT log or return the raw key for security reasons
        import logging
        logging.info(f"API key issued for user_id={user.id}, plan={plan}")
        
        return {
            "ok": True,
            "message": f"API key issued for {email}"
        }
    
    elif event_type in ("customer.subscription.deleted", "invoice.payment_failed"):
        # Try to find user by Stripe customer ID first (more reliable)
        customer_id = data.get("customer")
        user = None
        
        if customer_id:
            user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
        
        # Fallback to email lookup if no customer ID match
        if not user:
            customer_details = data.get("customer_details") or {}
            email = customer_details.get("email") or data.get("customer_email")
            
            if email:
                user = db.query(User).filter(User.email == email).first()
        
        if not user:
            return {"ok": True, "message": "User not found"}
        
        # Downgrade to free plan
        user.plan = "free"
        user.trial_ends_at = None
        
        # Revoke API keys
        db.query(ApiKey).filter(ApiKey.user_id == user.id).update({"status": "revoked"})
        db.commit()
        
        import logging
        logging.info(f"User downgraded to free plan: user_id={user.id}, event={event_type}")
        
        return {"ok": True, "message": f"API keys revoked for {email}"}
    
    return {"ok": True}
