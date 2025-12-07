"use client";

import { useState } from "react";

interface PricingToggleProps {
  onToggle: (isAnnual: boolean) => void;
}

export function PricingToggle({ onToggle }: PricingToggleProps) {
  const [isAnnual, setIsAnnual] = useState(false);

  const handleToggle = () => {
    const newValue = !isAnnual;
    setIsAnnual(newValue);
    onToggle(newValue);
  };

  return (
    <div className="flex items-center justify-center gap-4 mb-12">
      <span
        className={`text-sm font-medium ${
          !isAnnual ? "text-[--text]" : "text-[--muted]"
        }`}
      >
        Monthly
      </span>
      <button
        onClick={handleToggle}
        className="relative inline-flex h-7 w-14 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-[--primary] focus:ring-offset-2 focus:ring-offset-[--background]"
        style={{
          backgroundColor: isAnnual
            ? "var(--primary)"
            : "rgba(255, 255, 255, 0.1)",
        }}
      >
        <span
          className={`inline-block h-5 w-5 transform rounded-full bg-white transition-transform ${
            isAnnual ? "translate-x-8" : "translate-x-1"
          }`}
        />
      </button>
      <div className="flex items-center gap-2">
        <span
          className={`text-sm font-medium ${
            isAnnual ? "text-[--text]" : "text-[--muted]"
          }`}
        >
          Annual
        </span>
        <span className="inline-flex items-center rounded-full bg-green-500/10 px-2.5 py-0.5 text-xs font-medium text-green-400">
          Save 20%
        </span>
      </div>
    </div>
  );
}
