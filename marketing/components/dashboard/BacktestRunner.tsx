'use client';

import { useState } from 'react';
import { apiRequest } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { Play, TrendingUp, Target, Activity, DollarSign, BarChart3, TrendingDown, LineChart, Gauge } from 'lucide-react';

interface BacktestRunnerProps {
  strategyId: number;
  onRunComplete?: (runId: number) => void;
}

interface BacktestResult {
  run_id: number;
  total_return_pct: number;
  win_rate: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  avg_atr: number;
  parkinson_volatility: number;
  max_drawdown: number;
  total_trades: number;
  final_portfolio_value: number;
  initial_capital: number;
  avg_trade_return: number;
  avg_winning_trade: number;
  avg_losing_trade: number;
  largest_win: number;
  largest_loss: number;
}

export function BacktestRunner({ strategyId, onRunComplete }: BacktestRunnerProps) {
  const [startDate, setStartDate] = useState('2023-01-01');
  const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);
  const [initialCapital, setInitialCapital] = useState(100000);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRunBacktest = async () => {
    try {
      setRunning(true);
      setError(null);
      setResult(null);

      const response = await apiRequest<BacktestResult>('/api/proxy/backtesting/run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          strategy_id: strategyId,
          start_date: startDate,
          end_date: endDate,
          initial_capital: initialCapital,
        }),
      });

      setResult(response);
      if (onRunComplete && response.run_id) {
        onRunComplete(response.run_id);
      }
    } catch (err: any) {
      console.error('Failed to run backtest:', err);
      setError(err?.message || 'Failed to run backtest');
    } finally {
      setRunning(false);
    }
  };

  const isValidDateRange = () => {
    const start = new Date(startDate);
    const end = new Date(endDate);
    return start < end && end <= new Date();
  };

  return (
    <div className="space-y-6">
      <div className="bg-white/5 rounded-lg p-6 border border-white/10">
        <h3 className="text-lg font-semibold text-[--text] mb-4">Backtest Configuration</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-[--text] mb-2">
              Start Date
            </label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-[--text]"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[--text] mb-2">
              End Date
            </label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              max={new Date().toISOString().split('T')[0]}
              className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-[--text]"
            />
          </div>
        </div>

        <div className="mb-4">
          <label className="block text-sm font-medium text-[--text] mb-2">
            Initial Capital ($)
          </label>
          <input
            type="number"
            value={initialCapital}
            onChange={(e) => setInitialCapital(Number(e.target.value))}
            min={1000}
            step={1000}
            className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-[--text]"
          />
        </div>

        <Button
          onClick={handleRunBacktest}
          disabled={running || !isValidDateRange() || initialCapital < 1000}
          className="w-full"
        >
          {running ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
              Running Backtest...
            </>
          ) : (
            <>
              <Play className="h-4 w-4 mr-2" />
              Run Backtest
            </>
          )}
        </Button>

        {!isValidDateRange() && (
          <p className="text-sm text-red-400 mt-2">
            Please select a valid date range (start before end, end not in future)
          </p>
        )}

        {error && (
          <div className="mt-4 bg-red-500/10 border border-red-500/20 rounded-lg p-4">
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}
      </div>

      {result && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-[--text]">Backtest Results</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className={`rounded-lg p-4 border ${
              result.total_return_pct > 0 
                ? 'bg-green-500/10 border-green-500/30' 
                : 'bg-red-500/10 border-red-500/30'
            }`}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-[--muted]">Total Return</span>
                <TrendingUp className={`h-5 w-5 ${
                  result.total_return_pct > 0 ? 'text-green-400' : 'text-red-400'
                }`} />
              </div>
              <div className={`text-3xl font-bold ${
                result.total_return_pct > 0 ? 'text-green-400' : 'text-red-400'
              }`}>
                {result.total_return_pct > 0 ? '+' : ''}{result.total_return_pct.toFixed(2)}%
              </div>
              <div className="text-xs text-[--muted] mt-1">
                ${result.initial_capital.toLocaleString()} → ${result.final_portfolio_value.toLocaleString()}
              </div>
            </div>

            <div className="bg-white/5 rounded-lg p-4 border border-white/10">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-[--muted]">Win Rate</span>
                <Target className="h-5 w-5 text-blue-400" />
              </div>
              <div className="text-3xl font-bold text-[--text]">
                {result.win_rate.toFixed(1)}%
              </div>
              <div className="text-xs text-[--muted] mt-1">
                {Math.round(result.total_trades * result.win_rate / 100)} wins / {result.total_trades} trades
              </div>
            </div>

            <div className="bg-white/5 rounded-lg p-4 border border-white/10">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-[--muted]">Sharpe Ratio</span>
                <Activity className="h-5 w-5 text-purple-400" />
              </div>
              <div className="text-3xl font-bold text-[--text]">
                {result.sharpe_ratio.toFixed(2)}
              </div>
              <div className="text-xs text-[--muted] mt-1">
                Risk-adjusted return
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white/5 rounded-lg p-4 border border-white/10">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-[--muted]">Sortino Ratio</span>
                <TrendingDown className="h-5 w-5 text-orange-400" />
              </div>
              <div className="text-3xl font-bold text-[--text]">
                {result.sortino_ratio !== null && result.sortino_ratio !== undefined 
                  ? result.sortino_ratio.toFixed(2) 
                  : 'N/A'}
              </div>
              <div className="text-xs text-[--muted] mt-1">
                Downside risk-adjusted return
              </div>
            </div>

            <div className="bg-white/5 rounded-lg p-4 border border-white/10">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-[--muted]">Avg ATR</span>
                <LineChart className="h-5 w-5 text-cyan-400" />
              </div>
              <div className="text-3xl font-bold text-[--text]">
                {result.avg_atr !== null && result.avg_atr !== undefined 
                  ? result.avg_atr.toFixed(2) 
                  : 'N/A'}
              </div>
              <div className="text-xs text-[--muted] mt-1">
                Average True Range (volatility)
              </div>
            </div>

            <div className="bg-white/5 rounded-lg p-4 border border-white/10">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-[--muted]">Parkinson Vol</span>
                <Gauge className="h-5 w-5 text-yellow-400" />
              </div>
              <div className="text-3xl font-bold text-[--text]">
                {result.parkinson_volatility !== null && result.parkinson_volatility !== undefined 
                  ? `${result.parkinson_volatility.toFixed(2)}%` 
                  : 'N/A'}
              </div>
              <div className="text-xs text-[--muted] mt-1">
                High-low range volatility
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-white/5 rounded-lg p-4 border border-white/10">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-[--muted]">Max Drawdown</span>
                <BarChart3 className="h-5 w-5 text-red-400" />
              </div>
              <div className="text-2xl font-bold text-red-400">
                {result.max_drawdown.toFixed(2)}%
              </div>
              <div className="text-xs text-[--muted] mt-1">
                Maximum peak-to-trough decline
              </div>
            </div>

            <div className="bg-white/5 rounded-lg p-4 border border-white/10">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-[--muted]">Total Trades</span>
                <DollarSign className="h-5 w-5 text-emerald-400" />
              </div>
              <div className="text-2xl font-bold text-[--text]">
                {result.total_trades}
              </div>
              <div className="text-xs text-[--muted] mt-1">
                Avg return: {result.avg_trade_return.toFixed(2)}%
              </div>
            </div>
          </div>

          {result.avg_winning_trade !== undefined && result.avg_losing_trade !== undefined && (
            <div className="bg-white/5 rounded-lg p-4 border border-white/10">
              <h4 className="text-sm font-semibold text-[--text] mb-3">Trade Statistics</h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <p className="text-[--muted] mb-1">Avg Win</p>
                  <p className="font-semibold text-green-400">+{result.avg_winning_trade.toFixed(2)}%</p>
                </div>
                <div>
                  <p className="text-[--muted] mb-1">Avg Loss</p>
                  <p className="font-semibold text-red-400">{result.avg_losing_trade.toFixed(2)}%</p>
                </div>
                <div>
                  <p className="text-[--muted] mb-1">Largest Win</p>
                  <p className="font-semibold text-green-400">+{result.largest_win.toFixed(2)}%</p>
                </div>
                <div>
                  <p className="text-[--muted] mb-1">Largest Loss</p>
                  <p className="font-semibold text-red-400">{result.largest_loss.toFixed(2)}%</p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
