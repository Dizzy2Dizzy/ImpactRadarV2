'use client';

import { CheckCircle, XCircle, TrendingUp, TrendingDown, Flame, Award, Clock } from 'lucide-react';

interface Prediction {
  id: string;
  ticker: string;
  event_type: string;
  predicted_direction: 'up' | 'down';
  predicted_magnitude: number;
  actual_direction?: 'up' | 'down';
  actual_magnitude?: number;
  is_correct?: boolean;
  event_date: string;
  resolved_at?: string;
}

interface PredictionScorecardProps {
  predictions: Prediction[];
  winStreak?: number;
  lossStreak?: number;
  loading?: boolean;
}

function formatEventType(eventType: string): string {
  return eventType
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function formatPercentage(value: number): string {
  const percentage = value > 1 ? value : value * 100;
  return `${percentage >= 0 ? '+' : ''}${percentage.toFixed(2)}%`;
}

export function PredictionScorecard({
  predictions,
  winStreak = 0,
  lossStreak = 0,
  loading = false,
}: PredictionScorecardProps) {
  if (loading) {
    return (
      <div className="bg-white/5 rounded-lg p-6 border border-white/10">
        <div className="flex items-center gap-2 mb-6">
          <div className="h-5 w-5 bg-white/10 rounded animate-pulse"></div>
          <div className="h-6 w-48 bg-white/10 rounded animate-pulse"></div>
        </div>
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="flex items-center gap-4 p-4 bg-white/5 rounded-lg animate-pulse">
              <div className="h-10 w-10 bg-white/10 rounded-full"></div>
              <div className="flex-1 space-y-2">
                <div className="h-4 w-32 bg-white/10 rounded"></div>
                <div className="h-3 w-24 bg-white/10 rounded"></div>
              </div>
              <div className="h-8 w-20 bg-white/10 rounded"></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (!predictions || predictions.length === 0) {
    return (
      <div className="bg-white/5 rounded-lg p-6 border border-white/10">
        <div className="flex items-center gap-2 mb-6">
          <Award className="h-5 w-5 text-emerald-400" />
          <h3 className="text-lg font-semibold text-[--text]">Prediction Scorecard</h3>
        </div>
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <Clock className="w-12 h-12 text-[--muted] mb-4" />
          <h4 className="text-lg font-semibold text-[--text] mb-2">No Predictions Yet</h4>
          <p className="text-[--muted] max-w-md">
            Recent predictions and their outcomes will appear here once events are tracked and resolved.
          </p>
        </div>
      </div>
    );
  }

  const currentStreak = winStreak > 0 ? winStreak : -lossStreak;
  const streakType = currentStreak >= 0 ? 'win' : 'loss';
  const streakCount = Math.abs(currentStreak);

  return (
    <div className="bg-white/5 rounded-lg p-6 border border-white/10">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Award className="h-5 w-5 text-emerald-400" />
          <h3 className="text-lg font-semibold text-[--text]">Prediction Scorecard</h3>
        </div>
        
        {streakCount > 0 && (
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full ${
            streakType === 'win' 
              ? 'bg-emerald-500/20 border border-emerald-500/30' 
              : 'bg-red-500/20 border border-red-500/30'
          }`}>
            <Flame className={`h-4 w-4 ${streakType === 'win' ? 'text-emerald-400' : 'text-red-400'}`} />
            <span className={`text-sm font-medium ${streakType === 'win' ? 'text-emerald-400' : 'text-red-400'}`}>
              {streakCount} {streakType === 'win' ? 'Win' : 'Loss'} Streak
            </span>
          </div>
        )}
      </div>

      <div className="space-y-3">
        {predictions.map((prediction) => {
          const isPending = prediction.is_correct === undefined;
          const isCorrect = prediction.is_correct;

          return (
            <div
              key={prediction.id}
              className={`flex items-center gap-4 p-4 rounded-lg border transition-colors ${
                isPending
                  ? 'bg-white/5 border-white/10'
                  : isCorrect
                  ? 'bg-emerald-500/10 border-emerald-500/20'
                  : 'bg-red-500/10 border-red-500/20'
              }`}
            >
              <div className={`flex items-center justify-center h-10 w-10 rounded-full ${
                isPending
                  ? 'bg-white/10'
                  : isCorrect
                  ? 'bg-emerald-500/20'
                  : 'bg-red-500/20'
              }`}>
                {isPending ? (
                  <Clock className="h-5 w-5 text-[--muted]" />
                ) : isCorrect ? (
                  <CheckCircle className="h-5 w-5 text-emerald-400" />
                ) : (
                  <XCircle className="h-5 w-5 text-red-400" />
                )}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-[--text]">{prediction.ticker}</span>
                  <span className="text-xs px-2 py-0.5 bg-white/10 rounded text-[--muted]">
                    {formatEventType(prediction.event_type)}
                  </span>
                </div>
                <div className="text-sm text-[--muted] mt-1">
                  {formatDate(prediction.event_date)}
                </div>
              </div>

              <div className="flex flex-col items-end gap-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-[--muted]">Predicted:</span>
                  <div className={`flex items-center gap-1 ${
                    prediction.predicted_direction === 'up' ? 'text-emerald-400' : 'text-red-400'
                  }`}>
                    {prediction.predicted_direction === 'up' ? (
                      <TrendingUp className="h-3 w-3" />
                    ) : (
                      <TrendingDown className="h-3 w-3" />
                    )}
                    <span className="text-sm font-medium">
                      {formatPercentage(prediction.predicted_magnitude)}
                    </span>
                  </div>
                </div>

                {!isPending && prediction.actual_magnitude !== undefined && (
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-[--muted]">Actual:</span>
                    <div className={`flex items-center gap-1 ${
                      prediction.actual_direction === 'up' ? 'text-emerald-400' : 'text-red-400'
                    }`}>
                      {prediction.actual_direction === 'up' ? (
                        <TrendingUp className="h-3 w-3" />
                      ) : (
                        <TrendingDown className="h-3 w-3" />
                      )}
                      <span className="text-sm font-medium">
                        {formatPercentage(prediction.actual_magnitude)}
                      </span>
                    </div>
                  </div>
                )}

                {isPending && (
                  <span className="text-xs text-amber-400">Pending</span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-6 pt-4 border-t border-white/10">
        <div className="flex items-center justify-between text-sm text-[--muted]">
          <span>Showing {predictions.length} recent predictions</span>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-emerald-400" />
              <span>{predictions.filter(p => p.is_correct === true).length} Correct</span>
            </div>
            <div className="flex items-center gap-2">
              <XCircle className="h-4 w-4 text-red-400" />
              <span>{predictions.filter(p => p.is_correct === false).length} Incorrect</span>
            </div>
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-amber-400" />
              <span>{predictions.filter(p => p.is_correct === undefined).length} Pending</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
