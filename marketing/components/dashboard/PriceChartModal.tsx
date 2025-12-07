'use client';

import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { X, TrendingUp, TrendingDown, Calendar, DollarSign } from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
  Dot,
} from 'recharts';

interface PriceDataPoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface EventMarker {
  date: string;
  event_id: number;
  title: string;
  impact_score: number;
  direction: string;
  event_type: string;
}

interface ChartData {
  ticker: string;
  data: PriceDataPoint[];
  events: EventMarker[];
  price_range: {
    min: number;
    max: number;
  };
}

interface PriceChartModalProps {
  open: boolean;
  onClose: () => void;
  ticker: string;
  initialDays?: number;
  focusEventDate?: string;
}

export function PriceChartModal({
  open,
  onClose,
  ticker,
  initialDays = 90,
  focusEventDate,
}: PriceChartModalProps) {
  const [chartData, setChartData] = useState<ChartData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedDays, setSelectedDays] = useState(initialDays);
  const [showEvents, setShowEvents] = useState(true);

  const dateRangeOptions = [
    { label: '30d', value: 30 },
    { label: '60d', value: 60 },
    { label: '90d', value: 90 },
    { label: '180d', value: 180 },
    { label: '1y', value: 365 },
  ];

  useEffect(() => {
    if (open && ticker) {
      loadChartData();
    }
  }, [open, ticker, selectedDays, showEvents]);

  const loadChartData = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(
        `/api/proxy/charts/ticker/${ticker}?days=${selectedDays}&show_events=${showEvents}`
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        
        // Handle specific error cases with user-friendly messages
        if (response.status === 401 || response.status === 403) {
          if (errorData.code === 'EMAIL_NOT_VERIFIED') {
            throw new Error('Please verify your email to access price charts.');
          } else if (errorData.code === 'PREMIUM_FEATURE_REQUIRED') {
            throw new Error('Price charts require a Pro or Team plan. Upgrade to access this feature.');
          } else {
            throw new Error('Please sign in to view price charts.');
          }
        } else if (response.status === 404) {
          throw new Error(`No price data available for ${ticker}. This may be a delisted or invalid ticker.`);
        }
        
        throw new Error(errorData.detail || 'Failed to load chart data. Please try again.');
      }

      const data: ChartData = await response.json();
      setChartData(data);
    } catch (err: any) {
      console.error('Failed to load chart data:', err);
      setError(err.message || 'Failed to load chart data');
    } finally {
      setLoading(false);
    }
  };

  const getDirectionColor = (direction: string) => {
    switch (direction) {
      case 'positive':
        return '#10b981'; // green-500
      case 'negative':
        return '#ef4444'; // red-500
      case 'neutral':
        return '#9ca3af'; // gray-400
      default:
        return '#eab308'; // yellow-500
    }
  };

  const CustomDot = (props: any) => {
    const { cx, cy, payload } = props;

    if (!showEvents || !chartData) return null;

    const eventOnDate = chartData.events.find(
      (e) => e.date === payload.date
    );

    if (!eventOnDate) return null;

    const color = getDirectionColor(eventOnDate.direction);

    return (
      <g>
        <circle
          cx={cx}
          cy={cy}
          r={6}
          fill={color}
          stroke="#fff"
          strokeWidth={2}
          style={{ cursor: 'pointer' }}
        />
        <circle
          cx={cx}
          cy={cy}
          r={3}
          fill="#fff"
        />
      </g>
    );
  };

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload || !payload.length) return null;

    const price = payload[0].value;
    const eventsOnDate = chartData?.events.filter((e) => e.date === label) || [];

    const calculateProjectedChange = (currentPrice: number, impactScore: number, direction: string) => {
      const directionMultiplier = direction === 'positive' ? 1 : direction === 'negative' ? -1 : 0;
      
      // Scale impact score (0-100) to realistic percentage movements
      // Impact scores represent event severity, not direct percentage changes
      // Formula: Scale by ~12% max, adjusted by score and confidence
      // Examples: Score 80 → ~9.6%, Score 60 → ~7.2%, Score 50 → ~6%
      const percentageChange = (impactScore / 100) * 12 * directionMultiplier;
      const dollarChange = currentPrice * (percentageChange / 100);
      
      return {
        dollarChange,
        percentageChange,
      };
    };

    return (
      <div className="bg-[--panel] border-2 border-[--border] rounded-lg p-4 shadow-2xl max-w-md">
        <p className="text-sm text-[--muted] mb-2 font-medium">{label}</p>
        <div className="flex items-center gap-2 mb-2">
          <DollarSign className="h-4 w-4 text-[--primary]" />
          <span className="text-lg font-bold text-[--text]">
            ${price.toFixed(2)}
          </span>
        </div>
        {eventsOnDate.length > 0 && (
          <div className="mt-3 pt-3 border-t border-[--border] space-y-3">
            {eventsOnDate.map((event, idx) => {
              const projectedChange = calculateProjectedChange(price, event.impact_score, event.direction);
              return (
                <div key={event.event_id} className={idx > 0 ? 'pt-3 border-t border-[--border]' : ''}>
                  <div className="flex items-center gap-2 mb-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: getDirectionColor(event.direction) }}
                    />
                    <span className="text-sm font-semibold text-[--text]">
                      {eventsOnDate.length > 1 ? `Event ${idx + 1}` : 'Event'}
                    </span>
                  </div>
                  <p className="text-sm text-[--text] mb-1">{event.title}</p>
                  <div className="flex items-center gap-3 text-xs text-[--muted] mb-2">
                    <span>Impact: {event.impact_score}</span>
                    <span className="capitalize">{event.direction}</span>
                    <span>{event.event_type.replace(/_/g, ' ')}</span>
                  </div>
                  {projectedChange && projectedChange.dollarChange !== 0 && (
                    <div className="mt-2 pt-2 border-t border-[--border]">
                      <p className="text-xs text-[--muted] mb-1">Projected Impact:</p>
                      <div className="flex items-center gap-3 text-xs">
                        <span className={`font-semibold ${
                          projectedChange.dollarChange > 0 ? 'text-[--success]' : 'text-[--error]'
                        }`}>
                          {projectedChange.dollarChange > 0 ? '+' : ''}${Math.abs(projectedChange.dollarChange).toFixed(2)}
                        </span>
                        <span className={`font-semibold ${
                          projectedChange.percentageChange > 0 ? 'text-[--success]' : 'text-[--error]'
                        }`}>
                          ({projectedChange.percentageChange > 0 ? '+' : ''}{projectedChange.percentageChange.toFixed(2)}%)
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  };

  const calculatePriceChange = () => {
    if (!chartData || chartData.data.length < 2) return null;

    const firstPrice = chartData.data[0].close;
    const lastPrice = chartData.data[chartData.data.length - 1].close;
    const change = lastPrice - firstPrice;
    const changePercent = (change / firstPrice) * 100;

    return {
      change,
      changePercent,
      isPositive: change >= 0,
    };
  };

  const priceChange = calculatePriceChange();

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="max-w-6xl max-h-[90vh] overflow-hidden bg-[--modal-bg]">
        <DialogHeader className="border-b border-[--border] pb-4">
          <div className="flex items-center justify-between">
            <div>
              <DialogTitle className="text-2xl font-bold text-[--text]">
                {ticker} Price Chart
              </DialogTitle>
              <div className="flex items-center gap-4 mt-2">
                {priceChange && (
                  <div className="flex items-center gap-2">
                    {priceChange.isPositive ? (
                      <TrendingUp className="h-5 w-5 text-[--success]" />
                    ) : (
                      <TrendingDown className="h-5 w-5 text-[--error]" />
                    )}
                    <span
                      className={`text-lg font-semibold ${
                        priceChange.isPositive ? 'text-[--success]' : 'text-[--error]'
                      }`}
                    >
                      {priceChange.isPositive ? '+' : ''}
                      {priceChange.changePercent.toFixed(2)}%
                    </span>
                    <span className="text-sm text-[--muted]">
                      ({priceChange.change >= 0 ? '+' : ''}${priceChange.change.toFixed(2)})
                    </span>
                  </div>
                )}
                {chartData && (
                  <span className="text-sm text-[--muted]">
                    {chartData.events.length} {chartData.events.length === 1 ? 'event' : 'events'} in period
                  </span>
                )}
              </div>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-6 overflow-y-auto">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Calendar className="h-4 w-4 text-[--muted]" />
                <span className="text-sm text-[--muted]">Time Period:</span>
                <div className="flex gap-2">
                  {dateRangeOptions.map((option) => (
                    <button
                      key={option.value}
                      onClick={() => setSelectedDays(option.value)}
                      className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                        selectedDays === option.value
                          ? 'bg-[--primary] text-[--text-on-primary]'
                          : 'bg-[--surface-glass] text-[--muted] hover:bg-[--surface-hover]'
                      }`}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex items-center gap-2">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={showEvents}
                    onChange={(e) => setShowEvents(e.target.checked)}
                    className="w-4 h-4 rounded border-[--border] bg-[--surface-muted] text-[--primary] focus:ring-[--primary] focus:ring-offset-0"
                  />
                  <span className="text-sm text-[--text]">Show Event Markers</span>
                </label>
              </div>
            </div>

            {loading && (
              <div className="flex items-center justify-center py-32">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[--primary] mx-auto mb-4"></div>
                  <p className="text-[--muted]">Loading chart data...</p>
                </div>
              </div>
            )}

            {error && (
              <div className="bg-[--error-light] border border-[--border] rounded-lg p-6 text-center">
                <p className="text-[--error] mb-2 font-semibold">Failed to load chart</p>
                <p className="text-sm text-[--muted]">{error}</p>
                <Button onClick={loadChartData} className="mt-4">
                  Retry
                </Button>
              </div>
            )}

            {!loading && !error && chartData && chartData.data.length > 0 && (
              <div className="bg-[--surface-muted] rounded-lg p-4">
                <ResponsiveContainer width="100%" height={400}>
                  <LineChart
                    data={chartData.data}
                    margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                    <XAxis
                      dataKey="date"
                      stroke="rgba(255,255,255,0.5)"
                      style={{ fontSize: '12px' }}
                      tickFormatter={(value) => {
                        const date = new Date(value);
                        return `${date.getMonth() + 1}/${date.getDate()}`;
                      }}
                    />
                    <YAxis
                      stroke="rgba(255,255,255,0.5)"
                      style={{ fontSize: '12px' }}
                      domain={['auto', 'auto']}
                      tickFormatter={(value) => `$${value.toFixed(0)}`}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend
                      wrapperStyle={{ fontSize: '12px' }}
                      iconType="line"
                    />
                    <Line
                      type="monotone"
                      dataKey="close"
                      stroke="#3b82f6"
                      strokeWidth={2}
                      name="Close Price"
                      dot={<CustomDot />}
                      activeDot={{ r: 8 }}
                    />
                    {showEvents && chartData.events.map((event) => (
                      <ReferenceLine
                        key={event.event_id}
                        x={event.date}
                        stroke={getDirectionColor(event.direction)}
                        strokeDasharray="3 3"
                        strokeWidth={1}
                        opacity={0.5}
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>

                {showEvents && chartData.events.length > 0 && (
                  <div className="mt-6 pt-6 border-t border-[--border]">
                    <h4 className="text-sm font-semibold text-[--text] mb-3">Events in Period</h4>
                    <div className="space-y-2 max-h-40 overflow-y-auto">
                      {chartData.events.map((event) => (
                        <div
                          key={event.event_id}
                          className="flex items-center gap-3 p-2 bg-[--surface-muted] rounded hover:bg-[--surface-hover] transition-colors"
                        >
                          <div
                            className="w-3 h-3 rounded-full flex-shrink-0"
                            style={{ backgroundColor: getDirectionColor(event.direction) }}
                          />
                          <div className="flex-1 min-w-0">
                            <p className="text-sm text-[--text] truncate">{event.title}</p>
                            <p className="text-xs text-[--muted]">
                              {new Date(event.date).toLocaleDateString('en-US', { timeZone: 'America/New_York', month: '2-digit', day: '2-digit', year: 'numeric' })} • Impact: {event.impact_score}%
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

          {!loading && !error && chartData && chartData.data.length === 0 && (
            <div className="text-center py-12">
              <p className="text-[--muted]">No price data available for this ticker</p>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
