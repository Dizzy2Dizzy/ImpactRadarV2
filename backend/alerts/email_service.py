"""
Email service for sending alert notifications using Resend.

Uses the Replit Resend integration for transactional emails.
"""

import os
import httpx
import logging
from typing import Optional

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
    """Service for sending alert emails via Resend."""
    
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
            logger.warning("Resend not configured. Email alerts will fail.")
            return False
        
        return True
    
    def send_alert_email(
        self,
        to_email: str,
        event_headline: str,
        score: int,
        confidence: int,
        source_url: Optional[str] = None,
        ticker: str = "",
        event_type: str = ""
    ) -> bool:
        """
        Send an alert email for a matched event using Resend.
        
        Args:
            to_email: Recipient email address
            event_headline: Event title/headline
            score: Impact score (0-100)
            confidence: Confidence score (0-100)
            source_url: Optional link to source document
            ticker: Company ticker
            event_type: Type of event
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        if not self._ensure_initialized():
            logger.error("Cannot send email: Resend not configured")
            return False
        
        try:
            import resend
            resend.api_key = self._api_key
            
            html_body = self._create_email_html(
                event_headline=event_headline,
                score=score,
                confidence=confidence,
                source_url=source_url,
                ticker=ticker,
                event_type=event_type
            )
            
            text_body = self._create_email_text(
                event_headline=event_headline,
                score=score,
                confidence=confidence,
                source_url=source_url,
                ticker=ticker,
                event_type=event_type
            )
            
            params = {
                "from": self._from_email,
                "to": [to_email],
                "subject": f"Impact Radar Alert: {ticker} - {event_type}",
                "html": html_body,
                "text": text_body
            }
            
            result = resend.Emails.send(params)
            
            if result and result.get("id"):
                logger.info(f"Alert email sent successfully to {to_email}, id: {result.get('id')}")
                return True
            else:
                logger.error(f"Resend returned no ID for email to {to_email}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to send alert email to {to_email}: {e}")
            return False
    
    def _create_email_text(
        self,
        event_headline: str,
        score: int,
        confidence: int,
        source_url: Optional[str],
        ticker: str,
        event_type: str
    ) -> str:
        """Create plain text email body."""
        text = f"""
Impact Radar Alert

Company: {ticker}
Event Type: {event_type}
Impact Score: {score}/100
Confidence: {confidence}%

Event:
{event_headline}
"""
        
        if source_url:
            text += f"\nSource: {source_url}"
        
        text += "\n\nManage your alerts at https://releaseradar.app/dashboard/alerts"
        
        return text
    
    def _create_email_html(
        self,
        event_headline: str,
        score: int,
        confidence: int,
        source_url: Optional[str],
        ticker: str,
        event_type: str
    ) -> str:
        """Create HTML email body with professional styling."""
        if score >= 76:
            score_color = "#10b981"
        elif score >= 51:
            score_color = "#3b82f6"
        elif score >= 26:
            score_color = "#f59e0b"
        else:
            score_color = "#ef4444"
        
        source_link = ""
        if source_url:
            source_link = f'<a href="{source_url}" style="color: #3b82f6; text-decoration: none;">View Source</a>'
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f3f4f6;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background-color: #ffffff; border-radius: 8px; padding: 30px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
            <h1 style="margin: 0 0 20px 0; font-size: 24px; font-weight: 600; color: #111827;">Impact Radar Alert</h1>
            
            <div style="background-color: #f9fafb; border-left: 4px solid {score_color}; padding: 15px; margin-bottom: 20px;">
                <div style="font-size: 14px; color: #6b7280; margin-bottom: 5px;">
                    <strong>{ticker}</strong> - {event_type}
                </div>
                <div style="font-size: 18px; color: #111827; font-weight: 500; line-height: 1.5;">
                    {event_headline}
                </div>
            </div>
            
            <table style="width: 100%; margin-bottom: 20px;">
                <tr>
                    <td style="padding: 10px 0; border-bottom: 1px solid #e5e7eb;">
                        <div style="font-size: 12px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px;">Impact Score</div>
                        <div style="font-size: 24px; color: {score_color}; font-weight: 600;">{score}<span style="font-size: 14px; color: #9ca3af;">/100</span></div>
                    </td>
                    <td style="padding: 10px 0; border-bottom: 1px solid #e5e7eb;">
                        <div style="font-size: 12px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px;">Confidence</div>
                        <div style="font-size: 24px; color: #111827; font-weight: 600;">{confidence}<span style="font-size: 14px; color: #9ca3af;">%</span></div>
                    </td>
                </tr>
            </table>
            
            {source_link}
            
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; text-align: center;">
                <a href="https://releaseradar.app/dashboard/alerts" style="display: inline-block; background-color: #3b82f6; color: #ffffff; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 500;">Manage Alerts</a>
            </div>
        </div>
        
        <div style="text-align: center; margin-top: 20px; color: #6b7280; font-size: 12px;">
            Impact Radar - Event-driven signals for active traders
        </div>
    </div>
</body>
</html>
"""
        return html


_email_service = None

def get_email_service() -> EmailService:
    """Get or create the email service singleton."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
