'use client';

import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Copy, ExternalLink, Hash, Calendar, TrendingUp, TrendingDown, Minus, CheckCircle, XCircle } from 'lucide-react';
import { apiRequest } from '@/lib/api-client';

interface SourceEvent {
  ticker: string;
  event_type: string;
  date: string;
  source_url: string;
  event_id: number;
  title: string;
}

interface OutcomeData {
  horizon: string;
  return_pct: number | null; // Abnormal return (stock - benchmark)
  return_pct_raw: number | null; // Raw stock return
  abs_return_pct: number | null; // Absolute return magnitude
  direction_correct: boolean | null;
  has_benchmark_data: boolean; // Whether SPY benchmark data was available
}

interface PriceRecord {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface LineageData {
  metric_key: string;
  metric_name: string;
  source_events: SourceEvent[];
  outcomes: OutcomeData[];
  price_history: PriceRecord[];
  payload_hash: string;
  generated_at: string;
  total_events: number;
}

interface LineageDrilldownModalProps {
  metric_key: string;
  isOpen: boolean;
  onClose: () => void;
}

export function LineageDrilldownModal({
  metric_key,
  isOpen,
  onClose,
}: LineageDrilldownModalProps) {
  const [data, setData] = useState<LineageData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedItem, setCopiedItem] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && metric_key) {
      loadLineageData();
    }
  }, [isOpen, metric_key]);

  const loadLineageData = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiRequest<LineageData>(
        `/api/proxy/data-quality/lineage/${encodeURIComponent(metric_key)}`
      );
      setData(response);
    } catch (err: any) {
      console.error('Failed to load lineage data:', err);
      
      let errorMessage = 'Failed to load lineage data';
      if (err?.status === 404) {
        errorMessage = `No lineage data found for metric "${metric_key}". This metric may not have associated events yet.`;
      } else if (err?.status === 403) {
        errorMessage = 'Data lineage requires a Pro or Team plan.';
      } else if (err?.message) {
        errorMessage = err.message;
      }
      
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = async (text: string, itemId: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedItem(itemId);
      setTimeout(() => setCopiedItem(null), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Data Lineage: {metric_key}</DialogTitle>
        </DialogHeader>

        {loading && (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-400"></div>
            <p className="ml-3 text-[--muted]">Loading lineage data...</p>
          </div>
        )}

        {error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}

        {!loading && !error && data && (
          <div className="space-y-6">
            {/* Metadata Section */}
            <div className="bg-white/5 rounded-lg p-4 border border-white/10">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <p className="text-xs text-[--muted] mb-1">Metric Name</p>
                  <p className="text-sm font-semibold text-[--text]">{data.metric_name}</p>
                </div>
                <div>
                  <p className="text-xs text-[--muted] mb-1">Total Events</p>
                  <p className="text-sm font-semibold text-emerald-400">{data.total_events}</p>
                </div>
                <div>
                  <p className="text-xs text-[--muted] mb-1">Generated At</p>
                  <p className="text-sm font-semibold text-[--text]">
                    {formatDate(data.generated_at)}
                  </p>
                </div>
              </div>

              {data.payload_hash && (
                <div className="mt-4 pt-4 border-t border-white/10">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Hash className="h-4 w-4 text-[--muted]" />
                      <span className="text-xs text-[--muted]">Payload Hash:</span>
                      <code className="text-xs font-mono text-[--text] bg-black/30 px-2 py-1 rounded">
                        {data.payload_hash.substring(0, 16)}...
                      </code>
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => copyToClipboard(data.payload_hash, 'hash')}
                    >
                      {copiedItem === 'hash' ? (
                        <CheckCircle className="h-3 w-3 text-green-400" />
                      ) : (
                        <Copy className="h-3 w-3" />
                      )}
                      <span className="ml-1">Copy Hash</span>
                    </Button>
                  </div>
                </div>
              )}
            </div>

            {/* Source Events Table */}
            <div className="bg-white/5 rounded-lg p-4 border border-white/10">
              <h3 className="text-lg font-semibold text-[--text] mb-4">Source Events</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-white/10">
                      <th className="text-left py-3 px-3 text-xs font-semibold text-[--muted]">
                        Ticker
                      </th>
                      <th className="text-left py-3 px-3 text-xs font-semibold text-[--muted]">
                        Event Type
                      </th>
                      <th className="text-left py-3 px-3 text-xs font-semibold text-[--muted]">
                        Date
                      </th>
                      <th className="text-left py-3 px-3 text-xs font-semibold text-[--muted]">
                        Title
                      </th>
                      <th className="text-right py-3 px-3 text-xs font-semibold text-[--muted]">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.source_events.map((event, idx) => (
                      <tr
                        key={idx}
                        className="border-b border-white/5 hover:bg-white/5 transition-colors"
                      >
                        <td className="py-3 px-3 font-mono font-semibold text-[--text]">
                          {event.ticker}
                        </td>
                        <td className="py-3 px-3">
                          <span className="inline-flex items-center px-2 py-1 rounded text-xs bg-blue-500/10 text-blue-400">
                            {event.event_type}
                          </span>
                        </td>
                        <td className="py-3 px-3 text-[--muted]">
                          <div className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            {formatDate(event.date)}
                          </div>
                        </td>
                        <td className="py-3 px-3 text-[--text] max-w-xs truncate">
                          {event.title}
                        </td>
                        <td className="py-3 px-3 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() =>
                                copyToClipboard(event.source_url, `url-${idx}`)
                              }
                            >
                              {copiedItem === `url-${idx}` ? (
                                <CheckCircle className="h-3 w-3 text-green-400" />
                              ) : (
                                <Copy className="h-3 w-3" />
                              )}
                            </Button>
                            <a
                              href={event.source_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-emerald-400 hover:text-emerald-300 transition-colors"
                            >
                              <Button size="sm" variant="ghost">
                                <ExternalLink className="h-3 w-3" />
                                <span className="ml-1">View Source</span>
                              </Button>
                            </a>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Outcome Data */}
            {data.outcomes && data.outcomes.length > 0 && (
              <div className="bg-white/5 rounded-lg p-4 border border-white/10">
                <h3 className="text-lg font-semibold text-[--text] mb-4">Outcome Data</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {data.outcomes.map((outcome, idx) => (
                    <div
                      key={idx}
                      className="bg-white/5 rounded-lg p-4 border border-white/10"
                    >
                      <div className="flex items-center justify-between mb-3">
                        <h4 className="font-semibold text-[--text]">{outcome.horizon}</h4>
                        {outcome.direction_correct === true ? (
                          <CheckCircle className="h-5 w-5 text-green-400" />
                        ) : outcome.direction_correct === false ? (
                          <XCircle className="h-5 w-5 text-red-400" />
                        ) : (
                          <Minus className="h-5 w-5 text-gray-400" />
                        )}
                      </div>

                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-[--muted]">
                            Abnormal Return
                            {outcome.has_benchmark_data && (
                              <span className="ml-1 text-[10px]">(vs SPY)</span>
                            )}
                          </span>
                          <div className="flex items-center gap-1">
                            {outcome.return_pct !== null ? (
                              <>
                                {outcome.return_pct > 0 ? (
                                  <TrendingUp className="h-3 w-3 text-green-400" />
                                ) : outcome.return_pct < 0 ? (
                                  <TrendingDown className="h-3 w-3 text-red-400" />
                                ) : (
                                  <Minus className="h-3 w-3 text-gray-400" />
                                )}
                                <span
                                  className={`text-sm font-semibold ${
                                    outcome.return_pct > 0
                                      ? 'text-green-400'
                                      : outcome.return_pct < 0
                                      ? 'text-red-400'
                                      : 'text-gray-400'
                                  }`}
                                >
                                  {outcome.return_pct.toFixed(2)}%
                                </span>
                              </>
                            ) : (
                              <span className="text-sm text-gray-400">N/A</span>
                            )}
                          </div>
                        </div>

                        <div className="flex items-center justify-between">
                          <span className="text-xs text-[--muted]">Raw Return</span>
                          <div className="flex items-center gap-1">
                            {outcome.return_pct_raw !== null ? (
                              <>
                                {outcome.return_pct_raw > 0 ? (
                                  <TrendingUp className="h-3 w-3 text-green-400" />
                                ) : outcome.return_pct_raw < 0 ? (
                                  <TrendingDown className="h-3 w-3 text-red-400" />
                                ) : (
                                  <Minus className="h-3 w-3 text-gray-400" />
                                )}
                                <span
                                  className={`text-sm font-semibold ${
                                    outcome.return_pct_raw > 0
                                      ? 'text-green-400'
                                      : outcome.return_pct_raw < 0
                                      ? 'text-red-400'
                                      : 'text-gray-400'
                                  }`}
                                >
                                  {outcome.return_pct_raw.toFixed(2)}%
                                </span>
                              </>
                            ) : (
                              <span className="text-sm text-gray-400">N/A</span>
                            )}
                          </div>
                        </div>

                        <div className="pt-2 border-t border-white/10">
                          <span
                            className={`text-xs font-semibold ${
                              outcome.direction_correct === true
                                ? 'text-green-400'
                                : outcome.direction_correct === false
                                ? 'text-red-400'
                                : 'text-gray-400'
                            }`}
                          >
                            {outcome.direction_correct === true
                              ? 'Direction Correct'
                              : outcome.direction_correct === false
                              ? 'Direction Incorrect'
                              : 'Not Evaluated'}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Price History */}
            {data.price_history && data.price_history.length > 0 && (
              <div className="bg-white/5 rounded-lg p-4 border border-white/10">
                <h3 className="text-lg font-semibold text-[--text] mb-4">
                  Price History ({data.price_history.length} records)
                </h3>
                <div className="overflow-x-auto max-h-64 overflow-y-auto">
                  <table className="w-full text-sm">
                    <thead className="sticky top-0 bg-[--panel]">
                      <tr className="border-b border-white/10">
                        <th className="text-left py-2 px-3 text-xs font-semibold text-[--muted]">
                          Date
                        </th>
                        <th className="text-right py-2 px-3 text-xs font-semibold text-[--muted]">
                          Open
                        </th>
                        <th className="text-right py-2 px-3 text-xs font-semibold text-[--muted]">
                          High
                        </th>
                        <th className="text-right py-2 px-3 text-xs font-semibold text-[--muted]">
                          Low
                        </th>
                        <th className="text-right py-2 px-3 text-xs font-semibold text-[--muted]">
                          Close
                        </th>
                        <th className="text-right py-2 px-3 text-xs font-semibold text-[--muted]">
                          Volume
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.price_history.map((record, idx) => (
                        <tr
                          key={idx}
                          className="border-b border-white/5 hover:bg-white/5"
                        >
                          <td className="py-2 px-3 text-[--muted]">
                            {formatDate(record.date)}
                          </td>
                          <td className="py-2 px-3 text-right text-[--text]">
                            ${record.open.toFixed(2)}
                          </td>
                          <td className="py-2 px-3 text-right text-green-400">
                            ${record.high.toFixed(2)}
                          </td>
                          <td className="py-2 px-3 text-right text-red-400">
                            ${record.low.toFixed(2)}
                          </td>
                          <td className="py-2 px-3 text-right text-[--text] font-semibold">
                            ${record.close.toFixed(2)}
                          </td>
                          <td className="py-2 px-3 text-right text-[--muted] text-xs">
                            {(record.volume / 1000000).toFixed(2)}M
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
