'use client';

import { useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { api, Event, Company, ScannerStatus } from '@/lib/api';
import { TrendingUp, User, Activity, Database, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { ScorePill } from './ScorePill';
import { ImpactScoreBadge, DisplayVersion } from './ImpactScoreBadge';
import Link from 'next/link';
import { getServerFeatureFlags, FeatureFlags } from '@/lib/featureFlags';
import { format } from 'date-fns';

type ModalType = 'recent' | 'upcoming' | 'scanners' | 'companies' | null;

// Wave B: Score response interface
interface ScoreResponse {
  event_id: number;
  ticker: string;
  event_type: string;
  base_score: number;
  context_score: number;
  final_score: number;
  confidence: number;
  factors: {
    sector: number;
    volatility: number;
    earnings_proximity: number;
    market_mood: number;
    after_hours: number;
    duplicate_penalty: number;
  };
  rationale: string[];
  computed_at: string;
}

interface DashboardContentProps {
  onNavigate?: (tab: string) => void;
  modelVersion?: DisplayVersion;
}

export function DashboardContent({ onNavigate, modelVersion = 'v1.5' }: DashboardContentProps = {}) {
  const [events, setEvents] = useState<Event[]>([]);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [scanners, setScanners] = useState<ScannerStatus[]>([]);
  const [discoveries, setDiscoveries] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalType, setModalType] = useState<ModalType>(null);
  const [allCompanies, setAllCompanies] = useState<Company[]>([]);
  const [expandedCompany, setExpandedCompany] = useState<string | null>(null);
  const [companyEvents, setCompanyEvents] = useState<{ [ticker: string]: Event[] }>({});
  const [loadingEvents, setLoadingEvents] = useState<string | null>(null);
  // Wave B: Score fetching state
  const [eventScores, setEventScores] = useState<{ [eventId: number]: ScoreResponse | 'upgrade_required' | null }>({});
  const [loadingScores, setLoadingScores] = useState<string | null>(null);
  
  // Wave C: Scanner and company counts
  const [scannerCount, setScannerCount] = useState<number>(0);
  const [companyCount, setCompanyCount] = useState<number>(0);
  
  // Manual scan controls state
  const [selectedScanner, setSelectedScanner] = useState<string>('');
  const [scanJobs, setScanJobs] = useState<any[]>([]);
  const [isRescanning, setIsRescanning] = useState<boolean>(false);
  const [rescanningCompany, setRescanningCompany] = useState<string | null>(null);
  
  // Wave B: Sorting with querystring persistence
  const searchParams = useSearchParams();
  const router = useRouter();
  const [sortBy, setSortBy] = useState<string>(searchParams.get('sort') || 'date-newest');
  
  // Feature flags
  const [featureFlags, setFeatureFlags] = useState<FeatureFlags | null>(null);
  
  // Last scan metadata for Recent Events heading
  const [lastScanTime, setLastScanTime] = useState<string | null>(null);
  const [isAutomaticScan, setIsAutomaticScan] = useState<boolean>(false);
  
  useEffect(() => {
    getServerFeatureFlags().then(setFeatureFlags);
  }, []);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        
        // Use consolidated dashboard endpoint for faster loading (single API call)
        const dashboardData = await api.dashboard.init('watchlist');
        
        // Set all data from consolidated response
        setEvents(dashboardData.events as Event[]);
        setScanners(dashboardData.scanners);
        setScannerCount(dashboardData.scanner_count);
        setCompanyCount(dashboardData.company_count);
        setDiscoveries(dashboardData.discoveries);
        
        // Set last scan metadata
        if (dashboardData.last_scan?.started_at) {
          setLastScanTime(dashboardData.last_scan.started_at);
          setIsAutomaticScan(dashboardData.last_scan.is_automatic);
        }
        
        // Fetch companies separately (needed for modal) - lazy loaded
        api.companies.getAll({ with_event_counts: true }).then(setCompanies).catch(() => {});
        
        setError(null);
      } catch (err) {
        console.error('Failed to load dashboard data:', err);
        setError(err instanceof Error ? err.message : 'Failed to load data');
      } finally {
        setLoading(false);
      }
    }

    loadData();

    // Only set up SSE if feature flag is loaded
    if (featureFlags === null) {
      return;
    }

    // Conditionally use SSE or polling based on feature flag
    if (featureFlags.enableLiveWs) {
      console.log('Live WebSocket feature is enabled, using SSE stream for discoveries');
      const cleanup = api.scanners.streamDiscoveries(
        (data) => {
          // Map event_time to timestamp if needed for backward compatibility
          const normalizedData = {
            ...data,
            timestamp: data.timestamp || data.event_time || new Date().toISOString(),
          };
          setDiscoveries((prev) => [normalizedData, ...prev].slice(0, 10));
        },
        (error) => {
          console.error('SSE stream error:', error);
        }
      );
      return cleanup;
    } else {
      console.log('Live WebSocket feature is disabled, using polling fallback for discoveries');
      // Polling fallback: refresh discoveries every 30 seconds
      const pollDiscoveries = async () => {
        try {
          const latest = await api.scanners.getDiscoveries({ limit: 10 });
          setDiscoveries(latest);
        } catch (err) {
          console.error('Failed to poll discoveries:', err);
        }
      };

      // Initial poll
      pollDiscoveries();

      // Set up interval
      const interval = setInterval(pollDiscoveries, 30000);

      return () => clearInterval(interval);
    }
  }, [featureFlags]);

  // Poll for scan jobs when scanner modal is open
  useEffect(() => {
    if (modalType !== 'scanners') return;

    const pollJobs = async () => {
      try {
        const response = await api.scanners.getScanJobs({ limit: 25 });
        setScanJobs(response.jobs);
      } catch (error) {
        console.error('Failed to fetch scan jobs:', error);
      }
    };

    pollJobs();
    const interval = setInterval(pollJobs, 5000);

    return () => clearInterval(interval);
  }, [modalType]);

  const handleRescanScanner = async () => {
    if (!selectedScanner) {
      alert('Please select a scanner first');
      return;
    }

    setIsRescanning(true);
    try {
      const response = await api.scanners.rescanScanner(selectedScanner);
      alert(`Success: ${response.message}`);
      const jobsResponse = await api.scanners.getScanJobs({ limit: 25 });
      setScanJobs(jobsResponse.jobs);
    } catch (error: any) {
      const message = error?.message || 'Failed to enqueue rescan job';
      alert(`Error: ${message}`);
    } finally {
      setIsRescanning(false);
    }
  };

  const handleRescanCompany = async (ticker: string) => {
    setRescanningCompany(ticker);
    try {
      const response = await api.scanners.rescanCompany(ticker);
      alert(`Success: ${response.message}`);
    } catch (error: any) {
      const message = error?.message || 'Failed to enqueue company rescan';
      alert(`Error: ${message}`);
    } finally {
      setRescanningCompany(null);
    }
  };

  const upcomingEvents = events.filter(
    (e) => new Date(e.date) > new Date()
  ).length;

  const upcomingEventsList = events.filter(
    (e) => new Date(e.date) > new Date()
  ).slice(0, 10);

  const positiveEvents = events.filter((e) => e.direction === 'positive').length;

  const handleCardClick = async (type: ModalType) => {
    // Fetch fresh data for each modal type
    if (type === 'companies' && allCompanies.length === 0) {
      try {
        const data = await api.companies.getAll({ limit: 100, with_event_counts: true });
        setAllCompanies(data);
      } catch (err) {
        console.error('Failed to load all companies:', err);
      }
    } else if (type === 'upcoming') {
      // Fetch upcoming events (future only)
      try {
        const now = new Date().toISOString();
        const futureEvents = await api.events.getAll({ 
          from_date: now, 
          limit: 10 
        });
        // Update upcomingEventsList with fresh future events
        setEvents(prevEvents => {
          const pastEvents = prevEvents.filter(e => new Date(e.date) <= new Date());
          return [...pastEvents, ...futureEvents];
        });
      } catch (err) {
        console.error('Failed to load upcoming events:', err);
      }
    }
    setModalType(type);
  };

  const getDirectionColor = (direction: string) => {
    switch (direction) {
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

  const getImpactColor = (score: number) => {
    if (score >= 75) return 'bg-[--success]';
    if (score >= 50) return 'bg-[--primary]';
    if (score >= 25) return 'bg-[--warning]';
    return 'bg-[--error]';
  };

  const handleCompanyClick = async (ticker: string) => {
    // Toggle expansion
    if (expandedCompany === ticker) {
      setExpandedCompany(null);
      return;
    }

    setExpandedCompany(ticker);

    // Fetch events if not already cached
    if (!companyEvents[ticker]) {
      setLoadingEvents(ticker);
      try {
        const events = await api.companies.getEvents(ticker);
        setCompanyEvents(prev => ({ ...prev, [ticker]: events }));
        
        // Wave B: Fetch scores for all events
        setLoadingScores(ticker);
        const scorePromises = events.map(async (event) => {
          try {
            const response = await fetch(`/api/proxy/scores/events/${event.id}`);
            if (response.status === 402) {
              return { eventId: event.id, score: 'upgrade_required' as const };
            }
            if (response.ok) {
              const scoreData: ScoreResponse = await response.json();
              return { eventId: event.id, score: scoreData };
            }
            return { eventId: event.id, score: null };
          } catch (err) {
            console.error(`Failed to fetch score for event ${event.id}:`, err);
            return { eventId: event.id, score: null };
          }
        });

        const scoreResults = await Promise.all(scorePromises);
        const scoresMap: { [eventId: number]: ScoreResponse | 'upgrade_required' | null } = {};
        scoreResults.forEach(({ eventId, score }) => {
          scoresMap[eventId] = score;
        });
        
        setEventScores(prev => ({ ...prev, ...scoresMap }));
        setLoadingScores(null);
      } catch (err) {
        console.error(`Failed to load events for ${ticker}:`, err);
        setCompanyEvents(prev => ({ ...prev, [ticker]: [] }));
        setLoadingEvents(null);
      } finally {
        setLoadingEvents(null);
      }
    }
  };

  const getProjectionColor = (direction: string, is_uncertain?: boolean) => {
    if (is_uncertain) return 'text-[--neutral]';
    switch (direction) {
      case 'positive':
        return 'text-[--success]';
      case 'negative':
        return 'text-[--error]';
      default:
        return 'text-[--neutral]';
    }
  };

  // Wave B: Sort events by selected option
  const sortEvents = (events: Event[]) => {
    if (!events) return [];
    const sorted = [...events];
    
    switch (sortBy) {
      case 'date-newest':
        return sorted.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
      case 'date-oldest':
        return sorted.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
      case 'score-highest':
        return sorted.sort((a, b) => {
          const scoreA = typeof eventScores[a.id] === 'object' && eventScores[a.id] !== null ? (eventScores[a.id] as ScoreResponse).final_score : 0;
          const scoreB = typeof eventScores[b.id] === 'object' && eventScores[b.id] !== null ? (eventScores[b.id] as ScoreResponse).final_score : 0;
          return scoreB - scoreA;
        });
      case 'score-lowest':
        return sorted.sort((a, b) => {
          const scoreA = typeof eventScores[a.id] === 'object' && eventScores[a.id] !== null ? (eventScores[a.id] as ScoreResponse).final_score : 0;
          const scoreB = typeof eventScores[b.id] === 'object' && eventScores[b.id] !== null ? (eventScores[b.id] as ScoreResponse).final_score : 0;
          return scoreA - scoreB;
        });
      default:
        return sorted;
    }
  };

  const handleSortChange = (value: string) => {
    setSortBy(value);
    const params = new URLSearchParams(searchParams);
    params.set('sort', value);
    router.push(`?${params.toString()}`, { scroll: false });
  };

  if (error) {
    return (
      <div className="rounded-3xl border border-[--border] bg-[--error-light] p-8 text-center">
        <h2 className="text-2xl font-semibold text-[--error] mb-4">
          Connection Error
        </h2>
        <p className="text-lg text-[--error] mb-4">
          {error}
        </p>
        <p className="text-sm text-[--muted]">
          Make sure the FastAPI backend is running on port 8080.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
        {/* KPI Cards */}
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        <button
          onClick={() => handleCardClick('recent')}
          className="rounded-2xl border border-[--border] bg-[--panel] p-6 text-left hover:border-[--border-strong] hover:bg-[--surface-hover] transition-all cursor-pointer"
        >
          <div className="flex items-center justify-between mb-4">
            <span className="text-[--success]">
              <TrendingUp className="h-6 w-6" />
            </span>
          </div>
          <div className="text-3xl font-bold text-[--text] mb-1">
            {loading ? '...' : events.length}
          </div>
          <div className="text-sm text-[--muted]">Recent Events</div>
        </button>

        <button
          onClick={() => onNavigate?.('account')}
          className="rounded-2xl border border-[--border] bg-[--panel] p-6 text-left hover:border-[--border-strong] hover:bg-[--surface-hover] transition-all cursor-pointer"
        >
          <div className="flex items-center justify-between mb-4">
            <span className="text-[--primary]">
              <User className="h-6 w-6" />
            </span>
          </div>
          <div className="text-3xl font-bold text-[--text] mb-1">
            Account
          </div>
          <div className="text-sm text-[--muted]">View Settings</div>
        </button>

        <button
          onClick={() => handleCardClick('scanners')}
          className="rounded-2xl border border-[--border] bg-[--panel] p-6 text-left hover:border-[--border-strong] hover:bg-[--surface-hover] transition-all cursor-pointer"
        >
          <div className="flex items-center justify-between mb-4">
            <span className="text-[--warning]">
              <Activity className="h-6 w-6" />
            </span>
          </div>
          <div className="text-3xl font-bold text-[--text] mb-1">
            {loading ? '...' : scannerCount}
          </div>
          <div className="text-sm text-[--muted]">Active Scanners</div>
        </button>

        <button
          onClick={() => handleCardClick('companies')}
          className="rounded-2xl border border-[--border] bg-[--panel] p-6 text-left hover:border-[--border-strong] hover:bg-[--surface-hover] transition-all cursor-pointer"
        >
          <div className="flex items-center justify-between mb-4">
            <span className="text-[--accent]">
              <Database className="h-6 w-6" />
            </span>
          </div>
          <div className="text-3xl font-bold text-[--text] mb-1">
            {loading ? '...' : companyCount}
          </div>
          <div className="text-sm text-[--muted]">Companies Tracked</div>
        </button>
      </div>

      {/* Live Discoveries Feed */}
      {discoveries.length > 0 && (
        <div className="rounded-2xl border border-[--border] bg-[--success-light] p-6">
          <h3 className="text-lg font-semibold text-[--text] mb-4 flex items-center gap-2">
            <Activity className="h-5 w-5 text-[--success] animate-pulse" />
            Live Discoveries
          </h3>
          <div className="space-y-2">
            {discoveries.slice(0, 5).map((discovery, i) => {
              // Validate timestamp before displaying
              const timestamp = discovery.timestamp;
              const isValidDate = timestamp && !isNaN(new Date(timestamp).getTime());
              const timeDisplay = isValidDate 
                ? new Date(timestamp).toLocaleTimeString()
                : 'Just now';
              
              return (
                <div
                  key={i}
                  className="flex items-center gap-3 text-sm p-3 rounded-lg bg-[--panel] border border-[--border-muted]"
                >
                  <span className="text-[--success] font-mono">{discovery.ticker}</span>
                  <span className="text-[--muted]">{discovery.title}</span>
                  <span className="ml-auto text-xs text-[--muted]">
                    {timeDisplay}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Scanner Status */}
      <div className="rounded-2xl border border-[--border] bg-[--panel] p-6">
        <h3 className="text-lg font-semibold text-[--text] mb-4">
          Scanner Status
        </h3>
        <div className="space-y-3">
          {loading ? (
            <div className="space-y-1">
              <p className="text-[--muted]">Loading scanner status...</p>
            </div>
          ) : scanners.length === 0 ? (
            <p className="text-[--muted]">No scanner data available</p>
          ) : (
            scanners.map((scanner, i) => (
              <div
                key={i}
                className="flex items-center justify-between p-3 rounded-lg bg-[--surface-strong] border border-[--border-muted]"
              >
                <div>
                  <div className="font-semibold text-[--text] uppercase">
                    {scanner.scanner}
                  </div>
                  <div className="text-sm text-[--muted]">
                    {scanner.message || 'No message'}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`text-xs px-2 py-1 rounded ${
                      scanner.level === 'error'
                        ? 'bg-[--error-soft] text-[--error]'
                        : scanner.level === 'warning'
                        ? 'bg-[--warning-soft] text-[--warning]'
                        : 'bg-[--success-soft] text-[--success]'
                    }`}
                  >
                    {scanner.level}
                  </span>
                  {scanner.last_run && (
                    <span className="text-xs text-[--muted]">
                      {new Date(scanner.last_run).toLocaleString()}
                    </span>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Recent Events Table */}
      <div className="rounded-2xl border border-[--border] bg-[--panel] p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-[--text]">
            Recent Events
            {isAutomaticScan && lastScanTime && (
              <span className="text-sm font-normal text-[--muted] ml-2">
                (Automatic Scan {format(new Date(lastScanTime), 'h:mm a')})
              </span>
            )}
          </h3>
          <Button size="sm" variant="outline" asChild>
            <Link href="/events">View All</Link>
          </Button>
        </div>

        {(() => {
          const filteredEvents = modelVersion === 'v2.0'
            ? events.filter(e => (e as any).model_source && (e as any).model_source !== 'deterministic' && (e as any).ml_adjusted_score != null)
            : events;
          
          if (loading) {
            return (
              <div className="space-y-1">
                <p className="text-[--muted]">Loading events...</p>
              </div>
            );
          }
          
          if (filteredEvents.length === 0) {
            return (
              <p className="text-[--muted]">
                {modelVersion === 'v2.0'
                  ? 'No events with Market Echo ML scores found. Try switching to V1.5 (Hybrid) for full coverage.'
                  : 'No events found'}
              </p>
            );
          }
          
          return (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[--border]">
                    <th className="text-left py-3 px-4 text-sm font-medium text-[--muted]">
                      Ticker
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-[--muted]">
                      Event
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-[--muted]">
                      Type
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-[--muted]">
                      Impact
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-[--muted]">
                      Direction
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-[--muted]">
                      Date
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-[--muted]">
                      Source
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {filteredEvents.slice(0, 10).map((event) => (
                    <tr
                      key={event.id}
                      className="border-b border-[--border-muted] hover:bg-[--surface-hover] transition-colors"
                    >
                      <td className="py-3 px-4">
                        <span className="font-mono font-semibold text-[--text]">
                          {event.ticker}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <div className="max-w-xs">
                          <div className="text-sm text-[--text] truncate">
                            {event.title}
                          </div>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <span className="text-xs px-2 py-1 rounded bg-[--primary-soft] text-[--primary]">
                          {event.event_type}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <ImpactScoreBadge
                          baseScore={event.impact_score}
                          mlAdjustedScore={(event as any).ml_adjusted_score}
                          mlConfidence={(event as any).ml_confidence}
                          modelSource={(event as any).model_source}
                          modelVersion={(event as any).ml_model_version}
                          compact={true}
                          showDelta={modelVersion !== 'v1.0'}
                          displayVersion={modelVersion}
                        />
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`text-sm font-medium ${getDirectionColor(
                            event.direction
                          )}`}
                        >
                          {event.direction}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span className="text-sm text-[--muted]">
                          {new Date(event.date).toLocaleDateString()}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        {event.source_url ? (
                          <a
                            href={event.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[--primary] hover:text-[--primary] transition-colors"
                          >
                            <ExternalLink className="h-4 w-4" />
                          </a>
                        ) : (
                          <span className="text-xs text-[--muted]">
                            {event.source}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        })()}
      </div>

      {/* Modals */}
      <Dialog open={modalType === 'recent'} onOpenChange={() => setModalType(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Recent Events (Last 10)</DialogTitle>
          </DialogHeader>
          <div className="space-y-2 mt-4">
            {(() => {
              const filteredRecentEvents = modelVersion === 'v2.0'
                ? events.filter(e => (e as any).model_source && (e as any).model_source !== 'deterministic' && (e as any).ml_adjusted_score != null)
                : events;
              
              if (filteredRecentEvents.length === 0) {
                return (
                  <p className="text-[--muted] text-center py-8">
                    {modelVersion === 'v2.0'
                      ? 'No events with Market Echo ML scores found.'
                      : 'No recent events found'}
                  </p>
                );
              }
              
              return filteredRecentEvents.slice(0, 10).map((event) => (
                <div
                  key={event.id}
                  className="p-4 rounded-lg bg-[--surface-strong] border border-[--border-muted] hover:bg-[--surface-hover] transition-colors"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <span className="font-mono font-semibold text-[--text]">
                          {event.ticker}
                        </span>
                        <span className="text-xs px-2 py-1 rounded bg-[--primary-soft] text-[--primary]">
                          {event.event_type}
                        </span>
                        <ImpactScoreBadge
                          baseScore={event.impact_score}
                          mlAdjustedScore={(event as any).ml_adjusted_score}
                          mlConfidence={(event as any).ml_confidence}
                          modelSource={(event as any).model_source}
                          modelVersion={(event as any).ml_model_version}
                          compact={true}
                          showDelta={modelVersion !== 'v1.0'}
                          displayVersion={modelVersion}
                        />
                      </div>
                      <div className="text-sm text-[--text] mb-2">
                        {event.title}
                      </div>
                      <div className="flex items-center gap-3 text-xs">
                        <span className="text-[--muted]">
                          {new Date(event.date).toLocaleDateString()}
                        </span>
                        <span className={`font-medium ${getDirectionColor(event.direction)}`}>
                          {event.direction}
                        </span>
                      </div>
                    </div>
                    {event.source_url && (
                      <a
                        href={event.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[--primary] hover:text-[--primary] ml-2"
                      >
                        <ExternalLink className="h-4 w-4" />
                      </a>
                    )}
                  </div>
                </div>
              ));
            })()}
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={modalType === 'upcoming'} onOpenChange={() => setModalType(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Upcoming Events (Next 10)</DialogTitle>
          </DialogHeader>
          <div className="space-y-2 mt-4">
            {(() => {
              const filteredUpcomingEvents = modelVersion === 'v2.0'
                ? upcomingEventsList.filter(e => (e as any).model_source && (e as any).model_source !== 'deterministic' && (e as any).ml_adjusted_score != null)
                : upcomingEventsList;
              
              if (filteredUpcomingEvents.length === 0) {
                return (
                  <p className="text-[--muted] text-center py-8">
                    {modelVersion === 'v2.0'
                      ? 'No upcoming events with Market Echo ML scores found.'
                      : 'No upcoming events found'}
                  </p>
                );
              }
              
              return filteredUpcomingEvents.map((event) => (
                <div
                  key={event.id}
                  className="p-4 rounded-lg bg-[--surface-strong] border border-[--border-muted] hover:bg-[--surface-hover] transition-colors"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <span className="font-mono font-semibold text-[--text]">
                          {event.ticker}
                        </span>
                        <span className="text-xs px-2 py-1 rounded bg-[--primary-soft] text-[--primary]">
                          {event.event_type}
                        </span>
                        <ImpactScoreBadge
                          baseScore={event.impact_score}
                          mlAdjustedScore={(event as any).ml_adjusted_score}
                          mlConfidence={(event as any).ml_confidence}
                          modelSource={(event as any).model_source}
                          modelVersion={(event as any).ml_model_version}
                          compact={true}
                          showDelta={modelVersion !== 'v1.0'}
                          displayVersion={modelVersion}
                        />
                      </div>
                      <div className="text-sm text-[--text] mb-2">
                        {event.title}
                      </div>
                      <div className="flex items-center gap-3 text-xs">
                        <span className="text-[--muted]">
                          {new Date(event.date).toLocaleDateString()}
                        </span>
                        <span className={`font-medium ${getDirectionColor(event.direction)}`}>
                          {event.direction}
                        </span>
                      </div>
                    </div>
                    {event.source_url && (
                      <a
                        href={event.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[--primary] hover:text-[--primary] ml-2"
                      >
                        <ExternalLink className="h-4 w-4" />
                      </a>
                    )}
                  </div>
                </div>
              ));
            })()}
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={modalType === 'scanners'} onOpenChange={() => setModalType(null)}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Scanner Status & Manual Controls</DialogTitle>
          </DialogHeader>
          
          <div className="space-y-6 mt-4">
            <div>
              <h3 className="text-sm font-semibold text-[--text] mb-3">Active Scanners</h3>
              <div className="space-y-3">
                {scanners.map((scanner, i) => (
                  <div
                    key={i}
                    className="p-4 rounded-lg bg-[--surface-strong] border border-[--border-muted]"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="font-semibold text-[--text] mb-1 uppercase">
                          {scanner.scanner}
                        </div>
                        <div className="text-sm text-[--muted] mb-2">
                          {scanner.message || 'No message'}
                        </div>
                        {scanner.last_run && (
                          <div className="text-xs text-[--muted]">
                            Last run: {new Date(scanner.last_run).toLocaleString()}
                          </div>
                        )}
                        {scanner.next_run && (
                          <div className="text-xs text-[--muted]">
                            Next run: {new Date(scanner.next_run).toLocaleString()}
                          </div>
                        )}
                        <div className="text-xs text-[--muted] mt-1">
                          Discoveries: {scanner.discoveries || 0}
                        </div>
                      </div>
                      <span
                        className={`text-xs px-3 py-1 rounded ${
                          scanner.level === 'error'
                            ? 'bg-[--error-soft] text-[--error]'
                            : scanner.level === 'warning'
                            ? 'bg-[--warning-soft] text-[--warning]'
                            : 'bg-[--success-soft] text-[--success]'
                        }`}
                      >
                        {scanner.level}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="border-t border-[--border] pt-6">
              <h3 className="text-sm font-semibold text-[--text] mb-3">Manual Scan Controls</h3>
              <div className="flex gap-3 items-center">
                <select
                  value={selectedScanner}
                  onChange={(e) => setSelectedScanner(e.target.value)}
                  className="flex-1 px-3 py-2 bg-[--surface-strong] border border-[--border] rounded text-[--text] text-sm"
                >
                  <option value="">Select a scanner...</option>
                  <option value="sec_edgar">SEC EDGAR</option>
                  <option value="fda_announcements">FDA Announcements</option>
                  <option value="company_press">Press Releases</option>
                  <option value="earnings_calls">Earnings Calls</option>
                  <option value="sec_8k">SEC 8-K</option>
                  <option value="sec_10q">SEC 10-Q</option>
                  <option value="guidance_updates">Guidance Updates</option>
                  <option value="product_launch">Product Launches</option>
                  <option value="ma_activity">M&A & Strategic</option>
                  <option value="dividend_buyback">Dividends & Buybacks</option>
                </select>
                <button
                  onClick={handleRescanScanner}
                  disabled={!selectedScanner || isRescanning}
                  className="px-4 py-2 bg-[--accent] hover:bg-[--surface-hover] disabled:bg-[--muted-soft] disabled:cursor-not-allowed text-[--text-on-primary] rounded text-sm font-medium transition-colors"
                >
                  {isRescanning ? 'Queueing...' : 'Queue Manual Scan'}
                </button>
              </div>
              <p className="text-xs text-[--muted] mt-2">
                Rate limit: 1 scan per 2 minutes
              </p>
            </div>

            <div className="border-t border-[--border] pt-6">
              <h3 className="text-sm font-semibold text-[--text] mb-3">Recent Scan Jobs ({scanJobs.length})</h3>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {scanJobs.length === 0 ? (
                  <p className="text-sm text-[--muted]">No recent jobs</p>
                ) : (
                  scanJobs.map((job) => (
                    <div
                      key={job.id}
                      className="p-3 rounded-lg bg-[--surface-strong] border border-[--border-muted] text-sm"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-[--text]">
                            {job.scope === 'company' ? `Company: ${job.ticker}` : `Scanner: ${job.scanner_key}`}
                          </span>
                          <span
                            className={`text-xs px-2 py-0.5 rounded ${
                              job.status === 'success'
                                ? 'bg-[--success-soft] text-[--success]'
                                : job.status === 'error'
                                ? 'bg-[--error-soft] text-[--error]'
                                : job.status === 'running'
                                ? 'bg-[--primary-soft] text-[--primary]'
                                : 'bg-[--warning-soft] text-[--warning]'
                            }`}
                          >
                            {job.status}
                          </span>
                        </div>
                        {job.items_found !== null && job.items_found !== undefined && (
                          <span className="text-xs text-[--muted]">
                            Found: {job.items_found} items
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-4 text-xs text-[--muted]">
                        <span>Created: {new Date(job.created_at).toLocaleString()}</span>
                        {job.finished_at && job.started_at && (
                          <span>
                            Duration: {Math.round((new Date(job.finished_at).getTime() - new Date(job.started_at).getTime()) / 1000)}s
                          </span>
                        )}
                      </div>
                      {job.error && (
                        <div className="mt-2 text-xs text-[--error]">
                          Error: {job.error}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={modalType === 'companies'} onOpenChange={() => setModalType(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Companies Tracked (Top 100)</DialogTitle>
          </DialogHeader>
          <div className="space-y-2 mt-4 max-h-[60vh] overflow-y-auto">
            {(allCompanies.length > 0 ? allCompanies : companies).map((company) => (
              <div
                key={company.ticker}
                className="rounded-lg bg-[--surface-strong] border border-[--border-muted] overflow-hidden"
              >
                <div
                  onClick={() => handleCompanyClick(company.ticker)}
                  className="p-3 hover:bg-[--surface-hover] transition-colors cursor-pointer"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="text-lg">{expandedCompany === company.ticker ? '▼' : '▶'}</span>
                      <div>
                        <div className="font-mono font-semibold text-[--text]">
                          {company.ticker}
                        </div>
                        <div className="text-sm text-[--muted]">
                          {company.name}
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs text-[--muted]">
                        Events: {company.event_count || 0}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Expanded events */}
                {expandedCompany === company.ticker && (
                  <div className="border-t border-[--border-muted] p-4 bg-[--surface-strong]">
                    {loadingEvents === company.ticker ? (
                      <div className="space-y-3">
                        {/* Loading skeleton */}
                        {[1, 2, 3].map((i) => (
                          <div key={i} className="p-3 rounded-lg bg-[--panel] border border-[--border-muted] animate-pulse">
                            <div className="flex items-start justify-between gap-4">
                              <div className="flex-1 space-y-2">
                                <div className="h-4 bg-[--surface-glass] rounded w-3/4" />
                                <div className="flex gap-2">
                                  <div className="h-3 bg-[--surface-glass] rounded w-20" />
                                  <div className="h-3 bg-[--surface-glass] rounded w-24" />
                                </div>
                              </div>
                              <div className="flex flex-col gap-1">
                                <div className="h-5 w-16 bg-[--surface-glass] rounded" />
                                <div className="h-1 w-16 bg-[--surface-glass] rounded-full" />
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : companyEvents[company.ticker]?.length === 0 ? (
                      <div className="text-center py-8 px-4">
                        <div className="text-[--muted] mb-2">No scored events yet</div>
                        <div className="text-sm text-[--muted]">
                          New events appear here within ~60s of publication
                        </div>
                      </div>
                    ) : (
                      <>
                        {/* Historical Stats Indicator */}
                        {companyEvents[company.ticker]?.some((e) => e.projected_move && e.projected_move !== 'uncertain') ? (
                          <div className="text-[--success] text-sm mb-3 px-3 py-2 rounded bg-[--success-light] border border-[--border]">
                            Historical stats available ({companyEvents[company.ticker].filter((e) => e.projected_move).length} events)
                          </div>
                        ) : (
                          <div className="text-[--muted] text-sm mb-3 px-3 py-2 rounded bg-[--muted-light] border border-[--border]">
                            Insufficient price data for historical analysis yet
                          </div>
                        )}
                        
                        {/* Wave B: Sort Dropdown and Rescan Button */}
                        <div className="mb-3 flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <label className="text-sm text-[--muted]">Sort by:</label>
                            <select
                              value={sortBy}
                              onChange={(e) => handleSortChange(e.target.value)}
                              className="px-3 py-1.5 text-sm bg-[--panel] border border-[--border] rounded text-[--text] focus:outline-none focus:ring-2 focus:ring-[--primary]"
                            >
                              <option value="date-newest">Date (Newest)</option>
                              <option value="date-oldest">Date (Oldest)</option>
                              <option value="score-highest">Score (Highest)</option>
                              <option value="score-lowest">Score (Lowest)</option>
                            </select>
                          </div>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleRescanCompany(company.ticker);
                            }}
                            disabled={rescanningCompany === company.ticker}
                            className="px-3 py-1.5 text-sm bg-[--accent] hover:bg-[--surface-hover] disabled:bg-[--muted-soft] disabled:cursor-not-allowed text-[--text-on-primary] rounded font-medium transition-colors"
                          >
                            {rescanningCompany === company.ticker ? 'Queueing...' : 'Rescan Company'}
                          </button>
                        </div>
                        
                        <div className="space-y-3">
                          {sortEvents(companyEvents[company.ticker] || []).map((event) => (
                          <div
                            key={event.id}
                            className="p-3 rounded-lg bg-[--panel] border border-[--border-muted]"
                          >
                            <div className="flex items-start justify-between gap-4">
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 mb-1 flex-wrap">
                                  <span className="text-sm font-medium text-[--text] truncate">
                                    {event.title}
                                  </span>
                                  {event.projected_move && (
                                    <span
                                      className={`text-sm font-bold ${getProjectionColor(event.direction, event.is_uncertain)}`}
                                      title={`Confidence: ${Math.round(event.confidence * 100)}%`}
                                    >
                                      {event.projected_move}
                                    </span>
                                  )}
                                  {/* Wave B: Score Pill */}
                                  <ScorePill 
                                    score={eventScores[event.id]} 
                                    loading={loadingScores === company.ticker && !eventScores[event.id]}
                                  />
                                </div>
                                <div className="flex items-center gap-3 text-xs text-[--muted]">
                                  <span>
                                    {new Date(event.date).toLocaleDateString('en-US', {
                                      month: 'short',
                                      day: 'numeric',
                                      year: 'numeric'
                                    })}
                                  </span>
                                  <span className="px-2 py-0.5 rounded bg-[--primary-soft] text-[--primary]">
                                    {event.event_type}
                                  </span>
                                </div>
                              </div>
                              {event.source_url && (
                                <a
                                  href={event.source_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-[--primary] hover:text-[--primary] transition-colors flex-shrink-0"
                                  title="View source"
                                >
                                  <ExternalLink className="h-4 w-4" />
                                </a>
                              )}
                            </div>
                          </div>
                          ))}
                        </div>
                      </>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
