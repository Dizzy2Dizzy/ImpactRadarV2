'use client';

import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { TrendingUp, TrendingDown, Target } from 'lucide-react';

interface SnapshotData {
  snapshot_date: string;
  overall_win_rate: number;
  mae: number;
  rmse: number;
  total_predictions: number;
}

interface ModelPerformance {
  model_version: string;
  win_rate: number;
  total_predictions: number;
  mae: number;
  rmse: number;
}

interface ConfidenceBreakdown {
  confidence_level: string;
  win_rate: number;
  count: number;
}

interface AccuracyChartsProps {
  snapshots: SnapshotData[];
  modelPerformance: ModelPerformance[];
  confidenceBreakdown: ConfidenceBreakdown[];
  loading?: boolean;
}

export function AccuracyCharts({
  snapshots,
  modelPerformance,
  confidenceBreakdown,
  loading = false,
}: AccuracyChartsProps) {
  if (loading) {
    return (
      <div className="space-y-6">
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-white/5 rounded-lg p-6 border border-white/10 animate-pulse">
            <div className="h-64 bg-white/10 rounded"></div>
          </div>
        ))}
      </div>
    );
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const formatPercentage = (value: number) => `${(value * 100).toFixed(1)}%`;

  return (
    <div className="space-y-6">
      {/* Win Rate Trend Chart */}
      <div className="bg-white/5 rounded-lg p-6 border border-white/10">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp className="h-5 w-5 text-emerald-400" />
          <h3 className="text-lg font-semibold text-[--text]">Win Rate Trend Over Time</h3>
        </div>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={snapshots}>
            <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
            <XAxis
              dataKey="snapshot_date"
              stroke="#9ca3af"
              style={{ fontSize: '12px' }}
              tickFormatter={formatDate}
            />
            <YAxis
              stroke="#9ca3af"
              style={{ fontSize: '12px' }}
              tickFormatter={(value) => `${(value * 100).toFixed(0)}%`}
              domain={[0, 1]}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1f2937',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '8px',
              }}
              labelFormatter={(label) => `Date: ${formatDate(label)}`}
              formatter={(value: any) => [formatPercentage(value), 'Win Rate']}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="overall_win_rate"
              stroke="#10b981"
              strokeWidth={3}
              dot={{ fill: '#10b981', r: 4 }}
              name="Win Rate"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* MAE and RMSE Trends */}
      <div className="bg-white/5 rounded-lg p-6 border border-white/10">
        <div className="flex items-center gap-2 mb-4">
          <Target className="h-5 w-5 text-blue-400" />
          <h3 className="text-lg font-semibold text-[--text]">Error Metrics Trend (MAE & RMSE)</h3>
        </div>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={snapshots}>
            <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
            <XAxis
              dataKey="snapshot_date"
              stroke="#9ca3af"
              style={{ fontSize: '12px' }}
              tickFormatter={formatDate}
            />
            <YAxis
              stroke="#9ca3af"
              style={{ fontSize: '12px' }}
              tickFormatter={(value) => value.toFixed(3)}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1f2937',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '8px',
              }}
              labelFormatter={(label) => `Date: ${formatDate(label)}`}
              formatter={(value: any) => [value.toFixed(4), '']}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="mae"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={{ fill: '#3b82f6', r: 3 }}
              name="MAE (Mean Absolute Error)"
            />
            <Line
              type="monotone"
              dataKey="rmse"
              stroke="#f59e0b"
              strokeWidth={2}
              dot={{ fill: '#f59e0b', r: 3 }}
              name="RMSE (Root Mean Squared Error)"
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Model Performance Comparison */}
      <div className="bg-white/5 rounded-lg p-6 border border-white/10">
        <div className="flex items-center gap-2 mb-4">
          <TrendingDown className="h-5 w-5 text-purple-400" />
          <h3 className="text-lg font-semibold text-[--text]">Model Version Performance Comparison</h3>
        </div>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={modelPerformance}>
            <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
            <XAxis
              dataKey="model_version"
              stroke="#9ca3af"
              style={{ fontSize: '12px' }}
            />
            <YAxis
              stroke="#9ca3af"
              style={{ fontSize: '12px' }}
              tickFormatter={(value) => `${(value * 100).toFixed(0)}%`}
              domain={[0, 1]}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1f2937',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '8px',
              }}
              formatter={(value: any) => [formatPercentage(value), 'Win Rate']}
            />
            <Legend />
            <Bar
              dataKey="win_rate"
              fill="#8b5cf6"
              name="Win Rate"
              radius={[8, 8, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Confidence Level Breakdown */}
      <div className="bg-white/5 rounded-lg p-6 border border-white/10">
        <div className="flex items-center gap-2 mb-4">
          <Target className="h-5 w-5 text-emerald-400" />
          <h3 className="text-lg font-semibold text-[--text]">Win Rate by Confidence Level</h3>
        </div>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={confidenceBreakdown}>
            <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
            <XAxis
              dataKey="confidence_level"
              stroke="#9ca3af"
              style={{ fontSize: '12px' }}
            />
            <YAxis
              stroke="#9ca3af"
              style={{ fontSize: '12px' }}
              tickFormatter={(value) => `${(value * 100).toFixed(0)}%`}
              domain={[0, 1]}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1f2937',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '8px',
              }}
              formatter={(value: any, name: string) => {
                if (name === 'win_rate') return [formatPercentage(value), 'Win Rate'];
                return [value, 'Count'];
              }}
            />
            <Legend />
            <Bar
              dataKey="win_rate"
              fill="#10b981"
              name="Win Rate"
              radius={[8, 8, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
        <div className="mt-4 grid grid-cols-3 gap-4 text-sm">
          {confidenceBreakdown.map((item) => (
            <div key={item.confidence_level} className="bg-white/5 rounded-lg p-3">
              <div className="text-[--muted] capitalize mb-1">{item.confidence_level}</div>
              <div className="text-2xl font-bold text-emerald-400">
                {formatPercentage(item.win_rate)}
              </div>
              <div className="text-xs text-[--muted]">{item.count.toLocaleString()} predictions</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
