'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Filter, TrendingUp, RefreshCw, Info } from 'lucide-react';
import { Tooltip } from '@/components/ui/tooltip';
import { useDashboardModeStore } from '@/stores/dashboardModeStore';
import { ModelVersionFilter } from './ModelVersionFilter';
import { DisplayVersion } from './ImpactScoreBadge';

interface EventPattern {
  pattern: string;
  frequency: number;
  avg_days_between: number;
  example_tickers: string[];
}

interface PatternsResponse {
  patterns: EventPattern[];
  total_patterns: number;
  filters: {
    event_type: string | null;
    days_window: number;
    min_frequency: number;
  };
}

interface TickerEvent {
  id: number;
  ticker: string;
  event_type: string;
  title: string;
  date: string;
  impact_score: number;
  ml_adjusted_score?: number;
  model_source?: string;
  direction: string;
  source_url: string;
}

export function CorrelationTab() {
  const { mode } = useDashboardModeStore();
  const [patterns, setPatterns] = useState<EventPattern[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [eventType, setEventType] = useState('');
  const [daysWindow, setDaysWindow] = useState(30);
  const [minFrequency, setMinFrequency] = useState(3);
  const [showFilters, setShowFilters] = useState(false);
  const [loadingTicker, setLoadingTicker] = useState<string | null>(null);
  const [modelVersion, setModelVersion] = useState<DisplayVersion>('v1.5');
  
  // Ticker timeline view state
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [tickerEvents, setTickerEvents] = useState<TickerEvent[]>([]);
  
  // Cache for ticker events to avoid repeated API calls
  const [tickerCache, setTickerCache] = useState<Record<string, TickerEvent[]>>({});
  
  // Pagination state for patterns
  const [patternsPage, setPatternsPage] = useState(1);
  const patternsPerPage = 20;

  useEffect(() => {
    loadPatterns();
  }, [mode]);

  const loadPatterns = async () => {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams();
      if (eventType) params.append('event_type', eventType);
      params.append('days_window', daysWindow.toString());
      params.append('min_frequency', minFrequency.toString());
      if (mode) params.append('mode', mode);

      const response = await fetch(`/api/proxy/correlation/patterns?${params.toString()}`);
      
      if (!response.ok) {
        if (response.status === 403) {
          throw new Error('Access not available, please upgrade plan');
        }
        throw new Error('Failed to load patterns');
      }

      const data: PatternsResponse = await response.json();
      setPatterns(data.patterns);
    } catch (err: any) {
      console.error('Failed to load patterns:', err);
      setError(err?.message || 'Failed to load event patterns');
    } finally {
      setLoading(false);
    }
  };

  const handleApplyFilters = () => {
    loadPatterns();
  };

  const handleReset = () => {
    setEventType('');
    setDaysWindow(30);
    setMinFrequency(3);
    setTimeout(() => loadPatterns(), 100);
  };

  const handleTickerClick = async (ticker: string) => {
    try {
      setLoadingTicker(ticker);
      setError(null);

      // Check cache first
      if (tickerCache[ticker]) {
        console.log(`Using cached data for ${ticker}`);
        setSelectedTicker(ticker);
        setTickerEvents(tickerCache[ticker]);
        setLoadingTicker(null);
        return;
      }

      const response = await fetch(`/api/proxy/correlation/ticker/${ticker}?days=90&limit=100`);
      
      if (!response.ok) {
        if (response.status === 403) {
          throw new Error('Access not available, please upgrade plan');
        }
        if (response.status === 404) {
          throw new Error(`No events found for ticker ${ticker} in the last 90 days`);
        }
        throw new Error(`Failed to load correlation timeline for ${ticker}`);
      }

      const events = await response.json();
      console.log(`Loaded ${events.length} events for ${ticker}`);
      
      // Cache the results
      setTickerCache(prev => ({ ...prev, [ticker]: events }));
      
      // Show ticker-specific event timeline
      setSelectedTicker(ticker);
      setTickerEvents(events);
    } catch (err: any) {
      console.error(`Failed to load correlation for ${ticker}:`, err);
      setError(err?.message || `Failed to load correlation timeline for ${ticker}`);
    } finally {
      setLoadingTicker(null);
    }
  };
  
  const handleBackToPatterns = () => {
    setSelectedTicker(null);
    setTickerEvents([]);
    setError(null);
  };

  const getScoreForVersion = (event: TickerEvent): number => {
    switch (modelVersion) {
      case 'v1.0':
        return event.impact_score || 50;
      case 'v1.5':
        return event.ml_adjusted_score || event.impact_score || 50;
      case 'v2.0':
        if (event.model_source && event.model_source !== 'deterministic') {
          return event.ml_adjusted_score || event.impact_score || 50;
        }
        return event.impact_score || 50;
      default:
        return event.ml_adjusted_score || event.impact_score || 50;
    }
  };

  const getFilteredEvents = (): TickerEvent[] => {
    if (modelVersion === 'v2.0') {
      return tickerEvents.filter(event => 
        event.model_source && event.model_source !== 'deterministic'
      );
    }
    return tickerEvents;
  };

  const filteredTickerEvents = getFilteredEvents();

  if (loading && patterns.length === 0 && !selectedTicker) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-2">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[--primary]"></div>
        <p className="text-[--muted]">Analyzing event patterns...</p>
      </div>
    );
  }

  // Ticker-specific timeline view
  if (selectedTicker) {
    return (
      <div className="space-y-6">
        {/* Header with Back Button */}
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-4">
            <Button
              onClick={handleBackToPatterns}
              variant="outline"
              className="flex items-center gap-2"
            >
              ← Back to Patterns
            </Button>
            <div>
              <h2 className="text-2xl font-bold text-[--text]">
                Correlation Timeline: {selectedTicker}
              </h2>
              <p className="text-sm text-[--muted]">
                Event history for {selectedTicker} over the last 90 days
              </p>
            </div>
          </div>
          <ModelVersionFilter value={modelVersion} onChange={setModelVersion} />
        </div>

        {/* Error State */}
        {error && (
          <div className="bg-[--error-light] border border-[--border-strong] rounded-lg p-4 text-[--error]">
            {error}
          </div>
        )}

        {/* Events Timeline */}
        {filteredTickerEvents.length > 0 ? (
          <div className="bg-[--surface-muted] rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-[--surface-glass] border-b border-[--border]">
                  <tr>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-[--text]">Date</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-[--text]">Event Type</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-[--text]">Title</th>
                    <th className="px-6 py-4 text-center text-sm font-semibold text-[--text]">Impact</th>
                    <th className="px-6 py-4 text-center text-sm font-semibold text-[--text]">Direction</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-[--text]">Source</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[--border]">
                  {filteredTickerEvents.map((event) => {
                    const score = getScoreForVersion(event);
                    return (
                      <tr key={event.id} className="hover:bg-[--surface-hover] transition-colors">
                        <td className="px-6 py-4 text-sm text-[--muted]">
                          {new Date(event.date).toLocaleDateString('en-US', { 
                            month: 'short', 
                            day: 'numeric', 
                            year: 'numeric' 
                          })}
                        </td>
                        <td className="px-6 py-4">
                          <span className="inline-flex items-center px-2 py-1 bg-[--primary-soft] border border-[--border-strong] rounded text-xs text-[--primary]">
                            {event.event_type}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-sm text-[--text] max-w-md truncate">
                          {event.title}
                        </td>
                        <td className="px-6 py-4 text-center">
                          <span className={`font-semibold ${
                            score >= 70 ? 'text-[--error]' :
                            score >= 40 ? 'text-[--warning]' :
                            'text-[--success]'
                          }`}>
                            {score}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-center">
                          <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${
                            event.direction === 'positive' ? 'bg-[--success-soft] text-[--success] border border-[--border-strong]' :
                            event.direction === 'negative' ? 'bg-[--error-soft] text-[--error] border border-[--border-strong]' :
                            'bg-[--muted-soft] text-[--muted] border border-[--border-strong]'
                          }`}>
                            {event.direction}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <a 
                            href={event.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[--primary] hover:text-[--accent] text-sm underline"
                          >
                            View Source
                          </a>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="text-center py-12 bg-[--surface-muted] rounded-lg">
            <TrendingUp className="h-12 w-12 text-[--muted] mx-auto mb-4" />
            <p className="text-[--muted] mb-2">No events found for {selectedTicker}</p>
            <p className="text-sm text-[--muted]">
              {modelVersion === 'v2.0' 
                ? 'No ML-scored events found in the last 90 days for this ticker'
                : 'No events found in the last 90 days for this ticker'
              }
            </p>
          </div>
        )}

        {/* Footer Stats */}
        {filteredTickerEvents.length > 0 && (
          <div className="flex items-center justify-between text-sm text-[--muted] bg-[--surface-muted] rounded-lg p-4">
            <div>
              Found <span className="font-semibold text-[--text]">{filteredTickerEvents.length}</span> events for {selectedTicker}
              {modelVersion === 'v2.0' && tickerEvents.length !== filteredTickerEvents.length && (
                <span className="ml-2 text-xs">
                  ({tickerEvents.length - filteredTickerEvents.length} non-ML events hidden)
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-2xl font-bold text-[--text]">Event Correlation Patterns</h2>
          <p className="text-sm text-[--muted]">
            Discover common event sequences to anticipate follow-on events
          </p>
        </div>
        <div className="flex items-center gap-4 flex-wrap">
          <ModelVersionFilter value={modelVersion} onChange={setModelVersion} />
          <div className="flex gap-2">
            <Button
              onClick={() => loadPatterns()}
              variant="outline"
              className="flex items-center gap-2"
            >
              <RefreshCw className="h-4 w-4" />
              Refresh
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

      {/* Info Banner */}
      <div className="bg-[--primary-light] border border-[--border-strong] rounded-lg p-4">
        <div className="flex items-start gap-3">
          <Info className="h-5 w-5 text-[--primary] mt-0.5 flex-shrink-0" />
          <div className="text-sm text-[--text]">
            <p className="font-semibold text-[--primary] mb-1">How to use correlation patterns:</p>
            <ul className="space-y-1 text-[--muted]">
              <li>• Patterns show common event sequences (e.g., "SEC 8-K → Earnings")</li>
              <li>• High frequency patterns are more reliable predictors</li>
              <li>• Use avg days between to anticipate timing of follow-on events</li>
              <li>• Click on example tickers to research historical occurrences</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Filters */}
      {showFilters && (
        <div className="bg-[--surface-muted] rounded-lg p-6 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-[--text] mb-2">
                Event Type Filter
              </label>
              <select
                value={eventType}
                onChange={(e) => setEventType(e.target.value)}
                className="w-full px-3 py-2 bg-[--input-bg] border border-[--input-border] rounded-lg text-[--text]"
              >
                <option value="">All Event Types</option>
                <option value="sec_8k">SEC 8-K</option>
                <option value="sec_10q">SEC 10-Q</option>
                <option value="fda_approval">FDA Approval</option>
                <option value="earnings">Earnings</option>
                <option value="ma_activity">M&A Activity</option>
                <option value="product_launch">Product Launch</option>
                <option value="guidance">Guidance</option>
                <option value="dividend">Dividend</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-[--text] mb-2">
                Time Window (days): {daysWindow}
              </label>
              <input
                type="range"
                min="7"
                max="180"
                step="7"
                value={daysWindow}
                onChange={(e) => setDaysWindow(parseInt(e.target.value))}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-[--muted] mt-1">
                <span>7 days</span>
                <span>180 days</span>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-[--text] mb-2">
                Min Frequency: {minFrequency}
              </label>
              <input
                type="range"
                min="1"
                max="20"
                step="1"
                value={minFrequency}
                onChange={(e) => setMinFrequency(parseInt(e.target.value))}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-[--muted] mt-1">
                <span>1 occurrence</span>
                <span>20 occurrences</span>
              </div>
            </div>
          </div>

          <div className="flex gap-3">
            <Button onClick={handleApplyFilters}>Apply Filters</Button>
            <Button onClick={handleReset} variant="outline">Reset</Button>
          </div>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
          <p className="text-[--error]">{error}</p>
        </div>
      )}

      {/* Loading State */}
      {loading && patterns.length > 0 && (
        <p className="text-sm text-[--muted]">Updating patterns...</p>
      )}

      {/* Empty State */}
      {!loading && !error && patterns.length === 0 && (
        <div className="text-center py-12 bg-[--surface-muted] rounded-lg">
          <TrendingUp className="h-12 w-12 text-[--muted] mx-auto mb-4" />
          <p className="text-[--muted] mb-2">No event patterns found</p>
          <p className="text-sm text-[--muted]">
            Try adjusting your filters or reducing the minimum frequency
          </p>
        </div>
      )}

      {/* Patterns Table */}
      {!loading && !error && patterns.length > 0 && (
        <div>
          <div className="bg-[--surface-muted] rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-[--surface-glass] border-b border-[--border]">
                  <tr>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-[--text]">
                      Pattern
                    </th>
                    <th className="px-6 py-4 text-center text-sm font-semibold text-[--text]">
                      Frequency
                    </th>
                    <th className="px-6 py-4 text-center text-sm font-semibold text-[--text]">
                      Avg Days Between
                    </th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-[--text]">
                      Tickers
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[--border]">
                  {patterns
                    .slice((patternsPage - 1) * patternsPerPage, patternsPage * patternsPerPage)
                    .map((pattern, index) => (
                    <tr
                      key={index}
                      className="hover:bg-[--surface-hover] transition-colors"
                    >
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <div className="font-mono text-sm text-[--text] bg-blue-500/20 px-3 py-1.5 rounded border border-blue-500/30">
                          {pattern.pattern}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-center">
                      <span className="inline-flex items-center px-3 py-1 bg-[--success-soft] border border-[--border-strong] rounded text-[--success] font-semibold">
                        {pattern.frequency}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-center">
                      <span className="text-[--text] font-medium">
                        {pattern.avg_days_between} days
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-wrap gap-2">
                        {pattern.example_tickers.slice(0, 5).map((ticker, i) => (
                          <button
                            key={i}
                            onClick={() => handleTickerClick(ticker)}
                            disabled={loadingTicker === ticker}
                            className="px-2 py-1 bg-[--surface-glass] rounded text-sm text-[--muted] hover:bg-[--surface-hover] hover:text-[--primary] transition-colors cursor-pointer border border-transparent disabled:opacity-50 disabled:cursor-wait"
                            title={`Click to load correlation history for ${ticker}`}
                          >
                            {loadingTicker === ticker ? '...' : ticker}
                          </button>
                        ))}
                        {pattern.example_tickers.length > 5 && (
                          <span className="px-2 py-1 bg-[--surface-glass] rounded text-sm text-[--muted]">
                            +{pattern.example_tickers.length - 5} more
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Pagination Controls */}
        {patterns.length > patternsPerPage && (
          <div className="flex items-center justify-between bg-[--surface-muted] rounded-lg p-4">
            <div className="text-sm text-[--muted]">
              Showing {Math.min((patternsPage - 1) * patternsPerPage + 1, patterns.length)} - {Math.min(patternsPage * patternsPerPage, patterns.length)} of {patterns.length} patterns
            </div>
            <div className="flex gap-2">
              <Button
                onClick={() => setPatternsPage(prev => Math.max(1, prev - 1))}
                disabled={patternsPage === 1}
                variant="outline"
                size="sm"
              >
                Previous
              </Button>
              <div className="flex items-center gap-2 px-3">
                <span className="text-sm text-[--text]">
                  Page {patternsPage} of {Math.ceil(patterns.length / patternsPerPage)}
                </span>
              </div>
              <Button
                onClick={() => setPatternsPage(prev => Math.min(Math.ceil(patterns.length / patternsPerPage), prev + 1))}
                disabled={patternsPage >= Math.ceil(patterns.length / patternsPerPage)}
                variant="outline"
                size="sm"
              >
                Next
              </Button>
            </div>
          </div>
        )}

        {/* Footer Stats */}
        <div className="flex items-center justify-between text-sm text-[--muted] bg-[--surface-muted] rounded-lg p-4">
          <div>
            Found <span className="font-semibold text-[--text]">{patterns.length}</span> event patterns
          </div>
          <div className="flex items-center gap-2">
            <span>
              Total occurrences: <span className="font-semibold text-[--text]">
                {patterns.reduce((sum, p) => sum + p.frequency, 0)}
              </span>
            </span>
            <Tooltip content="Total occurrences is the sum of all pattern frequencies. This represents the total number of times all identified event patterns have occurred in the historical data. Higher numbers indicate more robust and reliable patterns.">
              <Info className="h-4 w-4 text-[--muted] hover:text-[--text] cursor-help" />
            </Tooltip>
          </div>
        </div>
        </div>
      )}
    </div>
  );
}
