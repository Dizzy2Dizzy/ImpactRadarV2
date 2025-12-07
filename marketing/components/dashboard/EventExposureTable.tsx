"use client";

import { EventExposure } from "@/lib/api";
import { TrendingUp, TrendingDown, Shield } from "lucide-react";

interface EventExposureTableProps {
  exposures: EventExposure[];
}

export function EventExposureTable({ exposures }: EventExposureTableProps) {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  const getImpactColor = (impact: number) => {
    const absImpact = Math.abs(impact);
    if (absImpact >= 5) return 'text-red-400';
    if (absImpact >= 3) return 'text-yellow-400';
    return 'text-green-400';
  };

  const getExposureColor = (exposure: number) => {
    const absExposure = Math.abs(exposure);
    if (absExposure >= 10000) return 'text-red-400';
    if (absExposure >= 5000) return 'text-yellow-400';
    return 'text-blue-400';
  };

  if (exposures.length === 0) {
    return (
      <div className="rounded-lg border border-white/10 bg-[--panel] p-8 text-center">
        <p className="text-[--muted]">No event exposures calculated yet. Click "Calculate Risk" above to analyze your portfolio.</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-white/10 bg-[--panel] overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-white/10 bg-black/20">
              <th className="px-4 py-3 text-left text-xs font-medium text-[--muted] uppercase tracking-wider">Ticker</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-[--muted] uppercase tracking-wider">Event</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-[--muted] uppercase tracking-wider">Date</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-[--muted] uppercase tracking-wider">Position Size</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-[--muted] uppercase tracking-wider">Est. Impact</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-[--muted] uppercase tracking-wider">$ Exposure</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-[--muted] uppercase tracking-wider">Hedge Recommendation</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {exposures.map((exposure) => (
              <tr key={exposure.id} className="hover:bg-white/5 transition-colors">
                <td className="px-4 py-3">
                  <div className="font-mono font-semibold text-[--text]">{exposure.ticker}</div>
                </td>
                <td className="px-4 py-3">
                  <div className="text-sm text-[--text] max-w-xs truncate">{exposure.event_title}</div>
                  <div className="text-xs text-[--muted]">{exposure.event_type}</div>
                </td>
                <td className="px-4 py-3">
                  <div className="text-sm text-[--text]">{formatDate(exposure.event_date)}</div>
                </td>
                <td className="px-4 py-3 text-right">
                  <span className="text-sm font-medium text-[--text]">
                    {exposure.position_size_pct.toFixed(1)}%
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <div className={`text-sm font-medium ${getImpactColor(exposure.estimated_impact_pct)}`}>
                    {exposure.estimated_impact_pct >= 0 ? <TrendingUp className="inline h-3 w-3 mr-1" /> : <TrendingDown className="inline h-3 w-3 mr-1" />}
                    {Math.abs(exposure.estimated_impact_pct).toFixed(2)}%
                  </div>
                </td>
                <td className="px-4 py-3 text-right">
                  <div className={`text-sm font-semibold ${getExposureColor(exposure.dollar_exposure)}`}>
                    ${Math.abs(exposure.dollar_exposure).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                  </div>
                </td>
                <td className="px-4 py-3">
                  {exposure.hedge_recommendation ? (
                    <div className="flex items-start gap-2">
                      <Shield className="h-4 w-4 text-blue-400 flex-shrink-0 mt-0.5" />
                      <span className="text-xs text-[--muted]">{exposure.hedge_recommendation}</span>
                    </div>
                  ) : (
                    <span className="text-xs text-[--muted]">-</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
