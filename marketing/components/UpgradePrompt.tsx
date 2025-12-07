"use client";

import { ArrowRight, Sparkles, X } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

interface UpgradePromptProps {
  feature: string;
  description: string;
  plan?: "pro" | "enterprise";
  inline?: boolean;
}

export function UpgradePrompt({
  feature,
  description,
  plan = "pro",
  inline = false,
}: UpgradePromptProps) {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed && !inline) return null;

  const planName = plan === "pro" ? "Pro" : "Enterprise";
  const planPrice = plan === "pro" ? "$49/mo" : "$199/mo";

  if (inline) {
    return (
      <div className="rounded-xl border border-blue-500/20 bg-gradient-to-br from-blue-500/10 to-purple-500/10 p-8">
        <div className="flex items-start gap-4">
          <div className="rounded-lg bg-[--primary]/10 p-3">
            <Sparkles className="h-6 w-6 text-[--primary]" />
          </div>
          <div className="flex-1">
            <h3 className="text-xl font-semibold text-[--text] mb-2">
              Unlock {feature}
            </h3>
            <p className="text-[--muted] mb-4">{description}</p>
            <div className="flex items-center gap-3">
              <Link
                href="/pricing"
                className="inline-flex items-center gap-2 rounded-lg bg-[--primary] px-6 py-3 text-sm font-semibold text-black hover:bg-[--primary-contrast] hover:text-white transition-colors"
              >
                Upgrade to {planName} {planPrice}
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                href="/pricing"
                className="text-sm text-[--muted] hover:text-[--text] underline"
              >
                View all features
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 max-w-sm">
      <div className="rounded-xl border border-white/10 bg-[--panel] shadow-2xl p-6">
        <button
          onClick={() => setDismissed(true)}
          className="absolute top-3 right-3 text-[--muted] hover:text-[--text]"
        >
          <X className="h-5 w-5" />
        </button>
        <div className="flex items-start gap-3 mb-4">
          <div className="rounded-lg bg-[--primary]/10 p-2">
            <Sparkles className="h-5 w-5 text-[--primary]" />
          </div>
          <div className="flex-1">
            <h3 className="font-semibold text-[--text] mb-1">{feature}</h3>
            <p className="text-sm text-[--muted]">{description}</p>
          </div>
        </div>
        <Link
          href="/pricing"
          className="block w-full rounded-lg bg-[--primary] px-4 py-2.5 text-center text-sm font-semibold text-black hover:bg-[--primary-contrast] hover:text-white transition-colors"
        >
          Upgrade to {planName} →
        </Link>
      </div>
    </div>
  );
}
