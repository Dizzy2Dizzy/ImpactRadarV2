'use client';

import { useState, useEffect } from 'react';
import { apiRequest } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { AccuracyCharts } from '@/components/dashboard/AccuracyCharts';
import { MetricsTable } from '@/components/dashboard/MetricsTable';
import { ModelVersionFilter } from '@/components/dashboard/ModelVersionFilter';
import { EventTypePerformance } from '@/components/dashboard/EventTypePerformance';
import { PredictionScorecard } from '@/components/dashboard/PredictionScorecard';
import { AlertBanner } from '@/components/dashboard/AlertBanner';
import { HorizonComparison } from '@/components/dashboard/HorizonComparison';
import { DisplayVersion } from '@/components/dashboard/ImpactScoreBadge';
import {
  Activity,
  TrendingUp,
  Target,
  CheckCircle,
  RefreshCw,
  Calendar,
  Clock,
  BarChart3,
  ListChecks,
} from 'lucide-react';

interface SummaryData {
  overall_win_rate: number;
  total_events_scored: number;
  avg_mae: number;
  avg_rmse: number;
  model_versions: Array<{
    model_version: string;
    win_rate: number;
    total_predictions: number;
  }>;
  trend_direction: 'up' | 'down' | 'stable';
  trend_percentage: number;
}

interface SnapshotData {
  snapshot_date: string;
  overall_win_rate: number;
  mae: number;
  rmse: number;
  total_predictions: number;
}

interface ConfidenceData {
  confidence_level: string;
  win_rate: number;
  count: number;
}

interface MetricRow {
  event_type: string;
  horizon: string;
  model_version: string;
  win_rate: number;
  mae: number;
  rmse: number;
  sharpe_ratio: number | null;
  total_predictions: number;
}

interface EventTypeData {
  event_types: Array<{
    event_type: string;
    display_name: string;
    win_rate: number;
    mae: number;
    total_predictions: number;
    trend_vs_previous: number;
    horizons: Record<string, number>;
  }>;
  best_performing: string;
  worst_performing: string;
}

interface RecentPrediction {
  event_id: number;
  ticker: string;
  event_type: string;
  title: string;
  event_date: string;
  predicted_direction: string;
  predicted_impact: number;
  confidence: number;
  actual_return: number | null;
  direction_correct: boolean | null;
  horizon: string;
  outcome_status: 'pending' | 'correct' | 'incorrect';
}

interface ScorecardData {
  predictions: RecentPrediction[];
  total_shown: number;
  wins: number;
  losses: number;
  pending: number;
  streak: number;
}

interface AlertData {
  alert_id: string;
  alert_type: string;
  severity: 'warning' | 'critical' | 'info';
  message: string;
  metric_name: string;
  current_value: number;
  previous_value: number;
  change_percentage: number;
  detected_at: string;
  dismissed: boolean;
}

interface AlertsData {
  alerts: AlertData[];
  has_critical: boolean;
  total_alerts: number;
}

interface HorizonData {
  horizons: Array<{
    horizon: string;
    display_name: string;
    win_rate: number;
    mae: number;
    total_predictions: number;
    confidence_avg: number;
  }>;
  best_horizon: string;
  recommendation: string;
}

export default function AccuracyPage() {
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [snapshots, setSnapshots] = useState<SnapshotData[]>([]);
  const [confidenceData, setConfidenceData] = useState<ConfidenceData[]>([]);
  const [metrics, setMetrics] = useState<MetricRow[]>([]);
  const [eventTypeData, setEventTypeData] = useState<EventTypeData | null>(null);
  const [scorecardData, setScorecardData] = useState<ScorecardData | null>(null);
  const [alertsData, setAlertsData] = useState<AlertsData | null>(null);
  const [horizonData, setHorizonData] = useState<HorizonData | null>(null);
  const [dismissedAlerts, setDismissedAlerts] = useState<Set<string>>(new Set());

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d'>('30d');
  const [modelVersion, setModelVersion] = useState<DisplayVersion>('v2.0');
  const [selectedHorizon, setSelectedHorizon] = useState<string>('1d');
  const [activeTab, setActiveTab] = useState<'overview' | 'scorecard' | 'event-types' | 'horizons'>('overview');

  const getApiModelVersion = (): string | undefined => {
    switch (modelVersion) {
      case 'v1.0':
        return 'deterministic';
      case 'v1.5':
        return 'hybrid';
      case 'v2.0':
        return undefined;
      default:
        return undefined;
    }
  };

  useEffect(() => {
    loadAllData();
  }, [timeRange, selectedHorizon, modelVersion]);

  const loadAllData = async () => {
    try {
      setLoading(true);
      setError(null);

      const days = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90;
      const apiVersion = getApiModelVersion();
      const versionParam = apiVersion ? `&model_version=${apiVersion}` : '';

      const [
        summaryData,
        snapshotsData,
        confidenceDataRes,
        metricsData,
        eventTypeDataRes,
        scorecardDataRes,
        alertsDataRes,
        horizonDataRes,
      ] = await Promise.all([
        apiRequest<SummaryData>(`/api/proxy/accuracy/summary?days=${days}${versionParam}`).catch(() => null),
        apiRequest<SnapshotData[]>(`/api/proxy/accuracy/snapshots?days=${days}${versionParam}`).catch(() => []),
        apiRequest<ConfidenceData[]>(`/api/proxy/accuracy/by-confidence${apiVersion ? `?model_version=${apiVersion}` : ''}`).catch(() => []),
        apiRequest<MetricRow[]>(`/api/proxy/accuracy/metrics${apiVersion ? `?model_version=${apiVersion}` : ''}`).catch(() => []),
        apiRequest<EventTypeData>(`/api/proxy/accuracy/by-event-type?horizon=${selectedHorizon}${versionParam}`).catch(() => null),
        apiRequest<ScorecardData>(`/api/proxy/accuracy/recent-predictions?horizon=${selectedHorizon}&limit=50`).catch(() => null),
        apiRequest<AlertsData>('/api/proxy/accuracy/alerts').catch(() => null),
        apiRequest<HorizonData>(`/api/proxy/accuracy/horizon-comparison${apiVersion ? `?model_version=${apiVersion}` : ''}`).catch(() => null),
      ]);

      setSummary(summaryData);
      setSnapshots(snapshotsData);
      setConfidenceData(confidenceDataRes);
      setMetrics(metricsData);
      setEventTypeData(eventTypeDataRes);
      setScorecardData(scorecardDataRes);
      setAlertsData(alertsDataRes);
      setHorizonData(horizonDataRes);
    } catch (err: any) {
      console.error('Failed to load accuracy data:', err);
      setError(err?.message || 'Failed to load accuracy data');
    } finally {
      setLoading(false);
    }
  };

  const handleDismissAlert = (alertId: string) => {
    setDismissedAlerts(prev => new Set([...prev, alertId]));
  };

  const getTrendIcon = () => {
    if (!summary) return null;
    
    if (summary.trend_direction === 'up') {
      return <TrendingUp className="h-5 w-5 text-emerald-400" />;
    } else if (summary.trend_direction === 'down') {
      return <TrendingUp className="h-5 w-5 text-red-400 rotate-180" />;
    }
    return <Activity className="h-5 w-5 text-gray-400" />;
  };

  const getTrendColor = () => {
    if (!summary) return 'text-gray-400';
    
    if (summary.trend_direction === 'up') return 'text-emerald-400';
    if (summary.trend_direction === 'down') return 'text-red-400';
    return 'text-gray-400';
  };

  const getModelVersionDescription = () => {
    switch (modelVersion) {
      case 'v1.0':
        return 'Deterministic model metrics using rule-based scoring';
      case 'v1.5':
        return 'Hybrid model combining deterministic rules with ML predictions';
      case 'v2.0':
        return 'Market Echo ML-only metrics using XGBoost models';
      default:
        return 'Model performance metrics';
    }
  };

  const isMarketEchoVersion = (version: string | undefined | null): boolean => {
    if (!version) return false;
    const v = version.toLowerCase();
    return v.includes('xgboost') || 
           v.includes('market-echo') || 
           v.includes('market echo') ||
           v.includes('v2.0') ||
           v.includes('neural') ||
           v.includes('ensemble') ||
           v.startsWith('2.0');
  };

  const isHybridVersion = (version: string | undefined | null): boolean => {
    if (!version) return false;
    const v = version.toLowerCase();
    return v.includes('hybrid') ||
           v.includes('v1.5') ||
           v.startsWith('1.5');
  };

  const isDeterministicVersion = (version: string | undefined | null): boolean => {
    if (!version) return false;
    const v = version.toLowerCase();
    return v.includes('deterministic') ||
           v.includes('rule-based') ||
           v.includes('v1.0') ||
           (v.startsWith('1.0') && !v.includes('xgboost'));
  };

  const filterMetricsByVersion = (metricsData: MetricRow[]) => {
    if (!metricsData || metricsData.length === 0) return metricsData;
    
    switch (modelVersion) {
      case 'v1.0':
        return metricsData.filter(m => isDeterministicVersion(m.model_version));
      case 'v1.5':
        return metricsData.filter(m => isHybridVersion(m.model_version));
      case 'v2.0':
        return metricsData.filter(m => isMarketEchoVersion(m.model_version));
      default:
        return metricsData;
    }
  };

  const filterModelVersions = (versions: SummaryData['model_versions']) => {
    if (!versions || versions.length === 0) return versions;
    
    switch (modelVersion) {
      case 'v1.0':
        return versions.filter(v => isDeterministicVersion(v.model_version));
      case 'v1.5':
        return versions.filter(v => isHybridVersion(v.model_version));
      case 'v2.0':
        return versions.filter(v => isMarketEchoVersion(v.model_version));
      default:
        return versions;
    }
  };

  const filteredMetrics = filterMetricsByVersion(metrics);
  const filteredModelVersionsRaw = summary ? filterModelVersions(summary.model_versions) : [];
  const filteredModelVersions = filteredModelVersionsRaw.map(v => ({
    ...v,
    mae: summary?.avg_mae || 0,
    rmse: summary?.avg_rmse || 0,
  }));

  const filteredSummary = summary && filteredModelVersionsRaw.length > 0 ? {
    overall_win_rate: filteredModelVersionsRaw.reduce((acc, v) => acc + v.win_rate, 0) / filteredModelVersionsRaw.length,
    total_events_scored: filteredModelVersionsRaw.reduce((acc, v) => acc + v.total_predictions, 0),
    avg_mae: summary.avg_mae,
    avg_rmse: summary.avg_rmse,
    trend_direction: summary.trend_direction,
    trend_percentage: summary.trend_percentage,
  } : summary;

  // Map API alert fields to AlertBanner component format
  const filteredAlerts = (alertsData?.alerts || [])
    .filter(a => !dismissedAlerts.has(a.alert_id))
    .map(a => ({
      id: a.alert_id,
      severity: a.severity as 'critical' | 'warning' | 'info',
      title: a.alert_type === 'accuracy_drop' ? 'Accuracy Drop' 
        : a.alert_type === 'accuracy_improvement' ? 'Performance Update'
        : a.alert_type === 'mae_spike' ? 'Error Spike'
        : 'Alert',
      message: a.message,
      metric: a.metric_name,
      value: a.current_value,
      threshold: a.previous_value,
      timestamp: a.detected_at || new Date().toISOString(),
    }));

  if (loading && !summary) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-400 mx-auto mb-4"></div>
          <p className="text-[--muted]">Loading accuracy dashboard...</p>
        </div>
      </div>
    );
  }

  if (error && !summary) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-6">
            <Target className="h-12 w-12 text-red-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-[--text] mb-2">Failed to Load Dashboard</h3>
            <p className="text-sm text-red-400 mb-4">{error}</p>
            <Button onClick={loadAllData}>Retry</Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[--bg] p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Performance Alerts Banner */}
        {alertsData && filteredAlerts.length > 0 && (
          <AlertBanner
            alerts={filteredAlerts}
            hasCritical={alertsData.has_critical}
            onDismiss={handleDismissAlert}
          />
        )}

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-[--text] mb-2">Accuracy Dashboard</h1>
            <p className="text-[--muted]">
              Track model performance, win rates, and prediction accuracy across all events
            </p>
          </div>
          <div className="flex items-center gap-3">
            {/* Time Range Selector */}
            <div className="flex items-center gap-2 bg-white/5 rounded-lg p-1 border border-white/10">
              <button
                onClick={() => setTimeRange('7d')}
                className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
                  timeRange === '7d'
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : 'text-[--muted] hover:text-[--text]'
                }`}
              >
                7 Days
              </button>
              <button
                onClick={() => setTimeRange('30d')}
                className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
                  timeRange === '30d'
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : 'text-[--muted] hover:text-[--text]'
                }`}
              >
                30 Days
              </button>
              <button
                onClick={() => setTimeRange('90d')}
                className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
                  timeRange === '90d'
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : 'text-[--muted] hover:text-[--text]'
                }`}
              >
                90 Days
              </button>
            </div>
            <Button onClick={loadAllData} variant="outline" disabled={loading}>
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center gap-2 bg-white/5 rounded-lg p-1 border border-white/10">
          <button
            onClick={() => setActiveTab('overview')}
            className={`flex items-center gap-2 px-4 py-2 rounded text-sm font-medium transition-colors ${
              activeTab === 'overview'
                ? 'bg-emerald-500/20 text-emerald-400'
                : 'text-[--muted] hover:text-[--text]'
            }`}
          >
            <BarChart3 className="h-4 w-4" />
            Overview
          </button>
          <button
            onClick={() => setActiveTab('scorecard')}
            className={`flex items-center gap-2 px-4 py-2 rounded text-sm font-medium transition-colors ${
              activeTab === 'scorecard'
                ? 'bg-emerald-500/20 text-emerald-400'
                : 'text-[--muted] hover:text-[--text]'
            }`}
          >
            <ListChecks className="h-4 w-4" />
            Scorecard
          </button>
          <button
            onClick={() => setActiveTab('event-types')}
            className={`flex items-center gap-2 px-4 py-2 rounded text-sm font-medium transition-colors ${
              activeTab === 'event-types'
                ? 'bg-emerald-500/20 text-emerald-400'
                : 'text-[--muted] hover:text-[--text]'
            }`}
          >
            <Calendar className="h-4 w-4" />
            Event Types
          </button>
          <button
            onClick={() => setActiveTab('horizons')}
            className={`flex items-center gap-2 px-4 py-2 rounded text-sm font-medium transition-colors ${
              activeTab === 'horizons'
                ? 'bg-emerald-500/20 text-emerald-400'
                : 'text-[--muted] hover:text-[--text]'
            }`}
          >
            <Clock className="h-4 w-4" />
            Time Horizons
          </button>
        </div>

        {/* Model Version Filter */}
        <div className="flex items-center justify-between bg-white/5 rounded-lg p-4 border border-white/10">
          <div className="flex items-center gap-4">
            <ModelVersionFilter value={modelVersion} onChange={setModelVersion} />
            <span className="text-sm text-[--muted]">{getModelVersionDescription()}</span>
          </div>
          {(activeTab === 'scorecard' || activeTab === 'event-types') && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-[--muted]">Horizon:</span>
              <select
                value={selectedHorizon}
                onChange={(e) => setSelectedHorizon(e.target.value)}
                className="px-3 py-1 bg-white/10 border border-white/20 rounded text-sm text-[--text]"
              >
                <option value="1d">1 Day</option>
                <option value="7d">7 Days</option>
                <option value="30d">30 Days</option>
              </select>
            </div>
          )}
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <>
            {/* Key Metrics */}
            {filteredSummary && (
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                {/* Overall Win Rate */}
                <div className="bg-gradient-to-br from-emerald-500/20 to-emerald-500/5 rounded-lg p-6 border border-emerald-500/30">
                  <div className="flex items-center justify-between mb-3">
                    <div className="text-sm font-medium text-emerald-400">Overall Win Rate</div>
                    {getTrendIcon()}
                  </div>
                  <div className="text-4xl font-bold text-[--text] mb-1">
                    {(filteredSummary.overall_win_rate * 100).toFixed(1)}%
                  </div>
                  <div className={`text-sm ${getTrendColor()} flex items-center gap-1`}>
                    {filteredSummary.trend_direction !== 'stable' && (
                      <>
                        {filteredSummary.trend_direction === 'up' ? '+' : '-'}
                        {Math.abs(filteredSummary.trend_percentage).toFixed(1)}%
                      </>
                    )}
                    {filteredSummary.trend_direction === 'stable' && 'Stable'}
                    <span className="text-[--muted] ml-1">vs previous period</span>
                  </div>
                </div>

                {/* Total Events Scored */}
                <div className="bg-white/5 rounded-lg p-6 border border-white/10">
                  <div className="flex items-center justify-between mb-3">
                    <div className="text-sm font-medium text-[--muted]">Total Events Scored</div>
                    <CheckCircle className="h-5 w-5 text-blue-400" />
                  </div>
                  <div className="text-4xl font-bold text-[--text] mb-1">
                    {filteredSummary.total_events_scored.toLocaleString()}
                  </div>
                  <div className="text-sm text-[--muted]">
                    Predictions evaluated
                  </div>
                </div>

                {/* Average MAE */}
                <div className="bg-white/5 rounded-lg p-6 border border-white/10">
                  <div className="flex items-center justify-between mb-3">
                    <div className="text-sm font-medium text-[--muted]">Average MAE</div>
                    <Target className="h-5 w-5 text-blue-400" />
                  </div>
                  <div className="text-4xl font-bold text-[--text] mb-1">
                    {filteredSummary.avg_mae.toFixed(2)}%
                  </div>
                  <div className="text-sm text-[--muted]">
                    Prediction Error
                  </div>
                </div>

                {/* Average RMSE */}
                <div className="bg-white/5 rounded-lg p-6 border border-white/10">
                  <div className="flex items-center justify-between mb-3">
                    <div className="text-sm font-medium text-[--muted]">Average RMSE</div>
                    <Activity className="h-5 w-5 text-amber-400" />
                  </div>
                  <div className="text-4xl font-bold text-[--text] mb-1">
                    {filteredSummary.avg_rmse.toFixed(2)}%
                  </div>
                  <div className="text-sm text-[--muted]">
                    Root Mean Squared Error
                  </div>
                </div>
              </div>
            )}

            {/* Model Performance Comparison */}
            {summary && filteredModelVersions.length > 0 && (
              <div className="bg-white/5 rounded-lg p-6 border border-white/10">
                <h2 className="text-xl font-bold text-[--text] mb-4">
                  Model Version Performance
                  <span className="text-sm font-normal text-[--muted] ml-2">
                    ({modelVersion === 'v1.0' ? 'Deterministic' : modelVersion === 'v1.5' ? 'Hybrid' : 'Market Echo'})
                  </span>
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {filteredModelVersions.map((model) => (
                    <div
                      key={model.model_version}
                      className="bg-purple-500/10 rounded-lg p-4 border border-purple-500/20"
                    >
                      <div className="text-sm text-purple-300 mb-2">{model.model_version}</div>
                      <div className="text-3xl font-bold text-purple-400 mb-1">
                        {(model.win_rate * 100).toFixed(1)}%
                      </div>
                      <div className="text-xs text-[--muted]">
                        {model.total_predictions.toLocaleString()} predictions
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Charts */}
            <div>
              <h2 className="text-2xl font-bold text-[--text] mb-4">Performance Trends</h2>
              <AccuracyCharts
                snapshots={snapshots}
                modelPerformance={filteredModelVersions}
                confidenceBreakdown={confidenceData}
                loading={loading}
              />
            </div>

            {/* Detailed Metrics Table */}
            <div>
              <h2 className="text-2xl font-bold text-[--text] mb-4">
                Detailed Metrics by Event Type & Horizon
                <span className="text-sm font-normal text-[--muted] ml-2">
                  ({modelVersion === 'v1.0' ? 'Deterministic' : modelVersion === 'v1.5' ? 'Hybrid' : 'Market Echo'} Model)
                </span>
              </h2>
              <MetricsTable metrics={filteredMetrics} loading={loading} />
            </div>
          </>
        )}

        {/* Scorecard Tab */}
        {activeTab === 'scorecard' && (
          <PredictionScorecard
            predictions={(scorecardData?.predictions || []).map(p => {
              let direction: 'up' | 'down';
              if (p.predicted_direction === 'positive') {
                direction = 'up';
              } else if (p.predicted_direction === 'negative') {
                direction = 'down';
              } else {
                direction = p.predicted_impact >= 60 ? 'up' : p.predicted_impact <= 40 ? 'down' : 'up';
              }
              return {
                id: String(p.event_id),
                ticker: p.ticker,
                event_type: p.event_type,
                predicted_direction: direction,
                predicted_magnitude: Math.abs(p.predicted_impact - 50) / 100,
                actual_direction: p.actual_return !== null ? (p.actual_return >= 0 ? 'up' : 'down') : undefined,
                actual_magnitude: p.actual_return !== null ? Math.abs(p.actual_return) / 100 : undefined,
                is_correct: p.outcome_status === 'pending' ? undefined : p.outcome_status === 'correct',
                event_date: p.event_date,
              };
            })}
            winStreak={scorecardData?.streak && scorecardData.streak > 0 ? scorecardData.streak : 0}
            lossStreak={scorecardData?.streak && scorecardData.streak < 0 ? Math.abs(scorecardData.streak) : 0}
            loading={loading}
          />
        )}

        {/* Event Types Tab */}
        {activeTab === 'event-types' && (
          <EventTypePerformance
            data={(eventTypeData?.event_types || []).map(e => ({
              event_type: e.event_type,
              win_rate: e.win_rate,
              mae: e.mae,
              total_predictions: e.total_predictions,
              trend: e.trend as 'up' | 'down' | 'stable' | undefined,
            }))}
            loading={loading}
          />
        )}

        {/* Time Horizons Tab */}
        {activeTab === 'horizons' && (
          <HorizonComparison
            data={(horizonData?.horizons || []).map(h => ({
              horizon: h.horizon,
              win_rate: h.win_rate,
              mae: h.mae,
              total_predictions: h.total_predictions,
              avg_confidence: h.confidence_avg,
            }))}
            loading={loading}
          />
        )}
      </div>
    </div>
  );
}
