'use client';

import { useState, useMemo } from 'react';
import { useLiveEventsStore } from '../../stores/liveEventsStore';
import { formatDistanceToNow } from 'date-fns';
import { ImpactScoreBadge } from './ImpactScoreBadge';

function getScoreColor(score: number): string {
  if (score >= 80) return 'text-[--error] bg-[--badge-negative-bg]';
  if (score >= 60) return 'text-[--warning] bg-[--warning-light]';
  if (score >= 40) return 'text-[--warning] bg-[--warning-light]';
  return 'text-[--muted] bg-[--surface-muted]';
}

function getDirectionColor(direction: string | null): string {
  if (!direction) return 'text-[--muted]';
  const dir = direction.toLowerCase();
  if (dir === 'positive') return 'text-[--success]';
  if (dir === 'negative') return 'text-[--error]';
  return 'text-[--muted]';
}

function getConnectionStatusColor(status: string): string {
  if (status === 'connected') return 'bg-[--success]';
  if (status === 'connecting') return 'bg-[--warning]';
  if (status === 'error') return 'bg-[--error]';
  return 'bg-[--neutral]';
}

export function LiveTape() {
  const { events, lastHeartbeat, isPaused, connectionState, togglePause } = useLiveEventsStore();
  const [tickerFilter, setTickerFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [minScoreFilter, setMinScoreFilter] = useState(0);
  
  const isDisconnected = connectionState === 'disconnected';
  
  const filteredEvents = useMemo(() => {
    return events.filter((event) => {
      if (tickerFilter && !event.ticker.toLowerCase().includes(tickerFilter.toLowerCase())) {
        return false;
      }
      
      if (typeFilter && event.event_type !== typeFilter) {
        return false;
      }
      
      if (event.impact_score < minScoreFilter) {
        return false;
      }
      
      return true;
    });
  }, [events, tickerFilter, typeFilter, minScoreFilter]);
  
  const eventTypes = useMemo(() => {
    const types = new Set(events.map(e => e.event_type));
    return Array.from(types).sort();
  }, [events]);
  
  const lastScanText = useMemo(() => {
    if (!lastHeartbeat) return 'Never';
    try {
      const timestamp = new Date(lastHeartbeat);
      return formatDistanceToNow(timestamp, { addSuffix: true });
    } catch {
      return 'Unknown';
    }
  }, [lastHeartbeat]);
  
  return (
    <div className="h-full flex flex-col bg-[--panel] border border-[--border] rounded-lg shadow-sm">
      <div className="px-4 py-3 border-b border-[--border]">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${getConnectionStatusColor(connectionState)}`} />
            <h3 className="font-semibold text-sm text-[--text]">Live Tape</h3>
          </div>
          <button
            onClick={togglePause}
            className={`px-2 py-1 text-xs rounded ${
              isPaused
                ? 'bg-[--badge-positive-bg] text-[--badge-positive-text] hover:opacity-80'
                : 'bg-[--surface-muted] text-[--muted] hover:bg-[--surface-hover]'
            }`}
          >
            {isPaused ? 'Resume' : 'Pause'}
          </button>
        </div>
        
        <div className="text-xs text-[--muted] mb-3">
          Last scan: {lastScanText}
        </div>
        
        <div className="space-y-2">
          <input
            type="text"
            placeholder="Filter by ticker..."
            value={tickerFilter}
            onChange={(e) => setTickerFilter(e.target.value)}
            className="w-full px-2 py-1 text-xs border border-[--input-border] rounded bg-[--input-bg] text-[--text] focus:outline-none focus:ring-1 focus:ring-[--primary]"
          />
          
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="w-full px-2 py-1 text-xs border border-[--input-border] rounded bg-[--input-bg] text-[--text] focus:outline-none focus:ring-1 focus:ring-[--primary]"
          >
            <option value="">All event types</option>
            {eventTypes.map((type) => (
              <option key={type} value={type}>
                {type.replace(/_/g, ' ')}
              </option>
            ))}
          </select>
          
          <div className="flex items-center gap-2">
            <label className="text-xs text-[--muted] whitespace-nowrap">Min score:</label>
            <input
              type="range"
              min="0"
              max="100"
              value={minScoreFilter}
              onChange={(e) => setMinScoreFilter(Number(e.target.value))}
              className="flex-1"
            />
            <span className="text-xs font-medium text-[--text] w-8">{minScoreFilter}</span>
          </div>
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto">
        {filteredEvents.length === 0 ? (
          <div className="p-4 text-center text-sm text-[--muted]">
            {events.length === 0 ? (
              <div>
                {isDisconnected ? (
                  <>
                    <p className="font-medium text-[--text]">Login required</p>
                    <p className="mt-2 text-xs text-[--muted]">
                      The Live Tape shows real-time market events as they happen. Sign in to see the feed.
                    </p>
                  </>
                ) : (
                  <>
                    <p>Waiting for events...</p>
                    <p className="mt-2 text-xs">Connection: {connectionState}</p>
                  </>
                )}
              </div>
            ) : (
              'No events match your filters'
            )}
          </div>
        ) : (
          <div className="divide-y divide-[--border-muted]">
            {filteredEvents.map((event) => {
              const timeAgo = formatDistanceToNow(new Date(event.published_at), {
                addSuffix: true,
              });
              
              return (
                <div
                  key={event.id}
                  className="p-3 hover:bg-[--surface-hover] transition-colors"
                >
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-sm text-[--text]">
                        {event.ticker}
                      </span>
                      <ImpactScoreBadge
                        baseScore={event.impact_score}
                        compact={true}
                      />
                    </div>
                    <span className="text-xs text-[--muted] whitespace-nowrap">
                      {timeAgo}
                    </span>
                  </div>
                  
                  <p className="text-xs text-[--text] line-clamp-2 mb-1">
                    {event.headline}
                  </p>
                  
                  <div className="flex items-center gap-3 text-xs">
                    <span className="text-[--muted]">
                      {event.event_type.replace(/_/g, ' ')}
                    </span>
                    {event.direction && (
                      <span className={`font-medium ${getDirectionColor(event.direction)}`}>
                        {event.direction}
                      </span>
                    )}
                    <span className="text-[--muted]">
                      {Math.round(event.confidence * 100)}% conf
                    </span>
                  </div>
                  
                  {event.source_url && (
                    <a
                      href={event.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-[--primary] hover:underline mt-1 inline-block"
                    >
                      Source
                    </a>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
      
      <div className="px-4 py-2 border-t border-[--border] bg-[--surface-muted]">
        <div className="text-xs text-[--muted]">
          {filteredEvents.length} event{filteredEvents.length !== 1 ? 's' : ''}
          {filteredEvents.length !== events.length && ` (${events.length} total)`}
        </div>
      </div>
    </div>
  );
}
