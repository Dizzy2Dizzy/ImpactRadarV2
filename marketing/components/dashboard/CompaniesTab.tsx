'use client';

import { useState, useEffect } from 'react';
import { api, Company, Event } from '@/lib/api';
import { ChevronDown, ChevronRight, ExternalLink, Calendar, LineChart, Search, Loader2 } from 'lucide-react';
import { StatsBadge } from './StatsBadge';
import { PriceChartModal } from './PriceChartModal';
import { ModelVersionFilter } from './ModelVersionFilter';
import { ImpactScoreBadge, DisplayVersion } from './ImpactScoreBadge';

const PAGE_SIZE = 100;

export function CompaniesTab() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [filteredCompanies, setFilteredCompanies] = useState<Company[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedCompany, setExpandedCompany] = useState<string | null>(null);
  const [companyEvents, setCompanyEvents] = useState<{ [ticker: string]: Event[] }>({});
  const [loadingEvents, setLoadingEvents] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const [totalCount, setTotalCount] = useState<number | null>(null);
  
  const [showChart, setShowChart] = useState(false);
  const [chartTicker, setChartTicker] = useState('');
  const [modelVersion, setModelVersion] = useState<DisplayVersion>('v1.5');

  useEffect(() => {
    loadCompanies();
    loadTotalCount();
  }, []);

  const loadTotalCount = async () => {
    try {
      const result = await api.companies.getUniverse({ count_only: true });
      setTotalCount(result.count);
    } catch (err) {
      console.error('Failed to load total count:', err);
    }
  };

  const loadCompanies = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.companies.getAll({ limit: PAGE_SIZE, offset: 0 });
      setCompanies(data);
      setFilteredCompanies(data);
      setHasMore(data.length === PAGE_SIZE);
    } catch (err: any) {
      console.error('Failed to load companies:', err);
      setError(err?.message || 'Failed to load companies');
    } finally {
      setLoading(false);
    }
  };

  const loadMoreCompanies = async () => {
    if (loadingMore || !hasMore) return;
    
    try {
      setLoadingMore(true);
      const data = await api.companies.getAll({ 
        limit: PAGE_SIZE, 
        offset: companies.length 
      });
      
      if (data.length < PAGE_SIZE) {
        setHasMore(false);
      }
      
      const newCompanies = [...companies, ...data];
      setCompanies(newCompanies);
      
      if (!searchQuery.trim()) {
        setFilteredCompanies(newCompanies);
      }
    } catch (err: any) {
      console.error('Failed to load more companies:', err);
    } finally {
      setLoadingMore(false);
    }
  };

  // Filter companies based on search query
  useEffect(() => {
    if (!searchQuery.trim()) {
      setFilteredCompanies(companies);
      return;
    }

    const query = searchQuery.toLowerCase();
    const filtered = companies.filter(company => 
      company.ticker.toLowerCase().includes(query) ||
      company.name.toLowerCase().includes(query) ||
      (company.sector && company.sector.toLowerCase().includes(query))
    );
    setFilteredCompanies(filtered);
  }, [searchQuery, companies]);

  const handleCompanyClick = async (ticker: string) => {
    if (expandedCompany === ticker) {
      setExpandedCompany(null);
      return;
    }

    setExpandedCompany(ticker);

    if (!companyEvents[ticker]) {
      setLoadingEvents(ticker);
      try {
        const events = await api.companies.getEvents(ticker);
        setCompanyEvents(prev => ({ ...prev, [ticker]: events }));
      } catch (err) {
        console.error(`Failed to load events for ${ticker}:`, err);
      } finally {
        setLoadingEvents(null);
      }
    }
  };

  const getDirectionColor = (dir: string) => {
    switch (dir) {
      case 'positive':
        return 'text-[--success]';
      case 'negative':
        return 'text-[--error]';
      case 'neutral':
        return 'text-[--muted]';
      default:
        return 'text-[--warning]';
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 75) return 'bg-red-500/20 text-[--error] border-red-500/30';
    if (score >= 50) return 'bg-yellow-500/20 text-[--warning] border-yellow-500/30';
    return 'bg-gray-500/20 text-[--muted] border-gray-500/30';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <p className="text-[--muted]">Loading companies...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
        <p className="text-[--error]">{error}</p>
      </div>
    );
  }

  const getFilteredEvents = (events: Event[]) => {
    if (modelVersion === 'v2.0') {
      return events.filter(event => 
        event.model_source !== 'deterministic' && event.ml_adjusted_score != null
      );
    }
    return events;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-2xl font-bold text-[--text] mb-2">Companies Tracked</h2>
          <p className="text-sm text-[--muted]">
            Click any company to see their event timeline
          </p>
        </div>
        <ModelVersionFilter value={modelVersion} onChange={setModelVersion} />
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-[--muted]" />
        <input
          type="text"
          placeholder="Search companies by ticker, name, or sector..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-10 pr-4 py-3 bg-[--surface-muted] border border-[--border] rounded-lg text-[--text] placeholder:text-[--muted] focus:outline-none focus:ring-2 focus:ring-[--focus-ring] focus:border-transparent"
        />
      </div>

      {companies.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-[--muted]">No companies tracked yet</p>
        </div>
      ) : filteredCompanies.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-[--muted]">No companies match your search</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filteredCompanies.map((company) => (
            <div key={company.ticker} className="bg-[--surface-muted] rounded-lg overflow-hidden">
              <div className="flex items-center">
                <button
                  onClick={() => handleCompanyClick(company.ticker)}
                  className="flex-1 px-6 py-4 flex items-center justify-between hover:bg-[--surface-hover] transition-colors text-left"
                >
                  <div className="flex items-center gap-4 flex-1">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-1">
                        <span className="font-semibold text-[--text]">{company.ticker}</span>
                        <span className="text-sm text-[--muted]">{company.name}</span>
                      </div>
                      <div className="flex items-center gap-3 text-sm">
                        {company.sector && (
                          <span className="px-2 py-1 bg-[--surface-glass] rounded text-[--muted]">
                            {company.sector}
                          </span>
                        )}
                        {company.event_count !== undefined && (
                          <span className="text-[--muted]">
                            {company.event_count} {company.event_count === 1 ? 'event' : 'events'}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {expandedCompany === company.ticker ? (
                    <ChevronDown className="h-5 w-5 text-[--muted]" />
                  ) : (
                    <ChevronRight className="h-5 w-5 text-[--muted]" />
                  )}
                </button>
                
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setChartTicker(company.ticker);
                    setShowChart(true);
                  }}
                  className="px-4 py-4 hover:bg-[--surface-hover] transition-colors flex items-center gap-2 text-[--success] hover:text-[--success]"
                  title="View Price Chart"
                >
                  <LineChart className="h-5 w-5" />
                </button>
              </div>

              {expandedCompany === company.ticker && (
                <div className="px-6 pb-6 pt-2 border-t border-[--border]">
                  {loadingEvents === company.ticker ? (
                    <p className="text-sm text-[--muted] py-4">Loading events...</p>
                  ) : companyEvents[company.ticker]?.length > 0 ? (
                    <div className="space-y-3 mt-4">
                      <h4 className="font-semibold text-[--text] mb-3">Event Timeline</h4>
                      {getFilteredEvents(companyEvents[company.ticker]).length === 0 ? (
                        <p className="text-sm text-[--muted] py-4">No ML-scored events found for this company (V2.0 filter active)</p>
                      ) : (
                        getFilteredEvents(companyEvents[company.ticker]).map((event) => (
                          <div
                            key={event.id}
                            className="bg-[--surface-muted] rounded-lg p-4 hover:bg-[--surface-hover] transition-colors"
                          >
                            <div className="flex items-start justify-between gap-4">
                              <div className="flex-1">
                                <div className="flex items-center gap-3 mb-2">
                                  <ImpactScoreBadge
                                    baseScore={event.impact_score}
                                    mlAdjustedScore={event.ml_adjusted_score}
                                    mlConfidence={event.ml_confidence}
                                    modelSource={event.model_source}
                                    modelVersion={event.ml_model_version}
                                    compact={true}
                                    displayVersion={modelVersion}
                                  />
                                  <span className={`text-sm capitalize ${getDirectionColor(event.direction)}`}>
                                    {event.direction}
                                  </span>
                                  <span className="text-sm text-[--muted]">
                                    {Math.round(event.confidence * 100)}% confidence
                                  </span>
                                </div>

                                <h4 className="font-medium text-[--text] mb-2">{event.title}</h4>

                                <div className="flex items-center gap-4 text-sm text-[--muted] flex-wrap">
                                  <span className="flex items-center gap-1">
                                    <Calendar className="h-4 w-4" />
                                    {new Date(event.date).toLocaleDateString()}
                                  </span>
                                  <span className="px-2 py-1 bg-[--surface-glass] rounded">
                                    {event.event_type?.replace(/_/g, ' ')}
                                  </span>
                                  <StatsBadge ticker={event.ticker} eventType={event.event_type} />
                                </div>
                              </div>

                              {event.source_url && (
                                <a
                                  href={event.source_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-[--primary] hover:text-[--primary] flex items-center gap-1"
                                >
                                  <ExternalLink className="h-4 w-4" />
                                </a>
                              )}
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  ) : (
                    <p className="text-sm text-[--muted] py-4">No events found for this company</p>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {companies.length > 0 && (
        <div className="space-y-4">
          {!searchQuery && hasMore && (
            <div className="flex justify-center">
              <button
                onClick={loadMoreCompanies}
                disabled={loadingMore}
                className="px-6 py-3 bg-[--primary-soft] hover:bg-[--surface-hover] border border-[--border-strong] rounded-lg text-[--primary] font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {loadingMore ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Loading...
                  </>
                ) : (
                  <>Load More Companies</>
                )}
              </button>
            </div>
          )}
          
          <div className="text-center text-sm text-[--muted]">
            {searchQuery ? (
              <>Showing {filteredCompanies.length} matching companies</>
            ) : (
              <>
                Showing {companies.length} of {totalCount ?? '...'} companies
                {!hasMore && totalCount && companies.length >= totalCount && ' (all loaded)'}
              </>
            )}
          </div>
        </div>
      )}

      <PriceChartModal
        open={showChart}
        onClose={() => setShowChart(false)}
        ticker={chartTicker}
      />
    </div>
  );
}
