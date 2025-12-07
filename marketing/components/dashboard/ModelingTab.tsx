'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { ExternalLink, Box, Activity, LineChart, FlaskConical, Info, Play, Loader2, RefreshCw, TrendingUp, TrendingDown } from 'lucide-react';

interface TopologyFeatures {
  betti0_count: number;
  betti1_count: number;
  max_lifetime_h0: number;
  max_lifetime_h1: number;
  mean_lifetime_h0: number;
  mean_lifetime_h1: number;
  total_persistence_h0: number;
  total_persistence_h1: number;
  persistence_entropy: number;
  betti_curve_h0_mean: number;
  betti_curve_h1_mean: number;
  topological_complexity: number;
}

interface TopologyPreviewResponse {
  ticker: string;
  analysis_date: string;
  lookback_days: number;
  embedding_dim: number;
  delay: number;
  embedding_points: number[][];
  prices: number[];
  dates: string[];
  returns: number[];
  persistence_diagram_h0: number[][];
  persistence_diagram_h1: number[][];
  betti_curve_scales: number[];
  betti_curve_h0: number[];
  betti_curve_h1: number[];
  features: TopologyFeatures;
  has_data: boolean;
  error_message?: string;
}

interface BacktestTrade {
  entry_date: string;
  exit_date: string;
  entry_price: number;
  exit_price: number;
  return_pct: number;
  profit_loss: number;
  holding_days: number;
  entry_reason: string;
  exit_reason: string;
}

interface BacktestResponse {
  ticker: string;
  start_date: string;
  end_date: string;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_return_pct: number;
  sharpe_ratio: number | null;
  max_drawdown_pct: number;
  avg_holding_days: number;
  trades: BacktestTrade[];
  equity_curve: { date: string; equity: number; in_position: boolean }[];
  initial_capital: number;
  final_capital: number;
}

export function ModelingTab() {
  const [selectedSection, setSelectedSection] = useState<'shape' | 'topology' | 'strategy'>('shape');
  const [ticker, setTicker] = useState('AAPL');
  const [lookbackDays, setLookbackDays] = useState(60);
  const [embeddingDim, setEmbeddingDim] = useState(3);
  const [delay, setDelay] = useState(2);
  const [loading, setLoading] = useState(false);
  const [topologyData, setTopologyData] = useState<TopologyPreviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  const [backtestLoading, setBacktestLoading] = useState(false);
  const [backtestData, setBacktestData] = useState<BacktestResponse | null>(null);
  const [backtestError, setBacktestError] = useState<string | null>(null);
  const [entryBetti1Threshold, setEntryBetti1Threshold] = useState(3);
  const [entryEntropyThreshold, setEntryEntropyThreshold] = useState(0.5);
  const [stopLossPct, setStopLossPct] = useState(5);
  const [takeProfitPct, setTakeProfitPct] = useState(10);
  const [maxHoldingDays, setMaxHoldingDays] = useState(10);
  
  const shapeChartRef = useRef<HTMLDivElement>(null);
  const persistenceChartRef = useRef<HTMLDivElement>(null);
  const bettiChartRef = useRef<HTMLDivElement>(null);
  const equityChartRef = useRef<HTMLDivElement>(null);

  const sections = [
    {
      id: 'shape' as const,
      title: 'Shape Explorer',
      description: 'Visualize 3D Takens delay embeddings to analyze attractor geometry',
      icon: Box,
      color: '#3b82f6',
    },
    {
      id: 'topology' as const,
      title: 'Topology Analyzer',
      description: 'Compute persistence diagrams and Betti curves using ripser',
      icon: Activity,
      color: '#a855f7',
    },
    {
      id: 'strategy' as const,
      title: 'Strategy Lab',
      description: 'Backtest topology-based trading strategies',
      icon: LineChart,
      color: '#22c55e',
    },
  ];

  const fetchTopologyData = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const endDate = new Date().toISOString().split('T')[0];
      const response = await fetch('/api/proxy/modeling/topology/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ticker: ticker.toUpperCase(),
          end_date: endDate,
          lookback_days: lookbackDays,
          embedding_dim: embeddingDim,
          delay: delay
        })
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Request failed: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.error_message) {
        setError(data.error_message);
        setTopologyData(null);
      } else {
        setTopologyData(data);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to fetch topology data');
      setTopologyData(null);
    } finally {
      setLoading(false);
    }
  }, [ticker, lookbackDays, embeddingDim, delay]);

  const runBacktest = useCallback(async () => {
    setBacktestLoading(true);
    setBacktestError(null);
    
    try {
      const endDate = new Date().toISOString().split('T')[0];
      const startDate = new Date(Date.now() - 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
      
      const response = await fetch('/api/proxy/modeling/backtest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ticker: ticker.toUpperCase(),
          start_date: startDate,
          end_date: endDate,
          embedding_dim: embeddingDim,
          delay: delay,
          lookback_days: lookbackDays,
          entry_conditions: {
            betti1_count: { operator: '>', value: entryBetti1Threshold },
            persistence_entropy: { operator: '>', value: entryEntropyThreshold }
          },
          exit_conditions: {
            stop_loss_pct: stopLossPct,
            take_profit_pct: takeProfitPct
          },
          initial_capital: 10000,
          position_size_pct: 100,
          max_holding_days: maxHoldingDays
        })
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Backtest failed: ${response.status}`);
      }
      
      const data = await response.json();
      setBacktestData(data);
    } catch (err: any) {
      setBacktestError(err.message || 'Backtest failed');
      setBacktestData(null);
    } finally {
      setBacktestLoading(false);
    }
  }, [ticker, embeddingDim, delay, lookbackDays, entryBetti1Threshold, entryEntropyThreshold, stopLossPct, takeProfitPct, maxHoldingDays]);

  useEffect(() => {
    if (typeof window === 'undefined' || !topologyData?.has_data) return;

    const timeoutId = setTimeout(async () => {
      const Plotly = await import('plotly.js-dist-min');

      if (selectedSection === 'shape' && shapeChartRef.current && topologyData.embedding_points.length > 0) {
        const points = topologyData.embedding_points;
        const is3D = points[0]?.length >= 3;

        if (is3D) {
          const trace: Plotly.Data = {
            type: 'scatter3d',
            mode: 'lines+markers',
            x: points.map(p => p[0]),
            y: points.map(p => p[1]),
            z: points.map(p => p[2]),
            marker: {
              size: 3,
              color: points.map((_, i) => i),
              colorscale: 'Viridis',
              opacity: 0.8
            },
            line: {
              color: '#3b82f6',
              width: 1
            }
          };

          const layout: Partial<Plotly.Layout> = {
            title: {
              text: `${topologyData.ticker} - Takens Embedding (m=${embeddingDim}, τ=${delay})`,
              font: { color: '#d1d4dc', size: 16 }
            },
            paper_bgcolor: '#1e222d',
            plot_bgcolor: '#1e222d',
            scene: {
              xaxis: { gridcolor: '#363a45', zerolinecolor: '#363a45', color: '#787b86' },
              yaxis: { gridcolor: '#363a45', zerolinecolor: '#363a45', color: '#787b86' },
              zaxis: { gridcolor: '#363a45', zerolinecolor: '#363a45', color: '#787b86' },
              bgcolor: '#1e222d'
            },
            margin: { l: 0, r: 0, t: 40, b: 0 }
          };

          Plotly.newPlot(shapeChartRef.current, [trace], layout, { responsive: true });
        }
      }

      if (selectedSection === 'topology' && persistenceChartRef.current) {
        const h0 = topologyData.persistence_diagram_h0;
        const h1 = topologyData.persistence_diagram_h1;
        
        const allPoints = [...h0, ...h1];
        const maxVal = allPoints.length > 0 
          ? Math.max(...allPoints.map(p => Math.max(p[0], p[1]))) * 1.1 
          : 1;

        const traces: Plotly.Data[] = [
          {
            type: 'scatter',
            mode: 'markers',
            name: 'H0 (Components)',
            x: h0.map(p => p[0]),
            y: h0.map(p => p[1]),
            marker: { size: 10, color: '#3b82f6', symbol: 'circle' }
          },
          {
            type: 'scatter',
            mode: 'markers',
            name: 'H1 (Loops)',
            x: h1.map(p => p[0]),
            y: h1.map(p => p[1]),
            marker: { size: 10, color: '#a855f7', symbol: 'diamond' }
          },
          {
            type: 'scatter',
            mode: 'lines',
            name: 'Diagonal',
            x: [0, maxVal],
            y: [0, maxVal],
            line: { color: '#787b86', dash: 'dash', width: 1 },
            showlegend: false
          }
        ];

        const layout: Partial<Plotly.Layout> = {
          title: { text: 'Persistence Diagram', font: { color: '#d1d4dc', size: 16 } },
          paper_bgcolor: '#1e222d',
          plot_bgcolor: '#1e222d',
          xaxis: { 
            title: 'Birth', 
            gridcolor: '#363a45', 
            zerolinecolor: '#363a45', 
            color: '#787b86',
            range: [0, maxVal]
          },
          yaxis: { 
            title: 'Death', 
            gridcolor: '#363a45', 
            zerolinecolor: '#363a45', 
            color: '#787b86',
            range: [0, maxVal]
          },
          legend: { font: { color: '#d1d4dc' }, bgcolor: 'transparent' },
          margin: { l: 60, r: 20, t: 40, b: 50 }
        };

        Plotly.newPlot(persistenceChartRef.current, traces, layout, { responsive: true });
      }

      if (selectedSection === 'topology' && bettiChartRef.current && topologyData.betti_curve_scales.length > 0) {
        const traces: Plotly.Data[] = [
          {
            type: 'scatter',
            mode: 'lines',
            name: 'β₀ (Components)',
            x: topologyData.betti_curve_scales,
            y: topologyData.betti_curve_h0,
            line: { color: '#3b82f6', width: 2 }
          },
          {
            type: 'scatter',
            mode: 'lines',
            name: 'β₁ (Loops)',
            x: topologyData.betti_curve_scales,
            y: topologyData.betti_curve_h1,
            line: { color: '#a855f7', width: 2 }
          }
        ];

        const layout: Partial<Plotly.Layout> = {
          title: { text: 'Betti Curves', font: { color: '#d1d4dc', size: 16 } },
          paper_bgcolor: '#1e222d',
          plot_bgcolor: '#1e222d',
          xaxis: { title: 'Scale (ε)', gridcolor: '#363a45', zerolinecolor: '#363a45', color: '#787b86' },
          yaxis: { title: 'Betti Number', gridcolor: '#363a45', zerolinecolor: '#363a45', color: '#787b86' },
          legend: { font: { color: '#d1d4dc' }, bgcolor: 'transparent' },
          margin: { l: 60, r: 20, t: 40, b: 50 }
        };

        Plotly.newPlot(bettiChartRef.current, traces, layout, { responsive: true });
      }
    }, 100);

    return () => clearTimeout(timeoutId);
  }, [topologyData, selectedSection, embeddingDim, delay]);

  useEffect(() => {
    if (typeof window === 'undefined' || !backtestData || selectedSection !== 'strategy') return;
    if (!equityChartRef.current) return;

    const loadPlotly = async () => {
      const Plotly = await import('plotly.js-dist-min');
      
      const trace: Plotly.Data = {
        type: 'scatter',
        mode: 'lines',
        name: 'Equity',
        x: backtestData.equity_curve.map(e => e.date),
        y: backtestData.equity_curve.map(e => e.equity),
        line: { color: '#22c55e', width: 2 },
        fill: 'tozeroy',
        fillcolor: 'rgba(34, 197, 94, 0.1)'
      };

      const layout: Partial<Plotly.Layout> = {
        title: { text: 'Equity Curve', font: { color: '#d1d4dc', size: 16 } },
        paper_bgcolor: '#1e222d',
        plot_bgcolor: '#1e222d',
        xaxis: { gridcolor: '#363a45', zerolinecolor: '#363a45', color: '#787b86' },
        yaxis: { title: 'Portfolio Value ($)', gridcolor: '#363a45', zerolinecolor: '#363a45', color: '#787b86' },
        margin: { l: 60, r: 20, t: 40, b: 50 }
      };

      Plotly.newPlot(equityChartRef.current, [trace], layout, { responsive: true });
    };

    loadPlotly();
  }, [backtestData, selectedSection]);

  return (
    <div className="space-y-6">
      <div className="bg-[--panel] rounded-xl border border-[--border] p-6">
        <div className="flex items-start justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center shadow-lg shadow-purple-500/20">
              <FlaskConical className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-[--text]">Modeling Workspace</h2>
              <p className="text-[--muted] text-sm">Topological Data Analysis for Market Patterns</p>
            </div>
          </div>
        </div>

        <div className="bg-[--surface-muted] rounded-lg border border-[--border-muted] p-4 mb-6">
          <div className="flex items-start gap-3">
            <Info className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-[--muted]">
              <p className="mb-2">
                The Modeling Workspace uses <strong className="text-[--text]">Persistent Homology</strong> to detect 
                topological patterns in stock price data that traditional technical analysis misses.
              </p>
              <ul className="space-y-1 text-xs">
                <li>- <strong>Takens Embedding:</strong> Reconstruct price attractor geometry in higher dimensions</li>
                <li>- <strong>Vietoris-Rips Complex:</strong> Build simplicial complexes to detect loops and voids</li>
                <li>- <strong>Betti Numbers:</strong> Count topological features (β₀=components, β₁=loops)</li>
              </ul>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          {sections.map((section) => {
            const Icon = section.icon;
            const isActive = selectedSection === section.id;
            return (
              <button
                key={section.id}
                onClick={() => setSelectedSection(section.id)}
                className={`p-4 rounded-xl border transition-all text-left ${
                  isActive
                    ? 'bg-[--surface-hover] border-blue-500/50 shadow-lg'
                    : 'bg-[--surface-muted] border-[--border] hover:border-[--border-strong]'
                }`}
              >
                <div className="flex items-center gap-3 mb-2">
                  <div
                    className="w-10 h-10 rounded-lg flex items-center justify-center"
                    style={{ backgroundColor: `${section.color}20` }}
                  >
                    <Icon className="w-5 h-5" style={{ color: section.color }} />
                  </div>
                  <h3 className="font-semibold text-[--text]">{section.title}</h3>
                </div>
                <p className="text-xs text-[--muted]">{section.description}</p>
              </button>
            );
          })}
        </div>

        <div className="bg-[--surface] rounded-xl border border-[--border] p-6">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
            <div>
              <label className="block text-xs text-[--muted] mb-1">Ticker</label>
              <input
                type="text"
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                className="w-full px-3 py-2 bg-[--surface-muted] border border-[--border] rounded-lg text-[--text] text-sm focus:border-blue-500 focus:outline-none"
                placeholder="AAPL"
              />
            </div>
            <div>
              <label className="block text-xs text-[--muted] mb-1">Lookback (days)</label>
              <input
                type="number"
                value={lookbackDays}
                onChange={(e) => setLookbackDays(parseInt(e.target.value) || 30)}
                min={20}
                max={180}
                className="w-full px-3 py-2 bg-[--surface-muted] border border-[--border] rounded-lg text-[--text] text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs text-[--muted] mb-1">Embed Dim (m)</label>
              <input
                type="number"
                value={embeddingDim}
                onChange={(e) => setEmbeddingDim(parseInt(e.target.value) || 3)}
                min={2}
                max={8}
                className="w-full px-3 py-2 bg-[--surface-muted] border border-[--border] rounded-lg text-[--text] text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs text-[--muted] mb-1">Time Delay (τ)</label>
              <input
                type="number"
                value={delay}
                onChange={(e) => setDelay(parseInt(e.target.value) || 2)}
                min={1}
                max={10}
                className="w-full px-3 py-2 bg-[--surface-muted] border border-[--border] rounded-lg text-[--text] text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div className="flex items-end">
              <button
                onClick={fetchTopologyData}
                disabled={loading}
                className="w-full px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-500/50 text-white rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Analyzing...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4" />
                    <span>Analyze</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {error && (
            <div className={`mb-6 p-4 rounded-lg text-sm ${
              error.includes('requires') || error.includes('Upgrade') || error.includes('402')
                ? 'bg-amber-500/10 border border-amber-500/30 text-amber-400'
                : 'bg-red-500/10 border border-red-500/30 text-red-400'
            }`}>
              {error.includes('requires') || error.includes('Upgrade') ? (
                <div className="flex items-center gap-3">
                  <span>{error}</span>
                  <a 
                    href="/pricing" 
                    className="px-3 py-1 bg-amber-500 hover:bg-amber-600 text-black text-xs font-semibold rounded transition-colors"
                  >
                    Upgrade Now
                  </a>
                </div>
              ) : error}
            </div>
          )}

          {selectedSection === 'shape' && (
            <div className="space-y-6">
              <div 
                ref={shapeChartRef} 
                className="w-full h-[500px] bg-[--surface-muted] rounded-lg"
              >
                {!topologyData?.has_data && !loading && (
                  <div className="flex items-center justify-center h-full text-[--muted]">
                    Enter a ticker and click Analyze to visualize the embedding
                  </div>
                )}
              </div>

              {topologyData?.has_data && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-[--surface-muted] rounded-lg p-4">
                    <div className="text-xs text-[--muted] mb-1">Data Points</div>
                    <div className="text-xl font-semibold text-[--text]">
                      {topologyData.embedding_points.length}
                    </div>
                  </div>
                  <div className="bg-[--surface-muted] rounded-lg p-4">
                    <div className="text-xs text-[--muted] mb-1">β₀ Components</div>
                    <div className="text-xl font-semibold text-blue-400">
                      {topologyData.features.betti0_count}
                    </div>
                  </div>
                  <div className="bg-[--surface-muted] rounded-lg p-4">
                    <div className="text-xs text-[--muted] mb-1">β₁ Loops</div>
                    <div className="text-xl font-semibold text-purple-400">
                      {topologyData.features.betti1_count}
                    </div>
                  </div>
                  <div className="bg-[--surface-muted] rounded-lg p-4">
                    <div className="text-xs text-[--muted] mb-1">Complexity</div>
                    <div className="text-xl font-semibold text-green-400">
                      {topologyData.features.topological_complexity.toFixed(1)}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {selectedSection === 'topology' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div 
                  ref={persistenceChartRef} 
                  className="w-full h-[350px] bg-[--surface-muted] rounded-lg"
                >
                  {!topologyData?.has_data && !loading && (
                    <div className="flex items-center justify-center h-full text-[--muted]">
                      Analyze a ticker to view persistence diagram
                    </div>
                  )}
                </div>
                <div 
                  ref={bettiChartRef} 
                  className="w-full h-[350px] bg-[--surface-muted] rounded-lg"
                >
                  {!topologyData?.has_data && !loading && (
                    <div className="flex items-center justify-center h-full text-[--muted]">
                      Analyze a ticker to view Betti curves
                    </div>
                  )}
                </div>
              </div>

              {topologyData?.has_data && (
                <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
                  <div className="bg-[--surface-muted] rounded-lg p-3">
                    <div className="text-xs text-[--muted] mb-1">Max H₀ Lifetime</div>
                    <div className="text-lg font-semibold text-blue-400">
                      {topologyData.features.max_lifetime_h0.toFixed(3)}
                    </div>
                  </div>
                  <div className="bg-[--surface-muted] rounded-lg p-3">
                    <div className="text-xs text-[--muted] mb-1">Max H₁ Lifetime</div>
                    <div className="text-lg font-semibold text-purple-400">
                      {topologyData.features.max_lifetime_h1.toFixed(3)}
                    </div>
                  </div>
                  <div className="bg-[--surface-muted] rounded-lg p-3">
                    <div className="text-xs text-[--muted] mb-1">Mean H₀ Lifetime</div>
                    <div className="text-lg font-semibold text-blue-400">
                      {topologyData.features.mean_lifetime_h0.toFixed(3)}
                    </div>
                  </div>
                  <div className="bg-[--surface-muted] rounded-lg p-3">
                    <div className="text-xs text-[--muted] mb-1">Mean H₁ Lifetime</div>
                    <div className="text-lg font-semibold text-purple-400">
                      {topologyData.features.mean_lifetime_h1.toFixed(3)}
                    </div>
                  </div>
                  <div className="bg-[--surface-muted] rounded-lg p-3">
                    <div className="text-xs text-[--muted] mb-1">Entropy</div>
                    <div className="text-lg font-semibold text-yellow-400">
                      {topologyData.features.persistence_entropy.toFixed(3)}
                    </div>
                  </div>
                  <div className="bg-[--surface-muted] rounded-lg p-3">
                    <div className="text-xs text-[--muted] mb-1">Total H₁ Persistence</div>
                    <div className="text-lg font-semibold text-purple-400">
                      {topologyData.features.total_persistence_h1.toFixed(3)}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {selectedSection === 'strategy' && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4 p-4 bg-[--surface-muted] rounded-lg">
                <div>
                  <label className="block text-xs text-[--muted] mb-1">β₁ Threshold</label>
                  <input
                    type="number"
                    value={entryBetti1Threshold}
                    onChange={(e) => setEntryBetti1Threshold(parseInt(e.target.value) || 3)}
                    min={1}
                    max={20}
                    className="w-full px-3 py-2 bg-[--surface] border border-[--border] rounded-lg text-[--text] text-sm focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs text-[--muted] mb-1">Entropy Threshold</label>
                  <input
                    type="number"
                    value={entryEntropyThreshold}
                    onChange={(e) => setEntryEntropyThreshold(parseFloat(e.target.value) || 0.5)}
                    min={0}
                    max={2}
                    step={0.1}
                    className="w-full px-3 py-2 bg-[--surface] border border-[--border] rounded-lg text-[--text] text-sm focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs text-[--muted] mb-1">Stop Loss %</label>
                  <input
                    type="number"
                    value={stopLossPct}
                    onChange={(e) => setStopLossPct(parseFloat(e.target.value) || 5)}
                    min={1}
                    max={20}
                    className="w-full px-3 py-2 bg-[--surface] border border-[--border] rounded-lg text-[--text] text-sm focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs text-[--muted] mb-1">Take Profit %</label>
                  <input
                    type="number"
                    value={takeProfitPct}
                    onChange={(e) => setTakeProfitPct(parseFloat(e.target.value) || 10)}
                    min={1}
                    max={50}
                    className="w-full px-3 py-2 bg-[--surface] border border-[--border] rounded-lg text-[--text] text-sm focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div className="flex items-end">
                  <button
                    onClick={runBacktest}
                    disabled={backtestLoading}
                    className="w-full px-4 py-2 bg-green-500 hover:bg-green-600 disabled:bg-green-500/50 text-white rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2"
                  >
                    {backtestLoading ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>Running...</span>
                      </>
                    ) : (
                      <>
                        <Play className="w-4 h-4" />
                        <span>Run Backtest</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {backtestError && (
                <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
                  {backtestError}
                </div>
              )}

              {backtestData && (
                <>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="bg-[--surface-muted] rounded-lg p-4">
                      <div className="text-xs text-[--muted] mb-1">Total Return</div>
                      <div className={`text-xl font-semibold ${backtestData.total_return_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {backtestData.total_return_pct >= 0 ? '+' : ''}{backtestData.total_return_pct.toFixed(2)}%
                      </div>
                    </div>
                    <div className="bg-[--surface-muted] rounded-lg p-4">
                      <div className="text-xs text-[--muted] mb-1">Win Rate</div>
                      <div className="text-xl font-semibold text-[--text]">
                        {backtestData.win_rate.toFixed(1)}%
                      </div>
                    </div>
                    <div className="bg-[--surface-muted] rounded-lg p-4">
                      <div className="text-xs text-[--muted] mb-1">Max Drawdown</div>
                      <div className="text-xl font-semibold text-red-400">
                        -{backtestData.max_drawdown_pct.toFixed(2)}%
                      </div>
                    </div>
                    <div className="bg-[--surface-muted] rounded-lg p-4">
                      <div className="text-xs text-[--muted] mb-1">Total Trades</div>
                      <div className="text-xl font-semibold text-[--text]">
                        {backtestData.total_trades}
                      </div>
                    </div>
                  </div>

                  <div 
                    ref={equityChartRef} 
                    className="w-full h-[300px] bg-[--surface-muted] rounded-lg"
                  />

                  {backtestData.trades.length > 0 && (
                    <div className="bg-[--surface-muted] rounded-lg overflow-hidden">
                      <div className="px-4 py-3 border-b border-[--border]">
                        <h4 className="font-semibold text-[--text]">Trade History</h4>
                      </div>
                      <div className="max-h-[300px] overflow-y-auto">
                        <table className="w-full text-sm">
                          <thead className="bg-[--surface] sticky top-0">
                            <tr className="text-[--muted]">
                              <th className="px-4 py-2 text-left">Entry</th>
                              <th className="px-4 py-2 text-left">Exit</th>
                              <th className="px-4 py-2 text-right">Return</th>
                              <th className="px-4 py-2 text-right">Days</th>
                              <th className="px-4 py-2 text-left">Exit Reason</th>
                            </tr>
                          </thead>
                          <tbody>
                            {backtestData.trades.map((trade, i) => (
                              <tr key={i} className="border-t border-[--border] hover:bg-[--surface]">
                                <td className="px-4 py-2 text-[--text]">{trade.entry_date}</td>
                                <td className="px-4 py-2 text-[--text]">{trade.exit_date}</td>
                                <td className={`px-4 py-2 text-right font-medium ${trade.return_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                  {trade.return_pct >= 0 ? '+' : ''}{trade.return_pct.toFixed(2)}%
                                </td>
                                <td className="px-4 py-2 text-right text-[--muted]">{trade.holding_days}</td>
                                <td className="px-4 py-2 text-[--muted] capitalize">{trade.exit_reason.replace(/_/g, ' ')}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </>
              )}

              {!backtestData && !backtestLoading && !backtestError && (
                <div className="h-[300px] bg-[--surface-muted] rounded-lg flex items-center justify-center text-[--muted]">
                  Configure strategy parameters and click Run Backtest
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-[--panel] rounded-xl border border-[--border] p-5">
          <h3 className="font-semibold text-[--text] mb-3 flex items-center gap-2">
            <Box className="w-4 h-4 text-blue-400" />
            Quick Start Guide
          </h3>
          <ol className="space-y-2 text-sm text-[--muted]">
            <li className="flex items-start gap-2">
              <span className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center text-xs font-medium">1</span>
              <span>Enter a stock ticker (e.g., AAPL, NVDA) and click Analyze</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center text-xs font-medium">2</span>
              <span>Adjust embedding dimension (m) and time delay (τ) parameters</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center text-xs font-medium">3</span>
              <span>View the 3D attractor reconstruction and analyze structure</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center text-xs font-medium">4</span>
              <span>Switch to Topology Analyzer for persistence features</span>
            </li>
          </ol>
        </div>

        <div className="bg-[--panel] rounded-xl border border-[--border] p-5">
          <h3 className="font-semibold text-[--text] mb-3 flex items-center gap-2">
            <Activity className="w-4 h-4 text-purple-400" />
            Key Metrics
          </h3>
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-[--surface-muted] rounded-lg p-3">
              <div className="text-xs text-[--muted] mb-1">β₀ (Components)</div>
              <div className="text-lg font-semibold text-[--text]">Connected regions</div>
            </div>
            <div className="bg-[--surface-muted] rounded-lg p-3">
              <div className="text-xs text-[--muted] mb-1">β₁ (Loops)</div>
              <div className="text-lg font-semibold text-[--text]">Cycle structures</div>
            </div>
            <div className="bg-[--surface-muted] rounded-lg p-3">
              <div className="text-xs text-[--muted] mb-1">Persistence</div>
              <div className="text-lg font-semibold text-[--text]">Feature lifetime</div>
            </div>
            <div className="bg-[--surface-muted] rounded-lg p-3">
              <div className="text-xs text-[--muted] mb-1">Entropy</div>
              <div className="text-lg font-semibold text-[--text]">Complexity score</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
