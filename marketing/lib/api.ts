/**
 * Impact Radar API Client
 * TypeScript client library for FastAPI backend
 */

import { showToast } from './toast';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api/proxy';

// API Error Interface
interface ApiError {
  error_code: string;
  message: string;
  details?: any;
  status_code: number;
}

// Types
export interface Company {
  id: number;
  ticker: string;
  name: string;
  sector?: string;
  industry?: string;
  tracked: boolean;
  created_at: string;
  event_count?: number;
}

export interface Event {
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
  direction: 'positive' | 'negative' | 'neutral' | 'uncertain';
  confidence: number;
  rationale?: string;
  sector?: string;
  projected_move?: string;
  projected_magnitude?: number;
  is_uncertain?: boolean;
  impact_p_move?: number;
  impact_p_up?: number;
  impact_p_down?: number;
  impact_score_version?: number;
  ml_adjusted_score?: number;
  ml_model_version?: string;
  model_source?: 'family-specific' | 'global' | 'deterministic';
  ml_confidence?: number;
  delta_applied?: number;
}

export interface WatchlistItem {
  id: number;
  user_id: number;
  ticker: string;
  notes?: string;
  created_at: string;
}

export interface ScannerStatus {
  scanner: string;  // Scanner display name
  last_run?: string;
  next_run?: string;
  level: string;     // 'success', 'error', 'info', 'pending'
  message?: string;
  discoveries?: number;
}

export interface PortfolioPosition {
  ticker: string;
  shares: number;
  company_name?: string;
  cost_basis?: number;
  current_price?: number;
  market_value?: number;
  gain_loss?: number;
  sector?: string;
  label?: string;
}

export interface PortfolioUploadResponse {
  success: boolean;
  positions_count: number;
  errors: Array<{
    row: number;
    field: string;
    message: string;
  }>;
  portfolio_id: number;
}

export interface PortfolioInsightsEvent {
  event_id: number;
  ticker: string;
  event_type: string;
  headline: string;
  date: string;
  days_until: number;
  final_score: number;
  direction: string;
  confidence: number;
  expected_move_1d: number | null;
  expected_move_5d: number | null;
  expected_move_20d: number | null;
  sample_size_1d: number | null;
  qty: number;
  last_price: number;
  exposure_1d: number;
}

export interface PortfolioInsightsResponse {
  events: PortfolioInsightsEvent[];
  total_events: number;
  window_start: string;
  window_end: string;
}

export interface PortfolioInsight {
  ticker: string;
  shares: number;
  market_value: number;
  upcoming_events_count: number;
  total_risk_score: number;
  exposure_1d: number;
  exposure_5d: number;
  exposure_20d: number;
  events: Array<{ title: string; date: string; score: number; direction: string }>;
}

export interface RiskMetrics {
  total_event_exposure: number;
  concentration_risk_score: number;
  sector_diversification_score: number;
  var_95: number;
  expected_shortfall: number;
}

export interface TopEventRisk {
  event_id: number;
  ticker: string;
  event_type: string;
  title: string;
  date: string;
  impact_score: number;
  direction?: string;
  position_size_pct: number;
  estimated_impact_pct: number;
  dollar_exposure: number;
}

export interface RiskSnapshotResponse {
  id: number;
  portfolio_id: number;
  snapshot_date: string;
  metrics: RiskMetrics;
  top_event_risks: TopEventRisk[];
}

export interface EventExposure {
  id: number;
  portfolio_id: number;
  event_id: number;
  ticker: string;
  event_type: string;
  event_title: string;
  event_date: string;
  position_size_pct: number;
  estimated_impact_pct: number;
  dollar_exposure: number;
  hedge_recommendation?: string;
  calculated_at: string;
}

export interface HedgingRecommendation {
  ticker: string;
  event_id: number;
  event_type: string;
  event_date: string;
  position_size_pct: number;
  estimated_impact_pct: number;
  dollar_exposure: number;
  recommendation: string;
  risk_level: string;
}

export interface Alert {
  id: number;
  user_id: number;
  name: string;
  min_score: number;
  tickers?: string[];
  sectors?: string[];
  event_types?: string[];
  keywords?: string[];
  channels: string[];
  active: boolean;
  created_at: string;
}

export interface AlertCreate {
  name: string;
  min_score?: number;
  tickers?: string[];
  sectors?: string[];
  event_types?: string[];
  keywords?: string[];
  channels?: string[];
  active?: boolean;
}

export interface AlertUpdate {
  name?: string;
  min_score?: number;
  tickers?: string[];
  sectors?: string[];
  event_types?: string[];
  keywords?: string[];
  channels?: string[];
  active?: boolean;
}

export interface PatternAlert {
  id: number;
  pattern_id: number;
  pattern_name?: string;
  user_id?: number;
  ticker: string;
  company_name: string;
  event_ids: number[];
  correlation_score: number;
  aggregated_impact_score: number;
  aggregated_direction: string;
  rationale?: string;
  status: string;
  detected_at: string;
  acknowledged_at?: string;
}

export interface HistoricalStatsResponse {
  ticker: string;
  event_type: string;
  sample_size: number;
  win_rate: number | null;
  avg_abs_move_1d: number | null;
  avg_abs_move_5d: number | null;
  avg_abs_move_20d: number | null;
  mean_move_1d: number | null;
  mean_move_5d: number | null;
  mean_move_20d: number | null;
  methodology: string;
}

// Helper function to get auth token from session
function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('auth_token');
}

// Helper function to make authenticated requests
async function fetchAPI<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getAuthToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers ? (options.headers as Record<string, string>) : {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let error: ApiError;
    
    try {
      error = await response.json();
    } catch {
      error = {
        error_code: 'UNKNOWN_ERROR',
        message: response.statusText || 'API request failed',
        status_code: response.status
      };
    }
    
    handleApiError(error);
    throw new Error(error.message || 'API request failed');
  }

  return response.json();
}

// Handle API errors with user-friendly toasts
function handleApiError(error: ApiError) {
  switch (error.error_code) {
    case 'QUOTA_EXCEEDED':
      showToast('API quota exceeded. Please upgrade your plan.', 'error');
      break;
      
    case 'UPGRADE_REQUIRED':
      showToast(error.message, 'warning');
      break;
      
    case 'RATE_LIMIT_EXCEEDED':
      showToast('Too many requests. Please wait a moment.', 'error');
      break;
      
    case 'UNAUTHORIZED':
      showToast('Please log in to continue.', 'error');
      setTimeout(() => {
        window.location.href = '/login';
      }, 1500);
      break;
      
    case 'FORBIDDEN':
      showToast('You do not have permission to perform this action.', 'error');
      break;
      
    case 'NOT_FOUND':
      showToast(error.message || 'Resource not found', 'error');
      break;
      
    case 'VALIDATION_ERROR':
      // Don't show toast for validation errors - let components handle these
      break;
      
    case 'INVALID_INPUT':
      showToast(error.message || 'Invalid input provided', 'error');
      break;
      
    default:
      showToast(error.message || 'An error occurred', 'error');
  }
}

// Authentication API
export const authAPI = {
  async register(email: string, password: string): Promise<{ access_token: string; token_type: string }> {
    return fetchAPI('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  },

  async login(email: string, password: string): Promise<{ access_token: string; token_type: string }> {
    const response = await fetchAPI<{ access_token: string; token_type: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    
    // Store token in localStorage
    if (typeof window !== 'undefined') {
      localStorage.setItem('auth_token', response.access_token);
    }
    
    return response;
  },

  async logout(): Promise<{ message: string }> {
    const response = await fetchAPI<{ message: string }>('/auth/logout', {
      method: 'POST',
    });
    
    // Remove token from localStorage
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth_token');
    }
    
    return response;
  },
};

// Companies API
export const companiesAPI = {
  async getAll(params?: {
    tracked_only?: boolean;
    sector?: string;
    with_event_counts?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<Company[]> {
    const queryParams = new URLSearchParams();
    if (params?.tracked_only) queryParams.set('tracked_only', 'true');
    if (params?.sector) queryParams.set('sector', params.sector);
    if (params?.with_event_counts) queryParams.set('with_event_counts', 'true');
    if (params?.limit) queryParams.set('limit', params.limit.toString());
    if (params?.offset) queryParams.set('offset', params.offset.toString());

    const query = queryParams.toString();
    return fetchAPI(`/companies${query ? `?${query}` : ''}`);
  },

  async getUniverse(params?: {
    count_only?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<{ count: number; companies?: Company[] }> {
    const queryParams = new URLSearchParams();
    if (params?.count_only) queryParams.set('count_only', 'true');
    if (params?.limit) queryParams.set('limit', params.limit.toString());
    if (params?.offset) queryParams.set('offset', params.offset.toString());

    const query = queryParams.toString();
    return fetchAPI(`/companies/universe${query ? `?${query}` : ''}`);
  },

  async getOne(ticker: string): Promise<Company> {
    return fetchAPI(`/companies/${ticker}`);
  },

  async getEvents(ticker: string, limit: number = 10): Promise<Event[]> {
    return fetchAPI(`/companies/${ticker}/events/public?limit=${limit}`);
  },
};

// Events API
export const eventsAPI = {
  async getAll(params?: {
    ticker?: string;
    category?: string;
    sector?: string;
    direction?: string;
    min_score?: number;
    from_date?: string;
    to_date?: string;
    limit?: number;
    offset?: number;
  }): Promise<Event[]> {
    const queryParams = new URLSearchParams();
    
    if (params?.ticker) queryParams.set('ticker', params.ticker);
    if (params?.category) queryParams.set('category', params.category);
    if (params?.sector) queryParams.set('sector', params.sector);
    if (params?.direction) queryParams.set('direction', params.direction);
    if (params?.min_score !== undefined) queryParams.set('min_impact', params.min_score.toString());
    if (params?.from_date) queryParams.set('from_date', params.from_date);
    if (params?.to_date) queryParams.set('to_date', params.to_date);
    if (params?.limit) queryParams.set('limit', params.limit.toString());
    if (params?.offset) queryParams.set('offset', params.offset.toString());

    const query = queryParams.toString();
    return fetchAPI(`/events/public${query ? `?${query}` : ''}`);
  },

  async search(params?: {
    ticker?: string;
    category?: string;
    sector?: string;
    direction?: string;
    min_score?: number;
    from_date?: string;
    to_date?: string;
    limit?: number;
    offset?: number;
  }): Promise<Event[]> {
    const queryParams = new URLSearchParams();
    
    if (params?.ticker) queryParams.set('ticker', params.ticker);
    if (params?.category) queryParams.set('category', params.category);
    if (params?.sector) queryParams.set('sector', params.sector);
    if (params?.direction) queryParams.set('direction', params.direction);
    if (params?.min_score !== undefined) queryParams.set('min_impact', params.min_score.toString());
    if (params?.from_date) queryParams.set('from_date', params.from_date);
    if (params?.to_date) queryParams.set('to_date', params.to_date);
    if (params?.limit) queryParams.set('limit', params.limit.toString());
    if (params?.offset) queryParams.set('offset', params.offset.toString());

    const query = queryParams.toString();
    return fetchAPI(`/events/search${query ? `?${query}` : ''}`);
  },

  async getOne(id: number): Promise<Event> {
    return fetchAPI(`/events/${id}`);
  },
};

// Watchlist API
export const watchlistAPI = {
  async getAll(): Promise<WatchlistItem[]> {
    return fetchAPI('/watchlist');
  },

  async add(company_id: number, notes?: string): Promise<{ message: string }> {
    return fetchAPI('/watchlist', {
      method: 'POST',
      body: JSON.stringify({ company_id, notes }),
    });
  },

  async remove(company_id: number): Promise<{ message: string }> {
    return fetchAPI(`/watchlist/${company_id}`, {
      method: 'DELETE',
    });
  },
};

// Impact Scoring API
export const impactAPI = {
  async score(event: {
    event_type: string;
    title: string;
    description?: string;
    sector?: string;
  }): Promise<{
    impact_score: number;
    direction: string;
    confidence: number;
    rationale: string;
  }> {
    return fetchAPI('/impact/score', {
      method: 'POST',
      body: JSON.stringify(event),
    });
  },
};

// Scanners API
export const scannersAPI = {
  async getCount(): Promise<{ count: number }> {
    return fetchAPI('/scanners/count');
  },

  async getStatus(): Promise<ScannerStatus[]> {
    return fetchAPI('/scanners/status');
  },

  async getDiscoveries(params?: {
    source?: string;
    limit?: number;
  }): Promise<any[]> {
    const queryParams = new URLSearchParams();
    if (params?.source) queryParams.set('source', params.source);
    if (params?.limit) queryParams.set('limit', params.limit.toString());

    const query = queryParams.toString();
    return fetchAPI(`/scanners/discoveries${query ? `?${query}` : ''}`);
  },

  async rescanCompany(ticker: string): Promise<{ job_id: number; status: string; message: string }> {
    return fetchAPI('/scanners/rescan/company', {
      method: 'POST',
      body: JSON.stringify({ ticker }),
    });
  },

  async rescanScanner(scanner_key: string): Promise<{ job_id: number; status: string; message: string }> {
    return fetchAPI('/scanners/rescan/scanner', {
      method: 'POST',
      body: JSON.stringify({ scanner_key }),
    });
  },

  async getScanJobs(params?: {
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<{
    jobs: Array<{
      id: number;
      scope: string;
      ticker?: string;
      scanner_key?: string;
      status: string;
      items_found?: number;
      error?: string;
      created_at: string;
      started_at?: string;
      finished_at?: string;
    }>;
    offset: number;
    limit: number;
  }> {
    const queryParams = new URLSearchParams();
    if (params?.status) queryParams.set('status', params.status);
    if (params?.limit) queryParams.set('limit', params.limit.toString());
    if (params?.offset) queryParams.set('offset', params.offset.toString());

    const query = queryParams.toString();
    return fetchAPI(`/scanners/jobs${query ? `?${query}` : ''}`);
  },

  async getScanJob(job_id: number): Promise<{
    id: number;
    scope: string;
    ticker?: string;
    scanner_key?: string;
    status: string;
    items_found?: number;
    error?: string;
    created_at: string;
    started_at?: string;
    finished_at?: string;
  }> {
    return fetchAPI(`/scanners/jobs/${job_id}`);
  },

  // SSE stream for real-time discoveries
  streamDiscoveries(onMessage: (data: any) => void, onError?: (error: Error) => void) {
    const eventSource = new EventSource(`${API_BASE_URL}/stream/discoveries`);
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (error) {
        console.error('Failed to parse SSE message:', error);
      }
    };

    eventSource.onerror = (error) => {
      console.error('SSE connection error:', error);
      if (onError) onError(new Error('SSE connection failed'));
      eventSource.close();
    };

    return () => eventSource.close();
  },
};

// Portfolio API
export const portfolioAPI = {
  async upload(file: File): Promise<PortfolioUploadResponse> {
    const token = getAuthToken();
    const formData = new FormData();
    formData.append('file', file);

    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE_URL}/portfolio/upload`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || 'Portfolio upload failed');
    }

    return response.json();
  },

  async get(): Promise<{ id: number; name: string; created_at: string; positions_count: number }> {
    return fetchAPI('/portfolio');
  },

  async getHoldings(): Promise<PortfolioPosition[]> {
    return fetchAPI('/portfolio/holdings');
  },

  async delete(): Promise<{ message: string }> {
    return fetchAPI('/portfolio', {
      method: 'DELETE',
    });
  },

  async insights(params?: {
    days_ahead?: number;
  }): Promise<PortfolioInsight[]> {
    const queryParams = new URLSearchParams();
    if (params?.days_ahead) queryParams.set('days_ahead', params.days_ahead.toString());
    if (params?.days_ahead) queryParams.set('window_days', params.days_ahead.toString());

    const query = queryParams.toString();
    return fetchAPI(`/portfolio/insights${query ? `?${query}` : ''}`);
  },

  async calculateRisk(portfolioId: number, lookforwardDays: number = 30): Promise<{ success: boolean; message: string; snapshot_id: number; snapshot_date: string }> {
    return fetchAPI(`/portfolio/${portfolioId}/risk/calculate`, {
      method: 'POST',
      body: JSON.stringify({ lookforward_days: lookforwardDays }),
    });
  },

  async getLatestRiskSnapshot(portfolioId: number): Promise<RiskSnapshotResponse> {
    return fetchAPI(`/portfolio/${portfolioId}/risk/latest`);
  },

  async getEventExposures(portfolioId: number, daysAhead: number = 30): Promise<EventExposure[]> {
    const queryParams = new URLSearchParams();
    queryParams.set('days_ahead', daysAhead.toString());
    return fetchAPI(`/portfolio/${portfolioId}/risk/events?${queryParams.toString()}`);
  },

  async getHedgingRecommendations(portfolioId: number, params?: {
    days_ahead?: number;
    min_risk_level?: 'low' | 'medium' | 'high';
  }): Promise<HedgingRecommendation[]> {
    const queryParams = new URLSearchParams();
    if (params?.days_ahead) queryParams.set('days_ahead', params.days_ahead.toString());
    if (params?.min_risk_level) queryParams.set('min_risk_level', params.min_risk_level);
    const query = queryParams.toString();
    return fetchAPI(`/portfolio/${portfolioId}/risk/hedging${query ? `?${query}` : ''}`);
  },
};

// Alerts API
export const alertsAPI = {
  async getAll(active_only?: boolean): Promise<Alert[]> {
    const queryParams = new URLSearchParams();
    if (active_only) queryParams.set('active_only', 'true');
    
    const query = queryParams.toString();
    return fetchAPI(`/alerts${query ? `?${query}` : ''}`);
  },

  async getOne(id: number): Promise<Alert> {
    return fetchAPI(`/alerts/${id}`);
  },

  async create(data: AlertCreate): Promise<Alert> {
    return fetchAPI('/alerts', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async update(id: number, data: AlertUpdate): Promise<Alert> {
    return fetchAPI(`/alerts/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  async delete(id: number): Promise<void> {
    return fetchAPI(`/alerts/${id}`, {
      method: 'DELETE',
    });
  },
};

// Pattern Alerts API
export const patternsAPI = {
  async getPatternAlerts(params?: {
    ticker?: string;
    status_filter?: string;
    limit?: number;
  }): Promise<PatternAlert[]> {
    const queryParams = new URLSearchParams();
    if (params?.ticker) queryParams.set('ticker', params.ticker);
    if (params?.status_filter) queryParams.set('status_filter', params.status_filter);
    if (params?.limit) queryParams.set('limit', params.limit.toString());
    
    const query = queryParams.toString();
    return fetchAPI(`/patterns/alerts${query ? `?${query}` : ''}`);
  },

  async acknowledgePatternAlert(alertId: number): Promise<{ message: string; alert_id: number }> {
    return fetchAPI(`/patterns/alerts/${alertId}/acknowledge`, {
      method: 'POST',
    });
  },
};

// Stats API
export const statsAPI = {
  async getEventStats(ticker: string, eventType: string): Promise<HistoricalStatsResponse> {
    return fetchAPI(`/stats/${ticker}/${eventType}`);
  },

  async getTickerStats(ticker: string): Promise<HistoricalStatsResponse[]> {
    return fetchAPI(`/stats/${ticker}`);
  },
};

// Demo API
export const demoAPI = {
  async loadDemoData(): Promise<{
    success: boolean;
    message: string;
    portfolio_holdings: number;
    watchlist_items: number;
    alerts: number;
  }> {
    return fetchAPI('/demo/load', {
      method: 'POST',
    });
  },
};

// Dashboard Init Response Type
export interface DashboardInitResponse {
  events: Event[];
  scanners: ScannerStatus[];
  scanner_count: number;
  company_count: number;
  discoveries: Array<{
    id: number;
    ticker: string;
    title: string;
    event_type: string;
    impact_score: number;
    direction: string;
    timestamp: string;
    source_url?: string;
  }>;
  last_scan?: {
    started_at: string;
    is_automatic: boolean;
  };
  cached_at: string;
}

// Dashboard API - Consolidated endpoint for fast loading
export const dashboardAPI = {
  async init(mode: 'watchlist' | 'portfolio' = 'watchlist'): Promise<DashboardInitResponse> {
    return fetchAPI(`/dashboard/init?mode=${mode}`);
  },

  async getStats(): Promise<{
    scanner_count: number;
    company_count: number;
    events_24h: number;
  }> {
    return fetchAPI('/dashboard/stats');
  },
};

// Sector types
export interface SectorMetrics {
  id: number;
  sector: string;
  win_rate: number;
  avg_impact: number;
  rotation_signal: string;
  momentum_score: number;
  total_events: number;
  updated_at: string;
}

export interface SectorRotationSignal {
  sector: string;
  signal: string;
  momentum_score: number;
  win_rate: number;
  total_events: number;
}

// Sectors API
export const sectorsAPI = {
  async getAll(): Promise<SectorMetrics[]> {
    return fetchAPI('/sectors');
  },
  async getSector(sector: string): Promise<SectorMetrics> {
    return fetchAPI(`/sectors/${encodeURIComponent(sector)}`);
  },
  async getRotationSignals(): Promise<SectorRotationSignal[]> {
    return fetchAPI('/sectors/rotation-signals');
  },
  async getPerformanceComparison(params?: { sectors?: string[]; days?: number }): Promise<any> {
    const queryParams = new URLSearchParams();
    if (params?.sectors) params.sectors.forEach(s => queryParams.append('sectors', s));
    if (params?.days) queryParams.set('days', params.days.toString());
    const query = queryParams.toString();
    return fetchAPI(`/sectors/performance-comparison${query ? `?${query}` : ''}`);
  },
};

// Trade Signal types
export interface TradeRecommendation {
  id: number;
  event_id: number;
  ticker: string;
  recommendation_type: string;
  entry_price_target: number;
  stop_loss: number;
  take_profit: number;
  position_size_pct: number;
  risk_reward_ratio: number;
  rationale: string;
  expires_at: string;
  created_at: string;
}

// Trade Signals API
export const tradeSignalsAPI = {
  async getAll(params?: { ticker?: string; min_confidence?: number; limit?: number }): Promise<TradeRecommendation[]> {
    const queryParams = new URLSearchParams();
    if (params?.ticker) queryParams.set('ticker', params.ticker);
    if (params?.min_confidence) queryParams.set('min_confidence', params.min_confidence.toString());
    if (params?.limit) queryParams.set('limit', params.limit.toString());
    const query = queryParams.toString();
    return fetchAPI(`/trade-signals${query ? `?${query}` : ''}`);
  },
  async getForEvent(eventId: number): Promise<TradeRecommendation> {
    return fetchAPI(`/trade-signals/event/${eventId}`);
  },
  async generate(eventId: number): Promise<TradeRecommendation> {
    return fetchAPI(`/trade-signals/generate/${eventId}`, { method: 'POST' });
  },
  async getForPortfolio(): Promise<TradeRecommendation[]> {
    return fetchAPI('/trade-signals/portfolio');
  },
};

// Explainability types
export interface SHAPExplanation {
  event_id: number;
  horizon: string;
  feature_contributions: Record<string, number>;
  top_factors: Array<{ factor: string; contribution: number; direction: string }>;
  shap_summary: string;
  model_version: string;
}

export interface ModelFactor {
  factor: string;
  description: string;
}

// Explainability API
export const explainabilityAPI = {
  async getExplanation(eventId: number, horizon?: string): Promise<SHAPExplanation> {
    const queryParams = new URLSearchParams();
    if (horizon) queryParams.set('horizon', horizon);
    const query = queryParams.toString();
    return fetchAPI(`/explainability/event/${eventId}${query ? `?${query}` : ''}`);
  },
  async getFactors(): Promise<ModelFactor[]> {
    return fetchAPI('/explainability/factors');
  },
  async compute(eventId: number): Promise<{ message: string; event_id: number }> {
    return fetchAPI(`/explainability/compute/${eventId}`, { method: 'POST' });
  },
};

// Preferences types
export interface UserPreferences {
  theme: string;
  default_horizon: string;
  saved_filters: Record<string, any>;
  notification_settings: Record<string, any>;
  timezone: string;
}

export interface SavedFilters {
  event_types: string[];
  sectors: string[];
  min_score: number;
  horizons: string[];
}

// Preferences API
export const preferencesAPI = {
  async getTheme(): Promise<{ theme: string }> {
    return fetchAPI('/preferences/theme');
  },
  async updateTheme(theme: string): Promise<{ theme: string }> {
    return fetchAPI('/preferences/theme', {
      method: 'PUT',
      body: JSON.stringify({ theme }),
    });
  },
  async getFilters(): Promise<SavedFilters> {
    return fetchAPI('/preferences/filters');
  },
  async updateFilters(filters: SavedFilters): Promise<SavedFilters> {
    return fetchAPI('/preferences/filters', {
      method: 'PUT',
      body: JSON.stringify(filters),
    });
  },
  async getSettings(): Promise<UserPreferences> {
    return fetchAPI('/preferences/settings');
  },
  async updateSettings(settings: Partial<UserPreferences>): Promise<UserPreferences> {
    return fetchAPI('/preferences/settings', {
      method: 'PUT',
      body: JSON.stringify(settings),
    });
  },
};

// Digest types
export interface DigestSubscription {
  id: number;
  frequency: string;
  delivery_time: string;
  delivery_day: number | null;
  include_sections: Record<string, boolean>;
  tickers_filter: string[];
  min_score_threshold: number;
  active: boolean;
  next_send_at: string | null;
  last_sent_at: string | null;
}

export interface DigestPreview {
  top_events: Array<{ id: number; ticker: string; title: string; impact_score: number; direction: string }>;
  portfolio_summary: { total_events: number; total_exposure: number } | null;
  alerts_count: number;
}

// Digests API
export const digestsAPI = {
  async get(): Promise<DigestSubscription | null> {
    return fetchAPI('/digests');
  },
  async createOrUpdate(data: Partial<DigestSubscription>): Promise<DigestSubscription> {
    return fetchAPI('/digests', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
  async delete(): Promise<void> {
    return fetchAPI('/digests', { method: 'DELETE' });
  },
  async preview(): Promise<DigestPreview> {
    return fetchAPI('/digests/preview', { method: 'POST' });
  },
  async sendNow(): Promise<{ message: string }> {
    return fetchAPI('/digests/send-now', { method: 'POST' });
  },
};

// History types
export interface HistoricalPattern {
  id: number;
  event_type: string;
  ticker: string | null;
  sector: string | null;
  pattern_name: string;
  avg_return_1d: number;
  avg_return_7d: number;
  avg_return_30d: number;
  win_rate_1d: number;
  sample_size: number;
}

export interface SimilarEvent {
  event_id: number;
  ticker: string;
  title: string;
  event_type: string;
  date: string;
  return_1d: number | null;
  return_5d: number | null;
  direction_correct: boolean | null;
}

// History API
export const historyAPI = {
  async getPatterns(params?: { event_type?: string; sector?: string; limit?: number }): Promise<HistoricalPattern[]> {
    const queryParams = new URLSearchParams();
    if (params?.event_type) queryParams.set('event_type', params.event_type);
    if (params?.sector) queryParams.set('sector', params.sector);
    if (params?.limit) queryParams.set('limit', params.limit.toString());
    const query = queryParams.toString();
    return fetchAPI(`/history/patterns${query ? `?${query}` : ''}`);
  },
  async getSimilarEvents(eventId: number, limit?: number): Promise<{ events: SimilarEvent[]; stats: any }> {
    const queryParams = new URLSearchParams();
    if (limit) queryParams.set('limit', limit.toString());
    const query = queryParams.toString();
    return fetchAPI(`/history/similar-events/${eventId}${query ? `?${query}` : ''}`);
  },
  async getEventOutcomes(eventId: number): Promise<any> {
    return fetchAPI(`/history/event-outcomes/${eventId}`);
  },
};

// Export API
export const exportAPI = {
  async exportEvents(params?: { from_date?: string; to_date?: string; tickers?: string[]; sectors?: string[] }): Promise<Blob> {
    const queryParams = new URLSearchParams();
    if (params?.from_date) queryParams.set('from_date', params.from_date);
    if (params?.to_date) queryParams.set('to_date', params.to_date);
    if (params?.tickers) params.tickers.forEach(t => queryParams.append('tickers', t));
    if (params?.sectors) params.sectors.forEach(s => queryParams.append('sectors', s));
    const query = queryParams.toString();
    
    const response = await fetch(`${API_BASE_URL}/export/events${query ? `?${query}` : ''}`);
    if (!response.ok) throw new Error('Export failed');
    return response.blob();
  },
  async exportPortfolio(portfolioId: number): Promise<Blob> {
    const response = await fetch(`${API_BASE_URL}/export/portfolio/${portfolioId}`);
    if (!response.ok) throw new Error('Export failed');
    return response.blob();
  },
};

// Export all APIs
export const api = {
  auth: authAPI,
  companies: companiesAPI,
  events: eventsAPI,
  watchlist: watchlistAPI,
  impact: impactAPI,
  scanners: scannersAPI,
  portfolio: portfolioAPI,
  alerts: alertsAPI,
  patterns: patternsAPI,
  stats: statsAPI,
  demo: demoAPI,
  dashboard: dashboardAPI,
  sectors: sectorsAPI,
  tradeSignals: tradeSignalsAPI,
  explainability: explainabilityAPI,
  preferences: preferencesAPI,
  digests: digestsAPI,
  history: historyAPI,
  export: exportAPI,
};

export default api;
