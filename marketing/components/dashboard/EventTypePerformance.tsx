'use client';

import { TrendingUp, TrendingDown, Target, BarChart3, Activity } from 'lucide-react';

interface EventTypeMetric {
  event_type: string;
  win_rate: number;
  mae: number;
  total_predictions: number;
  trend?: 'up' | 'down' | 'stable';
}

interface EventTypePerformanceProps {
  data: EventTypeMetric[];
  loading?: boolean;
}

function getEventTypeIcon(eventType: string) {
  const type = eventType.toLowerCase();
  if (type.includes('earning')) return '📊';
  if (type.includes('sec') || type.includes('filing')) return '📄';
  if (type.includes('fda')) return '💊';
  if (type.includes('merger') || type.includes('acquisition')) return '🤝';
  if (type.includes('dividend')) return '💰';
  if (type.includes('insider')) return '👤';
  if (type.includes('guidance')) return '🎯';
  if (type.includes('analyst')) return '📈';
  return '📋';
}

function formatEventType(eventType: string): string {
  return eventType
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function EventTypePerformance({ data, loading = false }: EventTypePerformanceProps) {
  if (loading) {
    return (
      <div className="bg-white/5 rounded-lg p-6 border border-white/10">
        <div className="flex items-center gap-2 mb-6">
          <div className="h-5 w-5 bg-white/10 rounded animate-pulse"></div>
          <div className="h-6 w-48 bg-white/10 rounded animate-pulse"></div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="bg-white/5 rounded-lg p-4 border border-white/10 animate-pulse">
              <div className="flex items-center gap-3 mb-4">
                <div className="h-10 w-10 bg-white/10 rounded-lg"></div>
                <div className="h-5 w-32 bg-white/10 rounded"></div>
              </div>
              <div className="space-y-3">
                <div className="h-4 w-24 bg-white/10 rounded"></div>
                <div className="h-4 w-20 bg-white/10 rounded"></div>
                <div className="h-4 w-28 bg-white/10 rounded"></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="bg-white/5 rounded-lg p-6 border border-white/10">
        <div className="flex items-center gap-2 mb-6">
          <BarChart3 className="h-5 w-5 text-emerald-400" />
          <h3 className="text-lg font-semibold text-[--text]">Performance by Event Type</h3>
        </div>
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <Activity className="w-12 h-12 text-[--muted] mb-4" />
          <h4 className="text-lg font-semibold text-[--text] mb-2">No Event Type Data</h4>
          <p className="text-[--muted] max-w-md">
            Performance metrics by event type will appear here once predictions are made and outcomes are tracked.
          </p>
        </div>
      </div>
    );
  }

  const sortedData = [...data].sort((a, b) => b.win_rate - a.win_rate);

  return (
    <div className="bg-white/5 rounded-lg p-6 border border-white/10">
      <div className="flex items-center gap-2 mb-6">
        <BarChart3 className="h-5 w-5 text-emerald-400" />
        <h3 className="text-lg font-semibold text-[--text]">Performance by Event Type</h3>
        <span className="ml-auto text-sm text-[--muted]">{data.length} event types</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {sortedData.map((metric) => {
          const winRatePercent = metric.win_rate > 1 ? metric.win_rate : metric.win_rate * 100;
          const isPositive = winRatePercent >= 50;

          return (
            <div
              key={metric.event_type}
              className="bg-white/5 rounded-lg p-4 border border-white/10 hover:border-white/20 transition-colors"
            >
              <div className="flex items-center gap-3 mb-4">
                <div className="flex items-center justify-center h-10 w-10 bg-white/10 rounded-lg text-lg">
                  {getEventTypeIcon(metric.event_type)}
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="font-medium text-[--text] truncate">
                    {formatEventType(metric.event_type)}
                  </h4>
                  {metric.trend && (
                    <div className="flex items-center gap-1 mt-0.5">
                      {metric.trend === 'up' && (
                        <TrendingUp className="h-3 w-3 text-emerald-400" />
                      )}
                      {metric.trend === 'down' && (
                        <TrendingDown className="h-3 w-3 text-red-400" />
                      )}
                      <span className="text-xs text-[--muted]">
                        {metric.trend === 'up' ? 'Improving' : metric.trend === 'down' ? 'Declining' : 'Stable'}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-[--muted]">Win Rate</span>
                  <span className={`font-semibold ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
                    {winRatePercent.toFixed(1)}%
                  </span>
                </div>

                <div className="w-full bg-white/10 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full transition-all ${isPositive ? 'bg-emerald-400' : 'bg-red-400'}`}
                    style={{ width: `${Math.min(winRatePercent, 100)}%` }}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-sm text-[--muted]">MAE</span>
                  <span className="text-sm text-blue-400">{metric.mae.toFixed(4)}</span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-sm text-[--muted]">Predictions</span>
                  <span className="text-sm text-[--text]">{metric.total_predictions.toLocaleString()}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-6 pt-4 border-t border-white/10">
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full bg-emerald-400"></div>
              <span className="text-[--muted]">Win Rate ≥ 50%</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full bg-red-400"></div>
              <span className="text-[--muted]">Win Rate &lt; 50%</span>
            </div>
          </div>
          <div className="text-[--muted]">
            Total predictions: {data.reduce((sum, m) => sum + m.total_predictions, 0).toLocaleString()}
          </div>
        </div>
      </div>
    </div>
  );
}
