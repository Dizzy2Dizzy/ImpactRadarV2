"""Server-Sent Events (SSE) streaming for real-time updates"""
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
import asyncio
import json
from datetime import datetime

from releaseradar.feature_flags import feature_flags

router = APIRouter(prefix="/stream", tags=["stream"])

# Global event queue for broadcasting new discoveries
event_queue: asyncio.Queue = asyncio.Queue()


async def event_stream() -> AsyncGenerator[str, None]:
    """Generate SSE events from the event queue"""
    try:
        while True:
            # Wait for new event with timeout
            try:
                event_data = await asyncio.wait_for(event_queue.get(), timeout=30.0)
                # Format as SSE
                yield f"data: {json.dumps(event_data)}\n\n"
            except asyncio.TimeoutError:
                # Send keepalive comment every 30 seconds
                yield f": keepalive\n\n"
    except asyncio.CancelledError:
        # Client disconnected
        pass


@router.get("/discoveries")
async def stream_discoveries():
    """
    SSE endpoint for real-time event discoveries.
    Streams new events as they are discovered by scanners.
    """
    # Check if SSE streaming feature is enabled
    if not feature_flags.ENABLE_LIVE_WS:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Real-time streaming feature is disabled"
        )
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )


async def broadcast_discovery(event_data: dict):
    """
    Broadcast a new discovery to all connected SSE clients.
    Called by scanners when they find new events.
    
    Args:
        event_data: Dictionary containing event information
    """
    await event_queue.put({
        **event_data,
        "timestamp": datetime.utcnow().isoformat(),
        "type": "discovery"
    })
