"""
Webhook notification service for Team plan users.

Supports:
- Custom webhooks (POST JSON payload)
- Slack incoming webhooks
- Discord webhooks
"""

import httpx
import logging
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Timeout for webhook requests (seconds)
WEBHOOK_TIMEOUT = 10


class WebhookService:
    """Handle webhook notifications for alerts."""
    
    @staticmethod
    async def send_custom_webhook(
        webhook_url: str,
        event_data: Dict[str, Any],
        alert_name: str
    ) -> Dict[str, Any]:
        """
        Send a notification to a custom webhook URL.
        
        Args:
            webhook_url: The webhook endpoint URL
            event_data: Event data to send
            alert_name: Name of the alert that triggered
            
        Returns:
            dict with success status and any error message
        """
        if not webhook_url:
            return {"success": False, "error": "No webhook URL configured"}
        
        try:
            payload = {
                "source": "impact_radar",
                "alert_name": alert_name,
                "timestamp": datetime.utcnow().isoformat(),
                "event": {
                    "id": event_data.get("id"),
                    "ticker": event_data.get("ticker"),
                    "company_name": event_data.get("company_name"),
                    "title": event_data.get("title"),
                    "event_type": event_data.get("event_type"),
                    "impact_score": event_data.get("impact_score"),
                    "direction": event_data.get("direction"),
                    "confidence": event_data.get("confidence"),
                    "date": event_data.get("date"),
                    "source_url": event_data.get("source_url"),
                    "sector": event_data.get("sector"),
                }
            }
            
            async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT) as client:
                response = await client.post(
                    webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code >= 200 and response.status_code < 300:
                    logger.info(f"Custom webhook sent successfully to {webhook_url[:50]}...")
                    return {"success": True}
                else:
                    error_msg = f"Webhook returned status {response.status_code}"
                    logger.warning(f"Custom webhook failed: {error_msg}")
                    return {"success": False, "error": error_msg}
                    
        except httpx.TimeoutException:
            logger.error(f"Custom webhook timeout: {webhook_url[:50]}...")
            return {"success": False, "error": "Webhook request timed out"}
        except Exception as e:
            logger.error(f"Custom webhook error: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def send_slack_notification(
        webhook_url: str,
        event_data: Dict[str, Any],
        alert_name: str
    ) -> Dict[str, Any]:
        """
        Send a notification to Slack via incoming webhook.
        
        Uses Slack's Block Kit for rich formatting.
        
        Args:
            webhook_url: Slack incoming webhook URL
            event_data: Event data to send
            alert_name: Name of the alert that triggered
            
        Returns:
            dict with success status and any error message
        """
        if not webhook_url:
            return {"success": False, "error": "No Slack webhook URL configured"}
        
        try:
            # Build Slack message with Block Kit
            ticker = event_data.get("ticker", "N/A")
            title = event_data.get("title", "No title")
            impact_score = event_data.get("impact_score", 0)
            direction = event_data.get("direction", "neutral")
            company_name = event_data.get("company_name", "")
            event_type = event_data.get("event_type", "")
            source_url = event_data.get("source_url", "")
            
            # Direction emoji
            direction_emoji = {
                "positive": ":chart_with_upwards_trend:",
                "negative": ":chart_with_downwards_trend:",
                "neutral": ":left_right_arrow:"
            }.get(direction, ":grey_question:")
            
            # Impact score color indicator
            if impact_score >= 75:
                score_indicator = ":red_circle:"
            elif impact_score >= 50:
                score_indicator = ":large_orange_circle:"
            else:
                score_indicator = ":large_green_circle:"
            
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"Impact Radar Alert: {alert_name}",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Ticker:* `{ticker}`"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Company:* {company_name}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Impact Score:* {score_indicator} {impact_score}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Direction:* {direction_emoji} {direction.capitalize()}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{title}*\n_{event_type}_"
                    }
                }
            ]
            
            # Add source link if available
            if source_url:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"<{source_url}|View Source>"
                    }
                })
            
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Sent from Impact Radar at {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
                    }
                ]
            })
            
            payload = {
                "blocks": blocks,
                "text": f"Impact Radar Alert: {ticker} - {title}"  # Fallback text
            }
            
            async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT) as client:
                response = await client.post(
                    webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200 and response.text == "ok":
                    logger.info(f"Slack notification sent successfully for {ticker}")
                    return {"success": True}
                else:
                    error_msg = f"Slack returned status {response.status_code}: {response.text[:100]}"
                    logger.warning(f"Slack webhook failed: {error_msg}")
                    return {"success": False, "error": error_msg}
                    
        except httpx.TimeoutException:
            logger.error(f"Slack webhook timeout")
            return {"success": False, "error": "Slack request timed out"}
        except Exception as e:
            logger.error(f"Slack webhook error: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def send_discord_notification(
        webhook_url: str,
        event_data: Dict[str, Any],
        alert_name: str
    ) -> Dict[str, Any]:
        """
        Send a notification to Discord via webhook.
        
        Uses Discord's embed format for rich formatting.
        
        Args:
            webhook_url: Discord webhook URL
            event_data: Event data to send
            alert_name: Name of the alert that triggered
            
        Returns:
            dict with success status and any error message
        """
        if not webhook_url:
            return {"success": False, "error": "No Discord webhook URL configured"}
        
        try:
            ticker = event_data.get("ticker", "N/A")
            title = event_data.get("title", "No title")
            impact_score = event_data.get("impact_score", 0)
            direction = event_data.get("direction", "neutral")
            company_name = event_data.get("company_name", "")
            event_type = event_data.get("event_type", "")
            source_url = event_data.get("source_url", "")
            confidence = event_data.get("confidence", 0.5)
            
            # Color based on direction
            color = {
                "positive": 0x00FF00,  # Green
                "negative": 0xFF0000,  # Red
                "neutral": 0x808080    # Gray
            }.get(direction, 0x808080)
            
            # Direction indicator
            direction_indicator = {
                "positive": ":arrow_up:",
                "negative": ":arrow_down:",
                "neutral": ":left_right_arrow:"
            }.get(direction, ":grey_question:")
            
            embed = {
                "title": f":radar: Impact Radar Alert",
                "description": f"**{alert_name}** triggered",
                "color": color,
                "fields": [
                    {
                        "name": ":chart_with_upwards_trend: Ticker",
                        "value": f"`{ticker}`",
                        "inline": True
                    },
                    {
                        "name": ":office: Company",
                        "value": company_name or "N/A",
                        "inline": True
                    },
                    {
                        "name": ":dart: Impact Score",
                        "value": f"**{impact_score}**/100",
                        "inline": True
                    },
                    {
                        "name": f"{direction_indicator} Direction",
                        "value": direction.capitalize(),
                        "inline": True
                    },
                    {
                        "name": ":bar_chart: Confidence",
                        "value": f"{int(confidence * 100)}%",
                        "inline": True
                    },
                    {
                        "name": ":label: Event Type",
                        "value": event_type or "N/A",
                        "inline": True
                    },
                    {
                        "name": ":newspaper: Event",
                        "value": title[:200] + ("..." if len(title) > 200 else ""),
                        "inline": False
                    }
                ],
                "timestamp": datetime.utcnow().isoformat(),
                "footer": {
                    "text": "Impact Radar"
                }
            }
            
            # Add source link if available
            if source_url:
                embed["url"] = source_url
            
            payload = {
                "embeds": [embed],
                "username": "Impact Radar",
            }
            
            async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT) as client:
                response = await client.post(
                    webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code in (200, 204):
                    logger.info(f"Discord notification sent successfully for {ticker}")
                    return {"success": True}
                else:
                    error_msg = f"Discord returned status {response.status_code}: {response.text[:100]}"
                    logger.warning(f"Discord webhook failed: {error_msg}")
                    return {"success": False, "error": error_msg}
                    
        except httpx.TimeoutException:
            logger.error(f"Discord webhook timeout")
            return {"success": False, "error": "Discord request timed out"}
        except Exception as e:
            logger.error(f"Discord webhook error: {e}")
            return {"success": False, "error": str(e)}
