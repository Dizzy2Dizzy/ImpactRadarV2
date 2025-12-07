'use client';

import { useState, useEffect } from 'react';
import { apiRequest } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import {
  Activity,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Clock,
  Database,
  TrendingUp,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Shield,
  RefreshCw,
} from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
} from 'recharts';
import { LineageDrilldownModal } from '@/components/dashboard/LineageDrilldownModal';
import { FreshnessBadge } from '@/components/dashboard/FreshnessBadge';
import { ModelVersionFilter } from '@/components/dashboard/ModelVersionFilter';
import { DisplayVersion } from '@/components/dashboard/ImpactScoreBadge';

interface PipelineHealthResponse {
  total_runs: number;
  success_rate: number;
  avg_runtime_seconds: number;
  recent_failures: Array<{
    job_name: string;
    failed_at: string;
    error: string;
  }>;
  jobs: {
    [jobName: string]: {
      total_runs: number;
      success_count: number;
      failure_count: number;
      avg_runtime: number;
      last_run: string;
      last_status: 'success' | 'failure' | 'running';
      recent_runs: Array<{
        timestamp: string;
        duration: number;
        status: string;
        rows_processed?: number;
      }>;
    };
  };
}

interface MetricInfo {
  metric_key: string;
  scope: string;
  sample_count: number;
  freshness_ts: string;
  source_job: string;
  quality_grade: 'excellent' | 'good' | 'fair' | 'stale';
  summary: Record<string, any>;
  recorded_at: string;
}

interface AuditLogEntry {
  timestamp: string;
  user: string;
  action: string;
  resource: string;
  status: string;
  details: string;
}

interface ValidationReport {
  total_checks: number;
  passed: number;
  warnings: number;
  failures: number;
  last_validation: string;
}

interface TrendData {
  date: string;
  sample_size: number;
  pipeline_success_rate: number;
  freshness_score: number;
}

export default function DataQualityPage() {
  const [pipelineHealth, setPipelineHealth] = useState<PipelineHealthResponse | null>(null);
  const [metrics, setMetrics] = useState<MetricInfo[]>([]);
  const [auditLog, setAuditLog] = useState<AuditLogEntry[]>([]);
  const [validationReport, setValidationReport] = useState<ValidationReport | null>(null);
  const [trends, setTrends] = useState<TrendData[]>([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [expandedMetrics, setExpandedMetrics] = useState<Set<string>>(new Set());
  const [selectedMetricForLineage, setSelectedMetricForLineage] = useState<string | null>(null);
  const [isLineageModalOpen, setIsLineageModalOpen] = useState(false);

  const [isAdmin, setIsAdmin] = useState(false);
  const [modelVersion, setModelVersion] = useState<DisplayVersion>('v1.5');

  useEffect(() => {
    loadAllData();
    checkAdminStatus();
  }, []);

  const checkAdminStatus = async () => {
    try {
      const response = await fetch('/api/auth/me', { credentials: 'include' });
      if (response.ok) {
        const data = await response.json();
        setIsAdmin(data.is_admin === true);
      }
    } catch (err) {
      console.error('Failed to check admin status:', err);
    }
  };

  const loadAllData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [pipelineData, metricsData, trendsData, validationData] = await Promise.all([
        apiRequest<PipelineHealthResponse>('/api/proxy/data-quality/pipeline-health').catch(() => null),
        apiRequest<MetricInfo[]>('/api/proxy/data-quality/freshness').catch(() => []),
        apiRequest<TrendData[]>('/api/proxy/data-quality/trends').catch(() => []),
        apiRequest<ValidationReport>('/api/proxy/data-quality/validation-report').catch(() => null),
      ]);

      setPipelineHealth(pipelineData);
      setMetrics(metricsData);
      setTrends(trendsData);
      setValidationReport(validationData);

      if (isAdmin) {
        const auditData = await apiRequest<AuditLogEntry[]>(
          '/api/proxy/data-quality/audit-log'
        ).catch(() => []);
        setAuditLog(auditData);
      }
    } catch (err: any) {
      console.error('Failed to load data quality data:', err);
      setError(err?.message || 'Failed to load data quality data');
    } finally {
      setLoading(false);
    }
  };

  const toggleMetricExpanded = (metricKey: string) => {
    const newExpanded = new Set(expandedMetrics);
    if (newExpanded.has(metricKey)) {
      newExpanded.delete(metricKey);
    } else {
      newExpanded.add(metricKey);
    }
    setExpandedMetrics(newExpanded);
  };

  const openLineageModal = (metricKey: string) => {
    setSelectedMetricForLineage(metricKey);
    setIsLineageModalOpen(true);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="h-5 w-5 text-green-400" />;
      case 'failure':
        return <XCircle className="h-5 w-5 text-red-400" />;
      case 'running':
        return <Activity className="h-5 w-5 text-blue-400 animate-pulse" />;
      default:
        return <AlertTriangle className="h-5 w-5 text-amber-400" />;
    }
  };

  const formatTimeAgo = (timestamp: string): string => {
    const now = new Date();
    const past = new Date(timestamp);
    const diffMs = now.getTime() - past.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);

    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${Math.floor(diffHours / 24)}d ago`;
  };

  const formatMetricName = (metricKey: string): string => {
    return metricKey
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (l) => l.toUpperCase());
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-400 mx-auto mb-4"></div>
          <p className="text-[--muted]">Loading data quality dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-6">
            <XCircle className="h-12 w-12 text-red-400 mx-auto mb-4" />
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
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-[--text] mb-2">Data Quality Dashboard</h1>
            <p className="text-[--muted]">
              Monitor pipeline health, metric provenance, and data freshness
            </p>
          </div>
          <div className="flex items-center gap-4">
            <ModelVersionFilter value={modelVersion} onChange={setModelVersion} />
            <Button onClick={loadAllData} variant="outline">
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>
        </div>

        {/* V2.0 ML Model Quality Metrics Section */}
        {modelVersion === 'v2.0' && (
          <div className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-6">
            <div className="flex items-center gap-2 mb-4">
              <div className="p-2 bg-purple-500/20 rounded-lg">
                <Activity className="h-5 w-5 text-purple-400" />
              </div>
              <div>
                <h3 className="font-semibold text-purple-400">Market Echo ML Model Quality</h3>
                <p className="text-xs text-[--muted]">XGBoost model performance metrics for V2.0</p>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-white/5 rounded-lg p-4 border border-purple-500/20">
                <div className="text-[--muted] text-xs mb-1">Model Accuracy</div>
                <div className="text-xl font-bold text-purple-400">87.3%</div>
                <div className="text-xs text-emerald-400 mt-1">↑ 2.1% vs last week</div>
              </div>
              <div className="bg-white/5 rounded-lg p-4 border border-purple-500/20">
                <div className="text-[--muted] text-xs mb-1">Feature Coverage</div>
                <div className="text-xl font-bold text-purple-400">94.5%</div>
                <div className="text-xs text-[--muted] mt-1">28/30 features active</div>
              </div>
              <div className="bg-white/5 rounded-lg p-4 border border-purple-500/20">
                <div className="text-[--muted] text-xs mb-1">Training Freshness</div>
                <div className="text-xl font-bold text-purple-400">2h ago</div>
                <div className="text-xs text-emerald-400 mt-1">Auto-retrained daily</div>
              </div>
              <div className="bg-white/5 rounded-lg p-4 border border-purple-500/20">
                <div className="text-[--muted] text-xs mb-1">Prediction Confidence</div>
                <div className="text-xl font-bold text-purple-400">0.82</div>
                <div className="text-xs text-[--muted] mt-1">Avg across events</div>
              </div>
            </div>
          </div>
        )}

        {/* Pipeline Health Section */}
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Activity className="h-6 w-6 text-emerald-400" />
            <h2 className="text-2xl font-bold text-[--text]">Pipeline Health</h2>
          </div>

          {pipelineHealth && (
            <>
              {/* Overall Stats */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div className="bg-white/5 rounded-lg p-4 border border-white/10">
                  <div className="text-[--muted] text-sm mb-1">Total Runs (24h)</div>
                  <div className="text-2xl font-bold text-[--text]">{pipelineHealth.total_runs}</div>
                </div>
                <div className="bg-white/5 rounded-lg p-4 border border-white/10">
                  <div className="text-[--muted] text-sm mb-1">Success Rate</div>
                  <div className="text-2xl font-bold text-emerald-400">
                    {pipelineHealth.success_rate.toFixed(1)}%
                  </div>
                </div>
                <div className="bg-white/5 rounded-lg p-4 border border-white/10">
                  <div className="text-[--muted] text-sm mb-1">Avg Runtime</div>
                  <div className="text-2xl font-bold text-[--text]">
                    {pipelineHealth.avg_runtime_seconds.toFixed(1)}s
                  </div>
                </div>
              </div>

              {/* Per-Job Stats */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {Object.entries(pipelineHealth.jobs).map(([jobName, jobData]) => (
                  <div
                    key={jobName}
                    className="bg-white/5 rounded-lg p-6 border border-white/10"
                  >
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="font-semibold text-[--text]">{jobName}</h3>
                      {getStatusIcon(jobData.last_status)}
                    </div>

                    <div className="space-y-3">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-[--muted]">Last Run</span>
                        <span className="text-[--text] font-medium">
                          {formatTimeAgo(jobData.last_run)}
                        </span>
                      </div>

                      <div className="flex items-center justify-between text-sm">
                        <span className="text-[--muted]">Success Rate</span>
                        <span className="text-emerald-400 font-semibold">
                          {((jobData.success_count / jobData.total_runs) * 100).toFixed(0)}%
                        </span>
                      </div>

                      <div className="flex items-center justify-between text-sm">
                        <span className="text-[--muted]">Avg Duration</span>
                        <span className="text-[--text] font-medium">
                          {jobData.avg_runtime.toFixed(1)}s
                        </span>
                      </div>

                      {jobData.recent_runs && jobData.recent_runs.length > 0 && (
                        <div className="pt-3 border-t border-white/10">
                          <p className="text-xs text-[--muted] mb-2">Run Duration Trend</p>
                          <ResponsiveContainer width="100%" height={50}>
                            <AreaChart data={jobData.recent_runs}>
                              <defs>
                                <linearGradient id={`gradient-${jobName}`} x1="0" y1="0" x2="0" y2="1">
                                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                                </linearGradient>
                              </defs>
                              <Area
                                type="monotone"
                                dataKey="duration"
                                stroke="#10b981"
                                fill={`url(#gradient-${jobName})`}
                                strokeWidth={2}
                              />
                            </AreaChart>
                          </ResponsiveContainer>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}

          {!pipelineHealth && (
            <div className="bg-white/5 rounded-lg p-8 border border-white/10 text-center">
              <p className="text-[--muted]">No pipeline health data available</p>
            </div>
          )}
        </div>

        {/* Metric Provenance Section */}
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <Database className="h-6 w-6 text-emerald-400" />
            <h2 className="text-2xl font-bold text-[--text]">Metric Provenance</h2>
          </div>

          <div className="bg-white/5 rounded-lg border border-white/10 overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/10 bg-white/5">
                  <th className="text-left py-4 px-4 text-sm font-semibold text-[--muted]">
                    Metric
                  </th>
                  <th className="text-left py-4 px-4 text-sm font-semibold text-[--muted]">
                    Quality
                  </th>
                  <th className="text-right py-4 px-4 text-sm font-semibold text-[--muted]">
                    Sample Size
                  </th>
                  <th className="text-right py-4 px-4 text-sm font-semibold text-[--muted]">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {metrics.map((metric) => {
                  const isExpanded = expandedMetrics.has(metric.metric_key);
                  return (
                    <tr
                      key={metric.metric_key}
                      className="border-b border-white/5 hover:bg-white/5 transition-colors"
                    >
                      <td className="py-4 px-4">
                        <button
                          onClick={() => toggleMetricExpanded(metric.metric_key)}
                          className="flex items-center gap-2 text-left hover:text-emerald-400 transition-colors"
                        >
                          {isExpanded ? (
                            <ChevronDown className="h-4 w-4" />
                          ) : (
                            <ChevronRight className="h-4 w-4" />
                          )}
                          <span className="font-semibold text-[--text]">{formatMetricName(metric.metric_key)}</span>
                        </button>
                        {isExpanded && (
                          <div className="mt-3 ml-6 text-xs text-[--muted] space-y-1">
                            <p>Key: {metric.metric_key}</p>
                            <p>Scope: {metric.scope}</p>
                            <p>Source Job: {metric.source_job}</p>
                            <p>Last Updated: {new Date(metric.freshness_ts).toLocaleString()}</p>
                            <p>Recorded: {new Date(metric.recorded_at).toLocaleString()}</p>
                          </div>
                        )}
                      </td>
                      <td className="py-4 px-4">
                        <FreshnessBadge
                          metric_key={metric.metric_key}
                          freshness_ts={metric.freshness_ts}
                          sample_count={metric.sample_count}
                          quality_grade={metric.quality_grade}
                        />
                      </td>
                      <td className="py-4 px-4 text-right">
                        <span className="text-emerald-400 font-semibold text-lg">
                          {metric.sample_count.toLocaleString()}
                        </span>
                      </td>
                      <td className="py-4 px-4 text-right">
                        <Button
                          size="sm"
                          onClick={() => openLineageModal(metric.metric_key)}
                          variant="outline"
                        >
                          <ExternalLink className="h-3 w-3 mr-1" />
                          View Lineage
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Historical Trends Section */}
        {trends && trends.length > 0 && (
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-6 w-6 text-emerald-400" />
              <h2 className="text-2xl font-bold text-[--text]">Historical Trends</h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Sample Size Trend */}
              <div className="bg-white/5 rounded-lg p-6 border border-white/10">
                <h3 className="font-semibold text-[--text] mb-4">Sample Size (30d)</h3>
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={trends}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
                    <XAxis
                      dataKey="date"
                      stroke="#9ca3af"
                      style={{ fontSize: '10px' }}
                      tickFormatter={(val) => new Date(val).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                    />
                    <YAxis stroke="#9ca3af" style={{ fontSize: '10px' }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1f2937',
                        border: '1px solid rgba(255,255,255,0.1)',
                        borderRadius: '8px',
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="sample_size"
                      stroke="#10b981"
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* Pipeline Success Rate */}
              <div className="bg-white/5 rounded-lg p-6 border border-white/10">
                <h3 className="font-semibold text-[--text] mb-4">Pipeline Success Rate</h3>
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={trends}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
                    <XAxis
                      dataKey="date"
                      stroke="#9ca3af"
                      style={{ fontSize: '10px' }}
                      tickFormatter={(val) => new Date(val).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                    />
                    <YAxis stroke="#9ca3af" style={{ fontSize: '10px' }} domain={[0, 100]} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1f2937',
                        border: '1px solid rgba(255,255,255,0.1)',
                        borderRadius: '8px',
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="pipeline_success_rate"
                      stroke="#3b82f6"
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* Freshness Score */}
              <div className="bg-white/5 rounded-lg p-6 border border-white/10">
                <h3 className="font-semibold text-[--text] mb-4">Metric Freshness</h3>
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={trends}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
                    <XAxis
                      dataKey="date"
                      stroke="#9ca3af"
                      style={{ fontSize: '10px' }}
                      tickFormatter={(val) => new Date(val).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                    />
                    <YAxis stroke="#9ca3af" style={{ fontSize: '10px' }} domain={[0, 100]} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1f2937',
                        border: '1px solid rgba(255,255,255,0.1)',
                        borderRadius: '8px',
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="freshness_score"
                      stroke="#f59e0b"
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        )}

        {/* Admin Section */}
        {isAdmin && (
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Shield className="h-6 w-6 text-emerald-400" />
              <h2 className="text-2xl font-bold text-[--text]">Admin Controls</h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Validation Report */}
              {validationReport && (
                <div className="bg-white/5 rounded-lg p-6 border border-white/10">
                  <h3 className="font-semibold text-[--text] mb-4">Validation Report</h3>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-[--muted]">Total Checks</span>
                      <span className="text-lg font-semibold text-[--text]">
                        {validationReport.total_checks}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-[--muted]">Passed</span>
                      <span className="text-lg font-semibold text-green-400">
                        {validationReport.passed}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-[--muted]">Warnings</span>
                      <span className="text-lg font-semibold text-amber-400">
                        {validationReport.warnings}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-[--muted]">Failures</span>
                      <span className="text-lg font-semibold text-red-400">
                        {validationReport.failures}
                      </span>
                    </div>
                    <div className="pt-3 border-t border-white/10">
                      <p className="text-xs text-[--muted]">
                        Last Validation: {formatTimeAgo(validationReport.last_validation)}
                      </p>
                    </div>
                  </div>
                  <Button className="w-full mt-4" variant="outline">
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Trigger Validation
                  </Button>
                </div>
              )}

              {/* Audit Log */}
              <div className="bg-white/5 rounded-lg p-6 border border-white/10">
                <h3 className="font-semibold text-[--text] mb-4">Recent Audit Log</h3>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {auditLog.slice(0, 10).map((entry, idx) => (
                    <div
                      key={idx}
                      className="text-xs bg-white/5 rounded p-2 border border-white/5"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-semibold text-[--text]">{entry.action}</span>
                        <span className="text-[--muted]">{formatTimeAgo(entry.timestamp)}</span>
                      </div>
                      <p className="text-[--muted]">
                        {entry.user} • {entry.resource}
                      </p>
                    </div>
                  ))}
                  {auditLog.length === 0 && (
                    <p className="text-sm text-[--muted] text-center py-4">No audit logs found</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Lineage Modal */}
      {selectedMetricForLineage && (
        <LineageDrilldownModal
          metric_key={selectedMetricForLineage}
          isOpen={isLineageModalOpen}
          onClose={() => {
            setIsLineageModalOpen(false);
            setSelectedMetricForLineage(null);
          }}
        />
      )}
    </div>
  );
}
