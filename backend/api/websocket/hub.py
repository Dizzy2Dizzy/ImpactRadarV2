"""
WebSocket Hub for realtime event delivery.

Manages WebSocket connections with JWT auth, message buffering,
backpressure handling, and heartbeat pings.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Set, Optional, Any
from collections import defaultdict

from fastapi import WebSocket
from jose import JWTError

from api.utils.auth import decode_access_token
from api.utils.metrics import increment_counter, increment_metric

logger = logging.getLogger(__name__)


class ConnectionInfo:
    """Track individual WebSocket connection state."""
    
    def __init__(self, websocket: WebSocket, user_id: int, email: str):
        self.websocket = websocket
        self.user_id = user_id
        self.email = email
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=500)
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.send_task: Optional[asyncio.Task] = None
        self.connected_at = datetime.utcnow()
        
    async def cancel_tasks(self):
        """Cancel background tasks for this connection."""
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
        
        if self.send_task:
            self.send_task.cancel()
            try:
                await self.send_task
            except asyncio.CancelledError:
                pass


class WebSocketHub:
    """
    Central hub for managing WebSocket connections.
    
    Features:
    - JWT authentication
    - Per-user connection limits (max 5)
    - Message buffering with backpressure (drop oldest when >500)
    - Heartbeat every 15s
    - Prometheus metrics
    """
    
    # Class-level configuration
    MAX_CONNECTIONS_PER_USER = 5
    HEARTBEAT_INTERVAL = 15  # seconds
    MESSAGE_BUFFER_SIZE = 500
    
    def __init__(self):
        self._connections: Dict[str, ConnectionInfo] = {}  # connection_id -> ConnectionInfo
        self._user_connections: Dict[int, Set[str]] = defaultdict(set)  # user_id -> Set[connection_id]
        self._lock = asyncio.Lock()
        self._connection_counter = 0
        logger.info("WebSocketHub initialized")
    
    async def connect(self, websocket: WebSocket, token: str) -> Optional[str]:
        """
        Accept a new WebSocket connection with JWT auth.
        
        Args:
            websocket: WebSocket connection
            token: JWT access token
            
        Returns:
            connection_id if successful, None if rejected
        """
        try:
            # Decode JWT token
            try:
                token_data = decode_access_token(token)
            except JWTError:
                logger.warning("WebSocket connection rejected: invalid JWT")
                await websocket.close(code=1008, reason="Invalid authentication token")
                return None
            
            user_id = token_data.user_id
            email = token_data.email
            
            if not user_id:
                logger.warning("WebSocket connection rejected: no user_id in token")
                await websocket.close(code=1008, reason="Invalid token: missing user_id")
                return None
            
            async with self._lock:
                # Check concurrent connection limit
                if len(self._user_connections[user_id]) >= self.MAX_CONNECTIONS_PER_USER:
                    logger.warning(f"User {user_id} exceeded max connections ({self.MAX_CONNECTIONS_PER_USER})")
                    await websocket.close(code=1008, reason=f"Max {self.MAX_CONNECTIONS_PER_USER} connections per user")
                    return None
                
                # Create connection ID
                self._connection_counter += 1
                connection_id = f"ws_{user_id}_{self._connection_counter}"
                
                # Accept WebSocket connection
                await websocket.accept()
                
                # Create connection info
                conn_info = ConnectionInfo(websocket, user_id, email)
                self._connections[connection_id] = conn_info
                self._user_connections[user_id].add(connection_id)
                
                # Start background tasks
                conn_info.heartbeat_task = asyncio.create_task(
                    self._heartbeat_loop(connection_id)
                )
                conn_info.send_task = asyncio.create_task(
                    self._send_loop(connection_id)
                )
                
                # Update metrics
                increment_metric("ws_connections", 1)
                
                logger.info(f"WebSocket connected: {connection_id} (user={user_id}, email={email})")
                
                return connection_id
                
        except Exception as e:
            logger.error(f"Error accepting WebSocket connection: {e}", exc_info=True)
            try:
                await websocket.close(code=1011, reason="Internal server error")
            except Exception:
                pass
            return None
    
    async def disconnect(self, connection_id: str):
        """
        Disconnect a WebSocket connection and cleanup resources.
        
        Args:
            connection_id: Connection identifier
        """
        async with self._lock:
            conn_info = self._connections.get(connection_id)
            if not conn_info:
                return
            
            # Cancel background tasks
            await conn_info.cancel_tasks()
            
            # Remove from tracking
            user_id = conn_info.user_id
            self._user_connections[user_id].discard(connection_id)
            if not self._user_connections[user_id]:
                del self._user_connections[user_id]
            
            del self._connections[connection_id]
            
            # Update metrics
            increment_metric("ws_connections", -1)
            increment_metric("ws_disconnects_total", 1)
            
            logger.info(f"WebSocket disconnected: {connection_id} (user={user_id})")
    
    async def broadcast_event_new(self, event: Dict[str, Any]):
        """
        Broadcast new event to all connected clients.
        
        Args:
            event: Event dictionary with id, ticker, headline, event_type, etc.
        """
        message = {
            "type": "event.new",
            "event": {
                "id": event.get("id"),
                "ticker": event.get("ticker"),
                "headline": event.get("title"),
                "event_type": event.get("event_type"),
                "published_at": event.get("date").isoformat() if event.get("date") else None,
                "source_url": event.get("source_url"),
                "impact_score": event.get("impact_score", 50),
                "direction": event.get("direction"),
                "confidence": event.get("confidence", 0.5),
            }
        }
        
        await self._broadcast(message, message_type="event.new")
    
    async def broadcast_event_scored(self, event_id: int, score_data: Dict[str, Any]):
        """
        Broadcast score update for an event to all connected clients.
        
        Args:
            event_id: Event ID
            score_data: Score dictionary with final_score, confidence, computed_at
        """
        message = {
            "type": "event.scored",
            "event_id": event_id,
            "score": score_data.get("final_score"),
            "confidence": score_data.get("confidence"),
            "direction": score_data.get("direction"),
            "computed_at": score_data.get("computed_at").isoformat() if score_data.get("computed_at") else None,
        }
        
        await self._broadcast(message, message_type="event.scored")
    
    async def _broadcast(self, message: Dict[str, Any], message_type: str):
        """
        Internal broadcast method that enqueues message to all connections.
        
        Args:
            message: Message dictionary
            message_type: Message type for metrics
        """
        json_message = json.dumps(message) + "\n"
        
        async with self._lock:
            connection_ids = list(self._connections.keys())
        
        queued_count = 0
        dropped_count = 0
        
        for conn_id in connection_ids:
            conn_info = self._connections.get(conn_id)
            if not conn_info:
                continue
            
            try:
                # Try to enqueue without blocking
                conn_info.queue.put_nowait(json_message)
                queued_count += 1
            except asyncio.QueueFull:
                # Backpressure: drop oldest message
                try:
                    conn_info.queue.get_nowait()
                    conn_info.queue.put_nowait(json_message)
                    dropped_count += 1
                except Exception:
                    pass
        
        # Update metrics
        if queued_count > 0:
            increment_counter("ws_messages_sent_total", labels={"type": message_type}, value=queued_count)
        
        if dropped_count > 0:
            logger.warning(f"Dropped {dropped_count} messages due to backpressure (type={message_type})")
    
    async def _heartbeat_loop(self, connection_id: str):
        """
        Send heartbeat messages every 15 seconds.
        
        Args:
            connection_id: Connection identifier
        """
        try:
            while True:
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)
                
                conn_info = self._connections.get(connection_id)
                if not conn_info:
                    break
                
                message = {
                    "type": "heartbeat",
                    "ts": datetime.utcnow().isoformat(),
                }
                json_message = json.dumps(message) + "\n"
                
                try:
                    conn_info.queue.put_nowait(json_message)
                    increment_counter("ws_messages_sent_total", labels={"type": "heartbeat"}, value=1)
                except asyncio.QueueFull:
                    pass  # Skip heartbeat if queue full
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in heartbeat loop for {connection_id}: {e}")
    
    async def _send_loop(self, connection_id: str):
        """
        Send queued messages to the WebSocket.
        
        Args:
            connection_id: Connection identifier
        """
        try:
            conn_info = self._connections.get(connection_id)
            if not conn_info:
                return
            
            while True:
                # Get message from queue (blocks until available)
                message = await conn_info.queue.get()
                
                try:
                    await conn_info.websocket.send_text(message)
                except Exception as e:
                    logger.warning(f"Failed to send message to {connection_id}: {e}")
                    break
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in send loop for {connection_id}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current connection statistics."""
        return {
            "total_connections": len(self._connections),
            "total_users": len(self._user_connections),
            "connections_by_user": {
                user_id: len(conn_ids)
                for user_id, conn_ids in self._user_connections.items()
            }
        }


# Global singleton instance
_hub: Optional[WebSocketHub] = None


def get_hub() -> WebSocketHub:
    """Get the global WebSocketHub instance."""
    global _hub
    if _hub is None:
        _hub = WebSocketHub()
    return _hub


def broadcast_event_new_sync(event: Dict[str, Any]):
    """
    Synchronous wrapper for broadcasting new events.
    Safe to call from sync contexts (e.g., DataManager).
    
    Args:
        event: Event dictionary
    """
    try:
        hub = get_hub()
        # Create new event loop if needed, or use existing
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, schedule the coroutine
                asyncio.create_task(hub.broadcast_event_new(event))
            else:
                # If loop is not running, run it
                loop.run_until_complete(hub.broadcast_event_new(event))
        except RuntimeError:
            # No event loop, create new one
            asyncio.run(hub.broadcast_event_new(event))
    except Exception as e:
        logger.warning(f"Failed to broadcast event.new: {e}")


def broadcast_event_scored_sync(event_id: int, score_data: Dict[str, Any]):
    """
    Synchronous wrapper for broadcasting score updates.
    Safe to call from sync contexts (e.g., scoring jobs).
    
    Args:
        event_id: Event ID
        score_data: Score dictionary
    """
    try:
        hub = get_hub()
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(hub.broadcast_event_scored(event_id, score_data))
            else:
                loop.run_until_complete(hub.broadcast_event_scored(event_id, score_data))
        except RuntimeError:
            asyncio.run(hub.broadcast_event_scored(event_id, score_data))
    except Exception as e:
        logger.warning(f"Failed to broadcast event.scored: {e}")
