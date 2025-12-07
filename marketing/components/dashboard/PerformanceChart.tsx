'use client';

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

interface EquityPoint {
  date: string;
  portfolio_value: number;
  benchmark_value?: number;
}

interface PerformanceChartProps {
  data: EquityPoint[];
  loading?: boolean;
}

export function PerformanceChart({ data, loading }: PerformanceChartProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-400"></div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <p className="text-[--muted]">No equity curve data available</p>
        <p className="text-sm text-[--muted] mt-2">Run a backtest to see performance over time</p>
      </div>
    );
  }

  const formatValue = (value: number) => {
    return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-[--card] border border-white/20 rounded-lg p-3 shadow-lg">
          <p className="text-sm text-[--muted] mb-2">{formatDate(label)}</p>
          {payload.map((entry: any, index: number) => (
            <p key={index} className="text-sm font-semibold" style={{ color: entry.color }}>
              {entry.name}: {formatValue(entry.value)}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="w-full h-64">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.1)" />
          <XAxis 
            dataKey="date" 
            stroke="rgba(255, 255, 255, 0.5)"
            tick={{ fill: 'rgba(255, 255, 255, 0.7)', fontSize: 12 }}
            tickFormatter={formatDate}
          />
          <YAxis 
            stroke="rgba(255, 255, 255, 0.5)"
            tick={{ fill: 'rgba(255, 255, 255, 0.7)', fontSize: 12 }}
            tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend 
            wrapperStyle={{ color: 'rgba(255, 255, 255, 0.7)' }}
          />
          <Line 
            type="monotone" 
            dataKey="portfolio_value" 
            stroke="#10b981" 
            strokeWidth={2}
            name="Portfolio Value"
            dot={false}
          />
          {data.some(d => d.benchmark_value) && (
            <Line 
              type="monotone" 
              dataKey="benchmark_value" 
              stroke="#6366f1" 
              strokeWidth={2}
              strokeDasharray="5 5"
              name="Benchmark"
              dot={false}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
