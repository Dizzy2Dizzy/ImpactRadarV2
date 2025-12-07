"""
WebSocket router for realtime event delivery.

Provides GET /ws/events endpoint for live event streaming with JWT authentication.
"""

import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from fastapi.responses import JSONResponse

from api.websocket.hub import get_hub
from releaseradar.feature_flags import feature_flags

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/events")
async def websocket_events(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="JWT access token for authentication")
):
    """
    WebSocket endpoint for realtime event delivery.
    
    Authentication: Pass JWT token as query parameter ?token=xxx
    
    Message Types (JSON lines):
    - {"type":"event.new", "event":{id, ticker, headline, event_type, published_at, source_url, impact_score, direction, confidence}}
    - {"type":"event.scored", "event_id":..., "score":..., "confidence":..., "direction":..., "computed_at":...}
    - {"type":"heartbeat", "ts":...}
    
    Connection Limits:
    - Max 5 concurrent connections per user
    - Backpressure: drops oldest messages when buffer >500
    - Heartbeat every 15 seconds
    """
    # Check if WebSocket feature is enabled
    if not feature_flags.ENABLE_LIVE_WS:
        await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA, reason="Real-time WebSocket feature is disabled")
        return
    
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing authentication token")
        return
    
    hub = get_hub()
    connection_id = await hub.connect(websocket, token)
    
    if not connection_id:
        # Connection rejected (hub already closed the WebSocket)
        return
    
    try:
        # Keep connection alive and handle incoming messages (if any)
        while True:
            # We don't expect client messages, but we need to keep the connection alive
            # If client sends anything, we just ignore it
            try:
                data = await websocket.receive_text()
                # Ignore client messages for now
                logger.debug(f"Received client message on {connection_id}: {data[:100]}")
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.warning(f"Error receiving from {connection_id}: {e}")
                break
                
    except Exception as e:
        logger.error(f"WebSocket error for {connection_id}: {e}", exc_info=True)
    finally:
        await hub.disconnect(connection_id)


@router.get("/stats")
async def websocket_stats():
    """Get current WebSocket connection statistics (for monitoring/debugging)."""
    hub = get_hub()
    stats = hub.get_stats()
    return JSONResponse(content=stats)
