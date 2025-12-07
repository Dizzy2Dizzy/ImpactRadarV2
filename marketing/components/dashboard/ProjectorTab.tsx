'use client';

import { useState, useEffect } from 'react';
import { Search, TrendingUp, TrendingDown, Calendar } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ModelVersionFilter } from './ModelVersionFilter';
import { DisplayVersion } from './ImpactScoreBadge';
import { ProjectorEventChart } from './ProjectorEventChart';

interface OHLCVDataPoint {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface EventMarker {
  time: number;
  position: 'aboveBar' | 'belowBar';
  color: string;
  shape: 'circle' | 'square' | 'arrowUp' | 'arrowDown';
  text: string;
  event_id: number;
  title?: string;
  event_type?: string;
  impact_score?: number;
  direction?: string;
  confidence?: number;
  model_source?: 'family-specific' | 'global' | 'deterministic';
  ml_adjusted_score?: number | null;
  ml_confidence?: number | null;
  impact_p_move?: number | null;
  impact_p_up?: number | null;
  impact_p_down?: number | null;
}

interface IndicatorData {
  time: number;
  value: number | null;
}

interface ProjectorData {
  ticker: string;
  interval: string;
  ohlcv: OHLCVDataPoint[];
  events: EventMarker[];
  indicators: {
    sma_20?: IndicatorData[];
    sma_50?: IndicatorData[];
    sma_200?: IndicatorData[];
    ema_20?: IndicatorData[];
    ema_50?: IndicatorData[];
  };
  rsi?: IndicatorData[];
  macd?: {
    macd: IndicatorData[];
    signal: IndicatorData[];
    histogram: IndicatorData[];
  };
}

export function ProjectorTab() {
  const [ticker, setTicker] = useState('AAPL');
  const [loadedTicker, setLoadedTicker] = useState('AAPL');
  const [timeframe, setTimeframe] = useState('1d');
  const [period, setPeriod] = useState('3mo');
  const [chartType, setChartType] = useState<'candlestick' | 'line'>('candlestick');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentPrice, setCurrentPrice] = useState(0);
  const [priceChange, setPriceChange] = useState(0);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  // Indicator toggles
  const [showSMA20, setShowSMA20] = useState(true);
  const [showSMA50, setShowSMA50] = useState(true);
  const [showSMA200, setShowSMA200] = useState(false);
  const [showEMA20, setShowEMA20] = useState(false);
  const [showEMA50, setShowEMA50] = useState(false);
  const [showRSI, setShowRSI] = useState(true);
  const [showMACD, setShowMACD] = useState(true);
  const [showEvents, setShowEvents] = useState(true);
  const [modelVersion, setModelVersion] = useState<DisplayVersion>('v1.5');
  
  // Chart data state
  const [cachedEvents, setCachedEvents] = useState<EventMarker[]>([]);
  const [cachedOHLCV, setCachedOHLCV] = useState<OHLCVDataPoint[]>([]);
  const [indicators, setIndicators] = useState<ProjectorData['indicators']>({});
  const [rsiData, setRsiData] = useState<IndicatorData[]>([]);
  const [macdData, setMacdData] = useState<ProjectorData['macd'] | null>(null);

  const timeframes = [
    { label: '1m', value: '1m', period: '1d' },
    { label: '5m', value: '5m', period: '5d' },
    { label: '15m', value: '15m', period: '5d' },
    { label: '30m', value: '30m', period: '1mo' },
    { label: '1h', value: '1h', period: '1mo' },
    { label: '1d', value: '1d', period: '3mo' },
    { label: '1w', value: '1wk', period: '1y' },
  ];

  const periods = [
    { label: '1D', value: '1d' },
    { label: '5D', value: '5d' },
    { label: '1M', value: '1mo' },
    { label: '3M', value: '3mo' },
    { label: '6M', value: '6mo' },
    { label: '1Y', value: '1y' },
  ];

  // Fetch chart data - no dependency on chartReady
  useEffect(() => {
    if (!loadedTicker || !timeframe || !period) return;

    const fetchChartData = async () => {
      setLoading(true);
      setError(null);
      setCachedEvents([]);
      setCachedOHLCV([]);
      setIndicators({});
      setRsiData([]);
      setMacdData(null);

      try {
        const response = await fetch(
          `/api/proxy/projector/full?ticker=${loadedTicker.toUpperCase()}&interval=${timeframe}&period=${period}`
        );

        if (!response.ok) {
          if (response.status === 403) {
            throw new Error('Access not available, please upgrade plan');
          }
          const errorData = await response.json().catch(() => ({}));
          const errorMessage = errorData.detail || `Failed to load chart data (${response.status})`;
          throw new Error(errorMessage);
        }

        const data: ProjectorData = await response.json();

        if (!data.ohlcv || data.ohlcv.length === 0) {
          setError('No data available for this ticker');
          return;
        }

        // Update price display
        const lastCandle = data.ohlcv[data.ohlcv.length - 1];
        if (lastCandle) {
          setCurrentPrice(lastCandle.close);
          if (data.ohlcv.length > 1) {
            const prevClose = data.ohlcv[data.ohlcv.length - 2].close;
            setPriceChange(((lastCandle.close - prevClose) / prevClose) * 100);
          }
        }

        // Cache all data
        setCachedOHLCV(data.ohlcv);
        
        if (data.events && data.events.length > 0) {
          setCachedEvents(data.events);
        }

        if (data.indicators) {
          setIndicators(data.indicators);
        }

        if (data.rsi) {
          setRsiData(data.rsi);
        }

        if (data.macd) {
          setMacdData(data.macd);
        }

      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load chart data');
      } finally {
        setLoading(false);
      }
    };

    fetchChartData();
  }, [loadedTicker, timeframe, period, refreshTrigger]);

  const handleTimeframeChange = (tf: string, per: string) => {
    setTimeframe(tf);
    setPeriod(per);
  };

  const handleTickerSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (ticker.trim()) {
      setLoadedTicker(ticker.trim().toUpperCase());
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-2xl font-bold text-[--text]">Projector</h2>
          <p className="text-[--muted] mt-1">Advanced trading charts with Impact Radar event overlays</p>
        </div>
        <ModelVersionFilter value={modelVersion} onChange={setModelVersion} />
      </div>

      {/* Controls */}
      <div className="space-y-4">
        {/* Ticker Search & Price Display */}
        <div className="flex items-center gap-4 flex-wrap">
          <form onSubmit={handleTickerSearch} className="flex items-center gap-2">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-[--muted]" />
              <input
                type="text"
                placeholder="Search ticker..."
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                className="pl-10 pr-4 py-2 bg-[--surface-muted] border border-[--border] rounded text-[--text] focus:outline-none focus:border-[--primary] min-w-[200px]"
              />
            </div>
            <Button type="submit" size="sm">
              Load
            </Button>
          </form>

          {!loading && currentPrice > 0 && (
            <div className="flex items-center gap-3 ml-auto">
              <span className="text-2xl font-bold text-[--text]">
                ${currentPrice.toFixed(2)}
              </span>
              <div className="flex items-center gap-1">
                {priceChange >= 0 ? (
                  <TrendingUp className="h-5 w-5 text-[--success]" />
                ) : (
                  <TrendingDown className="h-5 w-5 text-[--error]" />
                )}
                <span
                  className={`text-lg font-semibold ${
                    priceChange >= 0 ? 'text-[--success]' : 'text-[--error]'
                  }`}
                >
                  {priceChange >= 0 ? '+' : ''}
                  {priceChange.toFixed(2)}%
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Timeframe Selector */}
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4 text-[--muted]" />
            <span className="text-sm text-[--muted]">Interval:</span>
            <div className="flex gap-1">
              {timeframes.map((tf) => (
                <button
                  key={tf.value}
                  onClick={() => handleTimeframeChange(tf.value, tf.period)}
                  className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                    timeframe === tf.value
                      ? 'bg-[--primary] text-[--text-on-primary]'
                      : 'bg-[--surface-muted] text-[--muted] hover:bg-[--surface-hover]'
                  }`}
                >
                  {tf.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-sm text-[--muted]">Period:</span>
            <div className="flex gap-1">
              {periods.map((p) => (
                <button
                  key={p.value}
                  onClick={() => setPeriod(p.value)}
                  className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                    period === p.value
                      ? 'bg-[--primary] text-[--text-on-primary]'
                      : 'bg-[--surface-muted] text-[--muted] hover:bg-[--surface-hover]'
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Chart Type & Indicators */}
        <div className="flex items-center gap-6 flex-wrap">
          <div className="flex items-center gap-2">
            <span className="text-sm text-[--muted]">Chart Type:</span>
            <button
              onClick={() => setChartType('candlestick')}
              className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                chartType === 'candlestick'
                  ? 'bg-[--primary] text-[--text-on-primary]'
                  : 'bg-[--surface-muted] text-[--muted] hover:bg-[--surface-hover]'
              }`}
            >
              Candlestick
            </button>
            <button
              onClick={() => setChartType('line')}
              className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                chartType === 'line'
                  ? 'bg-[--primary] text-[--text-on-primary]'
                  : 'bg-[--surface-muted] text-[--muted] hover:bg-[--surface-hover]'
              }`}
            >
              Line
            </button>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-sm text-[--muted]">Indicators:</span>
            <label className="flex items-center gap-1 cursor-pointer">
              <input
                type="checkbox"
                checked={showSMA20}
                onChange={(e) => setShowSMA20(e.target.checked)}
                className="w-4 h-4 rounded border-[--border] bg-[--surface-muted] text-[--primary]"
              />
              <span className="text-sm text-[--text]">SMA 20</span>
            </label>
            <label className="flex items-center gap-1 cursor-pointer">
              <input
                type="checkbox"
                checked={showSMA50}
                onChange={(e) => setShowSMA50(e.target.checked)}
                className="w-4 h-4 rounded border-[--border] bg-[--surface-muted] text-[--warning]"
              />
              <span className="text-sm text-[--text]">SMA 50</span>
            </label>
            <label className="flex items-center gap-1 cursor-pointer">
              <input
                type="checkbox"
                checked={showSMA200}
                onChange={(e) => setShowSMA200(e.target.checked)}
                className="w-4 h-4 rounded border-[--border] bg-[--surface-muted] text-[--accent]"
              />
              <span className="text-sm text-[--text]">SMA 200</span>
            </label>
            <label className="flex items-center gap-1 cursor-pointer">
              <input
                type="checkbox"
                checked={showEMA20}
                onChange={(e) => setShowEMA20(e.target.checked)}
                className="w-4 h-4 rounded border-[--border] bg-[--surface-muted] text-[--accent]"
              />
              <span className="text-sm text-[--text]">EMA 20</span>
            </label>
            <label className="flex items-center gap-1 cursor-pointer">
              <input
                type="checkbox"
                checked={showEMA50}
                onChange={(e) => setShowEMA50(e.target.checked)}
                className="w-4 h-4 rounded border-[--border] bg-[--surface-muted] text-[--primary]"
              />
              <span className="text-sm text-[--text]">EMA 50</span>
            </label>
          </div>

          <div className="flex items-center gap-3">
            <label className="flex items-center gap-1 cursor-pointer">
              <input
                type="checkbox"
                checked={showRSI}
                onChange={(e) => setShowRSI(e.target.checked)}
                className="w-4 h-4 rounded border-[--border] bg-[--surface-muted] text-[--accent]"
              />
              <span className="text-sm text-[--text]">RSI</span>
            </label>
            <label className="flex items-center gap-1 cursor-pointer">
              <input
                type="checkbox"
                checked={showMACD}
                onChange={(e) => setShowMACD(e.target.checked)}
                className="w-4 h-4 rounded border-[--border] bg-[--surface-muted] text-[--primary]"
              />
              <span className="text-sm text-[--text]">MACD</span>
            </label>
            <label className="flex items-center gap-1 cursor-pointer">
              <input
                type="checkbox"
                checked={showEvents}
                onChange={(e) => setShowEvents(e.target.checked)}
                className="w-4 h-4 rounded border-[--border] bg-[--surface-muted] text-[--success]"
              />
              <span className="text-sm text-[--text]">Event Markers</span>
            </label>
          </div>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center h-96 bg-[--surface-muted] rounded-lg">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[--primary] mx-auto mb-4"></div>
            <p className="text-[--muted]">Loading chart data...</p>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="bg-[--error-light] border border-[--border] rounded-lg p-6">
          <p className="text-[--error] font-semibold mb-2">Failed to load chart</p>
          <p className="text-sm text-[--muted]">{error}</p>
          <Button onClick={() => setRefreshTrigger(prev => prev + 1)} className="mt-4">
            Retry
          </Button>
        </div>
      )}

      {/* Main Chart */}
      {!loading && !error && (
        <ProjectorEventChart
          ticker={loadedTicker}
          ohlcvData={cachedOHLCV}
          events={cachedEvents}
          indicators={indicators}
          rsiData={rsiData}
          macdData={macdData ?? undefined}
          chartType={chartType}
          showSMA20={showSMA20}
          showSMA50={showSMA50}
          showSMA200={showSMA200}
          showEMA20={showEMA20}
          showEMA50={showEMA50}
          showRSI={showRSI}
          showMACD={showMACD}
          showEvents={showEvents}
          modelVersion={modelVersion}
          loading={loading}
        />
      )}

      {/* Info Panel */}
      <div className="bg-[--surface-muted] rounded-lg p-4">
        <h4 className="text-sm font-semibold text-[--text] mb-3">About Projector</h4>
        <p className="text-sm text-[--muted] leading-relaxed">
          Projector combines professional-grade charting with Impact Radar&apos;s event intelligence.
          Toggle indicators to analyze price movements alongside corporate events like earnings, FDA
          approvals, product launches, and more. Event markers appear directly on the chart, allowing
          you to visualize the impact of news on stock performance.
        </p>
      </div>
    </div>
  );
}
