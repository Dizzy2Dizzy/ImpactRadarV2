'use client';

import { useState, useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  ReferenceArea,
  Bar,
  ComposedChart,
  Cell,
  Scatter,
} from 'recharts';
import { TrendingUp, TrendingDown, Minus, Calendar, Activity, BarChart3 } from 'lucide-react';
import { DisplayVersion } from './ImpactScoreBadge';

interface EventMarker {
  time: number;
  position: 'aboveBar' | 'belowBar';
  color: string;
  shape: string;
  text: string;
  event_id: number;
  title?: string;
  event_type?: string;
  impact_score?: number;
  direction?: string;
  confidence?: number;
  ml_adjusted_score?: number | null;
  ml_confidence?: number | null;
  impact_p_move?: number | null;
  impact_p_up?: number | null;
  impact_p_down?: number | null;
  model_source?: string | null;
  bearish_signal?: boolean | null;
  bearish_score?: number | null;
  bearish_confidence?: number | null;
  bearish_rationale?: string | null;
}

interface OHLCVDataPoint {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface IndicatorPoint {
  time: number;
  value: number | null;
}

interface ProjectorEventChartProps {
  ticker: string;
  ohlcvData: OHLCVDataPoint[];
  events: EventMarker[];
  indicators?: {
    sma_20?: IndicatorPoint[];
    sma_50?: IndicatorPoint[];
    sma_200?: IndicatorPoint[];
    ema_20?: IndicatorPoint[];
    ema_50?: IndicatorPoint[];
  };
  rsiData?: IndicatorPoint[];
  macdData?: {
    macd: IndicatorPoint[];
    signal: IndicatorPoint[];
    histogram: IndicatorPoint[];
  };
  chartType?: 'candlestick' | 'line';
  showSMA20?: boolean;
  showSMA50?: boolean;
  showSMA200?: boolean;
  showEMA20?: boolean;
  showEMA50?: boolean;
  showRSI?: boolean;
  showMACD?: boolean;
  showEvents?: boolean;
  modelVersion: DisplayVersion;
  loading?: boolean;
}

interface ChartDataPoint {
  time: number;
  date: string;
  dateShort: string;
  price: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  sma20?: number | null;
  sma50?: number | null;
  sma200?: number | null;
  ema20?: number | null;
  ema50?: number | null;
  hasEvent: boolean;
  eventId?: number;
  eventTitle?: string;
  eventType?: string;
  impactScore?: number;
  direction?: string;
  confidence?: number;
  projectedPrice?: number;
  projectedPctChange?: number;
  mlConfidence?: number;
  modelSource?: string;
  bearishSignal?: boolean;
  bearishScore?: number;
  bearishConfidence?: number;
  bearishRationale?: string;
}

interface RSIDataPoint {
  time: number;
  date: string;
  rsi: number | null;
  hasEvent: boolean;
  eventId?: number;
}

// Calculate RSI chart domain that fills the chart while keeping reference lines visible
function calculateRSIDomain(rsiData: RSIDataPoint[]): [number, number] {
  const validValues = rsiData.filter(d => d.rsi !== null).map(d => d.rsi as number);
  if (validValues.length === 0) return [0, 100];
  
  const min = Math.min(...validValues);
  const max = Math.max(...validValues);
  const range = max - min;
  
  // Use dynamic padding based on the data range to fill the chart
  // Smaller ranges get more padding, larger ranges get less
  const paddingPercent = range < 10 ? 0.5 : range < 20 ? 0.3 : 0.2;
  const padding = Math.max(range * paddingPercent, 5);
  
  // Ensure we include 30/70 reference lines if data is close
  let paddedMin = min - padding;
  let paddedMax = max + padding;
  
  // Include reference lines if they're close to the data
  if (min <= 35) paddedMin = Math.min(paddedMin, 25);
  if (max >= 65) paddedMax = Math.max(paddedMax, 75);
  
  // Clamp to valid RSI range
  return [Math.max(0, paddedMin), Math.min(100, paddedMax)];
}

interface MACDDataPoint {
  time: number;
  date: string;
  macd: number | null;
  signal: number | null;
  histogram: number | null;
  histogramColor: string;
  hasEvent: boolean;
  eventId?: number;
}

export function ProjectorEventChart({
  ticker,
  ohlcvData,
  events,
  indicators = {},
  rsiData = [],
  macdData,
  chartType = 'candlestick',
  showSMA20 = true,
  showSMA50 = true,
  showSMA200 = false,
  showEMA20 = false,
  showEMA50 = false,
  showRSI = true,
  showMACD = true,
  showEvents = true,
  modelVersion,
  loading = false,
}: ProjectorEventChartProps) {
  // All events for the table (always shown regardless of showEvents toggle)
  const allEventsForTable = useMemo(() => {
    if (modelVersion === 'v2.0') {
      return events.filter(e => e.model_source !== 'deterministic' && e.ml_adjusted_score != null);
    }
    return events;
  }, [events, modelVersion]);

  // Filtered events for chart markers (controlled by showEvents toggle)
  const filteredEvents = useMemo(() => {
    if (!showEvents) return [];
    return allEventsForTable;
  }, [allEventsForTable, showEvents]);

  const eventsByTime = useMemo(() => {
    const map = new Map<number, EventMarker>();
    filteredEvents.forEach(event => {
      map.set(event.time, event);
    });
    return map;
  }, [filteredEvents]);

  const indicatorsByTime = useMemo(() => {
    const sma20Map = new Map<number, number>();
    const sma50Map = new Map<number, number>();
    const sma200Map = new Map<number, number>();
    const ema20Map = new Map<number, number>();
    const ema50Map = new Map<number, number>();

    indicators.sma_20?.forEach(p => p.value != null && sma20Map.set(p.time, p.value));
    indicators.sma_50?.forEach(p => p.value != null && sma50Map.set(p.time, p.value));
    indicators.sma_200?.forEach(p => p.value != null && sma200Map.set(p.time, p.value));
    indicators.ema_20?.forEach(p => p.value != null && ema20Map.set(p.time, p.value));
    indicators.ema_50?.forEach(p => p.value != null && ema50Map.set(p.time, p.value));

    return { sma20Map, sma50Map, sma200Map, ema20Map, ema50Map };
  }, [indicators]);

  const chartData: ChartDataPoint[] = useMemo(() => {
    return ohlcvData.map(point => {
      const event = eventsByTime.get(point.time);
      const date = new Date(point.time * 1000).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });
      const dateShort = new Date(point.time * 1000).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
      });

      let projectedPrice: number | undefined;
      let projectedPctChange: number | undefined;

      if (event && event.impact_p_move != null) {
        const pctMove = event.impact_p_move * 100;
        const isUpward = (event.impact_p_up ?? 0) >= (event.impact_p_down ?? 0);
        projectedPctChange = isUpward ? pctMove : -pctMove;
        projectedPrice = point.close * (1 + projectedPctChange / 100);
      }

      const sma20Val = indicatorsByTime.sma20Map.get(point.time) ?? null;
      const sma50Val = indicatorsByTime.sma50Map.get(point.time) ?? null;
      
      return {
        time: point.time,
        date,
        dateShort,
        price: point.close,
        open: point.open,
        high: point.high,
        low: point.low,
        close: point.close,
        volume: point.volume,
        sma20: sma20Val,
        sma50: sma50Val,
        sma200: indicatorsByTime.sma200Map.get(point.time) ?? null,
        ema20: indicatorsByTime.ema20Map.get(point.time) ?? null,
        ema50: indicatorsByTime.ema50Map.get(point.time) ?? null,
        hasEvent: !!event,
        eventId: event?.event_id,
        eventTitle: event?.title,
        eventType: event?.event_type,
        impactScore: event?.impact_score ?? event?.ml_adjusted_score ?? undefined,
        direction: event?.direction,
        confidence: event?.confidence,
        projectedPrice,
        projectedPctChange,
        mlConfidence: event?.ml_confidence ?? undefined,
        modelSource: event?.model_source ?? undefined,
        bearishSignal: event?.bearish_signal ?? false,
        bearishScore: event?.bearish_score ?? undefined,
        bearishConfidence: event?.bearish_confidence ?? undefined,
        bearishRationale: event?.bearish_rationale ?? undefined,
      };
    });
  }, [ohlcvData, eventsByTime, indicatorsByTime]);

  // Create lookup maps for RSI and MACD data by time
  const rsiByTime = useMemo(() => {
    const map = new Map<number, number | null>();
    rsiData.forEach(p => map.set(p.time, p.value));
    return map;
  }, [rsiData]);

  const macdByTime = useMemo(() => {
    const macdMap = new Map<number, number | null>();
    const signalMap = new Map<number, number | null>();
    const histogramMap = new Map<number, number | null>();
    if (macdData) {
      macdData.macd.forEach(p => macdMap.set(p.time, p.value));
      macdData.signal.forEach(p => signalMap.set(p.time, p.value));
      macdData.histogram.forEach(p => histogramMap.set(p.time, p.value));
    }
    return { macdMap, signalMap, histogramMap };
  }, [macdData]);

  // RSI data aligned with OHLCV data (same x-axis range)
  const rsiChartData: RSIDataPoint[] = useMemo(() => {
    const result = ohlcvData.map(point => {
      const event = eventsByTime.get(point.time);
      const date = new Date(point.time * 1000).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
      });
      return {
        time: point.time,
        date,
        rsi: rsiByTime.get(point.time) ?? null,
        hasEvent: !!event,
        eventId: event?.event_id,
      };
    });
    
    // Debug: log RSI data stats
    const validRsi = result.filter(d => d.rsi !== null);
    if (validRsi.length > 0) {
      const rsiValues = validRsi.map(d => d.rsi as number);
      console.log('[RSI Debug] Valid points:', validRsi.length, 'of', result.length);
      console.log('[RSI Debug] Range:', Math.min(...rsiValues).toFixed(2), '-', Math.max(...rsiValues).toFixed(2));
    } else {
      console.log('[RSI Debug] No valid RSI values found!');
      console.log('[RSI Debug] rsiData prop length:', rsiData.length);
      console.log('[RSI Debug] ohlcvData length:', ohlcvData.length);
    }
    
    return result;
  }, [ohlcvData, rsiByTime, eventsByTime, rsiData.length]);

  // MACD data aligned with OHLCV data (same x-axis range)
  const macdChartData: MACDDataPoint[] = useMemo(() => {
    const result = ohlcvData.map(point => {
      const event = eventsByTime.get(point.time);
      const date = new Date(point.time * 1000).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
      });
      const macdVal = macdByTime.macdMap.get(point.time) ?? null;
      const signalVal = macdByTime.signalMap.get(point.time) ?? null;
      const histVal = macdByTime.histogramMap.get(point.time) ?? null;
      return {
        time: point.time,
        date,
        macd: macdVal,
        signal: signalVal,
        histogram: histVal,
        histogramColor: histVal !== null && histVal >= 0 ? '#10b981' : '#ef4444',
        hasEvent: !!event,
        eventId: event?.event_id,
      };
    });
    
    // Debug: log MACD data stats
    const validMacd = result.filter(d => d.macd !== null);
    if (validMacd.length > 0) {
      const macdValues = validMacd.map(d => d.macd as number);
      console.log('[MACD Debug] Valid points:', validMacd.length, 'of', result.length);
      console.log('[MACD Debug] Range:', Math.min(...macdValues).toFixed(2), '-', Math.max(...macdValues).toFixed(2));
    } else {
      console.log('[MACD Debug] No valid MACD values found!');
      console.log('[MACD Debug] macdData prop:', macdData ? 'exists' : 'null');
    }
    
    return result;
  }, [ohlcvData, macdByTime, eventsByTime, macdData]);

  const priceRange = useMemo(() => {
    if (chartData.length === 0) return { min: 0, max: 100 };
    
    const allPrices: number[] = [];
    chartData.forEach(d => {
      if (chartType === 'candlestick') {
        allPrices.push(d.high, d.low);
      } else {
        allPrices.push(d.price);
      }
      if (showSMA20 && d.sma20) allPrices.push(d.sma20);
      if (showSMA50 && d.sma50) allPrices.push(d.sma50);
      if (showSMA200 && d.sma200) allPrices.push(d.sma200);
      if (showEMA20 && d.ema20) allPrices.push(d.ema20);
      if (showEMA50 && d.ema50) allPrices.push(d.ema50);
    });
    
    const min = Math.min(...allPrices);
    const max = Math.max(...allPrices);
    const padding = (max - min) * 0.05;
    return { min: min - padding, max: max + padding };
  }, [chartData, chartType, showSMA20, showSMA50, showSMA200, showEMA20, showEMA50]);

  const formatCurrency = (value: number) => {
    return `$${value.toFixed(2)}`;
  };

  const formatPercent = (value: number) => {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}%`;
  };

  const CustomPriceTooltip = ({ active, payload }: any) => {
    if (!active || !payload || !payload.length) return null;
    const data = payload[0].payload as ChartDataPoint;

    return (
      <div className="bg-[#1a1a2e] border border-white/20 rounded-lg p-3 shadow-xl">
        <p className="text-[--text] font-medium mb-1">{data.date}</p>
        <p className="text-[--muted] text-sm">
          O: {formatCurrency(data.open)} H: {formatCurrency(data.high)}
        </p>
        <p className="text-[--muted] text-sm">
          L: {formatCurrency(data.low)} C: {formatCurrency(data.close)}
        </p>
        {showSMA20 && data.sma20 && (
          <p className="text-blue-400 text-sm">SMA20: {formatCurrency(data.sma20)}</p>
        )}
        {showSMA50 && data.sma50 && (
          <p className="text-orange-400 text-sm">SMA50: {formatCurrency(data.sma50)}</p>
        )}
        {showSMA200 && data.sma200 && (
          <p className="text-purple-400 text-sm">SMA200: {formatCurrency(data.sma200)}</p>
        )}
        {showEMA20 && data.ema20 && (
          <p className="text-teal-400 text-sm">EMA20: {formatCurrency(data.ema20)}</p>
        )}
        {showEMA50 && data.ema50 && (
          <p className="text-pink-400 text-sm">EMA50: {formatCurrency(data.ema50)}</p>
        )}
        {data.hasEvent && (
          <div className="mt-2 pt-2 border-t border-white/10">
            <p className="text-[--primary] text-sm font-medium">{data.eventTitle}</p>
            <p className="text-[--muted] text-xs">{data.eventType?.replace(/_/g, ' ')}</p>
            {data.projectedPctChange != null && (
              <p className={`text-sm mt-1 ${data.projectedPctChange >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                Projected: {formatPercent(data.projectedPctChange)}
              </p>
            )}
            {data.bearishSignal && (
              <div className="mt-2 pt-2 border-t border-red-500/30 bg-red-900/20 -mx-3 -mb-3 px-3 pb-3 rounded-b-lg">
                <div className="flex items-center gap-1 text-red-400 text-xs font-medium">
                  <span className="text-yellow-400">⚠</span>
                  Bearish Signal
                  {data.bearishConfidence && (
                    <span className="text-red-300">({Math.round((data.bearishConfidence ?? 0) * 100)}% confidence)</span>
                  )}
                </div>
                {data.bearishRationale && (
                  <p className="text-red-300/80 text-xs mt-1 line-clamp-2">{data.bearishRationale}</p>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  const CustomRSITooltip = ({ active, payload }: any) => {
    if (!active || !payload || !payload.length) return null;
    const data = payload[0].payload as RSIDataPoint;

    return (
      <div className="bg-[#1a1a2e] border border-white/20 rounded-lg p-3 shadow-xl">
        <p className="text-[--text] font-medium mb-1">{data.date}</p>
        <p className="text-purple-400 text-sm">RSI: {data.rsi?.toFixed(2) ?? 'N/A'}</p>
        {data.hasEvent && (
          <span className="inline-block mt-1 px-2 py-0.5 bg-[--primary-soft] text-[--primary] text-xs rounded">
            Event Day
          </span>
        )}
      </div>
    );
  };

  const CustomMACDTooltip = ({ active, payload }: any) => {
    if (!active || !payload || !payload.length) return null;
    const data = payload[0].payload as MACDDataPoint;

    return (
      <div className="bg-[#1a1a2e] border border-white/20 rounded-lg p-3 shadow-xl">
        <p className="text-[--text] font-medium mb-1">{data.date}</p>
        <p className="text-blue-400 text-sm">MACD: {data.macd?.toFixed(4) ?? 'N/A'}</p>
        <p className="text-orange-400 text-sm">Signal: {data.signal?.toFixed(4) ?? 'N/A'}</p>
        <p className={`text-sm ${(data.histogram ?? 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
          Histogram: {data.histogram?.toFixed(4) ?? 'N/A'}
        </p>
        {data.hasEvent && (
          <span className="inline-block mt-1 px-2 py-0.5 bg-[--primary-soft] text-[--primary] text-xs rounded">
            Event Day
          </span>
        )}
      </div>
    );
  };

  const EventMarkerDot = (props: any) => {
    const { cx, cy, payload } = props;
    if (!payload?.hasEvent) return null;

    const color = payload.direction === 'positive' ? '#10b981' :
                  payload.direction === 'negative' ? '#ef4444' : '#6b7280';

    return (
      <g>
        <circle cx={cx} cy={cy} r={8} fill={color} fillOpacity={0.3} />
        <circle cx={cx} cy={cy} r={5} fill={color} stroke="white" strokeWidth={1} />
        {payload.direction === 'positive' && (
          <polygon points={`${cx},${cy-3} ${cx-2},${cy+1} ${cx+2},${cy+1}`} fill="white" />
        )}
        {payload.direction === 'negative' && (
          <polygon points={`${cx},${cy+3} ${cx-2},${cy-1} ${cx+2},${cy-1}`} fill="white" />
        )}
      </g>
    );
  };

  const CandlestickShape = (props: any) => {
    const { x, y, width, height, payload } = props;
    if (!payload) return null;

    const { open, high, low, close, hasEvent, direction } = payload;
    const isUp = close >= open;
    const color = isUp ? '#10b981' : '#ef4444';
    
    // Calculate the scale from price range - use the passed y and height for positioning
    // The Bar component passes y (top of bar area) and height based on the data value
    // For candlesticks, we need to manually calculate based on priceRange
    const chartHeight = 320; // Approximate chart area height (400 - margins)
    const chartTop = 20; // Top margin
    
    // Use priceRange from parent scope for scaling
    const domainMin = priceRange.min;
    const domainMax = priceRange.max;
    const domainRange = domainMax - domainMin;
    
    // Convert price to Y coordinate (inverted because Y increases downward)
    const priceToY = (price: number) => {
      const ratio = (domainMax - price) / domainRange;
      return chartTop + ratio * chartHeight;
    };
    
    const highY = priceToY(high);
    const lowY = priceToY(low);
    const openY = priceToY(open);
    const closeY = priceToY(close);
    
    // Body top is the higher price (lower Y in screen coords)
    const bodyTopY = Math.min(openY, closeY);
    const bodyBottomY = Math.max(openY, closeY);
    const bodyHeight = Math.max(bodyBottomY - bodyTopY, 1);
    
    const barWidth = Math.max(width * 0.6, 3);
    const centerX = x + width / 2;

    return (
      <g>
        {/* Upper wick */}
        <line
          x1={centerX}
          y1={highY}
          x2={centerX}
          y2={bodyTopY}
          stroke={color}
          strokeWidth={1}
        />
        {/* Lower wick */}
        <line
          x1={centerX}
          y1={bodyBottomY}
          x2={centerX}
          y2={lowY}
          stroke={color}
          strokeWidth={1}
        />
        {/* Candle body */}
        <rect
          x={centerX - barWidth / 2}
          y={bodyTopY}
          width={barWidth}
          height={bodyHeight}
          fill={color}
          stroke={color}
          strokeWidth={1}
        />
        {hasEvent && (
          <g>
            <circle
              cx={centerX}
              cy={direction === 'positive' ? highY - 12 : lowY + 12}
              r={6}
              fill={direction === 'positive' ? '#10b981' : direction === 'negative' ? '#ef4444' : '#6b7280'}
              stroke="white"
              strokeWidth={1}
            />
          </g>
        )}
      </g>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96 bg-white/5 rounded-lg">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[--primary] mx-auto mb-4"></div>
          <p className="text-[--muted]">Loading chart data...</p>
        </div>
      </div>
    );
  }

  if (chartData.length === 0) {
    return (
      <div className="flex items-center justify-center h-96 bg-white/5 rounded-lg">
        <p className="text-[--muted]">No data available</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="bg-white/5 rounded-lg p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-[--text]">{ticker} Price Chart</h3>
          <div className="flex items-center gap-4">
            {filteredEvents.length > 0 && showEvents && (
              <span className="px-3 py-1 bg-[--primary-soft] text-[--primary] rounded-full text-sm">
                {filteredEvents.length} Event{filteredEvents.length !== 1 ? 's' : ''}
              </span>
            )}
            <span className="text-xs text-[--muted]">
              {chartType === 'candlestick' ? 'Candlestick' : 'Line'} Chart
            </span>
          </div>
        </div>

        <ResponsiveContainer width="100%" height={400}>
          <ComposedChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
            <XAxis
              dataKey="dateShort"
              tick={{ fill: 'rgba(255,255,255,0.7)', fontSize: 11 }}
              axisLine={{ stroke: 'rgba(255,255,255,0.2)' }}
              tickLine={{ stroke: 'rgba(255,255,255,0.2)' }}
              interval="preserveStartEnd"
              minTickGap={50}
            />
            <YAxis
              yAxisId="price"
              type="number"
              domain={[priceRange.min, priceRange.max]}
              tick={{ fill: 'rgba(255,255,255,0.7)', fontSize: 12 }}
              axisLine={{ stroke: 'rgba(255,255,255,0.2)' }}
              tickLine={{ stroke: 'rgba(255,255,255,0.2)' }}
              tickFormatter={formatCurrency}
              allowDataOverflow={true}
            />
            <Tooltip content={<CustomPriceTooltip />} />
            
            {chartType === 'line' ? (
              <Line
                yAxisId="price"
                type="monotone"
                dataKey="price"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={<EventMarkerDot />}
                activeDot={{ r: 6, stroke: '#3b82f6', strokeWidth: 2, fill: 'white' }}
              />
            ) : (
              <Bar
                yAxisId="price"
                dataKey="close"
                shape={<CandlestickShape />}
                isAnimationActive={false}
              />
            )}

            {showSMA20 && (
              <Line
                yAxisId="price"
                type="monotone"
                dataKey="sma20"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={false}
                connectNulls
                isAnimationActive={false}
              />
            )}
            {showSMA50 && (
              <Line
                yAxisId="price"
                type="monotone"
                dataKey="sma50"
                stroke="#f97316"
                strokeWidth={2}
                dot={false}
                connectNulls
                isAnimationActive={false}
              />
            )}
            {showSMA200 && (
              <Line
                yAxisId="price"
                type="monotone"
                dataKey="sma200"
                stroke="#8b5cf6"
                strokeWidth={2}
                dot={false}
                connectNulls
                isAnimationActive={false}
              />
            )}
            {showEMA20 && (
              <Line
                yAxisId="price"
                type="monotone"
                dataKey="ema20"
                stroke="#14b8a6"
                strokeWidth={2}
                dot={false}
                connectNulls
                isAnimationActive={false}
              />
            )}
            {showEMA50 && (
              <Line
                yAxisId="price"
                type="monotone"
                dataKey="ema50"
                stroke="#ec4899"
                strokeWidth={2}
                dot={false}
                connectNulls
                isAnimationActive={false}
              />
            )}
            
            {/* Event vertical bands - rendered behind price data */}
            {showEvents && chartData
              .filter(d => d.hasEvent)
              .map((eventPoint, idx) => {
                // Use darker red for bearish signals
                const bandColor = eventPoint.bearishSignal ? 'rgba(220, 38, 38, 0.35)' :
                                  eventPoint.direction === 'positive' ? 'rgba(16, 185, 129, 0.25)' :
                                  eventPoint.direction === 'negative' ? 'rgba(239, 68, 68, 0.25)' : 
                                  'rgba(107, 114, 128, 0.25)';
                return (
                  <ReferenceLine
                    key={`event-line-${idx}`}
                    yAxisId="price"
                    x={eventPoint.dateShort}
                    stroke={bandColor}
                    strokeWidth={20}
                    strokeOpacity={1}
                  />
                );
              })}
            
            {/* Event marker dots on the price line */}
            {showEvents && chartType === 'candlestick' && (
              <Scatter
                yAxisId="price"
                data={chartData.filter(d => d.hasEvent)}
                dataKey="close"
                shape={(props: any) => {
                  const { cx, cy, payload } = props;
                  if (!payload?.hasEvent || cx === undefined || cy === undefined) return null;
                  
                  // Special styling for bearish signals
                  if (payload.bearishSignal) {
                    return (
                      <g>
                        {/* Outer glow for bearish signal */}
                        <circle cx={cx} cy={cy} r={12} fill="#dc2626" fillOpacity={0.2} />
                        {/* Inner filled circle */}
                        <circle cx={cx} cy={cy} r={7} fill="#dc2626" stroke="#b91c1c" strokeWidth={2} />
                        {/* Downward triangle to indicate bearish */}
                        <polygon 
                          points={`${cx},${cy+4} ${cx-4},${cy-2} ${cx+4},${cy-2}`} 
                          fill="white" 
                        />
                        {/* Small warning indicator */}
                        <circle cx={cx+8} cy={cy-8} r={4} fill="#fbbf24" stroke="#f59e0b" strokeWidth={1} />
                        <text x={cx+8} y={cy-5} fontSize={6} fill="#000" textAnchor="middle" fontWeight="bold">!</text>
                      </g>
                    );
                  }
                  
                  const color = payload.direction === 'positive' ? '#10b981' :
                                payload.direction === 'negative' ? '#ef4444' : '#6b7280';
                  
                  return (
                    <g>
                      <circle cx={cx} cy={cy} r={10} fill={color} fillOpacity={0.3} />
                      <circle cx={cx} cy={cy} r={6} fill={color} stroke="white" strokeWidth={2} />
                      {/* Direction indicators */}
                      {payload.direction === 'positive' && (
                        <polygon points={`${cx},${cy-3} ${cx-2},${cy+1} ${cx+2},${cy+1}`} fill="white" />
                      )}
                      {payload.direction === 'negative' && (
                        <polygon points={`${cx},${cy+3} ${cx-2},${cy-1} ${cx+2},${cy-1}`} fill="white" />
                      )}
                    </g>
                  );
                }}
                isAnimationActive={false}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {showRSI && rsiChartData.length > 0 && (() => {
        const rsiDomain = calculateRSIDomain(rsiChartData);
        const rsiTicks = [rsiDomain[0], 30, 50, 70, rsiDomain[1]].filter(
          (v, i, arr) => v >= rsiDomain[0] && v <= rsiDomain[1] && arr.indexOf(v) === i
        ).sort((a, b) => a - b);
        
        return (
          <div className="bg-white/5 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-4">
              <Activity className="h-4 w-4 text-purple-400" />
              <h3 className="text-sm font-semibold text-[--text]">RSI (14)</h3>
              <span className="text-xs text-[--muted]">Overbought {'>'} 70 | Oversold {'<'} 30</span>
            </div>

            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={rsiChartData} margin={{ top: 15, right: 30, left: 20, bottom: 10 }}>
                <defs>
                  <linearGradient id="rsiGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                <XAxis
                  dataKey="date"
                  tick={{ fill: 'rgba(255,255,255,0.7)', fontSize: 10 }}
                  axisLine={{ stroke: 'rgba(255,255,255,0.2)' }}
                  tickLine={false}
                  interval="preserveStartEnd"
                  minTickGap={50}
                />
                <YAxis
                  type="number"
                  domain={rsiDomain}
                  ticks={rsiTicks}
                  tick={{ fill: 'rgba(255,255,255,0.7)', fontSize: 10 }}
                  axisLine={{ stroke: 'rgba(255,255,255,0.2)' }}
                  tickLine={false}
                  allowDataOverflow={true}
                  dataKey="rsi"
                />
                <Tooltip content={<CustomRSITooltip />} />
                {rsiDomain[1] >= 70 && (
                  <ReferenceLine y={70} stroke="#ef4444" strokeDasharray="3 3" strokeOpacity={0.7} label={{ value: '70', fill: '#ef4444', fontSize: 10, position: 'right' }} />
                )}
                {rsiDomain[0] <= 30 && (
                  <ReferenceLine y={30} stroke="#10b981" strokeDasharray="3 3" strokeOpacity={0.7} label={{ value: '30', fill: '#10b981', fontSize: 10, position: 'right' }} />
                )}
                <ReferenceLine y={50} stroke="rgba(255,255,255,0.3)" strokeDasharray="3 3" />
                <Line
                  type="monotone"
                  dataKey="rsi"
                  stroke="#8b5cf6"
                  strokeWidth={2.5}
                  fill="url(#rsiGradient)"
                  connectNulls
                  dot={(props: any) => {
                    if (!props.payload?.hasEvent) return <g key={props.key} />;
                    return (
                      <circle
                        key={props.key}
                        cx={props.cx}
                        cy={props.cy}
                        r={5}
                        fill="#8b5cf6"
                        stroke="white"
                        strokeWidth={2}
                      />
                    );
                  }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        );
      })()}

      {showMACD && macdChartData.length > 0 && (() => {
        const validMacd = macdChartData.filter(d => d.macd !== null).map(d => d.macd as number);
        const validSignal = macdChartData.filter(d => d.signal !== null).map(d => d.signal as number);
        const validHist = macdChartData.filter(d => d.histogram !== null).map(d => d.histogram as number);
        const allValues = [...validMacd, ...validSignal, ...validHist];
        
        let macdDomain: [number, number] = [-5, 5];
        if (allValues.length > 0) {
          const min = Math.min(...allValues);
          const max = Math.max(...allValues);
          const range = max - min;
          // Use 20% padding to fill the chart better
          const padding = Math.max(range * 0.2, 0.5);
          macdDomain = [min - padding, max + padding];
        }
        
        return (
          <div className="bg-white/5 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-4">
              <BarChart3 className="h-4 w-4 text-blue-400" />
              <h3 className="text-sm font-semibold text-[--text]">MACD (12, 26, 9)</h3>
              <div className="flex items-center gap-3 ml-4 text-xs">
                <span className="flex items-center gap-1">
                  <span className="w-3 h-0.5 bg-[#2962FF]"></span>
                  <span className="text-[--muted]">MACD</span>
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-3 h-0.5 bg-[#FF6D00]"></span>
                  <span className="text-[--muted]">Signal</span>
                </span>
              </div>
            </div>

            <ResponsiveContainer width="100%" height={200}>
              <ComposedChart data={macdChartData} margin={{ top: 15, right: 30, left: 20, bottom: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                <XAxis
                  dataKey="date"
                  tick={{ fill: 'rgba(255,255,255,0.7)', fontSize: 10 }}
                  axisLine={{ stroke: 'rgba(255,255,255,0.2)' }}
                  tickLine={false}
                  interval="preserveStartEnd"
                  minTickGap={50}
                />
                <YAxis
                  type="number"
                  domain={macdDomain}
                  tick={{ fill: 'rgba(255,255,255,0.7)', fontSize: 10 }}
                  axisLine={{ stroke: 'rgba(255,255,255,0.2)' }}
                  tickLine={false}
                  tickFormatter={(value) => value.toFixed(1)}
                  allowDataOverflow={true}
                />
                <Tooltip content={<CustomMACDTooltip />} />
                <ReferenceLine y={0} stroke="rgba(255,255,255,0.5)" strokeWidth={1} />
                <Bar
                  dataKey="histogram"
                  radius={[2, 2, 0, 0]}
                  barSize={8}
                  fillOpacity={0.8}
                >
                  {macdChartData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={entry.histogramColor}
                    />
                  ))}
                </Bar>
                <Line
                  type="monotone"
                  dataKey="macd"
                  stroke="#2962FF"
                  strokeWidth={2.5}
                  dot={false}
                  connectNulls
                />
                <Line
                  type="monotone"
                  dataKey="signal"
                  stroke="#FF6D00"
                  strokeWidth={2.5}
                  dot={false}
                  connectNulls
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        );
      })()}

      {allEventsForTable.length > 0 && (
        <div className="bg-white/5 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-4">
            <Calendar className="h-4 w-4 text-[--primary]" />
            <h3 className="text-sm font-semibold text-[--text]">Events Timeline</h3>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-xs text-[--muted] border-b border-white/10">
                  <th className="pb-3 pr-4">Date</th>
                  <th className="pb-3 pr-4">Event</th>
                  <th className="pb-3 pr-4 text-center">Impact</th>
                  <th className="pb-3 pr-4 text-center">Confidence</th>
                  <th className="pb-3 pr-4 text-right">Price at Event</th>
                  <th className="pb-3 pr-4 text-right">Projected Move</th>
                  <th className="pb-3 text-right">Projected Price</th>
                </tr>
              </thead>
              <tbody>
                {allEventsForTable.map((event) => {
                  // Find the closest price point by time (handles timezone/granularity differences)
                  const closestPricePoint = chartData.reduce((closest, point) => {
                    if (!closest) return point;
                    const closestDiff = Math.abs(closest.time - event.time);
                    const currentDiff = Math.abs(point.time - event.time);
                    return currentDiff < closestDiff ? point : closest;
                  }, null as ChartDataPoint | null);
                  const priceAtEvent = closestPricePoint?.close ?? 0;
                  
                  let projectedMove: number | null = null;
                  let projectedPrice: number | null = null;
                  
                  if (event.impact_p_move != null) {
                    const pctMove = event.impact_p_move * 100;
                    const isUpward = (event.impact_p_up ?? 0) >= (event.impact_p_down ?? 0);
                    projectedMove = isUpward ? pctMove : -pctMove;
                    projectedPrice = priceAtEvent * (1 + projectedMove / 100);
                  }

                  const eventDate = new Date(event.time * 1000).toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric',
                  });

                  const impactScore = modelVersion === 'v1.0' 
                    ? event.impact_score 
                    : (event.ml_adjusted_score ?? event.impact_score);

                  const confidence = modelVersion === 'v1.0'
                    ? event.confidence
                    : (event.ml_confidence ?? event.confidence);

                  return (
                    <tr key={event.event_id} className="border-b border-white/5 hover:bg-white/5">
                      <td className="py-3 pr-4 text-sm text-[--muted]">{eventDate}</td>
                      <td className="py-3 pr-4">
                        <div className="flex items-center gap-2">
                          {event.direction === 'positive' ? (
                            <TrendingUp className="h-4 w-4 text-green-400 flex-shrink-0" />
                          ) : event.direction === 'negative' ? (
                            <TrendingDown className="h-4 w-4 text-red-400 flex-shrink-0" />
                          ) : (
                            <Minus className="h-4 w-4 text-gray-400 flex-shrink-0" />
                          )}
                          <div className="min-w-0">
                            <p className="text-sm text-[--text] truncate max-w-[250px]">{event.title}</p>
                            <p className="text-xs text-[--muted]">{event.event_type?.replace(/_/g, ' ')}</p>
                          </div>
                        </div>
                      </td>
                      <td className="py-3 pr-4 text-center">
                        <span className={`inline-flex items-center justify-center w-10 h-6 rounded text-sm font-medium ${
                          (impactScore ?? 0) >= 75 ? 'bg-green-500/20 text-green-400' :
                          (impactScore ?? 0) >= 50 ? 'bg-yellow-500/20 text-yellow-400' :
                          'bg-gray-500/20 text-gray-400'
                        }`}>
                          {impactScore ?? '-'}
                        </span>
                      </td>
                      <td className="py-3 pr-4 text-center">
                        {confidence != null ? (
                          <span className="text-sm text-[--muted]">
                            {(confidence * 100).toFixed(0)}%
                          </span>
                        ) : (
                          <span className="text-sm text-[--muted]">-</span>
                        )}
                      </td>
                      <td className="py-3 pr-4 text-right text-sm text-[--text]">
                        {formatCurrency(priceAtEvent)}
                      </td>
                      <td className="py-3 pr-4 text-right">
                        {projectedMove != null ? (
                          <span className={`text-sm font-medium ${
                            projectedMove >= 0 ? 'text-green-400' : 'text-red-400'
                          }`}>
                            {formatPercent(projectedMove)}
                          </span>
                        ) : (
                          <span className="text-sm text-[--muted]">-</span>
                        )}
                      </td>
                      <td className="py-3 text-right">
                        {projectedPrice != null ? (
                          <span className={`text-sm font-medium ${
                            projectedMove && projectedMove >= 0 ? 'text-green-400' : 'text-red-400'
                          }`}>
                            {formatCurrency(projectedPrice)}
                          </span>
                        ) : (
                          <span className="text-sm text-[--muted]">-</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
