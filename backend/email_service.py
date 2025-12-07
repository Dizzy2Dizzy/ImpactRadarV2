"""
Email service for sending verification codes using Resend.

Uses the Replit Resend integration for transactional emails.
"""

import os
import httpx
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


async def _get_resend_credentials():
    """Get Resend API credentials from Replit connector."""
    hostname = os.environ.get("REPLIT_CONNECTORS_HOSTNAME")
    repl_identity = os.environ.get("REPL_IDENTITY")
    web_repl_renewal = os.environ.get("WEB_REPL_RENEWAL")
    
    if repl_identity:
        x_replit_token = f"repl {repl_identity}"
    elif web_repl_renewal:
        x_replit_token = f"depl {web_repl_renewal}"
    else:
        logger.error("No Replit identity token found")
        return None, None
    
    if not hostname:
        logger.error("REPLIT_CONNECTORS_HOSTNAME not found")
        return None, None
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"https://{hostname}/api/v2/connection",
                params={
                    "include_secrets": "true",
                    "connector_names": "resend"
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
                logger.error("No Resend connection found")
                return None, None
            
            connection_settings = items[0]
            settings = connection_settings.get("settings", {})
            
            api_key = settings.get("api_key")
            from_email = settings.get("from_email", "noreply@releaseradar.app")
            
            if not api_key:
                logger.error("Resend API key not found in connection settings")
                return None, None
            
            return api_key, from_email
            
    except Exception as e:
        logger.error(f"Failed to get Resend credentials: {e}")
        return None, None


def _get_resend_credentials_sync():
    """Get Resend API credentials synchronously."""
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, _get_resend_credentials())
            return future.result(timeout=15)
    except RuntimeError:
        return asyncio.run(_get_resend_credentials())


class EmailService:
    """Handle email sending for verification codes using Resend."""
    
    def __init__(self):
        """Initialize email service."""
        self._api_key = None
        self._from_email = None
        self._initialized = False
    
    def _ensure_initialized(self) -> bool:
        """Ensure we have Resend credentials."""
        if self._initialized:
            return bool(self._api_key)
        
        self._api_key, self._from_email = _get_resend_credentials_sync()
        self._initialized = True
        
        if not self._api_key:
            logger.warning("Resend not configured. Email verification will fail.")
            return False
        
        return True
    
    @staticmethod
    def send_verification_code(to_email: str, code: str) -> Dict[str, Any]:
        """Send a verification code via email using Resend."""
        service = EmailService()
        
        if not service._ensure_initialized():
            return {
                "success": False,
                "error": "Email service not configured. Please set up Resend integration."
            }
        
        try:
            import resend
            resend.api_key = service._api_key
            
            text = f"""
Impact Radar Account Verification

Your verification code is: {code}

This code will expire in 10 minutes.

If you did not request this code, please ignore this email.

---
Impact Radar - Market-moving events, tracked to the second.
            """
            
            html = f"""
<html>
  <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background-color: #f8f9fa; padding: 30px; border-radius: 10px;">
      <h2 style="color: #333; margin-bottom: 20px;">Impact Radar Account Verification</h2>
      <p style="color: #666; font-size: 16px; line-height: 1.6;">Your verification code is:</p>
      <div style="background-color: #000; color: #fff; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
        <h1 style="margin: 0; font-size: 36px; letter-spacing: 8px;">{code}</h1>
      </div>
      <p style="color: #666; font-size: 14px;">This code will expire in 10 minutes.</p>
      <p style="color: #999; font-size: 12px; margin-top: 30px;">If you did not request this code, please ignore this email.</p>
      <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
      <p style="color: #999; font-size: 12px; text-align: center;">Impact Radar - Market-moving events, tracked to the second.</p>
    </div>
  </body>
</html>
            """
            
            params = {
                "from": service._from_email,
                "to": [to_email],
                "subject": "Impact Radar - Verification Code",
                "html": html,
                "text": text
            }
            
            result = resend.Emails.send(params)
            
            if result and result.get("id"):
                logger.info(f"Verification email sent to {to_email}, id: {result.get('id')}")
                return {"success": True, "email_id": result.get("id")}
            else:
                return {"success": False, "error": "Failed to send email"}
            
        except Exception as e:
            logger.error(f"Failed to send verification email to {to_email}: {e}")
            return {"success": False, "error": str(e)}
