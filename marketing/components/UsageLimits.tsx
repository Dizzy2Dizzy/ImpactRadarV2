"use client";

import { AlertCircle } from "lucide-react";
import Link from "next/link";

interface UsageLimitsProps {
  current: number;
  limit: number;
  feature: string;
  unit?: string;
}

export function UsageLimits({
  current,
  limit,
  feature,
  unit = "items",
}: UsageLimitsProps) {
  const percentage = (current / limit) * 100;
  const isNearLimit = percentage >= 80;
  const isAtLimit = current >= limit;

  return (
    <div className="rounded-lg border border-white/10 bg-[--panel] p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-[--text]">{feature}</h3>
        <span className="text-sm text-[--muted]">
          {current} / {limit} {unit}
        </span>
      </div>

      <div className="relative h-2 rounded-full bg-white/5 overflow-hidden mb-3">
        <div
          className={`absolute inset-y-0 left-0 rounded-full transition-all ${
            isAtLimit
              ? "bg-red-500"
              : isNearLimit
              ? "bg-yellow-500"
              : "bg-[--primary]"
          }`}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>

      {isNearLimit && (
        <div className="flex items-start gap-2">
          <AlertCircle
            className={`h-4 w-4 mt-0.5 ${
              isAtLimit ? "text-red-400" : "text-yellow-400"
            }`}
          />
          <div className="flex-1">
            <p className="text-xs text-[--muted] mb-2">
              {isAtLimit
                ? `You've reached your ${feature.toLowerCase()} limit. Upgrade to add more.`
                : `You're using ${percentage.toFixed(0)}% of your ${feature.toLowerCase()} limit.`}
            </p>
            <Link
              href="/pricing"
              className="text-xs text-[--primary] hover:underline font-medium"
            >
              Upgrade for unlimited {unit} →
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
