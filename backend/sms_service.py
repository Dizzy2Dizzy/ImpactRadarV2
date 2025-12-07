"""
SMS service for sending verification codes and alerts using Twilio.

Uses the Replit Twilio integration for SMS delivery.
"""

import os
import httpx
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


async def _get_twilio_credentials():
    """Get Twilio credentials from Replit connector."""
    hostname = os.environ.get("REPLIT_CONNECTORS_HOSTNAME")
    repl_identity = os.environ.get("REPL_IDENTITY")
    web_repl_renewal = os.environ.get("WEB_REPL_RENEWAL")
    
    if repl_identity:
        x_replit_token = f"repl {repl_identity}"
    elif web_repl_renewal:
        x_replit_token = f"depl {web_repl_renewal}"
    else:
        logger.error("No Replit identity token found")
        return None
    
    if not hostname:
        logger.error("REPLIT_CONNECTORS_HOSTNAME not found")
        return None
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"https://{hostname}/api/v2/connection",
                params={
                    "include_secrets": "true",
                    "connector_names": "twilio"
                },
                headers={
                    "Accept": "application/json",
                    "X_REPLIT_TOKEN": x_replit_token
                }
            )
            response.raise_for_status()
            data = response.json()
            
            items = data.get("items", [])
            if not items:
                logger.warning("No Twilio connection found - SMS not available")
                return None
            
            connection_settings = items[0]
            settings = connection_settings.get("settings", {})
            
            account_sid = settings.get("account_sid")
            api_key = settings.get("api_key")
            api_key_secret = settings.get("api_key_secret")
            phone_number = settings.get("phone_number")
            
            if not all([account_sid, api_key, api_key_secret]):
                logger.warning("Twilio credentials incomplete in connection settings")
                return None
            
            return {
                "account_sid": account_sid,
                "api_key": api_key,
                "api_key_secret": api_key_secret,
                "phone_number": phone_number
            }
            
    except Exception as e:
        logger.warning(f"Failed to get Twilio credentials: {e}")
        return None


def _get_twilio_credentials_sync():
    """Get Twilio credentials synchronously."""
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, _get_twilio_credentials())
            return future.result(timeout=15)
    except RuntimeError:
        return asyncio.run(_get_twilio_credentials())


class SMSService:
    """Handle SMS sending for verification codes and alerts using Twilio."""
    
    def __init__(self):
        """Initialize SMS service."""
        self._credentials = None
        self._initialized = False
        self._twilio_client = None
    
    def _ensure_initialized(self) -> bool:
        """Ensure we have Twilio credentials."""
        if self._initialized:
            return bool(self._twilio_client)
        
        self._credentials = _get_twilio_credentials_sync()
        self._initialized = True
        
        if not self._credentials:
            logger.warning("Twilio not configured. SMS will fail.")
            return False
        
        try:
            from twilio.rest import Client
            self._twilio_client = Client(
                self._credentials["api_key"],
                self._credentials["api_key_secret"],
                account_sid=self._credentials["account_sid"]
            )
            return True
        except ImportError:
            logger.error("Twilio library not installed")
            return False
        except Exception as e:
            logger.error(f"Error initializing Twilio client: {e}")
            return False
    
    @property
    def phone_number(self) -> Optional[str]:
        """Get the configured phone number."""
        if self._credentials:
            return self._credentials.get("phone_number")
        return None
    
    @staticmethod
    def send_verification_code(to_phone: str, code: str) -> Dict[str, Any]:
        """Send a verification code via SMS using Twilio."""
        service = SMSService()
        
        if not service._ensure_initialized():
            return {
                "success": False,
                "error": "SMS service not configured. Please set up Twilio integration."
            }
        
        if not service.phone_number:
            return {
                "success": False,
                "error": "No sending phone number configured in Twilio."
            }
        
        try:
            message = service._twilio_client.messages.create(
                body=f"Your Impact Radar verification code is: {code}. This code expires in 10 minutes.",
                from_=service.phone_number,
                to=to_phone
            )
            
            logger.info(f"Verification SMS sent to {to_phone}: {message.sid}")
            return {"success": True, "message_sid": message.sid}
            
        except Exception as e:
            logger.error(f"Error sending verification SMS: {e}")
            return {"success": False, "error": str(e)}
    
    def send_alert_sms(
        self,
        to_phone: str,
        ticker: str,
        event_type: str,
        headline: str,
        score: int,
        confidence: int
    ) -> Dict[str, Any]:
        """
        Send an alert notification via SMS.
        
        Args:
            to_phone: Phone number in E.164 format (e.g., +14155551234)
            ticker: Stock ticker symbol
            event_type: Type of event
            headline: Event headline
            score: Impact score (0-100)
            confidence: Confidence percentage (0-100)
            
        Returns:
            Dict with 'success' (bool) and optional 'message_sid' or 'error'
        """
        if not self._ensure_initialized():
            logger.warning(f"Twilio not configured, skipping SMS to {to_phone}")
            return {
                "success": False,
                "error": "SMS service not configured. Please set up Twilio integration."
            }
        
        if not self.phone_number:
            return {
                "success": False,
                "error": "No sending phone number configured in Twilio."
            }
        
        try:
            event_type_formatted = event_type.replace('_', ' ').title()
            message_body = (
                f"Impact Radar Alert\n"
                f"{ticker}: {event_type_formatted}\n"
                f"{headline[:80]}{'...' if len(headline) > 80 else ''}\n"
                f"Score: {score}, Confidence: {confidence}%"
            )
            
            message = self._twilio_client.messages.create(
                body=message_body,
                from_=self.phone_number,
                to=to_phone
            )
            
            logger.info(f"Alert SMS sent to {to_phone} for {ticker}: {message.sid}")
            return {"success": True, "message_sid": message.sid}
            
        except Exception as e:
            logger.error(f"Error sending alert SMS to {to_phone}: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def check_sms_rate_limit(user_id: int, db: Session, limit: int = 10) -> tuple:
        """
        Check if user has exceeded SMS rate limit.
        
        Args:
            user_id: User ID to check
            db: Database session
            limit: Maximum SMS messages per 24 hours (default: 10)
            
        Returns:
            Tuple of (can_send: bool, remaining_quota: int)
        """
        try:
            from releaseradar.db.models import Alert, AlertLog
            
            user_alert_ids = db.query(Alert.id).filter(Alert.user_id == user_id).all()
            user_alert_ids = [a[0] for a in user_alert_ids]
            
            if not user_alert_ids:
                return True, limit
            
            twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
            
            sms_count = db.query(AlertLog).filter(
                AlertLog.alert_id.in_(user_alert_ids),
                AlertLog.channel == "sms",
                AlertLog.sent_at >= twenty_four_hours_ago,
                AlertLog.status == "sent"
            ).count()
            
            remaining = max(0, limit - sms_count)
            can_send = sms_count < limit
            
            if not can_send:
                logger.warning(
                    f"SMS rate limit exceeded for user {user_id}: "
                    f"{sms_count} messages in last 24 hours"
                )
            
            return can_send, remaining
            
        except Exception as e:
            logger.error(f"Error checking SMS rate limit: {e}")
            return True, limit


def get_sms_service() -> SMSService:
    """Get SMS service instance."""
    return SMSService()
