'use client';

import { useState } from 'react';
import { 
  AlertTriangle, 
  TrendingDown, 
  TrendingUp, 
  Info, 
  X, 
  ChevronDown, 
  ChevronUp,
  Bell 
} from 'lucide-react';

type AlertSeverity = 'critical' | 'warning' | 'info';

interface PerformanceAlert {
  id: string;
  severity: AlertSeverity;
  title: string;
  message: string;
  metric?: string;
  value?: number;
  threshold?: number;
  timestamp: string;
}

interface AlertBannerProps {
  alerts: PerformanceAlert[];
  loading?: boolean;
  onDismiss?: (alertId: string) => void;
}

function getSeverityStyles(severity: AlertSeverity) {
  switch (severity) {
    case 'critical':
      return {
        bg: 'bg-[--error-light]',
        border: 'border-[--border-strong]',
        text: 'text-[--error]',
        icon: AlertTriangle,
        iconBg: 'bg-[--error-soft]',
      };
    case 'warning':
      return {
        bg: 'bg-[--warning-light]',
        border: 'border-[--border-strong]',
        text: 'text-[--warning]',
        icon: TrendingDown,
        iconBg: 'bg-[--warning-soft]',
      };
    case 'info':
      return {
        bg: 'bg-[--success-light]',
        border: 'border-[--border-strong]',
        text: 'text-[--success]',
        icon: TrendingUp,
        iconBg: 'bg-[--success-soft]',
      };
    default:
      return {
        bg: 'bg-[--surface-muted]',
        border: 'border-[--border]',
        text: 'text-[--text]',
        icon: Info,
        iconBg: 'bg-[--surface-strong]',
      };
  }
}

function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export function AlertBanner({ alerts, loading = false, onDismiss }: AlertBannerProps) {
  const [dismissedAlerts, setDismissedAlerts] = useState<Set<string>>(new Set());
  const [isExpanded, setIsExpanded] = useState(true);

  const handleDismiss = (alertId: string) => {
    setDismissedAlerts((prev) => new Set([...prev, alertId]));
    onDismiss?.(alertId);
  };

  const visibleAlerts = alerts.filter((alert) => !dismissedAlerts.has(alert.id));

  if (loading) {
    return (
      <div className="space-y-2">
        {[1, 2].map((i) => (
          <div key={i} className="bg-[--surface-muted] rounded-lg p-4 border border-[--border] animate-pulse">
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 bg-[--surface-strong] rounded-full"></div>
              <div className="flex-1 space-y-2">
                <div className="h-4 w-48 bg-[--surface-strong] rounded"></div>
                <div className="h-3 w-64 bg-[--surface-strong] rounded"></div>
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (!alerts || visibleAlerts.length === 0) {
    return null;
  }

  const criticalCount = visibleAlerts.filter((a) => a.severity === 'critical').length;
  const warningCount = visibleAlerts.filter((a) => a.severity === 'warning').length;
  const infoCount = visibleAlerts.filter((a) => a.severity === 'info').length;

  return (
    <div className="space-y-2">
      <div 
        className="flex items-center justify-between p-3 bg-[--surface-muted] rounded-lg border border-[--border] cursor-pointer hover:bg-[--surface-hover] transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          <Bell className="h-5 w-5 text-[--text]" />
          <span className="font-medium text-[--text]">Performance Alerts</span>
          <div className="flex items-center gap-2 ml-2">
            {criticalCount > 0 && (
              <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-[--error-soft] text-[--error]">
                {criticalCount} Critical
              </span>
            )}
            {warningCount > 0 && (
              <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-[--warning-soft] text-[--warning]">
                {warningCount} Warning
              </span>
            )}
            {infoCount > 0 && (
              <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-[--success-soft] text-[--success]">
                {infoCount} Info
              </span>
            )}
          </div>
        </div>
        <button className="p-1 hover:bg-[--surface-hover] rounded transition-colors">
          {isExpanded ? (
            <ChevronUp className="h-4 w-4 text-[--muted]" />
          ) : (
            <ChevronDown className="h-4 w-4 text-[--muted]" />
          )}
        </button>
      </div>

      {isExpanded && (
        <div className="space-y-2">
          {visibleAlerts.map((alert) => {
            const styles = getSeverityStyles(alert.severity);
            const Icon = styles.icon;

            return (
              <div
                key={alert.id}
                className={`flex items-start gap-3 p-4 rounded-lg border ${styles.bg} ${styles.border}`}
              >
                <div className={`flex items-center justify-center h-8 w-8 rounded-full ${styles.iconBg}`}>
                  <Icon className={`h-4 w-4 ${styles.text}`} />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h4 className={`font-medium ${styles.text}`}>{alert.title}</h4>
                    <span className="text-xs text-[--muted]">{formatTimestamp(alert.timestamp)}</span>
                  </div>
                  <p className="text-sm text-[--muted]">{alert.message}</p>
                  
                  {alert.metric && alert.value !== undefined && (
                    <div className="flex items-center gap-4 mt-2 text-sm">
                      <span className="text-[--muted]">{alert.metric}:</span>
                      <span className={`font-medium ${styles.text}`}>
                        {typeof alert.value === 'number' && alert.value < 1 
                          ? `${(alert.value * 100).toFixed(1)}%`
                          : alert.value}
                      </span>
                      {alert.threshold !== undefined && (
                        <span className="text-[--muted]">
                          (Threshold: {typeof alert.threshold === 'number' && alert.threshold < 1 
                            ? `${(alert.threshold * 100).toFixed(1)}%`
                            : alert.threshold})
                        </span>
                      )}
                    </div>
                  )}
                </div>

                {onDismiss && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDismiss(alert.id);
                    }}
                    className="p-1 hover:bg-[--surface-hover] rounded transition-colors"
                  >
                    <X className="h-4 w-4 text-[--muted]" />
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
