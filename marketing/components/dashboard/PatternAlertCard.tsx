'use client';

import { PatternAlert } from '@/lib/api';
import { Check, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface PatternAlertCardProps {
  alert: PatternAlert;
  onAcknowledge: (alertId: number) => void;
}

export function PatternAlertCard({ alert, onAcknowledge }: PatternAlertCardProps) {
  const getCorrelationBadgeColor = (score: number) => {
    if (score > 0.8) return 'bg-[--success-soft] text-[--success] border-[--border-strong]';
    if (score > 0.6) return 'bg-[--warning-soft] text-[--warning] border-[--border-strong]';
    return 'bg-[--warning-soft] text-[--warning] border-[--border-strong]';
  };

  const getDirectionDisplay = () => {
    switch (alert.aggregated_direction?.toLowerCase()) {
      case 'positive':
        return {
          icon: <TrendingUp className="h-4 w-4" />,
          color: 'text-[--success]',
          label: 'Bullish',
        };
      case 'negative':
        return {
          icon: <TrendingDown className="h-4 w-4" />,
          color: 'text-[--error]',
          label: 'Bearish',
        };
      default:
        return {
          icon: <Minus className="h-4 w-4" />,
          color: 'text-[--muted]',
          label: 'Neutral',
        };
    }
  };

  const direction = getDirectionDisplay();
  const isAcknowledged = alert.status === 'acknowledged';

  return (
    <div
      className={`bg-[--surface-muted] rounded-lg p-6 border-l-4 transition-all ${
        isAcknowledged 
          ? 'border-[--border] opacity-60' 
          : 'border-[--primary] hover:bg-[--surface-hover]'
      }`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-3">
            <h3 className="text-lg font-semibold text-[--text]">
              {alert.pattern_name || 'Pattern Alert'}
            </h3>
            <span
              className={`px-2 py-1 rounded text-xs font-medium border ${getCorrelationBadgeColor(
                alert.correlation_score
              )}`}
            >
              {Math.round(alert.correlation_score * 100)}% Correlation
            </span>
            {isAcknowledged && (
              <span className="px-2 py-1 bg-[--surface-muted] text-[--muted] rounded text-xs flex items-center gap-1">
                <Check className="h-3 w-3" />
                Acknowledged
              </span>
            )}
          </div>

          <div className="mb-3">
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2 py-0.5 bg-[--primary-soft] text-[--primary] rounded text-sm font-mono">
                {alert.ticker}
              </span>
              <span className="text-[--muted] text-sm">{alert.company_name}</span>
            </div>
          </div>

          <div className="flex items-center gap-4 mb-3">
            <div className="flex items-center gap-2">
              <span className="text-sm text-[--muted]">Impact Score:</span>
              <span className="px-2 py-1 bg-[--accent-soft] text-[--accent] rounded text-sm font-semibold">
                {alert.aggregated_impact_score}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-[--muted]">Direction:</span>
              <span className={`flex items-center gap-1 text-sm font-medium ${direction.color}`}>
                {direction.icon}
                {direction.label}
              </span>
            </div>
          </div>

          {alert.rationale && (
            <div className="mb-3 p-3 bg-[--surface-muted] rounded border border-[--border]">
              <p className="text-sm text-[--text] italic">{alert.rationale}</p>
            </div>
          )}

          <div className="mb-2">
            <p className="text-xs text-[--muted] mb-1">
              {alert.event_ids.length} Event{alert.event_ids.length !== 1 ? 's' : ''} Detected:
            </p>
            <div className="flex flex-wrap gap-2">
              {alert.event_ids.map((eventId) => (
                <span
                  key={eventId}
                  className="px-2 py-1 bg-[--surface-muted] text-[--muted] rounded text-xs border border-[--border]"
                >
                  Event #{eventId}
                </span>
              ))}
            </div>
          </div>

          <p className="text-xs text-[--muted] mt-2">
            Detected: {new Date(alert.detected_at).toLocaleString()}
            {isAcknowledged && alert.acknowledged_at && (
              <span className="ml-2">
                • Acknowledged: {new Date(alert.acknowledged_at).toLocaleString()}
              </span>
            )}
          </p>
        </div>

        {!isAcknowledged && (
          <Button
            onClick={() => onAcknowledge(alert.id)}
            variant="outline"
            size="sm"
            className="flex-shrink-0"
          >
            <Check className="h-4 w-4 mr-1" />
            Acknowledge
          </Button>
        )}
      </div>
    </div>
  );
}
