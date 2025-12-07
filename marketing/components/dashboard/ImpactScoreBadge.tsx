'use client';

import { useState, useRef, useEffect } from 'react';
import { Sparkles, Target, Cpu, TrendingUp, TrendingDown, Calculator, Zap } from 'lucide-react';

export type HorizonType = '1d' | '5d' | '20d';
export type ModelSource = 'family-specific' | 'global' | 'deterministic';
export type DisplayVersion = 'v1.0' | 'v1.5' | 'v2.0';

export interface ImpactScoreBadgeProps {
  baseScore: number;  // 0-100
  mlAdjustedScore?: number;  // 0-100 (optional)
  mlConfidence?: number;  // 0.0-1.0 (optional)
  modelSource?: ModelSource;
  modelVersion?: string;  // e.g., "v1.0.2"
  horizons?: HorizonType[];  // Which horizons have ML predictions
  compact?: boolean;  // For smaller displays like LiveTape
  showDelta?: boolean;  // Show the difference between base and ML score
  displayVersion?: DisplayVersion;  // Which model version to highlight (v1.0, v1.5, v2.0)
}

export function ImpactScoreBadge({
  baseScore,
  mlAdjustedScore,
  mlConfidence,
  modelSource,
  modelVersion,
  horizons = [],
  compact = false,
  showDelta = true,
  displayVersion = 'v1.5',
}: ImpactScoreBadgeProps) {
  const [showTooltip, setShowTooltip] = useState(false);
  const [tooltipPosition, setTooltipPosition] = useState<{ top: number; left: number }>({ top: 0, left: 0 });
  const badgeRef = useRef<HTMLDivElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  // Only show ML sections if there's an actual ML prediction (not just deterministic)
  const hasMLScore = mlAdjustedScore !== undefined && 
                     mlAdjustedScore !== null && 
                     modelSource !== 'deterministic' &&
                     mlConfidence !== null &&
                     mlConfidence !== undefined;
  
  // Determine display score based on selected model version
  const getDisplayScore = () => {
    switch (displayVersion) {
      case 'v1.0':
        return baseScore; // Deterministic only
      case 'v1.5':
        return hasMLScore ? mlAdjustedScore : baseScore; // Hybrid (default)
      case 'v2.0':
        return hasMLScore ? mlAdjustedScore : baseScore; // ML-only (same as hybrid but filtered)
      default:
        return hasMLScore ? mlAdjustedScore : baseScore;
    }
  };

  const displayScore = getDisplayScore();
  const delta = hasMLScore ? (mlAdjustedScore || 0) - baseScore : 0;
  
  // Version label for display
  const getVersionLabel = () => {
    switch (displayVersion) {
      case 'v1.0':
        return { label: 'Deterministic', Icon: Calculator };
      case 'v1.5':
        return { label: hasMLScore ? 'Hybrid' : 'Deterministic', Icon: hasMLScore ? Zap : Calculator };
      case 'v2.0':
        return { label: hasMLScore ? 'Market Echo' : 'Deterministic', Icon: hasMLScore ? Cpu : Calculator };
      default:
        return { label: hasMLScore ? 'Hybrid' : 'Deterministic', Icon: hasMLScore ? Zap : Calculator };
    }
  };
  
  const versionInfo = getVersionLabel();

  const clampToViewport = (rect: DOMRect, margin = 8) => {
    const tooltipWidth = 280;
    const tooltipHeight = 200;
    
    let left = rect.left + rect.width / 2 - tooltipWidth / 2;
    let top = rect.top - tooltipHeight - margin;
    
    if (left < margin) left = margin;
    if (left + tooltipWidth > window.innerWidth - margin) {
      left = window.innerWidth - tooltipWidth - margin;
    }
    
    if (top < margin) {
      top = rect.bottom + margin;
    }
    
    return { top, left };
  };

  const handleToggleTooltip = () => {
    if (!showTooltip && badgeRef.current) {
      const rect = badgeRef.current.getBoundingClientRect();
      const position = clampToViewport(rect);
      setTooltipPosition(position);
    }
    setShowTooltip(!showTooltip);
  };

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        tooltipRef.current &&
        !tooltipRef.current.contains(e.target as Node) &&
        badgeRef.current &&
        !badgeRef.current.contains(e.target as Node)
      ) {
        setShowTooltip(false);
      }
    };

    if (showTooltip) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showTooltip]);

  const getScoreColor = (score: number) => {
    if (score >= 76) return { bg: 'bg-[--success-soft]', border: 'border-[--border-strong]', text: 'text-[--success]', barBg: 'bg-[--success]' };
    if (score >= 51) return { bg: 'bg-[--primary-soft]', border: 'border-[--border-strong]', text: 'text-[--primary]', barBg: 'bg-[--primary]' };
    if (score >= 26) return { bg: 'bg-[--warning-soft]', border: 'border-[--border-strong]', text: 'text-[--warning]', barBg: 'bg-[--warning]' };
    return { bg: 'bg-[--error-soft]', border: 'border-[--border-strong]', text: 'text-[--error]', barBg: 'bg-[--error]' };
  };

  const getModelSourceIcon = (source?: ModelSource) => {
    switch (source) {
      case 'family-specific':
        return <Sparkles className="h-3 w-3" />;
      case 'global':
        return <Cpu className="h-3 w-3" />;
      case 'deterministic':
        return <Target className="h-3 w-3" />;
      default:
        return <Target className="h-3 w-3" />;
    }
  };

  const getModelSourceLabel = (source?: ModelSource) => {
    switch (source) {
      case 'family-specific':
        return 'Family-Specific Model';
      case 'global':
        return 'Global Model';
      case 'deterministic':
        return 'Deterministic Only';
      default:
        return 'Base Scoring';
    }
  };

  const colors = getScoreColor(displayScore);

  // Compact mode for LiveTape
  if (compact) {
    return (
      <div className="relative inline-block">
        <div
          ref={badgeRef}
          role="button"
          tabIndex={0}
          aria-label={`Impact score ${displayScore}`}
          onClick={handleToggleTooltip}
          onMouseEnter={() => {
            if (badgeRef.current) {
              const rect = badgeRef.current.getBoundingClientRect();
              const position = clampToViewport(rect);
              setTooltipPosition(position);
              setShowTooltip(true);
            }
          }}
          onMouseLeave={() => setShowTooltip(false)}
          className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded ${colors.bg} border ${colors.border} cursor-pointer transition-all hover:opacity-80`}
        >
          <span className={`text-xs font-bold ${colors.text}`}>
            {displayScore}
          </span>
          {hasMLScore && (
            <Sparkles className={`h-2.5 w-2.5 ${colors.text}`} />
          )}
        </div>

        {showTooltip && (
          <div
            ref={tooltipRef}
            role="tooltip"
            className="fixed z-50 px-3 py-2 text-[--text] bg-[--panel] border border-[--border] rounded-lg shadow-lg"
            style={{ top: `${tooltipPosition.top}px`, left: `${tooltipPosition.left}px`, maxWidth: '280px' }}
          >
            <div className="text-xs space-y-2">
              <div className="font-semibold text-sm">Impact Score</div>
              
              <div className="space-y-1">
                <div className="flex justify-between">
                  <span className="text-[--muted]">Base:</span>
                  <span className="font-medium">{baseScore}</span>
                </div>
                {hasMLScore && (
                  <>
                    <div className="flex justify-between">
                      <span className="text-[--muted]">ML-Adjusted:</span>
                      <span className={`font-medium ${colors.text}`}>{mlAdjustedScore}</span>
                    </div>
                    {mlConfidence !== undefined && mlConfidence !== null && !isNaN(mlConfidence) && (
                      <div className="flex justify-between">
                        <span className="text-[--muted]">ML Confidence:</span>
                        <span className="font-medium">{Math.round(mlConfidence * 100)}%</span>
                      </div>
                    )}
                  </>
                )}
              </div>

              {(modelSource || modelVersion || horizons.length > 0) && (
                <>
                  <div className="border-t border-[--border] pt-2">
                    <div className="text-[--muted] text-xs mb-1">Model Info</div>
                    {modelSource && (
                      <div className="flex items-center gap-1 text-[--text]">
                        {getModelSourceIcon(modelSource)}
                        <span>{getModelSourceLabel(modelSource)}</span>
                      </div>
                    )}
                    {modelVersion && (
                      <div className="text-[--text]">Version: {modelVersion}</div>
                    )}
                    {horizons.length > 0 && (
                      <div className="flex items-center gap-1 mt-1">
                        <span className="text-[--muted] text-xs">Horizons:</span>
                        {horizons.map(h => (
                          <span key={h} className="px-1 py-0.5 bg-[--primary-soft] text-[--primary] rounded text-xs">
                            {h}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>
            <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-1 border-4 border-transparent border-t-[--panel]" />
          </div>
        )}
      </div>
    );
  }

  // Full mode
  return (
    <div className="relative inline-block">
      <div
        ref={badgeRef}
        role="button"
        tabIndex={0}
        aria-label={`Impact score ${displayScore}`}
        onClick={handleToggleTooltip}
        onMouseEnter={() => {
          if (badgeRef.current) {
            const rect = badgeRef.current.getBoundingClientRect();
            const position = clampToViewport(rect);
            setTooltipPosition(position);
            setShowTooltip(true);
          }
        }}
        onMouseLeave={() => setShowTooltip(false)}
        className="inline-flex flex-col gap-2 cursor-pointer"
      >
        {/* Main Score Display */}
        <div className={`flex items-center gap-2 px-3 py-2 rounded-lg border ${colors.bg} ${colors.border} transition-all hover:opacity-80`}>
          <div className="flex items-center gap-2">
            {hasMLScore ? (
              <>
                <div className="flex flex-col">
                  <div className="flex items-center gap-1">
                    <Sparkles className={`h-3.5 w-3.5 ${colors.text}`} />
                    <span className="text-xs text-[--muted]">AI-Adjusted</span>
                  </div>
                  <span className={`text-xl font-bold ${colors.text}`}>
                    {mlAdjustedScore}
                  </span>
                </div>
                
                {showDelta && delta !== 0 && (
                  <div className="flex items-center gap-1 ml-2">
                    {delta > 0 ? (
                      <TrendingUp className="h-3 w-3 text-[--success]" />
                    ) : (
                      <TrendingDown className="h-3 w-3 text-[--error]" />
                    )}
                    <span className={`text-xs font-medium ${delta > 0 ? 'text-[--success]' : 'text-[--error]'}`}>
                      {delta > 0 ? '+' : ''}{delta}
                    </span>
                  </div>
                )}
                
                <div className="ml-2 pl-2 border-l border-white/10">
                  <div className="text-xs text-[--muted]">Base</div>
                  <span className="text-sm font-semibold text-[--text]">
                    {baseScore}
                  </span>
                </div>
              </>
            ) : (
              <div className="flex items-center gap-2">
                <div className="flex flex-col">
                  <div className="flex items-center gap-1">
                    <Target className="h-3.5 w-3.5 text-[--muted]" />
                    <span className="text-xs text-[--muted]">Base Score</span>
                  </div>
                  <span className={`text-xl font-bold ${colors.text}`}>
                    {baseScore}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Confidence Bar */}
          {hasMLScore && mlConfidence !== undefined && (
            <div className="flex flex-col gap-1 ml-auto">
              <span className="text-xs text-[--muted] text-right">
                {Math.round(mlConfidence * 100)}% conf
              </span>
              <div className="w-16 h-1.5 bg-[--surface-strong] rounded-full overflow-hidden">
                <div
                  className={`h-full ${colors.barBg}`}
                  style={{ width: `${mlConfidence * 100}%` }}
                />
              </div>
            </div>
          )}
        </div>

        {/* Horizon Tags */}
        {horizons.length > 0 && (
          <div className="flex items-center gap-1">
            <span className="text-xs text-[--muted]">ML Horizons:</span>
            {horizons.map(horizon => (
              <span
                key={horizon}
                className="px-2 py-0.5 bg-[--primary-soft] border border-[--border-strong] text-[--primary] rounded text-xs font-medium"
              >
                {horizon}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Tooltip */}
      {showTooltip && (
        <div
          ref={tooltipRef}
          role="tooltip"
          className="fixed z-50 px-4 py-3 text-[--text] bg-[--panel] border border-[--border] rounded-lg shadow-lg"
          style={{ top: `${tooltipPosition.top}px`, left: `${tooltipPosition.left}px`, maxWidth: '280px' }}
        >
          <div className="text-xs space-y-2">
            <div className="font-semibold text-sm border-b border-[--border] pb-2">
              Impact Score Breakdown
            </div>
            
            <div className="space-y-1.5">
              <div className="flex justify-between items-center">
                <div className="flex items-center gap-1.5">
                  <Target className="h-3.5 w-3.5 text-[--muted]" />
                  <span className="text-[--muted]">Base Score (Deterministic):</span>
                </div>
                <span className="font-medium">{baseScore}</span>
              </div>
              
              {hasMLScore && (
                <>
                  <div className="flex justify-between items-center">
                    <div className="flex items-center gap-1.5">
                      <Sparkles className={`h-3.5 w-3.5 ${colors.text}`} />
                      <span className="text-[--muted]">Market Echo ML:</span>
                    </div>
                    <span className={`font-medium ${colors.text}`}>{mlAdjustedScore}</span>
                  </div>
                  
                  {delta !== 0 && (
                    <div className="flex justify-between items-center">
                      <span className="text-[--muted]">ML Adjustment:</span>
                      <span className={`font-medium ${delta > 0 ? 'text-[--success]' : 'text-[--error]'}`}>
                        {delta > 0 ? '+' : ''}{delta} points
                      </span>
                    </div>
                  )}
                  
                  {mlConfidence !== undefined && (
                    <div className="flex justify-between items-center">
                      <span className="text-[--muted]">ML Confidence:</span>
                      <span className="font-medium">{Math.round(mlConfidence * 100)}%</span>
                    </div>
                  )}
                </>
              )}
            </div>

            {(modelSource || modelVersion || horizons.length > 0) && (
              <>
                <div className="border-t border-[--border] pt-2 mt-2">
                  <div className="text-[--muted] text-xs font-semibold mb-1.5">Model Provenance</div>
                  {modelSource && (
                    <div className="flex items-center gap-1.5 text-[--text] mb-1">
                      {getModelSourceIcon(modelSource)}
                      <span>{getModelSourceLabel(modelSource)}</span>
                    </div>
                  )}
                  {modelVersion && (
                    <div className="text-[--text] text-xs">
                      Version: <span className="font-mono">{modelVersion}</span>
                    </div>
                  )}
                  {horizons.length > 0 && (
                    <div className="flex items-center gap-1.5 mt-1.5">
                      <span className="text-[--muted] text-xs">Prediction Horizons:</span>
                      <div className="flex gap-1">
                        {horizons.map(h => (
                          <span key={h} className="px-1.5 py-0.5 bg-[--primary-soft] border border-[--border-strong] text-[--primary] rounded text-xs font-medium">
                            {h}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </>
            )}

            {!hasMLScore && (
              <div className="border-t border-[--border] pt-2 mt-2">
                <div className="text-xs text-[--muted] italic">
                  ML predictions not available for this event. Showing deterministic base score only.
                </div>
              </div>
            )}
          </div>
          <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-1 border-4 border-transparent border-t-[--panel]" />
        </div>
      )}
    </div>
  );
}
