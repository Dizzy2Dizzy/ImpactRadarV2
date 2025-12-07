'use client';

import { useState, useEffect } from 'react';
import { api, Event } from '@/lib/api';
import { InfoTierBadge } from './InfoTierBadge';
import { ImpactScoreBadge } from './ImpactScoreBadge';
import { AdvancedSearchModal, AdvancedSearchCriteria } from './AdvancedSearchModal';
import { EventTimelineModal } from './EventTimelineModal';
import { PriceChartModal } from './PriceChartModal';
import { PeerComparisonModal } from './PeerComparisonModal';
import { ModelVersionFilter, ModelVersion, getScoreForVersion, getScoreLabel } from './ModelVersionFilter';
import { ExternalLink, Calendar, Filter, ChevronDown, ChevronUp, FileDown, Search, X, Clock, LineChart, Users, CheckCircle, Cpu, Target, Sparkles, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tooltip } from '@/components/ui/tooltip';
import { useDashboardModeStore } from '@/stores/dashboardModeStore';

export function EventsTab() {
  const { mode } = useDashboardModeStore();
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedEvents, setExpandedEvents] = useState<Set<number>>(new Set());
  const [exporting, setExporting] = useState(false);
  
  const [ticker, setTicker] = useState('');
  const [sector, setSector] = useState('');
  const [category, setCategory] = useState('');
  const [minScore, setMinScore] = useState(0);
  const [direction, setDirection] = useState('');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [infoTier, setInfoTier] = useState('both');
  const [bearishOnly, setBearishOnly] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [modelVersion, setModelVersion] = useState<ModelVersion>('v1.5');
  
  const [showAdvancedSearch, setShowAdvancedSearch] = useState(false);
  const [advancedSearchCriteria, setAdvancedSearchCriteria] = useState<AdvancedSearchCriteria | null>(null);
  
  const [showTimeline, setShowTimeline] = useState(false);
  const [timelineTicker, setTimelineTicker] = useState('');
  const [timelineEventId, setTimelineEventId] = useState<number | undefined>(undefined);
  
  const [showChart, setShowChart] = useState(false);
  const [chartTicker, setChartTicker] = useState('');
  
  const [showPeerComparison, setShowPeerComparison] = useState(false);
  const [peerComparisonEventId, setPeerComparisonEventId] = useState<number>(0);

  const [eventSummaries, setEventSummaries] = useState<Map<number, { text: string; loading: boolean; error?: string }>>(new Map());

  const generateEventSummary = async (eventId: number) => {
    setEventSummaries(prev => {
      const newMap = new Map(prev);
      newMap.set(eventId, { text: '', loading: true });
      return newMap;
    });

    try {
      const response = await fetch(`/api/proxy/events/${eventId}/summary`);
      if (!response.ok) {
        throw new Error('Failed to generate summary');
      }
      const data = await response.json();
      
      setEventSummaries(prev => {
        const newMap = new Map(prev);
        newMap.set(eventId, { text: data.summary, loading: false });
        return newMap;
      });
    } catch (err: any) {
      setEventSummaries(prev => {
        const newMap = new Map(prev);
        newMap.set(eventId, { text: '', loading: false, error: 'Failed to generate summary. Please try again.' });
        return newMap;
      });
    }
  };

  const toggleEventExpanded = (eventId: number) => {
    setExpandedEvents(prev => {
      const newSet = new Set(prev);
      if (newSet.has(eventId)) {
        newSet.delete(eventId);
      } else {
        newSet.add(eventId);
      }
      return newSet;
    });
  };

  const loadEvents = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // If advanced search is active, use it instead of basic filters
      if (advancedSearchCriteria) {
        await performAdvancedSearch(advancedSearchCriteria);
        return;
      }
      
      const params: any = {
        limit: 100,
      };
      
      if (ticker) params.ticker = ticker.toUpperCase();
      if (sector) params.sector = sector;
      if (category) params.category = category;
      if (minScore > 0) params.min_score = minScore;
      if (direction) params.direction = direction;
      if (fromDate) params.from_date = new Date(fromDate).toISOString();
      if (toDate) params.to_date = new Date(toDate).toISOString();
      if (infoTier) params.info_tier = infoTier;
      if (mode) params.mode = mode;
      
      // Use public events endpoint with filters (available to dashboard users)
      const data = await api.events.getAll(params);
      setEvents(data);
    } catch (err: any) {
      console.error('Failed to load events:', err);
      if (err?.status === 403 || err?.message?.includes('403')) {
        setError('Access not available, please upgrade plan');
      } else {
        setError(err?.message || 'Failed to load events');
      }
    } finally {
      setLoading(false);
    }
  };

  const performAdvancedSearch = async (criteria: AdvancedSearchCriteria) => {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams();
      params.append('limit', '100');
      params.append('offset', '0');

      if (criteria.filters && criteria.filters.length > 0) {
        const filters = criteria.filters.map(f => ({
          field: f.field,
          operator: f.operator,
          value: f.value,
        }));
        params.append('filters', JSON.stringify(filters));
        params.append('logic', criteria.logic);
      }

      if (criteria.keyword) {
        params.append('keyword', criteria.keyword);
        if (criteria.keywordFields && criteria.keywordFields.length > 0) {
          params.append('keyword_fields', criteria.keywordFields.join(','));
        }
      }

      const response = await fetch(`/api/proxy/events/advanced-search?${params.toString()}`);
      
      if (!response.ok) {
        if (response.status === 403) {
          throw new Error('Access not available, please upgrade plan');
        }
        throw new Error('Advanced search failed');
      }

      const data = await response.json();
      setEvents(data);
    } catch (err: any) {
      console.error('Failed to perform advanced search:', err);
      setError(err?.message || 'Advanced search failed');
    } finally {
      setLoading(false);
    }
  };

  const handleAdvancedSearch = (criteria: AdvancedSearchCriteria) => {
    setAdvancedSearchCriteria(criteria);
    setShowAdvancedSearch(false);
    performAdvancedSearch(criteria);
  };

  const handleClearAdvancedSearch = () => {
    setAdvancedSearchCriteria(null);
    loadEvents();
  };

  useEffect(() => {
    loadEvents();
  }, [mode]);

  const handleSearch = () => {
    loadEvents();
  };

  const handleReset = () => {
    setTicker('');
    setSector('');
    setCategory('');
    setMinScore(0);
    setDirection('');
    setFromDate('');
    setToDate('');
    setInfoTier('both');
    setBearishOnly(false);
    loadEvents();
  };

  const handleExport = async () => {
    try {
      setExporting(true);
      
      const params = new URLSearchParams();
      params.append('limit', '1000');
      
      if (ticker) params.append('ticker', ticker.toUpperCase());
      if (sector) params.append('sector', sector);
      if (category) params.append('category', category);
      if (minScore > 0) params.append('min_impact', minScore.toString());
      if (direction) params.append('direction', direction);
      if (fromDate) params.append('from_date', new Date(fromDate).toISOString());
      if (toDate) params.append('to_date', new Date(toDate).toISOString());
      if (infoTier) params.append('info_tier', infoTier);
      
      const url = `/api/proxy/events/export?${params.toString()}`;
      
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error('Export failed');
      }
      
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      
      const today = new Date().toISOString().split('T')[0];
      link.download = `impactradar_events_${today}.csv`;
      
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
      
    } catch (err: any) {
      console.error('Failed to export events:', err);
      alert('Failed to export events. Please try again.');
    } finally {
      setExporting(false);
    }
  };

  const getDirectionColor = (dir: string) => {
    switch (dir) {
      case 'positive':
        return 'text-[--success]';
      case 'negative':
        return 'text-[--error]';
      case 'neutral':
        return 'text-[--neutral]';
      default:
        return 'text-[--warning]';
    }
  };

  if (loading && events.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-2">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[--primary]"></div>
        <p className="text-[--muted]">Loading events...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-2xl font-bold text-[--text]">Events</h2>
          <p className="text-sm text-[--muted]">Browse and filter all market events</p>
        </div>
        <div className="flex items-center gap-4 flex-wrap">
          <ModelVersionFilter value={modelVersion} onChange={setModelVersion} />
          <div className="flex gap-2">
            <Button
              onClick={handleExport}
              disabled={exporting || events.length === 0}
              variant="outline"
              className="flex items-center gap-2"
            >
              <FileDown className="h-4 w-4" />
              {exporting ? 'Exporting...' : 'Export to CSV'}
            </Button>
            <Button
              onClick={() => setShowAdvancedSearch(true)}
              variant="outline"
              className="flex items-center gap-2"
            >
              <Search className="h-4 w-4" />
              Advanced Search
            </Button>
            <Button
              onClick={() => setShowFilters(!showFilters)}
              variant="outline"
              className="flex items-center gap-2"
            >
              <Filter className="h-4 w-4" />
              {showFilters ? 'Hide Filters' : 'Show Filters'}
            </Button>
          </div>
        </div>
      </div>

      {advancedSearchCriteria && (
        <div className="bg-[--primary-light] border border-[--border-strong] rounded-lg p-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <Search className="h-4 w-4 text-[--primary]" />
                <span className="text-sm font-semibold text-[--primary]">Active Advanced Search</span>
              </div>
              <div className="space-y-2 text-sm text-[--text]">
                {advancedSearchCriteria.filters && advancedSearchCriteria.filters.length > 0 && (
                  <div>
                    <span className="text-[--muted]">Filters ({advancedSearchCriteria.logic}):</span>
                    <div className="flex flex-wrap gap-2 mt-1">
                      {advancedSearchCriteria.filters.map((filter, index) => (
                        <span
                          key={filter.id}
                          className="px-2 py-1 bg-[--primary-soft] border border-[--border-strong] rounded text-xs"
                        >
                          {filter.field} {filter.operator} {Array.isArray(filter.value) ? filter.value.join(', ') : filter.value}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {advancedSearchCriteria.keyword && (
                  <div>
                    <span className="text-[--muted]">Keyword:</span>{' '}
                    <span className="font-medium">{advancedSearchCriteria.keyword}</span>
                    <span className="text-[--muted] ml-2">
                      (in: {advancedSearchCriteria.keywordFields.join(', ')})
                    </span>
                  </div>
                )}
              </div>
            </div>
            <Button
              onClick={handleClearAdvancedSearch}
              variant="outline"
              size="sm"
              className="flex items-center gap-2"
            >
              <X className="h-4 w-4" />
              Clear
            </Button>
          </div>
        </div>
      )}

      {showFilters && (
        <div className="bg-[--surface-muted] rounded-lg p-6 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-[--text] mb-2">
                Ticker
              </label>
              <input
                type="text"
                value={ticker}
                onChange={(e) => setTicker(e.target.value)}
                placeholder="e.g., AAPL"
                className="w-full px-3 py-2 bg-[--surface-glass] border border-[--border] rounded-lg text-[--text] placeholder-[--muted]"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-[--text] mb-2">
                Sector
              </label>
              <select
                value={sector}
                onChange={(e) => setSector(e.target.value)}
                className="w-full px-3 py-2 bg-[--surface-glass] border border-[--border] rounded-lg text-[--text]"
              >
                <option value="">All Sectors</option>
                <option value="technology">Technology</option>
                <option value="healthcare">Healthcare</option>
                <option value="biotech">Biotech</option>
                <option value="finance">Finance</option>
                <option value="energy">Energy</option>
                <option value="consumer">Consumer</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-[--text] mb-2">
                Event Type
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full px-3 py-2 bg-[--surface-glass] border border-[--border] rounded-lg text-[--text]"
              >
                <option value="">All Types</option>
                <option value="sec_8k">SEC 8-K</option>
                <option value="sec_10q">SEC 10-Q</option>
                <option value="fda_approval">FDA Approval</option>
                <option value="earnings">Earnings</option>
                <option value="ma_activity">M&A Activity</option>
                <option value="product_launch">Product Launch</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-[--text] mb-2">
                Direction
              </label>
              <select
                value={direction}
                onChange={(e) => setDirection(e.target.value)}
                className="w-full px-3 py-2 bg-[--surface-glass] border border-[--border] rounded-lg text-[--text]"
              >
                <option value="">All Directions</option>
                <option value="positive">Positive</option>
                <option value="negative">Negative</option>
                <option value="neutral">Neutral</option>
                <option value="uncertain">Uncertain</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-[--text] mb-2">
                Information Tier
              </label>
              <select
                value={infoTier}
                onChange={(e) => setInfoTier(e.target.value)}
                className="w-full px-3 py-2 bg-[--surface-glass] border border-[--border] rounded-lg text-[--text]"
              >
                <option value="both">All Events</option>
                <option value="primary">Primary Only</option>
                <option value="secondary">Secondary Only</option>
              </select>
            </div>

            <div>
              <label className="flex items-center gap-3 text-sm font-medium text-[--text] cursor-pointer">
                <input
                  type="checkbox"
                  checked={bearishOnly}
                  onChange={(e) => setBearishOnly(e.target.checked)}
                  className="w-4 h-4 rounded border-white/20 bg-white/10 text-red-500 focus:ring-red-500"
                />
                <span className="flex items-center gap-1">
                  <span className="text-[--warning]">!</span>
                  Bearish Signals Only
                </span>
              </label>
              <p className="text-xs text-[--muted] mt-1 ml-7">
                Show only events with detected bearish signals
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-[--text] mb-2">
                Min Score: {minScore}
              </label>
              <input
                type="range"
                min="0"
                max="100"
                step="5"
                value={minScore}
                onChange={(e) => setMinScore(parseInt(e.target.value))}
                className="w-full"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-[--text] mb-2">
                From Date
              </label>
              <input
                type="date"
                value={fromDate}
                onChange={(e) => setFromDate(e.target.value)}
                className="w-full px-3 py-2 bg-[--surface-glass] border border-[--border] rounded-lg text-[--text]"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-[--text] mb-2">
                To Date
              </label>
              <input
                type="date"
                value={toDate}
                onChange={(e) => setToDate(e.target.value)}
                className="w-full px-3 py-2 bg-[--surface-glass] border border-[--border] rounded-lg text-[--text]"
              />
            </div>
          </div>

          <div className="flex gap-3">
            <Button onClick={handleSearch}>Apply Filters</Button>
            <Button onClick={handleReset} variant="outline">Reset</Button>
          </div>
        </div>
      )}

      {error && (
        <div className="bg-[--error-light] border border-[--border] rounded-lg p-4">
          <p className="text-[--error]">{error}</p>
        </div>
      )}

      <div className="space-y-4">
        {loading && events.length > 0 && (
          <p className="text-sm text-[--muted]">Updating...</p>
        )}
        
        {/* Filter events based on model version and bearish filter */}
        {(() => {
          let filteredEvents = modelVersion === 'v2.0' 
            ? events.filter(e => e.model_source && e.model_source !== 'deterministic' && e.ml_adjusted_score != null)
            : events;
          
          // Apply bearish filter if enabled
          if (bearishOnly) {
            filteredEvents = filteredEvents.filter(e => (e as any).bearish_signal === true);
          }
          
          if (filteredEvents.length === 0 && !loading) {
            return (
              <div className="text-center py-12">
                <p className="text-[--muted]">
                  {bearishOnly 
                    ? 'No events with bearish signals found. The current dataset contains mostly positive events.'
                    : modelVersion === 'v2.0' 
                      ? 'No events with Market Echo ML scores found. Try switching to V1.5 (Hybrid) for full coverage.'
                      : 'No events found matching your filters'}
                </p>
              </div>
            );
          }
          
          return filteredEvents.map((event) => {
          const isExpanded = expandedEvents.has(event.id);
          const hasProbabilities = event.impact_p_move != null && event.impact_p_up != null && event.impact_p_down != null;
          const isLowConfidence = (event.confidence || 0) < 0.2;
          
          return (
            <div
              key={event.id}
              className="bg-[--surface-muted] rounded-lg p-6 hover:bg-[--surface-hover] transition-colors"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2 flex-wrap">
                    <span className="font-semibold text-[--text]">{event.ticker}</span>
                    <span className="text-sm text-[--muted]">{event.company_name}</span>
                    
                    <ImpactScoreBadge
                      baseScore={event.impact_score}
                      mlAdjustedScore={event.ml_adjusted_score}
                      mlConfidence={event.ml_confidence}
                      modelSource={event.model_source as any}
                      modelVersion={event.ml_model_version}
                      compact={false}
                      showDelta={modelVersion !== 'v1.0'}
                      displayVersion={modelVersion}
                    />
                    
                    {event.confidence !== null && event.confidence !== undefined ? (
                      <Tooltip
                        content={
                          <div className="space-y-1 max-w-xs text-sm">
                            <div className="font-semibold">Confidence Level: {Math.round(event.confidence * 100)}%</div>
                            <div>
                              This indicates how reliable the impact prediction is based on historical data. 
                              Higher confidence means more similar historical events to validate this prediction.
                            </div>
                            {isLowConfidence && (
                              <div className="text-[--warning] mt-2 pt-2 border-t border-[--border]">
                                Low confidence indicates limited historical data for this event type.
                              </div>
                            )}
                          </div>
                        }
                      >
                        <span className="px-2 py-1 bg-[--surface-glass] rounded text-sm text-[--muted] cursor-help">
                          {Math.round(event.confidence * 100)}% confidence
                        </span>
                      </Tooltip>
                    ) : (
                      <Tooltip
                        content={
                          <div className="space-y-1 max-w-xs text-sm">
                            <div className="font-semibold">Baseline Confidence</div>
                            <div>
                              This event uses baseline scoring without historical validation data.
                            </div>
                          </div>
                        }
                      >
                        <span className="px-2 py-1 bg-[--surface-glass] rounded text-sm text-[--muted] cursor-help">
                          Baseline
                        </span>
                      </Tooltip>
                    )}
                    
                    {isLowConfidence && (
                      <span className="px-2 py-1 bg-[--warning-soft] border border-[--border-strong] rounded text-[--warning] text-xs font-medium">
                        Baseline (limited data)
                      </span>
                    )}
                    
                    <InfoTierBadge tier={(event as any).info_tier || 'primary'} subtype={(event as any).info_subtype} />
                    <span className={`text-sm capitalize ${getDirectionColor(event.direction)}`}>
                      {event.direction}
                    </span>
                    
                    {(event as any).bearish_signal && (
                      <Tooltip
                        content={
                          <div className="space-y-1 max-w-xs text-sm">
                            <div className="font-semibold text-[--error] flex items-center gap-1">
                              <span className="text-[--warning]">Warning:</span> Bearish Signal Detected
                            </div>
                            <div className="text-sm text-[--muted]">
                              Confidence: {Math.round(((event as any).bearish_confidence || 0) * 100)}%
                            </div>
                            {(event as any).bearish_rationale && (
                              <div className="text-sm pt-2 border-t border-[--border-muted]">
                                {(event as any).bearish_rationale}
                              </div>
                            )}
                          </div>
                        }
                      >
                        <span className="px-2 py-1 bg-[--error-soft] border border-[--border-strong] rounded text-[--error] text-xs font-medium cursor-help flex items-center gap-1">
                          <span className="text-[--warning]">!</span>
                          Bearish Signal
                          <span className="text-[--error]">({Math.round(((event as any).bearish_confidence || 0) * 100)}%)</span>
                        </span>
                      </Tooltip>
                    )}
                  </div>

                  <h3 className="text-lg font-semibold text-[--text] mb-2">{event.title}</h3>
                  
                  {event.description && (
                    <p className="text-sm text-[--muted] mb-3">{event.description}</p>
                  )}

                  <div className="flex items-center gap-4 text-sm text-[--muted] mb-3">
                    <span className="flex items-center gap-1">
                      <Calendar className="h-4 w-4" />
                      {new Date(event.date).toLocaleDateString()}
                    </span>
                    <span className="px-2 py-1 bg-[--surface-glass] rounded">
                      {event.event_type?.replace(/_/g, ' ')}
                    </span>
                  </div>

                  <div className="flex items-center gap-4 mt-2">
                    {hasProbabilities && (
                      <button
                        onClick={() => toggleEventExpanded(event.id)}
                        className="flex items-center gap-2 text-sm text-[--primary] hover:opacity-80 transition-colors"
                      >
                        {isExpanded ? (
                          <>
                            <ChevronUp className="h-4 w-4" />
                            Hide Impact Analysis
                          </>
                        ) : (
                          <>
                            <ChevronDown className="h-4 w-4" />
                            Show Impact Analysis
                          </>
                        )}
                      </button>
                    )}
                    
                    <button
                      onClick={() => {
                        setChartTicker(event.ticker);
                        setShowChart(true);
                      }}
                      className="flex items-center gap-2 text-sm text-[--success] hover:opacity-80 transition-colors"
                    >
                      <LineChart className="h-4 w-4" />
                      View Chart
                    </button>
                    
                    <button
                      onClick={() => {
                        setTimelineTicker(event.ticker);
                        setTimelineEventId(event.id);
                        setShowTimeline(true);
                      }}
                      className="flex items-center gap-2 text-sm text-[--accent] hover:opacity-80 transition-colors"
                    >
                      <Clock className="h-4 w-4" />
                      View Timeline
                    </button>
                    
                    <button
                      onClick={() => {
                        setPeerComparisonEventId(event.id);
                        setShowPeerComparison(true);
                      }}
                      className="flex items-center gap-2 text-sm text-[--warning] hover:opacity-80 transition-colors"
                    >
                      <Users className="h-4 w-4" />
                      Compare Peers
                    </button>
                  </div>

                  {isExpanded && hasProbabilities && (
                    <div className="mt-4 p-4 bg-[--primary-light] border border-[--border] rounded-lg">
                      <div className="text-sm font-semibold mb-3 text-[--text]">Probabilistic Impact Analysis</div>
                      <div className="grid grid-cols-3 gap-4 text-sm mb-4">
                        <div>
                          <div className="text-[--muted] mb-1">Move Probability</div>
                          <div className="text-2xl font-bold text-[--primary]">{((event.impact_p_move || 0) * 100).toFixed(1)}%</div>
                          <div className="text-xs text-[--muted]">P(|move| &gt; 3%)</div>
                        </div>
                        <div>
                          <div className="text-[--muted] mb-1">Upside Probability</div>
                          <div className="text-2xl font-bold text-[--success]">{((event.impact_p_up || 0) * 100).toFixed(1)}%</div>
                          <div className="text-xs text-[--muted]">P(move &gt; +3%)</div>
                        </div>
                        <div>
                          <div className="text-[--muted] mb-1">Downside Probability</div>
                          <div className="text-2xl font-bold text-[--error]">{((event.impact_p_down || 0) * 100).toFixed(1)}%</div>
                          <div className="text-xs text-[--muted]">P(move &lt; -3%)</div>
                        </div>
                      </div>
                      <div className="text-xs text-[--muted] border-t border-[--border-muted] pt-3">
                        <strong>Disclaimer:</strong> This is a model-estimated impact based on historical behavior of similar events. 
                        It is not a guarantee of future performance and not investment advice.
                      </div>
                    </div>
                  )}

                  {isExpanded && (
                    <div className="mt-4 p-4 bg-[--accent-light] border border-[--border] rounded-lg">
                      <div className="text-sm font-semibold mb-3 text-[--text]">AI Prediction Details</div>
                      <div className="space-y-2 text-sm">
                        <div className="flex items-center justify-between">
                          <span className="text-[--muted]">Base Score:</span>
                          <span className="font-semibold text-[--text]">{event.impact_score}</span>
                        </div>
                        
                        {event.ml_adjusted_score != null && event.ml_adjusted_score !== event.impact_score && (
                          <div className="flex items-center justify-between">
                            <span className="text-[--muted]">ML-Adjusted Score:</span>
                            <span className="font-semibold text-[--accent]">{event.ml_adjusted_score}</span>
                          </div>
                        )}

                        <div className="flex items-center justify-between">
                          <span className="text-[--muted]">Model Used:</span>
                          <div className="flex items-center gap-2">
                            {event.model_source === 'family-specific' && (
                              <>
                                <CheckCircle className="h-4 w-4 text-[--success]" />
                                <span className="font-semibold text-[--success]">Family-Specific Model (SEC 8-K)</span>
                              </>
                            )}
                            {event.model_source === 'global' && (
                              <>
                                <Cpu className="h-4 w-4 text-[--primary]" />
                                <span className="font-semibold text-[--primary]">Global Model (All Families)</span>
                              </>
                            )}
                            {(!event.model_source || event.model_source === 'deterministic') && (
                              <>
                                <Target className="h-4 w-4 text-[--neutral]" />
                                <span className="font-semibold text-[--neutral]">Deterministic Only</span>
                              </>
                            )}
                          </div>
                        </div>

                        {event.ml_model_version && (
                          <div className="flex items-center justify-between">
                            <span className="text-[--muted]">Model Version:</span>
                            <span className="font-mono text-xs text-[--text]">{event.ml_model_version}</span>
                          </div>
                        )}

                        {event.ml_confidence != null && (
                          <div className="flex items-center justify-between">
                            <span className="text-[--muted]">Confidence:</span>
                            <span className="font-semibold text-[--text]">{(event.ml_confidence * 100).toFixed(1)}%</span>
                          </div>
                        )}

                        {event.delta_applied != null && event.delta_applied !== 0 && (
                          <div className="flex items-center justify-between">
                            <span className="text-[--muted]">Delta Applied:</span>
                            <span className={`font-semibold ${event.delta_applied > 0 ? 'text-[--success]' : 'text-[--error]'}`}>
                              {event.delta_applied > 0 ? '+' : ''}{event.delta_applied.toFixed(1)} points
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                <div className="flex flex-col gap-2 flex-shrink-0">
                  {event.source_url && (
                    <a
                      href={event.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-3 py-2 bg-[--primary-soft] hover:bg-[--surface-hover] border border-[--border-strong] rounded-lg text-[--primary] hover:opacity-80 flex items-center gap-2 transition-colors text-sm font-medium"
                      title="View source"
                    >
                      <ExternalLink className="h-4 w-4" />
                      View Source
                    </a>
                  )}
                  
                  <button
                    onClick={() => generateEventSummary(event.id)}
                    disabled={eventSummaries.get(event.id)?.loading}
                    className="px-3 py-2 bg-[--accent-soft] hover:bg-[--surface-hover] border border-[--border-strong] rounded-lg text-[--accent] hover:opacity-80 flex items-center gap-2 transition-colors text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                    title="Generate AI Summary"
                  >
                    {eventSummaries.get(event.id)?.loading ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Generating...
                      </>
                    ) : (
                      <>
                        <Sparkles className="h-4 w-4" />
                        Summary
                      </>
                    )}
                  </button>
                </div>
              </div>
              
              {eventSummaries.get(event.id)?.text && (
                <div className="mt-4 p-4 bg-[--accent-light] border border-[--border] rounded-lg">
                  <p className="text-sm text-[--text] leading-relaxed whitespace-pre-wrap">
                    {eventSummaries.get(event.id)?.text}
                  </p>
                  <div className="mt-3 flex items-center gap-2">
                    <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-[--accent] rounded-lg">
                      <Cpu className="h-4 w-4 text-[--text-on-primary]" />
                      <span className="text-sm font-semibold text-[--text-on-primary]">V2.0</span>
                      <span className="text-sm text-[--text-on-primary]/70">(Market Echo)</span>
                    </div>
                  </div>
                </div>
              )}
              
              {eventSummaries.get(event.id)?.error && (
                <div className="mt-4 p-3 bg-[--error-light] border border-[--border] rounded-lg">
                  <p className="text-sm text-[--error]">{eventSummaries.get(event.id)?.error}</p>
                </div>
              )}
            </div>
          );
        });
        })()}
      </div>

      {events.length > 0 && (
        <div className="text-center text-sm text-[--muted]">
          Showing {modelVersion === 'v2.0' 
            ? events.filter(e => e.model_source && e.model_source !== 'deterministic' && e.ml_adjusted_score != null).length
            : events.length} events
          {modelVersion !== 'v1.5' && (
            <span className="ml-2 text-xs text-[--muted]">
              ({modelVersion === 'v1.0' ? 'Deterministic' : 'Market Echo ML'} view)
            </span>
          )}
        </div>
      )}

      <AdvancedSearchModal
        open={showAdvancedSearch}
        onClose={() => setShowAdvancedSearch(false)}
        onSearch={handleAdvancedSearch}
        initialCriteria={advancedSearchCriteria || undefined}
      />

      <EventTimelineModal
        open={showTimeline}
        onClose={() => setShowTimeline(false)}
        ticker={timelineTicker}
        selectedEventId={timelineEventId}
      />

      <PriceChartModal
        open={showChart}
        onClose={() => setShowChart(false)}
        ticker={chartTicker}
      />

      <PeerComparisonModal
        open={showPeerComparison}
        onClose={() => setShowPeerComparison(false)}
        eventId={peerComparisonEventId}
      />
    </div>
  );
}
