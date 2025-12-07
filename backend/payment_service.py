import stripe
import os
from typing import Optional, Dict
import streamlit as st

class PaymentService:
    def __init__(self):
        self.stripe_key = os.getenv("STRIPE_SECRET_KEY")
        if self.stripe_key:
            stripe.api_key = self.stripe_key
        
        self.pricing_plans = {
            "free": {
                "name": "Free",
                "price": 0,
                "features": [
                    "1 watchlist",
                    "Weekly digest",
                    "Basic feed"
                ]
            },
            "pro": {
                "name": "Pro",
                "price": 2900,
                "price_display": "$29/mo",
                "features": [
                    "Unlimited watchlists",
                    "Real-time alerts",
                    "Impact scoring",
                    "Sector filters"
                ]
            },
            "team": {
                "name": "Team",
                "price": 9900,
                "price_display": "$99/mo",
                "features": [
                    "Everything in Pro",
                    "Slack/Discord integration",
                    "Historical export",
                    "API access"
                ]
            }
        }
    
    def create_checkout_session(self, plan: str, success_url: str, cancel_url: str) -> Optional[str]:
        """
        Create a Stripe checkout session for a subscription plan
        Returns the checkout URL or None if Stripe is not configured
        """
        if not self.stripe_key:
            return None
        
        if plan not in self.pricing_plans or plan == "free":
            return None
        
        try:
            plan_data = self.pricing_plans[plan]
            
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': f'Impact Radar {plan_data["name"]}',
                            'description': ', '.join(plan_data['features']),
                        },
                        'unit_amount': plan_data['price'],
                        'recurring': {
                            'interval': 'month',
                        },
                    },
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url,
                cancel_url=cancel_url,
            )
            
            return session.url
        except Exception as e:
            print(f"Error creating Stripe checkout session: {e}")
            return None
    
    def create_crypto_payment(self, plan: str, wallet_address: str) -> Dict:
        """
        Placeholder for crypto payment integration
        Returns payment details for manual crypto payment
        """
        if plan not in self.pricing_plans or plan == "free":
            return {"error": "Invalid plan"}
        
        plan_data = self.pricing_plans[plan]
        
        # Placeholder crypto wallet addresses
        crypto_wallets = {
            "BTC": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
            "ETH": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
            "USDC": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
            "USDT": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
        }
        
        # Convert USD to approximate crypto amounts (these would be real-time in production)
        usd_price = plan_data['price'] / 100
        
        return {
            "plan": plan_data["name"],
            "usd_price": usd_price,
            "crypto_wallets": crypto_wallets,
            "instructions": f"Send payment to one of the addresses above. Include your email in the transaction memo.",
            "note": "Crypto payments require manual verification. You'll receive confirmation within 24 hours."
        }
    
    def get_plan_features(self, plan: str) -> list:
        """Get features for a specific plan"""
        if plan in self.pricing_plans:
            return self.pricing_plans[plan]["features"]
        return []
    
    def is_stripe_configured(self) -> bool:
        """Check if Stripe is properly configured"""
        return bool(self.stripe_key)

def get_payment_service():
    """Get singleton payment service instance"""
    if 'payment_service' not in st.session_state:
        st.session_state.payment_service = PaymentService()
    return st.session_state.payment_service
