'use client';

import { useState, useMemo } from 'react';
import { ChevronUp, ChevronDown, Filter } from 'lucide-react';
import { Button } from '@/components/ui/button';

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

interface MetricsTableProps {
  metrics: MetricRow[];
  loading?: boolean;
}

type SortColumn = 'event_type' | 'horizon' | 'win_rate' | 'mae' | 'rmse' | 'sharpe_ratio' | 'total_predictions';
type SortDirection = 'asc' | 'desc';

export function MetricsTable({ metrics, loading = false }: MetricsTableProps) {
  const [sortColumn, setSortColumn] = useState<SortColumn>('win_rate');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [modelFilter, setModelFilter] = useState<string>('all');
  const [eventTypeFilter, setEventTypeFilter] = useState<string>('all');

  const uniqueModels = useMemo(() => {
    const models = new Set(metrics.map((m) => m.model_version));
    return Array.from(models).sort();
  }, [metrics]);

  const uniqueEventTypes = useMemo(() => {
    const types = new Set(metrics.map((m) => m.event_type));
    return Array.from(types).sort();
  }, [metrics]);

  const handleSort = (column: SortColumn) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('desc');
    }
  };

  let filteredMetrics = metrics;
  if (modelFilter !== 'all') {
    filteredMetrics = filteredMetrics.filter((m) => m.model_version === modelFilter);
  }
  if (eventTypeFilter !== 'all') {
    filteredMetrics = filteredMetrics.filter((m) => m.event_type === eventTypeFilter);
  }

  const filteredAndSortedMetrics = [...filteredMetrics].sort((a, b) => {
    let aVal: any = a[sortColumn];
    let bVal: any = b[sortColumn];

    if (aVal === null || aVal === undefined) return 1;
    if (bVal === null || bVal === undefined) return -1;

    if (typeof aVal === 'string') {
      aVal = aVal.toLowerCase();
      bVal = bVal.toLowerCase();
    }

    if (sortDirection === 'asc') {
      return aVal > bVal ? 1 : -1;
    } else {
      return aVal < bVal ? 1 : -1;
    }
  });

  const SortIcon = ({ column }: { column: SortColumn }) => {
    if (sortColumn !== column) {
      return <ChevronUp className="h-4 w-4 opacity-30" />;
    }
    return sortDirection === 'asc' ? (
      <ChevronUp className="h-4 w-4 text-[--success]" />
    ) : (
      <ChevronDown className="h-4 w-4 text-[--success]" />
    );
  };

  if (loading) {
    return (
      <div className="bg-[--surface-muted] rounded-lg p-6 border border-[--border]">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-[--surface-strong] rounded w-1/4"></div>
          <div className="h-64 bg-[--surface-strong] rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-[--surface-muted] rounded-lg border border-[--border] overflow-hidden">
      <div className="p-4 border-b border-[--border] bg-[--surface-muted]">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-[--muted]" />
            <span className="text-sm font-medium text-[--text]">Filters:</span>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-sm text-[--muted]">Model:</label>
            <select
              value={modelFilter}
              onChange={(e) => setModelFilter(e.target.value)}
              className="px-3 py-1 bg-[--surface-strong] border border-[--border-strong] rounded text-sm text-[--text]"
            >
              <option value="all">All Models</option>
              {uniqueModels.map((model) => (
                <option key={model} value={model}>
                  {model}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-sm text-[--muted]">Event Type:</label>
            <select
              value={eventTypeFilter}
              onChange={(e) => setEventTypeFilter(e.target.value)}
              className="px-3 py-1 bg-[--surface-strong] border border-[--border-strong] rounded text-sm text-[--text]"
            >
              <option value="all">All Types</option>
              {uniqueEventTypes.map((type) => (
                <option key={type} value={type}>
                  {type.replace(/_/g, ' ')}
                </option>
              ))}
            </select>
          </div>
          {(modelFilter !== 'all' || eventTypeFilter !== 'all') && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setModelFilter('all');
                setEventTypeFilter('all');
              }}
            >
              Clear Filters
            </Button>
          )}
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-[--border] bg-[--surface-muted]">
              <th className="text-left py-4 px-4 text-sm font-semibold">
                <button
                  onClick={() => handleSort('event_type')}
                  className="flex items-center gap-2 text-[--muted] hover:text-[--text] transition-colors select-none cursor-pointer"
                >
                  Event Type
                  <SortIcon column="event_type" />
                </button>
              </th>
              <th className="text-left py-4 px-4 text-sm font-semibold">
                <button
                  onClick={() => handleSort('horizon')}
                  className="flex items-center gap-2 text-[--muted] hover:text-[--text] transition-colors select-none cursor-pointer"
                >
                  Horizon
                  <SortIcon column="horizon" />
                </button>
              </th>
              <th className="text-left py-4 px-4 text-sm font-semibold text-[--muted]">
                Model Version
              </th>
              <th className="text-right py-4 px-4 text-sm font-semibold">
                <button
                  onClick={() => handleSort('win_rate')}
                  className="flex items-center justify-end gap-2 text-[--muted] hover:text-[--text] transition-colors select-none cursor-pointer w-full"
                >
                  Win Rate
                  <SortIcon column="win_rate" />
                </button>
              </th>
              <th className="text-right py-4 px-4 text-sm font-semibold">
                <button
                  onClick={() => handleSort('mae')}
                  className="flex items-center justify-end gap-2 text-[--muted] hover:text-[--text] transition-colors select-none cursor-pointer w-full"
                >
                  MAE
                  <SortIcon column="mae" />
                </button>
              </th>
              <th className="text-right py-4 px-4 text-sm font-semibold">
                <button
                  onClick={() => handleSort('rmse')}
                  className="flex items-center justify-end gap-2 text-[--muted] hover:text-[--text] transition-colors select-none cursor-pointer w-full"
                >
                  RMSE
                  <SortIcon column="rmse" />
                </button>
              </th>
              <th className="text-right py-4 px-4 text-sm font-semibold">
                <button
                  onClick={() => handleSort('sharpe_ratio')}
                  className="flex items-center justify-end gap-2 text-[--muted] hover:text-[--text] transition-colors select-none cursor-pointer w-full"
                >
                  Sharpe Ratio
                  <SortIcon column="sharpe_ratio" />
                </button>
              </th>
              <th className="text-right py-4 px-4 text-sm font-semibold">
                <button
                  onClick={() => handleSort('total_predictions')}
                  className="flex items-center justify-end gap-2 text-[--muted] hover:text-[--text] transition-colors select-none cursor-pointer w-full"
                >
                  Predictions
                  <SortIcon column="total_predictions" />
                </button>
              </th>
            </tr>
          </thead>
          <tbody>
            {filteredAndSortedMetrics.length === 0 ? (
              <tr>
                <td colSpan={8} className="py-12 text-center text-[--muted]">
                  No metrics found matching your filters
                </td>
              </tr>
            ) : (
              filteredAndSortedMetrics.map((metric, index) => (
                <tr
                  key={`${metric.event_type}-${metric.horizon}-${metric.model_version}-${index}`}
                  className="border-b border-[--border-muted] hover:bg-[--surface-muted] transition-colors"
                >
                  <td className="py-3 px-4">
                    <span className="font-medium text-[--text]">
                      {metric.event_type.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td className="py-3 px-4">
                    <span className="text-[--text]">{metric.horizon}</span>
                  </td>
                  <td className="py-3 px-4">
                    <span className="px-2 py-1 bg-[--accent-soft] border border-[--border-strong] rounded text-xs text-[--accent]">
                      {metric.model_version}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right">
                    <span className="text-[--success] font-semibold">
                      {(metric.win_rate > 1 ? metric.win_rate : metric.win_rate * 100).toFixed(1)}%
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right">
                    <span className="text-[--primary]">{metric.mae.toFixed(4)}</span>
                  </td>
                  <td className="py-3 px-4 text-right">
                    <span className="text-[--warning]">{metric.rmse.toFixed(4)}</span>
                  </td>
                  <td className="py-3 px-4 text-right">
                    {metric.sharpe_ratio !== null ? (
                      <span className="text-[--text] font-medium">
                        {metric.sharpe_ratio.toFixed(2)}
                      </span>
                    ) : (
                      <span className="text-[--muted] text-xs">N/A</span>
                    )}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <span className="text-[--muted]">{metric.total_predictions.toLocaleString()}</span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="p-4 border-t border-[--border] bg-[--surface-muted] text-sm text-[--muted]">
        Showing {filteredAndSortedMetrics.length} of {metrics.length} metrics
        <span className="ml-4 text-[--success]">
          Sorted by: {sortColumn.replace('_', ' ')} ({sortDirection})
        </span>
      </div>
    </div>
  );
}
