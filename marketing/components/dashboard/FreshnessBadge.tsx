'use client';

import { Clock, Database, CheckCircle, AlertTriangle, XCircle } from 'lucide-react';
import { Tooltip } from '@/components/ui/tooltip';

interface FreshnessBadgeProps {
  metric_key: string;
  freshness_ts: string;
  sample_count: number;
  quality_grade: 'excellent' | 'good' | 'fair' | 'stale';
}

export function FreshnessBadge({
  metric_key,
  freshness_ts,
  sample_count,
  quality_grade,
}: FreshnessBadgeProps) {
  const getTimeAgo = (timestamp: string): string => {
    if (!timestamp) return 'Unknown';
    try {
      const now = new Date();
      const past = new Date(timestamp);
      const diffMs = now.getTime() - past.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMins / 60);
      const diffDays = Math.floor(diffHours / 24);

      if (diffMins < 60) {
        return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
      } else if (diffHours < 24) {
        return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
      } else {
        return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
      }
    } catch (e) {
      return 'Unknown';
    }
  };

  const getQualityConfig = (grade: string) => {
    switch (grade) {
      case 'excellent':
        return {
          color: 'text-[--success]',
          bgColor: 'bg-[--success-light]',
          borderColor: 'border-[--border-strong]',
          icon: CheckCircle,
          label: 'Excellent',
        };
      case 'good':
        return {
          color: 'text-[--warning]',
          bgColor: 'bg-[--warning-light]',
          borderColor: 'border-[--border-strong]',
          icon: CheckCircle,
          label: 'Good',
        };
      case 'fair':
        return {
          color: 'text-[--warning]',
          bgColor: 'bg-[--warning-light]',
          borderColor: 'border-[--border-strong]',
          icon: AlertTriangle,
          label: 'Fair',
        };
      case 'stale':
        return {
          color: 'text-[--error]',
          bgColor: 'bg-[--error-light]',
          borderColor: 'border-[--border-strong]',
          icon: XCircle,
          label: 'Stale',
        };
      default:
        return {
          color: 'text-[--muted]',
          bgColor: 'bg-[--surface-muted]',
          borderColor: 'border-[--border]',
          icon: AlertTriangle,
          label: 'Unknown',
        };
    }
  };

  const config = getQualityConfig(quality_grade);
  const Icon = config.icon;
  const timeAgo = getTimeAgo(freshness_ts);

  const tooltipContent = (
    <div className="space-y-2 text-xs">
      <div>
        <p className="font-semibold text-[--text]">Data Quality Details</p>
        <p className="text-[--muted] mt-1">Metric: {metric_key}</p>
      </div>
      <div className="border-t border-[--border] pt-2">
        <p className="text-[--muted]">Last Updated: {freshness_ts ? new Date(freshness_ts).toLocaleString() : 'N/A'}</p>
        <p className="text-[--muted]">Sample Size: {sample_count?.toLocaleString() || 0} events</p>
        <p className={`${config.color} font-semibold mt-1`}>Quality: {config.label}</p>
      </div>
      <div className="border-t border-[--border] pt-2">
        <p className="text-[--muted] text-[10px]">
          {quality_grade === 'excellent' && 'Data is fresh and comprehensive'}
          {quality_grade === 'good' && 'Data is recent with good coverage'}
          {quality_grade === 'fair' && 'Data may need refresh soon'}
          {quality_grade === 'stale' && 'Data needs to be updated'}
        </p>
      </div>
    </div>
  );

  return (
    <Tooltip content={tooltipContent}>
      <div
        className={`inline-flex items-center gap-2 px-3 py-2 rounded-lg border ${config.bgColor} ${config.borderColor} cursor-help transition-all hover:scale-105`}
      >
        <Icon className={`h-4 w-4 ${config.color}`} />
        <div className="flex flex-col items-start">
          <div className="flex items-center gap-2">
            <Clock className={`h-3 w-3 ${config.color}`} />
            <span className={`text-xs font-medium ${config.color}`}>
              Updated {timeAgo}
            </span>
          </div>
          <div className="flex items-center gap-2 mt-0.5">
            <Database className={`h-3 w-3 ${config.color}`} />
            <span className={`text-xs ${config.color}`}>
              {sample_count?.toLocaleString() || 0} events
            </span>
          </div>
        </div>
      </div>
    </Tooltip>
  );
}
