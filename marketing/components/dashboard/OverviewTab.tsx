'use client';

import { useEffect, useState, useCallback } from 'react';
import { 
  TrendingUp, 
  TrendingDown, 
  Calendar, 
  DollarSign, 
  User,
  ArrowUpRight,
  ArrowDownRight,
  Clock,
  Zap,
  Target,
  ChevronRight,
  Loader2,
  AlertCircle,
  BarChart3,
  Activity,
  Shield
} from 'lucide-react';
import { portfolioAPI, type PortfolioInsightsEvent, type Event } from '@/lib/api';

interface OverviewTabProps {
  onNavigate?: (tab: string) => void;
}

interface PortfolioSummary {
  total_value: number;
  total_cost: number;
  total_change_pct: number;
  total_change_dollars: number;
  positions_count: number;
}

interface ImpactfulStock {
  ticker: string;
  company_name: string;
  change_pct: number;
  change_dollars: number;
  impact_score: number;
  direction: string;
  event_title: string;
  event_type: string;
}

interface UpcomingMilestone {
  date: string;
  ticker: string;
  event_type: string;
  headline: string;
  projected_move_pct: number;
  projected_move_dollars: number;
  direction: string;
  days_until: number;
}

interface MarketRegime {
  regime: string;
  confidence: number;
  volatility: number | null;
  avg_correlation: number | null;
  breadth: number | null;
  message: string;
}

export function OverviewTab({ onNavigate }: OverviewTabProps = {}) {
  const [loading, setLoading] = useState(true);
  const [portfolioSummary, setPortfolioSummary] = useState<PortfolioSummary | null>(null);
  const [impactfulStocks, setImpactfulStocks] = useState<ImpactfulStock[]>([]);
  const [upcomingMilestones, setUpcomingMilestones] = useState<UpcomingMilestone[]>([]);
  const [recentEvents, setRecentEvents] = useState<Event[]>([]);
  const [marketRegime, setMarketRegime] = useState<MarketRegime | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchOverviewData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [holdingsRes, performanceRes, insightsRes, eventsRes, regimeRes] = await Promise.allSettled([
        fetch('/api/proxy/portfolio/holdings', { credentials: 'include' }),
        fetch('/api/proxy/account/performance', { credentials: 'include' }),
        portfolioAPI.insights({ days_ahead: 30 }).catch(() => ({ events: [] })),
        fetch('/api/proxy/events/public?limit=10', { credentials: 'include' }),
        fetch('/api/proxy/analytics/market-regime', { credentials: 'include' })
      ]);
      
      if (regimeRes.status === 'fulfilled' && regimeRes.value.ok) {
        const regimeData = await regimeRes.value.json();
        setMarketRegime(regimeData);
      }

      let totalValue = 0;
      let totalCost = 0;
      let positionsCount = 0;

      if (holdingsRes.status === 'fulfilled' && holdingsRes.value.ok) {
        const holdings = await holdingsRes.value.json();
        if (Array.isArray(holdings)) {
          positionsCount = holdings.length;
          for (const holding of holdings) {
            const shares = holding.shares || 0;
            const costBasis = holding.cost_basis || 0;
            const marketValue = holding.market_value || (shares * costBasis);
            totalCost += shares * costBasis;
            totalValue += marketValue;
          }
        }
      }

      if (performanceRes.status === 'fulfilled' && performanceRes.value.ok) {
        const perfData = await performanceRes.value.json();
        if (perfData.total_portfolio_value && perfData.total_portfolio_value > 0 && totalValue === 0) {
          totalValue = perfData.total_portfolio_value;
        }
        if (perfData.total_positions && perfData.total_positions > 0 && positionsCount === 0) {
          positionsCount = perfData.total_positions;
        }
      }

      if (totalValue === 0 && totalCost > 0) {
        totalValue = totalCost;
      }

      const totalChangeDollars = totalValue - totalCost;
      const totalChangePct = totalCost > 0 ? ((totalValue - totalCost) / totalCost) * 100 : 0;

      setPortfolioSummary({
        total_value: totalValue,
        total_cost: totalCost,
        total_change_pct: totalChangePct,
        total_change_dollars: totalChangeDollars,
        positions_count: positionsCount
      });

      let events: Event[] = [];
      if (eventsRes.status === 'fulfilled' && eventsRes.value.ok) {
        const eventsData = await eventsRes.value.json();
        events = Array.isArray(eventsData) ? eventsData : (eventsData.events || []);
        setRecentEvents(events);
      }

      const impactful: ImpactfulStock[] = events
        .filter((e: Event) => e.impact_score >= 60)
        .sort((a: Event, b: Event) => b.impact_score - a.impact_score)
        .slice(0, 5)
        .map((e: Event) => {
          const projectedMove = e.impact_p_move ? e.impact_p_move * 100 : (e.impact_score / 100) * 8;
          const isPositive = e.direction === 'positive';
          return {
            ticker: e.ticker,
            company_name: e.company_name || e.ticker,
            change_pct: isPositive ? projectedMove : -projectedMove,
            change_dollars: 0,
            impact_score: e.impact_score,
            direction: e.direction,
            event_title: e.title,
            event_type: e.event_type
          };
        });
      setImpactfulStocks(impactful);

      const allMilestones: UpcomingMilestone[] = [];
      const now = new Date();
      
      // First, try to get portfolio-specific upcoming events
      if (insightsRes.status === 'fulfilled') {
        // Handle the API response structure - could be { events: [...] } or an array
        const insightsData = insightsRes.value as { events?: Array<PortfolioInsightsEvent> } | Array<unknown>;
        
        // Extract events array from response
        let portfolioEvents: PortfolioInsightsEvent[] = [];
        if (insightsData && typeof insightsData === 'object') {
          if ('events' in insightsData && Array.isArray(insightsData.events)) {
            portfolioEvents = insightsData.events;
          } else if (Array.isArray(insightsData)) {
            // Legacy format - array of positions with nested events
            for (const item of insightsData) {
              if (item && typeof item === 'object' && 'events' in item && Array.isArray((item as { events: unknown[] }).events)) {
                const position = item as { ticker: string; market_value: number; exposure_1d: number; events: Array<{ title: string; date: string; score: number; direction: string }> };
                for (const event of position.events) {
                  const eventDate = new Date(event.date);
                  const daysUntil = Math.ceil((eventDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
                  const projectedMovePct = event.score ? event.score / 20 : 2.5;
                  const projectedMoveDollars = position.exposure_1d || (position.market_value * projectedMovePct / 100);
                  
                  allMilestones.push({
                    date: event.date,
                    ticker: position.ticker,
                    event_type: 'portfolio',
                    headline: event.title,
                    projected_move_pct: projectedMovePct,
                    projected_move_dollars: projectedMoveDollars,
                    direction: event.direction || 'neutral',
                    days_until: daysUntil
                  });
                }
              }
            }
          }
        }
        
        // Process portfolio events from the standard API response
        for (const event of portfolioEvents) {
          const eventDate = new Date(event.date);
          const daysUntil = Math.ceil((eventDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
          const projectedMovePct = event.impact_score ? event.impact_score / 20 : 2.5;
          const projectedMoveDollars = event.exposure_1d || 0;
          
          allMilestones.push({
            date: event.date,
            ticker: event.ticker,
            event_type: 'portfolio',
            headline: event.headline || event.event_type,
            projected_move_pct: projectedMovePct,
            projected_move_dollars: projectedMoveDollars,
            direction: event.direction || 'neutral',
            days_until: daysUntil
          });
        }
      }
      
      // If no portfolio events, fall back to recent high-impact market events
      if (allMilestones.length === 0 && events.length > 0) {
        const highImpactEvents = events
          .filter((e: Event) => e.impact_score >= 50)
          .sort((a: Event, b: Event) => new Date(b.date).getTime() - new Date(a.date).getTime())
          .slice(0, 6);
        
        for (const event of highImpactEvents) {
          const eventDate = new Date(event.date);
          const daysAgo = Math.ceil((now.getTime() - eventDate.getTime()) / (1000 * 60 * 60 * 24));
          const projectedMovePct = event.impact_p_move ? event.impact_p_move * 100 : (event.impact_score / 100) * 8;
          
          allMilestones.push({
            date: event.date,
            ticker: event.ticker,
            event_type: 'market',
            headline: event.title,
            projected_move_pct: projectedMovePct,
            projected_move_dollars: 0,
            direction: event.direction || 'neutral',
            days_until: -daysAgo
          });
        }
      }
      
      // Sort by date (newest first for past events, soonest first for future)
      const sortedMilestones = allMilestones
        .sort((a, b) => {
          // Future events (positive days_until) come first, sorted by nearest
          // Past events (negative days_until) come after, sorted by most recent
          if (a.days_until >= 0 && b.days_until >= 0) {
            return a.days_until - b.days_until;
          }
          if (a.days_until < 0 && b.days_until < 0) {
            return b.days_until - a.days_until;
          }
          return a.days_until >= 0 ? -1 : 1;
        })
        .slice(0, 6);
      
      setUpcomingMilestones(sortedMilestones);

    } catch (err: any) {
      console.error('Failed to fetch overview data:', err);
      setError(err?.message || 'Failed to load overview data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOverviewData();
  }, [fetchOverviewData]);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  const formatPercent = (value: number) => {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}%`;
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const getDirectionColor = (direction: string) => {
    switch (direction) {
      case 'positive': return 'text-[--success]';
      case 'negative': return 'text-[--error]';
      default: return 'text-[--warning]';
    }
  };

  const getDirectionBg = (direction: string) => {
    switch (direction) {
      case 'positive': return 'bg-[--badge-positive-bg] border-[--border]';
      case 'negative': return 'bg-[--badge-negative-bg] border-[--border]';
      default: return 'bg-[--warning-light] border-[--border]';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-[--primary] mx-auto mb-4" />
          <p className="text-[--muted]">Loading your dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <AlertCircle className="h-8 w-8 text-[--error] mx-auto mb-4" />
          <p className="text-[--error] mb-2">Error loading dashboard</p>
          <p className="text-[--muted] text-sm">{error}</p>
          <button
            onClick={fetchOverviewData}
            className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with Account Button */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[--text]">Dashboard Overview</h1>
          <p className="text-[--muted] text-sm mt-1">Your portfolio performance and upcoming events at a glance</p>
        </div>
        <button
          onClick={() => onNavigate?.('account')}
          className="flex items-center gap-2 px-4 py-2 bg-[--surface-muted] hover:bg-[--surface-hover] border border-[--border] rounded-lg transition-colors"
        >
          <User className="h-4 w-4 text-[--muted]" />
          <span className="text-sm font-medium text-[--text]">Account</span>
          <ChevronRight className="h-4 w-4 text-[--muted]" />
        </button>
      </div>

      {/* Portfolio Value Summary */}
      <div className="bg-gradient-to-br from-blue-500/10 to-purple-500/10 border border-blue-500/20 rounded-xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <DollarSign className="h-5 w-5 text-blue-400" />
          <h2 className="text-lg font-semibold text-[--text]">Portfolio Value</h2>
        </div>
        
        {portfolioSummary && portfolioSummary.positions_count > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <p className="text-sm text-[--muted] mb-1">Total Value</p>
              <p className="text-3xl font-bold text-[--text]">
                {formatCurrency(portfolioSummary.total_value)}
              </p>
            </div>
            <div>
              <p className="text-sm text-[--muted] mb-1">Total Change</p>
              <div className="flex items-center gap-2">
                {portfolioSummary.total_change_dollars >= 0 ? (
                  <ArrowUpRight className="h-5 w-5 text-[--success]" />
                ) : (
                  <ArrowDownRight className="h-5 w-5 text-[--error]" />
                )}
                <span className={`text-2xl font-bold ${portfolioSummary.total_change_dollars >= 0 ? 'text-[--success]' : 'text-[--error]'}`}>
                  {formatCurrency(Math.abs(portfolioSummary.total_change_dollars))}
                </span>
              </div>
            </div>
            <div>
              <p className="text-sm text-[--muted] mb-1">Percent Change</p>
              <div className="flex items-center gap-2">
                {portfolioSummary.total_change_pct >= 0 ? (
                  <TrendingUp className="h-5 w-5 text-[--success]" />
                ) : (
                  <TrendingDown className="h-5 w-5 text-[--error]" />
                )}
                <span className={`text-2xl font-bold ${portfolioSummary.total_change_pct >= 0 ? 'text-[--success]' : 'text-[--error]'}`}>
                  {formatPercent(portfolioSummary.total_change_pct)}
                </span>
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center py-6">
            <BarChart3 className="h-12 w-12 text-[--muted] mx-auto mb-3" />
            <p className="text-[--muted] mb-2">No portfolio positions yet</p>
            <button
              onClick={() => onNavigate?.('portfolio')}
              className="text-[--primary] hover:opacity-80 text-sm font-medium"
            >
              Upload your portfolio to get started
            </button>
          </div>
        )}
      </div>

      {/* Market Regime Indicator */}
      {marketRegime && marketRegime.regime !== 'unknown' && (
        <div className={`border rounded-xl p-4 ${
          marketRegime.regime === 'risk_on' 
            ? 'bg-gradient-to-r from-green-500/10 to-emerald-500/10 border-green-500/20' 
            : 'bg-gradient-to-r from-amber-500/10 to-red-500/10 border-amber-500/20'
        }`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {marketRegime.regime === 'risk_on' ? (
                <div className="p-2 bg-green-500/20 rounded-lg">
                  <Activity className="h-5 w-5 text-green-400" />
                </div>
              ) : (
                <div className="p-2 bg-amber-500/20 rounded-lg">
                  <Shield className="h-5 w-5 text-amber-400" />
                </div>
              )}
              <div>
                <div className="flex items-center gap-2">
                  <span className={`text-lg font-bold ${
                    marketRegime.regime === 'risk_on' ? 'text-green-400' : 'text-amber-400'
                  }`}>
                    {marketRegime.regime === 'risk_on' ? 'RISK-ON' : 'RISK-OFF'}
                  </span>
                  <span className="text-xs px-2 py-0.5 bg-[--surface-glass] rounded text-[--muted]">
                    {Math.round(marketRegime.confidence * 100)}% confidence
                  </span>
                </div>
                <p className="text-sm text-[--muted]">
                  {marketRegime.regime === 'risk_on' 
                    ? 'Markets favoring bullish events' 
                    : 'Elevated caution in markets'}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-6 text-sm">
              {marketRegime.volatility && (
                <div className="text-center">
                  <p className="text-[--muted] text-xs">Volatility</p>
                  <p className="font-semibold text-[--text]">{(marketRegime.volatility * 100).toFixed(1)}%</p>
                </div>
              )}
              {marketRegime.breadth && (
                <div className="text-center">
                  <p className="text-[--muted] text-xs">Breadth</p>
                  <p className="font-semibold text-[--text]">{Math.round(marketRegime.breadth * 100)}%</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Most Impactful Stocks & Events */}
        <div className="bg-[--surface-muted] border border-[--border] rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Zap className="h-5 w-5 text-yellow-400" />
              <h2 className="text-lg font-semibold text-[--text]">Most Impactful Events</h2>
            </div>
            <button
              onClick={() => onNavigate?.('events')}
              className="text-sm text-[--primary] hover:opacity-80 flex items-center gap-1"
            >
              View all <ChevronRight className="h-4 w-4" />
            </button>
          </div>

          {impactfulStocks.length > 0 ? (
            <div className="space-y-3">
              {impactfulStocks.map((stock, idx) => (
                <div
                  key={`${stock.ticker}-${idx}`}
                  className={`p-4 rounded-lg border ${getDirectionBg(stock.direction)}`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-[--text]">{stock.ticker}</span>
                      <span className="text-xs px-2 py-0.5 bg-[--surface-glass] rounded text-[--muted]">
                        {stock.event_type.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      {stock.change_pct >= 0 ? (
                        <ArrowUpRight className="h-4 w-4 text-[--success]" />
                      ) : (
                        <ArrowDownRight className="h-4 w-4 text-[--error]" />
                      )}
                      <span className={`font-semibold ${stock.change_pct >= 0 ? 'text-[--success]' : 'text-[--error]'}`}>
                        {formatPercent(stock.change_pct)}
                      </span>
                    </div>
                  </div>
                  <p className="text-sm text-[--muted] truncate">{stock.event_title}</p>
                  <div className="flex items-center gap-2 mt-2">
                    <Target className="h-3 w-3 text-[--muted]" />
                    <span className="text-xs text-[--muted]">Impact Score: {stock.impact_score}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Zap className="h-10 w-10 text-[--muted] mx-auto mb-3" />
              <p className="text-[--muted]">No high-impact events found</p>
            </div>
          )}
        </div>

        {/* Upcoming Events & Milestones */}
        <div className="bg-[--surface-muted] border border-[--border] rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Calendar className="h-5 w-5 text-purple-400" />
              <h2 className="text-lg font-semibold text-[--text]">
                {upcomingMilestones.length > 0 && upcomingMilestones[0].event_type === 'market' 
                  ? 'Recent High-Impact Events' 
                  : 'Upcoming Milestones'}
              </h2>
              {upcomingMilestones.length > 0 && upcomingMilestones[0].event_type === 'market' && (
                <span className="text-xs text-[--muted]">No upcoming portfolio events - showing recent market activity</span>
              )}
            </div>
            <button
              onClick={() => onNavigate?.('calendar')}
              className="text-sm text-[--primary] hover:opacity-80 flex items-center gap-1"
            >
              View calendar <ChevronRight className="h-4 w-4" />
            </button>
          </div>

          {upcomingMilestones.length > 0 ? (
            <div className="space-y-3">
              {upcomingMilestones.map((milestone, idx) => {
                const isMarketEvent = milestone.event_type === 'market';
                const isPastEvent = milestone.days_until < 0;
                const daysAbs = Math.abs(milestone.days_until);
                
                return (
                  <div
                    key={`${milestone.ticker}-${milestone.date}-${idx}`}
                    className={`p-4 rounded-lg border transition-colors ${
                      isMarketEvent 
                        ? 'bg-[--primary-light] border-[--border] hover:border-[--border-strong]' 
                        : 'bg-[--surface-muted] border-[--border] hover:border-[--border-strong]'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-[--text]">{milestone.ticker}</span>
                        <span className={`text-xs px-2 py-0.5 rounded ${
                          isMarketEvent 
                            ? 'bg-[--primary-soft] text-[--primary]' 
                            : 'bg-[--accent-soft] text-[--accent]'
                        }`}>
                          {isMarketEvent ? 'market event' : 'portfolio'}
                        </span>
                      </div>
                      <div className="flex items-center gap-1 text-sm text-[--muted]">
                        <Clock className="h-3 w-3" />
                        <span>
                          {isPastEvent 
                            ? daysAbs === 0 
                              ? 'Today'
                              : daysAbs === 1 
                                ? 'Yesterday' 
                                : `${daysAbs} days ago`
                            : milestone.days_until === 0 
                              ? 'Today' 
                              : milestone.days_until === 1 
                                ? 'Tomorrow' 
                                : `In ${milestone.days_until} days`
                          }
                        </span>
                      </div>
                    </div>
                    <p className="text-sm text-[--muted] truncate mb-2">{milestone.headline}</p>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-[--muted]">{formatDate(milestone.date)}</span>
                      {milestone.projected_move_pct !== 0 && (
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-[--muted]">{isPastEvent ? 'Impact:' : 'Projected:'}</span>
                          <span className={`text-sm font-semibold ${getDirectionColor(milestone.direction)}`}>
                            {formatPercent(milestone.projected_move_pct)}
                          </span>
                          {milestone.projected_move_dollars !== 0 && (
                            <span className={`text-sm ${getDirectionColor(milestone.direction)}`}>
                              ({formatCurrency(milestone.projected_move_dollars)})
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-center py-8">
              <Calendar className="h-10 w-10 text-[--muted] mx-auto mb-3" />
              <p className="text-[--muted] mb-2">No milestones available</p>
              <p className="text-xs text-[--muted]">Check back later for upcoming events</p>
            </div>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <button
          onClick={() => onNavigate?.('events')}
          className="p-5 bg-[--surface-muted] hover:bg-[--surface-hover] border border-[--border] rounded-lg transition-colors text-left"
        >
          <Zap className="h-6 w-6 text-[--warning] mb-3" />
          <p className="text-lg font-medium text-[--text]">Events</p>
          <p className="text-sm text-[--muted]">Browse all events</p>
        </button>
        <button
          onClick={() => onNavigate?.('portfolio')}
          className="p-5 bg-[--surface-muted] hover:bg-[--surface-hover] border border-[--border] rounded-lg transition-colors text-left"
        >
          <BarChart3 className="h-6 w-6 text-[--primary] mb-3" />
          <p className="text-lg font-medium text-[--text]">Portfolio</p>
          <p className="text-sm text-[--muted]">Manage positions</p>
        </button>
        <button
          onClick={() => onNavigate?.('trade-signals')}
          className="p-5 bg-[--surface-muted] hover:bg-[--surface-hover] border border-[--border] rounded-lg transition-colors text-left"
        >
          <TrendingUp className="h-6 w-6 text-[--success] mb-3" />
          <p className="text-lg font-medium text-[--text]">Trade Signals</p>
          <p className="text-sm text-[--muted]">View recommendations</p>
        </button>
        <button
          onClick={() => onNavigate?.('account')}
          className="p-5 bg-[--surface-muted] hover:bg-[--surface-hover] border border-[--border] rounded-lg transition-colors text-left"
        >
          <User className="h-6 w-6 text-[--accent] mb-3" />
          <p className="text-lg font-medium text-[--text]">Account</p>
          <p className="text-sm text-[--muted]">Settings & billing</p>
        </button>
      </div>
    </div>
  );
}
