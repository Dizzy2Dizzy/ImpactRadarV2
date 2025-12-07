'use client';

import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { 
  TrendingUp, 
  TrendingDown, 
  Minus, 
  Building2, 
  Calendar, 
  Target,
  ExternalLink,
  BarChart3,
  AlertCircle
} from 'lucide-react';

interface PeerCompany {
  ticker: string;
  name: string;
  sector: string;
  industry: string;
  event_count: number;
  most_recent_event: string | null;
}

interface PeerEvent {
  id: number;
  ticker: string;
  company_name: string;
  event_type: string;
  title: string;
  description: string;
  date: string;
  impact_score: number;
  direction: string;
  confidence: number;
  sector: string;
  source_url: string | null;
  impact_p_move: number | null;
  impact_p_up: number | null;
  impact_p_down: number | null;
}

interface ComparisonData {
  target_event: PeerEvent;
  peer_events: PeerEvent[];
  comparison: {
    avg_peer_score: number;
    target_vs_peers: string;
    peer_count: number;
    score_diff: number;
    direction_distribution: Record<string, number>;
    avg_peer_confidence: number | null;
  };
}

interface PeerComparisonModalProps {
  open: boolean;
  onClose: () => void;
  eventId: number;
}

export function PeerComparisonModal({
  open,
  onClose,
  eventId,
}: PeerComparisonModalProps) {
  const [comparisonData, setComparisonData] = useState<ComparisonData | null>(null);
  const [peerCompanies, setPeerCompanies] = useState<PeerCompany[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'comparison' | 'peers'>('comparison');

  useEffect(() => {
    if (open && eventId) {
      loadComparisonData();
    }
  }, [open, eventId]);

  const loadComparisonData = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`/api/proxy/peers/event/${eventId}/compare`);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || 'Failed to load comparison data');
      }

      const data: ComparisonData = await response.json();
      setComparisonData(data);

      if (data.target_event) {
        loadPeerCompanies(data.target_event.ticker);
      }
    } catch (err: any) {
      console.error('Failed to load comparison data:', err);
      setError(err.message || 'Failed to load comparison data');
    } finally {
      setLoading(false);
    }
  };

  const loadPeerCompanies = async (ticker: string) => {
    try {
      const response = await fetch(`/api/proxy/peers/ticker/${ticker}?limit=5`);

      if (!response.ok) {
        console.error('Failed to load peer companies');
        return;
      }

      const peers: PeerCompany[] = await response.json();
      setPeerCompanies(peers);
    } catch (err: any) {
      console.error('Failed to load peer companies:', err);
    }
  };

  const getDirectionIcon = (direction: string) => {
    switch (direction) {
      case 'positive':
        return <TrendingUp className="h-4 w-4 text-green-400" />;
      case 'negative':
        return <TrendingDown className="h-4 w-4 text-red-400" />;
      case 'neutral':
        return <Minus className="h-4 w-4 text-gray-400" />;
      default:
        return <AlertCircle className="h-4 w-4 text-yellow-400" />;
    }
  };

  const getDirectionColor = (direction: string) => {
    switch (direction) {
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

  const getComparisonColor = (comparison: string) => {
    switch (comparison) {
      case 'higher':
        return 'text-green-400';
      case 'lower':
        return 'text-red-400';
      default:
        return 'text-blue-400';
    }
  };

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
      });
    } catch {
      return dateString;
    }
  };

  if (!open) return null;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-blue-400" />
            Peer Comparison Analysis
          </DialogTitle>
          <DialogDescription>
            Compare this event to similar events on peer companies
          </DialogDescription>
        </DialogHeader>

        {loading && (
          <div className="flex flex-col items-center justify-center py-12 gap-2">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400"></div>
            <p className="text-[--muted]">Loading peer comparison data...</p>
          </div>
        )}

        {error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-red-400 font-medium">Error loading comparison</p>
                <p className="text-sm text-red-400/80 mt-1">{error}</p>
              </div>
            </div>
          </div>
        )}

        {!loading && !error && comparisonData && (
          <>
            <div className="flex gap-2 border-b border-white/10 pb-2">
              <button
                onClick={() => setActiveTab('comparison')}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  activeTab === 'comparison'
                    ? 'bg-blue-500/20 text-blue-400'
                    : 'text-[--muted] hover:bg-white/5'
                }`}
              >
                Comparison
              </button>
              <button
                onClick={() => setActiveTab('peers')}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  activeTab === 'peers'
                    ? 'bg-blue-500/20 text-blue-400'
                    : 'text-[--muted] hover:bg-white/5'
                }`}
              >
                Peer Companies ({peerCompanies.length})
              </button>
            </div>

            {activeTab === 'comparison' && (
              <div className="space-y-6">
                <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4">
                  <div className="flex items-start gap-3 mb-3">
                    <Target className="h-5 w-5 text-blue-400 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-[--text] mb-1">Target Event</h3>
                      <p className="text-sm text-[--muted]">
                        {comparisonData.target_event.ticker} - {comparisonData.target_event.company_name}
                      </p>
                    </div>
                  </div>
                  
                  <div className="bg-white/5 rounded-lg p-4">
                    <h4 className="font-semibold text-[--text] mb-2">
                      {comparisonData.target_event.title}
                    </h4>
                    {comparisonData.target_event.description && (
                      <p className="text-sm text-[--muted] mb-3">
                        {comparisonData.target_event.description}
                      </p>
                    )}
                    <div className="flex items-center gap-4 text-sm">
                      <div className="flex items-center gap-2">
                        <Calendar className="h-4 w-4 text-[--muted]" />
                        <span className="text-[--muted]">
                          {formatDate(comparisonData.target_event.date)}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        {getDirectionIcon(comparisonData.target_event.direction)}
                        <span className={getDirectionColor(comparisonData.target_event.direction)}>
                          {comparisonData.target_event.direction}
                        </span>
                      </div>
                      <div className="px-3 py-1 bg-blue-500/20 border border-blue-500/30 rounded text-blue-400 font-bold">
                        {comparisonData.target_event.impact_score}% impact
                      </div>
                    </div>
                  </div>
                </div>

                <div className="bg-white/5 border border-white/10 rounded-lg p-6">
                  <h3 className="text-lg font-semibold text-[--text] mb-4 flex items-center gap-2">
                    <BarChart3 className="h-5 w-5 text-purple-400" />
                    Comparison Summary
                  </h3>
                  
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-white/5 rounded-lg p-4">
                      <div className="text-sm text-[--muted] mb-1">Target Score</div>
                      <div className="text-2xl font-bold text-blue-400">
                        {comparisonData.target_event.impact_score}
                      </div>
                    </div>
                    
                    <div className="bg-white/5 rounded-lg p-4">
                      <div className="text-sm text-[--muted] mb-1">Peer Average</div>
                      <div className="text-2xl font-bold text-purple-400">
                        {comparisonData.comparison.avg_peer_score.toFixed(1)}
                      </div>
                      <div className="text-xs text-[--muted] mt-1">
                        Based on {comparisonData.comparison.peer_count} similar events
                      </div>
                    </div>
                    
                    <div className="bg-white/5 rounded-lg p-4">
                      <div className="text-sm text-[--muted] mb-1">Comparison</div>
                      <div className={`text-2xl font-bold capitalize ${getComparisonColor(comparisonData.comparison.target_vs_peers)}`}>
                        {comparisonData.comparison.target_vs_peers}
                      </div>
                      <div className="text-xs text-[--muted] mt-1">
                        {comparisonData.comparison.score_diff > 0 ? '+' : ''}
                        {comparisonData.comparison.score_diff.toFixed(1)} points
                      </div>
                    </div>
                  </div>

                  {comparisonData.comparison.peer_count > 0 && (
                    <div className="mt-4 pt-4 border-t border-white/10">
                      <div className="text-sm text-[--muted] mb-2">Direction Distribution</div>
                      <div className="flex gap-3 flex-wrap">
                        {Object.entries(comparisonData.comparison.direction_distribution).map(([direction, count]) => (
                          <div key={direction} className="flex items-center gap-2 px-3 py-1.5 bg-white/5 rounded-lg">
                            {getDirectionIcon(direction)}
                            <span className="capitalize text-[--text]">{direction}</span>
                            <span className="text-[--muted]">×{count}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {comparisonData.peer_events.length > 0 ? (
                  <div>
                    <h3 className="text-lg font-semibold text-[--text] mb-4">
                      Similar Events on Peers ({comparisonData.peer_events.length})
                    </h3>
                    <div className="space-y-3">
                      {comparisonData.peer_events.slice(0, 10).map((event) => (
                        <div key={event.id} className="bg-white/5 border border-white/10 rounded-lg p-4 hover:bg-white/10 transition-colors">
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex-1">
                              <div className="flex items-center gap-3 mb-2">
                                <span className="font-semibold text-[--text]">{event.ticker}</span>
                                <span className="text-sm text-[--muted]">{event.company_name}</span>
                                <span className="px-2 py-1 bg-blue-500/20 border border-blue-500/30 rounded text-blue-400 text-sm font-bold">
                                  {event.impact_score}%
                                </span>
                                <div className="flex items-center gap-1">
                                  {getDirectionIcon(event.direction)}
                                  <span className={`text-sm capitalize ${getDirectionColor(event.direction)}`}>
                                    {event.direction}
                                  </span>
                                </div>
                              </div>
                              
                              <h4 className="text-sm font-medium text-[--text] mb-1">
                                {event.title}
                              </h4>
                              
                              {event.description && (
                                <p className="text-xs text-[--muted] mb-2 line-clamp-2">
                                  {event.description}
                                </p>
                              )}
                              
                              <div className="flex items-center gap-3 text-xs text-[--muted]">
                                <div className="flex items-center gap-1">
                                  <Calendar className="h-3 w-3" />
                                  {formatDate(event.date)}
                                </div>
                                {event.confidence !== null && (
                                  <span>{Math.round(event.confidence * 100)}% confidence</span>
                                )}
                              </div>
                            </div>
                            
                            {event.source_url && (
                              <a
                                href={event.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex-shrink-0 px-3 py-1.5 bg-blue-500/20 hover:bg-blue-500/30 border border-blue-500/30 rounded text-blue-400 hover:text-blue-300 flex items-center gap-2 transition-colors text-xs"
                              >
                                <ExternalLink className="h-3 w-3" />
                                Source
                              </a>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                    
                    {comparisonData.peer_events.length > 10 && (
                      <p className="text-sm text-[--muted] text-center mt-4">
                        Showing 10 of {comparisonData.peer_events.length} similar events
                      </p>
                    )}
                  </div>
                ) : (
                  <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-6 text-center">
                    <AlertCircle className="h-8 w-8 text-yellow-400 mx-auto mb-2" />
                    <p className="text-[--muted]">No similar events found on peer companies</p>
                    <p className="text-sm text-[--muted] mt-1">
                      Try adjusting the lookback period or check if there are peer companies available
                    </p>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'peers' && (
              <div>
                <h3 className="text-lg font-semibold text-[--text] mb-4 flex items-center gap-2">
                  <Building2 className="h-5 w-5 text-purple-400" />
                  Peer Companies in {comparisonData.target_event.sector}
                </h3>
                
                {peerCompanies.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {peerCompanies.map((peer) => (
                      <div key={peer.ticker} className="bg-white/5 border border-white/10 rounded-lg p-4">
                        <div className="flex items-start justify-between mb-2">
                          <div>
                            <h4 className="font-semibold text-[--text]">{peer.ticker}</h4>
                            <p className="text-sm text-[--muted]">{peer.name}</p>
                          </div>
                          <div className="text-right">
                            <div className="text-sm text-blue-400 font-medium">
                              {peer.event_count} events
                            </div>
                          </div>
                        </div>
                        
                        <div className="flex items-center gap-3 text-xs text-[--muted] mt-3 pt-3 border-t border-white/10">
                          <span className="px-2 py-1 bg-white/5 rounded">{peer.sector}</span>
                          {peer.industry && (
                            <span className="px-2 py-1 bg-white/5 rounded">{peer.industry}</span>
                          )}
                        </div>
                        
                        {peer.most_recent_event && (
                          <div className="flex items-center gap-2 mt-2 text-xs text-[--muted]">
                            <Calendar className="h-3 w-3" />
                            Last event: {formatDate(peer.most_recent_event)}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-6 text-center">
                    <AlertCircle className="h-8 w-8 text-yellow-400 mx-auto mb-2" />
                    <p className="text-[--muted]">No peer companies found</p>
                    <p className="text-sm text-[--muted] mt-1">
                      This company may be in a unique sector or there may not be enough data
                    </p>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
