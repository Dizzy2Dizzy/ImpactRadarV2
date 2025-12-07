'use client';

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  Cell,
} from 'recharts';
import { Clock, Target, Lightbulb, TrendingUp, AlertCircle } from 'lucide-react';

interface HorizonMetric {
  horizon: string;
  win_rate: number;
  mae: number;
  total_predictions: number;
  avg_confidence?: number;
}

interface HorizonComparisonProps {
  data: HorizonMetric[];
  loading?: boolean;
}

function getHorizonLabel(horizon: string): string {
  if (horizon === '1d' || horizon === '1_day') return '1 Day';
  if (horizon === '7d' || horizon === '7_day') return '7 Days';
  if (horizon === '30d' || horizon === '30_day') return '30 Days';
  return horizon.replace('_', ' ').replace('d', ' Day');
}

function getRecommendation(data: HorizonMetric[]): { text: string; type: 'success' | 'warning' | 'neutral' } {
  if (data.length === 0) {
    return { text: 'No data available for recommendations', type: 'neutral' };
  }

  const sortedByWinRate = [...data].sort((a, b) => b.win_rate - a.win_rate);
  const bestHorizon = sortedByWinRate[0];
  const worstHorizon = sortedByWinRate[sortedByWinRate.length - 1];
  
  const bestWinRate = bestHorizon.win_rate > 1 ? bestHorizon.win_rate : bestHorizon.win_rate * 100;
  const worstWinRate = worstHorizon.win_rate > 1 ? worstHorizon.win_rate : worstHorizon.win_rate * 100;

  if (bestWinRate >= 60) {
    return {
      text: `${getHorizonLabel(bestHorizon.horizon)} predictions show the highest accuracy at ${bestWinRate.toFixed(1)}%. Consider prioritizing this timeframe for trading decisions.`,
      type: 'success',
    };
  } else if (bestWinRate >= 50) {
    return {
      text: `${getHorizonLabel(bestHorizon.horizon)} predictions perform best at ${bestWinRate.toFixed(1)}%. Model shows moderate predictive power across horizons.`,
      type: 'neutral',
    };
  } else {
    return {
      text: `All horizons showing below 50% accuracy. Consider reviewing model parameters or waiting for more data before acting on predictions.`,
      type: 'warning',
    };
  }
}

export function HorizonComparison({ data, loading = false }: HorizonComparisonProps) {
  if (loading) {
    return (
      <div className="bg-[--surface-muted] rounded-lg p-6 border border-[--border]">
        <div className="flex items-center gap-2 mb-6">
          <div className="h-5 w-5 bg-[--surface-strong] rounded animate-pulse"></div>
          <div className="h-6 w-48 bg-[--surface-strong] rounded animate-pulse"></div>
        </div>
        <div className="h-64 bg-[--surface-strong] rounded animate-pulse"></div>
        <div className="mt-4 h-16 bg-[--surface-strong] rounded animate-pulse"></div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="bg-[--surface-muted] rounded-lg p-6 border border-[--border]">
        <div className="flex items-center gap-2 mb-6">
          <Clock className="h-5 w-5 text-[--success]" />
          <h3 className="text-lg font-semibold text-[--text]">Horizon Comparison</h3>
        </div>
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <Target className="w-12 h-12 text-[--muted] mb-4" />
          <h4 className="text-lg font-semibold text-[--text] mb-2">No Horizon Data</h4>
          <p className="text-[--muted] max-w-md">
            Comparison metrics across prediction horizons (1d, 7d, 30d) will appear here once outcomes are tracked.
          </p>
        </div>
      </div>
    );
  }

  const chartData = data.map((item) => ({
    ...item,
    horizonLabel: getHorizonLabel(item.horizon),
    winRatePercent: item.win_rate > 1 ? item.win_rate : item.win_rate * 100,
  }));

  const recommendation = getRecommendation(data);

  return (
    <div className="bg-[--surface-muted] rounded-lg p-6 border border-[--border]">
      <div className="flex items-center gap-2 mb-6">
        <Clock className="h-5 w-5 text-[--success]" />
        <h3 className="text-lg font-semibold text-[--text]">Horizon Comparison</h3>
        <span className="ml-auto text-sm text-[--muted]">{data.length} horizons</span>
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis
            dataKey="horizonLabel"
            stroke="var(--muted)"
            style={{ fontSize: '12px' }}
          />
          <YAxis
            yAxisId="left"
            stroke="var(--muted)"
            style={{ fontSize: '12px' }}
            tickFormatter={(value) => `${value}%`}
            domain={[0, 100]}
          />
          <YAxis
            yAxisId="right"
            orientation="right"
            stroke="var(--muted)"
            style={{ fontSize: '12px' }}
            tickFormatter={(value) => value.toFixed(3)}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'var(--panel)',
              border: '1px solid var(--border)',
              borderRadius: '8px',
            }}
            formatter={(value: any, name: string) => {
              if (name === 'Win Rate') return [`${value.toFixed(1)}%`, name];
              if (name === 'MAE') return [value.toFixed(4), name];
              return [value, name];
            }}
          />
          <Legend />
          <Bar
            yAxisId="left"
            dataKey="winRatePercent"
            name="Win Rate"
            radius={[8, 8, 0, 0]}
          >
            {chartData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.winRatePercent >= 50 ? 'var(--success)' : 'var(--error)'}
              />
            ))}
          </Bar>
          <Bar
            yAxisId="right"
            dataKey="mae"
            name="MAE"
            fill="var(--primary)"
            radius={[8, 8, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>

      <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
        {chartData.map((item) => (
          <div key={item.horizon} className="bg-[--surface-muted] rounded-lg p-4 border border-[--border]">
            <div className="text-sm text-[--muted] mb-2">{item.horizonLabel}</div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className={`text-xl font-bold ${item.winRatePercent >= 50 ? 'text-[--success]' : 'text-[--error]'}`}>
                  {item.winRatePercent.toFixed(1)}%
                </div>
                <div className="text-xs text-[--muted]">Win Rate</div>
              </div>
              <div>
                <div className="text-xl font-bold text-[--primary]">
                  {item.mae.toFixed(4)}
                </div>
                <div className="text-xs text-[--muted]">MAE</div>
              </div>
            </div>
            <div className="mt-2 text-xs text-[--muted]">
              {item.total_predictions.toLocaleString()} predictions
            </div>
          </div>
        ))}
      </div>

      <div className={`mt-6 p-4 rounded-lg border ${
        recommendation.type === 'success' 
          ? 'bg-[--success-light] border-[--border-strong]'
          : recommendation.type === 'warning'
          ? 'bg-[--warning-light] border-[--border-strong]'
          : 'bg-[--surface-muted] border-[--border]'
      }`}>
        <div className="flex items-start gap-3">
          <div className={`flex items-center justify-center h-8 w-8 rounded-full ${
            recommendation.type === 'success' 
              ? 'bg-[--success-soft]'
              : recommendation.type === 'warning'
              ? 'bg-[--warning-soft]'
              : 'bg-[--surface-strong]'
          }`}>
            {recommendation.type === 'success' ? (
              <TrendingUp className="h-4 w-4 text-[--success]" />
            ) : recommendation.type === 'warning' ? (
              <AlertCircle className="h-4 w-4 text-[--warning]" />
            ) : (
              <Lightbulb className="h-4 w-4 text-[--text]" />
            )}
          </div>
          <div>
            <h4 className={`font-medium mb-1 ${
              recommendation.type === 'success' 
                ? 'text-[--success]'
                : recommendation.type === 'warning'
                ? 'text-[--warning]'
                : 'text-[--text]'
            }`}>
              Recommendation
            </h4>
            <p className="text-sm text-[--muted]">{recommendation.text}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
