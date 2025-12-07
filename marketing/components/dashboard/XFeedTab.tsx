'use client';

import { Twitter, Wrench } from 'lucide-react';

export function XFeedTab() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-3 mb-2">
          <Twitter className="h-8 w-8 text-[--primary]" />
          <h2 className="text-3xl font-bold text-[--text]">X.com Event Sentiment</h2>
        </div>
        <p className="text-[--muted]">
          Event-driven chatter from X.com linked to Impact Radar events
        </p>
      </div>

      {/* Under Construction Message */}
      <div className="bg-white/5 border border-white/10 rounded-lg p-12 text-center">
        <Wrench className="h-16 w-16 text-[--muted] mx-auto mb-4" />
        <h3 className="text-xl font-semibold text-[--text] mb-2">
          Under Construction
        </h3>
        <p className="text-[--muted] max-w-md mx-auto">
          The X sentiment feature is currently under development. Check back soon!
        </p>
      </div>
    </div>
  );
}
