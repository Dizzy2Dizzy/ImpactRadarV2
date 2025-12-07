'use client';

import { useState, useEffect } from 'react';
import { api, HistoricalStatsResponse } from '@/lib/api';
import { Tooltip } from '@/components/ui/tooltip';

interface StatsBadgeProps {
  ticker: string;
  eventType: string;
}

export function StatsBadge({ ticker, eventType }: StatsBadgeProps) {
  const [stats, setStats] = useState<HistoricalStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadStats() {
      try {
        setLoading(true);
        setError(null);
        const response = await fetch(`/api/proxy/stats/${ticker}/${eventType}`, {
          headers: {
            'Content-Type': 'application/json',
          },
        });
        
        if (!response.ok) {
          if (response.status === 402 || response.status === 403) {
            setError('upgrade');
          } else if (response.status === 404) {
            setError('not_found');
          } else {
            setError('error');
          }
          return;
        }
        
        const data = await response.json();
        setStats(data);
      } catch (e: any) {
        setError('not_found');
      } finally {
        setLoading(false);
      }
    }
    
    loadStats();
  }, [ticker, eventType]);

  if (loading) {
    return (
      <span className="text-xs text-[--muted] animate-pulse">
        Loading stats...
      </span>
    );
  }

  if (error === 'upgrade') {
    return (
      <a
        href="/pricing"
        className="text-xs text-[--primary] hover:opacity-80 cursor-pointer transition-colors"
      >
        Upgrade for historical stats →
      </a>
    );
  }

  if (error === 'not_found' || error === 'error' || !stats) {
    return null;
  }

  const move = stats.mean_move_1d || stats.avg_abs_move_1d || 0;
  const absMove = Math.abs(move);
  const winRate = stats.win_rate || 0;

  const tooltipContent = (
    <div className="space-y-2 text-left">
      <div className="font-semibold">Historical Impact</div>
      <div className="space-y-1">
        <div className="flex justify-between gap-4">
          <span className="opacity-70">Sample Size:</span>
          <span className="font-medium">{stats.sample_size} events</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="opacity-70">Win Rate:</span>
          <span className="font-medium">{winRate.toFixed(1)}%</span>
        </div>
        
        {(stats.mean_move_1d !== null || stats.mean_move_5d !== null || stats.mean_move_20d !== null) && (
          <div className="border-t border-[--border] my-2 pt-2">
            <div className="font-medium mb-1">Average Moves:</div>
            {stats.mean_move_1d !== null && (
              <div className="flex justify-between gap-4">
                <span className="opacity-70">1 Day:</span>
                <span className="font-medium">{stats.mean_move_1d.toFixed(2)}%</span>
              </div>
            )}
            {stats.mean_move_5d !== null && (
              <div className="flex justify-between gap-4">
                <span className="opacity-70">5 Days:</span>
                <span className="font-medium">{stats.mean_move_5d.toFixed(2)}%</span>
              </div>
            )}
            {stats.mean_move_20d !== null && (
              <div className="flex justify-between gap-4">
                <span className="opacity-70">20 Days:</span>
                <span className="font-medium">{stats.mean_move_20d.toFixed(2)}%</span>
              </div>
            )}
          </div>
        )}

        {(stats.avg_abs_move_1d !== null || stats.avg_abs_move_5d !== null || stats.avg_abs_move_20d !== null) && (
          <div className="border-t border-[--border] my-2 pt-2">
            <div className="font-medium mb-1">Absolute Moves:</div>
            {stats.avg_abs_move_1d !== null && (
              <div className="flex justify-between gap-4">
                <span className="opacity-70">1 Day:</span>
                <span className="font-medium">±{stats.avg_abs_move_1d.toFixed(2)}%</span>
              </div>
            )}
            {stats.avg_abs_move_5d !== null && (
              <div className="flex justify-between gap-4">
                <span className="opacity-70">5 Days:</span>
                <span className="font-medium">±{stats.avg_abs_move_5d.toFixed(2)}%</span>
              </div>
            )}
            {stats.avg_abs_move_20d !== null && (
              <div className="flex justify-between gap-4">
                <span className="opacity-70">20 Days:</span>
                <span className="font-medium">±{stats.avg_abs_move_20d.toFixed(2)}%</span>
              </div>
            )}
          </div>
        )}
        
        <div className="border-t border-[--border] my-2 pt-2 opacity-70 text-xs">
          {stats.methodology}
        </div>
      </div>
    </div>
  );

  return (
    <Tooltip content={tooltipContent}>
      <span className="inline-flex items-center gap-1 bg-[--primary-light] text-[--primary] px-2 py-1 rounded text-xs cursor-help hover:bg-[--surface-hover] transition-colors">
        <span>Avg ±{absMove.toFixed(1)}%</span>
        <span className="text-[--muted]">(n={stats.sample_size})</span>
      </span>
    </Tooltip>
  );
}
