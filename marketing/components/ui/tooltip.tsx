"use client";

import { useState, useId } from "react";
import { HelpCircle } from "lucide-react";

interface TooltipProps {
  content: React.ReactNode;
  children?: React.ReactNode;
}

export function Tooltip({ content, children }: TooltipProps) {
  const [isVisible, setIsVisible] = useState(false);
  const tooltipId = useId();

  return (
    <div className="relative inline-block">
      <button
        type="button"
        className="inline-flex items-center"
        onMouseEnter={() => setIsVisible(true)}
        onMouseLeave={() => setIsVisible(false)}
        onFocus={() => setIsVisible(true)}
        onBlur={() => setIsVisible(false)}
        aria-describedby={isVisible ? tooltipId : undefined}
        aria-label="More information"
      >
        {children || <HelpCircle className="h-4 w-4 text-[--muted] hover:text-[--text]" />}
      </button>
      {isVisible && (
        <div
          id={tooltipId}
          className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 text-xs text-white bg-gray-900 rounded-lg shadow-lg max-w-xl whitespace-normal"
          role="tooltip"
        >
          {content}
          <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-1 border-4 border-transparent border-t-gray-900" />
        </div>
      )}
    </div>
  );
}
