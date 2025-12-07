import { useEffect, useRef, useCallback, useState } from 'react';
import { useLiveEventsStore } from '../stores/liveEventsStore';
import { getServerFeatureFlags, FeatureFlags } from '../lib/featureFlags';

const WS_URL = process.env.NEXT_PUBLIC_API_URL?.replace(/^http/, 'ws')?.replace(/:\d+$/, ':8080') || 'ws://localhost:8080';

interface EventNewMessage {
  type: 'event.new';
  event: {
    id: number;
    ticker: string;
    headline: string;
    event_type: string;
    published_at: string;
    source_url: string | null;
    impact_score: number;
    direction: string | null;
    confidence: number;
  };
}

interface EventScoredMessage {
  type: 'event.scored';
  event_id: number;
  score: number;
  confidence: number;
  direction?: string;
  computed_at?: string;
}

interface HeartbeatMessage {
  type: 'heartbeat';
  ts: string;
}

type WebSocketMessage = EventNewMessage | EventScoredMessage | HeartbeatMessage;

export function useLiveEvents(token: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const bufferRef = useRef('');
  const [featureFlags, setFeatureFlags] = useState<FeatureFlags | null>(null);
  
  const { addEvent, updateEventScore, setLastHeartbeat, setConnectionState } = useLiveEventsStore();
  
  useEffect(() => {
    getServerFeatureFlags().then(setFeatureFlags);
  }, []);
  
  const getReconnectDelay = useCallback(() => {
    const delays = [1000, 2000, 4000, 8000, 30000];
    const index = Math.min(reconnectAttemptsRef.current, delays.length - 1);
    return delays[index];
  }, []);
  
  const handleMessage = useCallback((data: string) => {
    bufferRef.current += data;
    
    const lines = bufferRef.current.split('\n');
    bufferRef.current = lines.pop() || '';
    
    for (const line of lines) {
      if (!line.trim()) continue;
      
      try {
        const message: WebSocketMessage = JSON.parse(line);
        
        switch (message.type) {
          case 'event.new':
            addEvent(message.event);
            break;
          
          case 'event.scored':
            updateEventScore(message.event_id, {
              score: message.score,
              confidence: message.confidence,
              direction: message.direction,
              computed_at: message.computed_at,
            });
            break;
          
          case 'heartbeat':
            setLastHeartbeat(message.ts);
            break;
          
          default:
            console.warn('Unknown WebSocket message type:', message);
        }
      } catch (error) {
        console.error('Failed to parse WebSocket message:', line, error);
      }
    }
  }, [addEvent, updateEventScore, setLastHeartbeat]);
  
  const connect = useCallback(() => {
    if (!featureFlags?.enableLiveWs) {
      console.log('Live WebSocket feature is disabled, skipping connection');
      setConnectionState('disabled');
      return;
    }
    
    if (!token) {
      console.log('No token available, skipping WebSocket connection');
      return;
    }
    
    if (wsRef.current?.readyState === WebSocket.OPEN || wsRef.current?.readyState === WebSocket.CONNECTING) {
      return;
    }
    
    setConnectionState('connecting');
    bufferRef.current = '';
    
    try {
      const ws = new WebSocket(`${WS_URL}/ws/events?token=${encodeURIComponent(token)}`);
      wsRef.current = ws;
      
      ws.onopen = () => {
        console.log('WebSocket connected');
        setConnectionState('connected');
        reconnectAttemptsRef.current = 0;
      };
      
      ws.onmessage = (event) => {
        handleMessage(event.data);
      };
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionState('error');
      };
      
      ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        setConnectionState('disconnected');
        wsRef.current = null;
        
        if (event.code !== 1000 && event.code !== 1008) {
          const delay = getReconnectDelay();
          console.log(`Reconnecting in ${delay}ms...`);
          reconnectAttemptsRef.current++;
          reconnectTimeoutRef.current = setTimeout(connect, delay);
        } else {
          reconnectAttemptsRef.current = 0;
        }
      };
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      setConnectionState('error');
      
      const delay = getReconnectDelay();
      reconnectAttemptsRef.current++;
      reconnectTimeoutRef.current = setTimeout(connect, delay);
    }
  }, [token, featureFlags, handleMessage, getReconnectDelay, setConnectionState]);
  
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (wsRef.current) {
      wsRef.current.close(1000, 'User disconnected');
      wsRef.current = null;
    }
    
    reconnectAttemptsRef.current = 0;
    setConnectionState('disconnected');
  }, [setConnectionState]);
  
  useEffect(() => {
    connect();
    
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);
  
  return {
    connect,
    disconnect,
  };
}
