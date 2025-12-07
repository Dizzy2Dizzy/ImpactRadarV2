'use client';

import { useState, useEffect, useRef } from 'react';
import { Lock } from 'lucide-react';
import Link from 'next/link';

interface ScorePillProps {
  score?: {
    final_score: number;
    confidence: number;
    factors: {
      sector: number;
      volatility: number;
      earnings_proximity: number;
      market_mood: number;
      after_hours: number;
      duplicate_penalty: number;
    };
  } | 'upgrade_required' | null;
  loading?: boolean;
}

export function ScorePill({ score, loading }: ScorePillProps) {
  const [showTooltip, setShowTooltip] = useState(false);
  const [tooltipPosition, setTooltipPosition] = useState<{ top: number; left: number }>({ top: 0, left: 0 });
  const pillRef = useRef<HTMLDivElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  const clampToViewport = (rect: DOMRect, margin = 8) => {
    const tooltipWidth = 200;
    const tooltipHeight = 150;
    
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
    if (!showTooltip && pillRef.current) {
      const rect = pillRef.current.getBoundingClientRect();
      const position = clampToViewport(rect);
      setTooltipPosition(position);
    }
    setShowTooltip(!showTooltip);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleToggleTooltip();
    } else if (e.key === 'Escape') {
      setShowTooltip(false);
    }
  };

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        tooltipRef.current &&
        !tooltipRef.current.contains(e.target as Node) &&
        pillRef.current &&
        !pillRef.current.contains(e.target as Node)
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

  if (loading) {
    return (
      <div className="inline-flex flex-col gap-0.5">
        <div className="h-5 w-16 bg-[--surface-muted] animate-pulse rounded" />
        <div className="h-1 w-16 bg-[--surface-muted] animate-pulse rounded-full" />
      </div>
    );
  }

  if (score === 'upgrade_required') {
    return (
      <div className="relative inline-block" ref={pillRef}>
        <Link
          href="/pricing?plan=pro"
          role="button"
          tabIndex={0}
          aria-label="Impact scores are a Pro feature. Start a 14-day trial"
          onMouseEnter={() => {
            if (pillRef.current) {
              const rect = pillRef.current.getBoundingClientRect();
              const position = clampToViewport(rect);
              setTooltipPosition(position);
              setShowTooltip(true);
            }
          }}
          onMouseLeave={() => setShowTooltip(false)}
          onFocus={() => {
            if (pillRef.current) {
              const rect = pillRef.current.getBoundingClientRect();
              const position = clampToViewport(rect);
              setTooltipPosition(position);
              setShowTooltip(true);
            }
          }}
          onBlur={() => setShowTooltip(false)}
          onKeyDown={handleKeyDown}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-[--warning-soft] border border-[--border-strong] text-[--warning] hover:bg-[--surface-hover] transition-colors"
        >
          <Lock className="h-3.5 w-3.5" />
          <span className="text-sm font-medium">Pro</span>
        </Link>
        {showTooltip && (
          <div
            ref={tooltipRef}
            role="tooltip"
            aria-live="polite"
            className="fixed z-50 px-3 py-2 text-xs text-[--text] bg-[--panel] border border-[--border] rounded-lg shadow-lg max-w-xs whitespace-normal"
            style={{ top: `${tooltipPosition.top}px`, left: `${tooltipPosition.left}px` }}
          >
            Impact scores are a Pro feature. Start a 14-day trial.
            <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-1 border-4 border-transparent border-t-[--panel]" />
          </div>
        )}
      </div>
    );
  }

  if (!score) {
    return null;
  }

  const getScoreColor = (finalScore: number) => {
    if (finalScore >= 76) return { bg: 'bg-[--success-soft]', border: 'border-[--border-strong]', text: 'text-[--success]', barBg: 'bg-[--success]' };
    if (finalScore >= 51) return { bg: 'bg-[--primary-soft]', border: 'border-[--border-strong]', text: 'text-[--primary]', barBg: 'bg-[--primary]' };
    if (finalScore >= 26) return { bg: 'bg-[--warning-soft]', border: 'border-[--border-strong]', text: 'text-[--warning]', barBg: 'bg-[--warning]' };
    return { bg: 'bg-[--error-soft]', border: 'border-[--border-strong]', text: 'text-[--error]', barBg: 'bg-[--error]' };
  };

  const getTopFactors = () => {
    if (!score.factors || typeof score.factors !== 'object') {
      return [];
    }
    
    const factorEntries = Object.entries(score.factors)
      .map(([name, value]) => ({ name, value: value as number }))
      .filter(f => f.value !== 0)
      .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
      .slice(0, 3);

    const factorNames: { [key: string]: string } = {
      sector: 'Sector',
      volatility: 'Volatility',
      earnings_proximity: 'Earnings',
      market_mood: 'Market',
      after_hours: 'After Hours',
      duplicate_penalty: 'Duplicate'
    };

    return factorEntries.map(f => ({
      name: factorNames[f.name] || f.name,
      value: f.value > 0 ? `+${f.value}` : `${f.value}`
    }));
  };

  const colors = getScoreColor(score.final_score);
  const topFactors = getTopFactors();
  const totalFactors = score.factors && typeof score.factors === 'object' ? Object.values(score.factors).filter(v => v !== 0).length : 0;
  const additionalFactors = Math.max(0, totalFactors - 3);

  return (
    <div className="relative inline-block">
      <div
        ref={pillRef}
        role="button"
        tabIndex={0}
        aria-label={`Impact score ${score.final_score}, confidence ${Math.round(score.confidence * 100)} percent`}
        onClick={handleToggleTooltip}
        onKeyDown={handleKeyDown}
        onMouseEnter={() => {
          if (pillRef.current) {
            const rect = pillRef.current.getBoundingClientRect();
            const position = clampToViewport(rect);
            setTooltipPosition(position);
            setShowTooltip(true);
          }
        }}
        onMouseLeave={() => setShowTooltip(false)}
        className={`inline-flex flex-col gap-0.5 px-2.5 py-1 rounded ${colors.bg} border ${colors.border} cursor-pointer transition-all hover:opacity-80`}
      >
        <div className="flex items-center gap-1.5">
          <span className={`text-sm font-bold ${colors.text}`}>
            {score.final_score}
          </span>
        </div>
        <div className="w-full h-1 bg-[--surface-strong] rounded-full overflow-hidden">
          <div
            className={`h-full ${colors.barBg}`}
            style={{ width: `${score.confidence * 100}%` }}
          />
        </div>
      </div>

      {showTooltip && (
        <div
          ref={tooltipRef}
          role="tooltip"
          aria-live="polite"
          className="fixed z-50 px-3 py-2 text-[--text] bg-[--panel] border border-[--border] rounded-lg shadow-lg whitespace-normal"
          style={{ top: `${tooltipPosition.top}px`, left: `${tooltipPosition.left}px`, maxWidth: '200px' }}
        >
          <div className="text-xs space-y-1">
            <div className="font-semibold">Impact Score: {score.final_score}</div>
            <div className="text-[--muted]">Confidence: {Math.round(score.confidence * 100)}%</div>
            {topFactors.length > 0 && (
              <>
                <div className="border-t border-[--border] my-1 pt-1 font-semibold">
                  Top Factors:
                </div>
                {topFactors.map((f, i) => (
                  <div key={i} className="text-[--text]">
                    {f.name}: {f.value}
                  </div>
                ))}
                {additionalFactors > 0 && (
                  <div className="text-[--muted] text-xs italic">
                    +{additionalFactors} more
                  </div>
                )}
              </>
            )}
          </div>
          <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-1 border-4 border-transparent border-t-[--panel]" />
        </div>
      )}
    </div>
  );
}
