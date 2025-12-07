'use client';

import { useState, useEffect } from 'react';
import { apiRequest } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { StrategyBuilder } from '@/components/dashboard/StrategyBuilder';
import { BacktestRunner } from '@/components/dashboard/BacktestRunner';
import { PerformanceChart } from '@/components/dashboard/PerformanceChart';
import { TradeHistoryTable } from '@/components/dashboard/TradeHistoryTable';
import {
  Plus,
  Edit2,
  Trash2,
  TrendingUp,
  Target,
  Activity,
  BarChart3,
  ChevronRight,
  AlertCircle,
  Info,
} from 'lucide-react';

interface Strategy {
  id: number;
  name: string;
  description: string;
  entry_conditions: {
    event_types: string[];
    min_score: number;
    direction: 'long' | 'short' | 'both';
    tickers?: string[];
    sectors?: string[];
  };
  exit_conditions: {
    method: 'fixed_horizon' | 'trailing_stop' | 'profit_target';
    horizon_days?: number;
    take_profit_pct?: number;
    stop_loss_pct?: number;
  };
  position_sizing: {
    method: 'equal_weight' | 'score_weighted' | 'fixed_dollar';
    max_position_pct?: number;
    fixed_amount?: number;
  };
  created_at: string;
  updated_at: string;
  last_backtest?: {
    total_return_pct: number;
    win_rate: number;
    sharpe_ratio: number;
    total_trades: number;
  };
}

interface Trade {
  id: number;
  ticker: string;
  entry_date: string;
  exit_date: string;
  entry_price: number;
  exit_price: number;
  shares: number;
  return_pct: number;
  profit_loss: number;
  event_type?: string;
}

interface EquityPoint {
  date: string;
  portfolio_value: number;
  benchmark_value?: number;
}

export default function BacktestingPage() {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState<Strategy | null>(null);
  const [showBuilder, setShowBuilder] = useState(false);
  const [editingStrategy, setEditingStrategy] = useState<Strategy | null>(null);
  
  const [currentRunId, setCurrentRunId] = useState<number | null>(null);
  const [equityCurve, setEquityCurve] = useState<EquityPoint[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tradesLoading, setTradesLoading] = useState(false);

  useEffect(() => {
    loadStrategies();
  }, []);

  const loadStrategies = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiRequest<Strategy[]>('/api/proxy/backtesting/strategies');
      setStrategies(data);
      
      // Auto-select first strategy if none selected
      if (data.length > 0 && !selectedStrategy) {
        setSelectedStrategy(data[0]);
      }
    } catch (err: any) {
      console.error('Failed to load strategies:', err);
      if (err?.status === 403 || err?.message?.includes('403')) {
        setError('Access not available, please upgrade plan');
      } else {
        setError(err?.message || 'Failed to load strategies');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteStrategy = async (id: number) => {
    if (!confirm('Are you sure you want to delete this strategy?')) return;
    
    try {
      await apiRequest(`/api/proxy/backtesting/strategies/${id}`, {
        method: 'DELETE',
      });
      
      if (selectedStrategy?.id === id) {
        setSelectedStrategy(null);
      }
      
      await loadStrategies();
    } catch (err: any) {
      alert(err?.message || 'Failed to delete strategy');
    }
  };

  const handleStrategySaved = async (strategy: Strategy) => {
    setShowBuilder(false);
    setEditingStrategy(null);
    await loadStrategies();
    setSelectedStrategy(strategy);
  };

  const handleBacktestComplete = async (runId: number) => {
    setCurrentRunId(runId);
    await loadBacktestResults(runId);
  };

  const loadBacktestResults = async (runId: number) => {
    try {
      // Load trades
      setTradesLoading(true);
      const tradesData = await apiRequest<Trade[]>(`/api/proxy/backtesting/runs/${runId}/trades`);
      setTrades(tradesData);
      
      // Load full results to get equity curve
      const results = await apiRequest<{
        equity_curve?: EquityPoint[];
        trades: Trade[];
      }>(`/api/proxy/backtesting/runs/${runId}`);
      
      if (results.equity_curve) {
        setEquityCurve(results.equity_curve);
      }
    } catch (err: any) {
      console.error('Failed to load backtest results:', err);
    } finally {
      setTradesLoading(false);
    }
  };

  if (loading && strategies.length === 0) {
    return (
      <div className="min-h-screen bg-[--bg] flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-400 mx-auto mb-4"></div>
          <p className="text-[--muted]">Loading backtesting dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[--bg] p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-[--text] mb-2">Strategy Backtesting</h1>
          <p className="text-[--muted]">
            Create and test trading strategies based on event signals
          </p>
        </div>

        {error && !loading && (
          <div className="mb-6 bg-red-500/10 border border-red-500/20 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-red-400 mt-0.5 flex-shrink-0" />
              <div>
                <h4 className="text-sm font-semibold text-red-400 mb-1">Error Loading Strategies</h4>
                <p className="text-sm text-[--muted]">{error}</p>
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Strategy List */}
          <div className="lg:col-span-1">
            <div className="bg-white/5 rounded-lg border border-white/10 p-4">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-[--text]">Strategies</h2>
                <Button
                  onClick={() => {
                    setShowBuilder(true);
                    setEditingStrategy(null);
                    setSelectedStrategy(null);
                  }}
                  size="sm"
                >
                  <Plus className="h-4 w-4 mr-1" />
                  New
                </Button>
              </div>

              {strategies.length === 0 ? (
                <div className="text-center py-12">
                  <BarChart3 className="h-12 w-12 text-[--muted] mx-auto mb-3" />
                  <p className="text-sm text-[--muted] mb-4">No strategies yet</p>
                  <Button
                    onClick={() => {
                      setShowBuilder(true);
                      setEditingStrategy(null);
                    }}
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Create Your First Strategy
                  </Button>
                </div>
              ) : (
                <div className="space-y-2 max-h-[calc(100vh-300px)] overflow-y-auto">
                  {strategies.map((strategy) => (
                    <div
                      key={strategy.id}
                      onClick={() => {
                        setSelectedStrategy(strategy);
                        setShowBuilder(false);
                      }}
                      className={`p-4 rounded-lg border cursor-pointer transition-colors ${
                        selectedStrategy?.id === strategy.id
                          ? 'bg-emerald-500/10 border-emerald-500/30'
                          : 'bg-white/5 border-white/10 hover:bg-white/10'
                      }`}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <h3 className="font-semibold text-[--text] text-sm">{strategy.name}</h3>
                        <div className="flex gap-1">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setEditingStrategy(strategy);
                              setShowBuilder(true);
                              setSelectedStrategy(null);
                            }}
                            className="p-1 hover:bg-white/10 rounded"
                          >
                            <Edit2 className="h-3 w-3 text-[--muted]" />
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteStrategy(strategy.id);
                            }}
                            className="p-1 hover:bg-white/10 rounded"
                          >
                            <Trash2 className="h-3 w-3 text-red-400" />
                          </button>
                        </div>
                      </div>

                      {strategy.description && (
                        <p className="text-xs text-[--muted] mb-3 line-clamp-2">
                          {strategy.description}
                        </p>
                      )}

                      {strategy.last_backtest ? (
                        <div className="grid grid-cols-2 gap-2 text-xs">
                          <div>
                            <span className="text-[--muted]">Return:</span>
                            <span className={`ml-1 font-semibold ${
                              strategy.last_backtest.total_return_pct > 0 ? 'text-green-400' : 'text-red-400'
                            }`}>
                              {strategy.last_backtest.total_return_pct > 0 ? '+' : ''}
                              {strategy.last_backtest.total_return_pct.toFixed(1)}%
                            </span>
                          </div>
                          <div>
                            <span className="text-[--muted]">Win Rate:</span>
                            <span className="ml-1 font-semibold text-[--text]">
                              {strategy.last_backtest.win_rate.toFixed(1)}%
                            </span>
                          </div>
                          <div>
                            <span className="text-[--muted]">Sharpe:</span>
                            <span className="ml-1 font-semibold text-[--text]">
                              {strategy.last_backtest.sharpe_ratio.toFixed(2)}
                            </span>
                          </div>
                          <div>
                            <span className="text-[--muted]">Trades:</span>
                            <span className="ml-1 font-semibold text-[--text]">
                              {strategy.last_backtest.total_trades}
                            </span>
                          </div>
                        </div>
                      ) : (
                        <p className="text-xs text-[--muted] italic">Not backtested yet</p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Strategy Details & Backtest */}
          <div className="lg:col-span-2">
            {showBuilder ? (
              <div className="bg-white/5 rounded-lg border border-white/10 p-6">
                <h2 className="text-xl font-semibold text-[--text] mb-6">
                  {editingStrategy ? 'Edit Strategy' : 'Create New Strategy'}
                </h2>
                <StrategyBuilder
                  strategy={editingStrategy}
                  onSaveComplete={handleStrategySaved}
                  onCancel={() => {
                    setShowBuilder(false);
                    setEditingStrategy(null);
                    if (strategies.length > 0) {
                      setSelectedStrategy(strategies[0]);
                    }
                  }}
                />
              </div>
            ) : selectedStrategy ? (
              <div className="space-y-6">
                {/* Strategy Details */}
                <div className="bg-white/5 rounded-lg border border-white/10 p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h2 className="text-xl font-semibold text-[--text] mb-2">
                        {selectedStrategy.name}
                      </h2>
                      {selectedStrategy.description && (
                        <p className="text-sm text-[--muted]">{selectedStrategy.description}</p>
                      )}
                    </div>
                    <Button
                      onClick={() => {
                        setEditingStrategy(selectedStrategy);
                        setShowBuilder(true);
                      }}
                      variant="outline"
                      size="sm"
                    >
                      <Edit2 className="h-4 w-4 mr-2" />
                      Edit
                    </Button>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                    <div className="bg-white/5 rounded-lg p-3">
                      <p className="text-[--muted] mb-1">Event Types</p>
                      <p className="font-semibold text-[--text]">
                        {selectedStrategy.entry_conditions.event_types.length} selected
                      </p>
                      <p className="text-xs text-[--muted] mt-1 line-clamp-2">
                        {selectedStrategy.entry_conditions.event_types.join(', ')}
                      </p>
                    </div>

                    <div className="bg-white/5 rounded-lg p-3">
                      <p className="text-[--muted] mb-1">Min Score</p>
                      <p className="font-semibold text-[--text]">
                        {selectedStrategy.entry_conditions.min_score}
                      </p>
                    </div>

                    <div className="bg-white/5 rounded-lg p-3">
                      <p className="text-[--muted] mb-1">Direction</p>
                      <p className="font-semibold text-[--text] capitalize">
                        {selectedStrategy.entry_conditions.direction}
                      </p>
                    </div>

                    <div className="bg-white/5 rounded-lg p-3">
                      <p className="text-[--muted] mb-1">Exit Method</p>
                      <p className="font-semibold text-[--text]">
                        {selectedStrategy.exit_conditions.method === 'fixed_horizon' && 'Fixed Horizon'}
                        {selectedStrategy.exit_conditions.method === 'profit_target' && 'Profit Target'}
                        {selectedStrategy.exit_conditions.method === 'trailing_stop' && 'Trailing Stop'}
                      </p>
                      {selectedStrategy.exit_conditions.horizon_days && (
                        <p className="text-xs text-[--muted] mt-1">
                          {selectedStrategy.exit_conditions.horizon_days} days
                        </p>
                      )}
                    </div>

                    <div className="bg-white/5 rounded-lg p-3">
                      <p className="text-[--muted] mb-1">Position Sizing</p>
                      <p className="font-semibold text-[--text] capitalize">
                        {selectedStrategy.position_sizing.method.replace('_', ' ')}
                      </p>
                      {selectedStrategy.position_sizing.max_position_pct && (
                        <p className="text-xs text-[--muted] mt-1">
                          Max {selectedStrategy.position_sizing.max_position_pct}%
                        </p>
                      )}
                    </div>

                    <div className="bg-white/5 rounded-lg p-3">
                      <p className="text-[--muted] mb-1">Created</p>
                      <p className="font-semibold text-[--text]">
                        {new Date(selectedStrategy.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Backtest Runner */}
                <BacktestRunner
                  strategyId={selectedStrategy.id}
                  onRunComplete={handleBacktestComplete}
                />

                {/* Performance Chart */}
                {equityCurve.length > 0 && (
                  <div className="bg-white/5 rounded-lg border border-white/10 p-6">
                    <h3 className="text-lg font-semibold text-[--text] mb-4">Equity Curve</h3>
                    <PerformanceChart data={equityCurve} />
                  </div>
                )}

                {/* Trade History */}
                {trades.length > 0 && (
                  <div className="bg-white/5 rounded-lg border border-white/10 p-6">
                    <h3 className="text-lg font-semibold text-[--text] mb-4">Trade History</h3>
                    <TradeHistoryTable trades={trades} loading={tradesLoading} />
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-white/5 rounded-lg border border-white/10 p-12 text-center">
                <Info className="h-16 w-16 text-[--muted] mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-[--text] mb-2">
                  Select a Strategy
                </h3>
                <p className="text-sm text-[--muted] mb-6">
                  Choose a strategy from the list to view details and run backtests,<br />
                  or create a new strategy to get started.
                </p>
                <Button
                  onClick={() => {
                    setShowBuilder(true);
                    setEditingStrategy(null);
                  }}
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Create New Strategy
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
