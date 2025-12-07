'use client';

import { useState, useEffect, useRef } from 'react';
import { apiRequest } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { TrendingUp, TrendingDown, Target, BarChart3, Info, Cpu, Zap, CheckCircle, AlertTriangle, XCircle, ChevronDown, ChevronRight, ExternalLink } from 'lucide-react';
import { Tooltip } from '@/components/ui/tooltip';
import { useDashboardModeStore } from '@/stores/dashboardModeStore';
import { FreshnessBadge } from './FreshnessBadge';
import { useRouter } from 'next/navigation';
import { ModelVersionFilter } from './ModelVersionFilter';
import { DisplayVersion } from './ImpactScoreBadge';

interface FamilyCoverageResponse {
  family: string;
  family_display_name: string;
  total_events: number;
  labeled_count_1d: number;
  labeled_count_5d: number;
  labeled_count_20d: number;
  model_status_1d: string;
  model_status_5d: string;
  model_status_20d: string;
  model_source_1d: string;
  model_source_5d: string;
  model_source_20d: string;
  model_version_1d: string | null;
  model_version_5d: string | null;
  model_version_20d: string | null;
  model_trained_at_1d: string | null;
  model_trained_at_5d: string | null;
  model_trained_at_20d: string | null;
  mae_1d: number | null;
  mae_5d: number | null;
  mae_20d: number | null;
  directional_accuracy_1d: number | null;
  directional_accuracy_5d: number | null;
  directional_accuracy_20d: number | null;
}

interface AccuracyMetrics {
  event_type: string;
  sector: string;
  total_events: number;
  events_with_data: number;
  direction_accuracy_1d: number;
  direction_accuracy_5d: number;
  direction_accuracy_20d: number;
  avg_magnitude_error_1d: number;
  avg_magnitude_error_5d: number;
  avg_magnitude_error_20d: number;
  high_confidence_accuracy_1d: number;
  high_confidence_accuracy_5d: number;
  high_confidence_accuracy_20d: number;
  high_confidence_count: number;
  avg_actual_return_1d: number;
  avg_actual_return_5d: number;
  avg_actual_return_20d: number;
}

interface EventTypeComparison {
  event_type: string;
  total_events: number;
  events_with_data: number;
  direction_accuracy_1d: number;
  direction_accuracy_5d: number;
  direction_accuracy_20d: number;
  high_confidence_accuracy_5d: number;
}

interface BacktestingSummary {
  overall: AccuracyMetrics;
  best_event_types: EventTypeComparison[];
  worst_event_types: EventTypeComparison[];
  total_event_types_analyzed: number;
}

interface MLModelInfo {
  name: string;
  version: string;
  status: string;
  feature_version: string;
  trained_at: string;
  promoted_at: string | null;
  metrics: {
    mae: number;
    rmse: number;
    r2: number;
    directional_accuracy: number;
    sharpe_ratio: number;
    max_error: number;
    n_train: number;
    n_test: number;
    feature_importance: Record<string, number>;
  };
}

interface MLMonitoringDashboard {
  labeled_events: {
    total_labeled_events: number;
    unique_tickers: number;
    labeled_by_family: Record<string, {1: number, 5: number, 20: number, tickers: number}>;
    labeled_by_horizon: {1: number, 5: number, 20: number};
    earliest_label_date: string | null;
    latest_label_date: string | null;
  };
  accuracy_by_horizon: Array<{
    horizon: string;
    total_samples: number;
    directional_accuracy: number | null;
    high_confidence_accuracy: number | null;
    high_confidence_samples: number;
    mae: number | null;
    rmse: number | null;
  }>;
  calibration_by_horizon: Array<{
    horizon: string;
    buckets: Array<{
      score_range: string;
      predicted_avg: number;
      actual_avg: number;
      sample_count: number;
      calibration_error: number;
    }>;
    overall_calibration_error: number;
  }>;
  family_model_status: Array<{
    family: string;
    display_name: string;
    labeled_events_1d: number;
    labeled_events_5d: number;
    labeled_events_20d: number;
    unique_tickers: number;
    model_type_1d: string;
    model_type_5d: string;
    model_type_20d: string;
    health_status_1d: string;
    health_status_5d: string;
    health_status_20d: string;
    directional_accuracy_1d: number | null;
    directional_accuracy_5d: number | null;
    directional_accuracy_20d: number | null;
  }>;
  generated_at: string;
}

const defaultMetrics: AccuracyMetrics = {
  event_type: 'all',
  sector: 'all',
  total_events: 0,
  events_with_data: 0,
  direction_accuracy_1d: 0,
  direction_accuracy_5d: 0,
  direction_accuracy_20d: 0,
  avg_magnitude_error_1d: 0,
  avg_magnitude_error_5d: 0,
  avg_magnitude_error_20d: 0,
  high_confidence_accuracy_1d: 0,
  high_confidence_accuracy_5d: 0,
  high_confidence_accuracy_20d: 0,
  high_confidence_count: 0,
  avg_actual_return_1d: 0,
  avg_actual_return_5d: 0,
  avg_actual_return_20d: 0,
};

export function BacktestingTab() {
  const router = useRouter();
  const { mode } = useDashboardModeStore();
  const [summary, setSummary] = useState<BacktestingSummary | null>(null);
  const [metrics, setMetrics] = useState<AccuracyMetrics>(defaultMetrics);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [eventType, setEventType] = useState('');
  const [sector, setSector] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [viewMode, setViewMode] = useState<'summary' | 'detailed'>('summary');
  const viewModeRef = useRef<'summary' | 'detailed'>('summary');
  
  const [mlModels, setMlModels] = useState<MLModelInfo[]>([]);
  const [mlLoading, setMlLoading] = useState(false);
  
  const [coverage, setCoverage] = useState<FamilyCoverageResponse[]>([]);
  const [coverageLoading, setCoverageLoading] = useState(false);
  const [coverageError, setCoverageError] = useState<string | null>(null);
  const [expandedFamilies, setExpandedFamilies] = useState<Set<string>>(new Set());
  
  const [monitoringData, setMonitoringData] = useState<MLMonitoringDashboard | null>(null);
  const [monitoringLoading, setMonitoringLoading] = useState(false);
  const [monitoringError, setMonitoringError] = useState<string | null>(null);
  const [expandedMonitoringFamilies, setExpandedMonitoringFamilies] = useState<Set<string>>(new Set());
  
  const [freshnessData, setFreshnessData] = useState<Array<{
    metric_key: string;
    scope: string;
    sample_count: number;
    freshness_ts: string;
    source_job: string;
    quality_grade: 'excellent' | 'good' | 'fair' | 'stale';
  }>>([]);
  const [freshnessLoading, setFreshnessLoading] = useState(false);
  
  const [modelVersion, setModelVersion] = useState<DisplayVersion>('v1.5');

  const getScoreType = (version: DisplayVersion): string => {
    switch (version) {
      case 'v1.0':
        return 'impact_score';
      case 'v1.5':
      case 'v2.0':
        return 'ml_adjusted_score';
      default:
        return 'ml_adjusted_score';
    }
  };

  const loadCoverage = async () => {
    try {
      setCoverageLoading(true);
      setCoverageError(null);
      
      const params = new URLSearchParams();
      if (mode) params.append('mode', mode);
      params.append('score_type', getScoreType(modelVersion));
      
      const url = `/api/proxy/backtesting/coverage${params.toString() ? '?' + params.toString() : ''}`;
      const data = await apiRequest<FamilyCoverageResponse[]>(url);
      setCoverage(data);
    } catch (err: any) {
      console.error('Failed to load coverage data:', err);
      if (err?.status === 403 || err?.message?.includes('403')) {
        setCoverageError('Access not available, please upgrade plan');
      } else {
        setCoverageError(err?.message || 'Failed to load coverage data');
      }
    } finally {
      setCoverageLoading(false);
    }
  };

  const loadSummary = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const params = new URLSearchParams();
      if (mode) params.append('mode', mode);
      params.append('score_type', getScoreType(modelVersion));
      
      const url = `/api/proxy/backtesting/summary${params.toString() ? '?' + params.toString() : ''}`;
      const data = await apiRequest<BacktestingSummary>(url);
      setSummary(data);
      // Only update metrics if we're still in summary mode (prevent race condition)
      if (viewModeRef.current === 'summary') {
        // Merge with defaults to ensure all properties exist
        setMetrics({ ...defaultMetrics, ...data.overall });
      }
    } catch (err: any) {
      console.error('Failed to load backtesting summary:', err);
      if (err?.status === 403 || err?.message?.includes('403')) {
        setError('Access not available, please upgrade plan');
      } else {
        setError(err?.message || 'Failed to load backtesting data');
      }
    } finally {
      setLoading(false);
    }
  };

  const loadDetailedMetrics = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const params = new URLSearchParams();
      if (eventType) params.append('event_type', eventType);
      if (sector) params.append('sector', sector);
      params.append('limit', '100');
      if (mode) params.append('mode', mode);
      params.append('score_type', getScoreType(modelVersion));
      
      const url = `/api/proxy/backtesting/accuracy?${params.toString()}`;
      const data = await apiRequest<AccuracyMetrics>(url);
      // Merge with defaults to ensure all properties exist
      setMetrics({ ...defaultMetrics, ...data });
    } catch (err: any) {
      console.error('Failed to load detailed metrics:', err);
      if (err?.status === 403 || err?.message?.includes('403')) {
        setError('Access not available, please upgrade plan');
      } else {
        setError(err?.message || 'Failed to load detailed metrics');
      }
    } finally {
      setLoading(false);
    }
  };

  const loadFreshness = async () => {
    try {
      setFreshnessLoading(true);
      const params = new URLSearchParams();
      if (mode) params.append('mode', mode);
      
      const url = `/api/proxy/data-quality/freshness${params.toString() ? '?' + params.toString() : ''}`;
      const data = await apiRequest<Array<{
        metric_key: string;
        scope: string;
        sample_count: number;
        freshness_ts: string;
        source_job: string;
        quality_grade: 'excellent' | 'good' | 'fair' | 'stale';
      }>>(url);
      setFreshnessData(data);
    } catch (err: any) {
      console.error('Failed to load freshness data:', err);
    } finally {
      setFreshnessLoading(false);
    }
  };

  useEffect(() => {
    if (viewMode === 'summary') {
      loadSummary();
    } else {
      loadDetailedMetrics();
    }
    loadMLModels();
    loadCoverage();
    loadMonitoring();
    loadFreshness();
  }, [mode, viewMode, modelVersion]);

  const handleSearch = () => {
    if (viewMode === 'detailed') {
      loadDetailedMetrics();
    }
  };

  const handleReset = () => {
    setEventType('');
    setSector('');
    if (viewMode === 'detailed') {
      loadDetailedMetrics();
    }
  };

  const loadMLModels = async () => {
    try {
      setMlLoading(true);
      const response = await apiRequest<{
        families: Array<{
          family: string;
          display_name: string;
          has_dedicated_model: boolean;
          model: MLModelInfo | null;
          sample_count: number;
          event_types_in_family: string[];
        }>;
        total_families: number;
        families_with_models: number;
        global_model: MLModelInfo | null;
      }>('/api/proxy/ml-scores/model-info');
      
      // Extract models from families that have dedicated models
      const models = response.families
        .filter(f => f.model !== null)
        .map(f => f.model!);
      
      // Add global model if it exists
      if (response.global_model) {
        models.push(response.global_model);
      }
      
      setMlModels(models);
    } catch (err: any) {
      console.error('Failed to load ML models:', err);
    } finally {
      setMlLoading(false);
    }
  };

  const loadMonitoring = async () => {
    try {
      setMonitoringLoading(true);
      setMonitoringError(null);
      
      const params = new URLSearchParams();
      if (mode) params.append('mode', mode);
      
      const url = `/api/proxy/ml-scores/monitoring${params.toString() ? '?' + params.toString() : ''}`;
      const data = await apiRequest<MLMonitoringDashboard>(url);
      setMonitoringData(data);
    } catch (err: any) {
      console.error('Failed to load monitoring data:', err);
      if (err?.status === 403 || err?.message?.includes('403')) {
        setMonitoringError('Access not available, please upgrade plan');
      } else {
        setMonitoringError(err?.message || 'Failed to load monitoring data');
      }
    } finally {
      setMonitoringLoading(false);
    }
  };

  const CircularProgress = ({ value, size = 120, strokeWidth = 8, label }: { 
    value: number; 
    size?: number; 
    strokeWidth?: number;
    label: string;
  }) => {
    const radius = (size - strokeWidth) / 2;
    const circumference = radius * 2 * Math.PI;
    const offset = circumference - (value / 100) * circumference;
    
    const getColor = (val: number) => {
      if (val >= 70) return 'var(--success)';
      if (val >= 50) return 'var(--warning)';
      return 'var(--error)';
    };

    return (
      <div className="flex flex-col items-center gap-2">
        <svg width={size} height={size} className="transform -rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="currentColor"
            strokeWidth={strokeWidth}
            fill="none"
            className="text-[--border]"
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke={getColor(value)}
            strokeWidth={strokeWidth}
            fill="none"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className="transition-all duration-1000"
          />
          <text
            x={size / 2}
            y={size / 2}
            className="text-2xl font-bold"
            fill="currentColor"
            textAnchor="middle"
            dominantBaseline="middle"
            transform={`rotate(90 ${size / 2} ${size / 2})`}
          >
            {value.toFixed(1)}%
          </text>
        </svg>
        <p className="text-sm text-[--muted]">{label}</p>
      </div>
    );
  };

  if (loading && !metrics) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-2">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[--primary]"></div>
        <p className="text-[--muted]">Loading backtesting data...</p>
      </div>
    );
  }

  if (error && !metrics) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
        <div className="text-center max-w-md">
          <div className="mb-4 inline-flex items-center justify-center w-16 h-16 rounded-full bg-[--error-light]">
            <Info className="h-8 w-8 text-[--error]" />
          </div>
          <h3 className="text-lg font-semibold text-[--text] mb-2">Backtesting Data Unavailable</h3>
          <p className="text-[--error] mb-1">{error}</p>
          <p className="text-sm text-[--muted] mb-4">
            This may be because backtesting data hasn't been generated yet, or the backend service is temporarily unavailable.
          </p>
          <Button onClick={loadSummary}>Retry</Button>
        </div>
      </div>
    );
  }

  if (!loading && !error && !metrics) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
        <div className="text-center max-w-md">
          <div className="mb-4 inline-flex items-center justify-center w-16 h-16 rounded-full bg-[--primary-light]">
            <BarChart3 className="h-8 w-8 text-[--primary]" />
          </div>
          <h3 className="text-lg font-semibold text-[--text] mb-2">No Backtesting Data Yet</h3>
          <p className="text-sm text-[--muted] mb-4">
            Backtesting data will appear here once historical event accuracy has been analyzed. 
            This usually takes 24-48 hours after initial setup.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-2xl font-bold text-[--text]">Backtesting & Accuracy</h2>
          <p className="text-sm text-[--muted]">Validate prediction accuracy against actual price movements</p>
        </div>
        <div className="flex items-center gap-4 flex-wrap">
          <ModelVersionFilter value={modelVersion} onChange={setModelVersion} />
        </div>
      </div>

      {!loading && metrics.total_events < 10 && metrics.total_events > 0 && (
        <div className="bg-[--primary-light] border border-[--border] rounded-lg p-4">
          <div className="flex items-start gap-3">
            <Info className="h-5 w-5 text-[--primary] mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <h4 className="text-sm font-semibold text-[--primary] mb-1">Limited Backtesting Data</h4>
              <p className="text-sm text-[--muted]">
                Events must be at least 21 days old to be backtested. Companies with longer tracking histories tend to have more accurate event data and predictions. As more events age and predictions with higher confidence scores accumulate, you'll see more meaningful accuracy metrics. This is normal for new portfolios or recently tracked companies.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ML Monitoring Overview Section */}
      <div className="bg-gradient-to-br from-emerald-500/10 to-teal-500/10 border border-emerald-500/30 rounded-lg p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-xl font-bold text-[--text] mb-2">ML Monitoring Overview</h3>
            <p className="text-sm text-[--muted]">Real-time tracking of model training data, accuracy, calibration, and health metrics</p>
          </div>
          <Button
            onClick={() => router.push('/dashboard/data-quality')}
            variant="outline"
            className="flex items-center gap-2"
          >
            <ExternalLink className="h-4 w-4" />
            View Data Quality Dashboard
          </Button>
        </div>

        {/* Data Freshness Badges */}
        {!freshnessLoading && freshnessData.length > 0 && (
          <div className="mb-6 bg-[--surface-muted] rounded-lg p-4 border border-[--border]">
            <h4 className="text-sm font-semibold text-[--text] mb-3">Key Metrics Freshness</h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {freshnessData.slice(0, 3).map((metric) => (
                <FreshnessBadge
                  key={metric.metric_key}
                  metric_key={metric.metric_key}
                  freshness_ts={metric.freshness_ts}
                  sample_count={metric.sample_count}
                  quality_grade={metric.quality_grade}
                />
              ))}
            </div>
          </div>
        )}

        {monitoringLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[--success]"></div>
          </div>
        ) : monitoringError ? (
          <div className="bg-[--error-light] border border-[--border] rounded-lg p-4">
            <p className="text-sm text-[--error]">{monitoringError}</p>
          </div>
        ) : !monitoringData ? (
          <div className="bg-[--surface-muted] rounded-lg p-8 text-center">
            <Info className="h-12 w-12 text-[--muted] mx-auto mb-3" />
            <p className="text-[--muted]">No monitoring data available yet</p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Labeled Data Panel */}
            {monitoringData.labeled_events && (
            <div className="bg-[--surface-muted] rounded-lg p-6 border border-[--border]">
              <div className="flex items-center gap-2 mb-4">
                <Target className="h-5 w-5 text-[--success]" />
                <h4 className="text-lg font-semibold text-[--text]">Labeled Training Data</h4>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div className="bg-[--surface-glass] rounded-lg p-4">
                  <p className="text-sm text-[--muted] mb-1">Total Labeled Events</p>
                  <p className="text-3xl font-bold text-[--success]">{monitoringData.labeled_events.total_labeled_events ?? 0}</p>
                </div>
                <div className="bg-[--surface-glass] rounded-lg p-4">
                  <p className="text-sm text-[--muted] mb-1">Unique Tickers</p>
                  <p className="text-3xl font-bold text-[--accent]">{monitoringData.labeled_events.unique_tickers ?? 0}</p>
                </div>
                <div className="bg-[--surface-glass] rounded-lg p-4">
                  <p className="text-sm text-[--muted] mb-1">Date Range</p>
                  <p className="text-sm font-semibold text-[--text]">
                    {monitoringData.labeled_events.earliest_label_date && monitoringData.labeled_events.latest_label_date ? (
                      <>
                        {new Date(monitoringData.labeled_events.earliest_label_date).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })} - {new Date(monitoringData.labeled_events.latest_label_date).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })}
                      </>
                    ) : 'N/A'}
                  </p>
                </div>
              </div>

              {monitoringData.labeled_events.labeled_by_family && (
              <div className="space-y-3">
                <h5 className="text-sm font-semibold text-[--text]">Breakdown by Event Family</h5>
                {Object.entries(monitoringData.labeled_events.labeled_by_family).map(([family, data]) => (
                  <div key={family} className="bg-[--surface-glass] rounded-lg p-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium text-[--text]">{family}</span>
                      <span className="text-xs text-[--muted]">{data.tickers} tickers</span>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-xs">
                      <div>
                        <span className="text-[--muted]">1d: </span>
                        <span className="font-semibold text-[--text]">{data['1']}</span>
                      </div>
                      <div>
                        <span className="text-[--muted]">5d: </span>
                        <span className="font-semibold text-[--text]">{data['5']}</span>
                      </div>
                      <div>
                        <span className="text-[--muted]">20d: </span>
                        <span className="font-semibold text-[--text]">{data['20']}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              )}
            </div>
            )}

            {/* Accuracy Panel */}
            {monitoringData.accuracy_by_horizon && monitoringData.accuracy_by_horizon.length > 0 && (
            <div className="bg-[--surface-muted] rounded-lg p-6 border border-[--border]">
              <div className="flex items-center gap-2 mb-4">
                <TrendingUp className="h-5 w-5 text-[--success]" />
                <h4 className="text-lg font-semibold text-[--text]">Accuracy by Horizon</h4>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {monitoringData.accuracy_by_horizon.map((horizonData) => (
                  <div key={horizonData.horizon} className="bg-[--surface-glass] rounded-lg p-4 border border-[--border]">
                    <div className="flex items-center justify-between mb-3">
                      <h5 className="font-semibold text-[--text]">{horizonData.horizon} Horizon</h5>
                      <span className="text-xs text-[--muted]">{horizonData.total_samples} samples</span>
                    </div>

                    <div className="space-y-3">
                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs text-[--muted]">Directional Accuracy</span>
                          <span className={`text-sm font-bold ${
                            horizonData.directional_accuracy !== null && horizonData.directional_accuracy >= 55 
                              ? 'text-[--success]' 
                              : 'text-[--warning]'
                          }`}>
                            {horizonData.directional_accuracy !== null 
                              ? `${horizonData.directional_accuracy.toFixed(1)}%` 
                              : 'N/A'}
                          </span>
                        </div>
                        {horizonData.directional_accuracy !== null && (
                          <div className="w-full bg-[--surface-glass] rounded-full h-1.5">
                            <div
                              className={`h-1.5 rounded-full ${
                                horizonData.directional_accuracy >= 55 ? 'bg-[--success]' : 'bg-[--warning]'
                              }`}
                              style={{ width: `${Math.min(horizonData.directional_accuracy, 100)}%` }}
                            />
                          </div>
                        )}
                      </div>

                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs text-[--muted]">High Confidence Accuracy</span>
                          <span className="text-sm font-semibold text-[--text]">
                            {horizonData.high_confidence_accuracy !== null 
                              ? `${horizonData.high_confidence_accuracy.toFixed(1)}%` 
                              : 'N/A'}
                          </span>
                        </div>
                        <span className="text-xs text-[--muted]">{horizonData.high_confidence_samples} high-conf samples</span>
                      </div>

                      <div className="pt-2 border-t border-[--border]">
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-[--muted]">MAE</span>
                          <span className="text-sm font-semibold text-[--text]">
                            {horizonData.mae !== null ? `${horizonData.mae.toFixed(2)}%` : 'N/A'}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            )}

            {/* Calibration Panel */}
            {monitoringData.calibration_by_horizon && monitoringData.calibration_by_horizon.length > 0 && (
            <div className="bg-[--surface-muted] rounded-lg p-6 border border-[--border]">
              <div className="flex items-center gap-2 mb-4">
                <BarChart3 className="h-5 w-5 text-[--success]" />
                <h4 className="text-lg font-semibold text-[--text]">Model Calibration</h4>
              </div>

              <div className="space-y-6">
                {monitoringData.calibration_by_horizon.map((horizonCal) => (
                  <div key={horizonCal.horizon}>
                    <div className="flex items-center justify-between mb-3">
                      <h5 className="font-semibold text-[--text]">{horizonCal.horizon} Horizon</h5>
                      <span className="text-xs px-2 py-1 rounded bg-[--success-soft] text-[--success]">
                        Overall Error: {horizonCal.overall_calibration_error.toFixed(2)}%
                      </span>
                    </div>

                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-[--border]">
                            <th className="text-left py-2 px-3 text-xs font-semibold text-[--muted]">Score Range</th>
                            <th className="text-right py-2 px-3 text-xs font-semibold text-[--muted]">Predicted Avg</th>
                            <th className="text-right py-2 px-3 text-xs font-semibold text-[--muted]">Actual Avg</th>
                            <th className="text-right py-2 px-3 text-xs font-semibold text-[--muted]">Samples</th>
                            <th className="text-right py-2 px-3 text-xs font-semibold text-[--muted]">Cal. Error</th>
                          </tr>
                        </thead>
                        <tbody>
                          {horizonCal.buckets.map((bucket, idx) => (
                            <tr key={idx} className="border-b border-[--border-muted] hover:bg-[--surface-hover]">
                              <td className="py-2 px-3 font-medium text-[--text]">{bucket.score_range}</td>
                              <td className="py-2 px-3 text-right text-[--text]">
                                {bucket.predicted_avg.toFixed(2)}%
                              </td>
                              <td className="py-2 px-3 text-right text-[--text]">
                                {bucket.actual_avg.toFixed(2)}%
                              </td>
                              <td className="py-2 px-3 text-right text-[--muted]">{bucket.sample_count}</td>
                              <td className={`py-2 px-3 text-right font-semibold ${
                                Math.abs(bucket.calibration_error) < 5 ? 'text-[--success]' : 
                                Math.abs(bucket.calibration_error) < 10 ? 'text-[--warning]' : 'text-[--error]'
                              }`}>
                                {bucket.calibration_error.toFixed(2)}%
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            )}

            {/* Family Health Panel */}
            {monitoringData.family_model_status && monitoringData.family_model_status.length > 0 && (
            <div className="bg-[--surface-muted] rounded-lg p-6 border border-[--border]">
              <div className="flex items-center gap-2 mb-4">
                <Cpu className="h-5 w-5 text-[--success]" />
                <h4 className="text-lg font-semibold text-[--text]">Family Model Health</h4>
              </div>

              <div className="space-y-3">
                {monitoringData.family_model_status.map((family) => {
                  const isExpanded = expandedMonitoringFamilies.has(family.family);
                  const toggleExpand = () => {
                    const newExpanded = new Set(expandedMonitoringFamilies);
                    if (isExpanded) {
                      newExpanded.delete(family.family);
                    } else {
                      newExpanded.add(family.family);
                    }
                    setExpandedMonitoringFamilies(newExpanded);
                  };

                  const getHealthColor = (status: string) => {
                    if (status === 'Production Ready') return 'text-[--success] bg-[--success-soft] border-[--border-strong]';
                    if (status === 'Prototype') return 'text-[--warning] bg-[--warning-soft] border-[--border-strong]';
                    return 'text-[--muted] bg-[--muted-soft] border-[--border-strong]';
                  };

                  const getHealthIcon = (status: string) => {
                    if (status === 'Production Ready') return <CheckCircle className="h-4 w-4" />;
                    if (status === 'Prototype') return <AlertTriangle className="h-4 w-4" />;
                    return <XCircle className="h-4 w-4" />;
                  };

                  return (
                    <div key={family.family} className="bg-[--surface-glass] rounded-lg border border-[--border] overflow-hidden">
                      <div 
                        className="p-4 cursor-pointer hover:bg-[--surface-hover] transition-colors"
                        onClick={toggleExpand}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3 flex-1">
                            {isExpanded ? (
                              <ChevronDown className="h-5 w-5 text-[--muted]" />
                            ) : (
                              <ChevronRight className="h-5 w-5 text-[--muted]" />
                            )}
                            <div>
                              <h5 className="font-semibold text-[--text]">{family.display_name}</h5>
                              <p className="text-xs text-[--muted]">{family.unique_tickers} tickers tracked</p>
                            </div>
                          </div>

                          <div className="flex items-center gap-2">
                            {[
                              { horizon: '1d', status: family.health_status_1d, type: family.model_type_1d },
                              { horizon: '5d', status: family.health_status_5d, type: family.model_type_5d },
                              { horizon: '20d', status: family.health_status_20d, type: family.model_type_20d }
                            ].map(({ horizon, status }) => (
                              <div key={horizon} className={`px-2 py-1 rounded border text-xs font-medium flex items-center gap-1 ${getHealthColor(status)}`}>
                                {getHealthIcon(status)}
                                <span>{horizon}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>

                      {isExpanded && (
                        <div className="border-t border-[--border] p-4 bg-[--surface-glass]">
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            {[
                              { 
                                horizon: '1-Day', 
                                events: family.labeled_events_1d, 
                                type: family.model_type_1d, 
                                status: family.health_status_1d,
                                accuracy: family.directional_accuracy_1d 
                              },
                              { 
                                horizon: '5-Day', 
                                events: family.labeled_events_5d, 
                                type: family.model_type_5d, 
                                status: family.health_status_5d,
                                accuracy: family.directional_accuracy_5d 
                              },
                              { 
                                horizon: '20-Day', 
                                events: family.labeled_events_20d, 
                                type: family.model_type_20d, 
                                status: family.health_status_20d,
                                accuracy: family.directional_accuracy_20d 
                              }
                            ].map((h) => (
                              <div key={h.horizon} className="space-y-2">
                                <h6 className="text-sm font-semibold text-[--text]">{h.horizon}</h6>
                                <div className={`px-2 py-1 rounded border text-xs font-medium ${getHealthColor(h.status)}`}>
                                  {h.status}
                                </div>
                                <div className="text-xs space-y-1">
                                  <div className="flex justify-between">
                                    <span className="text-[--muted]">Model Type:</span>
                                    <span className="text-[--text] font-medium">{h.type.replace('-', ' ')}</span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span className="text-[--muted]">Training Events:</span>
                                    <span className="text-[--text] font-medium">{h.events}</span>
                                  </div>
                                  {h.accuracy !== null && (
                                    <div className="flex justify-between">
                                      <span className="text-[--muted]">Accuracy:</span>
                                      <span className={`font-semibold ${
                                        h.accuracy >= 55 ? 'text-[--success]' : 'text-[--warning]'
                                      }`}>
                                        {h.accuracy.toFixed(1)}%
                                      </span>
                                    </div>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
            )}

            {/* Timestamp */}
            {monitoringData.generated_at && (
            <div className="text-xs text-[--muted] text-right">
              Generated at: {new Date(monitoringData.generated_at).toLocaleString()}
            </div>
            )}
          </div>
        )}
      </div>

      {/* ML Model Coverage Section */}
      <div className="bg-gradient-to-br from-indigo-500/10 to-purple-500/10 border border-indigo-500/30 rounded-lg p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-xl font-bold text-[--text] mb-2">ML Model Coverage by Event Family</h3>
            <p className="text-sm text-[--muted]">Training status and performance of Market Echo Engine models for each event category</p>
          </div>
        </div>

        {coverageLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[--primary]"></div>
          </div>
        ) : coverageError ? (
          <div className="bg-[--error-light] border border-[--border] rounded-lg p-4">
            <p className="text-sm text-[--error]">{coverageError}</p>
          </div>
        ) : coverage.length === 0 ? (
          <div className="bg-[--surface-muted] rounded-lg p-8 text-center">
            <Info className="h-12 w-12 text-[--muted] mx-auto mb-3" />
            <p className="text-[--muted]">No coverage data available yet</p>
          </div>
        ) : (
          <>
            {/* Callout about current model coverage */}
            <div className="bg-[--primary-light] border border-[--border-strong] rounded-lg p-4 mb-6">
              <div className="flex items-start gap-3">
                <Cpu className="h-5 w-5 text-[--primary] flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-sm font-semibold text-[--text] mb-1">Current Model Coverage</h4>
                  <p className="text-xs text-[--muted]">
                    SEC 8-K filings have specialized models trained on 355+ labeled events. All other event types (earnings, FDA, M&A, etc.) currently use our global model trained across all families, plus deterministic scoring. As more events accumulate labeled outcomes, additional families will receive specialized models.
                  </p>
                </div>
              </div>
            </div>

            {/* Model Source Legend */}
            <div className="bg-[--surface-muted] rounded-lg p-4 mb-6 border border-[--border]">
              <h4 className="text-sm font-semibold text-[--text] mb-3">Model Types</h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <CheckCircle className="h-4 w-4 text-[--success]" />
                    <span className="font-semibold text-[--text]">Production Ready (Family-Specific)</span>
                  </div>
                  <p className="text-[--muted]">150+ labeled events from 75+ companies trained specialized model for this event family (SEC 8-K only currently)</p>
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <Cpu className="h-4 w-4 text-[--primary]" />
                    <span className="font-semibold text-[--text]">Global Model (Experimental)</span>
                  </div>
                  <p className="text-[--muted]">Uses global ML model trained across all event types until family-specific model available</p>
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <Target className="h-4 w-4 text-[--muted]" />
                    <span className="font-semibold text-[--text]">Deterministic Only</span>
                  </div>
                  <p className="text-[--muted]">Using rule-based scoring, insufficient data for ML predictions</p>
                </div>
              </div>
            </div>

            {/* Family Coverage Table */}
            <div className="space-y-3">
              {coverage.map((family) => {
                const isExpanded = expandedFamilies.has(family.family);
                const toggleExpand = () => {
                  const newExpanded = new Set(expandedFamilies);
                  if (isExpanded) {
                    newExpanded.delete(family.family);
                  } else {
                    newExpanded.add(family.family);
                  }
                  setExpandedFamilies(newExpanded);
                };

                const getStatusColor = (status: string) => {
                  if (status === 'active') return 'text-[--success] bg-[--success-soft] border-[--border-strong]';
                  if (status === 'staging') return 'text-[--warning] bg-[--warning-soft] border-[--border-strong]';
                  return 'text-[--muted] bg-[--muted-soft] border-[--border-strong]';
                };

                const getStatusIcon = (status: string, labeledCount: number) => {
                  if (status === 'active' && labeledCount >= 150) return <CheckCircle className="h-4 w-4" />;
                  if (status === 'staging' || (status === 'active' && labeledCount < 150)) return <AlertTriangle className="h-4 w-4" />;
                  return <XCircle className="h-4 w-4" />;
                };

                const getStatusLabel = (status: string, source: string, labeledCount: number) => {
                  if (status === 'active' && source === 'family-specific') return 'Family Model';
                  if (status === 'active' && source === 'global') return 'Global Model';
                  if (status === 'staging') return 'Global Model';
                  if (source === 'deterministic') return 'Deterministic';
                  return 'No Model';
                };

                const getSampleProgress = (labeledCount: number) => {
                  const target = 150;
                  const percentage = Math.min((labeledCount / target) * 100, 100);
                  return { percentage, target };
                };

                return (
                  <div key={family.family} className="bg-[--surface-muted] rounded-lg border border-[--border] overflow-hidden">
                    {/* Family Header */}
                    <div 
                      className="p-4 cursor-pointer hover:bg-[--surface-hover] transition-colors"
                      onClick={toggleExpand}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3 flex-1">
                          {isExpanded ? (
                            <ChevronDown className="h-5 w-5 text-[--muted]" />
                          ) : (
                            <ChevronRight className="h-5 w-5 text-[--muted]" />
                          )}
                          <div>
                            <h4 className="font-semibold text-[--text]">{family.family_display_name}</h4>
                            <p className="text-xs text-[--muted]">{family.total_events} total events</p>
                          </div>
                        </div>

                        {/* Quick Status Overview */}
                        <div className="flex items-center gap-2">
                          {[
                            { horizon: '1d', status: family.model_status_1d, source: family.model_source_1d, count: family.labeled_count_1d },
                            { horizon: '5d', status: family.model_status_5d, source: family.model_source_5d, count: family.labeled_count_5d },
                            { horizon: '20d', status: family.model_status_20d, source: family.model_source_20d, count: family.labeled_count_20d }
                          ].map(({ horizon, status, source, count }) => (
                            <div key={horizon} className={`px-2 py-1 rounded border text-xs font-medium flex items-center gap-1 ${getStatusColor(status)}`}>
                              {getStatusIcon(status, count)}
                              <span>{horizon}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>

                    {/* Expanded Details */}
                    {isExpanded && (
                      <div className="border-t border-[--border] p-4 bg-[--surface-muted]">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                          {/* 1-Day Horizon */}
                          <div className="space-y-3">
                            <div className="flex items-center justify-between">
                              <h5 className="text-sm font-semibold text-[--text]">1-Day Horizon</h5>
                              <span className={`px-2 py-1 rounded border text-xs font-medium flex items-center gap-1 ${getStatusColor(family.model_status_1d)}`}>
                                {getStatusIcon(family.model_status_1d, family.labeled_count_1d)}
                                {getStatusLabel(family.model_status_1d, family.model_source_1d, family.labeled_count_1d)}
                              </span>
                            </div>

                            <div>
                              <div className="flex items-center justify-between mb-1">
                                <span className="text-xs text-[--muted]">Training Data</span>
                                <span className="text-xs font-semibold text-[--text]">
                                  {family.labeled_count_1d}/{getSampleProgress(family.labeled_count_1d).target}
                                </span>
                              </div>
                              <div className="w-full bg-[--surface-glass] rounded-full h-1.5">
                                <div
                                  className={`h-1.5 rounded-full transition-all ${
                                    family.labeled_count_1d >= 150 ? 'bg-[--success]' :
                                    family.labeled_count_1d >= 50 ? 'bg-[--warning]' : 'bg-[--muted]'
                                  }`}
                                  style={{ width: `${getSampleProgress(family.labeled_count_1d).percentage}%` }}
                                />
                              </div>
                            </div>

                            {family.directional_accuracy_1d !== null && (
                              <div>
                                <div className="flex items-center justify-between mb-1">
                                  <span className="text-xs text-[--muted]">Direction Accuracy</span>
                                  <span className="text-xs font-semibold text-[--text]">
                                    {(family.directional_accuracy_1d * 100).toFixed(1)}%
                                  </span>
                                </div>
                                {family.mae_1d !== null && (
                                  <div className="flex items-center justify-between">
                                    <span className="text-xs text-[--muted]">Error (MAE)</span>
                                    <span className="text-xs font-semibold text-[--text]">
                                      {(family.mae_1d * 100).toFixed(2)}%
                                    </span>
                                  </div>
                                )}
                              </div>
                            )}

                            {family.model_version_1d && (
                              <div className="text-xs text-[--muted] pt-2 border-t border-[--border]">
                                <div>Model: {family.model_version_1d}</div>
                                {family.model_trained_at_1d && (
                                  <div>Trained: {new Date(family.model_trained_at_1d).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })}</div>
                                )}
                              </div>
                            )}

                            <div className="text-xs text-[--muted]">
                              Source: {family.model_source_1d.replace('-', ' ')}
                            </div>
                          </div>

                          {/* 5-Day Horizon */}
                          <div className="space-y-3">
                            <div className="flex items-center justify-between">
                              <h5 className="text-sm font-semibold text-[--text]">5-Day Horizon</h5>
                              <span className={`px-2 py-1 rounded border text-xs font-medium flex items-center gap-1 ${getStatusColor(family.model_status_5d)}`}>
                                {getStatusIcon(family.model_status_5d, family.labeled_count_5d)}
                                {getStatusLabel(family.model_status_5d, family.model_source_5d, family.labeled_count_5d)}
                              </span>
                            </div>

                            <div>
                              <div className="flex items-center justify-between mb-1">
                                <span className="text-xs text-[--muted]">Training Data</span>
                                <span className="text-xs font-semibold text-[--text]">
                                  {family.labeled_count_5d}/{getSampleProgress(family.labeled_count_5d).target}
                                </span>
                              </div>
                              <div className="w-full bg-[--surface-glass] rounded-full h-1.5">
                                <div
                                  className={`h-1.5 rounded-full transition-all ${
                                    family.labeled_count_5d >= 150 ? 'bg-[--success]' :
                                    family.labeled_count_5d >= 50 ? 'bg-[--warning]' : 'bg-[--muted]'
                                  }`}
                                  style={{ width: `${getSampleProgress(family.labeled_count_5d).percentage}%` }}
                                />
                              </div>
                            </div>

                            {family.directional_accuracy_5d !== null && (
                              <div>
                                <div className="flex items-center justify-between mb-1">
                                  <span className="text-xs text-[--muted]">Direction Accuracy</span>
                                  <span className="text-xs font-semibold text-[--text]">
                                    {(family.directional_accuracy_5d * 100).toFixed(1)}%
                                  </span>
                                </div>
                                {family.mae_5d !== null && (
                                  <div className="flex items-center justify-between">
                                    <span className="text-xs text-[--muted]">Error (MAE)</span>
                                    <span className="text-xs font-semibold text-[--text]">
                                      {(family.mae_5d * 100).toFixed(2)}%
                                    </span>
                                  </div>
                                )}
                              </div>
                            )}

                            {family.model_version_5d && (
                              <div className="text-xs text-[--muted] pt-2 border-t border-[--border]">
                                <div>Model: {family.model_version_5d}</div>
                                {family.model_trained_at_5d && (
                                  <div>Trained: {new Date(family.model_trained_at_5d).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })}</div>
                                )}
                              </div>
                            )}

                            <div className="text-xs text-[--muted]">
                              Source: {family.model_source_5d.replace('-', ' ')}
                            </div>
                          </div>

                          {/* 20-Day Horizon */}
                          <div className="space-y-3">
                            <div className="flex items-center justify-between">
                              <h5 className="text-sm font-semibold text-[--text]">20-Day Horizon</h5>
                              <span className={`px-2 py-1 rounded border text-xs font-medium flex items-center gap-1 ${getStatusColor(family.model_status_20d)}`}>
                                {getStatusIcon(family.model_status_20d, family.labeled_count_20d)}
                                {getStatusLabel(family.model_status_20d, family.model_source_20d, family.labeled_count_20d)}
                              </span>
                            </div>

                            <div>
                              <div className="flex items-center justify-between mb-1">
                                <span className="text-xs text-[--muted]">Training Data</span>
                                <span className="text-xs font-semibold text-[--text]">
                                  {family.labeled_count_20d}/{getSampleProgress(family.labeled_count_20d).target}
                                </span>
                              </div>
                              <div className="w-full bg-[--surface-glass] rounded-full h-1.5">
                                <div
                                  className={`h-1.5 rounded-full transition-all ${
                                    family.labeled_count_20d >= 150 ? 'bg-[--success]' :
                                    family.labeled_count_20d >= 50 ? 'bg-[--warning]' : 'bg-[--muted]'
                                  }`}
                                  style={{ width: `${getSampleProgress(family.labeled_count_20d).percentage}%` }}
                                />
                              </div>
                            </div>

                            {family.directional_accuracy_20d !== null && (
                              <div>
                                <div className="flex items-center justify-between mb-1">
                                  <span className="text-xs text-[--muted]">Direction Accuracy</span>
                                  <span className="text-xs font-semibold text-[--text]">
                                    {(family.directional_accuracy_20d * 100).toFixed(1)}%
                                  </span>
                                </div>
                                {family.mae_20d !== null && (
                                  <div className="flex items-center justify-between">
                                    <span className="text-xs text-[--muted]">Error (MAE)</span>
                                    <span className="text-xs font-semibold text-[--text]">
                                      {(family.mae_20d * 100).toFixed(2)}%
                                    </span>
                                  </div>
                                )}
                              </div>
                            )}

                            {family.model_version_20d && (
                              <div className="text-xs text-[--muted] pt-2 border-t border-[--border]">
                                <div>Model: {family.model_version_20d}</div>
                                {family.model_trained_at_20d && (
                                  <div>Trained: {new Date(family.model_trained_at_20d).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })}</div>
                                )}
                              </div>
                            )}

                            <div className="text-xs text-[--muted]">
                              Source: {family.model_source_20d.replace('-', ' ')}
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>

      {(
        <>
          {/* Overall Stats */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-[--surface-muted] rounded-lg p-4 border border-[--border]">
              <div className="flex items-center gap-2 mb-2">
                <BarChart3 className="h-5 w-5 text-[--primary]" />
                <p className="text-sm text-[--muted]">Total Events</p>
              </div>
              <p className="text-2xl font-bold text-[--text]">
                {loading ? '...' : metrics.total_events}
              </p>
              <p className="text-xs text-[--muted] mt-1">
                {loading ? '...' : `${metrics.events_with_data} with price data`}
              </p>
            </div>

            <div className="bg-[--surface-muted] rounded-lg p-4 border border-[--border]">
              <div className="flex items-center gap-2 mb-2">
                <Target className="h-5 w-5 text-[--success]" />
                <p className="text-sm text-[--muted]">High Confidence</p>
              </div>
              <p className="text-2xl font-bold text-[--text]">
                {loading ? '...' : metrics.high_confidence_count}
              </p>
              <p className="text-xs text-[--muted] mt-1">
                Predictions &gt; 70% confidence
              </p>
            </div>

            <div className="bg-[--surface-muted] rounded-lg p-4 border border-[--border]">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="h-5 w-5 text-[--primary]" />
                <p className="text-sm text-[--muted]">Avg Return (5d)</p>
              </div>
              <p className={`text-2xl font-bold ${loading ? 'text-[--text]' : (metrics.avg_actual_return_5d ?? 0) >= 0 ? 'text-[--success]' : 'text-[--error]'}`}>
                {loading ? '...' : `${(metrics.avg_actual_return_5d ?? 0) > 0 ? '+' : ''}${(metrics.avg_actual_return_5d ?? 0).toFixed(2)}%`}
              </p>
              <p className="text-xs text-[--muted] mt-1">
                Across all analyzed events
              </p>
            </div>

            <div className="bg-[--surface-muted] rounded-lg p-4 border border-[--border]">
              <div className="flex items-center gap-2 mb-2">
                <Info className="h-5 w-5 text-[--accent]" />
                <p className="text-sm text-[--muted]">Scope</p>
              </div>
              <p className="text-2xl font-bold text-[--text]">
                {loading ? '...' : (metrics.event_type === 'all' ? 'All Types' : metrics.event_type)}
              </p>
              <p className="text-xs text-[--muted] mt-1">
                {loading ? '...' : (metrics.sector === 'all' ? 'All Sectors' : metrics.sector)}
              </p>
            </div>
          </div>

          {/* Direction Accuracy Gauges */}
          <div className="bg-[--surface-muted] rounded-lg p-6 border border-[--border]">
            <h3 className="text-lg font-semibold text-[--text] mb-6">Direction Accuracy</h3>
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <p className="text-2xl font-bold text-[--muted]">Loading data...</p>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                  <CircularProgress 
                    value={metrics.direction_accuracy_1d ?? 0} 
                    label="1-Day Accuracy"
                  />
                  <CircularProgress 
                    value={metrics.direction_accuracy_5d ?? 0} 
                    label="5-Day Accuracy"
                  />
                  <CircularProgress 
                    value={metrics.direction_accuracy_20d ?? 0} 
                    label="20-Day Accuracy"
                  />
                </div>
                <p className="text-xs text-[--muted] text-center mt-6">
                  Percentage of predictions with correct directional movement
                </p>
              </>
            )}
          </div>

          {/* High Confidence Accuracy */}
          <div className="bg-[--surface-muted] rounded-lg p-6 border border-[--border]">
            <h3 className="text-lg font-semibold text-[--text] mb-4">
              High Confidence Accuracy (&gt;70% confidence)
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-[--surface-glass] rounded-lg p-4">
                <p className="text-sm text-[--muted] mb-2">1-Day</p>
                <p className="text-3xl font-bold text-[--text]">
                  {loading ? '...' : `${(metrics.high_confidence_accuracy_1d ?? 0).toFixed(1)}%`}
                </p>
              </div>
              <div className="bg-[--surface-glass] rounded-lg p-4">
                <p className="text-sm text-[--muted] mb-2">5-Day</p>
                <p className="text-3xl font-bold text-[--text]">
                  {loading ? '...' : `${(metrics.high_confidence_accuracy_5d ?? 0).toFixed(1)}%`}
                </p>
              </div>
              <div className="bg-[--surface-glass] rounded-lg p-4">
                <p className="text-sm text-[--muted] mb-2">20-Day</p>
                <p className="text-3xl font-bold text-[--text]">
                  {loading ? '...' : `${(metrics.high_confidence_accuracy_20d ?? 0).toFixed(1)}%`}
                </p>
              </div>
            </div>
          </div>

          {/* Magnitude Errors */}
          <div className="bg-[--surface-muted] rounded-lg p-6 border border-[--border]">
            <h3 className="text-lg font-semibold text-[--text] mb-4">
              Average Magnitude Error
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-[--surface-glass] rounded-lg p-4">
                <p className="text-sm text-[--muted] mb-2">1-Day Error</p>
                <p className="text-3xl font-bold text-[--text]">
                  {loading ? '...' : `${(metrics.avg_magnitude_error_1d ?? 0).toFixed(2)}%`}
                </p>
              </div>
              <div className="bg-[--surface-glass] rounded-lg p-4">
                <p className="text-sm text-[--muted] mb-2">5-Day Error</p>
                <p className="text-3xl font-bold text-[--text]">
                  {loading ? '...' : `${(metrics.avg_magnitude_error_5d ?? 0).toFixed(2)}%`}
                </p>
              </div>
              <div className="bg-[--surface-glass] rounded-lg p-4">
                <p className="text-sm text-[--muted] mb-2">20-Day Error</p>
                <p className="text-3xl font-bold text-[--text]">
                  {loading ? '...' : `${(metrics.avg_magnitude_error_20d ?? 0).toFixed(2)}%`}
                </p>
              </div>
            </div>
            <p className="text-xs text-[--muted] mt-4">
              Average difference between predicted impact score and actual absolute return (lower is better)
            </p>
          </div>
        </>
      )}

      {/* Event Type Comparison (only in summary mode) */}
      {viewMode === 'summary' && summary && (
        <>
          {summary.best_event_types && summary.best_event_types.length > 0 && (
            <div className="bg-[--surface-muted] rounded-lg p-6 border border-[--border]">
              <div className="flex items-center gap-2 mb-4">
                <TrendingUp className="h-5 w-5 text-[--success]" />
                <h3 className="text-lg font-semibold text-[--text]">
                  Best Performing Event Types
                </h3>
              </div>
              <div className="space-y-3">
                {summary.best_event_types.map((type) => (
                  <div key={type.event_type} className="bg-[--surface-glass] rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <p className="font-medium text-[--text]">{type.event_type}</p>
                      <span className="text-sm text-[--muted]">
                        {type.events_with_data} events
                      </span>
                    </div>
                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <p className="text-xs text-[--muted]">1d Accuracy</p>
                        <p className="text-lg font-semibold text-[--success]">
                          {type.direction_accuracy_1d.toFixed(1)}%
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-[--muted]">5d Accuracy</p>
                        <p className="text-lg font-semibold text-[--success]">
                          {type.direction_accuracy_5d.toFixed(1)}%
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-[--muted]">20d Accuracy</p>
                        <p className="text-lg font-semibold text-[--success]">
                          {type.direction_accuracy_20d.toFixed(1)}%
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {summary.worst_event_types && summary.worst_event_types.length > 0 && (
            <div className="bg-[--surface-muted] rounded-lg p-6 border border-[--border]">
              <div className="flex items-center gap-2 mb-4">
                <TrendingDown className="h-5 w-5 text-[--warning]" />
                <h3 className="text-lg font-semibold text-[--text]">
                  Event Types Needing Improvement
                </h3>
              </div>
              <div className="space-y-3">
                {summary.worst_event_types.map((type) => (
                  <div key={type.event_type} className="bg-[--surface-glass] rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <p className="font-medium text-[--text]">{type.event_type}</p>
                      <span className="text-sm text-[--muted]">
                        {type.events_with_data} events
                      </span>
                    </div>
                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <p className="text-xs text-[--muted]">1d Accuracy</p>
                        <p className="text-lg font-semibold text-[--warning]">
                          {type.direction_accuracy_1d.toFixed(1)}%
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-[--muted]">5d Accuracy</p>
                        <p className="text-lg font-semibold text-[--warning]">
                          {type.direction_accuracy_5d.toFixed(1)}%
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-[--muted]">20d Accuracy</p>
                        <p className="text-lg font-semibold text-[--warning]">
                          {type.direction_accuracy_20d.toFixed(1)}%
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* Market Echo Engine Section */}
      <div className="bg-gradient-to-br from-purple-500/10 to-blue-500/10 border border-purple-500/30 rounded-lg p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 bg-[--accent-soft] rounded-lg">
            <Cpu className="h-6 w-6 text-[--accent]" />
          </div>
          <div>
            <h3 className="text-xl font-bold text-[--text]">Market Echo Engine</h3>
            <p className="text-sm text-[--muted]">Self-learning AI that improves predictions using real market outcomes</p>
          </div>
        </div>

        {mlLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[--accent]"></div>
          </div>
        ) : mlModels.length > 0 ? (
          <>
            {/* ML Model Performance */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              {mlModels
                .sort((a, b) => {
                  const horizonOrder: Record<string, number> = { '1d': 1, '5d': 2, '20d': 3 };
                  const aHorizon = a.name.includes('1d') ? '1d' : a.name.includes('5d') ? '5d' : '20d';
                  const bHorizon = b.name.includes('1d') ? '1d' : b.name.includes('5d') ? '5d' : '20d';
                  return horizonOrder[aHorizon] - horizonOrder[bHorizon];
                })
                .map((model) => {
                  const horizon = model.name.includes('1d') ? '1-Day' : model.name.includes('5d') ? '5-Day' : '20-Day';
                  const dirAcc = (model.metrics.directional_accuracy * 100);
                  const mae = (model.metrics.mae * 100);
                  const isProfitable = dirAcc >= 55;
                  const needsData = model.metrics.n_train < 100;

                  return (
                    <div key={model.name} className="bg-[--surface-glass] rounded-lg p-4 border border-[--border]">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <Zap className="h-4 w-4 text-[--accent]" />
                          <h4 className="font-semibold text-[--text]">{horizon}</h4>
                        </div>
                        <span className={`text-xs px-2 py-1 rounded ${isProfitable ? 'bg-[--success-soft] text-[--success]' : 'bg-[--warning-soft] text-[--warning]'}`}>
                          {isProfitable ? 'Profitable' : 'Learning'}
                        </span>
                      </div>

                      <div className="space-y-3">
                        <div>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs text-[--muted]">Direction Accuracy</span>
                            <span className={`text-sm font-bold ${isProfitable ? 'text-[--success]' : 'text-[--warning]'}`}>
                              {dirAcc.toFixed(1)}%
                            </span>
                          </div>
                          <div className="w-full bg-[--surface-glass] rounded-full h-1.5">
                            <div
                              className={`h-1.5 rounded-full ${isProfitable ? 'bg-[--success]' : 'bg-[--warning]'}`}
                              style={{ width: `${Math.min(dirAcc, 100)}%` }}
                            />
                          </div>
                        </div>

                        <div>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs text-[--muted]">Avg Error (MAE)</span>
                            <span className="text-sm font-semibold text-[--text]">{mae.toFixed(2)}%</span>
                          </div>
                        </div>

                        <div className="pt-2 border-t border-[--border]">
                          <div className="flex items-center justify-between text-xs">
                            <span className="text-[--muted]">Training Data</span>
                            <span className={needsData ? 'text-[--warning]' : 'text-[--success]'}>
                              {model.metrics.n_train} samples
                            </span>
                          </div>
                          {needsData && (
                            <p className="text-xs text-[--warning] mt-1">Needs more data (min 100)</p>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
            </div>

            {/* Model Info */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              <div className="bg-[--surface-muted] rounded-lg p-4 border border-[--border]">
                <h4 className="text-sm font-semibold text-[--text] mb-3">What This Means</h4>
                <ul className="text-xs text-[--muted] space-y-2">
                  <li className="flex items-start gap-2">
                    <span className="text-[--success] mt-0.5">•</span>
                    <span>The system learns from real stock price movements after each event</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[--success] mt-0.5">•</span>
                    <span>Predictions above 55% direction accuracy are considered profitable for trading</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[--success] mt-0.5">•</span>
                    <span>SPY-normalized returns isolate event-specific impact from market trends</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-[--success] mt-0.5">•</span>
                    <span>All predictions have ±20 point guardrails to prevent wild swings</span>
                  </li>
                </ul>
              </div>

              <div className="bg-[--surface-muted] rounded-lg p-4 border border-[--border]">
                <h4 className="text-sm font-semibold text-[--text] mb-3">Training Progress</h4>
                <div className="space-y-3">
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-[--muted]">Total Events Labeled</span>
                      <span className="text-sm font-semibold text-[--text]">
                        {mlModels.reduce((sum, m) => sum + m.metrics.n_train + m.metrics.n_test, 0)}
                      </span>
                    </div>
                  </div>
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-[--muted]">Active Models</span>
                      <span className="text-sm font-semibold text-[--success]">
                        {mlModels.filter(m => m.status === 'active').length}/3
                      </span>
                    </div>
                  </div>
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-[--muted]">Model Version</span>
                      <span className="text-sm font-semibold text-[--text]">
                        {mlModels[0]?.version || 'N/A'}
                      </span>
                    </div>
                  </div>
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-[--muted]">Last Updated</span>
                      <span className="text-sm font-semibold text-[--text]">
                        {mlModels[0]?.trained_at ? new Date(mlModels[0].trained_at).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }) : 'N/A'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Comparison Info */}
            <div className="bg-[--accent-light] border border-[--border] rounded-lg p-4">
              <div className="flex gap-2">
                <Info className="h-5 w-5 text-[--accent] flex-shrink-0 mt-0.5" />
                <div className="text-sm">
                  <p className="font-medium text-[--accent] mb-1">How ML Compares to Base Predictions</p>
                  <p className="text-[--muted]">
                    When you view event details, you'll see both the base impact score and the ML-adjusted score. 
                    The backtesting data above tracks both separately, allowing you to see whether machine learning 
                    is improving accuracy over time. ML predictions use historical patterns, market context, and 
                    event-specific features to refine the base deterministic scores.
                  </p>
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="text-center py-8">
            <p className="text-[--muted]">No ML models available yet</p>
          </div>
        )}
      </div>

      {/* Info Footer */}
      <div className="bg-[--primary-light] border border-[--border] rounded-lg p-4">
        <div className="flex gap-2">
          <Info className="h-5 w-5 text-[--primary] flex-shrink-0 mt-0.5" />
          <div className="text-sm text-[--text]">
            <p className="font-medium mb-1">About Backtesting</p>
            <p className="text-[--muted]">
              This analysis compares predicted impact scores and directions to actual stock price movements 
              at 1-day, 5-day, and 20-day horizons. Only events at least 21 days old are included to ensure 
              complete data. Some events may not have price data available.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
