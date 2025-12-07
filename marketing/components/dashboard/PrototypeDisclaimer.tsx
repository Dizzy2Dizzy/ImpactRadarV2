'use client';

import { Info } from 'lucide-react';
import Link from 'next/link';

export function PrototypeDisclaimer() {
  return (
    <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-4 flex gap-3">
      <Info className="h-5 w-5 text-blue-400 flex-shrink-0 mt-0.5" />
      <div className="flex-1">
        <h3 className="text-sm font-semibold text-blue-300 mb-1">
          Experimental Prototype
        </h3>
        <p className="text-sm text-blue-200/90">
          The Market Echo Engine is an experimental, self-learning prototype. Current training data: ~355 SEC 8-K events and growing. Metrics are research tools, not guarantees or investment advice.
        </p>
        <Link 
          href="/market-echo" 
          className="text-sm text-blue-400 hover:text-blue-300 underline mt-2 inline-block transition-colors"
        >
          Learn more about limitations
        </Link>
      </div>
    </div>
  );
}
