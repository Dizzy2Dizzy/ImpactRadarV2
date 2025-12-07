"""Pricing and Stripe integration router"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import os
from typing import Optional

router = APIRouter(prefix="/pricing", tags=["pricing"])

# Stripe configuration (stub in dev, working when keys exist)
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PRICE_PRO = os.getenv("STRIPE_PRICE_PRO")
STRIPE_PRICE_TEAM = os.getenv("STRIPE_PRICE_TEAM")

# Check if Stripe is configured
STRIPE_ENABLED = bool(STRIPE_SECRET_KEY and STRIPE_PRICE_PRO and STRIPE_PRICE_TEAM)

if STRIPE_ENABLED:
    try:
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY
    except ImportError:
        STRIPE_ENABLED = False


class PricingPlan(BaseModel):
    """Pricing plan information"""
    name: str
    price_monthly: float
    price_annual: Optional[float] = None
    features: list[str]
    stripe_price_id: Optional[str] = None


class CheckoutRequest(BaseModel):
    """Checkout session request"""
    plan: str  # "pro" or "team"
    billing_period: str = "monthly"  # "monthly" or "annual"


class CheckoutResponse(BaseModel):
    """Checkout session response"""
    checkout_url: Optional[str] = None
    session_id: Optional[str] = None
    message: Optional[str] = None


@router.get("/plans", response_model=list[PricingPlan])
async def get_pricing_plans():
    """Get available pricing plans"""
    plans = [
        PricingPlan(
            name="Free",
            price_monthly=0.0,
            features=[
                "Track up to 10 companies",
                "View public events and filings",
                "Basic impact scoring",
                "Community support"
            ]
        ),
        PricingPlan(
            name="Pro",
            price_monthly=49.0,
            price_annual=490.0,
            stripe_price_id=STRIPE_PRICE_PRO if STRIPE_ENABLED else None,
            features=[
                "Track unlimited companies",
                "Real-time SSE streaming",
                "Advanced impact scoring with confidence metrics",
                "Portfolio impact analysis",
                "Email & SMS alerts",
                "Historical event archive",
                "API access",
                "Priority support"
            ]
        ),
        PricingPlan(
            name="Team",
            price_monthly=199.0,
            price_annual=1990.0,
            stripe_price_id=STRIPE_PRICE_TEAM if STRIPE_ENABLED else None,
            features=[
                "Everything in Pro",
                "Up to 10 team members",
                "Shared watchlists",
                "Custom webhooks",
                "White-label reports",
                "Dedicated account manager",
                "SLA guarantee",
                "Custom integrations"
            ]
        )
    ]
    return plans


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout_session(request: CheckoutRequest):
    """Create Stripe checkout session"""
    
    # If Stripe is not configured, return stub response
    if not STRIPE_ENABLED:
        return CheckoutResponse(
            message="Stripe integration not configured. Please add STRIPE_SECRET_KEY, STRIPE_PRICE_PRO, and STRIPE_PRICE_TEAM to environment variables."
        )
    
    try:
        # Determine price ID based on plan and billing period
        if request.plan == "pro":
            price_id = STRIPE_PRICE_PRO
        elif request.plan == "team":
            price_id = STRIPE_PRICE_TEAM
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid plan. Choose 'pro' or 'team'"
            )
        
        # Create Stripe checkout session
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=os.getenv("STRIPE_SUCCESS_URL", "http://localhost:5000/dashboard?success=true"),
            cancel_url=os.getenv("STRIPE_CANCEL_URL", "http://localhost:5000/pricing?canceled=true"),
        )
        
        return CheckoutResponse(
            checkout_url=session.url,
            session_id=session.id
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create checkout session: {str(e)}"
        )


@router.get("/config")
async def get_stripe_config():
    """Get Stripe public configuration"""
    return {
        "enabled": STRIPE_ENABLED,
        "publishable_key": os.getenv("STRIPE_PUBLISHABLE_KEY") if STRIPE_ENABLED else None
    }
