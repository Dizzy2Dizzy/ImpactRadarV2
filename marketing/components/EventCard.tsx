'use client';

import { ScoreChip } from "./ScoreChip";
import { ExternalLink, TrendingUp, TrendingDown, Minus } from "lucide-react";

interface EventCardProps {
  title: string;
  company: string;
  date: string;
  category: string;
  score: number;
  direction: "positive" | "negative" | "neutral";
  sourceUrl?: string;
}

export function EventCard({
  title,
  company,
  date,
  category,
  score,
  direction,
  sourceUrl,
}: EventCardProps) {
  const directionIcon = {
    positive: <TrendingUp className="h-4 w-4 text-green-400" />,
    negative: <TrendingDown className="h-4 w-4 text-red-400" />,
    neutral: <Minus className="h-4 w-4 text-[--muted]" />,
  };

  return (
    <div className="relative rounded-2xl border border-white/10 bg-[--panel] p-4 hover:border-white/20 transition-all duration-200 group min-h-[160px] flex flex-col">
      <div className="flex items-start justify-between gap-4 flex-1">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <span className="inline-flex items-center rounded-md bg-white/5 px-2 py-1 text-xs font-medium text-[--muted]">
              {category}
            </span>
            {directionIcon[direction]}
          </div>
          <h3 className="text-sm font-semibold text-[--text] line-clamp-2 mb-1">
            {title}
          </h3>
          <div className="flex items-center gap-3 text-xs text-[--muted]">
            <span className="font-medium">{company}</span>
            <span>•</span>
            <time>{date}</time>
          </div>
        </div>
        <ScoreChip score={score} />
      </div>
      {sourceUrl && (
        <span
          role="link"
          tabIndex={0}
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            window.open(sourceUrl, '_blank', 'noopener,noreferrer');
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              e.stopPropagation();
              window.open(sourceUrl, '_blank', 'noopener,noreferrer');
            }
          }}
          className="mt-3 inline-flex items-center gap-1 text-xs text-[--primary] hover:text-[--accent] transition-colors cursor-pointer"
        >
          View source
          <ExternalLink className="h-3 w-3" />
        </span>
      )}
    </div>
  );
}
