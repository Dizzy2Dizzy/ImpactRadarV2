'use client';

import { X, Calendar, ExternalLink } from 'lucide-react';
import { InfoTierBadge } from './InfoTierBadge';
import { ImpactScoreBadge, DisplayVersion } from './ImpactScoreBadge';
import { Tooltip } from '@/components/ui/tooltip';

interface Event {
  id: number;
  ticker: string;
  company_name: string;
  event_type: string;
  title: string;
  description?: string;
  date: string;
  source: string;
  source_url?: string;
  impact_score: number;
  direction: string;
  confidence: number;
  rationale?: string;
  sector?: string;
  info_tier?: string;
  info_subtype?: string;
  impact_p_move?: number;
  impact_p_up?: number;
  impact_p_down?: number;
  ml_adjusted_score?: number;
  ml_confidence?: number;
  model_source?: 'family-specific' | 'global' | 'deterministic';
  ml_model_version?: string;
}

interface CalendarDayModalProps {
  open: boolean;
  onClose: () => void;
  date: string;
  events: Event[];
  displayVersion?: DisplayVersion;
}

export function CalendarDayModal({ open, onClose, date, events, displayVersion = 'v1.5' }: CalendarDayModalProps) {
  // Sort events by impact score (descending)
  const sortedEvents = [...events].sort((a, b) => b.impact_score - a.impact_score);

  const getDirectionColor = (dir: string) => {
    switch (dir) {
      case 'positive':
        return 'text-green-400';
      case 'negative':
        return 'text-red-400';
      case 'neutral':
        return 'text-gray-400';
      default:
        return 'text-yellow-400';
    }
  };

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { 
      weekday: 'long', 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric' 
    });
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/50 backdrop-blur-sm" 
        onClick={onClose}
      />
      
      {/* Modal Content */}
      <div className="relative bg-[--panel] rounded-lg border border-white/10 w-full max-w-3xl max-h-[80vh] overflow-hidden flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-white/10">
            <div>
              <h2 className="text-2xl font-bold text-[--text] flex items-center gap-2">
                <Calendar className="h-6 w-6" />
                {formatDate(date)}
              </h2>
              <p className="text-sm text-[--muted] mt-1">
                {sortedEvents.length} {sortedEvents.length === 1 ? 'event' : 'events'}
              </p>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-sm opacity-70 hover:opacity-100 text-[--muted] hover:text-[--text] transition-opacity"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Events List */}
          <div className="flex-1 overflow-y-auto p-6">
            {sortedEvents.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-[--muted]">No events on this date</p>
              </div>
            ) : (
              <div className="space-y-4">
                {sortedEvents.map((event) => {
                  const hasProbabilities = 
                    event.impact_p_move != null && 
                    event.impact_p_up != null && 
                    event.impact_p_down != null;

                  return (
                    <div
                      key={event.id}
                      className="bg-white/5 rounded-lg p-5 hover:bg-white/10 transition-colors border border-white/5"
                    >
                      {/* Event Header */}
                      <div className="flex items-start justify-between gap-4 mb-3">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2 flex-wrap">
                            <span className="font-semibold text-[--text]">
                              {event.ticker}
                            </span>
                            <span className="text-sm text-[--muted]">
                              {event.company_name}
                            </span>
                            
                            <ImpactScoreBadge
                              baseScore={event.impact_score}
                              mlAdjustedScore={event.ml_adjusted_score}
                              mlConfidence={event.ml_confidence}
                              modelSource={event.model_source}
                              modelVersion={event.ml_model_version}
                              compact={false}
                              showDelta={true}
                              displayVersion={displayVersion}
                            />
                            
                            <InfoTierBadge 
                              tier={event.info_tier || 'primary'} 
                              subtype={event.info_subtype} 
                            />
                            
                            <span className={`text-sm capitalize ${getDirectionColor(event.direction)}`}>
                              {event.direction}
                            </span>
                          </div>

                          <h3 className="text-base font-semibold text-[--text] mb-2">
                            {event.title}
                          </h3>
                          
                          {event.description && (
                            <p className="text-sm text-[--muted] mb-2">
                              {event.description}
                            </p>
                          )}

                          <div className="flex items-center gap-3 text-xs text-[--muted]">
                            <span className="px-2 py-1 bg-white/10 rounded">
                              {event.event_type?.replace(/_/g, ' ')}
                            </span>
                            {event.sector && (
                              <span className="px-2 py-1 bg-white/10 rounded">
                                {event.sector}
                              </span>
                            )}
                            {event.confidence !== null && event.confidence !== undefined && (
                              <span className="px-2 py-1 bg-white/10 rounded">
                                {Math.round(event.confidence * 100)}% confidence
                              </span>
                            )}
                          </div>
                        </div>

                        {event.source_url && (
                          <a
                            href={event.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-400 hover:text-blue-300 transition-colors"
                          >
                            <ExternalLink className="h-4 w-4" />
                          </a>
                        )}
                      </div>

                      {/* Rationale */}
                      {event.rationale && (
                        <div className="mt-3 p-3 bg-blue-500/10 border border-blue-500/20 rounded text-sm text-[--text]">
                          <span className="text-blue-400 font-medium">Rationale: </span>
                          {event.rationale}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
  );
}
