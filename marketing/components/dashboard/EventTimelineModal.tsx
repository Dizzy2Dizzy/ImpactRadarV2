'use client';

import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Event } from '@/lib/api';
import { X, Calendar, TrendingUp, TrendingDown, Minus, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { InfoTierBadge } from './InfoTierBadge';
import { ImpactScoreBadge } from './ImpactScoreBadge';

interface EventTimelineModalProps {
  open: boolean;
  onClose: () => void;
  ticker: string;
  selectedEventId?: number;
}

export function EventTimelineModal({ open, onClose, ticker, selectedEventId }: EventTimelineModalProps) {
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [days, setDays] = useState(90);

  useEffect(() => {
    if (open && ticker) {
      loadTimeline();
    }
  }, [open, ticker, days]);

  const loadTimeline = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch(`/api/proxy/correlation/ticker/${ticker}?days=${days}`);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        
        // Handle paywall/plan restriction
        if (response.status === 402 || response.status === 403) {
          throw new Error('Event Timeline requires Pro or Enterprise plan. Upgrade to access correlation analytics.');
        }
        
        // Handle not found
        if (response.status === 404) {
          throw new Error(errorData.detail || `No events found for ${ticker} in the last ${days} days`);
        }
        
        throw new Error(errorData.detail || 'Failed to load timeline');
      }
      
      const data = await response.json();
      setEvents(data);
    } catch (err: any) {
      console.error('Failed to load timeline:', err);
      setError(err?.message || 'Failed to load timeline');
    } finally {
      setLoading(false);
    }
  };

  const getDirectionIcon = (direction: string) => {
    switch (direction) {
      case 'positive':
        return <TrendingUp className="h-4 w-4 text-green-400" />;
      case 'negative':
        return <TrendingDown className="h-4 w-4 text-red-400" />;
      default:
        return <Minus className="h-4 w-4 text-gray-400" />;
    }
  };

  const getDirectionColor = (direction: string) => {
    switch (direction) {
      case 'positive':
        return 'border-green-400 bg-green-400/10';
      case 'negative':
        return 'border-red-400 bg-red-400/10';
      case 'neutral':
        return 'border-gray-400 bg-gray-400/10';
      default:
        return 'border-yellow-400 bg-yellow-400/10';
    }
  };

  const formatTimeGap = (event: Event, nextEvent?: Event) => {
    if (!nextEvent) return null;
    
    const diff = new Date(nextEvent.date).getTime() - new Date(event.date).getTime();
    const days = Math.abs(Math.floor(diff / (1000 * 60 * 60 * 24)));
    
    return days;
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden flex flex-col p-0">
        <DialogHeader className="px-6 pt-6 pb-4 border-b border-white/10">
          <div className="flex items-center justify-between">
            <div>
              <DialogTitle className="text-2xl font-bold text-[--text]">
                Event Timeline: {ticker}
              </DialogTitle>
              <p className="text-sm text-[--muted] mt-1">
                Chronological view of all events for this ticker
              </p>
            </div>
            <div className="flex items-center gap-3">
              <select
                value={days}
                onChange={(e) => setDays(parseInt(e.target.value))}
                className="px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-[--text] text-sm"
              >
                <option value={30}>Last 30 days</option>
                <option value={60}>Last 60 days</option>
                <option value={90}>Last 90 days</option>
                <option value={180}>Last 180 days</option>
                <option value={365}>Last year</option>
              </select>
            </div>
          </div>
        </DialogHeader>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
            {loading && (
              <div className="flex flex-col items-center justify-center py-12 gap-2">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[--primary]"></div>
                <p className="text-[--muted]">Loading timeline...</p>
              </div>
            )}

            {error && (
              <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
                <p className="text-red-400">{error}</p>
              </div>
            )}

            {!loading && !error && events.length === 0 && (
              <div className="text-center py-12">
                <p className="text-[--muted]">No events found for {ticker} in the last {days} days</p>
              </div>
            )}

            {!loading && !error && events.length > 0 && (
              <div className="relative">
                {/* Vertical timeline line */}
                <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-white/10"></div>

                {/* Events */}
                <div className="space-y-6">
                  {events.map((event, index) => {
                    const isSelected = event.id === selectedEventId;
                    const nextEvent = index < events.length - 1 ? events[index + 1] : undefined;
                    const timeGap = formatTimeGap(event, nextEvent);
                    
                    return (
                      <div key={event.id} className="relative pl-20">
                        {/* Timeline dot */}
                        <div
                          className={`absolute left-6 top-3 w-5 h-5 rounded-full border-2 ${
                            isSelected
                              ? 'border-[--primary] bg-[--primary] ring-4 ring-[--border-strong]'
                              : getDirectionColor(event.direction)
                          } flex items-center justify-center z-10`}
                        >
                          {!isSelected && getDirectionIcon(event.direction)}
                        </div>

                        {/* Event card */}
                        <div
                          className={`bg-white/5 rounded-lg p-4 border ${
                            isSelected
                              ? 'border-[--primary] ring-2 ring-[--border-strong]'
                              : 'border-white/10'
                          } hover:bg-white/10 transition-colors`}
                        >
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-2 flex-wrap">
                                <span className="text-sm text-[--muted] flex items-center gap-1">
                                  <Calendar className="h-3 w-3" />
                                  {new Date(event.date).toLocaleDateString('en-US', {
                                    year: 'numeric',
                                    month: 'short',
                                    day: 'numeric'
                                  })}
                                </span>
                                <span className="px-2 py-1 bg-white/10 rounded text-xs text-[--muted]">
                                  {event.event_type?.replace(/_/g, ' ')}
                                </span>
                                <ImpactScoreBadge
                                  baseScore={event.impact_score}
                                  mlAdjustedScore={event.ml_adjusted_score}
                                  mlConfidence={event.ml_confidence}
                                  modelSource={event.model_source as any}
                                  modelVersion={event.ml_model_version}
                                  compact={true}
                                />
                                <InfoTierBadge tier={(event as any).info_tier || 'primary'} subtype={(event as any).info_subtype} />
                              </div>
                              
                              <h3 className="font-semibold text-[--text] mb-1">
                                {event.title}
                              </h3>
                              
                              {event.description && (
                                <p className="text-sm text-[--muted] mb-2">
                                  {event.description}
                                </p>
                              )}

                              {isSelected && (
                                <div className="mt-2 px-2 py-1 bg-[--primary-soft] border border-[--border-strong] rounded text-xs text-[--primary] inline-block">
                                  Selected Event
                                </div>
                              )}
                            </div>

                            {event.source_url && (
                              <a
                                href={event.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex-shrink-0 px-2 py-1 bg-blue-500/20 hover:bg-blue-500/30 border border-blue-500/30 rounded text-blue-400 hover:text-blue-300 flex items-center gap-1 transition-colors text-xs"
                              >
                                <ExternalLink className="h-3 w-3" />
                                Source
                              </a>
                            )}
                          </div>
                        </div>

                        {/* Time gap indicator */}
                        {timeGap !== null && (
                          <div className="absolute left-6 top-full mt-2 ml-2 text-xs text-[--muted] bg-[#0a0a0a] px-2 py-1 rounded border border-white/10 z-10">
                            ↓ {timeGap} day{timeGap !== 1 ? 's' : ''} later
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

        {/* Footer */}
        {!loading && events.length > 0 && (
          <div className="px-6 py-4 border-t border-white/10 bg-white/5">
            <p className="text-sm text-[--muted] text-center">
              Showing {events.length} event{events.length !== 1 ? 's' : ''} for {ticker}
            </p>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
